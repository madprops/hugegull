from __future__ import annotations

#   _    _ _    _  _____  ______     _____ _    _ _      _
#  | |  | | |  | |/ ____||  ____|   / ____| |  | | |    | |
#  | |__| | |  | | |  __ | |__     | |  __| |  | | |    | |
#  |  __  | |  | | | |_ ||  __|    | | |_ | |  | | |    | |
#  | |  | | |__| | |__| || |____   | |__| | |__| | |____| |____
#  |_|  |_|\____/ \_____||______|   \_____|\____/|______|______|

import sys
import time

import gui
from info import info
from config import config
from utils import utils
from engine import engine


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
                if config.amount == 1:
                    utils.open_file(engine.file)
                else:
                    utils.open_dir(config.output_dir)
            else:
                if config.amount == 1:
                    utils.notify("Video Complete")
                else:
                    utils.notify("Videos Complete")
    except:
        engine.cleanup()


def main() -> None:
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
