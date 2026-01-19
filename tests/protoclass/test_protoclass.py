import pytest

import ipaddress
import struct
from typing import Annotated, List, Union
from enum import IntEnum, IntFlag
import sys

from tests.buffers import HexBuffer

from routesia.protoclass import (
    protoclass,
    ProtoClass,
    NullTerminatedString,
    VariableLengthData,
    VariableData,
    FixedLengthData,
    IPv4,
    IPv6,
    Bytes,
    typed_field,
    Integer,
    UInt1,
    UInt4,
    UInt7,
    UInt8,
    UInt16,
    UInt24,
    UInt32,
    UInt60,
    UInt64,
    UInt128,
    Int8,
    Int16,
    Int32,
    Int128,
    UInt8Base,
)


class TestFixedSizeStructs:
    """Tests for basic fixed-size struct serialization and deserialization."""

    def test_fixed_size_struct(self):

        @protoclass(byteorder="big")
        class FixedStruct:
            f1: Annotated[int, UInt32]
            f2: Annotated[int, UInt16]
            f3: Annotated[int, UInt8]

        data = HexBuffer(
            # fmt: off
            "00 00 00 01"
            "00 02"
            "03"
            # fmt: on
        )
        obj = FixedStruct.from_bytes(data)
        assert obj.f1 == 1
        assert obj.f2 == 2
        assert obj.f3 == 3
        assert obj.to_bytes() == data
        assert bytes(obj) == data
        assert len(obj) == 7

    def test_struct_with_defaults(self):

        @protoclass(byteorder="big")
        class DefaultStruct:
            f1: Annotated[int, UInt32] = 0x12345678
            f2: Annotated[int, UInt16] = 0xABCD

        obj = DefaultStruct()
        assert obj.f1 == 0x12345678
        assert obj.f2 == 0xABCD
        assert obj.to_bytes() == HexBuffer("12 34 56 78 ab cd")

    def test_default_values(self):

        @protoclass(byteorder="big")
        class BaseD:
            f1: Annotated[int, UInt8] = 0xAA
            f2: Annotated[int, UInt8] = 0xBB

        b = BaseD()
        assert b.f1 == 0xAA
        assert b.f2 == 0xBB
        assert b.to_bytes() == HexBuffer("aa bb")

    def test_big_endian_types(self):

        @protoclass(byteorder="big")
        class BEG:
            a: Annotated[int, UInt16]
            b: Annotated[int, Integer(128)]

        val128 = (1 << 127) | 1
        obj = BEG(a=0x1234, b=val128)
        data = obj.to_bytes()
        assert data[0:2] == HexBuffer("12 34")
        assert data[2:18] == val128.to_bytes(16, "big")

        obj2 = BEG.from_bytes(data)
        assert obj2.a == 0x1234
        assert obj2.b == val128

    def test_int128_support(self):

        @protoclass(byteorder="big")
        class LargeInt:
            u128: Annotated[int, UInt128]
            i128: Annotated[int, Int128]

        v_u = (1 << 127) + (1 << 64) + 123
        v_i = -(1 << 120) + 456

        obj = LargeInt(u128=v_u, i128=v_i)
        data = obj.to_bytes()
        assert len(data) == 32

        obj2 = LargeInt.from_bytes(data)
        assert obj2.u128 == v_u
        assert obj2.i128 == v_i


class TestBitFields:
    """Tests for bit field packing and boundary handling."""

    def test_bitfield_boundaries(self):

        @protoclass(byteorder="big")
        class Bits:
            a: Annotated[int, UInt1]
            b: Annotated[int, UInt7]
            c: Annotated[int, UInt16]

        b = Bits.from_bytes(HexBuffer("81 ff ff"))
        assert b.a == 1
        assert b.b == 1
        assert b.c == 0xFFFF
        assert len(b.to_bytes()) == 3  # Densely packed

        b.a = 3
        b.b = 130
        assert b.a == 1
        assert b.b == 2

    def test_bitfield_spanning_64bit(self):

        @protoclass(byteorder="big")
        class BigBits:
            f1: Annotated[int, UInt60]
            f2: Annotated[int, UInt4]

        raw = struct.pack(">Q", (0xFFFFFFFFFFFFFFF << 4) | 0xA)
        b = BigBits.from_bytes(raw)
        assert b.f1 == 0xFFFFFFFFFFFFFFF
        assert b.f2 == 0xA

    def test_bit_spanning(self):

        @protoclass()
        class LargeBitfield2:
            a: Annotated[int, Integer(100)]
            b: Annotated[int, Integer(28)]

        lb2 = LargeBitfield2(a=(1 << 99), b=1)
        assert lb2.a == (1 << 99)
        assert lb2.b == 1
        assert len(lb2) == 16

    def test_large_bitfield(self):

        @protoclass()
        class LargeBitfield:
            a: Annotated[int, Integer(64)]
            b: Annotated[int, Integer(64)]

        # This should trigger the 128-bit container logic
        data = (1 << 127) | (1 << 63) | 1
        # Trigger bytearray conversion in 128-bit setter
        lb = LargeBitfield.from_bytes(HexBuffer("00") * 16)
        lb.a = data >> 64
        lb.b = data & ((1 << 64) - 1)

        assert lb.a == data >> 64
        assert lb.b == data & ((1 << 64) - 1)

    def test_bitfield_rounding(self):

        # This should test the bit_queue flushing logic more thoroughly
        @protoclass()
        class Rounded:
            a: Annotated[int, Integer(7)]
            # This should flush the 7 bits into a 1-byte container
            b: Annotated[int, UInt32]

        obj = Rounded(a=0x3F, b=0x12345678)
        data = obj.to_bytes()
        assert len(data) == 5
        assert data[0] == 0x7E


