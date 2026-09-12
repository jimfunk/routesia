#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>



static PyObject *StructError = NULL;
static PyObject *NullTerminatedString_Class = NULL;

typedef struct {
    PyObject *fixed_size;
    PyObject *var_defs;
    PyObject *type_meta;
    PyObject *from_buffer;
    PyObject *packed;
    PyObject *to_bytes;
} InternedKeys;

static InternedKeys keys = {NULL, NULL, NULL};

/* Compatibility shims for Python version differences */
static inline int
pc_PyLong_AsByteArray(PyObject *value, unsigned char *bytes, size_t n, int little_endian, int is_signed)
{
    if (!PyLong_Check(value) && !PyBool_Check(value)) {
        PyErr_Format(PyExc_TypeError, "expected integer, %.200s found", Py_TYPE(value)->tp_name);
        return -1;
    }
#if PY_VERSION_HEX >= 0x030D0000
    int flags = (little_endian ? Py_ASNATIVEBYTES_LITTLE_ENDIAN : Py_ASNATIVEBYTES_BIG_ENDIAN);
    if (!is_signed) flags |= Py_ASNATIVEBYTES_UNSIGNED_BUFFER;
    return PyLong_AsNativeBytes(value, bytes, n, flags) == -1 ? -1 : 0;
#else
    extern int _PyLong_AsByteArray(PyLongObject* v, unsigned char* bytes, size_t n, int little_endian, int is_signed);
    int res = -1;
    PyObject *long_val = PyNumber_Long(value);
    if (!long_val) return -1;
    res = _PyLong_AsByteArray((PyLongObject*)long_val, bytes, n, little_endian, is_signed);
    Py_DECREF(long_val);

    if (res == -1 && !PyErr_Occurred()) {
        PyErr_SetString(PyExc_OverflowError, "int too big to convert");
    }
    return res;
#endif
}

static inline PyObject *
pc_PyLong_FromByteArray(const unsigned char *bytes, size_t n, int little_endian, int is_signed)
{
#if PY_VERSION_HEX >= 0x030D0000
    int flags = (little_endian ? Py_ASNATIVEBYTES_LITTLE_ENDIAN : Py_ASNATIVEBYTES_BIG_ENDIAN);
    if (!is_signed) flags |= Py_ASNATIVEBYTES_UNSIGNED_BUFFER;
    return PyLong_FromNativeBytes(bytes, n, flags);
#else
    extern PyObject *_PyLong_FromByteArray(const unsigned char *bytes, size_t n, int little_endian, int is_signed);
    return _PyLong_FromByteArray(bytes, n, little_endian, is_signed);
#endif
}

/**
 * Metadata for a fixed-position field within a ProtoClass.
 * Used by getter functions to locate and interpret field data.
 */
typedef struct {
    Py_ssize_t offset;  /* Byte offset from start of struct */
    int type_code;      /* Type identifier for the field */
    int bit_pos;        /* Bit position within byte (for bitfields) */
    int bits;           /* Number of bits (for bitfields) */
    int big_endian;     /* 1 = big endian, 0 = little endian */
    int kind;           /* TypeKind (KIND_INT, KIND_BYTES, etc) */
    int has_callback;   /* 1 = field has Python-level callbacks */
    PyObject *to_python;
    PyObject *from_python;
    PyObject *name;      /* Field name (Python string) */
    int is_metadata;    /* 1 = changes variable field layout */
} FieldInfo;

/**
 * Type categories for variable-length field items.
 */
typedef enum {
    KIND_PROTOCLASS = 0,  /* Nested ProtoClass instance */
    KIND_INT = 1,         /* Explicitly marked integer [Integer] */
    KIND_BYTES = 2,       /* Explicitly marked bytes [FixedLengthData or VariableLengthData] */
    KIND_STRING = 3,      /* Null-terminated string [NullTerminatedString] */
    KIND_UNION = 4        /* Union of typed branches */
} TypeKind;

/**
 * Type information resolved at runtime for polymorphic fields.
 * Populated by resolve_target_strategy() based on type_map lookup.
 */
typedef struct {
    TypeKind kind;        /* Type category */
    int bits;             /* Bit width for KIND_INT */
    int is_signed;        /* 1 = signed, 0 = unsigned (KIND_INT) */
    int big_endian;       /* 1 = big-endian, 0 = little-endian */
    PyObject *cls;        /* Class object (owned ref for PROTOCLASS) */
    Py_ssize_t fixed_size;/* Fixed byte size, or 0 if variable */
    struct TypeMeta_s *meta; /* C-level metadata */
    PyObject *to_python;   /* Converter to Python */
    PyObject *from_python; /* Converter from Python */
} PolyTypeInfo;

/**
 * Metadata for a variable-length field within a ProtoClass.
 * Supports lists, nested ProtoClasses, and polymorphic type_map dispatch.
 */
typedef struct VarFieldInfo_s {
    PyObject *name;           /* Field name (Python string) */
    int align;                /* Alignment requirement in bytes */
    PyObject *length_field;   /* Name of field containing length */
    Py_ssize_t length_offset; /* Offset to add to length value */
    int length_multiplier;    /* Multiplier for length value */
    PyObject *type_field;     /* Name of field for type_map lookup */
    PyObject *type_map;       /* Dict mapping type values to classes */
    PyObject *item_type;      /* Type for list items or nested class */
    int big_endian;           /* 1 = big endian, 0 = little endian */
    int is_list;              /* 1 = field is a list, 0 = single item */

    /* Pre-computed item type info (populated at class creation) */
    TypeKind item_kind;       /* Type category of item_type */
    int item_bits;            /* Bit width if item is integer */
    int item_is_signed;       /* 1 = signed integer */
    Py_ssize_t item_fixed_size; /* Fixed size or 0 */

    /* For FixedLengthData and callbacks */
    PyObject *fixed_length;   /* Fixed length (PyLong or None) */
    PyObject *to_python;      /* Callback to convert raw bytes to Python object (or NULL) */
    PyObject *from_python;    /* Callback to convert Python object to raw bytes (or NULL) */

    /* try-each support */
    struct {
        PyObject *fixed_length;
        PyObject *to_python;
        PyObject *from_python;
        PolyTypeInfo type_info;
    } *branches;
    Py_ssize_t branch_count;

    PolyTypeInfo *resolved_targets;
    PyObject **resolved_keys;
    Py_ssize_t resolved_count;

    Py_ssize_t member_offset; /* Offset to PyObject* slot on instance */
    int has_callback;   /* 1 = field has Python-level callbacks */
    int is_metadata;    /* 1 = provides a length_field or type_field for another field */
    int index;          /* Index in var_offsets for this field */

    /* Linked descriptors for dependency fields */
    PyGetSetDef *length_field_gs;
    PyGetSetDef *type_field_gs;
    /* Set when length_field is itself a variable field (a fixed field that
       follows a variable field, so its offset is only known at runtime). */
    struct VarFieldInfo_s *length_field_vf;
} VarFieldInfo;

/**
 * Container for variable field definitions on a ProtoClass type.
 */
typedef struct {
    VarFieldInfo *array;      /* Array of variable field info */
    Py_ssize_t size;          /* Number of variable fields */
    PyMemberDef *members_array; /* Python member definitions */
} VarDefs;

typedef struct {
    PyObject *name;
    PyGetSetDef *gs;
} FieldMapping;

/**
 * Entry in the lazy offset map for variable fields.
 */
typedef struct {
    Py_ssize_t offset;
    Py_ssize_t length;
    int resolved;
} VarFieldOffset;

/**
 * C-level type metadata stored on each ProtoClass subclass.
 * Contains field definitions, getset descriptors, and size info.
 * Reference counted for safe sharing.
 */
typedef struct TypeMeta_s {
    PyGetSetDef *getset;      /* Array of property descriptors */
    PyMemberDef *members;     /* Array of member descriptors */
    VarDefs *var_defs;        /* Variable field definitions */
    FieldInfo **field_infos;  /* Fixed field info pointers */
    unsigned char *template_buffer; /* Pre-populated buffer with default values */
    Py_ssize_t field_info_count; /* Number of fixed fields */
    Py_ssize_t fixed_size;    /* Total fixed size in bytes */
    PyObject *defaults;       /* Dict of default values (cached) */
    PyObject *field_map;      /* Dict mapping field names to FieldInfo capsules */
    PyObject *var_map;        /* Dict mapping field names to VarFieldInfo indices */
    FieldMapping *field_mappings; /* Array of all field mappings for fast init */
    Py_ssize_t field_mapping_count;
    int ref_count;            /* Reference count for lifecycle */
} TypeMeta;

/**
 * Instance structure for ProtoClass objects.
 * Wraps a binary buffer and provides field access via descriptors.
 */
typedef struct {
    PyObject_HEAD
    unsigned char *buf;       /* Backing buffer (malloc'd or borrowed) */
    Py_ssize_t buf_cap;       /* Allocated capacity (0 if borrowed) */
    Py_ssize_t data_len;      /* Actual data length within buf */
    Py_ssize_t _offset;       /* Start of THIS object's data within buf */
    int readonly;             /* 1 = borrowed from _buffer (copy-on-write) */
    TypeMeta *type_meta;      /* C-level shared metadata */
    VarFieldOffset *var_offsets; /* Lazily-built offset map */
    Py_ssize_t var_offsets_resolved; /* Number of fields resolved in offset map */
    PyObject *dict;           /* Instance __dict__ for overrides */
    PyObject *_buffer;        /* Original Python buffer object */
} ProtoClassObject;

typedef struct {
    PyHeapTypeObject base;
    TypeMeta *meta;
} ProtoClassMetaInstance;

static PyTypeObject *ProtoClassMeta_TypePtr = NULL;
static PyTypeObject *ProtoClass_TypePtr = NULL;


static inline TypeMeta*
_get_type_meta_safe(PyTypeObject *type);

static inline TypeMeta*
_get_type_meta(ProtoClassObject *self);


static int ProtoClass_init(ProtoClassObject *self, PyObject *args, PyObject *kwds);
static int ProtoClass_clear(ProtoClassObject *self);
static int ProtoClass_traverse(ProtoClassObject *self, visitproc visit, void *arg);
static PyObject * ProtoClass_len(ProtoClassObject *self, PyObject *noargs);
static PyObject * _deserialize_var_field(ProtoClassObject *self, VarFieldInfo *vf, unsigned char *data, Py_ssize_t vlen);
static int _pc_get_poly_info(ProtoClassObject *self, VarFieldInfo *info, PolyTypeInfo *out);
static int _pc_resolve_var_offsets_to(ProtoClassObject *self, Py_ssize_t index, int strict);
static Py_ssize_t _pc_get_instance_length(ProtoClassObject *self);
static int _pc_is_protoclass(PyObject *obj);
static int _init_obj_from_view(ProtoClassObject *obj, PyTypeObject *tp, TypeMeta *meta, ProtoClassObject *parent, unsigned char *data, Py_ssize_t data_len);

// get_item_kind removed - all kinds must be passed explicitly from Python

/* Get fixed size for item_type (0 if variable) */
static inline Py_ssize_t
get_item_fixed_size(PyObject *item_type)
{
    if (!item_type || item_type == Py_None) return 0;

    PyObject *len_obj = PyObject_GetAttrString(item_type, "length");
    if (len_obj) {
        if (len_obj != Py_None) {
            Py_ssize_t length = PyLong_AsSsize_t(len_obj);
            Py_DECREF(len_obj);
            return length;
        }
        Py_DECREF(len_obj);
    }
    PyErr_Clear();

    if (PyObject_HasAttrString(item_type, "bits")) {
        PyObject *bits_obj = PyObject_GetAttrString(item_type, "bits");
        if (bits_obj) {
            long bits = PyLong_AsLong(bits_obj);
            Py_DECREF(bits_obj);
            return (bits + 7) / 8;
        }
    }
    PyErr_Clear();

    if (PyType_Check(item_type)) {
        TypeMeta *meta = _get_type_meta_safe((PyTypeObject*)item_type);
        if (meta) {
            return meta->fixed_size;
        }
    }
    return 0;
}

static Py_ssize_t
_pc_read_length_field(ProtoClassObject *self, VarFieldInfo *vf)
{
    /* A length field that is itself a variable field (a fixed field following
       a variable field) lives at a runtime offset. Read its storage directly:
       calling the field getter would resolve offsets strictly and fail while
       the length field has not been materialized yet, e.g. during
       construction. An absent length field reads as 0. */
    if (vf->length_field_vf) {
        VarFieldInfo *lf = vf->length_field_vf;
        if (_pc_resolve_var_offsets_to(self, lf->index, 0) < 0) return -1;
        Py_ssize_t off = self->var_offsets[lf->index].offset;
        int bits = lf->item_bits > 0 ? lf->item_bits : (int)(lf->item_fixed_size * 8);
        int nbytes = (bits + 7) / 8;
        if (off < 0 || nbytes <= 0 || off + nbytes > self->data_len) return 0;
        unsigned char *p = self->buf + self->_offset + off;
        unsigned long long v = 0;
        if (lf->big_endian) {
            for (int k = 0; k < nbytes; k++) v = (v << 8) | p[k];
        } else {
            for (int k = nbytes - 1; k >= 0; k--) v = (v << 8) | p[k];
        }
        return (Py_ssize_t)v;
    }

    if (!vf->length_field_gs || !vf->length_field_gs->get) {
        PyErr_Format(PyExc_RuntimeError, "Length field descriptor missing for field '%S'", vf->name);
        return -1;
    }
    PyObject *val = vf->length_field_gs->get((PyObject *)self, vf->length_field_gs->closure);
    if (!val) return -1;
    Py_ssize_t res = PyLong_AsSsize_t(val);
    Py_DECREF(val);
    if (res == -1 && PyErr_Occurred()) {
        return -1;
    }
    return res;
}

static int
_pc_resolve_var_offsets_to(ProtoClassObject *self, Py_ssize_t index, int strict)
{
    if (index < 0) return 0;
    if (self->var_offsets_resolved > index) return 0;

    TypeMeta *meta = self->type_meta;
    if (!meta || !meta->var_defs) return 0;

    if (!self->var_offsets) {
        self->var_offsets = PyMem_New(VarFieldOffset, meta->var_defs->size);
        if (!self->var_offsets) {
            PyErr_NoMemory();
            return -1;
        }
        memset(self->var_offsets, 0, sizeof(VarFieldOffset) * meta->var_defs->size);
    }

    VarDefs *defs = meta->var_defs;
    Py_ssize_t i = self->var_offsets_resolved;
    Py_ssize_t current_pos = 0;

    if (i > 0) {
        Py_ssize_t prev_offset = self->var_offsets[i - 1].offset;
        Py_ssize_t prev_len    = self->var_offsets[i - 1].length;
        Py_ssize_t prev_align  = defs->array[i - 1].align;
        /* Skip alignment for protoclass fields - they manage their own alignment */
        int prev_is_protoclass = (defs->array[i - 1].item_kind == 0);  /* KIND_PROTOCLASS = 0 */
        if (prev_align > 1 && prev_len > 0 && !prev_is_protoclass) {
            /* Same formula as in-loop: next = offset + rounded_up(length) */
            current_pos = prev_offset + ((prev_len + prev_align - 1) & ~(prev_align - 1));
        } else {
            current_pos = prev_offset + prev_len;
        }
    } else {
        current_pos = meta->fixed_size;
    }

    while (i <= index && i < defs->size) {
        VarFieldInfo *vf = &defs->array[i];

        Py_ssize_t length = 0;
        if (vf->length_field) {
            Py_ssize_t l_val = _pc_read_length_field(self, vf);
            if (l_val < 0) {
                return -1;
            }
            length = l_val * vf->length_multiplier + vf->length_offset;
        } else if (vf->item_kind == KIND_PROTOCLASS && vf->item_type && !vf->is_list) {
            /* Protoclass field (not a list) - parse from buffer during deserialization */
            if (strict && self->buf && self->data_len > current_pos) {
                PyTypeObject *tp = (PyTypeObject *)vf->item_type;
                TypeMeta *inner_meta = _get_type_meta_safe(tp);
                if (inner_meta) {
                    ProtoClassObject *obj = (ProtoClassObject *)tp->tp_alloc(tp, 0);
                    if (obj) {
                        Py_ssize_t available = self->data_len - current_pos;
                        if (_init_obj_from_view(obj, tp, inner_meta, self, self->buf + self->_offset + current_pos, available) >= 0) {
                            /* Use _pc_get_instance_length to get actual length from inner structure */
                            Py_ssize_t inner_len = _pc_get_instance_length(obj);
                            if (inner_len >= 0) {
                                length = inner_len;
                                /* Store in dict - this is where protoclass fields live */
                                if (!self->dict) self->dict = PyDict_New();
                                if (self->dict) PyDict_SetItem(self->dict, vf->name, (PyObject *)obj);
                            }
                        }
                        Py_DECREF(obj);
                    }
                    if (length <= 0) length = inner_meta->fixed_size > 0 ? inner_meta->fixed_size : (self->data_len - current_pos);
                } else {
                    length = self->data_len - current_pos;
                }
            } else {
                /* Construction mode - protoclass not in parent buffer */
                length = 0;
            }
        } else if (vf->item_fixed_size > 0 && !vf->is_list) {
            /* Fixed-size field that comes after a variable field */
            length = vf->item_fixed_size;
        } else {
            /* No length field -> tail field: consumes remaining bytes */
            length = self->data_len - current_pos;
        }

        if (length < 0) {
            /* If length_offset is negative (e.g. Netlink header size), and the
               length_field is 0 or uninitialized, we must clamp to 0 rather than
               erroring, especially during initialization. */
            length = 0;
        }
        /* Bounds check: field must not read past end of buffer.
           Exception: If we are not in strict mode, we allow the target field
           to be OOB because we might be in a setter that is about to grow the buffer.
           Also skip bounds check for protoclass fields in dict (they manage their own buffer). */
        if ((strict || i < index) && (current_pos + length > self->data_len)) {
            /* Check if this is a protoclass field with value in dict */
            int is_pc_in_dict = 0;
            if (vf->item_kind == KIND_PROTOCLASS && self->dict) {
                PyObject *dv = PyDict_GetItem(self->dict, vf->name);
                if (dv) is_pc_in_dict = 1;
            }
            if (!is_pc_in_dict && !vf->is_metadata) {
                PyErr_Format(PyExc_ValueError,
                    "Buffer too small: field %zd at offset %zd needs %zd bytes, only %zd available",
                    i, current_pos, length, self->data_len - current_pos);
                return -1;
            }
        }

        self->var_offsets[i].offset = current_pos;
        self->var_offsets[i].length = length;
        self->var_offsets[i].resolved = 1;

        current_pos += length;

        /* Post-field alignment: advance by the padded length.
           Serializer pads the data to the next multiple of align, so the next
           field starts at: offset + ((length + align - 1) & ~(align - 1))
           
           NOTE: Skip alignment for protoclass fields - they manage their own alignment
           and are stored externally (not in parent buffer). */
        if (vf->align > 1 && length > 0 && vf->item_kind != 0) {
            Py_ssize_t padded = (self->var_offsets[i].offset +
                                 ((length + vf->align - 1) & ~(vf->align - 1)));
            current_pos = padded;
        }

        i++;
    }
    self->var_offsets_resolved = i;
    return 0;
}

