from __future__ import annotations

import os
import random
import subprocess
import json
import shutil
import time
import threading
import concurrent.futures
from typing import Any

from config import config
from utils import utils
from data import data
import gui

import webrtcvad  # type: ignore


class Engine:
    def __init__(self) -> None:
        self.sources: list[dict[str, Any]] = []
        self.clips: dict[str, float] = {}
        self.workers = 3
        self.max_width = 0
        self.max_height = 0
        self.clip_timeout = 120
        self.resolve_timeout = 60
        self.concat_timeout = 120
        self.probe_timeout = 15
        self.min_clip_duration = 0.5
        self.active_processes: list[subprocess.Popen[str]] = []
        self.files: list[str] = []
        self.live_locks: dict[str, threading.Lock] = {}
        self.lock_mutex = threading.Lock()

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
        ext = config.format
        self.file = os.path.join(config.output_dir, f"{config.name}.{ext}")
        counter = 2

        while os.path.exists(self.file):
            self.file = os.path.join(
                config.output_dir, f"{config.name}_{counter}.{ext}"
            )

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

        if (width > 0) and (height > 0):
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

    def reset_engine(self) -> None:
        self.sources.clear()
        self.clips.clear()
        self.files.clear()
        self.max_width = 0
        self.max_height = 0

    def start(self) -> bool:
        if data.abort:
            return False

        self.reset_engine()
        config.check_name()
        gui.update_progress("Starting")
        utils.info(f"Starting: {config.name} | {int(config.duration)}s")
        os.makedirs(config.project_dir, exist_ok=True)
        self.prepare_sources()

        if len(self.sources) == 0:
            utils.info("No valid sources found in the pool. Stream is invalid.")
            self.cleanup()
            return False

        amount = config.amount or 1
        total_needed_duration = config.duration * amount
        buffer_duration = total_needed_duration * 1.3
        utils.info(f"Generating clip pool for {amount} videos...")
        self.generate_random_clips(buffer_duration, total_needed_duration)

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
            is_live = source["duration"] == 0.0
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

            if current_sum + clip_length > target_duration:
                clip_length = target_duration - current_sum

            if clip_length < min_cd:
                clip_length = min_cd

            if is_live:
                start = 0.0
            else:
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
        base_duration = section["duration"]
        v_data = source["v_data"]
        a_url = source["a_url"]
        is_split_stream = False
        is_live = source.get("duration", 0.0) == 0.0

        if a_url is not None:
            is_split_stream = True

        use_local_cache = False

        if config.audio == "":
            if not is_live:
                if str(v_data).startswith("http"):
                    use_local_cache = True

        ext = config.format
        name = os.path.join(config.project_dir, f"temp_clip_{i + 1}.{ext}")
        local_cache_file = os.path.join(config.project_dir, f"local_cache_{i + 1}.mkv")

        if use_local_cache:
            dl_duration = base_duration + 5.0
            dl_cmd = ["ffmpeg", "-ss", str(start), "-i", v_data]

            if is_split_stream:
                dl_cmd.extend(["-ss", str(start), "-i", a_url])
                dl_cmd.extend(["-map", "0:v:0", "-map", "1:a:0"])
            else:
                dl_cmd.extend(["-map", "0:v:0", "-map", "0:a:0?"])

            dl_cmd.extend(
                ["-t", str(dl_duration), "-c", "copy", "-y", local_cache_file]
            )

            res = self.run_process(dl_cmd, self.clip_timeout)

            if res.returncode == 0:
                # Override network vars to use our fast local file
                v_data = local_cache_file
                a_url = None
                is_split_stream = False
                start = 0.0
            else:
                utils.error(
                    f"Failed to create local cache for clip {i + 1}, falling back to network."
                )

                use_local_cache = False

        if config.audio != "":
            duration = base_duration
        else:
            if is_live:
                duration = base_duration
            else:
                duration = self.find_silence_end(
                    v_data=v_data,
                    a_url=a_url,
                    start=start,
                    min_dur=base_duration,
                    max_search=5.0,
                )

        modes_to_try = [config.gpu]

        if config.gpu in ("amd", "nvidia"):
            modes_to_try = [config.gpu, "cpu"]
        else:
            modes_to_try = ["cpu"]

        url_lock = None

        if is_live:
            with self.lock_mutex:
                if v_data not in self.live_locks:
                    self.live_locks[v_data] = threading.Lock()

                url_lock = self.live_locks[v_data]

            url_lock.acquire()

        try:
            for mode in modes_to_try:
                command = ["ffmpeg"]

                if mode == "amd":
                    command.extend(["-vaapi_device", "/dev/dri/renderD128"])
                elif mode == "nvidia":
                    command.extend(["-hwaccel", "cuda"])

                if not is_live:
                    command.extend(["-ss", str(start)])

                command.extend(["-i", v_data])

                if is_split_stream:
                    if not is_live:
                        command.extend(["-ss", str(start)])

                    command.extend(["-i", a_url])

                fade_out_start = duration - config.fade

                if config.resolution == "720p":
                    baseline = 720
                elif config.resolution == "1080p":
                    baseline = 1080
                elif config.resolution == "1440p":
                    baseline = 1440
                elif config.resolution == "4k":
                    baseline = 2160
                else:
                    baseline = min(self.max_width, self.max_height)

                if baseline == 0:
                    baseline = 720

                ratio_w = 16
                ratio_h = 9

                if config.aspect_ratio == "original":
                    if (self.max_width > 0) and (self.max_height > 0):
                        ratio_w = self.max_width
                        ratio_h = self.max_height
                else:
                    try:
                        parts = config.aspect_ratio.split(":")

                        if len(parts) == 2:
                            ratio_w = int(parts[0])
                            ratio_h = int(parts[1])
                    except (ValueError, AttributeError):
                        pass

                if ratio_w >= ratio_h:
                    pad_h = baseline
                    pad_w = int(baseline * ratio_w / ratio_h)
                else:
                    pad_w = baseline
                    pad_h = int(baseline * ratio_h / ratio_w)

                if pad_w % 2 != 0:
                    pad_w += 1

                if pad_h % 2 != 0:
                    pad_h += 1

                vf_filter = f"scale={pad_w}:{pad_h}:force_original_aspect_ratio=decrease,pad={pad_w}:{pad_h}:(ow-iw)/2:(oh-ih)/2,fps={config.fps},setsar=1"

                if config.watermark != "":
                    safe_text = config.watermark.replace(":", "\\:").replace("'", "\\'")
                    vf_filter = f"{vf_filter},drawtext=text='{safe_text}':fontcolor=white:fontsize=h/20:x=w-tw-20:y=h-th-20"

                if mode == "amd":
                    vf_filter = f"{vf_filter},format=nv12,hwupload"

                if config.audio != "":
                    command.extend(["-t", str(duration), "-vf", vf_filter])
                    command.extend(["-map", "0:v:0", "-an"])
                else:
                    af_filter = f"afade=t=in:st=0:d={config.fade},afade=t=out:st={fade_out_start}:d={config.fade}"

                    command.extend(
                        ["-t", str(duration), "-vf", vf_filter, "-af", af_filter]
                    )

                    if is_split_stream:
                        command.extend(["-map", "0:v:0", "-map", "1:a:0"])
                    else:
                        command.extend(["-map", "0:v:0", "-map", "0:a:0?"])

                    command.extend(["-c:a", "aac", "-ar", "48000", "-ac", "2"])

                if mode == "amd":
                    adjusted_crf = config.crf - 4

                    if adjusted_crf < 0:
                        adjusted_crf = 0

                    command.extend(
                        [
                            "-c:v",
                            "h264_vaapi",
                            "-rc_mode",
                            "CQP",
                            "-qp",
                            str(adjusted_crf),
                        ]
                    )
                elif mode == "nvidia":
                    adjusted_crf = config.crf - 4

                    if adjusted_crf < 0:
                        adjusted_crf = 0

                    command.extend(
                        [
                            "-c:v",
                            "h264_nvenc",
                            "-cq",
                            str(adjusted_crf),
                            "-preset",
                            "p6",
                        ]
                    )
                else:
                    command.extend(
                        [
                            "-c:v",
                            "libx264",
                            "-preset",
                            "medium",
                            "-crf",
                            str(config.crf),
                        ]
                    )

                command.extend(["-video_track_timescale", "90000", "-y", name])
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
                    utils.error(
                        f"Timeout expired. Extracting clip {i + 1} using {mode}."
                    )

                    if mode != modes_to_try[-1]:
                        utils.info(f"Retrying clip {i + 1} with CPU fallback...")

                except Exception as e:
                    utils.error(f"Exception extracting clip {i + 1} using {mode}: {e}")

                    if mode != modes_to_try[-1]:
                        utils.info(f"Retrying clip {i + 1} with CPU fallback...")
        finally:
            if url_lock is not None:
                url_lock.release()

            if use_local_cache:
                if os.path.exists(local_cache_file):
                    try:
                        os.remove(local_cache_file)
                    except Exception:
                        pass

        return None

    def concatenate_clips(self, selected_clips: list[str]) -> bool:
        if data.abort:
            return False

        if len(selected_clips) == 0:
            utils.error("No clips to concatenate.")
            return False

        total_duration = 0.0

        for clip in selected_clips:
            total_duration += self.clips.get(clip, 0.0)

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
        ]

        if config.audio != "":
            command.extend(["-stream_loop", "-1", "-i", config.audio])

            command.extend(
                [
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "copy",
                    "-c:a",
                    "aac",
                    "-t",
                    str(total_duration),
                ]
            )
        else:
            command.extend(["-c", "copy"])

        command.extend(
            [
                "-video_track_timescale",
                "90000",
                "-y",
                self.file,
            ]
        )

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

    def generate_random_clips(
        self, target_duration: float, required_duration: float = 0.0
    ) -> None:
        if data.abort:
            return

        sections = self.generate_clip_sections(target_duration)
        accumulated_duration = 0.0

        if required_duration == 0.0:
            required_duration = target_duration

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
                    accumulated_duration += duration

                    if accumulated_duration >= required_duration:
                        for f in futures:
                            f.cancel()
                        break

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

    def find_silence_end(
        self,
        v_data: str,
        a_url: str | None,
        start: float,
        min_dur: float,
        max_search: float = 5.0,
    ) -> float:
        search_start = start + min_dur
        target_url = a_url

        if target_url is None:
            target_url = v_data

        # webrtcvad requires exactly 16kHz, 1-channel (mono), 16-bit PCM audio
        command = [
            "ffmpeg",
            "-ss",
            str(search_start),
            "-i",
            target_url,
            "-t",
            str(max_search),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-f",
            "s16le",
            "-",
        ]

        try:
            # We bypass self.run_process here because we need stdout as raw bytes, not text
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.probe_timeout,
            )

            if process.returncode != 0:
                return min_dur

            audio_data = process.stdout

            # Aggressiveness mode from 0 to 3. 2 is usually a good middle ground for noisy audio.
            vad = webrtcvad.Vad(2)

            sample_rate = 16000
            # webrtcvad requires frame durations of 10, 20, or 30 ms. We use 30ms.
            frame_duration_ms = 30
            frame_size = int(sample_rate * (frame_duration_ms / 1000.0) * 2)

            consecutive_silence_frames = 0

            # Target ~0.6 seconds of consecutive silence to clear a full breath/pause
            required_silence_frames = int(600 / frame_duration_ms)

            for i in range(0, len(audio_data) - frame_size, frame_size):
                frame = audio_data[i : i + frame_size]

                is_speech = vad.is_speech(frame, sample_rate)

                if not is_speech:
                    consecutive_silence_frames += 1
                else:
                    consecutive_silence_frames = 0

                if consecutive_silence_frames >= required_silence_frames:
                    bytes_processed = i + frame_size
                    current_offset_sec = bytes_processed / (sample_rate * 2)

                    silence_duration_sec = (
                        required_silence_frames * frame_duration_ms
                    ) / 1000.0

                    # Back up to the exact moment speech ended, then add a 0.25s natural breathing buffer
                    final_offset = current_offset_sec - silence_duration_sec + 0.25

                    if final_offset < 0:
                        final_offset = 0

                    return min_dur + final_offset

        except Exception:
            pass

        return min_dur


engine = Engine()