class TestFixedLengthData:
    """Tests for fixed-length data fields with type conversion (IPv4, IPv6, callbacks)."""

    def test_ipv4_address_type(self):

        @protoclass(byteorder="big")
        class IPStruct:
            src: Annotated[
                ipaddress.IPv4Address,
                FixedLengthData(
                    4,
                    to_python=ipaddress.IPv4Address,
                    from_python=lambda a: a.packed,
                ),
            ]
            dst: Annotated[
                ipaddress.IPv4Address,
                FixedLengthData(
                    4,
                    to_python=ipaddress.IPv4Address,
                    from_python=lambda a: a.packed,
                ),
            ]

        obj = IPStruct(
            src=ipaddress.IPv4Address("1.2.3.4"), dst=ipaddress.IPv4Address("5.6.7.8")
        )
        assert obj.src == ipaddress.IPv4Address("1.2.3.4")
        assert obj.to_bytes() == HexBuffer("01 02 03 04 05 06 07 08")

        obj2 = IPStruct.from_bytes(HexBuffer("7f 00 00 01 00 00 00 00"))
        assert obj2.src == ipaddress.IPv4Address("127.0.0.1")
        assert obj2.dst == ipaddress.IPv4Address("0.0.0.0")

        # Trigger bytearray conversion
        obj2.src = ipaddress.IPv4Address("10.0.0.1")
        assert obj2.src == ipaddress.IPv4Address("10.0.0.1")
        assert obj2.to_bytes()[0:4] == HexBuffer("0a 00 00 01")

    def test_ipv6_serialization_in_typemap(self):

        @protoclass(byteorder="big")
        class IPContainer6:
            type: Annotated[int, UInt16]
            len: Annotated[int, UInt16]
            payload: Annotated[
                Union[Bytes, IPv6],
                VariableData(
                    length_field="len",
                    length_offset=-4,
                    type_field="type",
                    type_map={2: IPv6},
                    align=4,
                ),
            ]

        # Test serialization of IPv6Address
        # type=2, len=20 (2+2+16), payload=2001:db8::1
        addr = ipaddress.IPv6Address("2001:db8::1")
        obj = IPContainer6(type=2, payload=addr)
        assert len(obj) == 20
        data = obj.to_bytes()
        assert len(data) == 20
        assert data[0:2] == HexBuffer("00 02")
        assert data[2:4] == HexBuffer("00 14")
        assert data[4:] == addr.packed

        # Test deserialization
        obj2 = IPContainer6.from_bytes(data)
        assert obj2.type == 2
        assert isinstance(obj2.payload, ipaddress.IPv6Address)
        assert obj2.payload == addr

    def test_ipv4_serialization_in_typemap(self):

        @protoclass(byteorder="big")
        class IPContainer:
            type: Annotated[int, UInt16]
            len: Annotated[int, UInt16]
            payload: Annotated[
                Union[Bytes, IPv4],
                VariableData(
                    length_field="len",
                    length_offset=-4,
                    type_field="type",
                    type_map={1: IPv4},
                    align=4,
                ),
            ]

        # Test serialization of IPv4Address
        # type=1, len=8 (2+2+4), payload=10.0.0.1
        obj = IPContainer(type=1, payload=ipaddress.IPv4Address("10.0.0.1"))
        data = obj.to_bytes()
        assert len(data) == 8
        assert data[0:2] == HexBuffer("00 01")
        assert data[2:4] == HexBuffer("00 08")
        assert data[4:8] == HexBuffer("0a 00 00 01")  # 10.0.0.1

        # Test deserialization
        obj2 = IPContainer.from_bytes(data)
        assert obj2.type == 1
        assert isinstance(obj2.payload, ipaddress.IPv4Address)
        assert obj2.payload == ipaddress.IPv4Address("10.0.0.1")

    def test_ipv4_property_assignment(self):
        @protoclass()
        class IPv4Packet:
            addr: IPv4

        addr = ipaddress.IPv4Address("1.1.1.1")
        packet = IPv4Packet(addr=addr)
        assert bytes(packet) == HexBuffer("01 01 01 01")
        assert packet.addr == addr

    def test_ipv6_property_assignment(self):
        @protoclass()
        class IPv6Packet:
            addr: IPv6

        addr = ipaddress.IPv6Address("::1")
        packet = IPv6Packet(addr=addr)
        expected = HexBuffer("00") * 15 + HexBuffer("01")
        assert bytes(packet) == expected
        assert packet.addr == addr

    def test_fixed_length_data_callbacks(self):
        @protoclass()
        class ConvStruct:
            addr: Annotated[
                ipaddress.IPv4Address,
                FixedLengthData(
                    4,
                    to_python=ipaddress.IPv4Address,
                    from_python=lambda x: ipaddress.IPv4Address(x).packed,
                ),
            ]

        obj = ConvStruct(addr=ipaddress.IPv4Address("1.2.3.4"))
        assert obj.addr == ipaddress.IPv4Address("1.2.3.4")
        assert obj.to_bytes() == HexBuffer("01 02 03 04")

        obj2 = ConvStruct.from_bytes(HexBuffer("0a 00 00 01"))
        assert obj2.addr == ipaddress.IPv4Address("10.0.0.1")

    def test_invalid_ipv4_assignment(self):

        @protoclass()
        class IPv4Header:
            source_address: Annotated[
                ipaddress.IPv4Address,
                FixedLengthData(
                    4,
                    to_python=ipaddress.IPv4Address,
                    from_python=lambda a: a.packed,
                ),
            ] = ipaddress.IPv4Address("0.0.0.0")

        ip = IPv4Header()
        with pytest.raises(AttributeError):
            ip.source_address = "not an ip"


class TestVariableLengthData:
    """Tests for variable length data fields and auto-updating length fields."""

    def test_auto_updating_length_field(self):

        @protoclass(byteorder="big")
        class VariableStruct:
            length: Annotated[int, UInt16]
            data: Annotated[bytes, VariableData(length_field="length", length_offset=-2)]

        obj = VariableStruct(data=b"hello")
        buf = obj.to_bytes()
        assert obj.length == 7  # payload len 5 + header 2
        assert buf == HexBuffer("00 07 68 65 6c 6c 6f")

        obj.data = b"longer payload"
        buf2 = obj.to_bytes()
        assert obj.length == 16  # 14 + 2
        assert buf2 == HexBuffer("00 10 6c 6f 6e 67 65 72 20 70 61 79 6c 6f 61 64")

    def test_auto_updating_length_field_data_only(self):
        """
        Test that length field is auto-updated when it represents data length only
        (no length_offset). This verifies the common case where length field
        contains only the payload length, not including the header.
        """

        @protoclass(byteorder="big")
        class DataLengthStruct:
            length: Annotated[int, UInt16]
            data: Annotated[bytes, VariableData(length_field="length")]  # No offset

        # Test construction
        obj = DataLengthStruct(data=b"hello")
        assert obj.length == 5  # Just data length, not including header
        assert bytes(obj) == HexBuffer("00 05 68 65 6c 6c 6f")

        # Test modification
        obj.data = b"hi"
        assert obj.length == 2  # Auto-updated to new data length
        assert bytes(obj) == HexBuffer("00 02 68 69")

        # Test deserialization and re-serialization
        raw = HexBuffer("00 06 77 6f 72 6c 64 21")  # length=6, data="world!"
        obj2 = DataLengthStruct.from_bytes(raw)
        assert obj2.length == 6
        assert obj2.data == b"world!"

        # Modify and verify round-trip
        obj2.data = b"test"
        assert obj2.length == 4
        assert bytes(obj2) == HexBuffer("00 04 74 65 73 74")

    def test_variable_length_data_callbacks(self):
        @protoclass()
        class VarConvStruct:
            data: Annotated[
                str,
                VariableLengthData(
                    to_python=lambda x: x.decode(),
                    from_python=lambda x: x.encode(),
                ),
            ]

        obj = VarConvStruct(data="hello")
        assert obj.data == "hello"
        assert obj.to_bytes() == HexBuffer("68 65 6c 6c 6f")

        obj2 = VarConvStruct.from_bytes(HexBuffer("77 6f 72 6c 64"))
        assert obj2.data == "world"

    def test_null_terminated_string(self):

        @protoclass()
        class Item:
            s: Annotated[str, NullTerminatedString]

        buf = HexBuffer("68 65 6c 6c 6f 00 77 6f 72 6c 64")
        obj = Item.from_buffer(buf)
        assert obj.s == "hello"

        buf2 = HexBuffer("6e 6f 5f 6e 75 6c 6c")
        obj2 = Item.from_buffer(buf2)
        assert obj2.s == "no_null"

        buf3 = HexBuffer("00")
        obj3 = Item.from_buffer(buf3)
        assert obj3.s == ""

    def test_variable_serialization(self):

        @protoclass()
        class VarDataS:
            s: Annotated[str, NullTerminatedString]

        @protoclass()
        class VarDataL:
            l: Annotated[List[int], VariableData(item_type=UInt8)]

        # Test string serialization (hits .encode())
        obj_s = VarDataS(s="hello")
        assert HexBuffer("68 65 6c 6c 6f") in obj_s.to_bytes()

        # Test list and int-fallback serialization
        obj_l = VarDataL(l=[1, 2, 3])
        assert HexBuffer("01 02 03") in obj_l.to_bytes()


