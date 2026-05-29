import configparser
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

CONFIG_FILE = Path(__file__).with_name("LogViewer.ini")
CONFIG_SECTION = "RecentFiles"
SETTINGS_SECTION = "Settings"
FILTER_PRESETS_SECTION = "FilterPresets"
RECENT_FILTERS_SECTION = "RecentFilters"
MAX_RECENT_FILES = 10
MAX_RECENT_FILTERS = 5
DEFAULT_FILTER_PRESETS = ["error", "warning", "fatal"]
FILTER_SEPARATOR = "---------------- recent filters ----------------"

LIGHT_THEME = {
    "window_bg": "#cfd3d8",
    "panel_bg": "#cfd3d8",
    "input_bg": "#f6f7f8",
    "text_bg": "#f8f9fa",
    "text_fg": "#20242a",
    "button_bg": "#e6e8eb",
    "button_fg": "#20242a",
    "active_bg": "#d9dde1",
    "status_fg": "#3b424a",
}

DARK_THEME = {
    "window_bg": "#22262b",
    "panel_bg": "#22262b",
    "input_bg": "#2f353c",
    "text_bg": "#161a1f",
    "text_fg": "#e8edf2",
    "button_bg": "#343b44",
    "button_fg": "#edf2f7",
    "active_bg": "#414a55",
    "status_fg": "#bec7d1",
}


def load_text_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8", errors="replace") as file:
        return file.read()


def load_recent_files() -> list[str]:
    config = read_config()

    if CONFIG_SECTION not in config:
        return []

    recent_files = []
    for index in range(1, MAX_RECENT_FILES + 1):
        file_path = config[CONFIG_SECTION].get(f"file{index}", "").strip()
        if file_path and file_path not in recent_files:
            recent_files.append(file_path)

    return recent_files


def load_filter_presets() -> list[str]:
    config = read_config()

    if FILTER_PRESETS_SECTION not in config:
        return DEFAULT_FILTER_PRESETS.copy()

    return load_ordered_values(
        config,
        FILTER_PRESETS_SECTION,
        "filter",
        len(DEFAULT_FILTER_PRESETS) + 20,
    ) or DEFAULT_FILTER_PRESETS.copy()


def load_recent_filters(filter_presets: list[str]) -> list[str]:
    config = read_config()
    preset_lookup = {filter_text.lower() for filter_text in filter_presets}

    recent_filters = load_ordered_values(
        config,
        RECENT_FILTERS_SECTION,
        "filter",
        MAX_RECENT_FILTERS,
    )
    return [
        filter_text
        for filter_text in recent_filters
        if filter_text.lower() not in preset_lookup
    ]


def load_ordered_values(
    config: configparser.ConfigParser,
    section: str,
    key_prefix: str,
    max_count: int,
) -> list[str]:
    if section not in config:
        return []

    values = []
    value_lookup = set()
    for index in range(1, max_count + 1):
        value = config[section].get(f"{key_prefix}{index}", "").strip()
        lookup_value = value.lower()
        if value and lookup_value not in value_lookup:
            values.append(value)
            value_lookup.add(lookup_value)

    return values


def load_dark_mode() -> bool:
    config = read_config()
    return config.getboolean(SETTINGS_SECTION, "dark_mode", fallback=False)


def read_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if CONFIG_FILE.is_file():
        config.read(CONFIG_FILE, encoding="utf-8")
    return config