static int
_pc_is_protoclass(PyObject *obj)
{
    if (!obj || !ProtoClass_TypePtr) return 0;
    return PyObject_TypeCheck(obj, ProtoClass_TypePtr);
}

static PyObject *
_pc_get_field_value(ProtoClassObject *self, VarFieldInfo *vf, Py_ssize_t index)
{
    PyObject *val = NULL;
    if (self->dict) {
        val = PyDict_GetItem(self->dict, vf->name);
        if (val) {
            Py_INCREF(val);
            return val;
        }
    }

    if (_pc_resolve_var_offsets_to(self, index, 1) < 0) return NULL;

    unsigned char *data = self->buf + self->_offset + self->var_offsets[index].offset;
    Py_ssize_t vlen = self->var_offsets[index].length;

    val = _deserialize_var_field(self, vf, data, vlen);
    if (!val) return NULL;

    /* If this is a variable-length protoclass, update var_offsets with actual length */
    if (_pc_is_protoclass(val)) {
        ProtoClassObject *obj = (ProtoClassObject *)val;
        if (self->var_offsets[index].length != obj->data_len) {
            self->var_offsets[index].length = obj->data_len;
            /* Invalidate resolved state for subsequent fields */
            if (index < self->var_offsets_resolved - 1) {
                self->var_offsets_resolved = index + 1;
            }
        }
    }

    if (_pc_is_protoclass(val) || PyList_Check(val)) {
        if (!self->dict) self->dict = PyDict_New();
        if (self->dict) {
            PyDict_SetItem(self->dict, vf->name, val);
        }
    }
    return val;
}

static unsigned char *_pc_serialize_data(ProtoClassObject *self, Py_ssize_t *out_len);
static PyObject *_pc_get_bytes(PyObject *obj);

/**
 * Store a length value at ptr with the given width and byte order.
 */
static void
_pc_store_length(unsigned char *ptr, int bits, int big_endian, long val)
{
    if (bits == 8) {
        *ptr = (uint8_t)val;
    } else if (bits == 16) {
        uint16_t v = (uint16_t)val;
        if (big_endian) v = __builtin_bswap16(v);
        *(uint16_t *)ptr = v;
    } else if (bits == 32) {
        uint32_t v = (uint32_t)val;
        if (big_endian) v = __builtin_bswap32(v);
        *(uint32_t *)ptr = v;
    } else if (bits == 64) {
        uint64_t v = (uint64_t)val;
        if (big_endian) v = __builtin_bswap64(v);
        *(uint64_t *)ptr = v;
    }
}

/**
 * Refresh a length_field in a buffer.
 *
 * A length_field is usually a fixed field, but when it follows a variable
 * field the metaclass promotes it to a variable field whose storage offset is
 * only known at runtime. The caller supplies that offset as variable_offset
 * (self->var_offsets for the live buffer, or the serialization output offsets
 * for a serialized buffer).
 */
static void
_pc_pack_length(unsigned char *buf, Py_ssize_t variable_offset, VarFieldInfo *vf, Py_ssize_t length)
{
    if (!vf->length_field) return;
    long val = (length - vf->length_offset) / vf->length_multiplier;

    if (vf->length_field_vf) {
        VarFieldInfo *lf = vf->length_field_vf;
        int bits = lf->item_bits > 0 ? lf->item_bits : (int)(lf->item_fixed_size * 8);
        _pc_store_length(buf + variable_offset, bits, lf->big_endian, val);
        return;
    }

    if (!vf->length_field_gs || !vf->length_field_gs->set) return;
    FieldInfo *info = (FieldInfo *)vf->length_field_gs->closure;
    if (!info) return;
    int bits = info->bits ? info->bits : (abs(info->type_code) * 8);
    _pc_store_length(buf + info->offset, bits, info->big_endian, val);
}

/**
 * Promote a read-only (borrowed) buffer to a private, mutable malloc'd buffer.
 */
static int
_pc_promote_to_writable(ProtoClassObject *self)
{
    if (!self->readonly) return 0;

    unsigned char *new_buf = (unsigned char *)malloc(self->data_len);
    if (!new_buf) {
        PyErr_NoMemory();
        return -1;
    }
    memcpy(new_buf, self->buf + self->_offset, self->data_len);
    self->buf = new_buf;
    self->buf_cap = self->data_len;
    self->_offset = 0;
    self->readonly = 0;
    return 0;
}

/**
 * Shift data in the buffer to accommodate a size change for a variable field.
 */
static int
_pc_shift_buffer(ProtoClassObject *self, Py_ssize_t move_at, Py_ssize_t diff, Py_ssize_t field_idx)
{
    if (diff == 0) return 0;

    Py_ssize_t new_data_len = self->data_len + diff;
    if (diff > 0 && new_data_len > self->buf_cap) {
        Py_ssize_t new_cap = (new_data_len > 128) ? new_data_len * 2 : 128;
        unsigned char *new_buf = (unsigned char *)realloc(self->buf, new_cap);
        if (!new_buf) {
            PyErr_NoMemory();
            return -1;
        }
        memset(new_buf + self->buf_cap, 0, new_cap - self->buf_cap);
        self->buf = new_buf;
        self->buf_cap = new_cap;
    }

    if (move_at < self->data_len) {
        memmove(self->buf + move_at + diff, self->buf + move_at, self->data_len - move_at);
    }
    self->data_len = new_data_len;

    if (self->var_offsets) {
        for (Py_ssize_t i = field_idx + 1; i < self->var_offsets_resolved; i++) {
            if (self->var_offsets[i].resolved) {
                self->var_offsets[i].offset += diff;
            }
        }
    }
    return 0;
}

/**
 * Resolve type metadata for a polymorphic field.
 */
static int
_pc_get_poly_info(ProtoClassObject *self, VarFieldInfo *info, PolyTypeInfo *out)
{
    out->kind = 0;
    out->cls = NULL;
    out->meta = NULL;

    if (!info->type_field || info->type_field == Py_None) {
        out->kind = info->item_kind;
        out->bits = info->item_bits;
        out->is_signed = info->item_is_signed;
        out->fixed_size = info->item_fixed_size;
        out->cls = info->item_type;
        Py_XINCREF(out->cls);
        out->to_python = info->to_python;
        Py_XINCREF(out->to_python);
        out->from_python = info->from_python;
        Py_XINCREF(out->from_python);
        if (out->cls && ProtoClass_TypePtr && PyType_Check(out->cls) && PyType_IsSubtype((PyTypeObject *)out->cls, ProtoClass_TypePtr)) {
            out->meta = _get_type_meta_safe((PyTypeObject *)out->cls);
        }
        return 0;
    }

    PyObject *t_val = NULL;
    if (info->type_field_gs && info->type_field_gs->get) {
        t_val = info->type_field_gs->get((PyObject *)self, info->type_field_gs->closure);
    } else {
        t_val = PyObject_GetAttr((PyObject*)self, info->type_field);
    }

    if (!t_val) {
        PyErr_Clear();
        return -1;
    }

    int is_long = PyLong_Check(t_val);
    long long_val = is_long ? PyLong_AsLong(t_val) : 0;
    if (is_long) {
        long_val &= ~(0x8000 | 0x4000);
    }

    for (Py_ssize_t i = 0; i < info->resolved_count; i++) {
        int match = 0;
        if (is_long && PyLong_Check(info->resolved_keys[i])) {
            long k_val = PyLong_AsLong(info->resolved_keys[i]);
            if ((k_val & ~(0x8000 | 0x4000)) == long_val) match = 1;
        } else {
            PyObject *cmp = PyObject_RichCompare(info->resolved_keys[i], t_val, Py_EQ);
            if (cmp) { match = (cmp == Py_True); Py_DECREF(cmp); } else PyErr_Clear();
        }

        if (match) {
            *out = info->resolved_targets[i];
            Py_XINCREF(out->cls);
            Py_XINCREF(out->to_python);
            Py_XINCREF(out->from_python);
            Py_DECREF(t_val);
            return 0;
        }
    }
    Py_DECREF(t_val);
    return -1;
}

static PyObject *
_pc_get_null_terminated_bytes(PyObject *obj)
{
    PyObject *b = _pc_get_bytes(obj);
    if (!b) return NULL;
    Py_ssize_t n = PyBytes_GET_SIZE(b);
    const char *s = PyBytes_AS_STRING(b);
    if (n > 0 && s[n-1] == 0) return b;
    PyObject *res = PyBytes_FromStringAndSize(NULL, n + 1);
    char *rs = PyBytes_AS_STRING(res);
    memcpy(rs, s, n);
    rs[n] = 0;
    Py_DECREF(b);
    return res;
}


/**
 * Convert a Python list of base types to a concatenated PyBytes object for write-through.
 * Includes alignment padding between items.
 */
static PyObject *
_pc_convert_list_to_bytes(ProtoClassObject *self, PyObject *list, VarFieldInfo *vf, PolyTypeInfo *info)
{
    Py_ssize_t size = PyList_GET_SIZE(list);
    if (size == 0) return PyBytes_FromStringAndSize("", 0);

    Py_ssize_t cap = 256;
    Py_ssize_t total_len = 0;
    unsigned char *buf = (unsigned char *)malloc(cap);
    if (!buf) return PyErr_NoMemory();

    for (Py_ssize_t i = 0; i < size; i++) {
        PyObject *item = PyList_GET_ITEM(list, i);
        PyObject *bval = NULL;

        /* Nested ProtoClasses in a list are NOT packed into the buffer by the setter.
           They are handled by dict storage and interpolated serialization. */
        if (_pc_is_protoclass(item)) {
            free(buf);
            PyErr_SetString(PyExc_TypeError, "Lists of ProtoClasses must be handled via dict storage, not write-through.");
            return NULL;
        }

        switch (info->kind) {
            case KIND_INT: {
                Py_ssize_t n = (info->bits + 7) / 8;
                bval = PyBytes_FromStringAndSize(NULL, n);
                if (bval) {
                    if (pc_PyLong_AsByteArray(item, (unsigned char *)PyBytes_AS_STRING(bval), n, !vf->big_endian, info->is_signed) < 0) {
                        Py_DECREF(bval);
                        bval = NULL;
                    }
                }
                break;
            }
            case KIND_STRING:
                bval = _pc_get_null_terminated_bytes(item);
                break;
            case KIND_BYTES:
            default:
                if (info->from_python && info->from_python != Py_None) {
                    bval = PyObject_CallOneArg(info->from_python, item);
                } else {
                    bval = _pc_get_bytes(item);
                }
                break;
        }

        if (!bval) {
            free(buf);
            return NULL;
        }

        Py_ssize_t ilen = PyBytes_GET_SIZE(bval);
        Py_ssize_t pad = 0;
        if (vf->align > 1) {
            pad = (vf->align - (ilen % vf->align)) % vf->align;
        }

        if (total_len + ilen + pad > cap) {
            cap = (total_len + ilen + pad) * 2;
            unsigned char *new_buf = (unsigned char *)realloc(buf, cap);
            if (!new_buf) {
                Py_DECREF(bval);
                free(buf);
                return PyErr_NoMemory();
            }
            buf = new_buf;
        }

        memcpy(buf + total_len, PyBytes_AS_STRING(bval), ilen);
        total_len += ilen;
        Py_DECREF(bval);

        if (pad > 0) {
            memset(buf + total_len, 0, pad);
            total_len += pad;
        }
    }

    PyObject *res = PyBytes_FromStringAndSize((char *)buf, total_len);
    free(buf);
    return res;
}

/**
 * Convert a single Python object to packed bytes based on pre-resolved metadata.
 */
static PyObject *
_pc_convert_to_bytes(ProtoClassObject *self, PyObject *obj, VarFieldInfo *vf, PolyTypeInfo *info)
{
    if (PyList_Check(obj)) return _pc_convert_list_to_bytes(self, obj, vf, info);

    PyObject *res = NULL;
    switch (info->kind) {
        case KIND_INT: {
            Py_ssize_t n = (info->bits + 7) / 8;
            /* If it's a tail-field with no specified bits, it might be auto-length */
            if (n == 0 && PyLong_Check(obj)) {
                unsigned long v = PyLong_AsUnsignedLongMask(obj);
                n = (v > 0xFFFFFFFF) ? 8 : (v > 0xFFFF) ? 4 : (v > 0xFF) ? 2 : 1;
            }
            res = PyBytes_FromStringAndSize(NULL, n);
            if (res) {
                if (pc_PyLong_AsByteArray(obj, (unsigned char *)PyBytes_AS_STRING(res), n, !vf->big_endian, info->is_signed) < 0) {
                    Py_DECREF(res);
                    res = NULL;
                }
            }
            break;
        }

        case KIND_STRING:
            res = _pc_get_null_terminated_bytes(obj);
            break;

        case KIND_BYTES:
        default:
            if (info->from_python && info->from_python != Py_None) {
                res = PyObject_CallOneArg(info->from_python, obj);
            } else {
                res = _pc_get_bytes(obj);
            }
            break;
    }

    if (res && !PyBytes_CheckExact(res) && !PyBytes_Check(res)) {
        PyObject *b_res = PyObject_Bytes(res);
        Py_DECREF(res);
        res = b_res;
    }

    return res;
}

/* Get bits for integer item_type */
static inline int
get_item_bits(PyObject *item_type)
{
    if (!item_type) return 0;
    PyObject *bits_obj = PyObject_GetAttrString(item_type, "bits");
    if (bits_obj) {
        int bits = (int)PyLong_AsLong(bits_obj);
        Py_DECREF(bits_obj);
        return bits;
    }
    PyErr_Clear();
    return 0;
}

/* Get signed for integer item_type */
static inline int
get_item_is_signed(PyObject *item_type)
{
    if (!item_type) return 0;
    PyObject *signed_obj = PyObject_GetAttrString(item_type, "signed");
    if (signed_obj) {
        int is_signed = PyObject_IsTrue(signed_obj);
        Py_DECREF(signed_obj);
        return is_signed;
    }
    PyErr_Clear();
    return 0;
}

static void
VarFieldInfo_free(VarFieldInfo *info)
{
    Py_XDECREF(info->name);
    Py_XDECREF(info->length_field);
    Py_XDECREF(info->type_field);
    Py_XDECREF(info->type_map);
    Py_XDECREF(info->item_type);
    Py_XDECREF(info->fixed_length);
    Py_XDECREF(info->to_python);
    Py_XDECREF(info->from_python);
    if (info->branches) {
        for (Py_ssize_t i = 0; i < info->branch_count; i++) {
            Py_XDECREF(info->branches[i].fixed_length);
            Py_XDECREF(info->branches[i].to_python);
            Py_XDECREF(info->branches[i].from_python);
            Py_XDECREF(info->branches[i].type_info.cls);
            Py_XDECREF(info->branches[i].type_info.to_python);
            Py_XDECREF(info->branches[i].type_info.from_python);
        }
        PyMem_Free(info->branches);
    }
    if (info->resolved_targets) {
        for (Py_ssize_t i = 0; i < info->resolved_count; i++) {
            Py_XDECREF(info->resolved_targets[i].cls);
            Py_XDECREF(info->resolved_targets[i].to_python);
            Py_XDECREF(info->resolved_targets[i].from_python);
        }
        PyMem_Free(info->resolved_targets);
    }
    if (info->resolved_keys) {
        for (Py_ssize_t i = 0; i < info->resolved_count; i++) {
            Py_XDECREF(info->resolved_keys[i]);
        }
        PyMem_Free(info->resolved_keys);
    }

}