class TestUnionsAndTypeMaps:
    """Tests for union types and type map dispatching."""

    def test_polymorphic_payload(self):

        @protoclass(byteorder="big")
        class SubTypeA:
            val: Annotated[int, UInt16]

        @protoclass(byteorder="big")
        class Container:
            size: Annotated[int, UInt32]
            type: Annotated[int, UInt16]
            payload: Annotated[
                Union[Bytes, SubTypeA],
                VariableData(
                    length_field="size",
                    length_offset=-6,
                    type_field="type",
                    type_map={1: SubTypeA},
                ),
            ]

        # 1. Test bytes payload (unknown type)
        # header is 4(size) + 2(type) = 6 bytes.
        # If size=10, payload=4.
        raw_bytes = HexBuffer("00 00 00 0a 00 00 41 42 43 44")
        c1 = Container.from_bytes(raw_bytes)
        assert c1.type == 0
        assert c1.payload == HexBuffer("41 42 43 44")

        # 2. Test SubTypeA payload (type 1)
        # size 8, type 1, 2 bytes payload
        raw_subtype = HexBuffer("00 00 00 08 00 01 12 34")
        c2 = Container.from_bytes(raw_subtype)
        assert c2.type == 1
        assert isinstance(c2.payload, SubTypeA)
        assert c2.payload.val == 0x1234

    def test_variable_data_typemap(self):

        @protoclass()
        class TypeA:
            val: Annotated[int, UInt16]

        @protoclass()
        class TypeB:
            text: Annotated[bytes, VariableData()]

        @protoclass()
        class Dispatcher:
            type: Annotated[int, UInt8]
            payload: Annotated[
                Union[TypeA, TypeB],
                VariableData(type_field="type", type_map={1: TypeA, 2: TypeB}),
            ]

        d1 = Dispatcher.from_bytes(HexBuffer("01 39 05"))
        assert d1.type == 1
        assert isinstance(d1.payload, TypeA)
        assert d1.payload.val == 1337

        d2 = Dispatcher.from_bytes(HexBuffer("02") + b"hello")
        assert d2.type == 2
        assert isinstance(d2.payload, TypeB)
        assert d2.payload.text == b"hello"

    def test_try_each_union_dispatch(self):
        @protoclass(byteorder="big")
        class MultiProtocol:
            payload: (
                Annotated[
                    ipaddress.IPv4Address,
                    FixedLengthData(4, to_python=ipaddress.IPv4Address),
                ]
                | Annotated[
                    ipaddress.IPv6Address,
                    FixedLengthData(16, to_python=ipaddress.IPv6Address),
                ]
                | Bytes
            )

        # 1. IPv4 match
        obj4 = MultiProtocol.from_bytes(HexBuffer("01 02 03 04"))
        assert obj4.payload == ipaddress.IPv4Address("1.2.3.4")

        # 2. IPv6 match
        obj6 = MultiProtocol.from_bytes(HexBuffer("00") * 15 + HexBuffer("01"))
        assert obj6.payload == ipaddress.IPv6Address("::1")

        # 3. Fallback to bytes
        obj_raw = MultiProtocol.from_bytes(HexBuffer("68 65 6c 6c 6f"))
        assert obj_raw.payload == b"hello"

    def test_type_map_none_fallback(self):
        @protoclass(byteorder="big")
        class FallbackStruct:
            type: Annotated[int, UInt8]
            payload: Annotated[
                Union[UInt32, Bytes],
                VariableLengthData(type_field="type", type_map={1: UInt32, None: Bytes}),
            ]

        # Type 1 matches UInt32
        obj1 = FallbackStruct.from_bytes(HexBuffer("01 12 34 56 78"))
        assert obj1.payload == 0x12345678

        # Type 2 falls back to bytes
        obj2 = FallbackStruct.from_bytes(HexBuffer("02") + b"hello")
        assert obj2.payload == b"hello"

    def test_typed_field_helper_basic(self):
        PayloadType = typed_field(type_field="type", type_map={1: UInt32, 2: Bytes})

        @protoclass(byteorder="big")
        class HelperStruct:
            type: Annotated[int, UInt8]
            payload: PayloadType

        obj = HelperStruct.from_bytes(HexBuffer("01 00 00 00 0a"))
        assert obj.payload == 10

        obj2 = HelperStruct.from_bytes(HexBuffer("02") + b"world")
        assert obj2.payload == b"world"


