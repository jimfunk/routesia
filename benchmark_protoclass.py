import timeit
from typing import Annotated, Union
from enum import IntEnum
from routesia.protoclass import (
    protoclass,
    UInt8,
    UInt16,
    UInt32,
    VariableLengthData,
    UInt8Base,
    UInt16Base,
)


# Fixed setup
@protoclass()
class FixedStruct:
    f1: Annotated[int, UInt32]
    f2: Annotated[int, UInt16]
    f3: Annotated[int, UInt8]


@protoclass()
class FixedStructDefaults:
    f1: Annotated[int, UInt32] = 1
    f2: Annotated[int, UInt16] = 2
    f3: Annotated[int, UInt8] = 3


fixed_instance = FixedStruct(f1=1, f2=2, f3=3)
fixed_bytes = bytes(fixed_instance)


def bench_fixed_encode():
    return FixedStruct(f1=1, f2=2, f3=3)


def bench_fixed_encode_defaults():
    return FixedStructDefaults()


def bench_fixed_decode():
    FixedStruct.from_bytes(fixed_bytes)


def bench_fixed_access():
    _ = fixed_instance.f1
    _ = fixed_instance.f2
    _ = fixed_instance.f3


# Poly setup
class PolyType(UInt16Base, IntEnum):
    TYPE_A = 1
    TYPE_B = 2


@protoclass()
class PolyA:
    val: Annotated[int, UInt32]


@protoclass()
class PolyB:
    val: Annotated[int, UInt16]


@protoclass()
class PolyStruct:
    len: Annotated[int, UInt16]
    type: Annotated[PolyType, UInt16]
    payload: Annotated[
        Union[PolyA, PolyB],
        VariableLengthData(
            length_field="len",
            length_offset=-4,
            type_field="type",
            type_map={PolyType.TYPE_A: PolyA, PolyType.TYPE_B: PolyB},
        ),
    ]


poly_instance = PolyStruct(len=8, type=PolyType.TYPE_A, payload=PolyA(val=0x12345678))
poly_bytes = bytes(poly_instance)


def bench_poly_encode():
    return PolyStruct(len=8, type=PolyType.TYPE_A, payload=PolyA(val=0x12345678))


def bench_poly_decode():
    PolyStruct.from_bytes(poly_bytes)


def bench_poly_access():
    _ = poly_instance.type
    _ = poly_instance.payload.val


def bench_fixed_first_access():
    inst = FixedStruct.from_bytes(fixed_bytes)
    _ = inst.f1
    _ = inst.f2
    _ = inst.f3


def bench_poly_first_access():
    inst = PolyStruct.from_bytes(poly_bytes)
    _ = inst.type
    _ = inst.payload


def run_benchmark(name, func):
    # Run
    number = 1000000
    try:
        total_time = timeit.timeit(func, number=number)
        iter_s = number / total_time
        print(f"{name:<30} {iter_s:,.2f} iter/s")
    except Exception as e:
        print(f"Error in benchmark {name}: {e}")


if __name__ == "__main__":
    run_benchmark("fixed encode", bench_fixed_encode)
    run_benchmark("fixed encode default values", bench_fixed_encode_defaults)
    run_benchmark("fixed decode", bench_fixed_decode)
    run_benchmark("fixed first access", bench_fixed_first_access)
    run_benchmark("fixed access", bench_fixed_access)
    run_benchmark("poly encode", bench_poly_encode)
    run_benchmark("poly decode", bench_poly_decode)
    run_benchmark("poly first access", bench_poly_first_access)
    run_benchmark("poly access", bench_poly_access)