static TypeMeta *
TypeMeta_alloc(void)
{
    TypeMeta *meta = PyMem_Calloc(1, sizeof(TypeMeta));
    if (meta) {
        meta->ref_count = 1;
        meta->defaults = NULL;
        meta->field_map = PyDict_New();
        meta->var_map = PyDict_New();
    }
    return meta;
}

static void
TypeMeta_incref(TypeMeta *meta)
{
    if (meta) meta->ref_count++;
}

static void
TypeMeta_free(TypeMeta *meta);

static void
TypeMeta_decref(TypeMeta *meta);

static void
TypeMeta_capsule_destructor(PyObject *capsule)
{
    TypeMeta *meta = (TypeMeta *)PyCapsule_GetPointer(capsule, "protoclass.type_meta");
    if (meta) {
        TypeMeta_decref(meta);
    }
}

static void
TypeMeta_decref(TypeMeta *meta)
{
    if (meta && --meta->ref_count == 0) {
        TypeMeta_free(meta);
    }
}

static void
TypeMeta_free(TypeMeta *meta)
{
    if (meta->getset) {
        for (Py_ssize_t i = 0; meta->getset[i].name; i++) {
            free((char*)meta->getset[i].name);
        }
        PyMem_Free(meta->getset);
    }
    if (meta->members) {
        for (Py_ssize_t i = 0; meta->members[i].name; i++) {
            free((char*)meta->members[i].name);
        }
        PyMem_Free(meta->members);
    }
    if (meta->field_infos) {
        for (Py_ssize_t i = 0; i < meta->field_info_count; i++) {
            FieldInfo *fi = meta->field_infos[i];
            if (fi) {
                Py_XDECREF(fi->to_python);
                Py_XDECREF(fi->from_python);
                Py_XDECREF(fi->name);
                PyMem_Free(fi);
            }
        }
        PyMem_Free(meta->field_infos);
    }
    if (meta->var_defs) {
        for (Py_ssize_t i = 0; i < meta->var_defs->size; i++) {
            VarFieldInfo_free(&meta->var_defs->array[i]);
        }
        PyMem_Free(meta->var_defs->array);
        PyMem_Free(meta->var_defs);
    }
    if (meta->field_mappings) {
        for (Py_ssize_t i = 0; i < meta->field_mapping_count; i++) {
            Py_XDECREF(meta->field_mappings[i].name);
        }
      if (meta->field_mappings) PyMem_Free(meta->field_mappings);
    }
    if (meta->template_buffer) PyMem_Free(meta->template_buffer);
    Py_XDECREF(meta->defaults);
    Py_XDECREF(meta->field_map);
    Py_XDECREF(meta->var_map);
    PyMem_Free(meta);
}



static void
init_interned_keys(void)
{
    if (keys.fixed_size) return;
    keys.fixed_size = PyUnicode_InternFromString("_fixed_size");
    keys.var_defs = PyUnicode_InternFromString("_c_var_defs");
    keys.from_buffer = PyUnicode_InternFromString("from_buffer");
    keys.packed = PyUnicode_InternFromString("packed");
    keys.to_bytes = PyUnicode_InternFromString("to_bytes");
}


static inline TypeMeta*
_get_type_meta_safe(PyTypeObject *type)
{
    if (type && ProtoClassMeta_TypePtr && Py_TYPE(type) == (PyTypeObject *)ProtoClassMeta_TypePtr) {
        return ((ProtoClassMetaInstance *)type)->meta;
    }
    return NULL;
}

static inline TypeMeta*
_get_type_meta(ProtoClassObject *self)
{
    if (self->type_meta) {
        return self->type_meta;
    }
    TypeMeta *meta = _get_type_meta_safe(Py_TYPE(self));
    if (meta) {
         self->type_meta = meta;
         TypeMeta_incref(meta);
    }
    return meta;
}



static void
ProtoClassMeta_dealloc(PyObject *self)
{
    PyObject_GC_UnTrack(self);
    ProtoClassMetaInstance *mi = (ProtoClassMetaInstance *)self;
    if (mi->meta) {
        TypeMeta_decref(mi->meta);
        mi->meta = NULL;
    }
    PyType_Type.tp_dealloc(self);
}

static int
ProtoClassMeta_traverse(PyObject *self, visitproc visit, void *arg)
{
    /* Delegate entirely to PyType_Type.tp_traverse. TypeMeta's Python objects
       (defaults, field_map, var_map) are plain dicts/values that do not form
       reference cycles back to this type, so they don't need to be visited
       by our GC traversal. The type's tp_dict, bases, and subclasses are
       handled by PyType_Type.tp_traverse. */
    return PyType_Type.tp_traverse(self, visit, arg);
}

static int
ProtoClassMeta_clear(PyObject *self)
{
    /* TypeMeta is managed by mi->meta (C refcount) and the capsule in tp_dict
       (Python refcount). GC will call tp_dealloc after tp_clear, and
       PyType_Type.tp_dealloc internally handles clearing tp_dict etc.
       We must NOT call PyType_Type.tp_clear here — that clears tp_dict prematurely,
       then tp_dealloc tries to free it again, causing a crash. Just return 0
       to satisfy GC's requirement that tp_clear exist. */
    return 0;
}

static PyObject *
ProtoClassMeta_get_type_meta(PyObject *self, void *closure)
{
    TypeMeta *meta = _get_type_meta_safe((PyTypeObject *)self);
    if (!meta) Py_RETURN_NONE;

    PyObject *capsule = PyCapsule_New(meta, "protoclass.type_meta", TypeMeta_capsule_destructor);
    if (capsule) {
        TypeMeta_incref(meta);
    }
    return capsule;
}

static int
ProtoClass_populate_type_from_meta(PyTypeObject *type, TypeMeta *meta);

static int
ProtoClassMeta_set_type_meta(PyObject *self, PyObject *value, void *closure)
{
    ProtoClassMetaInstance *mi = (ProtoClassMetaInstance *)self;

    if (value == Py_None) {
        if (mi->meta) {
            TypeMeta_decref(mi->meta);
            mi->meta = NULL;
        }
    } else if (PyCapsule_CheckExact(value)) {
        TypeMeta *new_meta = (TypeMeta *)PyCapsule_GetPointer(value, "protoclass.type_meta");
        if (new_meta) {
            if (mi->meta) {
                TypeMeta_decref(mi->meta);
            }
            mi->meta = new_meta;
            TypeMeta_incref(new_meta);
            // Automatically populate descriptors if we have meta
            if (ProtoClass_populate_type_from_meta((PyTypeObject *)self, new_meta) < 0) {
                return -1;
            }
        }
    } else {
        PyErr_SetString(PyExc_TypeError, "Expected TypeMeta capsule or None");
        return -1;
    }
    return 0;
}
static PyObject *
ProtoClassMeta_call(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    // Fast path instantiation
    ProtoClassObject *self = (ProtoClassObject *)type->tp_alloc(type, 0);
    if (!self) return NULL;

    if (ProtoClass_init(self, args, kwds) < 0) {
        Py_DECREF(self);
        return NULL;
    }

    return (PyObject *)self;
}

static PyGetSetDef ProtoClassMeta_getset[] = {
    {"_c_type_meta", (getter)ProtoClassMeta_get_type_meta, (setter)ProtoClassMeta_set_type_meta, "C-level metadata pointer", NULL},
    {NULL}
};

static PyMemberDef ProtoClassMeta_members[] = {
    {"_c_meta_ptr", T_PYSSIZET, offsetof(ProtoClassMetaInstance, meta), READONLY, "C-level metadata pointer"},
    {NULL}
};

static PyType_Slot ProtoClassMeta_slots[] = {
    {Py_tp_dealloc, ProtoClassMeta_dealloc},
    {Py_tp_traverse, ProtoClassMeta_traverse},
    {Py_tp_clear, ProtoClassMeta_clear},
    {Py_tp_getset, ProtoClassMeta_getset},
    {Py_tp_call, (void *)ProtoClassMeta_call},
    {Py_tp_members, ProtoClassMeta_members},
    {0, NULL}
};

static PyType_Spec ProtoClassMeta_spec = {
    .name = "protoclass._cprotoclass.ProtoClassMeta",
    .basicsize = sizeof(ProtoClassMetaInstance),
    .flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_TYPE_SUBCLASS | Py_TPFLAGS_HAVE_GC | Py_TPFLAGS_BASETYPE,
    .slots = ProtoClassMeta_slots,
};

