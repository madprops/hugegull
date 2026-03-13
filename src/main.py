from __future__ import annotations

#   _    _ _    _  _____  ______     _____ _    _ _      _
#  | |  | | |  | |/ ____||  ____|   / ____| |  | | |    | |
#  | |__| | |  | | |  __ | |__     | |  __| |  | | |    | |
#  |  __  | |  | | | |_ ||  __|    | | |_ | |  | | |    | |
#  | |  | | |__| | |__| || |____   | |__| | |__| | |____| |____
#  |_|  |_|\____/ \_____||______|   \_____|\____/|______|______|

import sys
import time

from config import config
from utils import utils
from engine import engine


def run() -> None:
    if not config.urls:
        utils.error("No valid URLs to process.")
        return

    start_time = time.perf_counter()

    if engine.start():
        end_time = time.perf_counter()
        duration = end_time - start_time
        utils.info(f"Done in {int(duration)} seconds")

        if config.open:
            utils.open_file(engine.file)
        else:

            if config.amount == 1:
                utils.notify("Video Complete")
            else:
                utils.notify("Videos Complete")


def main() -> None:
    if not config.urls:
        config.show_help()
        sys.exit(1)

    run()


if __name__ == "__main__":
    main()
