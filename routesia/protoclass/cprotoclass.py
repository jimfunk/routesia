import ipaddress
import sys
from typing import (
    Annotated,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)
from enum import Enum, IntEnum, IntFlag

from . import _cprotoclass

from .types import (
    Integer,
    VariableLengthData,
    FixedLengthData,
    NullTerminatedString,
)


class TypeKind(IntEnum):
    BYTES = _cprotoclass.KIND_BYTES
    INT = _cprotoclass.KIND_INT
    PROTOCLASS = _cprotoclass.KIND_PROTOCLASS
    STRING = _cprotoclass.KIND_STRING
    UNION = _cprotoclass.KIND_UNION


class ProtoClass(_cprotoclass.ProtoClass):
    __slots__ = ()


def make_union_dispatcher(branches_meta):
    def union_to_python(data):
        for (
            kind,
            bits,
            signed,
            fixed_size,
            to_python,
            from_python,
            cls,
            big_endian,
        ) in branches_meta:
            if fixed_size and fixed_size == len(data):
                if to_python:
                    try:
                        return to_python(data)
                    except Exception:
                        continue
                return data
        return data

    return union_to_python


def make_union_serializer(branches_meta):
    def union_from_python(value):
        errors = []
        for (
            kind,
            bits,
            signed,
            fixed_size,
            to_python,
            from_python,
            cls,
            big_endian,
        ) in branches_meta:
            try:
                if from_python:
                    res = from_python(value)
                    if isinstance(res, (bytes, bytearray)):
                        if fixed_size and len(res) != fixed_size:
                            continue
                        return res
                elif kind == TypeKind.PROTOCLASS and isinstance(
                    value, (dict, cls, _cprotoclass.ProtoClass)
                ):
                    obj = cls(**value) if isinstance(value, dict) else value
                    res = bytes(obj)
                    if fixed_size and len(res) != fixed_size:
                        continue
                    return res
                elif kind == TypeKind.INT and isinstance(value, (int, Enum)):
                    byte_len = (bits + 7) // 8
                    try:
                        return int(value).to_bytes(
                            byte_len, "big" if big_endian else "little", signed=signed
                        )
                    except (OverflowError, ValueError):
                        continue
                elif kind == TypeKind.BYTES and isinstance(value, (bytes, bytearray)):
                    if fixed_size and len(value) != fixed_size:
                        continue
                    return bytes(value)
            except Exception as e:
                errors.append(e)
                continue
        raise TypeError(
            f"Could not serialize {value!r} to any Union branch. Errors: {errors}"
        )

    return union_from_python


