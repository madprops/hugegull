import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox
import sys
import importlib
import os
import time
import threading

import config as config_module
from engine import engine
from utils import utils
from main import run

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

        self.root.geometry("720x550")
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

        c_col = 0

        self.text_entry("path", self.settings_frame, "Path", config.path, c_col)
        self.text_entry("name", self.settings_frame, "Name", config.name, c_col)

        gpu_val = "cpu"

        if config.gpu:
            gpu_val = config.gpu

        self.text_entry("fps", self.settings_frame, "FPS", config.fps, c_col)
        self.text_entry("crf", self.settings_frame, "CRF", config.crf, c_col)
        self.combo_entry("gpu", self.settings_frame, "GPU", ["cpu", "amd", "nvidia"], gpu_val, c_col)
        self.checkbox_entry("open", self.settings_frame, "Open", config.open, c_col)

        ROW = 0
        c_col = 3

        self.text_entry("duration", self.settings_frame, "Duration", config.duration, c_col)
        self.text_entry("clip_duration", self.settings_frame, "Clip Duration", config.clip_duration, c_col)
        self.text_entry("clip_diff", self.settings_frame, "Clip Diff", config.clip_diff, c_col)
        self.text_entry("fade", self.settings_frame, "Fade", config.fade, c_col)
        self.text_entry("amount", self.settings_frame, "Amount", config.amount, c_col)

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

        self.save_button = tk.Button(
            self.button_frame,
            text="Save",
            command=self.save_config,
            bg=ACCENT_COLOR,
            fg=BG_COLOR,
            font=("monospace", 12, "bold"),
            activebackground=TEXT_COLOR,
            activeforeground=BG_COLOR,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )

        self.load_button = tk.Button(
            self.button_frame,
            text="Load",
            command=self.load_config,
            bg=ACCENT_COLOR,
            fg=BG_COLOR,
            font=("monospace", 12, "bold"),
            activebackground=TEXT_COLOR,
            activeforeground=BG_COLOR,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )

        self.load_button.pack(side=tk.LEFT, padx=(0, 10), ipadx=0, ipady=0)
        self.save_button.pack(side=tk.LEFT, padx=(0, 10), ipadx=0, ipady=0)
        self.make_button.pack(side=tk.LEFT, padx=(0, 0), ipadx=0, ipady=0)

    def show_info_msg(self, id_):
        help_text = "No help available for this setting."

        for action in config.parser._actions:
            if action.dest == id_:
                if action.help:
                    help_text = action.help
                break

        messagebox.showinfo("Config Information", help_text)

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

        help_btn = tk.Button(
            frame,
            text="?",
            command=lambda i=id_: self.show_info_msg(i),
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            activebackground=BG_COLOR,
            activeforeground=TEXT_COLOR,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("helvetica", 10, "bold"),
            cursor="hand2",
        )

        help_btn.grid(row=ROW, column=col + 2, padx=(5, 10))
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

        help_btn = tk.Button(
            frame,
            text="?",
            command=lambda i=id_: self.show_info_msg(i),
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            activebackground=BG_COLOR,
            activeforeground=TEXT_COLOR,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("helvetica", 10, "bold"),
            cursor="hand2",
        )

        help_btn.grid(row=ROW, column=col + 2, padx=(5, 10))
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

        help_btn = tk.Button(
            frame,
            text="?",
            command=lambda i=id_: self.show_info_msg(i),
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            activebackground=BG_COLOR,
            activeforeground=TEXT_COLOR,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("helvetica", 10, "bold"),
            cursor="hand2",
        )

        help_btn.grid(row=ROW, column=col + 2, padx=(5, 10))
        ROW += 1

    def update_entry(self, entry_widget, new_value):
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, str(new_value))

    def save_config(self):
        config_name = simpledialog.askstring(
            "Save Config",
            "Enter config name (e.g. my_preset):",
            parent=self.root
        )

        if not config_name:
            return

        config_name = config_name.strip()

        if not config_name.endswith(".toml"):
            config_name = f"{config_name}.toml"

        save_dir = os.path.expanduser("~/.config/hugegull/configs")

        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)

        save_path = os.path.join(save_dir, config_name)

        path_val = self.path_entry.get().strip()
        gpu_val = self.gpu_var.get().strip()
        fps_val = self.fps_entry.get().strip()
        crf_val = self.crf_entry.get().strip()
        duration_val = self.duration_entry.get().strip()
        clip_duration_val = self.clip_duration_entry.get().strip()
        clip_diff_val = self.clip_diff_entry.get().strip()
        fade_val = self.fade_entry.get().strip()
        amount_val = self.amount_entry.get().strip()
        open_val = self.open_var.get()

        toml_lines = [
            f'path = "{path_val}"',
            f'gpu = "{gpu_val}"',
            f'fps = {fps_val}',
            f'crf = {crf_val}',
            f'duration = {duration_val}',
            f'clip_duration = {clip_duration_val}',
            f'clip_diff = {clip_diff_val}',
            f'fade = {fade_val}',
            f'amount = {amount_val}',
        ]

        if open_val:
            toml_lines.append('open = true')
        else:
            toml_lines.append('open = false')

        with open(save_path, "w") as f:
            f.write("\n".join(toml_lines))

        print(f"Config successfully saved to {save_path}")

    def load_config(self):
        global config

        load_dir = os.path.expanduser("~/.config/hugegull/configs")

        if not os.path.exists(load_dir):
            os.makedirs(load_dir, exist_ok=True)

        config_path = filedialog.askopenfilename(
            initialdir=load_dir,
            title="Select Config",
            filetypes=[("TOML files", "*.toml"), ("All files", "*.*")]
        )

        if not config_path:
            return

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
        urls = list(map(lambda e: e.strip(), raw_urls.split("\n")))

        data = {
            "urls": urls,
            "path": self.path_entry.get().strip(),
            "name": self.name_entry.get().strip(),
            "gpu": self.gpu_var.get().strip(),
            "fps": self.fps_entry.get().strip(),
            "crf": self.crf_entry.get().strip(),
            "duration": self.duration_entry.get().strip(),
            "clip_duration": self.clip_duration_entry.get().strip(),
            "clip_diff": self.clip_diff_entry.get().strip(),
            "fade": self.fade_entry.get().strip(),
            "amount": self.amount_entry.get().strip(),
            "open": self.open_var.get(),
        }

        config.update(data)

        def thread_target():
            self.make_button.config(state=tk.DISABLED, text="Working...")
            run()
            self.make_button.config(state=tk.NORMAL, text="Make")

        threading.Thread(target=thread_target, daemon=True).start()

if __name__ == "__main__":
    main_window = tk.Tk()
    app = VideoApp(main_window)
    main_window.mainloop()