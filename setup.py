from setuptools import setup, find_packages

setup(
    name='routesia',
    description='Configuration system for Linux-based routers',
    packages=find_packages(),
    install_requires=[
        'paho-mqtt',
        'protobuf',
    ],
)
