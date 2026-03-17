import os
import sys
import socket
import hashlib
import tempfile
import importlib
import threading
import tkinter as tk
from typing import cast
from typing import Any, Callable
from tkinter import simpledialog, filedialog, messagebox, ttk

from info import info
from utils import utils
import config as config_module
from data import data

config = config_module.config

WIDTH = 624
HEIGHT = 588
ROW: int = 0
INSTANCE = None
BG_COLOR = "#121212"
WIDGET_BG = "#242424"
TEXT_COLOR = "#ff2a6d"
TEXT_COLOR_2 = "#ffffff"
ACCENT_COLOR = "#05d9e8"
DISABLED_BG = "#333333"
DISABLED_FG = "#777777"
SMALL_BUTTON_BG = "#6e838b"
SMALL_BUTTON_FG = "#ffffff"
BUTTON_FONT = ("monospace", 11, "bold")
FONT_1 = ("helvetica", 10, "bold")
FONT_2 = ("helvetica", 10)
FONT_3 = ("helvetica", 12)
FONT_4 = ("monospace", 12)


def main() -> None:
    utils.set_proc_name(info.name)
    main_window = tk.Tk(className=info.name)
    main_window.minsize(WIDTH, HEIGHT)
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


class ToolTip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self.show_tip, add="+")
        self.widget.bind("<Leave>", self.hide_tip, add="+")

    def show_tip(self, event: Any = None) -> None:
        if self.tip_window is not None or self.text == "":
            return

        text_widget = cast(tk.Text, self.widget)
        bbox_result = text_widget.bbox("insert")

        if not bbox_result:
            return

        x, y, _, _ = bbox_result
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 20

        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tip_window,
            text=self.text,
            justify=tk.LEFT,
            background=WIDGET_BG,
            foreground=TEXT_COLOR_2,
            relief="solid",
            borderwidth=1,
            font=FONT_2,
            padx=5,
            pady=5,
            wraplength=300,
        )

        label.pack()

    def hide_tip(self, event: Any = None) -> None:
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


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
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.configure(bg=BG_COLOR)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._is_moving = False
        self._start_x = 0
        self._start_y = 0
        self._start_win_x = 0
        self._start_win_y = 0
        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.move_window)
        self.is_running: bool = False
        self.start_ipc_listener()

        icon_path = get_resource_path("icon.png")

        if os.path.exists(icon_path):
            self.icon_img = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(True, self.icon_img)

        self.url_header_frame = tk.Frame(root, bg=BG_COLOR)
        self.url_header_frame.pack(fill=tk.X, padx=20, pady=(20, 5))

        self.url_label = tk.Label(
            self.url_header_frame,
            text="URL List",
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=FONT_3,
            cursor="hand2",
        )

        self.url_label.pack(side=tk.LEFT)
        self.url_label.bind("<Button-1>", self.paste_urls)
        self.url_label.bind("<Button-2>", self.clear_urls)
        self.url_label.bind("<Enter>", lambda e: self.url_label.config(fg=ACCENT_COLOR))
        self.url_label.bind("<Leave>", lambda e: self.url_label.config(fg=TEXT_COLOR))
        ToolTip(self.url_label, self.get_help_text("urls"))
        self.checkbox_pack("open", self.url_header_frame, "Open", config.open)
        self.progress_var = tk.StringVar(value="")

        self.progress_label = tk.Label(
            root,
            textvariable=self.progress_var,
            bg=BG_COLOR,
            fg=TEXT_COLOR_2,
            font=FONT_1,
            justify="center",
        )

        self.progress_label.place(relx=1.0, y=20, x=-80, anchor="ne")

        self.version_label = tk.Label(
            root,
            text=f"v{info.version}",
            bg=BG_COLOR,
            fg=DISABLED_FG,
            font=FONT_2,
        )

        self.version_label.place(relx=1.0, y=20, x=-20, anchor="ne")
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
            font=FONT_3,
            yscrollcommand=self.url_scrollbar.set,
            padx=4,
            pady=4,
            spacing3=5,
        )

        self.url_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.url_scrollbar.config(command=self.url_text.yview)

        # Bindings for Select All, dynamic counting, and focus traversal
        self.url_text.bind("<Control-a>", self.select_all)
        self.url_text.bind("<Control-A>", self.select_all)
        self.url_text.bind("<Tab>", self.focus_next_widget)
        self.url_text.bind("<Shift-Tab>", self.focus_prev_widget)
        self.url_text.bind("<ISO_Left_Tab>", self.focus_prev_widget)
        self.url_text.bind("<KeyRelease>", self.update_url_count)
        self.url_text.bind("<FocusOut>", self.deselect_all)

        self.update_url_count()

        if len(config.urls) > 0:
            self.url_text.insert(tk.END, "\n".join(config.urls))

        self.settings_frame = tk.Frame(root, bg=BG_COLOR)
        self.settings_frame.pack(pady=(30, 10), padx=0, fill=tk.X)

        c_col = 0

        self.text_entry("name", self.settings_frame, "Name", "", c_col)
        self.text_entry("path", self.settings_frame, "Path", config.path, c_col)
        self.number_entry("fps", self.settings_frame, "FPS", config.fps, c_col)
        self.number_entry("crf", self.settings_frame, "CRF", config.crf, c_col)

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

        ar_choices = []

        for action in config.parser._actions:
            if action.dest == "aspect_ratio" and action.choices:
                ar_choices = list(action.choices)
                break

        self.combo_entry(
            "aspect_ratio",
            self.settings_frame,
            "Ratio",
            ar_choices,
            config.aspect_ratio,
            c_col,
        )

        self.text_entry("audio", self.settings_frame, "Audio", config.audio, c_col)

        ROW = 0
        c_col = 3

        self.number_entry("amount", self.settings_frame, "Amount", config.amount, c_col)

        self.number_entry(
            "duration", self.settings_frame, "Duration", config.duration, c_col
        )

        self.number_entry(
            "clip_duration",
            self.settings_frame,
            "Clip Duration",
            config.clip_duration,
            c_col,
        )

        self.number_entry(
            "clip_diff", self.settings_frame, "Clip Diff", config.clip_diff, c_col
        )

        self.number_entry("fade", self.settings_frame, "Fade", config.fade, c_col)

        res_choices = []

        for action in config.parser._actions:
            if action.dest == "resolution" and action.choices:
                res_choices = list(action.choices)
                break

        self.combo_entry(
            "resolution",
            self.settings_frame,
            "Resolution",
            res_choices,
            config.resolution,
            c_col,
        )

        self.text_entry(
            "watermark", self.settings_frame, "Watermark", config.watermark, c_col
        )

        self.button_frame = tk.Frame(root, bg=BG_COLOR)
        self.button_frame.pack(side=tk.BOTTOM, pady=(0, 20))

        self.exit_button = self.action_button("Exit", self.exit)
        self.default_button = self.action_button("Default", self.default_config)
        self.load_button = self.action_button("Load", self.load_config)
        self.save_button = self.action_button("Save", self.save_config)
        self.make_button = self.action_button("Make", self.make_video)

        self.exit_button.pack(side=tk.LEFT, padx=(0, 10), ipadx=0, ipady=0)
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
        if event is not None:
            if isinstance(event.widget, tk.Entry):
                event.widget.select_range(0, tk.END)
                event.widget.icursor(tk.END)
                return "break"

            if isinstance(event.widget, tk.Text):
                event.widget.tag_add(tk.SEL, "1.0", tk.END)
                event.widget.mark_set(tk.INSERT, "1.0")
                event.widget.see(tk.INSERT)
                return "break"

        self.url_text.tag_add(tk.SEL, "1.0", tk.END)
        self.url_text.mark_set(tk.INSERT, "1.0")
        self.url_text.see(tk.INSERT)
        return "break"

    def deselect_all(self, event: Any = None) -> None:
        if event is not None:
            if isinstance(event.widget, tk.Entry):
                event.widget.select_clear()

            if isinstance(event.widget, tk.Text):
                event.widget.tag_remove(tk.SEL, "1.0", tk.END)

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

        lines = clipboard_content.split("\n")

        for line in lines:
            text_line = line.strip()

            if not utils.is_path(text_line):
                continue

            current_text = self.url_text.get("1.0", "end-1c")

            if current_text != "":
                if not current_text.endswith("\n"):
                    self.url_text.insert(tk.END, "\n")

            self.url_text.insert(tk.END, text_line)

        self.clean_urls()

    def update_url_count(self, event: Any = None) -> None:
        raw_text = self.url_text.get("1.0", tk.END).strip()

        if raw_text == "":
            count = 0
        else:
            count = len(raw_text.split("\n"))

        self.url_label.config(text=f"URL List ({count})")

    def get_help_text(self, id_: str) -> str:
        help_text = "No help available for this setting."

        if id_ == "urls":
            help_text = "One URL per line. You can click the label to paste from the clipboard. Middle Clicking the label clears the textarea."
            return help_text

        for action in config.parser._actions:
            if action.dest == id_:
                if action.help is not None:
                    help_text = action.help
                break

        return help_text

    def get_default_value(self, id_: str) -> str:
        original_argv = sys.argv.copy()
        sys.argv = [sys.argv[0]]

        try:
            temp_config = config_module.Config()
            val = getattr(temp_config, id_, "")
        finally:
            sys.argv = original_argv

        return str(val)

    def show_info_msg(self, id_: str) -> None:
        help_text = "No help available for this setting."

        if id_ == "urls":
            help_text = "One URL per line. You can click the label to paste from the clipboard. Middle Clicking the label clears the textarea."
        else:
            for action in config.parser._actions:
                if action.dest == id_:
                    if action.help:
                        help_text = action.help
                    break

        messagebox.showinfo("Config Information", help_text)

    def action_button(self, text: str, cmd: Callable[[], None]) -> tk.Button:
        return tk.Button(
            self.button_frame,
            text=text,
            command=cmd,
            bg=ACCENT_COLOR,
            fg=BG_COLOR,
            font=BUTTON_FONT,
            activebackground=TEXT_COLOR,
            activeforeground=BG_COLOR,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
        )

    def text_entry(
        self, id_: str, frame: tk.Frame, text: str, value: Any, col: int
    ) -> None:
        global ROW

        label = tk.Label(
            frame,
            text=text,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=FONT_3,
        )

        label.grid(row=ROW, column=col, sticky="e", padx=(10, 10), pady=0)
        self.labels[id_] = label
        ToolTip(label, self.get_help_text(id_))
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
            font=FONT_4,
            width=20,
            justify="center",
        )

        entry.pack(padx=4, pady=4)
        entry.insert(0, str(value))
        entry.xview(tk.END)
        entry.bind("<Control-a>", self.select_all)
        entry.bind("<Control-A>", self.select_all)
        entry.bind("<FocusOut>", self.deselect_all)
        self.entries[id_] = entry

        def on_middle_click(event: Any) -> None:
            default_val = self.get_default_value(id_)
            self.update_entry(entry, default_val)

        label.bind("<Button-2>", on_middle_click)
        ROW += 1

    def number_entry(
        self, id_: str, frame: tk.Frame, text: str, value: Any, col: int
    ) -> None:
        global ROW

        label = tk.Label(
            frame,
            text=text,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=FONT_3,
        )

        label.grid(row=ROW, column=col, sticky="e", padx=(10, 10), pady=0)
        self.labels[id_] = label
        ToolTip(label, self.get_help_text(id_))

        entry_frame = tk.Frame(frame, bg=WIDGET_BG)
        entry_frame.grid(row=ROW, column=col + 1, pady=5, sticky="w")

        def change_value(amount: int) -> None:
            current_str = entry.get()
            try:
                if "." in current_str:
                    new_val = round(float(current_str) + amount, 2)
                else:
                    new_val = int(current_str) + amount

                entry.delete(0, tk.END)
                entry.insert(0, str(new_val))
            except ValueError:
                pass

        def decrement() -> None:
            change_value(-1)

        def increment() -> None:
            change_value(1)

        btn_minus = tk.Button(
            entry_frame,
            text="-",
            command=decrement,
            bg=SMALL_BUTTON_BG,
            fg=SMALL_BUTTON_FG,
            font=BUTTON_FONT,
            activebackground=TEXT_COLOR,
            activeforeground=BG_COLOR,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=0,
        )

        btn_minus.pack(side=tk.LEFT)

        entry = tk.Entry(
            entry_frame,
            bg=WIDGET_BG,
            fg=TEXT_COLOR_2,
            insertbackground=TEXT_COLOR,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            font=FONT_4,
            width=15,
            justify="center",
        )

        entry.pack(side=tk.LEFT, padx=4, pady=4)
        entry.insert(0, str(value))
        entry.xview(tk.END)
        entry.bind("<Control-a>", self.select_all)
        entry.bind("<Control-A>", self.select_all)
        entry.bind("<FocusOut>", self.deselect_all)
        self.entries[id_] = entry

        btn_plus = tk.Button(
            entry_frame,
            text="+",
            command=increment,
            bg=SMALL_BUTTON_BG,
            fg=SMALL_BUTTON_FG,
            font=BUTTON_FONT,
            activebackground=TEXT_COLOR,
            activeforeground=BG_COLOR,
            highlightthickness=0,
            relief="flat",
            cursor="hand2",
            padx=6,
            pady=0,
        )

        btn_plus.pack(side=tk.LEFT)

        def on_middle_click(event: Any) -> None:
            default_val = self.get_default_value(id_)
            self.update_entry(entry, default_val)

        label.bind("<Button-2>", on_middle_click)
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
            font=FONT_3,
        )

        label.grid(row=ROW, column=col, sticky="e", padx=(10, 10), pady=0)
        self.labels[f"{id_}_combo"] = label
        ToolTip(label, self.get_help_text(id_))
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
            font=FONT_3,
            anchor="center",
            padx=8,
        )

        dropdown["menu"].config(bg=WIDGET_BG, fg=TEXT_COLOR_2, font=FONT_3)
        dropdown.grid(row=ROW, column=col + 1, pady=5, sticky="ew")

        def on_middle_click(event: Any) -> None:
            default_val = self.get_default_value(id_)
            self.string_vars[id_].set(default_val)

        label.bind("<Button-2>", on_middle_click)
        ROW += 1

    def checkbox_pack(
        self,
        id_: str,
        frame: tk.Frame,
        text: str,
        value: Any,
        padx: tuple[int, int] | int = (30, 5),
    ) -> None:
        label = tk.Label(
            frame,
            text=text,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=FONT_3,
        )

        label.pack(side=tk.LEFT, padx=padx)
        self.labels[id_] = label
        ToolTip(label, self.get_help_text(id_))
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
            font=FONT_3,
        )

        checkbox.pack(side=tk.LEFT)

    def checkbox_entry(
        self, id_: str, frame: tk.Frame, text: str, value: Any, col: int
    ) -> None:
        global ROW

        label = tk.Label(
            frame,
            text=text,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=FONT_3,
        )

        label.grid(row=ROW, column=col, sticky="e", padx=(10, 10), pady=0)
        self.labels[id_] = label
        ToolTip(label, self.get_help_text(id_))
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
            font=FONT_3,
        )

        checkbox.grid(row=ROW, column=col + 1, sticky="w", pady=5)
        ROW += 1

    def update_entry(self, entry_widget: tk.Entry, new_value: Any) -> None:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, str(new_value))
        entry_widget.xview(tk.END)

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

        save_dir = os.path.expanduser(f"~/.config/{info.name}/configs")

        if not os.path.exists(save_dir):
            os.makedirs(save_dir, exist_ok=True)

        save_path = os.path.join(save_dir, config_name)
        path_val = self.entries["path"].get().strip()
        gpu_val = self.string_vars["gpu"].get().strip()
        aspect_ratio_val = self.string_vars["aspect_ratio"].get().strip()
        resolution_val = self.string_vars["resolution"].get().strip()
        fps_val = self.entries["fps"].get().strip()
        crf_val = self.entries["crf"].get().strip()
        duration_val = self.entries["duration"].get().strip()
        clip_duration_val = self.entries["clip_duration"].get().strip()
        clip_diff_val = self.entries["clip_diff"].get().strip()
        fade_val = self.entries["fade"].get().strip()
        amount_val = self.entries["amount"].get().strip()
        open_val = self.bool_vars["open"].get()
        name = self.entries["name"].get()
        watermark_val = self.entries["watermark"].get().strip()
        audio_val = self.entries["audio"].get().strip()

        toml_lines = [
            f'path = "{path_val}"',
            f'name = "{name}"',
            f'gpu = "{gpu_val}"',
            f'aspect_ratio = "{aspect_ratio_val}"',
            f'resolution = "{resolution_val}"',
            f"fps = {fps_val}",
            f"crf = {crf_val}",
            f"duration = {duration_val}",
            f"clip_duration = {clip_duration_val}",
            f"clip_diff = {clip_diff_val}",
            f"fade = {fade_val}",
            f"amount = {amount_val}",
            f'watermark = "{watermark_val}"',
            f'audio = "{audio_val}"',
        ]

        if open_val:
            toml_lines.append("open = true")
        else:
            toml_lines.append("open = false")

        with open(save_path, "w") as f:
            f.write("\n".join(toml_lines))

        print(f"Config successfully saved to {save_path}")

    def load_config(self) -> None:
        load_dir = os.path.expanduser(f"~/.config/{info.name}/configs")

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
        self.update_entry(self.entries["watermark"], config.watermark)
        self.update_entry(self.entries["audio"], config.audio)
        self.string_vars["gpu"].set(config.gpu)
        self.string_vars["aspect_ratio"].set(config.aspect_ratio)
        self.string_vars["resolution"].set(config.resolution)
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
        self.update_entry(self.entries["audio"], config.audio)
        self.update_entry(self.entries["watermark"], config.watermark)
        self.string_vars["gpu"].set(config.gpu)
        self.string_vars["aspect_ratio"].set(config.aspect_ratio)
        self.string_vars["resolution"].set(config.resolution)
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
            "aspect_ratio": self.string_vars["aspect_ratio"].get().strip(),
            "resolution": self.string_vars["resolution"].get().strip(),
            "fps": self.entries["fps"].get().strip(),
            "crf": self.entries["crf"].get().strip(),
            "duration": self.entries["duration"].get().strip(),
            "clip_duration": self.entries["clip_duration"].get().strip(),
            "clip_diff": self.entries["clip_diff"].get().strip(),
            "fade": self.entries["fade"].get().strip(),
            "amount": self.entries["amount"].get().strip(),
            "open": self.bool_vars["open"].get(),
            "watermark": self.entries["watermark"].get().strip(),
            "audio": self.entries["audio"].get().strip(),
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

    def raise_window(self) -> None:
        if self.root.state() == "iconic":
            self.root.deiconify()

        if os.name == "posix":
            self.root.withdraw()
            self.root.deiconify()

        self.root.attributes("-topmost", True)
        self.root.attributes("-topmost", False)
        self.root.lift()
        self.root.focus_force()

    def start_ipc_listener(self) -> None:
        def listener() -> None:
            if os.name == "posix":
                # Unix Domain Socket for Linux/Mac (X11 & Wayland)
                socket_path = os.path.join(
                    tempfile.gettempdir(), f"{info.name}_ipc.sock"
                )

                if os.path.exists(socket_path):
                    try:
                        os.remove(socket_path)
                    except OSError:
                        pass

                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                server.bind(socket_path)
            else:
                # Localhost TCP Socket for Windows
                port = (
                    50000 + int(hashlib.md5(info.name.encode()).hexdigest(), 16) % 10000
                )
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                try:
                    server.bind(("127.0.0.1", port))
                except OSError:
                    return

            server.listen(1)

            while True:
                try:
                    conn, _ = server.accept()
                    data = conn.recv(1024).decode("utf-8")

                    if data == "RAISE":
                        # Safely trigger the Tkinter event from the background thread
                        self.root.after(0, self.raise_window)

                    conn.close()
                except Exception:
                    break

        thread = threading.Thread(target=listener, daemon=True)
        thread.start()

    def start_move(self, event: Any) -> None:
        if isinstance(event.widget, (tk.Tk, tk.Frame, tk.Label)):
            self._is_moving = True
            self._start_x = event.x_root
            self._start_y = event.y_root
            self._start_win_x = self.root.winfo_x()
            self._start_win_y = self.root.winfo_y()
        else:
            self._is_moving = False

    def move_window(self, event: Any) -> None:
        if self._is_moving:
            dx = event.x_root - self._start_x
            dy = event.y_root - self._start_y
            x = self._start_win_x + dx
            y = self._start_win_y + dy
            self.root.geometry(f"+{x}+{y}")

    def exit(self) -> None:
        sys.exit(0)


if __name__ == "__main__":
    main()