class TestTypeMapWithAnnotatedTypes:
    """Tests for type maps with non-Protoclass annotated types (IPv4, IPv6, custom types)."""

    def test_type_map_with_ipv4_annotated_type(self):
        """
        Test that type_map supports annotated IPv4 type, not just Protoclass classes.
        """

        @protoclass(byteorder="big")
        class IPTypeDispatcher:
            type: Annotated[int, UInt8]
            payload: Annotated[
                IPv4,
                VariableData(type_field="type", type_map={1: IPv4}),
            ]

        # Type 1 should deserialize as IPv4Address
        obj = IPTypeDispatcher.from_bytes(HexBuffer("01 0a 00 00 01"))
        assert obj.type == 1
        assert isinstance(obj.payload, ipaddress.IPv4Address)
        assert obj.payload == ipaddress.IPv4Address("10.0.0.1")

        # Serialization
        obj2 = IPTypeDispatcher(type=1, payload=ipaddress.IPv4Address("192.168.1.1"))
        assert bytes(obj2) == HexBuffer("01 c0 a8 01 01")

    def test_type_map_with_ipv6_annotated_type(self):
        """
        Test that type_map supports annotated IPv6 type.
        """

        @protoclass(byteorder="big")
        class IPv6TypeDispatcher:
            type: Annotated[int, UInt8]
            payload: Annotated[
                IPv6,
                VariableData(type_field="type", type_map={1: IPv6}),
            ]

        addr = ipaddress.IPv6Address("2001:db8::1")
        obj = IPv6TypeDispatcher.from_bytes(HexBuffer("01") + addr.packed)
        assert obj.type == 1
        assert isinstance(obj.payload, ipaddress.IPv6Address)
        assert obj.payload == addr

        # Serialization
        obj2 = IPv6TypeDispatcher(type=1, payload=addr)
        assert bytes(obj2) == HexBuffer("01") + addr.packed

    def test_type_map_with_fixed_length_data_annotated_type(self):
        """
        Test that type_map supports custom FixedLengthData annotated types.
        """

        # Custom 8-byte fixed length type with conversion
        CustomID = Annotated[
            int,
            FixedLengthData(
                8,
                to_python=lambda b: int.from_bytes(b, "big"),
                from_python=lambda i: i.to_bytes(8, "big"),
            ),
        ]

        @protoclass(byteorder="big")
        class CustomTypeDispatcher:
            type: Annotated[int, UInt8]
            payload: Annotated[
                int,
                VariableData(type_field="type", type_map={1: CustomID}),
            ]

        # Type 1 should deserialize as int using the custom converter
        obj = CustomTypeDispatcher.from_bytes(HexBuffer("01 00 00 00 00 00 00 00 2a"))
        assert obj.type == 1
        assert isinstance(obj.payload, int)
        assert obj.payload == 42

        # Serialization
        obj2 = CustomTypeDispatcher(type=1, payload=0x123456789ABCDEF0)
        assert bytes(obj2) == HexBuffer("01 12 34 56 78 9a bc de f0")

    def test_type_map_with_null_terminated_string(self):
        """
        Test that type_map supports NullTerminatedString annotated type.
        """

        @protoclass()
        class StringDispatcher:
            type: Annotated[int, UInt8]
            payload: Annotated[
                str,
                VariableData(type_field="type", type_map={1: NullTerminatedString}),
            ]

        # Type 1 should deserialize as null-terminated string
        obj = StringDispatcher.from_bytes(HexBuffer("01 68 65 6c 6c 6f 00"))
        assert obj.type == 1
        assert isinstance(obj.payload, str)
        assert obj.payload == "hello"

        # Serialization
        obj2 = StringDispatcher(type=1, payload="world")
        assert bytes(obj2) == HexBuffer("01 77 6f 72 6c 64 00")

    def test_type_map_with_multiple_annotated_types(self):
        """
        Test type_map with multiple different annotated types in one dispatcher.
        """

        @protoclass(byteorder="big")
        class MultiTypeDispatcher:
            type: Annotated[int, UInt8]
            payload: Annotated[
                Union[IPv4, IPv6, NullTerminatedString],
                VariableData(
                    type_field="type",
                    type_map={1: IPv4, 2: IPv6, 3: NullTerminatedString},
                ),
            ]

        # Test IPv4
        obj4 = MultiTypeDispatcher.from_bytes(HexBuffer("01 c0 a8 01 01"))
        assert obj4.type == 1
        assert isinstance(obj4.payload, ipaddress.IPv4Address)
        assert obj4.payload == ipaddress.IPv4Address("192.168.1.1")

        # Test IPv6
        addr6 = ipaddress.IPv6Address("fe80::1")
        obj6 = MultiTypeDispatcher.from_bytes(HexBuffer("02") + addr6.packed)
        assert obj6.type == 2
        assert isinstance(obj6.payload, ipaddress.IPv6Address)
        assert obj6.payload == addr6

        # Test string
        objstr = MultiTypeDispatcher.from_bytes(HexBuffer("03 74 65 73 74 00"))
        assert objstr.type == 3
        assert isinstance(objstr.payload, str)
        assert objstr.payload == "test"

    def test_type_map_with_integer_types(self):
        """
        Test that type_map supports Integer annotated types (UInt16, UInt32, etc).
        """

        @protoclass(byteorder="big")
        class IntDispatcher:
            type: Annotated[int, UInt8]
            payload: Annotated[
                int,
                VariableData(type_field="type", type_map={1: UInt16, 2: UInt32}),
            ]

        # Type 1 = UInt16
        obj1 = IntDispatcher.from_bytes(HexBuffer("01 12 34"))
        assert obj1.type == 1
        assert isinstance(obj1.payload, int)
        assert obj1.payload == 0x1234

        # Type 2 = UInt32
        obj2 = IntDispatcher.from_bytes(HexBuffer("02 12 34 56 78"))
        assert obj2.type == 2
        assert isinstance(obj2.payload, int)
        assert obj2.payload == 0x12345678

        # Serialization
        obj3 = IntDispatcher(type=1, payload=0xABCD)
        assert bytes(obj3) == HexBuffer("01 ab cd")

        obj4 = IntDispatcher(type=2, payload=0xDEADBEEF)
        assert bytes(obj4) == HexBuffer("02 de ad be ef")


class TestAlignment:
    """Tests for field alignment and padding in structures."""

    def test_alignment_and_typemap(self):

        @protoclass(byteorder="big")
        class Header:
            type: Annotated[int, UInt16]
            len: Annotated[int, UInt16]
            payload: Annotated[
                Union[Bytes, UInt32],
                VariableData(
                    length_field="len",
                    length_offset=-4,
                    type_field="type",
                    type_map={1: UInt32},
                    align=4,
                ),
            ]

        # 1. Test unaligned payload (bytes)
        # len=1, payload=b"A", should be padded to 4 bytes in buffer but from_buffer should respect len.
        raw_unaligned = HexBuffer(
            "00 02 00 05 41 00 00 00"
        )  # type 2, len 5, payload 'A', 3 bytes pad
        obj = Header.from_bytes(raw_unaligned)
        assert obj.payload == HexBuffer("41")

        # 2. Test aligned payload (UInt32)
        raw_aligned = HexBuffer(
            "00 01 00 08 12 34 56 78"
        )  # type 1, len 8, payload 0x12345678
        obj2 = Header.from_bytes(raw_aligned)
        assert obj2.payload == 0x12345678

    def test_aligned_list_items(self):

        @protoclass(byteorder="big")
        class AlignedItem:
            val: Annotated[int, UInt8]

        @protoclass(byteorder="big")
        class Container:
            # Items are 1 byte each, but we force 2-byte alignment for EACH ITEM
            items: Annotated[
                List[AlignedItem], VariableData(item_type=AlignedItem, align=2)
            ]

        # items=[AlignedItem(1), AlignedItem(2)]
        # Each item: 1 byte data + 1 byte padding = 2 bytes.
        # Total 4 bytes.
        c = Container(items=[AlignedItem(val=1), AlignedItem(val=2)])
        data = c.to_bytes()
        assert len(data) == 4
        assert data[0] == 1
        assert data[1] == 0  # padding
        assert data[2] == 2
        assert data[3] == 0  # padding

        c2 = Container.from_bytes(data)
        assert len(c2.items) == 2
        assert c2.items[0].val == 1
        assert c2.items[1].val == 2

    def test_aligned_list_items_struct(self):

        # Mimics NlAttr structure with dynamic length but no manual __len__
        @protoclass(byteorder="native")
        class VarItem:
            len: Annotated[int, UInt16]
            # Payload size depends on len
            payload: Annotated[bytes, VariableData(length_field="len", length_offset=-2)]

        @protoclass(byteorder="native")
        class Container:
            # Items must be aligned to 4 bytes
            items: Annotated[List[VarItem], VariableData(item_type=VarItem, align=4)]

        # Item 1: Header 2 bytes + Payload 1 byte ("A") = 3 bytes.
        # Aligned to 4 -> 1 byte padding.
        item1 = VarItem(payload=b"A")
        # Item 2: Header 2 bytes + Payload 5 bytes ("BBBBB") = 7 bytes.
        # Aligned to 4 -> 1 byte padding.
        item2 = VarItem(payload=b"BBBBB")

        c = Container(items=[item1, item2])
        data = c.to_bytes()

        # Verify serialized data structure
        # Item 1: 03 00 [41] [00] (len=3, payload=A, pad=0)
        # Item 2: 07 00 [42 42 42 42 42] [00] (len=7, payload=BBBBB, pad=0)
        # Total: 4 + 8 = 12 bytes
        assert len(data) == 12
        assert data[0:2] == HexBuffer("03 00")
        assert data[2:4] == HexBuffer("41 00")
        assert data[4:6] == HexBuffer("07 00")
        assert data[6:11] == b"BBBBB"
        assert data[11] == 0

        # Verify Parsing
        c2 = Container.from_bytes(data)
        assert len(c2.items) == 2
        assert c2.items[0].payload == b"A"
        assert c2.items[1].payload == b"BBBBB"

        @protoclass(byteorder="big")
        class IntHeader:
            type: Annotated[int, UInt16]
            len: Annotated[int, UInt16]
            payload: Annotated[
                Union[Bytes, UInt32],
                VariableData(
                    length_field="len",
                    length_offset=-4,
                    type_field="type",
                    type_map={1: UInt32},
                    align=4,
                ),
            ]

        # Test serialization of native int (UInt32)
        # type=1, len=8 (2+2+4), payload=0x12345678
        obj = IntHeader(type=1, payload=0x12345678)
        assert len(obj) == 8
        data = obj.to_bytes()
        assert len(data) == 8
        assert data[0:2] == HexBuffer("00 01")  # type
        assert data[2:4] == HexBuffer("00 08")  # len
        assert data[4:8] == HexBuffer("12 34 56 78")  # payload

        # Test deserialization
        obj2 = IntHeader.from_bytes(data)
        assert obj2.type == 1
        assert obj2.payload == 0x12345678
        assert isinstance(obj2.payload, int)

    def test_alignment_manual(self):

        @protoclass(byteorder="native")
        class Aligned:
            a: Annotated[int, UInt8]
            _pad: Annotated[int, UInt24] = 0
            b: Annotated[int, UInt32]

        assert Aligned._fixed_size == 8
        obj = Aligned(a=1, b=2)
        assert len(obj.to_bytes()) == 8

    def test_multiple_variable_fields_with_alignment(self):

        @protoclass()
        class MultiVar:
            len1: Annotated[int, UInt8]
            var1: Annotated[bytes, VariableData(length_field="len1", align=4)]
            var2: Annotated[bytes, VariableData(align=8)]

        # var1 length 2, aligned to 4 -> 4 bytes
        # var2 length 3, aligned to 8 -> 8 bytes
        mv = MultiVar(var1=b"ab", var2=b"cde")
        b = mv.to_bytes()
        assert mv.len1 == 2
        # 1 (len1) + 4 (var1 + pad) + 8 (var2 + pad) = 13
        assert len(b) == 13

        mv2 = MultiVar.from_bytes(b)
        assert mv2.var1 == HexBuffer("61 62")
        assert mv2.var2.rstrip(b"\x00") == b"cde"


