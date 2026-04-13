import sys
from pathlib import Path
from setuptools import setup
from hugegull.info import info

requirements = []

with open("requirements.txt") as f:
    for line in f:
        clean_line = line.strip()

        if clean_line and not clean_line.startswith("#"):
            requirements.append(clean_line)

setup(
    name=info.name,
    version=info.version,
    packages=["hugegull"],
    package_data={"hugegull": ["*.toml", "*.txt", "*.png"]},
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            f"{info.name} = hugegull.main:main",
        ],
    },
)