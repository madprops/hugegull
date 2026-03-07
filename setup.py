import glob
import os
from setuptools import setup

# assuming info.py also moved into src
from src.info import info

modules = []

for file_path in glob.glob("src/*.py"):
    file_name = os.path.basename(file_path)
    modules.append(file_name[:-3])

setup(
    name=info.name,
    version=info.version,
    package_dir={"": "src"},
    py_modules=modules,
    entry_points={
        "console_scripts": [
            "hugegull = main:main",
        ],
    },
)