![](seagulls.jpg)

This gets random sections from a stream video.

Each section is of variable duration.

Then it joins them into a single video.

`--open` can be used to open the file when ready.

## Installation

### Automatic (Recommended)

You can simply use `pipx`:

`pipx install git+https://github.com/madprops/hugegull --force`

### Manual

git clone this somewhere.

Make a shell alias:

`alias hgg="python ~/code/hugegull/main.py"`

## Configuration

Edit `~/.config/hugegull/hugegull.toml`

It is empty but you can make it look like this:

```
path = "/home/memphis/toilet"
duration = 35
fps = 30
crf = 30
gpu = "amd"
```

## Usage

`hugegull https://something.m3u8`

Local, YouTube, and Twitch video urls work as well.

The name can be ommitted to use a random one.

---

Or:

`hugegull --url https://something.m3u8 --name "nice video" --open`

---

Or:

```
export HUGE_URL="https://something.m3u8"
export HUGE_NAME="nice video"
hugegull
```

---

Or:

`hugegull https://something.m3u8 https://otherthing.m3u8`

It supports multiple source arguments.

--

Or:

`hugegull --url https://something.m3u8 --url https://otherthing.m3u8`

---

Or:

```
export HUGE_URL="https://something.m3u8 https://otherthing.m3u8"
hugegull
```

## More

Suggested alias:

`alias hgg="hugegull"`

Or:

`alias hgg="python ~/code/hugegull/main.py"`

---

Suggested `fish` function:

```
function egull
  export HUGE_URL="$argv[1]"
end
```

Then you can do:

```
egull "https://something.m3u8 https://otherthing.m3u8"
hgg
```