static void
ProtoClass_dealloc(ProtoClassObject *self)
{
    PyObject_GC_UnTrack(self);
    ProtoClass_clear(self);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static int
ProtoClass_traverse(ProtoClassObject *self, visitproc visit, void *arg)
{
    Py_VISIT(self->_buffer);
    /* Since we have tp_dictoffset, the dictionary is automatically visited
       by the standard machinery. Double-visiting it can cause crashes in GC. */
    return 0;
}

static int
ProtoClass_clear(ProtoClassObject *self)
{
    Py_CLEAR(self->_buffer);
    Py_CLEAR(self->dict);

    if (self->buf_cap > 0 && self->buf) {
        free(self->buf);
        self->buf = NULL;
    }
    self->buf_cap = 0;
    self->data_len = 0;

    if (self->var_offsets) {
        PyMem_Free(self->var_offsets);
        self->var_offsets = NULL;
        self->var_offsets_resolved = 0;
    }
    if (self->type_meta) {
        TypeMeta_decref(self->type_meta);
        self->type_meta = NULL;
    }
    return 0;
}


static int
_pc_ensure_mutable(ProtoClassObject *self)
{
    if (!self->readonly) return 0;

    unsigned char *new_buf = (unsigned char *)malloc(self->data_len);
    if (!new_buf) {
        PyErr_NoMemory();
        return -1;
    }
    memcpy(new_buf, self->buf + self->_offset, self->data_len);

    self->buf = new_buf;
    self->buf_cap = self->data_len;
    self->_offset = 0;
    self->readonly = 0;

    Py_CLEAR(self->_buffer);
    return 0;
}

/**
 * Macro to verify buffer bounds and resolve the data pointer.
 *
 * This macro ensures that the buffer pointer is initialized and that the
 * requested memory access (base offset + field offset + size) is within
 * the buffer's bounds. If the check fails, it sets a Python exception
 * and returns NULL from the current function.
 *
 * @param OBJ The ProtoClassObject pointer.
 * @param INFO The field info structure containing the relative offset.
 * @param SIZE The size of the data to access.
 */
#define CHECK_BOUNDS(OBJ, INFO, SIZE) \
    if (INFO->offset + SIZE > OBJ->data_len) { \
        Py_RETURN_NONE; \
    } \
    unsigned char *data = OBJ->buf + OBJ->_offset + INFO->offset;

/**
 * Get an 8-bit unsigned integer from a ProtoClassObject.
 *
 * @param self The ProtoClassObject instance.
 * @param closure The field info structure containing the relative offset.
 * @return A Python long object representing the unsigned integer value.
 */
static PyObject *getter_u8(ProtoClassObject *self, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_BOUNDS(self, info, 1);
    return PyLong_FromUnsignedLong(*data);
}

/**
 * Get an 8-bit signed integer from a ProtoClassObject.
 *
 * @param self The ProtoClassObject instance.
 * @param closure The field info structure containing the relative offset.
 * @return A Python long object representing the signed integer value.
 */
static PyObject *getter_i8(ProtoClassObject *self, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_BOUNDS(self, info, 1);
    return PyLong_FromLong(*(signed char*)data);
}

/**
 * Macro to define a standard getter function for fixed-size integer types.
 *
 * @param NAME The name of the function to define.
 * @param TYPE The C type of the data.
 * @param BYTES The size of the data in bytes.
 * @param CONV A conversion macro/function (e.g., for endianness) or empty.
 * @param PYFROMFUNC The Python C API function to convert the C value to a Python object.
 */
#define DEFINE_STD_GETTER(NAME, TYPE, BYTES, CONV, PYFROMFUNC) \
static PyObject * NAME(ProtoClassObject *self, void *closure) { \
    FieldInfo *info = (FieldInfo*)closure; \
    CHECK_BOUNDS(self, info, BYTES); \
    TYPE val = CONV(*(TYPE*)data); \
    return PYFROMFUNC(val); \
}

DEFINE_STD_GETTER(getter_u16_le, uint16_t, 2, , PyLong_FromUnsignedLong)
DEFINE_STD_GETTER(getter_u16_be, uint16_t, 2, __builtin_bswap16, PyLong_FromUnsignedLong)
DEFINE_STD_GETTER(getter_i16_le, int16_t, 2, , PyLong_FromLong)
DEFINE_STD_GETTER(getter_i16_be, int16_t, 2, (int16_t)__builtin_bswap16, PyLong_FromLong)

DEFINE_STD_GETTER(getter_u32_le, uint32_t, 4, , PyLong_FromUnsignedLong)
DEFINE_STD_GETTER(getter_u32_be, uint32_t, 4, __builtin_bswap32, PyLong_FromUnsignedLong)
DEFINE_STD_GETTER(getter_i32_le, int32_t, 4, , PyLong_FromLong)
DEFINE_STD_GETTER(getter_i32_be, int32_t, 4, (int32_t)__builtin_bswap32, PyLong_FromLong)

DEFINE_STD_GETTER(getter_u64_le, uint64_t, 8, , PyLong_FromUnsignedLongLong)
DEFINE_STD_GETTER(getter_u64_be, uint64_t, 8, __builtin_bswap64, PyLong_FromUnsignedLongLong)
DEFINE_STD_GETTER(getter_i64_le, int64_t, 8, , PyLong_FromLongLong)
DEFINE_STD_GETTER(getter_i64_be, int64_t, 8, (int64_t)__builtin_bswap64, PyLong_FromLongLong)

static PyObject *getter_u128_le(ProtoClassObject *self, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_BOUNDS(self, info, 16);
    return pc_PyLong_FromByteArray(data, 16, 1, 0);
}

static PyObject *getter_u128_be(ProtoClassObject *self, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_BOUNDS(self, info, 16);
    return pc_PyLong_FromByteArray(data, 16, 0, 0);
}

static PyObject *getter_i128_le(ProtoClassObject *self, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_BOUNDS(self, info, 16);
    return pc_PyLong_FromByteArray(data, 16, 1, 1);
}

static PyObject *getter_i128_be(ProtoClassObject *self, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_BOUNDS(self, info, 16);
    return pc_PyLong_FromByteArray(data, 16, 0, 1);
}



/**
 * Get a 128-bit unsigned integer from a ProtoClassObject.
 *
 * @param self The ProtoClassObject instance.
 * @param closure The field info structure containing the relative offset.
 * @return A Python long object representing the unsigned integer value.
 */



/**
 * Calculate the serialized length of a variable field value.
 *
 * @param val The Python value to measure (list, ProtoClass, bytes, etc.)
 * @param vf The VarFieldInfo describing the field
 * @return The length in bytes the value would occupy when serialized
 */
static PyObject*
_pc_get_bytes(PyObject *obj)
{
    if (!obj || obj == Py_None) return NULL;
    if (PyBytes_Check(obj)) {
        Py_INCREF(obj);
        return obj;
    }
    if (PyUnicode_Check(obj)) {
        return PyUnicode_AsUTF8String(obj);
    }
    if (PyObject_HasAttr(obj, keys.packed)) {
        return PyObject_GetAttr(obj, keys.packed);
    }
    if (!PyLong_Check(obj) && PyObject_HasAttr(obj, keys.to_bytes)) {
         return PyObject_CallMethodObjArgs(obj, keys.to_bytes, NULL);
    }
    return PyObject_Bytes(obj);
}



static int
_init_obj_from_view(ProtoClassObject *obj, PyTypeObject *tp, TypeMeta *tp_meta, ProtoClassObject *parent, unsigned char *data, Py_ssize_t vlen)
{
    if (parent) {
        obj->buf = parent->buf;
        obj->_offset = data - parent->buf;
        if (parent->_buffer) {
            obj->_buffer = parent->_buffer;
        } else {
            // Parent owns its own buffer, we must keep parent alive
            obj->_buffer = (PyObject *)parent;
        }
        Py_XINCREF(obj->_buffer);
    } else {
        // For top-level objects, buf is already allocated or set
        obj->_offset = 0;
    }
    obj->buf_cap = 0; // borrowed if parent, or already allocated
    obj->data_len = vlen;
    obj->readonly = parent ? parent->readonly : 0;

    obj->type_meta = tp_meta;
    if (tp_meta) {
        if (tp_meta->fixed_size > vlen && vlen >= 0) {
            PyErr_Format(PyExc_ValueError, "Buffer too small for %s: expected %zd, got %zd", tp->tp_name, tp_meta->fixed_size, vlen);
            return -1;
        }
        TypeMeta_incref(tp_meta);
    }

    obj->var_offsets = NULL;
    obj->var_offsets_resolved = 0;
    obj->dict = NULL;
    return 0;
}

static PyObject * _deserialize_var_field(ProtoClassObject *self, VarFieldInfo *vf, unsigned char *data, Py_ssize_t vlen);


/**
 * Deserialize a list of items from binary data.
 *
 * Creates Python list from binary data according to item type
 * (integers, IP addresses, or nested ProtoClass instances).
 *
 * @param self The parent ProtoClass instance
 * @param vf   VarFieldInfo describing the list field
 * @param data Pointer to raw binary data
 * @param vlen Total length of data in bytes
 * @return New Python list, or NULL on error
 */
static PyObject *
deserialize_list(ProtoClassObject *self, VarFieldInfo *vf, unsigned char *data, Py_ssize_t vlen)
{
    PyObject *list = PyList_New(0);
    if (!list) return NULL;

    TypeKind kind = vf->item_kind;
    int bits = vf->item_bits;
    int is_signed = vf->item_is_signed;
    Py_ssize_t fixed_size = vf->item_fixed_size;

    Py_ssize_t pos = 0;
    while (pos < vlen) {
        unsigned char *item_data = data + pos;
        PyObject *item = NULL;
        Py_ssize_t itlen = 0;

        switch (kind) {
            case KIND_INT:
                itlen = (bits + 7) / 8;
                if (pos + itlen > vlen) goto end_loop;
                item = pc_PyLong_FromByteArray(item_data, itlen, !vf->big_endian, is_signed);
                break;
            case KIND_PROTOCLASS:
                {
                    PyTypeObject *tp = (PyTypeObject *)vf->item_type;
                    if (fixed_size > 0 && pos + fixed_size > vlen) {
                        Py_DECREF(list);
                        PyErr_SetString(PyExc_ValueError, "Buffer too small for list item");
                        return NULL;
                    }

                    ProtoClassObject *obj = (ProtoClassObject *)tp->tp_alloc(tp, 0);
                    if (obj) {
                        if (_init_obj_from_view(obj, tp, _get_type_meta_safe(tp), self, item_data, (vlen - pos)) < 0) {
                            Py_DECREF(obj);
                            Py_DECREF(list);
                            return NULL;
                        }
                        if (tp->tp_basicsize > (Py_ssize_t)sizeof(ProtoClassObject)) {
                            memset((char *)obj + sizeof(ProtoClassObject), 0, tp->tp_basicsize - sizeof(ProtoClassObject));
                        }
                        item = (PyObject *)obj;

                        /* Compute the true item length. */
                        itlen = _pc_get_instance_length(obj);
                        if (itlen < 0) {
                            Py_DECREF(obj);
                            Py_DECREF(list);
                            return NULL;
                        }

                        obj->data_len = itlen;
                        obj->var_offsets_resolved = 0;  /* Force re-resolve with correct data_len */
                    }
                }
                break;
            case KIND_STRING:
                itlen = fixed_size;
                if (itlen <= 0) { // Find null terminator
                    unsigned char *end = (unsigned char *)memchr(item_data, '\0', vlen - pos);
                    if (end) {
                        itlen = end - item_data + 1; // Include null terminator
                    } else {
                        itlen = vlen - pos; // No null terminator found, take remaining
                    }
                }
                if (pos + itlen > vlen) itlen = vlen - pos; // Ensure it doesn't go past vlen

                // Exclude null terminator from unicode string
                Py_ssize_t strlen = itlen;
                if (strlen > 0 && item_data[strlen-1] == '\0') {
                    strlen--;
                }
                item = PyUnicode_DecodeUTF8((const char*)item_data, strlen, NULL);
                break;
            default:
                itlen = fixed_size;
                if (itlen <= 0) itlen = vlen - pos;
                if (pos + itlen > vlen) itlen = vlen - pos;
                item = PyBytes_FromStringAndSize((char*)item_data, itlen);
                break;
        }

        if (item) {
            // try-each branches for list items
            if (vf->branch_count > 0) {
                for (Py_ssize_t b = 0; b < vf->branch_count; b++) {
                    if (!vf->branches[b].to_python || vf->branches[b].to_python == Py_None) continue;
                    Py_ssize_t b_len = itlen;
                    if (vf->branches[b].fixed_length && vf->branches[b].fixed_length != Py_None) {
                        b_len = PyLong_AsSsize_t(vf->branches[b].fixed_length);
                    }

                    // For list items, we might not know itlen yet if it's variable
                    // But if it's a fixed branch, it must fit in what's left
                    if (pos + b_len > vlen) continue;

                    PyObject *raw = PyBytes_FromStringAndSize((char*)item_data, b_len);
                    if (!raw) { PyErr_Clear(); continue; }
                    PyObject *res = PyObject_CallOneArg(vf->branches[b].to_python, raw);
                    Py_DECREF(raw);
                    if (res) {
                        Py_ssize_t real_len = b_len;
                        if (ProtoClass_TypePtr && PyObject_TypeCheck(res, ProtoClass_TypePtr)) {
                            real_len = _pc_get_instance_length((ProtoClassObject *)res);
                            if (real_len < 0) {
                                Py_DECREF(res);
                                Py_XDECREF(item);
                                PyErr_Clear();
                                continue;
                            }
                            ((ProtoClassObject *)res)->data_len = real_len;
                        }

                        Py_XDECREF(item);
                        item = res;
                        itlen = real_len;
                        break;
                    }
                    PyErr_Clear();
                }
            } else if (vf->to_python && vf->to_python != Py_None) {
                PyObject *converted = PyObject_CallOneArg(vf->to_python, item);
                Py_DECREF(item);
                item = converted;
            }
        }

        if (!item) {
            Py_DECREF(list);
            return NULL;
        }
        PyList_Append(list, item);
        Py_DECREF(item);

        if (vf->align > 1) {
            itlen = (itlen + vf->align - 1) & ~(vf->align - 1);
        }
        pos += itlen;
        if (itlen <= 0) break;
    }

end_loop:
    return list;
}


static Py_ssize_t
_pc_get_instance_length(ProtoClassObject *self)
{
    TypeMeta *meta = self->type_meta;
    if (!meta->var_defs || meta->var_defs->size == 0) {
        return meta->fixed_size;
    }

    Py_ssize_t last_idx = meta->var_defs->size - 1;
    VarFieldInfo *last_vf = &meta->var_defs->array[last_idx];

    /* If the last field has a length_field, the extent is well-defined. */
    if (last_vf->length_field) {
        if (_pc_resolve_var_offsets_to(self, last_idx, 1) < 0) return -1;
        Py_ssize_t payload_len = self->var_offsets[last_idx].length;
        Py_ssize_t offset = self->var_offsets[last_idx].offset;
        /* Calculate padded length of the last field */
        Py_ssize_t padded_len = payload_len;
        if (last_vf->align > 1) {
            padded_len = (payload_len + last_vf->align - 1) & ~(last_vf->align - 1);
        }
        return offset + padded_len;
    }

    /* Tail field. Find where it starts first, so it can be measured from its
       own start rather than the fixed header. */
    if (_pc_resolve_var_offsets_to(self, last_idx - 1, 1) < 0) return -1;
    Py_ssize_t prev_end = meta->fixed_size;
    if (last_idx > 0) {
        prev_end = self->var_offsets[last_idx-1].offset + self->var_offsets[last_idx-1].length;
        if (meta->var_defs->array[last_idx-1].align > 1 && self->var_offsets[last_idx-1].length > 0) {
            prev_end = (prev_end + meta->var_defs->array[last_idx-1].align - 1) & ~(meta->var_defs->array[last_idx-1].align - 1);
        }
    }

    PolyTypeInfo poly;
    memset(&poly, 0, sizeof(poly));
    Py_ssize_t field_len = 0;
    if (_pc_get_poly_info(self, last_vf, &poly) == 0) {
        if (poly.fixed_size > 0 && poly.kind != KIND_PROTOCLASS) {
            field_len = poly.fixed_size;
        } else if (poly.kind == KIND_PROTOCLASS && poly.meta) {
            /* Parse the nested object and use its own computed extent. */
            PyTypeObject *tp = (PyTypeObject *)poly.cls;
            ProtoClassObject *obj = (ProtoClassObject *)tp->tp_alloc(tp, 0);
            if (obj) {
                Py_ssize_t available = self->data_len - prev_end;
                if (_init_obj_from_view(obj, tp, poly.meta, self, self->buf + self->_offset + prev_end, available) >= 0) {
                    field_len = _pc_get_instance_length(obj);
                }
                Py_DECREF(obj);
            }
            if (field_len <= 0) {
                field_len = self->data_len - prev_end; /* Fallback to gobble */
            }
        } else if (poly.kind == KIND_STRING) {
            unsigned char *start = self->buf + self->_offset + prev_end;
            Py_ssize_t available = self->data_len - prev_end;
            unsigned char *end = (unsigned char *)memchr(start, '\0', available);
            field_len = end ? (end - start + 1) : available;
        } else {
            field_len = self->data_len - prev_end; /* Fallback to gobble */
        }
        Py_XDECREF(poly.cls); Py_XDECREF(poly.to_python); Py_XDECREF(poly.from_python);
        Py_ssize_t total = prev_end + field_len;
        if (last_vf->align > 1 && field_len > 0) {
            total = (total + last_vf->align - 1) & ~(last_vf->align - 1);
        }
        return total;
    }

    /* Full gobble fallback. */
    return self->data_len;
}

static inline int
is_matching_type(PyObject *branch_type, PyObject *target_type)
{
    if (!branch_type || !target_type) return 0;
    if (branch_type == target_type) return 1;

    // Fast path: if target is a type, use IsSubclass
    if (PyType_Check(target_type)) {
        int res = PyObject_IsSubclass(branch_type, target_type);
        if (res != -1) return res;
        PyErr_Clear();
    }

    // Check if target_type is a Union (has __args__)
    PyObject *args = PyObject_GetAttrString(target_type, "__args__");
    if (args) {
        int match = 0;
        if (PyTuple_Check(args)) {
            Py_ssize_t n = PyTuple_Size(args);
            for (Py_ssize_t i = 0; i < n; i++) {
                PyObject *arg = PyTuple_GetItem(args, i);
                if (arg == branch_type) {
                    match = 1;
                    break;
                }
                if (PyType_Check(arg)) {
                    int r = PyObject_IsSubclass(branch_type, arg);
                    if (r == 1) {
                        match = 1;
                        break;
                    }
                    if (r == -1) PyErr_Clear();
                }
            }
        }
        Py_DECREF(args);
        if (match) return 1;
    } else {
        PyErr_Clear();
    }

    return 0;
}

/**
 * Helper to deserialize a value based on a PolyTypeInfo.
 */
static PyObject *
_pc_deserialize_from_info(ProtoClassObject *self, PolyTypeInfo *target, unsigned char *data, Py_ssize_t vlen)
{
    PyObject *val = NULL;
    switch (target->kind) {
        case KIND_PROTOCLASS: {
            PyTypeObject *tp = (PyTypeObject *)target->cls;
            ProtoClassObject *obj = (ProtoClassObject *)tp->tp_alloc(tp, 0);
            if (obj) {
                if (_init_obj_from_view(obj, tp, _get_type_meta_safe(tp), self, data, vlen) < 0) {
                    Py_DECREF(obj);
                    val = NULL;
                } else {
                    if (tp->tp_basicsize > (Py_ssize_t)sizeof(ProtoClassObject)) {
                        memset((char *)obj + sizeof(ProtoClassObject), 0, tp->tp_basicsize - sizeof(ProtoClassObject));
                    }
                    val = (PyObject *)obj;
                }
            }
            break;
        }
        case KIND_INT: {
            Py_ssize_t int_len = target->bits > 0 ? (target->bits + 7) / 8 : vlen;
            if (int_len > vlen) int_len = vlen;
            val = pc_PyLong_FromByteArray(data, int_len, !target->big_endian, target->is_signed);
            break;
        }
        case KIND_STRING: {
            Py_ssize_t s_len = 0;
            while (s_len < vlen && data[s_len] != 0) s_len++;
            val = PyUnicode_DecodeUTF8((const char *)data, s_len, NULL);
            break;
        }
        case KIND_BYTES:
        default:
            val = PyBytes_FromStringAndSize((char *)data, vlen);
            break;
    }

    if (val && target->to_python && target->to_python != Py_None) {
        PyObject *converted = PyObject_CallOneArg(target->to_python, val);
        Py_DECREF(val);
        val = converted;
    }
    return val;
}

/**
 * Deserializes a variable-length field from the buffer.
 * Rule 197: Use strictly metadata-driven dispatch for KIND_UNION.
 */
static PyObject *
_deserialize_var_field(ProtoClassObject *self, VarFieldInfo *vf, unsigned char *data, Py_ssize_t vlen)
{
    if (vf->is_list) {
        return deserialize_list(self, vf, data, vlen);
    }

    PolyTypeInfo target;
    memset(&target, 0, sizeof(target));
    int has_poly = (_pc_get_poly_info(self, vf, &target) == 0);
    if (!has_poly) {
        /* If it's a Union, we MUST try branches. */
        if (vf->item_kind == KIND_UNION) {
            target.kind = KIND_UNION;
        } else if (!vf->type_map || vf->type_map == Py_None) {
            /* Fallback to raw bytes ONLY if it's not a Union and has no type_map */
            target.kind = vf->item_kind;
            target.cls = vf->item_type;
            target.to_python = vf->to_python;
            target.from_python = vf->from_python;
            target.bits = vf->item_bits;
            target.is_signed = vf->item_is_signed;
            target.fixed_size = vf->item_fixed_size;
            target.big_endian = vf->big_endian;
            Py_XINCREF(target.cls); Py_XINCREF(target.to_python); Py_XINCREF(target.from_python);
        } else {
            return PyBytes_FromStringAndSize((char *)data, vlen);
        }
    }

    if (!has_poly && target.kind == KIND_UNION) {
        PyObject *res = NULL;
        for (Py_ssize_t i = 0; i < vf->branch_count; i++) {
            Py_ssize_t b_len = vlen;
            if (vf->branches[i].fixed_length && vf->branches[i].fixed_length != Py_None) {
                b_len = PyLong_AsSsize_t(vf->branches[i].fixed_length);
                /* Rule: If a branch has a fixed length, it MUST match the available length
                   exactly for discriminator-less dispatch. */
                if (b_len != vlen) continue;
            }

            res = _pc_deserialize_from_info(self, &vf->branches[i].type_info, data, b_len);
            if (res) {
                break;
            }
            PyErr_Clear();
        }
        Py_XDECREF(target.cls); Py_XDECREF(target.to_python); Py_XDECREF(target.from_python);
        if (res) return res;
        return PyBytes_FromStringAndSize((char *)data, vlen);
    }

    PyObject *val = _pc_deserialize_from_info(self, &target, data, vlen);
    Py_XDECREF(target.cls);
    Py_XDECREF(target.to_python);
    Py_XDECREF(target.from_python);
    return val;
}

static PyObject *
ProtoClass_var_getter(ProtoClassObject *self, void *closure)
{
    VarFieldInfo *vf = (VarFieldInfo *)closure;
    PyObject *res = _pc_get_field_value(self, vf, vf->index);
    if (!res && !PyErr_Occurred()) {
        PyErr_Format(PyExc_RuntimeError, "ProtoClass_var_getter returned NULL without exception for field '%S'", vf->name);
    }
    return res;
}


static int
ProtoClass_var_setter(ProtoClassObject *self, PyObject *value, void *closure)
{
    VarFieldInfo *vf = (VarFieldInfo *)closure;
    Py_ssize_t index = vf->index;

    /* Rule 221: If protoclass instance: store in dict, skip buffer write.
       This covers nested ProtoClasses and lists of them. */
    int is_pc = _pc_is_protoclass(value);
    int is_pc_list = 0;
    if (PyList_Check(value)) {
        if (PyList_GET_SIZE(value) > 0 && _pc_is_protoclass(PyList_GET_ITEM(value, 0))) {
            is_pc_list = 1;
        }
    }

    if (is_pc || is_pc_list) {
        if (!self->dict) {
            self->dict = PyDict_New();
            if (!self->dict) return -1;
        }
        
        /* Get the new length from the protoclass instance */
        Py_ssize_t new_len = ((ProtoClassObject *)value)->data_len;
        
        /* Resolve offsets to find current position and old length */
        if (_pc_resolve_var_offsets_to(self, index, 0) < 0) {
            if (PyDict_SetItem(self->dict, vf->name, value) < 0) return -1;
            self->var_offsets_resolved = 0;
            return 0;
        }
        
        Py_ssize_t offset = self->var_offsets[index].offset;
        Py_ssize_t old_len = self->var_offsets[index].length;
        Py_ssize_t diff = new_len - old_len;
        
        /* Store in dict */
        if (PyDict_SetItem(self->dict, vf->name, value) < 0) return -1;
        
        /* If length changed, we may need to grow the buffer first */
        if (diff != 0) {
            Py_ssize_t new_total = self->data_len + diff;
            if (new_total > self->buf_cap) {
                /* Grow the buffer */
                Py_ssize_t new_cap = new_total * 2;
                unsigned char *new_buf = (unsigned char *)realloc(self->buf, new_cap);
                if (!new_buf) { PyErr_NoMemory(); return -1; }
                memset(new_buf + self->buf_cap, 0, new_cap - self->buf_cap);
                self->buf = new_buf;
                self->buf_cap = new_cap;
            }
            self->data_len = new_total;
            
            /* Shift subsequent buffer data */
            if (_pc_shift_buffer(self, offset + old_len, diff, index) < 0) return -1;
        }
        
        /* Invalidate the offset map for recalculation */
        self->var_offsets_resolved = 0;
        
        return 0;
    }

    /* Base type field (KIND_INT, KIND_STRING, KIND_BYTES).
       Rule 223: Convert value to bytes. Compute new vs old length. */
    PolyTypeInfo target;
    memset(&target, 0, sizeof(target));
    PyObject *bval = NULL;
    int has_poly = (_pc_get_poly_info(self, vf, &target) == 0);
    if (!has_poly) {
        if (vf->item_kind == KIND_UNION) {
            for (Py_ssize_t i = 0; i < vf->branch_count; i++) {
                bval = _pc_convert_to_bytes(self, value, vf, &vf->branches[i].type_info);
                if (bval) {
                    target = vf->branches[i].type_info;
                    Py_XINCREF(target.cls); Py_XINCREF(target.to_python); Py_XINCREF(target.from_python);
                    goto found;
                }
                PyErr_Clear();
            }
        }
        PyErr_Format(PyExc_TypeError, "Field '%U' could not resolve branch for write-through setter", vf->name);
        return -1;
    }

    bval = _pc_convert_to_bytes(self, value, vf, &target);
    if (!bval) {
        Py_XDECREF(target.cls); Py_XDECREF(target.to_python); Py_XDECREF(target.from_python);
        return -1;
    }

found:;
    Py_ssize_t new_len = PyBytes_GET_SIZE(bval);

    /* Rule 222: If readonly: copy-on-write promote. */
    if (self->readonly) {
        if (_pc_promote_to_writable(self) < 0) {
            Py_DECREF(bval);
            Py_XDECREF(target.cls); Py_XDECREF(target.to_python); Py_XDECREF(target.from_python);
            return -1;
        }
    }

    /* Determine current offset and calculate shift.
       We must ensure the lazy offset map is resolved up to this field.
       We use strict=0 because the target field might be OOB (buffer not grown yet). */
    if (_pc_resolve_var_offsets_to(self, index, 0) < 0) {
        Py_DECREF(bval);
        Py_XDECREF(target.cls); Py_XDECREF(target.to_python); Py_XDECREF(target.from_python);
        return -1;
    }
    Py_ssize_t offset = self->var_offsets[index].offset;
    Py_ssize_t old_len = self->var_offsets[index].length;

    /* Base type fields in the buffer include their alignment padding. */
    Py_ssize_t old_padded = (old_len == 0) ? 0 : (old_len + vf->align - 1) & ~(vf->align - 1);
    Py_ssize_t new_padded = (new_len == 0) ? 0 : (new_len + vf->align - 1) & ~(vf->align - 1);
    
    /* Check if we need to grow the buffer to accommodate this field */
    Py_ssize_t required_end = offset + new_padded;
    if (required_end > self->data_len) {
        Py_ssize_t diff = required_end - self->data_len;
        Py_ssize_t new_total = self->data_len + diff;
        if (new_total > self->buf_cap) {
            Py_ssize_t new_cap = new_total * 2;
            unsigned char *new_buf = (unsigned char *)realloc(self->buf, new_cap);
            if (!new_buf) { Py_DECREF(bval); PyErr_NoMemory(); return -1; }
            memset(new_buf + self->buf_cap, 0, new_cap - self->buf_cap);
            self->buf = new_buf;
            self->buf_cap = new_cap;
        }
        self->data_len = new_total;
    }
    
    Py_ssize_t diff = new_padded - old_padded;

    /* Rule 224: If length changed: memmove subsequent data, update data_len, update
       all subsequent var_offsets[] entries, realloc if needed. */
    if (diff != 0) {
        if (_pc_shift_buffer(self, offset + old_padded, diff, index) < 0) {
            Py_DECREF(bval);
            Py_XDECREF(target.cls); Py_XDECREF(target.to_python); Py_XDECREF(target.from_python);
            return -1;
        }
    }

    /* Rule 225: memcpy new data into position. */
    memcpy(self->buf + offset, PyBytes_AS_STRING(bval), new_len);
    if (new_padded > new_len) {
        memset(self->buf + offset + new_len, 0, new_padded - new_len);
    }

    self->var_offsets[index].length = new_len;
    Py_DECREF(bval);

    /* Rule 226: Auto-sync length_field if present. */
    Py_ssize_t length_field_offset = 0;
    if (vf->length_field_vf) {
        if (_pc_resolve_var_offsets_to(self, vf->length_field_vf->index, 0) < 0) {
            Py_XDECREF(target.cls); Py_XDECREF(target.to_python); Py_XDECREF(target.from_python);
            return -1;
        }
        length_field_offset = self->var_offsets[vf->length_field_vf->index].offset;
    }
    _pc_pack_length(self->buf, length_field_offset, vf, new_len);

    /* Remove from dict if it was there (e.g. replacing a ProtoClass with base type) */
    if (self->dict) {
        PyDict_DelItem(self->dict, vf->name);
        PyErr_Clear();
    }

    Py_XDECREF(target.cls); Py_XDECREF(target.to_python); Py_XDECREF(target.from_python);
    return 0;
}



static PyObject *
ProtoClass_getter(ProtoClassObject *self, void *closure)
{
    FieldInfo *info = (FieldInfo*)closure;

    // 1. Check dict first (local overrides)
    if (self->dict) {
        PyObject *val = PyDict_GetItem(self->dict, info->name);
        if (val) {
            Py_INCREF(val);
            return val;
        }
    }

    Py_ssize_t field_size = abs(info->type_code);
    CHECK_BOUNDS(self, info, field_size);

    PyObject *raw_val = NULL;
    int is_small_int = (info->kind == KIND_INT && field_size <= 8);

    if (is_small_int) {
        uint64_t val = 0;
        switch (field_size) {
            case 1: val = *data; break;
            case 2: val = info->big_endian ? __builtin_bswap16(*(uint16_t*)data) : *(uint16_t*)data; break;
            case 4: val = info->big_endian ? __builtin_bswap32(*(uint32_t*)data) : *(uint32_t*)data; break;
            case 8: val = info->big_endian ? __builtin_bswap64(*(uint64_t*)data) : *(uint64_t*)data; break;
            default: is_small_int = 0; break; // Should not happen given check
        }
        if (is_small_int) {
             if (info->bits > 0) val = (val >> info->bit_pos) & ((1ULL << info->bits) - 1);
             if (info->type_code < 0) raw_val = PyLong_FromLongLong((long long)val);
             else raw_val = PyLong_FromUnsignedLongLong(val);
        }
    }

    if (!raw_val) {
        // Large int or bytes
        if (info->kind == KIND_INT) {
             // Integer (large or odd size)
             // Copy to temp buffer to avoid alignment issues if needed, but FromByteArray handles it.
             raw_val = pc_PyLong_FromByteArray(data, field_size, !info->big_endian, info->type_code < 0);
             if (info->bits > 0 && raw_val) {
                  // Apply bitmask on Python object
                  PyObject *val = raw_val;
                  PyObject *shift = PyLong_FromLong(info->bit_pos);
                  PyObject *mask_val = PyLong_FromLong(1);
                  PyObject *bits = PyLong_FromLong(info->bits);
                  PyObject *shifted = PyNumber_Lshift(mask_val, bits);
                  PyObject *mask = PyNumber_Subtract(shifted, mask_val);

                  PyObject *v_shifted = PyNumber_Rshift(val, shift);
                  raw_val = PyNumber_And(v_shifted, mask);

                  Py_DECREF(val); Py_DECREF(shift); Py_DECREF(mask_val);
                  Py_DECREF(bits); Py_DECREF(shifted); Py_DECREF(mask);
                  Py_DECREF(v_shifted);
             }
        } else {
             // Bytes
             raw_val = PyBytes_FromStringAndSize((char*)data, field_size);
        }
    }

    if (!raw_val) return NULL;

    PyObject *final_val = raw_val;
    if (info->has_callback && info->to_python) {
        final_val = PyObject_CallOneArg(info->to_python, raw_val);
        Py_DECREF(raw_val);
        if (!final_val) return NULL;
    }

    return final_val;
}

/**
 * Macro to check bounds and prepare for setting a value in a buffer.
 *
 * @param OBJ The ProtoClassObject pointer.
 * @param INFO The field info structure containing the relative offset.
 * @param SIZE The size of the data to access.
 */
#define CHECK_SETTER(OBJ, INFO, SIZE) \
    if (OBJ->readonly) { \
        if (_pc_ensure_mutable(OBJ) < 0) return -1; \
    } \
    if (INFO->offset + SIZE > OBJ->data_len) { \
        PyErr_Format(PyExc_IndexError, "Field '%S' out of bounds (offset %zd, size %d, data_len %zd)", INFO->name, INFO->offset, SIZE, OBJ->data_len); \
        return -1; \
    } \
    unsigned char *data = OBJ->buf + OBJ->_offset + INFO->offset;

static PyObject *
getter_bytes(ProtoClassObject *self, void *closure)
{
    FieldInfo *info = (FieldInfo*)closure;
    Py_ssize_t size = abs(info->type_code);
    CHECK_BOUNDS(self, info, size);
    return PyBytes_FromStringAndSize((char*)data, size);
}

static int
setter_bytes(ProtoClassObject *self, PyObject *value, void *closure)
{
    FieldInfo *info = (FieldInfo*)closure;
    Py_ssize_t size = abs(info->type_code);
    CHECK_SETTER(self, info, size);



    if (PyBytes_Check(value)) {
        if (PyBytes_GET_SIZE(value) != size) {
            PyErr_Format(PyExc_ValueError, "Expected %zd bytes, got %zd", size, PyBytes_GET_SIZE(value));
            return -1;
        }
        memcpy(data, PyBytes_AS_STRING(value), size);
    } else if (PyByteArray_Check(value)) {
        if (PyByteArray_GET_SIZE(value) != size) {
            PyErr_Format(PyExc_ValueError, "Expected %zd bytes, got %zd", size, PyByteArray_GET_SIZE(value));
            return -1;
        }
        memcpy(data, PyByteArray_AS_STRING(value), size);
    } else if (PyLong_Check(value)) {
        unsigned long long v = PyLong_AsUnsignedLongLong(value);
        if (!PyErr_Occurred()) {
            if (size <= 8) {
                for (Py_ssize_t i = 0; i < size; i++) {
                    Py_ssize_t shift = info->big_endian ? (size - 1 - i) * 8 : i * 8;
                    data[i] = (uint8_t)((v >> shift) & 0xFF);
                }
            } else {
                PyErr_SetString(PyExc_ValueError, "Integer too large for fixed-size byte field");
                return -1;
            }
        } else {
            return -1;
        }
    } else {
        PyErr_SetString(PyExc_TypeError, "Bytes, ByteArray or compatible int required for fixed-size byte field");
        return -1;
    }

    if (info->is_metadata) {
        self->var_offsets_resolved = 0;
    }
    return 0;
}

/**
 * Set an 8-bit unsigned integer in a ProtoClassObject.
 *
 * @param self The ProtoClassObject instance.
 * @param value The Python long object representing the unsigned integer value.
 * @param closure The field info structure containing the relative offset.
 * @return 0 on success, -1 on failure (with a Python exception set).
 */
static int setter_u8(ProtoClassObject *self, PyObject *value, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_SETTER(self, info, 1);
    unsigned long val = PyLong_AsUnsignedLong(value);
    if (PyErr_Occurred()) return -1;
    *data = (uint8_t)val;
    if (info->is_metadata) {
        self->var_offsets_resolved = 0;
    }
    return 0;
}

/**
 * Set an 8-bit signed integer in a ProtoClassObject.
 *
 * @param self The ProtoClassObject instance.
 * @param value The Python long object representing the signed integer value.
 * @param closure The field info structure containing the relative offset.
 * @return 0 on success, -1 on failure (with a Python exception set).
 */
static int setter_i8(ProtoClassObject *self, PyObject *value, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_SETTER(self, info, 1);
    long val = PyLong_AsLong(value);
    if (PyErr_Occurred()) return -1;
    *(signed char*)data = (signed char)val;
    if (info->is_metadata) {
        self->var_offsets_resolved = 0;
    }
    return 0;
}

/**
 * Macro to define a standard setter function for fixed-size integer types.
 *
 * @param NAME The name of the setter function.
 * @param TYPE The C type of the integer.
 * @param BITS The number of bits in the integer.
 * @param BYTES The number of bytes in the integer.
 * @param CONV A conversion function to apply to the value.
 * @param PYASFUNC A function to convert a Python object to the C type.
 */
#define DEFINE_STD_SETTER(NAME, TYPE, BITS, BYTES, CONV, PYASFUNC) \
static int NAME(ProtoClassObject *self, PyObject *value, void *closure) { \
    FieldInfo *info = (FieldInfo*)closure; \
    CHECK_SETTER(self, info, BYTES); \
    TYPE val = (TYPE)PYASFUNC(value); \
    if (PyErr_Occurred()) return -1; \
    *(uint##BITS##_t*)data = CONV((uint##BITS##_t)val); \
    if (info->is_metadata) { \
        self->var_offsets_resolved = 0; \
    } \
    return 0; \
}

DEFINE_STD_SETTER(setter_u16_le, uint16_t, 16, 2, , PyLong_AsUnsignedLong)
DEFINE_STD_SETTER(setter_u16_be, uint16_t, 16, 2, __builtin_bswap16, PyLong_AsUnsignedLong)
DEFINE_STD_SETTER(setter_i16_le, int16_t, 16, 2, , PyLong_AsLong)
DEFINE_STD_SETTER(setter_i16_be, int16_t, 16, 2, (uint16_t)__builtin_bswap16, PyLong_AsLong)

DEFINE_STD_SETTER(setter_u32_le, uint32_t, 32, 4, , PyLong_AsUnsignedLong)
DEFINE_STD_SETTER(setter_u32_be, uint32_t, 32, 4, __builtin_bswap32, PyLong_AsUnsignedLong)
DEFINE_STD_SETTER(setter_i32_le, int32_t, 32, 4, , PyLong_AsLong)
DEFINE_STD_SETTER(setter_i32_be, int32_t, 32, 4, (uint32_t)__builtin_bswap32, PyLong_AsLong)

DEFINE_STD_SETTER(setter_u64_le, uint64_t, 64, 8, , PyLong_AsUnsignedLongLong)
DEFINE_STD_SETTER(setter_u64_be, uint64_t, 64, 8, __builtin_bswap64, PyLong_AsUnsignedLongLong)
DEFINE_STD_SETTER(setter_i64_le, int64_t, 64, 8, , PyLong_AsLongLong)
DEFINE_STD_SETTER(setter_i64_be, int64_t, 64, 8, (uint64_t)__builtin_bswap64, PyLong_AsLongLong)

/**
 * Set a 128-bit unsigned integer in a ProtoClassObject.
 *
 * @param self The ProtoClassObject instance.
 * @param value The Python long object representing the unsigned integer value.
 * @param closure The field info structure containing the relative offset.
 * @return 0 on success, -1 on failure (with a Python exception set).
 */
static int setter_u128_le(ProtoClassObject *self, PyObject *value, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_SETTER(self, info, 16);
    if (!PyLong_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "Integer required");
        return -1;
    }
    int res = pc_PyLong_AsByteArray(value, data, 16, 1, 0);
    if (res == 0 && info->is_metadata) {
        self->var_offsets_resolved = 0;
    }
    return res;
}

/**
 * Set a 128-bit unsigned integer in a ProtoClassObject.
 *
 * @param self The ProtoClassObject instance.
 * @param value The Python long object representing the unsigned integer value.
 * @param closure The field info structure containing the relative offset.
 * @return 0 on success, -1 on failure (with a Python exception set).
 */
static int setter_u128_be(ProtoClassObject *self, PyObject *value, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_SETTER(self, info, 16);
    if (!PyLong_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "Integer required");
        return -1;
    }
    int res = pc_PyLong_AsByteArray(value, data, 16, 0, 0);
    if (res == 0 && info->is_metadata) {
        self->var_offsets_resolved = 0;
    }
    return res;
}