class TestListsAndNestedStructures:
    """Tests for lists, nested structures, and complex nested polymorphism."""

    def test_nested_variable_data(self):

        @protoclass()
        class SubItem:
            len: Annotated[int, UInt8]
            data: Annotated[bytes, VariableData(length_field="len")]

        @protoclass()
        class RootContainer:
            count: Annotated[int, UInt8]
            items: Annotated[List[SubItem], VariableData(item_type=SubItem)]

        raw = HexBuffer("02")
        raw += HexBuffer("03 41 42 43")
        raw += HexBuffer("01 58")

        c = RootContainer.from_bytes(raw)
        assert len(c.items) == 2
        assert c.items[0].data == HexBuffer("41 42 43")
        assert c.items[1].data == HexBuffer("58")

    def test_nested_polymorphism_in_list(self):

        @protoclass()
        class SubItem:
            type: Annotated[int, UInt8]
            payload: Annotated[
                Union[Bytes, UInt32],
                VariableData(
                    type_field="type",
                    type_map={1: UInt32},
                ),
            ]

        @protoclass()
        class Container:
            items: Annotated[List[SubItem], VariableData(item_type=SubItem, align=4)]

        # 1. Test creation and serialization
        item1 = SubItem(type=1, payload=0x12345678)
        item2 = SubItem(type=2, payload=b"hello")
        c = Container(items=[item1, item2])
        data = c.to_bytes()

        # 2. Test deserialization
        c2 = Container.from_bytes(data)
        assert len(c2.items) == 2
        assert c2.items[0].type == 1
        assert c2.items[0].payload == 0x12345678
        assert c2.items[1].type == 2
        assert c2.items[1].payload.rstrip(b"\x00") == b"hello"

    def test_netlink_style_nesting_and_alignment(self):
        """
        Specifically tests the case of nested Protoclass structures with 4-byte
        alignment, mimicking the complexity of a Netlink LinkInfo attribute.
        """

        @protoclass()
        class NestedAttr:
            rta_len: Annotated[int, UInt16]
            rta_type: Annotated[int, UInt16]
            payload: Annotated[
                Union[Bytes, NullTerminatedString],
                VariableData(
                    length_field="rta_len",
                    length_offset=-4,
                    type_field="rta_type",
                    type_map={1: NullTerminatedString},
                    align=4,
                ),
            ]

        @protoclass()
        class ListContainer:
            attrs: Annotated[list[NestedAttr], VariableData(item_type=NestedAttr, align=4)]

        @protoclass()
        class RootAttr:
            rta_len: Annotated[int, UInt16]
            rta_type: Annotated[int, UInt16]
            payload: Annotated[
                Union[Bytes, ListContainer],
                VariableData(
                    length_field="rta_len",
                    length_offset=-4,
                    type_field="rta_type",
                    type_map={10: ListContainer},
                    align=4,
                ),
            ]

        @protoclass()
        class RootMessage:
            family: Annotated[int, UInt8]
            _pad: Annotated[int, UInt8] = 0
            type: Annotated[int, UInt16]
            index: Annotated[int, UInt32]
            flags: Annotated[int, UInt32]
            change: Annotated[int, UInt32]
            attrs: Annotated[list[RootAttr], VariableData(item_type=RootAttr, align=4)]

        # 1. Construct the message
        msg = RootMessage(family=2, type=1, index=42, flags=1, change=0)

        # Nested LinkInfo-style structure
        lc = ListContainer()
        lc.attrs.append(
            NestedAttr(rta_type=1, payload="vlan")
        )  # "vlan\0" (5) + 4 = 9. Aligned 12.

        msg.attrs.append(RootAttr(rta_type=10, payload=lc))  # 12 + 4 = 16. Aligned 16.
        msg.attrs.append(RootAttr(rta_type=3, payload=b"eth0\0"))  # 5 + 4 = 9. Aligned 12.

        # header: 16
        # attr1: payload is lc. lc has 1 NestedAttr.
        # NestedAttr: type=1, payload="vlan" -> NullTerminatedString.
        # payload="vlan\0" (5) -> len 5+4 = 9. Aligned 4 -> 12.
        # NestedAttr rta_len=9.
        # ListContainer has 12 bytes.
        # RootAttr(type=10, payload=lc): rta_len = 16 (12+4). Aligned 4 -> 16.
        # RootAttr(type=3, payload=b"eth0\0"): rta_len = 9 (5+4). Aligned 4 -> 12.
        # Total: 16 + 16 + 12 = 44.
        data = msg.to_bytes()
        # The C extension currently doesn't add padding AFTER the last attribute in a list if not explicitly requested?
        # Actually, it should align each item.
        assert len(data) == 44

        # 2. Verify Decoding
        msg2 = RootMessage.from_bytes(data)
        assert msg2.family == 2
        assert msg2.index == 42
        assert len(msg2.attrs) == 2

        # Check Root Attr 1 (Nested List)
        attr1 = msg2.attrs[0]
        assert attr1.rta_type == 10
        assert isinstance(attr1.payload, ListContainer)
        assert len(attr1.payload.attrs) == 1
        assert attr1.payload.attrs[0].payload == "vlan"

        # Check Root Attr 2 (Bytes)
        attr2 = msg2.attrs[1]
        assert attr2.rta_type == 3
        assert attr2.payload == b"eth0\0"

        # 3. Verify modifications still work and maintain alignment
        msg2.attrs[1].payload = b"longer_name\0"  # "longer_name\0" (12) + 4 = 16.
        # Total should be 16 + 16 + 16 = 48.
        data2 = msg2.to_bytes()
        assert len(data2) == 48
        msg3 = RootMessage.from_bytes(data2)
        assert msg3.attrs[1].payload == b"longer_name\0"

    def test_list_of_integers(self):
        """
        Test serialization of lists for all fixed-width integer types.
        """

        # UInt16 list (little-endian)
        @protoclass(byteorder="little")
        class UInt16List:
            items: Annotated[List[int], VariableLengthData(item_type=UInt16)]

        data = b"\x01\x00\x02\x00\x03\x00"  # Little-endian [1, 2, 3]
        obj = UInt16List.from_bytes(data)
        assert obj.items == [1, 2, 3]
        assert bytes(obj) == data

        # UInt32 list (little-endian)
        @protoclass(byteorder="little")
        class UInt32List:
            items: Annotated[List[int], VariableLengthData(item_type=UInt32)]

        data = b"\x01\x00\x00\x00\x02\x00\x00\x00\x03\x00\x00\x00"
        obj = UInt32List.from_bytes(data)
        assert obj.items == [1, 2, 3]
        assert bytes(obj) == data

        # UInt64 list (little-endian)
        @protoclass(byteorder="little")
        class UInt64List:
            items: Annotated[List[int], VariableLengthData(item_type=UInt64)]

        data = b"\x01\x00\x00\x00\x00\x00\x00\x00" b"\x02\x00\x00\x00\x00\x00\x00\x00"
        obj = UInt64List.from_bytes(data)
        assert obj.items == [1, 2]
        assert bytes(obj) == data

        # Int8 list (signed) - byte order doesn't matter for single bytes
        @protoclass()
        class Int8List:
            items: Annotated[List[int], VariableLengthData(item_type=Int8)]

        data = b"\x7f\x80\xff"  # [127, -128, -1]
        obj = Int8List.from_bytes(data)
        assert obj.items == [127, -128, -1]
        assert bytes(obj) == data

        # Int16 list (signed, little-endian)
        @protoclass(byteorder="little")
        class Int16List:
            items: Annotated[List[int], VariableLengthData(item_type=Int16)]

        # Little-endian: [32767, -32768, -1] = 0x7fff, 0x8000, 0xffff
        data = b"\xff\x7f\x00\x80\xff\xff"
        obj = Int16List.from_bytes(data)
        assert obj.items == [32767, -32768, -1]
        assert bytes(obj) == data

        # Int32 list (signed, little-endian)
        @protoclass(byteorder="little")
        class Int32List:
            items: Annotated[List[int], VariableLengthData(item_type=Int32)]

        # Little-endian: [2147483647, -2147483648, -1]
        data = b"\xff\xff\xff\x7f\x00\x00\x00\x80\xff\xff\xff\xff"
        obj = Int32List.from_bytes(data)
        assert obj.items == [2147483647, -2147483648, -1]
        assert bytes(obj) == data

    def test_list_of_primitives_big_endian(self):
        """Test serialization of lists with big-endian byte order."""

        @protoclass(byteorder="big")
        class BigEndianList:
            items: Annotated[List[int], VariableLengthData(item_type=UInt16)]

        data = b"\x00\x01\x00\x02\x00\x03"  # Big-endian [1, 2, 3]
        obj = BigEndianList.from_bytes(data)
        assert obj.items == [1, 2, 3]
        assert bytes(obj) == data

    def test_list_of_primitives_empty(self):
        """Test serialization of empty list."""

        @protoclass()
        class EmptyList:
            items: Annotated[List[int], VariableLengthData(item_type=UInt8)]

        data = b""
        obj = EmptyList.from_bytes(data)
        assert obj.items == []
        assert bytes(obj) == data

    def test_list_of_primitives_large_values(self):
        """Test serialization of lists with maximum values."""

        @protoclass()
        class MaxValList:
            items: Annotated[List[int], VariableLengthData(item_type=UInt32)]

        data = b"\xff\xff\xff\xff" * 3  # [0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF]
        obj = MaxValList.from_bytes(data)
        assert obj.items == [0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF]
        assert bytes(obj) == data

    def test_list_of_fixed_length_bytes(self):
        """Test serialization of lists with fixed-length bytes (e.g., IPv4, IPv6, FixedLengthData)."""

        # List of IPv4 addresses (4 bytes each)
        @protoclass()
        class IPv4List:
            items: Annotated[
                List[ipaddress.IPv4Address], VariableLengthData(item_type=IPv4)
            ]

        data = b"\x0a\x00\x00\x01\x0a\x00\x00\x02\x0a\x00\x00\x03"
        obj = IPv4List.from_bytes(data)
        assert obj.items == [
            ipaddress.IPv4Address("10.0.0.1"),
            ipaddress.IPv4Address("10.0.0.2"),
            ipaddress.IPv4Address("10.0.0.3"),
        ]
        assert bytes(obj) == data

        # List of IPv6 addresses (16 bytes each)
        @protoclass()
        class IPv6List:
            items: Annotated[
                List[ipaddress.IPv6Address], VariableLengthData(item_type=IPv6)
            ]

        addr1 = ipaddress.IPv6Address("2001:db8::1")
        addr2 = ipaddress.IPv6Address("2001:db8::2")
        data = addr1.packed + addr2.packed
        obj = IPv6List.from_bytes(data)
        assert obj.items == [addr1, addr2]
        assert bytes(obj) == data

        # List of custom fixed-length bytes
        @protoclass()
        class FixedBytesList:
            items: Annotated[
                List[bytes],
                VariableLengthData(item_type=Annotated[bytes, FixedLengthData(length=4)]),
            ]

        data = b"ABCD" + b"EFGH" + b"IJKL"
        obj = FixedBytesList.from_bytes(data)
        assert obj.items == [b"ABCD", b"EFGH", b"IJKL"]
        assert bytes(obj) == data


