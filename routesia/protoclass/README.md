# Protoclass

Protoclass is a Python module that provides a way to define protocols that can be
serialized and deserialized to and from a buffer.

The primary purpose is for implementing network protocols, but can be used for things
like Linux netlink and even binary file formats.

The design is largely inspired by the `dataclasses` module, but with type annotations
to describe the layout of the data in buffers.

For example, for an IPv4 header we can do this:

```python
class IPv4Header(ProtoClass):
    version: UInt4 = 4
    ihl: UInt4 = 5
    tos: UInt8 = 0
    total_len: UInt16 = 0
    id: UInt16 = 0
    flags: UInt3 = 0
    frag_offset: UInt13 = 0
    ttl: UInt8 = 255
    protocol: UInt8 = 0
    checksum: UInt16 = 0
    src_ip: UInt32 = 0
    dst_ip: UInt32 = 0


ip = IPv4Header(
    src_ip=int(ipaddress.IPv4Address("10.1.1.1")),
    dst_ip=int(ipaddress.IPv4Address("10.1.1.2"))
)

serialized_ip = bytes(ip)

deserialized_ip = IPv4Header.from_buffer(serialized_ip)

assert deserialized_ip.src_ip == int(ipaddress.IPv4Address("10.1.1.1"))
```

Of course, we don't need to live with having to convert the IP addresses manually. We
can define them as fixed-width fields with conversion using type annotations:

```python

IPv4 = Annotated[
    ipaddress.IPv4Address,
    FixedLengthData(
        length=4,
        to_python=ipaddress.IPv4Address,
        from_python=lambda x: x.packed,
    ),
]


class IPv4Header(ProtoClass):
    version: UInt4 = 4
    ihl: UInt4 = 5
    tos: UInt8 = 0
    total_len: UInt16 = 0
    id: UInt16 = 0
    flags: UInt3 = 0
    frag_offset: UInt13 = 0
    ttl: UInt8 = 255
    protocol: UInt8 = 0
    checksum: UInt16 = 0
    src_ip: IPv4
    dst_ip: IPv4

ip = IPv4Header(
    src_ip=ipaddress.IPv4Address("10.1.1.1"),
    dst_ip=ipaddress.IPv4Address("10.1.1.2")
)

assert isinstance(ip.src_ip, ipaddress.IPv4Address)
```

For IPv4 and IPv6, the types are already defined in `protoclass.types` so we don't have
to define them ourselves in this case. The example was just for demonstration of how to
integrate your own types.

In fact, all of the annotations we use for protoclass have metadata to define the
information needed to serialize and deserialize the data:

```python
# protoclass/types.py

class Integer:
    """
    Metadata for protoclass integers.
    """

    def __init__(self, bits: int, signed: bool = False):
        self.bits = bits
        self.signed = signed

    def __repr__(self):
        return f"Integer({self.bits}, signed={self.signed})"


UInt8 = Annotated[int, Integer(8)]
Int8 = Annotated[int, Integer(8, signed=True)]
```

These annotations are a requirement since most Python types do not have a fixed size.
It would be impossible to figure out how large a standard Python integer is since it
can be arbitrarily large. Binary representations of integers generally need a fixed
size so that the alignment of the fields are known. In fact, if you attempted to use an
annotation without protoclass metadata, it will raise an error.

Fixed length buffer fields are supported of course:

```python
class MyMessage(ProtoClass):
    version: UInt8 = 1
    payload: Annotated[
        bytes,
        FixedLengthData(length=10)
    ]
```

So are variable length fields, eg:

```python
class MyMessage(ProtoClass):
    version: UInt8 = 1
    payload_len: UInt8
    payload: Annotated[
        bytes,
        VariableLengthData(length_field="payload_len")
    ]
```

When reading a buffer, the `payload_len` field is read first, then the `payload`
field is read using the value of `payload_len`. When writing a buffer, the
`payload_len` is automatically updated to the length of `payload`.

Sometimes, the length of a variable length field is not stored in a previous field, but
is simply appended after the previous fields and read up until the end of the input
buffer, for example:

```python
class MyMessage(ProtoClass):
    first_data_len: UInt16
    first_data: Annotated[
        bytes,
        VariableLengthData(length_field="first_data_len")
    ]
    last_data: Annotated[bytes, VariableLengthData()]
```

Note that this works in protoclass even though it follows another variable length field
and is not at a fixed offset.

Unions are also supported in many cases, for example:

```python

# These are already defined in protoclass.types and are here for demonstration purposes
IPv4 = Annotated[
    ipaddress.IPv4Address,
    FixedLengthData(
        length=4,
        to_python=ipaddress.IPv4Address,
        from_python=lambda x: x.packed,
    ),
]

IPv6 = Annotated[
    ipaddress.IPv6Address,
    FixedLengthData(
        length=16,
        to_python=ipaddress.IPv6Address,
        from_python=lambda x: x.packed,
    ),
]

class MyMessage(ProtoClass):
    version: UInt8 = 1
    payload_len: UInt8
    payload: Annotated[
        IPv4 | IPv6,
        VariableLengthData(length_field="payload_len")
    ]
```

When reading a buffer, each branch of the union is tried in order until one
matches the data in the buffer. If all fail, an error is raised.

Sometimes, a header may have a type field to denote the type of data in a variable
length field. Protoclass helps encode and decode such structures using a type_map.

For example:

```python

class PayloadType(IntEnum):
    TYPE_A = 0
    TYPE_B = 1
    TYPE_C = 2


class MyMessage(Protoclass):
    length: UInt8
    type: Annotated[PayloadType, UInt8]
    payload: Annotated[
        UInt8 | UInt16 | UInt32,
        VariableLengthData(
            length_field="length",
            type_field="type",
            type_map={
                PayloadType.TYPE_A: UInt8,
                PayloadType.TYPE_B: UInt16,
                PayloadType.TYPE_C: UInt32,
            }
        )
    ]
```

If a length field is used, but does not directly match the length of the actual data in
the field, conversion is possible:

```python

class MyMessage(Protoclass):
    length: UInt8  # Length of entire message in bytes
    type: Annotated[PayloadType, UInt8]
    payload: Annotated[
        UInt8 | UInt16 | UInt32,
        VariableLengthData(
            length_field="length",
            length_offset=-8,  # Subtract the length of the previous fields
            type_map={
                PayloadType.TYPE_A: UInt8,
                PayloadType.TYPE_B: UInt16,
                PayloadType.TYPE_C: UInt32,
            }
        )
    ]
```

Length multipliers are also supported:

```python

class MyMessage(Protoclass):
    length: UInt8  # Length of payload in 4-byte words
    payload: Annotated[
        bytes,
        VariableLengthData(
            length_field="length",
            length_multiplier=4,  # Multiply by 4
        )
    ]
```


Alignment is also supported, where the payload is padded with zeros to the nearest
alignment boundary:

```python

class MyMessage(Protoclass):
    length: UInt8
    payload: Annotated[
        bytes,
        VariableLengthData(
            length_field="length",
            alignment=4,  # Align to multiple of 4 bytes, padding if necessary
        )
    ]
```