/**
 * Set a 128-bit signed integer in a ProtoClassObject.
 *
 * @param self The ProtoClassObject instance.
 * @param value The Python long object representing the signed integer value.
 * @param closure The field info structure containing the relative offset.
 * @return 0 on success, -1 on failure (with a Python exception set).
 */
static int setter_i128_le(ProtoClassObject *self, PyObject *value, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_SETTER(self, info, 16);
    if (!PyLong_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "Integer required");
        return -1;
    }
    int res = pc_PyLong_AsByteArray(value, data, 16, 1, 1);
    if (res == 0 && info->is_metadata) {
        self->var_offsets_resolved = 0;
    }
    return res;
}

/**
 * Set a 128-bit signed integer in a ProtoClassObject.
 *
 * @param self The ProtoClassObject instance.
 * @param value The Python long object representing the signed integer value.
 * @param closure The field info structure containing the relative offset.
 * @return 0 on success, -1 on failure (with a Python exception set).
 */
static int setter_i128_be(ProtoClassObject *self, PyObject *value, void *closure) {
    FieldInfo *info = (FieldInfo*)closure;
    CHECK_SETTER(self, info, 16);
    if (!PyLong_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "Integer required");
        return -1;
    }
    int res = pc_PyLong_AsByteArray(value, data, 16, 0, 1);
    if (res == 0 && info->is_metadata) {
        self->var_offsets_resolved = 0;
    }
    return res;
}