def resolve_field_type(h):
    origin, args = get_origin(h), get_args(h)
    uint_meta = None
    fixed_meta = None
    variable_meta = None
    has_null_term = h is NullTerminatedString

    if origin is Annotated:
        for arg in args[1:]:
            if isinstance(arg, Integer):
                uint_meta = uint_meta or arg
            elif isinstance(arg, FixedLengthData):
                fixed_meta = fixed_meta or arg
            elif isinstance(arg, VariableLengthData):
                variable_meta = variable_meta or arg
            elif get_origin(arg) is Annotated:
                (
                    _,
                    inner_uint,
                    inner_fixed,
                    inner_variable,
                    inner_null,
                ) = resolve_field_type(arg)
                uint_meta = uint_meta or inner_uint
                fixed_meta = fixed_meta or inner_fixed
                variable_meta = variable_meta or inner_variable
                has_null_term = has_null_term or inner_null

        (
            inner_type,
            inner_uint,
            inner_fixed,
            inner_variable,
            inner_null,
        ) = resolve_field_type(args[0])

        res_uint = uint_meta or inner_uint
        res_fixed = fixed_meta or inner_fixed
        res_var = variable_meta or inner_variable

        if res_fixed and inner_fixed:
            res_fixed.to_python = res_fixed.to_python or inner_fixed.to_python
            res_fixed.from_python = res_fixed.from_python or inner_fixed.from_python
            if hasattr(res_fixed, "item_type") and hasattr(inner_fixed, "item_type"):
                res_fixed.item_type = res_fixed.item_type or inner_fixed.item_type
        if res_var and inner_variable:
            res_var.to_python = res_var.to_python or inner_variable.to_python
            res_var.from_python = res_var.from_python or inner_variable.from_python
            if hasattr(res_var, "item_type") and hasattr(inner_variable, "item_type"):
                res_var.item_type = res_var.item_type or inner_variable.item_type

        return (inner_type, res_uint, res_fixed, res_var, has_null_term or inner_null)

    if origin is Union or (
        hasattr(sys, "modules")
        and "types" in sys.modules
        and origin is getattr(sys.modules["types"], "UnionType", None)
    ):
        stripped_args = []
        has_branch_meta = False
        for arg in args:
            (
                stripped_type,
                branch_uint,
                branch_fixed,
                branch_variable,
                branch_null,
            ) = resolve_field_type(arg)
            if get_origin(stripped_type) is Union or (
                hasattr(sys, "modules")
                and "types" in sys.modules
                and get_origin(stripped_type)
                is getattr(sys.modules["types"], "UnionType", None)
            ):
                raise TypeError(f"Nested unions are prohibited: {h!r}")

            is_proto = isinstance(stripped_type, type) and issubclass(
                stripped_type, (ProtoClass, _cprotoclass.ProtoClass)
            )
            if not (
                branch_uint
                or branch_fixed
                or branch_variable
                or branch_null
                or is_proto
            ):
                raise TypeError(
                    f"Field {arg!r} is ambiguous and lacks rigid Protoclass metadata."
                )

            stripped_args.append(stripped_type)
            if branch_uint or branch_fixed or branch_variable or branch_null:
                has_branch_meta = True

        return (
            Union[tuple(stripped_args)],
            None,
            None,
            VariableLengthData() if has_branch_meta else None,
            False,
        )

    if isinstance(h, Integer):
        return int, h, None, None, False
    if isinstance(h, FixedLengthData):
        return bytes, None, h, None, False
    if isinstance(h, VariableLengthData):
        return bytes, None, None, h, False

    if isinstance(h, type) and issubclass(h, (ProtoClass, _cprotoclass.ProtoClass)):
        fs = getattr(h, "_fixed_size", 0)
        has_vars = hasattr(h, "_c_type_meta") or getattr(h, "_var_field_names", None)
        if has_vars:
            return (h, None, None, VariableLengthData(item_type=h), False)
        else:
            return (h, None, FixedLengthData(length=fs, item_type=h), None, False)

    return h, None, None, None, False


def resolve_binary_info(hint, byteorder="little"):
    is_big = byteorder == "big"
    (
        real_type,
        uint_meta,
        fixed_meta,
        variable_meta,
        has_null_term,
    ) = resolve_field_type(hint)
    origin = get_origin(hint) or getattr(hint, "__origin__", hint)
    bits = 0
    signed = False
    to_python = None
    from_python = None

    if uint_meta:
        bits = uint_meta.bits
        signed = uint_meta.signed
        to_python = getattr(uint_meta, "to_python", None)
        from_python = getattr(uint_meta, "from_python", None)

    if isinstance(real_type, type) and issubclass(real_type, (IntEnum, IntFlag)):
        for base in real_type.__mro__:
            if (
                hasattr(base, "bits")
                and hasattr(base, "signed")
                and base is not real_type
            ):
                bits = bits or getattr(base, "bits", 0)
                signed = getattr(base, "signed", signed)
        if not to_python:
            to_python = lambda x, rt=real_type: rt(x)
        if not from_python:
            from_python = int
        if bits == 0:
            raise TypeError(
                f"Enum {real_type!r} lacks rigid Protoclass metadata (bits)."
            )

    if real_type is ipaddress.IPv4Address:
        to_python = to_python or ipaddress.IPv4Address
        from_python = from_python or (lambda x: x.packed)
        fixed_meta = fixed_meta or FixedLengthData(4)
    elif real_type is ipaddress.IPv6Address:
        to_python = to_python or ipaddress.IPv6Address
        from_python = from_python or (lambda x: x.packed)
        fixed_meta = fixed_meta or FixedLengthData(16)

    if fixed_meta:
        to_python = to_python or getattr(fixed_meta, "to_python", None)
        from_python = from_python or getattr(fixed_meta, "from_python", None)
    if variable_meta:
        to_python = to_python or getattr(variable_meta, "to_python", None)
        from_python = from_python or getattr(variable_meta, "from_python", None)

    marker = uint_meta or fixed_meta or variable_meta
    kind = None
    fixed_size = 0
    check_type = real_type if origin is Annotated else origin
    check_origin = get_origin(check_type) or check_type
    is_union = check_origin is Union or (
        hasattr(sys, "modules")
        and "types" in sys.modules
        and check_origin is getattr(sys.modules["types"], "UnionType", None)
    )

    if is_union:
        kind = TypeKind.UNION
        union_branches = []
        for branch_hint in flatten_union(hint):
            (
                b_kind,
                b_marker,
                b_bits,
                b_signed,
                b_fixed_size,
                b_to_python,
                b_from_python,
                b_real_type,
                b_has_null,
            ) = resolve_binary_info(branch_hint, byteorder=byteorder)
            union_branches.append(
                (
                    b_kind,
                    b_bits,
                    b_signed,
                    b_fixed_size,
                    b_to_python,
                    b_from_python,
                    b_real_type,
                    1 if is_big else 0,
                )
            )
        to_python = make_union_dispatcher(union_branches)
        from_python = make_union_serializer(union_branches)
    elif isinstance(real_type, type) and issubclass(
        real_type, (ProtoClass, _cprotoclass.ProtoClass)
    ):
        kind = TypeKind.PROTOCLASS
        fixed_size = getattr(real_type, "_fixed_size", 0)
    elif isinstance(marker, FixedLengthData):
        kind = TypeKind.BYTES
        fixed_size = marker.length
        bits = 0
    elif isinstance(marker, Integer) or bits > 0:
        kind = TypeKind.INT
        fixed_size = (bits + 7) // 8
    elif has_null_term:
        kind = TypeKind.STRING
    elif isinstance(marker, VariableLengthData):
        kind = TypeKind.BYTES
    elif check_origin is list or check_origin is List:
        # Fallback for generic lists
        kind = TypeKind.BYTES

    if kind is None:
        raise TypeError(
            f"Field with hint {hint!r} is ambiguous and lacks rigid Protoclass metadata."
        )

    return (
        kind,
        marker,
        bits,
        1 if signed else 0,
        fixed_size,
        to_python,
        from_python,
        real_type,
        has_null_term,
    )


