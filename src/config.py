from __future__ import annotations

import argparse
import os
import time
import tomllib
from typing import Any

from utils import utils


class Config:
    def __init__(self) -> None:
        # 1. Load Environment Variables
        self.env_url = utils.get_env("HUGE_URL")
        self.env_name = utils.get_env("HUGE_NAME")

        # 2. Setup standard attributes
        self.path = os.path.dirname(os.path.abspath(__file__))
        self.info_name = "hugegull"
        self.info_version = "0.0.0"

        # 3. Parse CLI Arguments
        self.args = self.parse_arguments()
        self.open = self.args.open
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
            env_urls = self.env_url.split(" ")

        raw_urls = self.resolve("urls", "urls", env_urls)
        self.urls = []

        for s in raw_urls:
            if s != "":
                self.urls.append(s)

        default_name = self.env_name or utils.get_random_name()

        self.name = self.resolve("name", "name", default_name)
        self.amount = self.resolve("amount", "amount", 1)
        self.duration = self.resolve("duration", "duration", 35.0)
        self.fps = self.resolve("fps", "fps", 30)
        self.crf = self.resolve("crf", "crf", 30)
        self.fade = self.resolve("fade", "fade", 0.03)
        self.help = False
        self.version = False

        self.min_clip_duration = self.resolve(
            "min_clip_duration", "min_clip_duration", 3.0
        )

        self.avg_clip_duration = self.resolve(
            "avg_clip_duration", "avg_clip_duration", 6.0
        )

        self.max_clip_duration = self.resolve(
            "max_clip_duration", "max_clip_duration", 9.0
        )

        self.gpu = self.resolve("gpu", "gpu", "")
        self.path = self.resolve("path", "path", self.path)

        # 7. Finalize generated paths
        self.temp_dir = os.path.join(self.path, "temp")
        self.output_dir = os.path.join(self.path, "output")

        run_id = str(int(time.time() * 1000))
        self.project_dir = os.path.join(self.temp_dir, f"project_{run_id}")

    def parse_arguments(self) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description="Hugegull Config Parser", add_help=False)

        # Info
        parser.add_argument("--help", "-h", action="store_true")
        parser.add_argument("--version", "-v", action="store_true")

        # Flags (Booleans)
        parser.add_argument("--open", action="store_true")

        # Strings
        parser.add_argument("--config", type=str)
        parser.add_argument("--name", type=str)
        parser.add_argument("--gpu", type=str)
        parser.add_argument("--path", type=str)

        # Lists (action="append" allows multiple --url arguments)
        parser.add_argument("--url", action="append", dest="urls")

        # Integers
        parser.add_argument("--amount", type=int)
        parser.add_argument("--fps", type=int)
        parser.add_argument("--crf", type=int)

        # Floats
        parser.add_argument("--duration", type=float)
        parser.add_argument("--fade", type=float)
        parser.add_argument("--min-clip-duration", type=float, dest="min_clip_duration")
        parser.add_argument("--avg-clip-duration", type=float, dest="avg_clip_duration")
        parser.add_argument("--max-clip-duration", type=float, dest="max_clip_duration")

        return parser.parse_args()

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


config = Config()
