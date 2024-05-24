from setuptools import setup, find_packages

from routesia import VERSION

setup(
    name='routesia',
    description='Configuration system for Linux-based routers',
    packages=find_packages(),
    scripts=(
        "scripts/rcl",
        "scripts/routesia",
        "scripts/routesia-dhcpv4-event",
    ),
    install_requires=[
        'paho-mqtt',
        'protobuf',
    ],
    version=VERSION,
)
