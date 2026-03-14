from __future__ import annotations

import os
import random
import subprocess
import json
import shutil
import time
import concurrent.futures
from typing import Any

from config import config
from utils import utils
from data import data
import gui


class Engine:
    def __init__(self) -> None:
        self.sources: list[dict[str, Any]] = []
        self.clips: dict[str, float] = {}
        self.workers = 6
        self.max_width = 0
        self.max_height = 0
        self.clip_timeout = 120
        self.resolve_timeout = 60
        self.concat_timeout = 120
        self.probe_timeout = 15
        self.min_clip_duration = 0.5
        self.active_processes: list[subprocess.Popen[str]] = []
        self.files: list[str] = []

    def kill_all_processes(self) -> None:
        for p in self.active_processes:
            try:
                p.kill()
            except Exception:
                pass

        self.active_processes.clear()

    def run_process(
        self, command: list[str], timeout_val: float
    ) -> subprocess.CompletedProcess[str]:
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        self.active_processes.append(process)
        end_time = time.time() + timeout_val

        try:
            while True:
                if data.abort:
                    process.terminate()
                    process.wait()
                    return subprocess.CompletedProcess(process.args, 1, "", "Aborted")

                if time.time() > end_time:
                    process.kill()
                    process.wait()
                    raise subprocess.TimeoutExpired(process.args, timeout_val)

                try:
                    # Check every 0.5 seconds so we can respond to data.abort quickly
                    out, err = process.communicate(timeout=0.5)

                    return subprocess.CompletedProcess(
                        process.args, process.returncode, out, err
                    )
                except subprocess.TimeoutExpired:
                    continue
        finally:
            if process in self.active_processes:
                self.active_processes.remove(process)

    def prepare(self) -> None:
        os.makedirs(config.project_dir, exist_ok=True)
        os.makedirs(config.output_dir, exist_ok=True)
        self.file = os.path.join(config.output_dir, f"{config.name}.mp4")
        counter = 2

        while os.path.exists(self.file):
            self.file = os.path.join(config.output_dir, f"{config.name}_{counter}.mp4")
            counter += 1

    def process_url(self, url: str) -> dict[str, Any] | None:
        if data.abort:
            return None

        source: dict[str, Any] = {
            "url": url,
            "v_data": url,
            "a_url": None,
            "duration": 0.0,
            "width": 0,
            "height": 0,
        }

        if os.path.isfile(url):
            info = self.get_stream_info(url)
            source.update(info)
        else:
            if utils.is_site(url):
                yt_data = self.resolve_with_ytdlp(url)

                if yt_data is not None:
                    source.update(yt_data)

                v_data = source.get("v_data")

                if v_data is None:
                    v_data = ""

                info = self.get_stream_info(str(v_data))
                source["width"] = info["width"]
                source["height"] = info["height"]

                if source["duration"] == 0.0:
                    source["duration"] = info["duration"]
            else:
                info = self.get_stream_info(url)
                source.update(info)

        raw_duration = source.get("duration")
        duration = 0.0

        if raw_duration is not None:
            try:
                duration = float(raw_duration)
            except ValueError:
                duration = 0.0

        raw_width = source.get("width")
        width = 0

        if raw_width is not None:
            width = int(raw_width)

        raw_height = source.get("height")
        height = 0

        if raw_height is not None:
            height = int(raw_height)

        if (duration > 0) and (width > 0) and (height > 0):
            source["duration"] = duration
            source["width"] = width
            source["height"] = height
            return source
        else:
            utils.info(f"Could not determine valid data for {url}, skipping.")
            return None

    def prepare_sources(self) -> None:
        if data.abort:
            return

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.workers
        ) as executor:
            futures = []

            for url in config.urls:
                if data.abort:
                    break

                future = executor.submit(self.process_url, url)
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                if data.abort:
                    break

                source = future.result()

                if source is not None:
                    self.sources.append(source)

                    if source["width"] > self.max_width:
                        self.max_width = source["width"]

                    if source["height"] > self.max_height:
                        self.max_height = source["height"]

    def start(self) -> bool:
        if data.abort:
            return False

        self.sources.clear()
        self.clips.clear()
        config.check_name()
        gui.update_progress("Starting")
        utils.info(f"Starting: {config.name} | {int(config.duration)}s")
        os.makedirs(config.project_dir, exist_ok=True)
        self.prepare_sources()

        if len(self.sources) == 0:
            utils.info(
                "No valid sources found in the pool. Stream is live/endless or invalid."
            )

            self.cleanup()
            return False

        amount = config.amount or 1
        total_needed_duration = config.duration * amount * 1.3
        utils.info(f"Generating clip pool for {amount} videos...")
        self.generate_random_clips(total_needed_duration)

        if len(self.clips) == 0:
            if not data.abort:
                utils.error("Failed to generate any clips for the master pool.")

            return False

        all_successful = True
        available_clips = list(self.clips.keys())

        for i in range(amount):
            if data.abort:
                return False

            if amount > 1:
                gui.update_progress(f"Video {i + 1}")
                utils.info(f"--- Generating video {i + 1} of {amount} ---")

            self.prepare()

            selected_clips = self.select_clips_for_duration(
                config.duration, available_clips
            )

            for clip in selected_clips:
                if clip in available_clips:
                    available_clips.remove(clip)

            if not self.concatenate_clips(selected_clips):
                all_successful = False

        self.cleanup()
        return all_successful

    def resolve_with_ytdlp(self, url: str) -> dict[str, Any] | None:
        cookie_args: list[Any] = [[]]

        if os.path.isfile("cookies.txt"):
            cookie_args.append(["--cookies", "cookies.txt"])

        cookie_args.extend(
            [
                ["--cookies-from-browser", "firefox"],
                ["--cookies-from-browser", "chrome"],
            ]
        )

        result = None
        errors = []

        for args in cookie_args:
            command = ["yt-dlp", "--no-playlist", "--no-warnings"]
            command.extend(args)

            command.extend(
                [
                    "-f",
                    "bv*[height<=1080]+ba/b[height<=1080]/bv+ba/b",
                    "--dump-json",
                    url,
                ]
            )

            method_name = "default"

            if len(args) > 0:
                method_name = " ".join(args)

            try:
                result = self.run_process(command, self.resolve_timeout)
            except subprocess.TimeoutExpired:
                errors.append(f"[{method_name}] -> Process timed out.")
                continue

            if result.returncode == 0:
                break

            errors.append(f"[{method_name}] -> {result.stderr.strip()}")

        if result is None or result.returncode != 0:
            utils.error(f"Error resolving URL {url}. All attempts failed:")

            for err in errors:
                utils.error(err)

            return None

        try:
            metadata = json.loads(result.stdout)
            duration = 0.0

            if "duration" in metadata:
                if metadata["duration"] is not None:
                    duration = float(metadata["duration"])

            if "requested_formats" in metadata:
                if len(metadata["requested_formats"]) >= 2:
                    v_data = metadata["requested_formats"][0]["url"]
                    a_url = metadata["requested_formats"][1]["url"]
                    return {"v_data": v_data, "a_url": a_url, "duration": duration}
                else:
                    return {
                        "v_data": metadata["requested_formats"][0]["url"],
                        "a_url": None,
                        "duration": duration,
                    }
            else:
                return {
                    "v_data": metadata.get("url"),
                    "a_url": None,
                    "duration": duration,
                }

        except Exception as e:
            utils.error(f"Error parsing yt-dlp output: {e}")
            return None

    def generate_clip_sections(self, target_duration: float) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []
        current_sum = 0.0
        end_buffer = 2.0

        while current_sum < target_duration:
            source = random.choice(self.sources)
            safe_duration = source["duration"] - end_buffer
            avg_cd = config.clip_duration
            min_cd = avg_cd - config.clip_diff

            if min_cd < self.min_clip_duration:
                min_cd = self.min_clip_duration

            max_cd = avg_cd + config.clip_diff

            clip_length = random.triangular(
                min_cd,
                avg_cd,
                max_cd,
            )

            if (current_sum + clip_length) > target_duration:
                clip_length = target_duration - current_sum

            if clip_length < min_cd:
                clip_length = min_cd

            max_start = safe_duration - clip_length

            if max_start <= 0:
                continue

            start = random.uniform(0, max_start)
            sections.append({"start": start, "duration": clip_length, "source": source})
            current_sum += clip_length

        return sections

    def extract_single_clip(
        self, i: int, section: dict[str, Any]
    ) -> tuple[str, float] | None:
        if data.abort:
            return None

        source = section["source"]
        start = section["start"]
        duration = section["duration"]
        v_data = source["v_data"]
        a_url = source["a_url"]
        is_split_stream = False

        if a_url is not None:
            is_split_stream = True

        name = os.path.join(config.project_dir, f"temp_clip_{i + 1}.mp4")
        modes_to_try = [config.gpu]

        if config.gpu in ("amd", "nvidia"):
            modes_to_try = [config.gpu, "cpu"]
        else:
            modes_to_try = ["cpu"]

        for mode in modes_to_try:
            command = ["ffmpeg"]

            if mode == "amd":
                command.extend(["-vaapi_device", "/dev/dri/renderD128"])
            elif mode == "nvidia":
                command.extend(["-hwaccel", "cuda"])

            command.extend(["-ss", str(start), "-i", v_data])

            if is_split_stream:
                command.extend(["-ss", str(start), "-i", a_url])

            fade_out_start = duration - config.fade
            pad_w = self.max_width
            pad_h = self.max_height

            if pad_w % 2 != 0:
                pad_w += 1

            if pad_h % 2 != 0:
                pad_h += 1

            vf_filter = f"scale={pad_w}:{pad_h}:force_original_aspect_ratio=decrease,pad={pad_w}:{pad_h}:(ow-iw)/2:(oh-ih)/2,fps={config.fps},setsar=1"

            if mode == "amd":
                vf_filter = f"{vf_filter},format=nv12,hwupload"

            af_filter = f"afade=t=in:st=0:d={config.fade},afade=t=out:st={fade_out_start}:d={config.fade}"

            if is_split_stream:
                command.extend(["-map", "0:v:0", "-map", "1:a:0"])
            else:
                command.extend(["-map", "0:v:0", "-map", "0:a:0?"])

            command.extend(["-t", str(duration), "-vf", vf_filter, "-af", af_filter])

            if mode == "amd":
                adjusted_crf = config.crf - 4

                if adjusted_crf < 0:
                    adjusted_crf = 0

                command.extend(
                    ["-c:v", "h264_vaapi", "-rc_mode", "CQP", "-qp", str(adjusted_crf)]
                )
            elif mode == "nvidia":
                adjusted_crf = config.crf - 4

                if adjusted_crf < 0:
                    adjusted_crf = 0

                command.extend(
                    ["-c:v", "h264_nvenc", "-cq", str(adjusted_crf), "-preset", "p6"]
                )
            else:
                command.extend(
                    ["-c:v", "libx264", "-preset", "medium", "-crf", str(config.crf)]
                )

            command.extend(
                [
                    "-c:a",
                    "aac",
                    "-ar",
                    "48000",
                    "-ac",
                    "2",
                    "-video_track_timescale",
                    "90000",
                    "-y",
                    name,
                ]
            )

            gui.update_progress(f"Clip {i + 1}")

            utils.action(
                f"Clip {i + 1} starting at {round(start)}s (Duration: {round(duration)}s) ({mode})"
            )

            try:
                result = self.run_process(command, self.clip_timeout)

                if result.returncode == 0:
                    return name, duration

                utils.error(f"Error extracting clip {i + 1} using {mode}:")
                utils.error(result.stderr)

                if mode != modes_to_try[-1]:
                    utils.info(f"Retrying clip {i + 1} with CPU fallback...")

            except subprocess.TimeoutExpired:
                utils.error(f"Timeout expired. Extracting clip {i + 1} using {mode}.")

                if mode != modes_to_try[-1]:
                    utils.info(f"Retrying clip {i + 1} with CPU fallback...")

            except Exception as e:
                utils.error(f"Exception extracting clip {i + 1} using {mode}: {e}")

                if mode != modes_to_try[-1]:
                    utils.info(f"Retrying clip {i + 1} with CPU fallback...")

        return None

    def generate_random_clips(self, target_duration: float) -> None:
        if data.abort:
            return

        sections = self.generate_clip_sections(target_duration)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.workers
        ) as executor:
            futures = []

            for i in range(len(sections)):
                if data.abort:
                    break

                future = executor.submit(self.extract_single_clip, i, sections[i])
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                if data.abort:
                    break

                result = future.result()

                if result is not None:
                    clip_path, duration = result
                    self.clips[clip_path] = duration

    def select_clips_for_duration(
        self, target_duration: float, available_clips: list[str]
    ) -> list[str]:
        selected = []
        current_duration = 0.0

        # Shuffle the remaining available clips to keep selection random
        pool = list(available_clips)
        random.shuffle(pool)

        for clip in pool:
            if current_duration >= target_duration:
                break

            clip_duration = self.clips.get(clip, 0.0)

            if clip_duration > 0:
                selected.append(clip)
                current_duration += clip_duration

        return selected

    def concatenate_clips(self, selected_clips: list[str]) -> bool:
        if data.abort:
            return False

        if len(selected_clips) == 0:
            utils.error("No clips to concatenate.")
            return False

        list_file = os.path.join(
            config.project_dir, f"concat_list_{random.randint(1000, 9999)}.txt"
        )

        with open(list_file, "w") as f:
            for clip in selected_clips:
                abs_clip_path = os.path.abspath(clip)
                f.write(f"file '{abs_clip_path}'\n")

        command = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_file,
            "-c",
            "copy",
            "-video_track_timescale",
            "90000",
            "-y",
            self.file,
        ]

        try:
            result = self.run_process(command, self.concat_timeout)

            if result.returncode != 0:
                utils.error("Error concatenating clips:")
                utils.error(result.stderr)
            else:
                self.files.append(self.file)
                utils.info(f"Saved: {self.file}")

        except subprocess.TimeoutExpired:
            utils.error("Timeout expired while concatenating clips.")
            return False

        return True

    def get_stream_info(self, url: str) -> dict[str, Any]:
        command = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            url,
        ]

        info = {"duration": 0.0, "width": 0, "height": 0}

        try:
            result = self.run_process(command, self.probe_timeout)
        except subprocess.TimeoutExpired:
            utils.error(f"Timeout expired probing stream info for {url}.")
            return info

        if result.returncode != 0:
            return info

        try:
            metadata = json.loads(result.stdout)

            if "format" in metadata:
                if "duration" in metadata["format"]:
                    info["duration"] = float(metadata["format"]["duration"])

            if "streams" in metadata:
                for stream in metadata["streams"]:
                    if stream.get("codec_type") == "video":
                        info["width"] = int(stream.get("width", 0))
                        info["height"] = int(stream.get("height", 0))
                        break
        except Exception:
            pass

        return info

    def cleanup(self) -> None:
        shutil.rmtree(config.project_dir, ignore_errors=True)


engine = Engine()
