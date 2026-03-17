import shutil
from setuptools import setup
from src.info import info
import platform

requirements = []


def _copy_icon_file():
    source = Path(f"{info.name}/src/icon.png").expanduser().resolve()
    destination = Path(f"~/.local/share/icons/{program}.png").expanduser().resolve()
    shutil.copy2(source, destination)


def _create_desktop_file():
    content = f"""[Desktop Entry]
Version={info.version}
Name={info.full_name}
Exec={Path(f"~/.local/bin/{info.name}").expanduser().resolve()} --gui
Icon={Path(f"~/.local/share/icons/{info.name}.png").expanduser().resolve()}
Terminal=false
Type=Application
Categories=Utility;
"""

    file_path = (
        Path(f"~/.local/share/applications/{program}.desktop").expanduser().resolve()
    )

    with open(file_path, "w") as f:
        f.write(content)


def _post_install():
    system = platform.system()

    if system == "Linux":
        try:
            _copy_icon_file()
            _create_desktop_file()
        except Exception as e:
            print(f"Error during post install: {e}")

with open("requirements.txt") as f:
    for line in f:
        clean_line = line.strip()

        if clean_line and not clean_line.startswith("#"):
            requirements.append(clean_line)

setup(
    name=info.name,
    version=info.version,
    package_dir={"": "src"},
    packages=[""],
    package_data={"": ["*.toml", "*.txt", "*.png"]},
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            f"{info.name} = main:main",
        ],
    },
)

_post_install()