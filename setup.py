from setuptools import setup, find_packages

setup(
    name='routesia',
    description='Configuration system for Linux-based routers',
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "rcl = routesia.programs.rcl:main",
            "routesia = routesia.programs.routesia_agent:main",
            "routesia-dhcpv4-event = routesia.programs.routesia_dhcpv4_event:main",
        ],
    },
)