class TestEnumsAndIntFlag:
    """Tests for Enum and IntFlag field handling."""

    def test_enum_casting(self):
        @protoclass()
        class EnumStruct:
            val: SampleEnum
            bit_val: Annotated[SampleEnum, UInt4]
            _pad: Annotated[int, UInt4] = 0

        s = EnumStruct(val=SampleEnum.VAL1, bit_val=SampleEnum.VAL2)
        assert s.val == SampleEnum.VAL1
        assert s.bit_val == SampleEnum.VAL2
        assert isinstance(s.val, SampleEnum)
        assert isinstance(s.bit_val, SampleEnum)
        assert bytes(s) == HexBuffer("01 20")

        s = EnumStruct.from_bytes(HexBuffer("02 10"))
        assert s.val == SampleEnum.VAL2
        assert s.bit_val == SampleEnum.VAL1
        assert isinstance(s.val, SampleEnum)
        assert isinstance(s.bit_val, SampleEnum)

    def test_intflag_field_and_offset(self):
        @protoclass(byteorder="big")
        class FlagStruct:
            flags: Annotated[MyFlags, UInt8]
            next_val: Annotated[int, UInt16]

        # Structure:
        # flags: 1 byte (0x03 -> FLAG_A | FLAG_B)
        # next_val: 2 bytes (0x1234)
        # Total: 3 bytes

        raw = HexBuffer("03 12 34")

        obj = FlagStruct.from_bytes(raw)

        # Check flags
        assert obj.flags == MyFlags.FLAG_A | MyFlags.FLAG_B
        assert isinstance(obj.flags, MyFlags)

        # Check next value - this fails if offsets are wrong
        # If flags was ignored, next_val might be read from offset 0 or have other issues
        assert obj.next_val == 0x1234

        # Check serialization
        assert obj.to_bytes() == raw