/**
 * Set a generic bitfield in a ProtoClassObject.
 *
 * @param self The ProtoClassObject instance.
 * @param value The Python long object representing the bitfield value.
 * @param closure The field info structure containing the relative offset.
 * @return 0 on success, -1 on failure (with a Python exception set).
 */
static int
ProtoClass_setter(ProtoClassObject *self, PyObject *value, void *closure)
{
    FieldInfo *info = (FieldInfo *) closure;
    Py_ssize_t field_size = abs(info->type_code);
    PyObject *final_value = NULL;

    // 1. Process Callback (transform value)
    if (info->has_callback && info->from_python) {
        final_value = PyObject_CallOneArg(info->from_python, value);
        if (!final_value) return -1; // Exception raised by callback
    } else {
        Py_INCREF(value);
        final_value = value;
    }
    // Now 'final_value' is an owned reference we must DECREF at end

    CHECK_SETTER(self, info, field_size);

    int ret = 0;

    // 3. Write Logic
    if (info->kind == KIND_INT) {
        // Integer path
        if (field_size <= 8 && !info->big_endian && field_size != 3 && field_size != 5 && field_size != 6 && field_size != 7) {
             // Try fast path for standard sizes
             // Note: Excluding odd sizes explicitly for now as switch handles standard
             unsigned long long v_in;
             if (info->type_code < 0) v_in = (unsigned long long)PyLong_AsLongLong(final_value);
             else v_in = PyLong_AsUnsignedLongLong(final_value);

             if (PyErr_Occurred()) { ret = -1; goto done; }

             uint64_t mask = ((1ULL << info->bits) - 1);

             // RMW if bits used
             if (info->bits > 0) {
                 uint64_t current = 0;
                 switch (field_size) {
                     case 1: current = *data; break;
                     case 2: current = *(uint16_t*)data; break; // Assumes Little Endian host for now? logic below handles swap
                     case 4: current = *(uint32_t*)data; break;
                     case 8: current = *(uint64_t*)data; break;
                 }
                 // Handle Endianness for RMW
                 if (info->big_endian) {
                      if (field_size==2) current = __builtin_bswap16(current);
                      else if (field_size==4) current = __builtin_bswap32(current);
                      else if (field_size==8) current = __builtin_bswap64(current);
                 }

                 current &= ~(mask << info->bit_pos);
                 current |= (v_in & mask) << info->bit_pos;
                 v_in = current;
             }

             if (info->big_endian) {
                  switch (field_size) {
                      case 1: *data = (uint8_t)v_in; break;
                      case 2: *(uint16_t*)data = __builtin_bswap16((uint16_t)v_in); break;
                      case 4: *(uint32_t*)data = __builtin_bswap32((uint32_t)v_in); break;
                      case 8: *(uint64_t*)data = __builtin_bswap64((uint64_t)v_in); break;
                  }
             } else {
                  switch (field_size) {
                      case 1: *data = (uint8_t)v_in; break;
                      case 2: *(uint16_t*)data = (uint16_t)v_in; break;
                      case 4: *(uint32_t*)data = (uint32_t)v_in; break;
                      case 8: *(uint64_t*)data = (uint64_t)v_in; break;
                  }
             }
        } else {
             // Slow path (Large ints, odd sizes)
             if (info->bits > 0) {
                 // RMW via Python Objects

                 if (field_size > 16) { ret = -1; PyErr_SetString(PyExc_ValueError, "Bitfields > 128 bit not supported"); goto done; }

                 PyObject *current = pc_PyLong_FromByteArray(data, field_size, !info->big_endian, info->type_code < 0);

                 PyObject *one = PyLong_FromLong(1);
                 PyObject *bits_val = PyLong_FromLong(info->bits);
                 PyObject *shifted_one = PyNumber_Lshift(one, bits_val);
                 PyObject *mask_obj = PyNumber_Subtract(shifted_one, one);
                 PyObject *shift = PyLong_FromLong(info->bit_pos);
                 PyObject *shifted_mask = PyNumber_Lshift(mask_obj, shift);
                 PyObject *inverted_mask = PyNumber_Invert(shifted_mask);

                 PyObject *masked_current = PyNumber_And(current, inverted_mask);
                 PyObject *masked_value = PyNumber_And(final_value, mask_obj);
                 PyObject *shifted_value = PyNumber_Lshift(masked_value, shift);
                 PyObject *res_val = PyNumber_Or(masked_current, shifted_value);

                 if (pc_PyLong_AsByteArray(res_val, data, field_size, !info->big_endian, info->type_code < 0) < 0) ret = -1;

                 Py_DECREF(current); Py_DECREF(one); Py_DECREF(bits_val); Py_DECREF(shifted_one);
                 Py_DECREF(mask_obj); Py_DECREF(shift); Py_DECREF(shifted_mask); Py_DECREF(inverted_mask);
                 Py_DECREF(masked_current); Py_DECREF(masked_value); Py_DECREF(shifted_value); Py_DECREF(res_val);
             } else {
                 if (pc_PyLong_AsByteArray(final_value, data, field_size, !info->big_endian, info->type_code < 0) < 0) ret = -1;
             }
        }
    } else {
        // Bytes/Buffer path
        Py_buffer view;
        if (PyObject_GetBuffer(final_value, &view, PyBUF_SIMPLE) == 0) {
            if (view.len != field_size) {
                 PyErr_Format(PyExc_ValueError, "Expected %zd bytes, got %zd", field_size, view.len);
                 ret = -1;
            } else {
                 memcpy(data, view.buf, field_size);
            }
            PyBuffer_Release(&view);
        } else {
            // Fallback
            PyErr_Clear();
            PyErr_Format(PyExc_TypeError, "Expected bytes-like object of size %zd", field_size);
            ret = -1;
        }
    }

done:
    if (ret == 0 && info->is_metadata) {
        self->var_offsets_resolved = 0;
    }
    Py_DECREF(final_value);
    return ret;
}

/**
 * Create a new ProtoClassObject from a buffer.
 *
 * @param type The type object for the ProtoClassObject.
 * @param args A tuple containing the buffer and optional offset.
 * @param kwds A dictionary of keyword arguments.
 * @return A new ProtoClassObject on success, or NULL on failure (with a Python exception set).
 */
static PyObject *
ProtoClass_from_buffer(PyTypeObject *type, PyObject *args, PyObject *kwargs)
{
    PyObject *obj;
    Py_ssize_t offset = 0;
    unsigned char *ptr;
    Py_ssize_t buf_len;
    Py_buffer view;

    /* No offset provided. Don't bother with kwarg parsing */
    if (kwargs == NULL && PyTuple_GET_SIZE(args) == 1) {
        obj = PyTuple_GET_ITEM(args, 0);
    } else {
        static char *kwlist[] = {"buffer", "offset", NULL};
        if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|n", kwlist, &obj, &offset))
            return NULL;
    }

    if (PyObject_GetBuffer(obj, &view, PyBUF_SIMPLE) < 0)
        return NULL;
    ptr = (unsigned char *)view.buf;
    buf_len = view.len;
    PyBuffer_Release(&view);

    if (offset < 0 || offset > buf_len) {
        PyErr_SetString(PyExc_ValueError, "Offset out of bounds");
        return NULL;
    }

    TypeMeta *meta = _get_type_meta_safe(type);
    if (meta && meta->fixed_size > 0 && buf_len - offset < meta->fixed_size) {
        PyErr_SetString(PyExc_ValueError, "Buffer too small");
        return NULL;
    }

    ProtoClassObject *self = (ProtoClassObject *) type->tp_alloc(type, 0);
    if (!self) return NULL;

    self->buf = ptr;
    self->buf_cap = 0; // borrowed
    self->data_len = buf_len - offset;
    self->_offset = offset;
    self->readonly = 1;

    self->_buffer = obj;
    Py_INCREF(obj);

    self->type_meta = meta;
    if (meta) TypeMeta_incref(meta);

    self->var_offsets = NULL;
    self->var_offsets_resolved = 0;
    self->dict = NULL;

    /* Zero out subclass slots if any */
    if (type->tp_basicsize > (Py_ssize_t)sizeof(ProtoClassObject)) {
        memset((char *)self + sizeof(ProtoClassObject), 0, type->tp_basicsize - sizeof(ProtoClassObject));
    }

    return (PyObject *)self;
}

/**
 * Initialize a new ProtoClassObject.
 *
 * @param self The ProtoClassObject instance to initialize.
 * @param args A tuple containing the buffer and optional offset.
 * @param kwds A dictionary of keyword arguments.
 * @return 0 on success, -1 on failure (with a Python exception set).
 */
static int
ProtoClass_init(ProtoClassObject *self, PyObject *args, PyObject *kwds)
{
    if (self->buf) return 0; /* Already initialized */

    TypeMeta *meta = _get_type_meta(self);
    if (!meta) {
        PyErr_SetString(PyExc_TypeError, "Class is not a valid ProtoClass (missing metadata)");
        return -1;
    }

    Py_ssize_t sz = meta->fixed_size;
    self->data_len = sz;
    self->buf_cap = sz > 8 ? sz : 8;
    self->buf = (unsigned char *)malloc(self->buf_cap);
    if (!self->buf) {
        PyErr_NoMemory();
        return -1;
    }

    if (sz > 0) {
        if (meta->template_buffer) {
            memcpy(self->buf, meta->template_buffer, sz);
        } else {
            memset(self->buf, 0, sz);
        }
    }
    /* Variable-field resolution reads fields whose storage may not have been
       materialized yet, so keep the spare capacity zeroed. */
    if (meta->var_defs && meta->var_defs->size > 0 && self->buf_cap > sz) {
        memset(self->buf + sz, 0, self->buf_cap - sz);
    }

    self->_offset = 0;
    self->readonly = 0;
    self->_buffer = NULL;
    self->dict = NULL;
    self->type_meta = meta;
    TypeMeta_incref(meta);

    self->var_offsets = NULL;
    self->var_offsets_resolved = 0;

    /* Phase 1: Apply defaults (skip any key that will be overridden by kwds) */
    PyObject *defaults = meta->defaults;
    if (defaults && PyDict_Check(defaults)) {
        PyObject *key, *value;
        Py_ssize_t pos = 0;
        while (PyDict_Next(defaults, &pos, &key, &value)) {
            if (kwds && PyDict_GetItem(kwds, key)) continue;

            PyObject *capsule = PyDict_GetItem(meta->field_map, key);
            if (capsule) {
                PyGetSetDef *gs = (PyGetSetDef *)PyCapsule_GetPointer(capsule, "protoclass.getset");
                if (gs && gs->set) {
                    if (gs->set((PyObject *)self, value, gs->closure) < 0) return -1;
                    continue;
                }
            }
            if (PyObject_SetAttr((PyObject*)self, key, value) < 0) return -1;
        }
    }

    /* Phase 2: Apply keyword arguments.
       Rule: Apply fixed fields FIRST to ensure type_fields and length_fields
       are available for write-through variable setters. */
    if (kwds && PyDict_Check(kwds)) {
        PyObject *key, *value;
        Py_ssize_t pos = 0;

        /* Pass 2a: Fixed fields */
        while (PyDict_Next(kwds, &pos, &key, &value)) {
            PyObject *capsule = PyDict_GetItem(meta->field_map, key);
            if (capsule) {
                PyGetSetDef *gs = (PyGetSetDef *)PyCapsule_GetPointer(capsule, "protoclass.getset");
                if (gs && gs->set) {
                    /* Only apply fixed fields in this pass.closure is FieldInfo* for fixed fields. */
                    /* Use binary check: fixed fields in field_infos array, var fields in var_defs. */
                    int is_var = 0;
                    if (meta->var_defs) {
                        for (Py_ssize_t i = 0; i < meta->var_defs->size; i++) {
                            if (gs->closure == (void *)&meta->var_defs->array[i]) { is_var = 1; break; }
                        }
                    }
                    if (!is_var) {
                        if (gs->set((PyObject *)self, value, gs->closure) < 0) return -1;
                    }
                }
            }
        }

        /* Pass 2b: Variable fields */
        pos = 0;
        while (PyDict_Next(kwds, &pos, &key, &value)) {
            PyObject *capsule = PyDict_GetItem(meta->field_map, key);
            if (capsule) {
                PyGetSetDef *gs = (PyGetSetDef *)PyCapsule_GetPointer(capsule, "protoclass.getset");
                if (gs && gs->set) {
                    int is_var = 0;
                    if (meta->var_defs) {
                        for (Py_ssize_t i = 0; i < meta->var_defs->size; i++) {
                            if (gs->closure == (void *)&meta->var_defs->array[i]) { is_var = 1; break; }
                        }
                    }
                    if (is_var) {
                        if (gs->set((PyObject *)self, value, gs->closure) < 0) return -1;
                    }
                    continue;
                }
            }
            if (!PyObject_HasAttr((PyObject*)self, key)) {
                 if (PyObject_SetAttr((PyObject*)self, key, value) < 0) return -1;
            }
        }
    }

    return 0;
}
static PyObject *
ProtoClass_init_callable(ProtoClassObject *self, PyObject *args, PyObject *kwds)
{
    if (ProtoClass_init(self, args, kwds) < 0) return NULL;
    Py_RETURN_NONE;
}

/**
 * Resolve the target type for a polymorphic field.
 *
 * Looks up the value of type_field on the instance, then uses type_map
 * to find the corresponding target type. Populates `out` with type info.
 *
 * @param self The ProtoClass instance
 * @param info The VarFieldInfo containing type_field and type_map
 * @param out  Output struct to populate with resolved type info
 */
/**
 * Resolve the target type for a polymorphic field.
 */
static void
_resolve_poly_info(PyObject *obj, PolyTypeInfo *out)
{
    out->kind = 0;
    out->bits = 0;
    out->is_signed = 0;
    out->fixed_size = 0;
    out->to_python = NULL;
    out->from_python = NULL;
    out->cls = NULL;
    out->meta = NULL;

    if (!obj || obj == Py_None) return;

    if (PyTuple_Check(obj)) {
        if (PyArg_ParseTuple(obj, "iiinOOOi", &out->kind, &out->bits, &out->is_signed,
                            &out->fixed_size, &out->to_python, &out->from_python, &out->cls,
                            &out->big_endian)) {

            Py_XINCREF(out->to_python);
            if (out->to_python == Py_None) { Py_DECREF(out->to_python); out->to_python = NULL; }

            Py_XINCREF(out->from_python);
            if (out->from_python == Py_None) { Py_DECREF(out->from_python); out->from_python = NULL; }

            Py_XINCREF(out->cls);
            if (out->cls == Py_None) { Py_DECREF(out->cls); out->cls = NULL; }

            if (out->cls && PyType_Check(out->cls) && PyType_IsSubtype((PyTypeObject *)out->cls, ProtoClass_TypePtr)) {
                out->meta = _get_type_meta_safe((PyTypeObject *)out->cls);
            }
        } else {
            PyErr_Clear();
        }
    }
}


/* Variable fields whose output offsets/lengths live in a fixed-size inline
   array, spilling to the heap only for unusually wide structs. */
#define PC_INLINE_VAR_FIELDS 16

/**
 * Canonical Single-Pass Interpolated Serialization.
 * Rule 164: Copy fixed header + interpolate ProtoClasses from dict.
 */
