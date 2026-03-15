from __future__ import annotations

#   _    _ _    _  _____  ______     _____ _    _ _      _
#  | |  | | |  | |/ ____||  ____|   / ____| |  | | |    | |
#  | |__| | |  | | |  __ | |__     | |  __| |  | | |    | |
#  |  __  | |  | | | |_ ||  __|    | | |_ | |  | | |    | |
#  | |  | | |__| | |__| || |____   | |__| | |__| | |____| |____
#  |_|  |_|\____/ \_____||______|   \_____|\____/|______|______|

import os
import sys
import time

import gui
from info import info
from config import config
from utils import utils
from engine import engine

LOCKS = []


def run() -> None:
    if not config.urls:
        utils.error("No valid URLs to process.")
        return

    start_time = time.perf_counter()

    try:
        if engine.start():
            end_time = time.perf_counter()
            duration = end_time - start_time
            utils.info(f"Done in {int(duration)} seconds")

            if config.open:
                utils.open_videos(engine.files)
            else:
                if config.amount == 1:
                    utils.notify("Video Complete")
                else:
                    utils.notify("Videos Complete")
    except Exception as e:
        utils.error(f"Error at Main: {e}")
        engine.cleanup()


def singleton() -> None:
    app_name = info.name

    if os.name == "nt":
        import ctypes

        mutex_name = f"Global\\{app_name}_mutex"
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)  # type: ignore
        last_error = ctypes.windll.kernel32.GetLastError()  # type: ignore

        if last_error == 183:
            print(f"An instance of {app_name} is already running.")
            sys.exit(1)

        LOCKS.append(mutex)
    else:
        import fcntl
        import tempfile

        lock_path = os.path.join(tempfile.gettempdir(), f"{app_name}.lock")
        lock_file = open(lock_path, "w")

        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print(f"An instance of {app_name} is already running.")
            trigger_raise()
            sys.exit(1)

        LOCKS.append(lock_file)

def trigger_raise() -> None:
    import socket
    import tempfile
    import hashlib

    app_name = info.name

    try:
        if os.name == "posix":
            socket_path = os.path.join(tempfile.gettempdir(), f"{app_name}_ipc.sock")
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(socket_path)
        else:
            port = 50000 + int(hashlib.md5(app_name.encode()).hexdigest(), 16) % 10000
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(("127.0.0.1", port))

        client.sendall("RAISE".encode("utf-8"))
        client.close()
    except Exception:
        pass


def main() -> None:
    if not config.multiple:
        singleton()

    if config.gui:
        gui.main()
    elif not config.urls:
        config.show_help()
        sys.exit(1)
    else:
        utils.set_proc_name(info.name)
        run()


if __name__ == "__main__":
    main()
