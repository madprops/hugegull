import platform
import shutil
from pathlib import Path
from info import info

def install_desktop_integration():
    system = platform.system()

    if system != "Linux":
        print("Desktop integration is only supported on Linux.")
        return

    try:
        # Resolve paths dynamically based on the current user
        icon_source = Path(__file__).parent / "icon.png"
        icon_dest = Path(f"~/.local/share/icons/{info.name}.png").expanduser().resolve()
        desktop_dest = Path(f"~/.local/share/applications/{info.name}.desktop").expanduser().resolve()
        bin_path = Path(f"~/.local/bin/{info.name}").expanduser().resolve()

        # Ensure the destination directories actually exist before copying
        icon_dest.parent.mkdir(parents=True, exist_ok=True)
        desktop_dest.parent.mkdir(parents=True, exist_ok=True)

        if icon_source.exists():
            shutil.copy2(icon_source, icon_dest)
            print(f"Installed icon to {icon_dest}")
        else:
            print(f"Warning: Icon not found at {icon_source}")

        content = f"""[Desktop Entry]
Version={info.version}
Name={info.full_name}
Exec={bin_path} --gui
Icon={icon_dest}
Terminal=false
Type=Application
Categories=Utility;
"""
        with open(desktop_dest, "w") as f:
            f.write(content)

        print(f"Installed desktop file to {desktop_dest}")

    except Exception as e:
        print(f"Error during desktop installation: {e}")

if __name__ == "__main__":
    install_desktop_integration()