class SampleEnum(UInt8Base, IntEnum):
    VAL1 = 1
    VAL2 = 2


class MyFlags(UInt8Base, IntFlag):
    NONE = 0
    FLAG_A = 1
    FLAG_B = 2
    FLAG_C = 4


class TestTypeRigidity:
    """Tests for explicit type annotation requirements and type rigidity."""

    def test_implicit_int_fails(self):
        with pytest.raises(
            TypeError, match="ambiguous and lacks rigid Protoclass metadata"
        ):

            @protoclass()
            class FailMsg:
                f: int

    def test_implicit_bytes_fails(self):
        with pytest.raises(
            TypeError, match="ambiguous and lacks rigid Protoclass metadata"
        ):

            @protoclass()
            class FailMsg:
                f: bytes

    def test_implicit_union_branch_fails(self):
        with pytest.raises(TypeError, match="lacks rigid Protoclass metadata"):

            @protoclass()
            class FailMsg:
                f: Annotated[Union[int, Bytes], FixedLengthData(length=4)]

    def test_explicit_int_works(self):
        @protoclass()
        class SuccessMsg:
            f: UInt32

        m = SuccessMsg(f=123)
        assert bytes(m) == HexBuffer("7b 00 00 00")

    def test_explicit_bytes_works(self):
        @protoclass()
        class SuccessMsg:
            f: Bytes

        m = SuccessMsg(f=b"abc")
        assert bytes(m) == HexBuffer("61 62 63")

    def test_union_bytes(self):
        m = UnionMsg(type=2, payload=b"hello")
        assert m.length == 13
        assert bytes(m) == HexBuffer("0d 00 00 00 02 00 00 00") + b"hello"

    def test_union_int_works(self):
        m = UnionMsg(type=1, payload=0x12345678)
        data = bytes(m)
        assert len(data) == 12
        assert data[8:] == HexBuffer("78 56 34 12")
        assert m.length == 12

    def test_generic_union_int(self):
        m = GenericUnionMsg(type=1, payload=0x11223344)
        data = bytes(m)
        assert len(data) == 12
        assert m.length == 12


@protoclass()
class UnionMsg(ProtoClass):
    length: UInt32
    type: UInt32
    payload: Annotated[
        Union[UInt32, Bytes],
        VariableLengthData(
            length_field="length",
            length_offset=-8,
            type_field="type",
            type_map={1: UInt32, 2: Bytes},
        ),
    ]


@protoclass()
class GenericUnionMsg(ProtoClass):
    length: UInt32
    type: UInt32
    payload: Annotated[
        Union[UInt32, Bytes],
        VariableLengthData(
            length_field="length",
            length_offset=-8,
            type_field="type",
            type_map={},
        ),
    ]


class TestObjectBehavior:
    """Tests for object behavior, buffer management, and copy-on-write semantics."""

    def test_immutable_to_mutable_transition(self):

        raw = HexBuffer("01 02 03 04")

        @protoclass(byteorder="big")
        class SimpleS:
            val: Annotated[int, UInt32]

        # from_buffer creates a read-only view over the original bytes object
        s = SimpleS.from_bytes(raw)
        assert s.val == 0x01020304
        # After mutation, the object owns its own buffer (CoW) and can be written
        s.val = 0xDEADBEEF
        assert s.val == 0xDEADBEEF
        assert s.to_bytes() == HexBuffer("de ad be ef")
        # Original bytes unchanged (CoW semantics)
        assert raw == HexBuffer("01 02 03 04")

    def test_memoryview_buffer_link(self):

        raw = bytearray(HexBuffer("00 00 00 01"))
        mv = memoryview(raw)

        @protoclass(byteorder="big")
        class SimpleM:
            val: Annotated[int, UInt32]

        # from_buffer creates a read-only view
        s = SimpleM.from_buffer(mv)
        assert s.val == 1
        # After CoW promotion, writes go to an owned buffer, not the original
        s.val = 2
        assert s.val == 2
        assert s.to_bytes() == HexBuffer("00 00 00 02")
        # Original bytearray is unchanged (CoW semantics per DESIGN.md)
        assert raw[3] == 1

    def test_buffer_too_small(self):

        raw = HexBuffer("01 02")

        @protoclass(byteorder="big")
        class SimpleErr:
            val: Annotated[int, UInt32]

        with pytest.raises(ValueError):
            s = SimpleErr.from_bytes(raw)


