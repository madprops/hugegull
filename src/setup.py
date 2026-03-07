import glob
from setuptools import setup

from info import info

modules = []

for file_name in glob.glob("*.py"):
    if file_name != "setup.py":
        modules.append(file_name[:-3])

setup(
    name=info.name,
    version=info.version,
    py_modules=modules,
    entry_points={
        "console_scripts": [
            "hugegull = main:main",
        ],
    },
)