def write_config(
    recent_files: list[str],
    filter_presets: list[str],
    recent_filters: list[str],
    dark_mode: bool,
):
    config = configparser.ConfigParser()
    config[SETTINGS_SECTION] = {
        "dark_mode": "yes" if dark_mode else "no",
    }
    config[CONFIG_SECTION] = {
        f"file{index}": file_path
        for index, file_path in enumerate(recent_files[:MAX_RECENT_FILES], start=1)
    }
    config[FILTER_PRESETS_SECTION] = {
        f"filter{index}": filter_text
        for index, filter_text in enumerate(filter_presets, start=1)
    }
    config[RECENT_FILTERS_SECTION] = {
        f"filter{index}": filter_text
        for index, filter_text in enumerate(recent_filters[:MAX_RECENT_FILTERS], start=1)
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        config.write(file)


class LogViewerApp:
    def __init__(self):
        # Window
        self.window = tk.Tk()
        self.window.title("Log Viewer")
        self.window.geometry("1000x650")

        self.loaded_text = ""
        self.recent_files = load_recent_files()
        self.filter_presets = load_filter_presets()
        self.recent_filters = load_recent_filters(self.filter_presets)
        self.last_filter_text = ""
        self.style = ttk.Style()
        self.use_theme_engine()

        # Inputs
        self.file_entry = ttk.Combobox(self.window, values=self.recent_files)
        self.filter_entry = ttk.Combobox(self.window, values=self.build_filter_choices())
        self.case_sensitive_var = tk.BooleanVar(value=False)
        self.invert_match_var = tk.BooleanVar(value=False)
        self.dark_mode_var = tk.BooleanVar(value=load_dark_mode())

        # Buttons
        self.open_button = tk.Button(self.window, text="Open", command=self.open_file)
        self.reload_button = tk.Button(self.window, text="Reload", command=self.reload_file)
        self.refresh_button = tk.Button(self.window, text="Apply Filter", command=self.apply_filter)
        self.copy_button = tk.Button(self.window, text="Copy Result", command=self.copy_result)

        # Status
        self.status_var = tk.StringVar(value="Open a log or text file to begin.")
        self.status_label = tk.Label(self.window, textvariable=self.status_var, anchor="w")

        # Text - file content
        self.text_frame = tk.Frame(self.window)
        self.text_box = tk.Text(self.text_frame, wrap="none")
        self.text_box.configure(state="disabled")
        self.vertical_scrollbar = tk.Scrollbar(
            self.text_frame,
            orient="vertical",
            command=self.text_box.yview,
        )
        self.horizontal_scrollbar = tk.Scrollbar(
            self.text_frame,
            orient="horizontal",
            command=self.text_box.xview,
        )
        self.text_box.configure(
            yscrollcommand=self.vertical_scrollbar.set,
            xscrollcommand=self.horizontal_scrollbar.set,
        )

        # Regex helper
        self.regex_help = tk.Label(
            self.window,
            text=(
                "Regex    Meaning\n"
                "------------------------------\n"
                ".        Any single character\n"
                "*        0 or more repetitions\n"
                "+        1 or more repetitions\n"
                "?        0 or 1 repetition\n"
                "|        OR\n"
                "^        Start of line\n"
                "$        End of line\n\n"
            ),
            justify="left",
            anchor="n",
            font=("Consolas", 8)
        )
        self.build_layout()
        self.bind_shortcuts()
        self.apply_theme()

    def build_layout(self):
        self.window.columnconfigure(0, weight=0)
        self.window.columnconfigure(1, weight=1)
        self.window.columnconfigure(2, weight=0)
        self.window.columnconfigure(3, weight=0)
        self.window.columnconfigure(4, weight=0)
        self.window.rowconfigure(4, weight=1)

        tk.Label(self.window, text="File:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.file_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        self.open_button.grid(row=0, column=2, sticky="ew", padx=4, pady=4)
        self.reload_button.grid(row=0, column=3, sticky="ew", padx=8, pady=4)

        tk.Label(self.window, text="Filter:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.filter_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        self.refresh_button.grid(row=1, column=2, sticky="ew", padx=4, pady=4)
        self.copy_button.grid(row=1, column=3, sticky="ew", padx=8, pady=4)

        options_frame = tk.Frame(self.window)
        options_frame.grid(row=2, column=1, sticky="w", padx=8, pady=2)
        tk.Checkbutton(
            options_frame,
            text="Case sensitive",
            variable=self.case_sensitive_var,
            command=self.apply_filter,
        ).pack(side="left")
        tk.Checkbutton(
            options_frame,
            text="Invert match",
            variable=self.invert_match_var,
            command=self.apply_filter,
        ).pack(side="left", padx=(16, 0))
        tk.Checkbutton(
            options_frame,
            text="Dark mode",
            variable=self.dark_mode_var,
            command=self.toggle_theme,
        ).pack(side="left", padx=(16, 0))

        self.regex_help.grid(row=0, column=4, rowspan=4, sticky="nw", padx=16, pady=4)
        self.status_label.grid(row=3, column=0, columnspan=4, sticky="ew", padx=8, pady=4)

        self.text_frame.grid(row=4, column=0, columnspan=5, sticky="nsew", padx=8, pady=8)
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.rowconfigure(0, weight=1)
        self.text_box.grid(row=0, column=0, sticky="nsew")
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

    def bind_shortcuts(self):
        self.filter_entry.bind("<Return>", lambda _event: self.apply_filter())
        self.filter_entry.bind("<<ComboboxSelected>>", lambda _event: self.select_filter())
        self.file_entry.bind("<Return>", lambda _event: self.reload_file())
        self.file_entry.bind("<<ComboboxSelected>>", lambda _event: self.reload_file())
        self.window.bind("<F5>", lambda _event: self.reload_file())

    def build_filter_choices(self) -> list[str]:
        if not self.recent_filters:
            return self.filter_presets.copy()

        return self.filter_presets + [FILTER_SEPARATOR] + self.recent_filters

    def select_filter(self):
        selected_filter = self.filter_entry.get().strip()

        if selected_filter == FILTER_SEPARATOR:
            self.filter_entry.set(self.last_filter_text)
            return

        self.apply_filter()

    @staticmethod
    def configure_widget(widget, **options):
        for name, value in options.items():
            try:
                widget.configure(**{name: value})
            except tk.TclError:
                pass

    def use_theme_engine(self):
        try:
            if "clam" in self.style.theme_names():
                self.style.theme_use("clam")
        except tk.TclError:
            pass

    def toggle_theme(self):
        self.apply_theme()
        self.save_config()

    def apply_theme(self):
        theme = DARK_THEME if self.dark_mode_var.get() else LIGHT_THEME

        self.configure_widget(self.window, bg=theme["window_bg"])
        self.configure_widget(self.text_frame, bg=theme["panel_bg"])

        for widget in self.window.winfo_children():
            if isinstance(widget, tk.Frame):
                self.configure_widget(widget, bg=theme["panel_bg"])
            elif isinstance(widget, (tk.Label, tk.Checkbutton)):
                self.configure_widget(widget, bg=theme["panel_bg"], fg=theme["status_fg"])
            elif isinstance(widget, tk.Button):
                self.configure_widget(
                    widget,
                    bg=theme["button_bg"],
                    fg=theme["button_fg"],
                    activebackground=theme["active_bg"],
                    activeforeground=theme["button_fg"],
                    relief="flat",
                    padx=8,
                    pady=3,
                )
            elif isinstance(widget, tk.Entry):
                self.configure_widget(
                    widget,
                    bg=theme["input_bg"],
                    fg=theme["text_fg"],
                    insertbackground=theme["text_fg"],
                    relief="flat",
                )

        try:
            self.style.configure(
                "LogViewer.TCombobox",
                fieldbackground=theme["input_bg"],
                background=theme["button_bg"],
                foreground=theme["text_fg"],
                arrowcolor=theme["text_fg"],
                bordercolor=theme["active_bg"],
                lightcolor=theme["active_bg"],
                darkcolor=theme["active_bg"],
                insertcolor=theme["text_fg"],
                selectbackground=theme["active_bg"],
                selectforeground=theme["text_fg"],
            )
            self.style.map(
                "LogViewer.TCombobox",
                fieldbackground=[
                    ("readonly", theme["input_bg"]),
                    ("focus", theme["input_bg"]),
                    ("!disabled", theme["input_bg"]),
                ],
                foreground=[
                    ("readonly", theme["text_fg"]),
                    ("focus", theme["text_fg"]),
                    ("!disabled", theme["text_fg"]),
                ],
                background=[
                    ("active", theme["active_bg"]),
                    ("!disabled", theme["button_bg"]),
                ],
                arrowcolor=[
                    ("active", theme["text_fg"]),
                    ("!disabled", theme["text_fg"]),
                ],
            )
            self.file_entry.configure(style="LogViewer.TCombobox")
            self.filter_entry.configure(style="LogViewer.TCombobox")
            self.window.option_add("*TCombobox*Listbox.background", theme["input_bg"])
            self.window.option_add("*TCombobox*Listbox.foreground", theme["text_fg"])
            self.window.option_add("*TCombobox*Listbox.selectBackground", theme["active_bg"])
            self.window.option_add("*TCombobox*Listbox.selectForeground", theme["text_fg"])
        except tk.TclError:
            pass

        for widget in self.window.winfo_children():
            if isinstance(widget, tk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, tk.Checkbutton):
                        self.configure_widget(
                            child,
                            bg=theme["panel_bg"],
                            fg=theme["status_fg"],
                            activebackground=theme["panel_bg"],
                            activeforeground=theme["status_fg"],
                            selectcolor=theme["input_bg"],
                        )

        self.configure_widget(self.regex_help, bg=theme["panel_bg"], fg=theme["status_fg"])
        self.configure_widget(self.status_label, bg=theme["panel_bg"], fg=theme["status_fg"])
        self.configure_widget(
            self.text_box,
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            insertbackground=theme["text_fg"],
            selectbackground=theme["active_bg"],
            relief="flat",
            borderwidth=8,
        )

    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Open text file",
            filetypes=[
                ("Log/Text Files", "*.log *.txt"),
                ("All Files", "*.*")
            ]
        )

        if not file_path:
            return

        self.file_entry.set(file_path)

        self.load_file(file_path)

    def reload_file(self):
        file_path = self.file_entry.get().strip()

        if not file_path:
            messagebox.showinfo("No File", "Choose a file first.")
            return

        self.load_file(file_path)

    def load_file(self, file_path: str):
        if not Path(file_path).is_file():
            messagebox.showerror("File Not Found", f"Cannot find file:\n{file_path}")
            return

        self.loaded_text = load_text_file(file_path)
        self.remember_file(file_path)
        self.apply_filter()

    def remember_file(self, file_path: str):
        normalized_path = str(Path(file_path))
        self.recent_files = [
            recent_file
            for recent_file in self.recent_files
            if recent_file.lower() != normalized_path.lower()
        ]
        self.recent_files.insert(0, normalized_path)
        self.recent_files = self.recent_files[:MAX_RECENT_FILES]

        self.file_entry.configure(values=self.recent_files)
        self.file_entry.set(normalized_path)
        self.save_config()

    def save_config(self):
        write_config(
            self.recent_files,
            self.filter_presets,
            self.recent_filters,
            self.dark_mode_var.get(),
        )

    def apply_filter(self):
        filter_text = self.filter_entry.get().strip()
        if filter_text == FILTER_SEPARATOR:
            self.filter_entry.set(self.last_filter_text)
            return

        lines = self.loaded_text.splitlines()

        if not filter_text:
            visible_text = self.loaded_text
            matching_count = len(lines)
        else:
            try:
                flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
                pattern = re.compile(filter_text, flags)
                matching_lines = [
                    line for line in lines
                    if bool(pattern.search(line)) != self.invert_match_var.get()
                ]
                visible_text = "\n".join(matching_lines)
                matching_count = len(matching_lines)
            except re.error as error:
                messagebox.showerror("Regex Error", str(error))
                return

        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", tk.END)
        self.text_box.insert(tk.END, visible_text)
        self.text_box.configure(state="disabled")
        self.update_status(matching_count, len(lines))
        self.remember_filter(filter_text)

    def remember_filter(self, filter_text: str):
        if not filter_text:
            self.last_filter_text = ""
            return

        preset_lookup = {preset.lower() for preset in self.filter_presets}
        normalized_lookup = filter_text.lower()
        self.last_filter_text = filter_text

        if normalized_lookup in preset_lookup:
            return

        self.recent_filters = [
            recent_filter
            for recent_filter in self.recent_filters
            if recent_filter.lower() != normalized_lookup
        ]
        self.recent_filters.insert(0, filter_text)
        self.recent_filters = self.recent_filters[:MAX_RECENT_FILTERS]

        self.filter_entry.configure(values=self.build_filter_choices())
        self.save_config()

    def update_status(self, matching_count: int, total_count: int):
        if not self.loaded_text:
            self.status_var.set("Open a log or text file to begin.")
            return

        self.status_var.set(f"Showing {matching_count} of {total_count} lines.")

    def copy_result(self):
        result = self.text_box.get("1.0", "end-1c")
        self.window.clipboard_clear()
        self.window.clipboard_append(result)
        self.status_var.set(f"Copied {len(result)} characters to clipboard.")

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    app = LogViewerApp()
    app.run()
