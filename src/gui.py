import tkinter as tk
from tkinter import simpledialog, filedialog, messagebox, ttk
import sys
import importlib
import os
import threading
from typing import Any, Callable

from info import info
from utils import utils
import config as config_module
from data import data

config = config_module.config

URLS: list[str] = []
ROW: int = 0
INSTANCE = None

# Style
BG_COLOR = "#121212"
WIDGET_BG = "#242424"
TEXT_COLOR = "#ff2a6d"
TEXT_COLOR_2 = "#ffffff"
ACCENT_COLOR = "#05d9e8"
DISABLED_BG = "#333333"
DISABLED_FG = "#777777"


def main() -> None:
    utils.set_proc_name(info.name)
    main_window = tk.Tk(className="hugegull")
    GUI(main_window)
    main_window.mainloop()


def update_progress(text: str) -> None:
    """Updates the progress label from any thread or module."""
    if INSTANCE is not None:
        INSTANCE.root.after(0, lambda: INSTANCE.progress_var.set(text))


def get_resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS  # type: ignore
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)


class GUI:
    def __init__(self, root: tk.Tk) -> None:
        global ROW
        global INSTANCE

        INSTANCE = self

        self.entries: dict[str, tk.Entry] = {}
        self.string_vars: dict[str, tk.StringVar] = {}
        self.bool_vars: dict[str, tk.BooleanVar] = {}
        self.labels: dict[str, tk.Label] = {}
        self.current_config_name: str = ""
        self.root = root
        self.root.title("Huge Gull")
        self.root.geometry("720x550")
        self.root.configure(bg=BG_COLOR)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.is_running: bool = False

        icon_path = get_resource_path("icon.png")

        if os.path.exists(icon_path):
            self.icon_img = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(True, self.icon_img)

        self.version_label = tk.Label(
            root,
            text=f"v{info.version}",
            bg=BG_COLOR,
            fg=DISABLED_FG,
            font=("helvetica", 10),
        )

        self.version_label.place(relx=1.0, y=20, x=-20, anchor="ne")

        # Progress Widget setup
        self.progress_var = tk.StringVar(value="")

        self.progress_label = tk.Label(
            root,
            textvariable=self.progress_var,
            bg=BG_COLOR,
            fg=TEXT_COLOR_2,
            font=("helvetica", 10, "bold"),
            justify="center",
        )

        # Placed to the left of the version text, expanding backwards
        self.progress_label.place(relx=1.0, y=20, x=-80, anchor="ne")

        self.url_label = tk.Label(
            root,
            text="Source URLs",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("helvetica", 12),
            cursor="hand2",
        )

        self.url_label.pack(pady=(20, 5), padx=20, anchor="w")
        self.url_label.bind("<Button-1>", self.paste_urls)
        self.url_label.bind("<Button-2>", self.clear_urls)
        self.url_label.bind("<Enter>", lambda e: self.url_label.config(fg=ACCENT_COLOR))
        self.url_label.bind("<Leave>", lambda e: self.url_label.config(fg=TEXT_COLOR))

        # Frame to hold the Text widget and Scrollbar
        self.url_frame = tk.Frame(root, bg=BG_COLOR)
        self.url_frame.pack(padx=20, fill=tk.BOTH, expand=False)

        # Apply ttk style for the scrollbar
        style = ttk.Style()

        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(
            "Vertical.TScrollbar",
            background=WIDGET_BG,
            troughcolor=BG_COLOR,
            bordercolor=BG_COLOR,
            arrowcolor=ACCENT_COLOR,
            lightcolor=WIDGET_BG,
            darkcolor=WIDGET_BG,
        )

        # Map dynamic states (disabled, active/hover, pressed) to dark colors
        style.map(
            "Vertical.TScrollbar",
            background=[
                ("disabled", BG_COLOR),
                ("pressed", "#444444"),
                ("active", "#333333"),
            ],
            arrowcolor=[("disabled", DISABLED_BG)],
            troughcolor=[("disabled", BG_COLOR)],
            lightcolor=[
                ("disabled", BG_COLOR),
                ("pressed", "#444444"),
                ("active", "#333333"),
            ],
            darkcolor=[
                ("disabled", BG_COLOR),
                ("pressed", "#444444"),
                ("active", "#333333"),
            ],
            bordercolor=[("disabled", BG_COLOR)],
        )

        self.url_scrollbar = ttk.Scrollbar(
            self.url_frame, orient="vertical", style="Vertical.TScrollbar"
        )

        self.url_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.url_text = tk.Text(
            self.url_frame,
            height=6,
            bg=WIDGET_BG,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("helvetica", 12),
            yscrollcommand=self.url_scrollbar.set,
            padx=4,
            pady=4,
        )

        self.url_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.url_scrollbar.config(command=self.url_text.yview)

        # Bindings for Select All, dynamic counting, and focus traversal
        self.url_text.bind("<Control-a>", self.select_all)
        self.url_text.bind("<Control-A>", self.select_all)
        self.url_text.bind("<Tab>", self.focus_next_widget)
        self.url_text.bind("<Shift-Tab>", self.focus_prev_widget)
        self.url_text.bind("<ISO_Left_Tab>", self.focus_prev_widget)

        if len(config.urls) > 0:
            self.url_text.insert(tk.END, "\n".join(config.urls))

        self.settings_frame = tk.Frame(root, bg=BG_COLOR)
        self.settings_frame.pack(pady=(30, 10), padx=0, fill=tk.X)

        c_col = 0

        self.text_entry("path", self.settings_frame, "Path", config.path, c_col)
        self.text_entry("name", self.settings_frame, "Name", "", c_col)
        self.text_entry("fps", self.settings_frame, "FPS", config.fps, c_col)
        self.text_entry("crf", self.settings_frame, "CRF", config.crf, c_col)

        gpu_choices = []

        for action in config.parser._actions:
            if action.dest == "gpu" and action.choices:
                gpu_choices = list(action.choices)
                break

        self.combo_entry(
            "gpu",
            self.settings_frame,
            "GPU",
            gpu_choices,
            config.gpu,
            c_col,
        )

        self.checkbox_entry("open", self.settings_frame, "Open", config.open, c_col)

        ROW = 0
        c_col = 3

        self.text_entry(
            "duration", self.settings_frame, "Duration", config.duration, c_col
        )

        self.text_entry(
            "clip_duration",
            self.settings_frame,
            "Clip Duration",
            config.clip_duration,
            c_col,
        )

        self.text_entry(
            "clip_diff", self.settings_frame, "Clip Diff", config.clip_diff, c_col
        )

        self.text_entry("fade", self.settings_frame, "Fade", config.fade, c_col)
        self.text_entry("amount", self.settings_frame, "Amount", config.amount, c_col)

        self.button_frame = tk.Frame(root, bg=BG_COLOR)
        self.button_frame.pack(side=tk.BOTTOM, pady=(0, 20))

        self.default_button = tk.Button(
            self.button_frame,
            text="Default",
            command=self.default_config,
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

        self.default_button.pack(side=tk.LEFT, padx=(0, 10), ipadx=0, ipady=0)
        self.load_button.pack(side=tk.LEFT, padx=(0, 10), ipadx=0, ipady=0)
        self.save_button.pack(side=tk.LEFT, padx=(0, 10), ipadx=0, ipady=0)
        self.make_button.pack(side=tk.LEFT, padx=(0, 0), ipadx=0, ipady=0)

    def focus_next_widget(self, event: Any) -> str:
        event.widget.tk_focusNext().focus()
        return "break"

    def focus_prev_widget(self, event: Any) -> str:
        event.widget.tk_focusPrev().focus()
        return "break"

    def select_all(self, event: Any = None) -> str:
        self.url_text.tag_add(tk.SEL, "1.0", tk.END)
        self.url_text.mark_set(tk.INSERT, "1.0")
        self.url_text.see(tk.INSERT)
        return "break"

    def clear_urls(self, event: Any = None) -> None:
        self.url_text.delete("1.0", tk.END)
        self.update_url_count()

    def clean_urls(self, event: Any = None) -> None:
        try:
            cursor_pos = self.url_text.index(tk.INSERT)
        except tk.TclError:
            cursor_pos = "1.0"

        raw_text = self.url_text.get("1.0", "end-1c")

        if raw_text == "":
            self.update_url_count()
            return

        lines = raw_text.split("\n")
        unique_lines = []
        seen = set()

        for line in lines:
            if line not in seen:
                unique_lines.append(line)
                seen.add(line)

        new_text = "\n".join(unique_lines)

        if new_text != raw_text:
            self.url_text.delete("1.0", tk.END)
            self.url_text.insert("1.0", new_text)

            try:
                self.url_text.mark_set(tk.INSERT, cursor_pos)
            except tk.TclError:
                pass

        self.update_url_count()

    def paste_urls(self, event: Any = None) -> None:
        try:
            clipboard_content = self.root.clipboard_get()
        except tk.TclError:
            return

        if not clipboard_content:
            return

        current_text = self.url_text.get("1.0", "end-1c")

        if current_text != "":
            if not current_text.endswith("\n"):
                self.url_text.insert(tk.END, "\n")

        self.url_text.insert(tk.END, clipboard_content.strip())
        self.clean_urls()

    def update_url_count(self, event: Any = None) -> None:
        raw_text = self.url_text.get("1.0", tk.END).strip()

        if raw_text == "":
            count = 0
        else:
            count = len(raw_text.split("\n"))

        self.url_label.config(text=f"Source URLs ({count})")

    def show_info_msg(self, id_: str) -> None:
        help_text = "No help available for this setting."

        for action in config.parser._actions:
            if action.dest == id_:
                if action.help:
                    help_text = action.help
                break

        messagebox.showinfo("Config Information", help_text)

    def make_help_cmd(self, id_: str) -> Callable[[], None]:
        return lambda: self.show_info_msg(id_)

    def text_entry(
        self, id_: str, frame: tk.Frame, text: str, value: Any, col: int
    ) -> None:
        global ROW

        label = tk.Label(
            frame,
            text=text,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("helvetica", 12),
        )

        label.grid(row=ROW, column=col, sticky="e", padx=(10, 10), pady=0)
        self.labels[id_] = label

        entry_frame = tk.Frame(frame, bg=WIDGET_BG)
        entry_frame.grid(row=ROW, column=col + 1, pady=5)

        entry = tk.Entry(
            entry_frame,
            bg=WIDGET_BG,
            fg=TEXT_COLOR_2,
            insertbackground=TEXT_COLOR,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("monospace", 12),
        )

        entry.pack(padx=4, pady=4)
        entry.insert(0, str(value))
        self.entries[id_] = entry

        help_btn = tk.Button(
            frame,
            text="?",
            command=self.make_help_cmd(id_),
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            activebackground=BG_COLOR,
            activeforeground=TEXT_COLOR,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("helvetica", 10, "bold"),
            cursor="hand2",
            takefocus=0,
        )

        help_btn.grid(row=ROW, column=col + 2, padx=(5, 10))
        ROW += 1

    def combo_entry(
        self,
        id_: str,
        frame: tk.Frame,
        text: str,
        options: list[str],
        value: str,
        col: int,
    ) -> None:
        global ROW

        label = tk.Label(
            frame,
            text=text,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("helvetica", 12),
        )

        label.grid(row=ROW, column=col, sticky="e", padx=(10, 10), pady=0)
        self.labels[f"{id_}_combo"] = label

        var = tk.StringVar(value=value)
        self.string_vars[id_] = var

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

        help_btn = tk.Button(
            frame,
            text="?",
            command=self.make_help_cmd(id_),
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            activebackground=BG_COLOR,
            activeforeground=TEXT_COLOR,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("helvetica", 10, "bold"),
            cursor="hand2",
            takefocus=0,
        )

        help_btn.grid(row=ROW, column=col + 2, padx=(5, 10))
        ROW += 1

    def checkbox_entry(
        self, id_: str, frame: tk.Frame, text: str, value: Any, col: int
    ) -> None:
        global ROW

        label = tk.Label(
            frame,
            text=text,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("helvetica", 12),
        )

        label.grid(row=ROW, column=col, sticky="e", padx=(10, 10), pady=0)
        self.labels[id_] = label

        var = tk.BooleanVar(value=bool(value))
        self.bool_vars[id_] = var

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

        help_btn = tk.Button(
            frame,
            text="?",
            command=self.make_help_cmd(id_),
            bg=BG_COLOR,
            fg=ACCENT_COLOR,
            activebackground=BG_COLOR,
            activeforeground=TEXT_COLOR,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=("helvetica", 10, "bold"),
            cursor="hand2",
            takefocus=0,
        )

        help_btn.grid(row=ROW, column=col + 2, padx=(5, 10))
        ROW += 1

    def update_entry(self, entry_widget: tk.Entry, new_value: Any) -> None:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, str(new_value))

    def save_config(self) -> None:
        config_name = simpledialog.askstring(
            "Save Config",
            "Enter config name (e.g. my_preset):",
            parent=self.root,
            initialvalue=self.current_config_name,
        )

        if not config_name:
            return

        config_name = config_name.strip()

        if config_name.endswith(".toml"):
            self.current_config_name = config_name[:-5]
        else:
            self.current_config_name = config_name
            config_name = f"{config_name}.toml"

        save_dir = os.path.expanduser("~/.config/hugegull/configs")

        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)

        save_path = os.path.join(save_dir, config_name)
        path_val = self.entries["path"].get().strip()
        gpu_val = self.string_vars["gpu"].get().strip()
        fps_val = self.entries["fps"].get().strip()
        crf_val = self.entries["crf"].get().strip()
        duration_val = self.entries["duration"].get().strip()
        clip_duration_val = self.entries["clip_duration"].get().strip()
        clip_diff_val = self.entries["clip_diff"].get().strip()
        fade_val = self.entries["fade"].get().strip()
        amount_val = self.entries["amount"].get().strip()
        open_val = self.bool_vars["open"].get()
        name = self.entries["name"].get()

        toml_lines = [
            f'path = "{path_val}"',
            f'name = "{name}"',
            f'gpu = "{gpu_val}"',
            f"fps = {fps_val}",
            f"crf = {crf_val}",
            f"duration = {duration_val}",
            f"clip_duration = {clip_duration_val}",
            f"clip_diff = {clip_diff_val}",
            f"fade = {fade_val}",
            f"amount = {amount_val}",
        ]

        if open_val:
            toml_lines.append("open = true")
        else:
            toml_lines.append("open = false")

        with open(save_path, "w") as f:
            f.write("\n".join(toml_lines))

        print(f"Config successfully saved to {save_path}")

    def load_config(self) -> None:
        load_dir = os.path.expanduser("~/.config/hugegull/configs")

        if not os.path.exists(load_dir):
            os.makedirs(load_dir, exist_ok=True)

        config_path = filedialog.askopenfilename(
            initialdir=load_dir,
            title="Select Config",
            filetypes=[("TOML files", "*.toml"), ("All files", "*.*")],
        )

        if not config_path:
            return

        self.current_config_name = os.path.splitext(os.path.basename(config_path))[0]

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
        self.update_config()
        self.update_entry(self.entries["path"], config.path)
        self.update_entry(self.entries["name"], config.name)
        self.update_entry(self.entries["fps"], config.fps)
        self.update_entry(self.entries["crf"], config.crf)
        self.update_entry(self.entries["duration"], config.duration)
        self.update_entry(self.entries["clip_duration"], config.clip_duration)
        self.update_entry(self.entries["clip_diff"], config.clip_diff)
        self.update_entry(self.entries["fade"], config.fade)
        self.update_entry(self.entries["amount"], config.amount)
        self.string_vars["gpu"].set(config.gpu)
        self.bool_vars["open"].set(bool(config.open))

    def update_config(self) -> None:
        importlib.reload(config_module)

        # Update the existing object in place
        config.__dict__.update(config_module.config.__dict__)

        # FORCE the module namespace to point back to our unified object
        config_module.config = config

    def default_config(self) -> None:
        self.current_config_name = ""
        sys.argv = [sys.argv[0]]
        self.update_config()
        self.update_entry(self.entries["path"], config.path)
        self.update_entry(self.entries["name"], config.name)
        self.update_entry(self.entries["fps"], config.fps)
        self.update_entry(self.entries["crf"], config.crf)
        self.update_entry(self.entries["duration"], config.duration)
        self.update_entry(self.entries["clip_duration"], config.clip_duration)
        self.update_entry(self.entries["clip_diff"], config.clip_diff)
        self.update_entry(self.entries["fade"], config.fade)
        self.update_entry(self.entries["amount"], config.amount)
        self.string_vars["gpu"].set(config.gpu)
        self.bool_vars["open"].set(bool(config.open))

    def make_video(self) -> None:
        import main

        if self.is_running:
            self.make_button.config(
                state=tk.DISABLED,
                text="Aborting",
                bg=DISABLED_BG,
                fg=DISABLED_FG,
                cursor="arrow",
            )

            data.abort = True
            return

        self.is_running = True
        data.abort = False

        # Reset progress label on each run
        self.progress_var.set("")

        self.clean_urls()
        raw_urls = self.url_text.get("1.0", tk.END).strip()
        urls = list(map(lambda e: e.strip(), raw_urls.split("\n")))

        props = {
            "urls": urls,
            "path": self.entries["path"].get().strip(),
            "name": self.entries["name"].get().strip(),
            "gpu": self.string_vars["gpu"].get().strip(),
            "fps": self.entries["fps"].get().strip(),
            "crf": self.entries["crf"].get().strip(),
            "duration": self.entries["duration"].get().strip(),
            "clip_duration": self.entries["clip_duration"].get().strip(),
            "clip_diff": self.entries["clip_diff"].get().strip(),
            "fade": self.entries["fade"].get().strip(),
            "amount": self.entries["amount"].get().strip(),
            "open": self.bool_vars["open"].get(),
        }

        config.update(props)

        self.make_button.config(
            state=tk.NORMAL,
            text="Working",
            bg=TEXT_COLOR,  # Using the pinkish/red text color to indicate a stop action
            fg=BG_COLOR,
            cursor="hand2",
        )

        def thread_target() -> None:
            try:
                # Run the heavy task in the background thread
                main.run()
            finally:
                self.is_running = False

                self.root.after(
                    0,
                    lambda: self.make_button.config(
                        state=tk.NORMAL,
                        text="Make",
                        bg=ACCENT_COLOR,
                        fg=BG_COLOR,
                        cursor="hand2",
                    ),
                )

                update_progress("")
                config.name = self.entries["name"].get()


        threading.Thread(target=thread_target, daemon=True).start()

    def on_closing(self) -> None:
        from engine import engine

        if self.is_running:
            data.abort = True

        engine.kill_all_processes()

        self.root.destroy()
        os._exit(0)


if __name__ == "__main__":
    main()