static unsigned char *
_pc_serialize_data(ProtoClassObject *self, Py_ssize_t *out_len)
{
    TypeMeta *meta = self->type_meta;
    if (!meta) return NULL;

    Py_ssize_t inline_out_offset[PC_INLINE_VAR_FIELDS];
    Py_ssize_t inline_out_len[PC_INLINE_VAR_FIELDS];
    Py_ssize_t *var_out_offset = NULL;
    Py_ssize_t *var_out_len = NULL;
    int var_arrays_heap = 0;

    Py_ssize_t written = meta->fixed_size;
    Py_ssize_t cap = written + 256;
    unsigned char *out = (unsigned char *)malloc(cap);
    if (!out) {
        PyErr_NoMemory();
        return NULL;
    }

    memcpy(out, self->buf + self->_offset, meta->fixed_size);

    VarDefs *defs = meta->var_defs;
    if (defs) {
        var_out_offset = inline_out_offset;
        var_out_len = inline_out_len;
        if (defs->size > PC_INLINE_VAR_FIELDS) {
            var_arrays_heap = 1;
            var_out_offset = PyMem_Malloc(sizeof(Py_ssize_t) * defs->size);
            var_out_len = PyMem_Malloc(sizeof(Py_ssize_t) * defs->size);
            if (!var_out_offset || !var_out_len) {
                free(out);
                PyErr_NoMemory();
                goto fail;
            }
        }
        for (Py_ssize_t i = 0; i < defs->size; i++) {
            VarFieldInfo *vf = &defs->array[i];

            PyObject *dict_val = NULL;
            if (self->dict) {
                dict_val = PyDict_GetItem(self->dict, vf->name);
            }

            unsigned char *v_src = NULL;
            Py_ssize_t v_len = 0;
            PyObject *b_pc = NULL;

            if (dict_val) {
                if (vf->is_list) {
                    Py_ssize_t list_size = PyList_GET_SIZE(dict_val);
                    Py_ssize_t list_cap = 256;
                    Py_ssize_t list_total = 0;
                    unsigned char *list_buf = (unsigned char *)malloc(list_cap);
                    if (!list_buf) { free(out); PyErr_NoMemory(); goto fail; }

                    for (Py_ssize_t j = 0; j < list_size; j++) {
                        PyObject *item = PyList_GET_ITEM(dict_val, j);
                        Py_ssize_t item_len = 0;
                        unsigned char *item_bytes = NULL;
                        PyObject *b_item = NULL;

                        if (_pc_is_protoclass(item)) {
                            b_item = PyObject_CallMethod(item, "__bytes__", NULL);
                            if (!b_item) { free(list_buf); free(out); goto fail; }
                            item_bytes = (unsigned char *)PyBytes_AS_STRING(b_item);
                            item_len = PyBytes_GET_SIZE(b_item);
                        } else {
                            /* Primitive list item - serialize using pre-computed vf->item_* metadata */
                            switch (vf->item_kind) {
                                case KIND_INT: {
                                    Py_ssize_t n = (vf->item_bits + 7) / 8;
                                    b_item = PyBytes_FromStringAndSize(NULL, n);
                                    if (b_item) {
                                        if (pc_PyLong_AsByteArray(item, (unsigned char *)PyBytes_AS_STRING(b_item), n, !vf->big_endian, vf->item_is_signed) < 0) {
                                            Py_DECREF(b_item);
                                            b_item = NULL;
                                        }
                                    }
                                    break;
                                }
                                case KIND_STRING:
                                    b_item = _pc_get_null_terminated_bytes(item);
                                    break;
                                case KIND_BYTES:
                                default:
                                    if (vf->from_python && vf->from_python != Py_None) {
                                        b_item = PyObject_CallOneArg(vf->from_python, item);
                                    } else {
                                        b_item = _pc_get_bytes(item);
                                    }
                                    break;
                            }
                            if (!b_item) { free(list_buf); free(out); goto fail; }
                            item_bytes = (unsigned char *)PyBytes_AS_STRING(b_item);
                            item_len = PyBytes_GET_SIZE(b_item);
                        }

                        Py_ssize_t pad = (vf->align > 1) ? (vf->align - (item_len % vf->align)) % vf->align : 0;
                        if (list_total + item_len + pad > list_cap) {
                            list_cap = (list_total + item_len + pad) * 2;
                            unsigned char *new_lbuf = (unsigned char *)realloc(list_buf, list_cap);
                            if (!new_lbuf) { free(list_buf); free(out); Py_DECREF(b_item); PyErr_NoMemory(); goto fail; }
                            list_buf = new_lbuf;
                        }
                        memcpy(list_buf + list_total, item_bytes, item_len);
                        if (pad > 0) memset(list_buf + list_total + item_len, 0, pad);
                        list_total += item_len + pad;
                        Py_DECREF(b_item);
                    }
                    b_pc = PyBytes_FromStringAndSize((char *)list_buf, list_total);
                    free(list_buf);
                    if (!b_pc) { free(out); goto fail; }
                    v_src = (unsigned char *)PyBytes_AS_STRING(b_pc);
                    v_len = list_total;
                } else {
                    b_pc = PyObject_CallMethod(dict_val, "__bytes__", NULL);
                    if (!b_pc) { free(out); goto fail; }
                    v_src = (unsigned char *)PyBytes_AS_STRING(b_pc);
                    v_len = PyBytes_GET_SIZE(b_pc);
                }
            } else {
                /* Base type (Rule 6): Already in self->buf. Direct copy. */
                if (_pc_resolve_var_offsets_to(self, i, 1) < 0) { free(out); goto fail; }
                v_src = self->buf + self->_offset + self->var_offsets[i].offset;
                v_len = self->var_offsets[i].length;
            }

            Py_ssize_t pad = (vf->align > 1 && v_len > 0) ? (vf->align - (v_len % vf->align)) % vf->align : 0;
            if (written + v_len + pad > cap) {
                cap = (written + v_len + pad) * 2;
                unsigned char *new_out = (unsigned char *)realloc(out, cap);
                if (!new_out) { free(out); Py_XDECREF(b_pc); PyErr_NoMemory(); goto fail; }
                out = new_out;
            }

            var_out_offset[i] = written;
            var_out_len[i] = v_len;
            memcpy(out + written, v_src, v_len);
            if (pad > 0) memset(out + written + v_len, 0, pad);

            written += v_len + pad;
            Py_XDECREF(b_pc);
        }

        /* Refresh length_fields now that every field's output offset and
           serialized length are known. */
        for (Py_ssize_t i = 0; i < defs->size; i++) {
            VarFieldInfo *vf = &defs->array[i];
            if (!vf->length_field) continue;
            Py_ssize_t variable_offset = 0;
            if (vf->length_field_vf) {
                variable_offset = var_out_offset[vf->length_field_vf->index];
            }
            _pc_pack_length(out, variable_offset, vf, var_out_len[i]);
        }

        if (var_arrays_heap) {
            PyMem_Free(var_out_offset);
            PyMem_Free(var_out_len);
        }
    }
    *out_len = written;
    return out;

fail:
    if (var_arrays_heap) {
        PyMem_Free(var_out_offset);
        PyMem_Free(var_out_len);
    }
    return NULL;
}

static PyObject *
ProtoClass_bytes(ProtoClassObject *self, PyObject *noargs)
{
    Py_ssize_t out_len = 0;
    unsigned char *serialized = _pc_serialize_data(self, &out_len);
    if (!serialized) return NULL;

    PyObject *result = PyBytes_FromStringAndSize((char *)serialized, out_len);
    free(serialized);
    return result;
}

static int
ProtoClass_getbuffer(ProtoClassObject *self, Py_buffer *view, int flags)
{
    TypeMeta *meta = self->type_meta;
    if (!meta) return -1;

    if (meta->var_defs && meta->var_defs->size > 0) {
        PyErr_SetString(PyExc_BufferError, "Buffer protocol only supported for fixed-size ProtoClass");
        return -1;
    }

    return PyBuffer_FillInfo(view, (PyObject *)self, self->buf + self->_offset, meta->fixed_size, self->readonly, flags);
}

static PyBufferProcs ProtoClass_as_buffer = {
    (getbufferproc)ProtoClass_getbuffer,
    NULL,
};

/**
 * Serialized length of a list field's items, including per-item alignment.
 */
static Py_ssize_t
_pc_list_serialized_length(ProtoClassObject *self, PyObject *list, VarFieldInfo *vf)
{
    Py_ssize_t total = 0;
    Py_ssize_t size = PyList_GET_SIZE(list);
    for (Py_ssize_t i = 0; i < size; i++) {
        PyObject *item = PyList_GET_ITEM(list, i);
        Py_ssize_t item_len;

        if (_pc_is_protoclass(item)) {
            item_len = PyObject_Length(item);
            if (item_len < 0) return -1;
        } else {
            PolyTypeInfo info;
            memset(&info, 0, sizeof(info));
            info.kind = vf->item_kind;
            info.bits = vf->item_bits;
            info.is_signed = vf->item_is_signed;
            info.fixed_size = vf->item_fixed_size;
            info.big_endian = vf->big_endian;
            info.cls = vf->item_type;
            info.to_python = vf->to_python;
            info.from_python = vf->from_python;
            PyObject *bval = _pc_convert_to_bytes(self, item, vf, &info);
            if (!bval) return -1;
            item_len = PyBytes_GET_SIZE(bval);
            Py_DECREF(bval);
        }

        total += item_len;
        if (vf->align > 1) {
            total += (vf->align - (item_len % vf->align)) % vf->align;
        }
    }
    return total;
}

/**
 * Convert a ProtoClassObject to a bytes object.
 *
 * @param self The ProtoClassObject instance to convert.
 * @param args A tuple containing the size of the bytes object.
 * @return A bytes object on success, or NULL on failure (with a Python exception set).
 */
static PyObject *
ProtoClass_len(ProtoClassObject *self, PyObject *noargs)
{
    TypeMeta *meta = self->type_meta;
    if (!meta) return PyLong_FromLong(0);

    Py_ssize_t total = meta->fixed_size;
    VarDefs *defs = meta->var_defs;
    if (defs) {
        for (Py_ssize_t i = 0; i < defs->size; i++) {
            VarFieldInfo *vf = &defs->array[i];

            Py_ssize_t field_len = -1;

            /* Fast path: if the field is not overridden in dict, read its raw
               length from the buffer's var_offsets. This avoids calling
               _pc_convert_to_bytes which can fail with OverflowError for union fields
               whose raw buffer bytes look like an integer. */
            int in_dict = 0;
            if (self->dict && vf->name) {
                in_dict = PyDict_Contains(self->dict, vf->name);
                if (in_dict < 0) return NULL;
            }

            if (!in_dict && self->buf) {
                /* Read from buffer: resolve offsets and use stored length */
                if (_pc_resolve_var_offsets_to(self, i, 1) == 0 &&
                    self->var_offsets && self->var_offsets[i].resolved) {
                    field_len = self->var_offsets[i].length;
                }
            }

            if (field_len < 0) {
                /* Dict-backed or unknown: compute via _pc_convert_to_bytes */
                PyObject *val = _pc_get_field_value(self, vf, i);
                if (!val) return NULL;

                if (PyList_Check(val)) {
                    field_len = _pc_list_serialized_length(self, val, vf);
                    if (field_len < 0) { Py_DECREF(val); return NULL; }
                } else if (_pc_is_protoclass(val)) {
                    field_len = PyObject_Length(val);
                    if (field_len < 0) { Py_DECREF(val); return NULL; }
                } else {
                    PyObject *bval = _pc_convert_to_bytes(self, val, vf, NULL);
                    if (!bval) { Py_DECREF(val); return NULL; }
                    field_len = PyBytes_GET_SIZE(bval);
                    Py_DECREF(bval);
                }
                Py_DECREF(val);
            }

            total += field_len;
            /* Post-field alignment padding */
            if (vf->align > 1) {
                total += (vf->align - (field_len % vf->align)) % vf->align;
            }
        }
    }
    return PyLong_FromSsize_t(total);
}

static PyMethodDef ProtoClass_methods[] = {
    {"from_buffer", (PyCFunction)(void(*)(void))ProtoClass_from_buffer, METH_CLASS | METH_VARARGS | METH_KEYWORDS, NULL},
    {"from_bytes", (PyCFunction)(void(*)(void))ProtoClass_from_buffer, METH_CLASS | METH_VARARGS | METH_KEYWORDS, NULL},
    {"__init__", (PyCFunction)(void(*)(void))ProtoClass_init_callable, METH_VARARGS | METH_KEYWORDS, NULL},
    {"__bytes__", (PyCFunction) ProtoClass_bytes, METH_NOARGS, NULL},
    {"to_bytes", (PyCFunction) ProtoClass_bytes, METH_NOARGS, NULL},
    {"__len__", (PyCFunction) ProtoClass_len, METH_NOARGS, NULL},
    {NULL}
};

static int
ProtoClass_populate_type_from_meta(PyTypeObject *type, TypeMeta *meta)
{
    PyObject *tp_dict = type->tp_dict;
    Py_ssize_t idx;

    // Check if already populated to avoid duplication
    if (PyDict_GetItemString(tp_dict, "_populated")) return 0;
    PyDict_SetItemString(tp_dict, "_populated", Py_True);

    /* We skip adding ProtoClass_methods here because they are inherited from ProtoClass.
       Adding them specifically for the type might be faster but it's redundant and
       can cause issues with multiple inheritance or type reconstruction. */

    if (meta->var_defs) {
        for (Py_ssize_t i = 0; i < meta->var_defs->size; i++) {
            VarFieldInfo *vf = &meta->var_defs->array[i];
            PyObject *d = PyDict_GetItemString(tp_dict, PyUnicode_AsUTF8(vf->name));
            if (d && PyObject_TypeCheck(d, &PyMemberDescr_Type)) {
                PyMemberDescrObject *m = (PyMemberDescrObject *)d;
                vf->member_offset = m->d_member->offset;
            }
        }
    }
    for (idx = 0; meta->getset[idx].name; idx++) {
        PyObject *descr = PyDescr_NewGetSet(type, &meta->getset[idx]);
        if (descr) {
            PyObject *existing = PyDict_GetItemString(tp_dict, meta->getset[idx].name);
            if (!existing || (!PyObject_HasAttrString(existing, "__get__") && !PyObject_HasAttrString(existing, "__set__"))) {
                PyDict_SetItemString(tp_dict, meta->getset[idx].name, descr);
            }

            // Always add _pc_ alias for trusted access from Python wrappers
            char alias[256];
            snprintf(alias, sizeof(alias), "_pc_%s", meta->getset[idx].name);
            PyDict_SetItemString(tp_dict, alias, descr);

            Py_DECREF(descr);
        }
    }

    if (!meta->defaults) {
        meta->defaults = PyObject_GetAttrString((PyObject *)type, "_defaults");
        if (!meta->defaults) PyErr_Clear();
    }

    if (meta->fixed_size > 0 && meta->template_buffer) {
        if (meta->defaults && PyDict_Check(meta->defaults) && PyDict_Size(meta->defaults) > 0) {
            ProtoClassObject *temp = (ProtoClassObject *)type->tp_alloc(type, 0);
            if (temp) {
                temp->buf = (unsigned char *)malloc(meta->fixed_size);
                if (!temp->buf) {
                    Py_DECREF(temp);
                    return -1;
                }
                memcpy(temp->buf, meta->template_buffer, meta->fixed_size);
                temp->buf_cap = meta->fixed_size;
                temp->data_len = meta->fixed_size;
                temp->_offset = 0;
                temp->readonly = 0;
                temp->type_meta = meta;
                TypeMeta_incref(meta);
                temp->var_offsets = NULL;
                temp->var_offsets_resolved = 0;
                temp->dict = NULL;
                temp->_buffer = NULL;

                PyObject *key, *value;
                Py_ssize_t pos = 0;
                while (PyDict_Next(meta->defaults, &pos, &key, &value)) {
                    PyObject *capsule = PyDict_GetItem(meta->field_map, key);
                    if (capsule) {
                        PyGetSetDef *gs = (PyGetSetDef *)PyCapsule_GetPointer(capsule, "protoclass.getset");
                        if (gs && gs->set) {
                            gs->set((PyObject *)temp, value, gs->closure);
                        }
                    }
                }
                memcpy(meta->template_buffer, temp->buf, meta->fixed_size);
                Py_DECREF(temp);
            }
        }
    }

    PyType_Modified(type);

    return 0;
}

/**
 * Prepare C-level metadata for a ProtoClass
 */
