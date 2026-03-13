from __future__ import annotations

import argparse
import os
import time
import tomllib
from typing import Any

from utils import utils
from info import info


class Config:
    def __init__(self) -> None:
        # 1. Load Environment Variables
        self.env_url = utils.get_env("HUGE_URL")
        self.env_name = utils.get_env("HUGE_NAME")

        # 2. Setup standard attributes
        self.path = os.path.dirname(os.path.abspath(__file__))

        # 3. Parse CLI Arguments
        self.args = self.parse_arguments()
        self.open = self.args.open
        self.gui = self.args.gui
        self.config = self.args.config or ""

        # 4. Setup Directories and Files
        self.config_file = self.config or "~/.config/hugegull/config.toml"
        self.config_path = os.path.expanduser(self.config_file)
        self.config_dir = os.path.dirname(self.config_path)

        self.make_dirs()

        # 5. Read TOML Configuration
        self.toml_data = self.read_toml()

        # 6. Resolve final values
        env_urls = []

        if self.env_url:
            env_urls = self.env_url.split("|")

        raw_urls = self.resolve("urls", "urls", env_urls)
        self.urls = []

        for s in raw_urls:
            if s != "":
                self.urls.append(s.strip())

        self.name = self.resolve("name", "name", "")
        self.amount = self.resolve("amount", "amount", 1)
        self.duration = self.resolve("duration", "duration", 35)
        self.clip_duration = self.resolve("clip_duration", "clip_duration", 6.0)
        self.clip_diff = self.resolve("clip_diff", "clip_diff", 3.0)
        self.fps = self.resolve("fps", "fps", 30)
        self.crf = self.resolve("crf", "crf", 30)
        self.fade = self.resolve("fade", "fade", 0.03)
        self.gpu = self.resolve("gpu", "gpu", "cpu")
        self.path = self.resolve("path", "path", self.path)

        if self.gpu not in ["cpu", "amd", "nvidia"]:
            raise ValueError(f"Invalid GPU option '{self.gpu}'. Allowed values are 'cpu', 'amd', 'nvidia'.")

        # 7. Finalize generated paths
        self.temp_dir = os.path.join(self.path, "temp")
        self.output_dir = os.path.join(self.path, "output")

        run_id = str(int(time.time() * 1000))
        self.project_dir = os.path.join(self.temp_dir, f"project_{run_id}")

    def parse_arguments(self) -> argparse.Namespace:
        self.parser = argparse.ArgumentParser(description="Hugegull Config Parser")

        self.parser.add_argument(
            "--version", "-v", action="version", version=info.version
        )

        self.parser.add_argument(
            "positional_urls", nargs="*", type=str, help="Source video URLs."
        )

        self.parser.add_argument(
            "--url", action="append", dest="urls", help="Source video URLs."
        )

        self.parser.add_argument(
            "--open",
            action="store_true",
            help="Opens the final video file automatically when finished.",
        )

        self.parser.add_argument(
            "--gui",
            action="store_true",
            help="Show the graphical user interface.",
        )

        self.parser.add_argument(
            "--config", type=str, help="Path to a custom TOML config file."
        )

        self.parser.add_argument(
            "--name", type=str, help="Output filename. (Env: HUGE_NAME)"
        )

        self.parser.add_argument(
            "--gpu",
            type=str,
            choices=["cpu", "amd", "nvidia"],
            help="Hardware acceleration identifier."
        )

        self.parser.add_argument(
            "--path", type=str, help="Base directory for the temp and output folders."
        )

        self.parser.add_argument(
            "--amount", type=int, help="Total number of output videos to generate."
        )

        self.parser.add_argument(
            "--fps", type=int, help="Output video frames per second."
        )

        self.parser.add_argument(
            "--crf",
            type=int,
            help="Video quality/compression factor. Lower means higher quality.",
        )

        self.parser.add_argument(
            "--duration",
            type=int,
            help="Total target duration (in seconds) of the output video.",
        )

        self.parser.add_argument(
            "--clip-duration",
            type=float,
            help="Average duration for a single grabbed section.",
        )

        self.parser.add_argument(
            "--clip-diff",
            type=float,
            help="The range around the clip duration, more or less.",
        )

        self.parser.add_argument(
            "--fade", type=float, help="Crossfade duration between clips."
        )

        args = self.parser.parse_args()

        cli_urls = []

        if args.positional_urls:
            cli_urls.extend(args.positional_urls)

        if args.urls:
            cli_urls.extend(args.urls)

        if cli_urls:
            args.urls = cli_urls
        else:
            args.urls = None

        return args

    # Add a new method to call help programmatically
    def show_help(self) -> None:
        self.parser.print_help()

    def read_toml(self) -> dict[str, Any]:
        if not os.path.exists(self.config_path):
            return {}

        with open(self.config_path, "rb") as f:
            return tomllib.load(f)

    def resolve(self, cli_key: str, toml_key: str, default_val: Any) -> Any:
        cli_val = getattr(self.args, cli_key, None)

        if cli_val is not None:
            return cli_val

        if toml_key in self.toml_data:
            return self.toml_data[toml_key]

        return default_val

    def make_dirs(self) -> None:
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)

        if not os.path.exists(self.config_path):
            with open(self.config_path, "w") as f:
                f.write("")

    def refresh_paths(self) -> None:
        self.temp_dir = os.path.join(self.path, "temp")
        self.output_dir = os.path.join(self.path, "output")
        run_id = str(int(time.time() * 1000))
        self.project_dir = os.path.join(self.temp_dir, f"project_{run_id}")

        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def update(self, data: dict[str, Any]) -> None:
        if "urls" in data:
            self.urls = []

            for u in data["urls"]:
                if u:
                    self.urls.append(u)

        if "path" in data:
            self.path = data["path"]

        if "name" in data:
            if data["name"]:
                self.name = data["name"]

        if "gpu" in data:
            if data["gpu"] not in ["cpu", "amd", "nvidia"]:
                raise ValueError(f"Invalid GPU option '{data['gpu']}'. Allowed values are 'cpu', 'amd', 'nvidia'.")

            self.gpu = data["gpu"]

        if "fps" in data:
            self.fps = int(data["fps"])

        if "crf" in data:
            self.crf = int(data["crf"])

        if "duration" in data:
            self.duration = int(data["duration"])

        if "clip_duration" in data:
            self.clip_duration = float(data["clip_duration"])

        if "clip_diff" in data:
            self.clip_diff = float(data["clip_diff"])

        if "fade" in data:
            self.fade = float(data["fade"])

        if "amount" in data:
            self.amount = int(data["amount"])

        if "open" in data:
            self.open = bool(data["open"])

        self.refresh_paths()

    def check_name(self) -> None:
        if not self.name:
            self.name = utils.get_random_name()


config = Config()