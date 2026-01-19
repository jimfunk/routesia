from setuptools import setup, find_packages, Extension

from routesia import VERSION

CFLAGS = ["-Wall", "-Werror"]

setup(
    name="routesia",
    description="Configuration system for Linux-based routers",
    packages=find_packages(),
    ext_modules=[
        Extension(
            "routesia.netlink.constants",
            sources=["routesia/netlink/constants.c"],
            extra_compile_args=CFLAGS,
        ),
        Extension(
            "routesia.protoclass._cprotoclass",
            sources=["routesia/protoclass/_cprotoclass.c"],
            extra_compile_args=CFLAGS,
        ),
    ],
    entry_points={
        "console_scripts": [
            "rcl = routesia.programs.rcl:main",
            "routesia = routesia.programs.routesia_agent:main",
            "routesia-dhcpv4-event = routesia.programs.routesia_dhcpv4_event:main",
        ],
    },
    version=VERSION,
)