class TestSafetyAndErrorHandling:
    """Tests for safety checks, error handling, and edge cases."""

    def test_invalid_nested_data(self):

        @protoclass()
        class FixedInner:
            val: Annotated[int, UInt32]

        @protoclass()
        class VarContainer:
            len: Annotated[int, UInt8]
            inner: Annotated[FixedInner, VariableData(length_field="len")]

        # Inner needs 4 bytes, len says 2.
        obj = VarContainer.from_bytes(b"\x02\x01\x02")
        with pytest.raises(ValueError):
            _ = obj.inner

    def test_invalid_list_data(self):

        @protoclass()
        class FixedInner:
            val: Annotated[int, UInt32]

        @protoclass()
        class ListContainer:
            items: Annotated[List[FixedInner], VariableData(item_type=FixedInner)]

        # 7 bytes total. First item 4 bytes. 3 bytes left.
        # Item 2 should fail because only 3 bytes are available.
        raw = HexBuffer("01 02 03 04 05 06 07")
        obj = ListContainer.from_bytes(raw)

    def test_system_error_on_invalid_type(self):

        @protoclass(byteorder="big")
        class VarStruct:
            type: Annotated[int, UInt16]
            len: Annotated[int, UInt16]
            payload: Annotated[
                Union[Bytes, UInt32],
                VariableData(
                    length_field="len",
                    length_offset=-4,
                    type_field="type",
                    type_map={1: UInt32, 2: Bytes},
                ),
            ]

        # Union[Bytes, UInt32] with type=1 (type_map→UInt32) but bytes passed.
        # The Union allows bytes, but because type=1 is authoritative, it resolves to UInt32.
        # Our strict write-through setter now validates this immediately.
        with pytest.raises(TypeError, match="expected integer, bytes found"):
            VarStruct(type=1, payload=b"\x00\x00\x00\x01")

    def test_safety_malformed_length_oob(self):
        """
        Verifies that a length_field specifying more data than available in the
        buffer raises a ValueError instead of performing an out-of-bounds read.
        """

        @protoclass()
        class Malicious:
            length: Annotated[int, UInt16]
            data: Annotated[bytes, VariableData(length_field="length", length_offset=-2)]

        # Buffer is only 2 bytes, but length field says 100
        bad_data = HexBuffer("00 64")  # length = 100
        obj = Malicious.from_bytes(bad_data)

        with pytest.raises(ValueError, match="Buffer too small"):
            _ = obj.data

    def test_safety_truncated_nested_object(self):
        """
        Verifies that a nested object that is truncated in the buffer raises
        an error when accessed.
        """

        @protoclass()
        class Inner:
            val: Annotated[int, UInt32]

        @protoclass()
        class Outer:
            len: Annotated[int, UInt16]
            inner: Annotated[Inner, VariableData(length_field="len", length_offset=-2)]

        # Inner needs 4 bytes + 2 bytes header = 6 bytes total.
        # Buffer provides 5 bytes (2 header + 3 data).
        bad_data = HexBuffer("00 05 11 22 33")
        obj = Outer.from_bytes(bad_data)

        with pytest.raises(ValueError):
            _ = obj.inner

    def test_safety_negative_length_clamping(self):
        """
        Verifies that calculations resulting in negative lengths (due to offsets)
        are handled safely (either clamped to 0 or raising an error).
        """

        @protoclass()
        class NegLen:
            length: Annotated[int, UInt16]
            # offset -10 on a length field of 2 -> -8.
            data: Annotated[bytes, VariableData(length_field="length", length_offset=-10)]

        obj = NegLen.from_bytes(HexBuffer("00 02"))
        # A negative length calculation should now trigger a ValueError
        # because it will definitely be out of bounds or invalid.
        with pytest.raises(ValueError):
            _ = obj.data

    def test_integer_metadata_repr(self):
        """Test Integer metadata representation."""
        u = Integer(8)
        assert repr(u) == "Integer(8, signed=False)"

    def test_variable_length_data_metadata_repr(self):
        """Test VariableLengthData metadata representation."""
        v = VariableLengthData(length_field="len")
        assert "VariableLengthData(length_field='len')" in repr(v)

    def test_invalid_variable_data_constructor(self):
        """Test that VariableData rejects invalid constructor arguments."""
        with pytest.raises(TypeError):
            VariableData(123)


class TestPlatformCompatibility:
    """Tests for platform compatibility with ctypes and native byte order."""

    def test_native_byteorder_compatibility_with_ctypes(self):
        """
        Test that native byteorder protoclass matches ctypes Structure layout.

        This verifies that protoclass with default (native) byteorder produces
        identical serialization to equivalent ctypes structures.
        """
        import ctypes

        # Define ctypes structure with native byte order
        class CTypesMessage(ctypes.Structure):
            _fields_ = [
                ("magic", ctypes.c_uint16),  # 2 bytes
                ("version", ctypes.c_uint8),  # 1 byte
                ("flags", ctypes.c_uint8),  # 1 byte
                ("length", ctypes.c_uint32),  # 4 bytes
                ("data", ctypes.c_uint8 * 4),  # 4 bytes
            ]

        # Define equivalent protoclass
        @protoclass()
        class PyMessage:
            magic: Annotated[int, UInt16]
            version: Annotated[int, UInt8]
            flags: Annotated[int, UInt8]
            length: Annotated[int, UInt32]
            data: Annotated[bytes, FixedLengthData(length=4)]

        # Test values
        test_magic = 0x1234
        test_version = 0x56
        test_flags = 0x78
        test_length = 0x9ABCDEF0
        test_data = b"\xde\xad\xbe\xef"

        # Create ctypes instance
        c_msg = CTypesMessage(
            magic=test_magic,
            version=test_version,
            flags=test_flags,
            length=test_length,
            data=(ctypes.c_uint8 * 4)(*test_data),
        )

        # Serialize ctypes to bytes
        c_bytes = bytes(ctypes.string_at(ctypes.byref(c_msg), ctypes.sizeof(CTypesMessage)))

        # Create protoclass instance
        p_msg = PyMessage(
            magic=test_magic,
            version=test_version,
            flags=test_flags,
            length=test_length,
            data=test_data,
        )

        # Serialize protoclass to bytes
        p_bytes = bytes(p_msg)

        # Verify serialization matches
        assert (
            p_bytes == c_bytes
        ), f"Serialization mismatch:\n  protoclass: {p_bytes.hex()}\n  ctypes:     {c_bytes.hex()}"

        # Verify deserialization matches
        p_msg2 = PyMessage.from_bytes(c_bytes)
        assert p_msg2.magic == test_magic
        assert p_msg2.version == test_version
        assert p_msg2.flags == test_flags
        assert p_msg2.length == test_length
        assert p_msg2.data == test_data

        # Verify round-trip through ctypes
        c_msg2 = CTypesMessage()
        ctypes.memmove(ctypes.byref(c_msg2), p_bytes, ctypes.sizeof(CTypesMessage))
        assert c_msg2.magic == test_magic
        assert c_msg2.version == test_version
        assert c_msg2.flags == test_flags
        assert c_msg2.length == test_length
        assert bytes(c_msg2.data) == test_data

    def test_native_byteorder_list_with_ctypes(self):
        """
        Test that native byteorder list serialization matches ctypes array.

        Uses _pack_ = 1 on ctypes structure to ensure no padding,
        matching protoclass behavior.
        """
        import ctypes

        # Define ctypes structure with array (packed to match protoclass)
        class CTypesArrayMessage(ctypes.Structure):
            _pack_ = 1  # No padding - matches protoclass behavior
            _fields_ = [
                ("count", ctypes.c_uint8),
                ("items", ctypes.c_uint16 * 3),  # 3 x 16-bit values
            ]

        # Define equivalent protoclass
        @protoclass()
        class PyArrayMessage:
            count: Annotated[int, UInt8]
            items: Annotated[List[int], VariableLengthData(item_type=UInt16)]

        # Test values
        test_count = 3
        test_items = [0x1234, 0x5678, 0x9ABC]

        # Create ctypes instance
        c_msg = CTypesArrayMessage(
            count=test_count, items=(ctypes.c_uint16 * 3)(*test_items)
        )

        # Serialize ctypes to bytes
        c_bytes = bytes(
            ctypes.string_at(ctypes.byref(c_msg), ctypes.sizeof(CTypesArrayMessage))
        )

        # Create protoclass instance
        p_msg = PyArrayMessage(count=test_count, items=test_items)

        # Serialize protoclass to bytes
        p_bytes = bytes(p_msg)

        # Verify serialization matches
        assert (
            p_bytes == c_bytes
        ), f"List serialization mismatch:\n  protoclass: {p_bytes.hex()}\n  ctypes:     {c_bytes.hex()}"

        # Verify deserialization
        p_msg2 = PyArrayMessage.from_bytes(c_bytes)
        assert p_msg2.count == test_count
        assert p_msg2.items == test_items