def flatten_union(h):
    origin = get_origin(h)
    if origin is Union or (
        hasattr(sys, "modules")
        and "types" in sys.modules
        and origin is getattr(sys.modules["types"], "UnionType", None)
    ):
        return get_args(h)
    if origin is Annotated:
        inner = get_args(h)[0]
        if get_origin(inner) is Union or (
            hasattr(sys, "modules")
            and "types" in sys.modules
            and get_origin(inner) is getattr(sys.modules["types"], "UnionType", None)
        ):
            return get_args(inner)
    return [h]


class ProtoclassMeta(_cprotoclass.ProtoClassMeta):
    def __new__(metaclass, cls_name, bases, dct, byteorder="native"):
        if cls_name == "ProtoClass" or cls_name.startswith("C_"):
            return super().__new__(metaclass, cls_name, bases, dct)

        annotations = {}
        if current_anns := dct.get("__annotations__", {}):
            try:
                f_globals = sys._getframe(2).f_globals
            except ValueError:
                f_globals = sys._getframe(1).f_globals
            annotations.update(
                get_type_hints(
                    type(cls_name, (object,), {"__annotations__": current_anns}),
                    include_extras=True,
                    globalns=f_globals,
                )
            )

        processed = set()
        defaults = {}
        metadata_fields = set()
        for hint in annotations.values():
            _, _, _, vm, _ = resolve_field_type(hint)
            if vm:
                if vm.length_field:
                    metadata_fields.add(vm.length_field)
                if vm.type_field:
                    metadata_fields.add(vm.type_field)

        c_fields = []
        var_fields_list = []
        current_offset = 0
        bit_queue = []
        is_big = byteorder == "big"
        seen_variable = False  # Track if we've seen a variable field

        def flush_bits():
            nonlocal current_offset, seen_variable
            if not bit_queue:
                return
            total = sum(b_bit["bits"] for b_bit in bit_queue)
            container_size = (
                8
                if total <= 8
                else (
                    16
                    if total <= 16
                    else (32 if total <= 32 else (64 if total <= 64 else 128))
                )
            )
            curr_bit = container_size
            for b_info in bit_queue:
                curr_bit -= b_info["bits"]
                has_cb = 1 if (b_info["to_python"] or b_info["from_python"]) else 0
                
                # If we've seen a variable field, this bitfield needs runtime offset
                if seen_variable:
                    # Add as variable field with placeholder offset
                    var_fields_list.append((
                        b_info["name"],
                        1,  # align
                        None,  # length_field
                        0,  # length_offset
                        1,  # length_multiplier
                        None,  # type_field
                        None,  # type_map
                        None,  # item_type
                        is_big,
                        False,  # is_list
                        TypeKind.INT,
                        b_info["bits"],
                        0,  # signed
                        container_size // 8,  # fixed_size
                        None,  # cls
                        b_info["to_python"],
                        b_info["from_python"],
                        [],  # branches
                        has_cb,
                    ))
                else:
                    c_fields.append(
                        (
                            b_info["name"],
                            current_offset,
                            container_size // 8,
                            curr_bit,
                            b_info["bits"],
                            1 if is_big else 0,
                            TypeKind.INT,
                            has_cb,
                            1 if b_info["name"] in metadata_fields else 0,
                            b_info["to_python"],
                            b_info["from_python"],
                        )
                    )
            current_offset += container_size // 8
            bit_queue.clear()

        for f_name, hint in annotations.items():
            if f_name in processed:
                continue
            processed.add(f_name)
            if f_name in dct and not isinstance(dct[f_name], property):
                defaults[f_name] = dct[f_name]

            (
                kind,
                marker,
                bits,
                signed,
                fixed_size,
                to_python,
                from_python,
                real_type,
                has_null_term,
            ) = resolve_binary_info(hint, byteorder=byteorder)

            if bits > 0 and (bits % 8 != 0):
                bit_queue.append(
                    {
                        "name": f_name,
                        "bits": bits,
                        "to_python": to_python,
                        "from_python": from_python,
                    }
                )
                if sum(b["bits"] for b in bit_queue) % 8 == 0:
                    flush_bits()
                continue
            flush_bits()

            if kind == TypeKind.INT and bits > 0:
                type_code = {1: 1, 2: 2, 4: 4, 8: 8, 16: 16}.get(bits // 8, 0) or (
                    bits // 8
                )
                if signed:
                    type_code = -type_code
                has_cb = 1 if (to_python or from_python) else 0
                
                if seen_variable:
                    # Add as variable field with placeholder offset
                    var_fields_list.append((
                        f_name,
                        1,  # align
                        None,  # length_field
                        0,  # length_offset
                        1,  # length_multiplier
                        None,  # type_field
                        None,  # type_map
                        None,  # item_type
                        is_big,
                        False,  # is_list
                        TypeKind.INT,
                        bits,
                        1 if signed else 0,
                        bits // 8,  # fixed_size
                        None,  # cls
                        to_python,
                        from_python,
                        [],  # branches
                        has_cb,
                    ))
                else:
                    c_fields.append(
                        (
                            f_name,
                            current_offset,
                            type_code,
                            0,  # bit_pos
                            0,  # bits
                            1 if is_big else 0,
                            TypeKind.INT,
                            has_cb,
                            1 if f_name in metadata_fields else 0,
                            to_python,
                            from_python,
                        )
                    )
                    current_offset += bits // 8
                continue

            branches = []
            real_hint = hint
            if get_origin(hint) is Annotated:
                real_hint = get_args(hint)[0]
            is_union_field = get_origin(real_hint) is Union or (
                hasattr(sys, "modules")
                and "types" in sys.modules
                and get_origin(real_hint)
                is getattr(sys.modules["types"], "UnionType", None)
            )
            if is_union_field:
                union_branches = []
                for branch_hint in flatten_union(hint):
                    (
                        b_kind,
                        b_marker,
                        b_bits,
                        b_signed,
                        b_fixed_size,
                        b_to_python,
                        b_from_python,
                        b_real_type,
                        b_has_null,
                    ) = resolve_binary_info(branch_hint, byteorder=byteorder)
                    # C expects (kind, bits, signed, fixed_size, to_python, from_python, cls, big_endian)
                    union_branches.append(
                        (
                            b_kind,
                            b_bits,
                            b_signed,
                            b_fixed_size,
                            b_to_python,
                            b_from_python,
                            b_real_type,
                            1 if is_big else 0,
                        )
                    )
                branches = union_branches

            fixed_meta = marker if isinstance(marker, FixedLengthData) else None
            variable_meta = marker if isinstance(marker, VariableLengthData) else None

            if fixed_meta:
                if fixed_meta.length <= 0:
                    raise TypeError(
                        f"FixedLengthData for field {f_name!r} must have length > 0"
                    )
                has_cb = 1 if (to_python or from_python) else 0
                
                if seen_variable:
                    # Add as variable field with placeholder offset
                    var_fields_list.append((
                        f_name,
                        1,  # align
                        None,  # length_field
                        0,  # length_offset
                        1,  # length_multiplier
                        None,  # type_field
                        None,  # type_map
                        None,  # item_type
                        is_big,
                        False,  # is_list
                        TypeKind.BYTES,
                        0,  # bits
                        0,  # signed
                        fixed_meta.length,  # fixed_size
                        None,  # cls
                        to_python,
                        from_python,
                        [],  # branches
                        has_cb,
                    ))
                else:
                    c_fields.append(
                        (
                            f_name,
                            current_offset,
                            fixed_meta.length,
                            0,  # bit_pos
                            0,  # bits
                            1 if is_big else 0,
                            TypeKind.BYTES,
                            has_cb,
                            1 if f_name in metadata_fields else 0,
                            to_python,
                            from_python,
                        )
                    )
                    current_offset += fixed_meta.length
            elif variable_meta or has_null_term or kind == TypeKind.PROTOCLASS:
                # For protoclass types, length is determined by the protoclass itself
                variable_meta = variable_meta or VariableLengthData()
                is_list = get_origin(real_type) is list or real_type is list

                if kind != TypeKind.PROTOCLASS:
                    # Lists with item_type need length_field unless they're the tail
                    if (is_list or variable_meta.item_type) and not variable_meta.length_field:
                        if f_name != list(annotations.keys())[-1]:
                            raise TypeError(
                                f"Variable length field {f_name!r} must specify 'length_field' unless it is the tail."
                            )
                final_type_map = None
                if variable_meta.type_map:
                    tm_items = []
                    for k, v in variable_meta.type_map.items():
                        (
                            v_kind,
                            v_marker,
                            v_bits,
                            v_signed,
                            v_fixed_size,
                            v_to_python,
                            v_from_python,
                            v_real_type,
                            v_has_null,
                        ) = resolve_binary_info(v, byteorder=byteorder)
                        tm_items.append(
                            (
                                k,
                                (
                                    v_kind,
                                    v_bits,
                                    v_signed,
                                    v_fixed_size,
                                    v_to_python,
                                    v_from_python,
                                    v_real_type,
                                    1 if is_big else 0,
                                ),
                            )
                        )
                    final_type_map = dict(tm_items)

                list_kind = kind
                list_bits = bits
                list_signed = signed
                list_fixed_size = fixed_size
                list_real_type = real_type
                if is_list and variable_meta.item_type:
                    (
                        item_kind,
                        item_marker,
                        item_bits,
                        item_signed,
                        item_fixed_size,
                        item_to_python,
                        item_from_python,
                        item_real_type,
                        item_has_null,
                    ) = resolve_binary_info(variable_meta.item_type)
                    list_kind = item_kind
                    list_bits = item_bits
                    list_signed = item_signed
                    list_fixed_size = item_fixed_size
                    if item_real_type is not None:
                        list_real_type = item_real_type
                    if not to_python and item_to_python:
                        to_python = item_to_python
                    if not from_python and item_from_python:
                        from_python = item_from_python

                has_cb = 1 if (to_python or from_python) else 0
                var_fields_list.append(
                    (
                        f_name,
                        variable_meta.align,
                        variable_meta.length_field,
                        variable_meta.length_offset,
                        variable_meta.length_multiplier,
                        variable_meta.type_field,
                        final_type_map,
                        list_real_type,
                        is_big,
                        is_list,
                        list_kind,
                        list_bits,
                        1 if list_signed else 0,
                        list_fixed_size,
                        None,
                        to_python,
                        from_python,
                        branches,
                        has_cb,
                    )
                )
                seen_variable = True  # Mark that we've seen a variable field
            else:
                raise TypeError(
                    f"Field {f_name!r} is ambiguous and lacks rigid Protoclass metadata."
                )

        flush_bits()
        mod_name = dct.get("__module__", "routesia.protoclass.cprotoclass")
        meta_capsule = _cprotoclass.make_binary_type(
            f"{mod_name}.{cls_name}", c_fields, current_offset, var_fields_list
        )
        res_attrs = {
            "__module__": mod_name,
            "__annotations__": annotations,
            "_defaults": defaults,
            "_fixed_size": current_offset,
            "__slots__": (),
        }
        res_attrs.update(dct)
        res = type.__new__(_cprotoclass.ProtoClassMeta, cls_name, bases, res_attrs)
        res._c_type_meta = meta_capsule
        return res


def protoclass(byteorder: str = "native") -> Callable[[type], type]:
    def wrapper(cls: type) -> type:
        if isinstance(cls, ProtoclassMeta):
            return cls
        bases = cls.__bases__
        if ProtoClass not in bases and not any(
            issubclass(b, ProtoClass) for b in bases if isinstance(b, type)
        ):
            bases = (ProtoClass,) if bases == (object,) else bases + (ProtoClass,)
        d = dict(cls.__dict__)
        d.setdefault("__slots__", ())
        return ProtoclassMeta(cls.__name__, bases, d, byteorder=byteorder)

    return wrapper