static PyObject *
make_binary_type(PyObject *self, PyObject *args)
{
    char *name;
    PyObject *fields;
    PyObject *var_fields_list = NULL;
    Py_ssize_t fixed_size = 0;

    if (!PyArg_ParseTuple(args, "sO!nO!", &name, &PyList_Type, &fields, &fixed_size, &PyList_Type, &var_fields_list))
        return NULL;

    TypeMeta *meta = TypeMeta_alloc();
    if (!meta) return PyErr_NoMemory();

    Py_ssize_t n_fields = PyList_Size(fields);
    Py_ssize_t vn = 0;
    if (var_fields_list && PyList_Check(var_fields_list)) {
        vn = PyList_Size(var_fields_list);
    }
    meta->field_info_count = n_fields;
    if (n_fields > 0) {
        meta->field_infos = PyMem_Calloc(n_fields, sizeof(FieldInfo *));
    }
    meta->fixed_size = fixed_size;
    if (fixed_size > 0) {
        meta->template_buffer = PyMem_Malloc(fixed_size);
        if (meta->template_buffer) memset(meta->template_buffer, 0, fixed_size);
    }
    meta->getset = PyMem_Calloc(n_fields + vn + 1, sizeof(PyGetSetDef));
    meta->field_mapping_count = n_fields + vn;
    meta->field_mappings = PyMem_Calloc(meta->field_mapping_count, sizeof(FieldMapping));


    for (Py_ssize_t i = 0; i < n_fields; i++) {
        PyObject *item = PyList_GetItem(fields, i);
        FieldInfo *info = PyMem_Calloc(1, sizeof(FieldInfo));
        meta->field_infos[i] = info;
        PyObject *f_name_obj;
        int endian;
        if (!PyArg_ParseTuple(item, "OniiiiiiiOO", &f_name_obj, &info->offset, &info->type_code, &info->bit_pos, &info->bits, &endian, &info->kind, &info->has_callback, &info->is_metadata, &info->to_python, &info->from_python)) {
            TypeMeta_decref(meta);
            return NULL;
        }
        Py_XINCREF(info->to_python);
        Py_XINCREF(info->from_python);
        if (info->to_python == Py_None) { Py_DECREF(info->to_python); info->to_python = NULL; }
        if (info->from_python == Py_None) { Py_DECREF(info->from_python); info->from_python = NULL; }

        info->big_endian = endian;
        info->name = f_name_obj;
        Py_INCREF(info->name);

        meta->field_mappings[i].name = f_name_obj;
        meta->field_mappings[i].gs = &meta->getset[i];

        meta->getset[i].name = strdup(PyUnicode_AsUTF8(f_name_obj));
        meta->getset[i].doc = NULL;
        meta->getset[i].closure = (void *) info;

        if (info->has_callback) {
            meta->getset[i].get = (getter)ProtoClass_getter;
            meta->getset[i].set = (setter)ProtoClass_setter;
        } else if (info->kind == KIND_INT) {
            if (info->bits == 0) {
                switch (info->type_code) {
                    case 1:
                        meta->getset[i].get = (getter)getter_u8;
                        meta->getset[i].set = (setter)setter_u8;
                        break;
                    case -1:
                        meta->getset[i].get = (getter)getter_i8;
                        meta->getset[i].set = (setter)setter_i8;
                        break;
                    case 2:
                        meta->getset[i].get = info->big_endian ? (getter)getter_u16_be : (getter)getter_u16_le;
                        meta->getset[i].set = info->big_endian ? (setter)setter_u16_be : (setter)setter_u16_le;
                        break;
                    case -2:
                        meta->getset[i].get = info->big_endian ? (getter)getter_i16_be : (getter)getter_i16_le;
                        meta->getset[i].set = info->big_endian ? (setter)setter_i16_be : (setter)setter_i16_le;
                        break;
                    case 4:
                        meta->getset[i].get = info->big_endian ? (getter)getter_u32_be : (getter)getter_u32_le;
                        meta->getset[i].set = info->big_endian ? (setter)setter_u32_be : (setter)setter_u32_le;
                        break;
                    case -4:
                        meta->getset[i].get = info->big_endian ? (getter)getter_i32_be : (getter)getter_i32_le;
                        meta->getset[i].set = info->big_endian ? (setter)setter_i32_be : (setter)setter_i32_le;
                        break;
                    case 8:
                        meta->getset[i].get = info->big_endian ? (getter)getter_u64_be : (getter)getter_u64_le;
                        meta->getset[i].set = info->big_endian ? (setter)setter_u64_be : (setter)setter_u64_le;
                        break;
                    case -8:
                        meta->getset[i].get = info->big_endian ? (getter)getter_i64_be : (getter)getter_i64_le;
                        meta->getset[i].set = info->big_endian ? (setter)setter_i64_be : (setter)setter_i64_le;
                        break;
                    case 16:
                        meta->getset[i].get = info->big_endian ? (getter)getter_u128_be : (getter)getter_u128_le;
                        meta->getset[i].set = info->big_endian ? (setter)setter_u128_be : (setter)setter_u128_le;
                        break;
                    case -16:
                        meta->getset[i].get = info->big_endian ? (getter)getter_i128_be : (getter)getter_i128_le;
                        meta->getset[i].set = info->big_endian ? (setter)setter_i128_be : (setter)setter_i128_le;
                        break;

                    default:
                        meta->getset[i].get = (getter)getter_bytes;
                        meta->getset[i].set = (setter)setter_bytes;
                        break;
                }
            } else {
                meta->getset[i].get = (getter)ProtoClass_getter;
                meta->getset[i].set = (setter)ProtoClass_setter;
            }
        } else {
            meta->getset[i].get = (getter)getter_bytes;
            meta->getset[i].set = (setter)setter_bytes;
        }

        PyObject *capsule = PyCapsule_New(&meta->getset[i], "protoclass.getset", NULL);
        PyDict_SetItem(meta->field_map, f_name_obj, capsule);
        Py_DECREF(capsule);
    }

    if (vn > 0) {
        meta->members = PyMem_Calloc(vn + 1, sizeof(PyMemberDef));
        meta->var_defs = PyMem_Calloc(1, sizeof(VarDefs));
        if (!meta->var_defs) {
            TypeMeta_decref(meta);
            return PyErr_NoMemory();
        }
        meta->var_defs->size = vn;
        meta->var_defs->members_array = meta->members;
        meta->var_defs->array = PyMem_Calloc(vn, sizeof(VarFieldInfo));
        if (!meta->var_defs->array) {
            PyMem_Free(meta->var_defs);
            meta->var_defs = NULL;
            TypeMeta_decref(meta);
            return PyErr_NoMemory();
        }

        for (Py_ssize_t i = 0; i < vn; i++) {
            PyObject *tuple = PyList_GetItem(var_fields_list, i);
            VarFieldInfo *vf = &meta->var_defs->array[i];
            PyObject *branches_list = NULL;
            if (!PyArg_ParseTuple(tuple, "OiOniOOOiiiiinOOOOi",
                &vf->name, &vf->align, &vf->length_field, &vf->length_offset, &vf->length_multiplier,
                &vf->type_field, &vf->type_map, &vf->item_type, &vf->big_endian, &vf->is_list,
                &vf->item_kind, &vf->item_bits, &vf->item_is_signed, &vf->item_fixed_size,
                &vf->fixed_length, &vf->to_python, &vf->from_python, &branches_list, &vf->has_callback)) {
                TypeMeta_decref(meta);
                return NULL;
            }
            vf->index = i;
            Py_XINCREF(vf->name);
            Py_XINCREF(vf->length_field);
            Py_XINCREF(vf->type_field);
            Py_XINCREF(vf->type_map);
            Py_XINCREF(vf->item_type);
            Py_XINCREF(vf->fixed_length);
            Py_XINCREF(vf->to_python);
            Py_XINCREF(vf->from_python);

            if (vf->type_map == Py_None) { Py_DECREF(vf->type_map); vf->type_map = NULL; }
            if (vf->type_field == Py_None) { Py_DECREF(vf->type_field); vf->type_field = NULL; }
            if (vf->to_python == Py_None) { Py_DECREF(vf->to_python); vf->to_python = NULL; }
            if (vf->from_python == Py_None) { Py_DECREF(vf->from_python); vf->from_python = NULL; }
            if (vf->fixed_length == Py_None) { Py_DECREF(vf->fixed_length); vf->fixed_length = NULL; }
            if (vf->length_field == Py_None) { Py_DECREF(vf->length_field); vf->length_field = NULL; }
            if (vf->item_type == Py_None) { Py_DECREF(vf->item_type); vf->item_type = NULL; }

            meta->members[i].name = strdup(PyUnicode_AsUTF8(vf->name));
            meta->members[i].type = T_OBJECT;
            meta->members[i].offset = 0; // Not used as we use custom getter/setter
            meta->members[i].flags = 0;
            meta->members[i].doc = NULL;

            // Metadata now passed explicitly from Python
            if (vf->item_type && vf->item_type != Py_None && PyObject_HasAttr(vf->item_type, keys.from_buffer)) {
                 // Still need to get TypeMeta for ProtoClasses
                 TypeMeta *item_meta = _get_type_meta_safe((PyTypeObject *)vf->item_type);
                 (void)item_meta; // _get_type_meta_safe caches it
            }

            if (branches_list && branches_list != Py_None && PyList_Check(branches_list)) {
                vf->branch_count = PyList_Size(branches_list);
                if (vf->branch_count > 0) {
                    vf->branches = PyMem_Calloc(vf->branch_count, sizeof(*vf->branches));
                    for (Py_ssize_t b = 0; b < vf->branch_count; b++) {
                        PyObject *b_tuple = PyList_GetItem(branches_list, b);
                        if (PyTuple_Check(b_tuple)) {
                            _resolve_poly_info(b_tuple, &vf->branches[b].type_info);

                            // Compatibility: fixed_length/converters still need extraction for direct access
                            // though type_info has most of them now.
                            if (PyTuple_Size(b_tuple) >= 6) {
                                vf->branches[b].fixed_length = PyTuple_GetItem(b_tuple, 3); // FixedSize
                                vf->branches[b].to_python = PyTuple_GetItem(b_tuple, 4);   // BTP
                                vf->branches[b].from_python = PyTuple_GetItem(b_tuple, 5); // BFP
                                Py_XINCREF(vf->branches[b].fixed_length);
                                Py_XINCREF(vf->branches[b].to_python);
                                Py_XINCREF(vf->branches[b].from_python);
                                if (vf->branches[b].fixed_length == Py_None) { Py_DECREF(vf->branches[b].fixed_length); vf->branches[b].fixed_length = NULL; }
                                if (vf->branches[b].to_python == Py_None) { Py_DECREF(vf->branches[b].to_python); vf->branches[b].to_python = NULL; }
                                if (vf->branches[b].from_python == Py_None) { Py_DECREF(vf->branches[b].from_python); vf->branches[b].from_python = NULL; }
                            }
                        }
                    }
                }
            }

            // Populate getset for variable field
            Py_ssize_t gs_idx = n_fields + i;
            meta->getset[gs_idx].name = strdup(PyUnicode_AsUTF8(vf->name));
            meta->getset[gs_idx].get = (getter)ProtoClass_var_getter;
            meta->getset[gs_idx].set = (setter)ProtoClass_var_setter;
            meta->getset[gs_idx].closure = vf;
            meta->getset[gs_idx].doc = NULL;

            PyObject *capsule = PyCapsule_New(&meta->getset[gs_idx], "protoclass.getset", NULL);
            PyDict_SetItem(meta->field_map, vf->name, capsule);
            Py_DECREF(capsule);

            // Populate FieldMapping
            meta->field_mappings[gs_idx].name = vf->name;
            Py_INCREF(vf->name);
            meta->field_mappings[gs_idx].gs = &meta->getset[gs_idx];

            PyObject *idx_obj = PyLong_FromSsize_t(i);
            PyDict_SetItem(meta->var_map, vf->name, idx_obj);
            Py_DECREF(idx_obj);

            /* Pre-resolve type_map entries */
            if (vf->type_map && PyDict_Check(vf->type_map)) {
                vf->resolved_count = PyDict_Size(vf->type_map);
                if (vf->resolved_count > 0) {
                    vf->resolved_targets = PyMem_Calloc(vf->resolved_count, sizeof(PolyTypeInfo));
                    vf->resolved_keys = PyMem_Calloc(vf->resolved_count, sizeof(PyObject *));
                    PyObject *key, *val;
                    Py_ssize_t pos = 0;
                    Py_ssize_t k = 0;
                    if (vf->resolved_targets && vf->resolved_keys) {
                        while (PyDict_Next(vf->type_map, &pos, &key, &val)) {
                            Py_INCREF(key);
                            vf->resolved_keys[k] = key;
                            _resolve_poly_info(val, &vf->resolved_targets[k]);
                            k++;
                        }
                    }
                }
            }
        }

        // Phase 4: Link descriptors in variable fields for fast resolution
        if (vn > 0 && meta->var_defs) {
            for (Py_ssize_t i = 0; i < meta->var_defs->size; i++) {
                VarFieldInfo *vf = &meta->var_defs->array[i];
                if (vf->length_field && vf->length_field != Py_None) {
                    PyObject *capsule = PyDict_GetItem(meta->field_map, vf->length_field);
                    if (capsule) {
                        vf->length_field_gs = (PyGetSetDef *)PyCapsule_GetPointer(capsule, "protoclass.getset");
                    }
                    PyObject *lf_idx_obj = PyDict_GetItem(meta->var_map, vf->length_field);
                    if (lf_idx_obj) {
                        Py_ssize_t lf_idx = PyLong_AsSsize_t(lf_idx_obj);
                        if (lf_idx >= 0 && lf_idx < meta->var_defs->size) {
                            vf->length_field_vf = &meta->var_defs->array[lf_idx];
                        }
                    }
                }
                if (vf->type_field && vf->type_field != Py_None) {
                    PyObject *capsule = PyDict_GetItem(meta->field_map, vf->type_field);
                    if (capsule) {
                        vf->type_field_gs = (PyGetSetDef *)PyCapsule_GetPointer(capsule, "protoclass.getset");
                    }
                }
            }

            /* Mark fields that provide a length or type for another field so the
               offset resolver tolerates them not being materialized yet. */
            for (Py_ssize_t i = 0; i < meta->var_defs->size; i++) {
                VarFieldInfo *vf = &meta->var_defs->array[i];
                for (Py_ssize_t j = 0; j < meta->var_defs->size; j++) {
                    VarFieldInfo *other = &meta->var_defs->array[j];
                    if (other->length_field && other->length_field != Py_None &&
                        PyObject_RichCompareBool(vf->name, other->length_field, Py_EQ) == 1) {
                        vf->is_metadata = 1;
                        break;
                    }
                    if (other->type_field && other->type_field != Py_None &&
                        PyObject_RichCompareBool(vf->name, other->type_field, Py_EQ) == 1) {
                        vf->is_metadata = 1;
                        break;
                    }
                }
            }
        }

        meta->getset[n_fields + vn].name = NULL;
        meta->members[vn].name = NULL;
    } else {
        meta->getset[n_fields].name = NULL;
    }

    return PyCapsule_New(meta, "protoclass.type_meta", TypeMeta_capsule_destructor);
}

static PyMethodDef module_methods[] = {
    {"make_binary_type", make_binary_type, METH_VARARGS, NULL},
    {NULL}
};

static struct PyModuleDef cprotoclass_module = { PyModuleDef_HEAD_INIT, "protoclass._cprotoclass", NULL, -1, module_methods };

static PyMemberDef ProtoClass_members[] = {
    {"_buffer", T_OBJECT_EX, offsetof(ProtoClassObject, _buffer), READONLY, "Original buffer"},
    {"dict", T_OBJECT, offsetof(ProtoClassObject, dict), READONLY, "Instance dictionary"},
    {NULL}
};

static PyGetSetDef ProtoClass_getset[] = {
    {NULL}
};

static PyTypeObject ProtoClass_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "protoclass._cprotoclass.ProtoClass",
    .tp_doc = "Binary protocol buffer base class",
    .tp_basicsize = sizeof(ProtoClassObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_new = PyType_GenericNew,
    .tp_init = (initproc)ProtoClass_init,
    .tp_dealloc = (destructor)ProtoClass_dealloc,
    .tp_traverse = (traverseproc)ProtoClass_traverse,
    .tp_clear = (inquiry)ProtoClass_clear,
    .tp_methods = ProtoClass_methods,
    .tp_members = ProtoClass_members,
    .tp_as_buffer = &ProtoClass_as_buffer,
    .tp_getset = ProtoClass_getset,
    .tp_dictoffset = offsetof(ProtoClassObject, dict),
};

PyMODINIT_FUNC PyInit__cprotoclass(void) {
    init_interned_keys();

    /* Set up ProtoClassMeta_Type (Dynamic Heap Type) */
    ProtoClassMeta_spec.basicsize = sizeof(ProtoClassMetaInstance);

    PyObject *meta_bases = PyTuple_Pack(1, &PyType_Type);
    if (!meta_bases) return NULL;

    ProtoClassMeta_TypePtr = (PyTypeObject*)PyType_FromSpecWithBases(&ProtoClassMeta_spec, meta_bases);
    Py_DECREF(meta_bases);

    if (!ProtoClassMeta_TypePtr) {
        PyErr_Print();
        return NULL;
    }

    /* ProtoClass type uses standard metaclass */

    /* Initialize ProtoClass type */
    if (PyType_Ready(&ProtoClass_Type) < 0) return NULL;

    ProtoClass_TypePtr = &ProtoClass_Type;

    PyObject *m = PyModule_Create(&cprotoclass_module);
    if (!m) return NULL;


    Py_INCREF(ProtoClass_TypePtr);
    PyModule_AddObject(m, "ProtoClass", (PyObject *)ProtoClass_TypePtr);
    Py_INCREF(ProtoClassMeta_TypePtr);
    PyModule_AddObject(m, "ProtoClassMeta", (PyObject *)ProtoClassMeta_TypePtr);



    PyObject *struct_mod = PyImport_ImportModule("struct");
    if (struct_mod) {
        StructError = PyObject_GetAttrString(struct_mod, "error");
        Py_DECREF(struct_mod);
    }
    if (!StructError) {
        StructError = PyExc_RuntimeError;
    }

    PyModule_AddIntConstant(m, "KIND_BYTES", KIND_BYTES);
    PyModule_AddIntConstant(m, "KIND_INT", KIND_INT);
    PyModule_AddIntConstant(m, "KIND_PROTOCLASS", KIND_PROTOCLASS);
    PyModule_AddIntConstant(m, "KIND_STRING", KIND_STRING);
    PyModule_AddIntConstant(m, "KIND_UNION", KIND_UNION);

    PyObject *types_mod = PyImport_ImportModule("routesia.protoclass.types");
    if (types_mod) {
        NullTerminatedString_Class = PyObject_GetAttrString(types_mod, "NullTerminatedString");
        Py_XDECREF(types_mod);
    }

    return m;
}
