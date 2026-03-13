import tkinter as tk
import sys
import importlib
import config as config_module

config = config_module.config

URLS = []
ROW = 0

# Style
BG_COLOR = "#121212"
WIDGET_BG = "#242424"
TEXT_COLOR = "#ff2a6d"
TEXT_COLOR_2 = "#ffffff"
ACCENT_COLOR = "#05d9e8"

class VideoApp:
    def __init__(self, root):
        global ROW

        self.root = root
        self.root.title("HugeGull")

        self.root.geometry("640x550")
        self.root.configure(bg=BG_COLOR)

        self.url_label = tk.Label(
            root,
            text="Source URLs (one per line)",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("helvetica", 12),
        )

        self.url_label.pack(pady=(20, 5), padx=20, anchor="w")

        self.url_text = tk.Text(
            root,
            height=6,
            bg=WIDGET_BG,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("helvetica", 12),
        )

        self.url_text.pack(padx=20, fill=tk.X)

        if len(config.urls) > 0:
            self.url_text.insert(tk.END, "\n".join(config.urls))

        self.settings_frame = tk.Frame(root, bg=BG_COLOR)
        self.settings_frame.pack(pady=(30, 10), padx=0, fill=tk.X)

        self.text_entry("config", self.settings_frame, "Config", config.config, 0)
        self.text_entry("path", self.settings_frame, "Path", config.path, 0)
        self.text_entry("name", self.settings_frame, "Name", config.name, 0)

        gpu_val = "cpu"

        if config.gpu:
            gpu_val = config.gpu

        self.combo_entry("gpu", self.settings_frame, "GPU", ["cpu", "amd", "nvidia"], gpu_val, 0)

        self.text_entry("fps", self.settings_frame, "FPS", config.fps, 0)
        self.text_entry("crf", self.settings_frame, "CRF", config.crf, 0)

        ROW = 0

        self.text_entry("duration", self.settings_frame, "Duration", config.duration, 2)
        self.text_entry("clip_duration", self.settings_frame, "Clip Duration", config.clip_duration, 2)
        self.text_entry("clip_diff", self.settings_frame, "Clip Diff", config.clip_diff, 2)
        self.text_entry("fade", self.settings_frame, "Fade", config.fade, 2)
        self.text_entry("amount", self.settings_frame, "Amount", config.amount, 2)
        self.checkbox_entry("open", self.settings_frame, "Open", config.open, 2)

        self.button_frame = tk.Frame(root, bg=BG_COLOR)
        self.button_frame.pack(side=tk.BOTTOM, pady=(0, 20))

        self.make_button = tk.Button(
            self.button_frame,
            text="Make",
            command=self.make_video,
            bg=ACCENT_COLOR,
            fg=BG_COLOR,
            font=("monospace", 12, "bold"),
            activebackground=TEXT_COLOR,
            activeforeground=BG_COLOR,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )

        self.config_button = tk.Button(
            self.button_frame,
            text="Config",
            command=self.reload_config,
            bg=ACCENT_COLOR,
            fg=BG_COLOR,
            font=("monospace", 12, "bold"),
            activebackground=TEXT_COLOR,
            activeforeground=BG_COLOR,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )

        self.make_button.pack(side=tk.LEFT, padx=(0, 10), ipadx=0, ipady=0)
        self.config_button.pack(side=tk.LEFT, padx=(10, 0), ipadx=0, ipady=0)

    def text_entry(self, id_, frame, text, value, col):
        global ROW

        label = tk.Label(
            frame,
            text=text,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("helvetica", 12),
        )

        label.grid(row=ROW, column=col, sticky="e", padx=(10, 10), pady=0)
        setattr(self, f"{id_}_label", label)

        entry = tk.Entry(
            frame,
            bg=WIDGET_BG,
            fg=TEXT_COLOR_2,
            insertbackground=TEXT_COLOR,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("monospace", 12),
        )

        entry.grid(row=ROW, column=col + 1, pady=5, ipadx=8, ipady=4)
        entry.insert(0, str(value))
        setattr(self, f"{id_}_entry", entry)
        ROW += 1

    def combo_entry(self, id_, frame, text, options, value, col):
        global ROW

        label = tk.Label(
            frame,
            text=text,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("helvetica", 12),
        )

        label.grid(row=ROW, column=col, sticky="e", padx=(10, 10), pady=0)
        setattr(self, f"{id_}_label", label)

        var = tk.StringVar(value=value)
        setattr(self, f"{id_}_var", var)

        dropdown = tk.OptionMenu(
            frame,
            var,
            *options,
        )

        dropdown.config(
            bg=WIDGET_BG,
            fg=TEXT_COLOR_2,
            activebackground=BG_COLOR,
            activeforeground=TEXT_COLOR_2,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("helvetica", 12),
            anchor="w",
            padx=8,
        )

        dropdown["menu"].config(
            bg=WIDGET_BG,
            fg=TEXT_COLOR_2,
        )

        dropdown.grid(row=ROW, column=col + 1, pady=5, sticky="ew")
        setattr(self, f"{id_}_dropdown", dropdown)
        ROW += 1

    def checkbox_entry(self, id_, frame, text, value, col):
        global ROW

        label = tk.Label(
            frame,
            text=text,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("helvetica", 12),
        )

        label.grid(row=ROW, column=col, sticky="e", padx=(10, 10), pady=0)
        setattr(self, f"{id_}_label", label)

        var = tk.BooleanVar(value=bool(value))

        checkbox = tk.Checkbutton(
            frame,
            variable=var,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            activebackground=BG_COLOR,
            activeforeground=TEXT_COLOR,
            selectcolor=WIDGET_BG,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("helvetica", 12),
        )

        checkbox.grid(row=ROW, column=col + 1, sticky="w", pady=5)

        setattr(self, f"{id_}_checkbox", checkbox)
        setattr(self, f"{id_}_var", var)

        ROW += 1

    def update_entry(self, entry_widget, new_value):
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, str(new_value))

    def reload_config(self):
        global config
        config_path = self.config_entry.get().strip()
        new_argv = []
        skip_next = False

        for arg in sys.argv:

            if skip_next:
                skip_next = False
                continue

            if arg == "--config":
                skip_next = True
                continue

            if arg.startswith("--config="):
                continue

            new_argv.append(arg)

        sys.argv = new_argv

        if config_path != "":
            sys.argv.extend(["--config", config_path])

        importlib.reload(config_module)
        config = config_module.config

        self.url_text.delete("1.0", tk.END)

        if len(config.urls) > 0:
            self.url_text.insert(tk.END, "\n".join(config.urls))

        self.update_entry(self.path_entry, config.path)
        self.update_entry(self.name_entry, config.name)
        self.update_entry(self.fps_entry, config.fps)
        self.update_entry(self.crf_entry, config.crf)
        self.update_entry(self.duration_entry, config.duration)
        self.update_entry(self.clip_duration_entry, config.clip_duration)
        self.update_entry(self.clip_diff_entry, config.clip_diff)
        self.update_entry(self.fade_entry, config.fade)
        self.update_entry(self.amount_entry, config.amount)

        gpu_val = "cpu"

        if config.gpu:
            gpu_val = config.gpu

        self.gpu_var.set(gpu_val)
        self.open_var.set(bool(config.open))

    def make_video(self):
        raw_urls = self.url_text.get("1.0", tk.END).strip()

        if len(raw_urls) == 0:
            print("No URLs found in the text area.")
            return

        URLS = list(map(lambda e: e.strip(), raw_urls.split("\n")))
        print(URLS)

if __name__ == "__main__":
    main_window = tk.Tk()
    app = VideoApp(main_window)
    main_window.mainloop()