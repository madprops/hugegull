![](seagulls.jpg)

hugegull grabs random sections of variable durations from streaming videos and stitches them together into a single, cohesive highlight video.

It supports local files, YouTube links, Twitch streams, and direct `.m3u8` URLs.

## Installation

### Automatic (Recommended)

The easiest way to install hugegull is globally via `pipx` or `uv`:

```bash
pipx install git+https://github.com/madprops/hugegull --force
```

Or

```bash
uv tool install --python python git+https://github.com/madprops/hugegull.git
```

### Manual

Alternatively, you can clone the repository and set up a shell alias:

```bash
git clone https://github.com/madprops/hugegull ~/code/hugegull
alias hgg="python ~/code/hugegull/main.py"
```

---

## Usage

You can pass URLs directly to the program. The output name will be randomly generated unless specified.

**Basic Usage:**
```bash
hugegull "https://something.m3u8"
```

**Multiple Sources:**
```bash
hugegull "https://something.m3u8" "https://otherthing.m3u8"
# OR
hugegull --url "https://something.m3u8" --url "https://otherthing.m3u8"
```

**With Options:**
```bash
hugegull "https://something.m3u8" --name "nice video" --open
```

**Using Environment Variables:**
```bash
export HUGE_URL="https://something.m3u8" "https://otherthing.m3u8"
export HUGE_NAME="nice video"
hugegull
```

---

## Configuration

hugegull can be configured via Command Line Arguments, Environment Variables, or a TOML configuration file.

The default configuration file is located at `~/.config/hugegull/config.toml`. It is created automatically on your first run.

### Configuration File Example
```toml
path = "/home/memphis/toilet"
duration = 35.0
fps = 30
crf = 30
gpu = "amd"
amount = 1
fade = 0.03
```

### Options Reference

*Note: CLI arguments will always override TOML config settings.*

| Option | CLI Argument | TOML Key | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| **URLs** | `[urls]` or `--url` | `urls` | *None* | Source video URLs. |
| **Name** | `--name` | `name` | *Random* | Output filename. (Env: `HUGE_NAME`) |
| **Config Path** | `--config` | *N/A* | `~/.config/hugegull/config.toml` | Path to a custom TOML config file. |
| **Output Path** | `--path` | `path` | Script directory | Base directory for the `temp` and `output` folders. |
| **Open** | `--open` | *N/A* | `False` | Opens the final video file automatically when finished. |
| **GPU** | `--gpu` | `gpu` | `""` | Hardware acceleration identifier (e.g., "amd"). |
| **Amount** | `--amount` | `amount` | `1` | Total number of output videos to generate. |
| **Total Duration** | `--duration` | `duration` | `35` | Total target duration (in seconds) of the output video. |
| **FPS** | `--fps` | `fps` | `30` | Output video frames per second. |
| **CRF** | `--crf` | `crf` | `30` | Video quality/compression factor. |
| **Crossfade** | `--fade` | `fade` | `0.03` | Crossfade duration between clips. |
| **Clip Duration** | `--clip-duration`| `clip_duration`| `6.0` | Average duration for a single grabbed section. |
| **Clip Diff** | `--clip-diff`| `clip_diff`| `3.0` | The range around the clip duration, more or less. |
| **Player** | `--player`| `player`| `mpv` | Name of the video player to open files. |

---

## Shell Integration

To make running hugegull even faster, you can add these snippets to your shell configuration.

### Fish Shell (`~/.config/fish/config.fish`)

```fish
alias hgg="hugegull"
# Or if installed manually: alias hgg="python ~/code/hugegull/main.py"

function egull
  set -x HUGE_URL $argv[1]
end
```

Then you can do:
```fish
egull "https://something.m3u8" "https://otherthing.m3u8"
hgg
```

---

## GUI

There is a graphical user interface that can be spawned with `--gui`.

![](gui.png)