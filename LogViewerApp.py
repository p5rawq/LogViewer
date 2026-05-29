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
HIGHLIGHT_RULES_SECTION = "HighlightRules"
MAX_RECENT_FILES = 10
MAX_RECENT_FILTERS = 5
DEFAULT_FILTER_PRESETS = ["error", "warning", "fatal"]
DEFAULT_HIGHLIGHT_RULES = [
    ("error", "#b00020", "#ff6b6b"),
    ("warning", "#8a6500", "#f2c94c"),
]
FILTER_SEPARATOR = "---------------- recent filters ----------------"
CONTEXT_SEPARATOR = "----------------------------------------"
TOOL_BUTTON_WIDTH = 8
WIDE_BUTTON_WIDTH = 12

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
    "status_applied_fg": "#24703d",
    "status_dirty_fg": "#8a6500",
    "search_bg": "#2f80ed",
    "search_fg": "#ffffff",
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
    "status_applied_fg": "#7bd88f",
    "status_dirty_fg": "#f2c45c",
    "search_bg": "#ffd166",
    "search_fg": "#101419",
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


def load_highlight_rules() -> list[tuple[str, str, str]]:
    config = read_config()

    if HIGHLIGHT_RULES_SECTION not in config:
        return DEFAULT_HIGHLIGHT_RULES.copy()

    rules = []
    for index in range(1, 51):
        value = config[HIGHLIGHT_RULES_SECTION].get(f"rule{index}", "").strip()
        rule = parse_highlight_rule(value)
        if rule:
            rules.append(rule)

    return rules or DEFAULT_HIGHLIGHT_RULES.copy()


def parse_highlight_rule(value: str) -> tuple[str, str, str] | None:
    if not value:
        return None

    if "|" in value:
        parts = [part.strip().strip('"') for part in value.split("|")]
    elif "," in value:
        pattern, color = value.split(",", 1)
        parts = [pattern.strip().strip('"'), color.strip().strip('"')]
    else:
        return None

    if len(parts) < 2:
        return None

    pattern = parts[0]
    light_color = normalize_color(parts[1])
    dark_color = normalize_color(parts[2]) if len(parts) >= 3 else light_color

    if not pattern or not light_color or not dark_color:
        return None

    return pattern, light_color, dark_color


def normalize_color(color: str) -> str:
    color = color.strip()

    if color.startswith("#") and len(color) == 7:
        return color

    rgb_text = color.strip("()")
    rgb_parts = [part.strip() for part in rgb_text.split(",")]
    if len(rgb_parts) != 3:
        return ""

    try:
        red, green, blue = [int(part) for part in rgb_parts]
    except ValueError:
        return ""

    if not all(0 <= color_part <= 255 for color_part in (red, green, blue)):
        return ""

    return f"#{red:02x}{green:02x}{blue:02x}"


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


def load_text_wrap() -> bool:
    config = read_config()
    return config.getboolean(SETTINGS_SECTION, "text_wrap", fallback=False)


def load_row_offset() -> int:
    config = read_config()
    try:
        row_offset = config.getint(SETTINGS_SECTION, "row_offset", fallback=0)
    except ValueError:
        row_offset = 0

    return max(0, row_offset)


def read_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    if CONFIG_FILE.is_file():
        config.read(CONFIG_FILE, encoding="utf-8")
    return config


def write_config(
    recent_files: list[str],
    filter_presets: list[str],
    recent_filters: list[str],
    highlight_rules: list[tuple[str, str, str]],
    dark_mode: bool,
    text_wrap: bool,
    row_offset: int,
):
    config = configparser.ConfigParser()
    config[SETTINGS_SECTION] = {
        "dark_mode": "yes" if dark_mode else "no",
        "text_wrap": "yes" if text_wrap else "no",
        "row_offset": str(max(0, row_offset)),
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
    config[HIGHLIGHT_RULES_SECTION] = {
        f"rule{index}": f"{pattern} | {light_color} | {dark_color}"
        for index, (pattern, light_color, dark_color) in enumerate(highlight_rules, start=1)
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
        self.applied_filter_text = ""
        self.applied_row_offset = 0
        self.last_matching_count = 0
        self.last_match_count = 0
        self.last_total_count = 0
        self.last_search_text = ""
        self.last_search_end = "1.0"
        self.recent_files = load_recent_files()
        self.filter_presets = load_filter_presets()
        self.recent_filters = load_recent_filters(self.filter_presets)
        self.highlight_rules = load_highlight_rules()
        self.compiled_highlight_rules = []
        self.last_filter_text = ""
        self.style = ttk.Style()
        self.use_theme_engine()

        # Inputs
        self.file_entry = ttk.Combobox(self.window, values=self.recent_files)
        self.filter_entry = ttk.Combobox(self.window, values=self.build_filter_choices())
        self.search_entry = None
        self.case_sensitive_var = tk.BooleanVar(value=False)
        self.invert_match_var = tk.BooleanVar(value=False)
        self.dark_mode_var = tk.BooleanVar(value=load_dark_mode())
        self.text_wrap_var = tk.BooleanVar(value=load_text_wrap())
        self.row_offset_var = tk.StringVar(value=str(load_row_offset()))

        # Buttons
        self.open_button = tk.Button(self.window, text="Open", width=TOOL_BUTTON_WIDTH, command=self.open_file)
        self.reload_button = tk.Button(self.window, text="Reload", width=TOOL_BUTTON_WIDTH, command=self.reload_file)
        self.clear_filter_button = tk.Button(
            self.window,
            text="Clear",
            width=TOOL_BUTTON_WIDTH,
            command=self.clear_filter,
        )
        self.refresh_button = tk.Button(
            self.window,
            text="Apply",
            width=TOOL_BUTTON_WIDTH,
            command=self.apply_filter,
        )
        self.copy_button = tk.Button(
            self.window,
            text="Copy Result",
            width=TOOL_BUTTON_WIDTH,
            command=self.copy_result,
        )
        self.search_button = None
        self.next_search_button = None
        self.row_offset_spinbox = None

        # Status
        self.status_var = tk.StringVar(value="Open a log or text file to begin.")
        self.status_label = tk.Label(self.window, textvariable=self.status_var, anchor="w")

        # Text - file content
        self.text_frame = tk.Frame(self.window)
        self.text_box = tk.Text(self.text_frame, wrap=self.get_text_wrap_mode())
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
        self.compile_highlight_rules()
        self.apply_theme()

    def create_row_offset_spinbox(self, parent: tk.Widget):
        self.row_offset_spinbox = tk.Spinbox(
            parent,
            from_=0,
            to=99,
            width=5,
            textvariable=self.row_offset_var,
            command=self.mark_filter_dirty,
        )

    def build_layout(self):
        self.window.columnconfigure(0, weight=0)
        self.window.columnconfigure(1, weight=1)
        self.window.columnconfigure(2, weight=0)
        self.window.columnconfigure(3, weight=0)
        self.window.columnconfigure(4, weight=0)
        self.window.rowconfigure(5, weight=1)

        tk.Label(self.window, text="File:").grid(row=0, column=0, sticky="w", padx=8, pady=3)
        self.file_entry.grid(row=0, column=1, sticky="ew", padx=8, pady=3)
        self.open_button.grid(row=0, column=2, sticky="w", padx=4, pady=3)
        self.reload_button.grid(row=0, column=3, sticky="w", padx=8, pady=3)

        tk.Label(self.window, text="Filter:").grid(row=1, column=0, sticky="w", padx=8, pady=3)
        self.filter_entry.grid(row=1, column=1, sticky="ew", padx=8, pady=3)
        self.clear_filter_button.grid(row=1, column=2, sticky="w", padx=4, pady=3)
        self.refresh_button.grid(row=1, column=3, sticky="w", padx=8, pady=3)

        tk.Label(self.window, text="Search:").grid(row=2, column=0, sticky="w", padx=8, pady=3)
        self.search_entry = tk.Entry(self.window)
        self.search_entry.grid(row=2, column=1, sticky="ew", padx=8, pady=3)
        self.search_button = tk.Button(
            self.window,
            text="Find",
            width=TOOL_BUTTON_WIDTH,
            command=self.find_first,
        )
        self.search_button.grid(row=2, column=2, sticky="w", padx=4, pady=3)
        self.next_search_button = tk.Button(
            self.window,
            text="Next",
            width=TOOL_BUTTON_WIDTH,
            command=self.find_next,
        )
        self.next_search_button.grid(row=2, column=3, sticky="w", padx=8, pady=3)

        controls_frame = tk.Frame(self.window)
        controls_frame.grid(row=3, column=1, columnspan=2, sticky="w", padx=8, pady=2)
        tk.Checkbutton(
            controls_frame,
            text="Case sensitive",
            variable=self.case_sensitive_var,
            command=self.apply_filter,
        ).pack(side="left")
        tk.Checkbutton(
            controls_frame,
            text="Invert match",
            variable=self.invert_match_var,
            command=self.apply_filter,
        ).pack(side="left", padx=(16, 0))
        tk.Checkbutton(
            controls_frame,
            text="Text wrap",
            variable=self.text_wrap_var,
            command=self.toggle_text_wrap,
        ).pack(side="left", padx=(16, 0))
        tk.Checkbutton(
            controls_frame,
            text="Dark mode",
            variable=self.dark_mode_var,
            command=self.toggle_theme,
        ).pack(side="left", padx=(16, 0))
        tk.Label(controls_frame, text="Span:").pack(side="left", padx=(22, 0))
        self.create_row_offset_spinbox(controls_frame)
        self.row_offset_spinbox.pack(side="left", padx=(6, 0))

        self.copy_button.grid(row=3, column=3, sticky="w", padx=8, pady=3)

        self.regex_help.grid(row=0, column=4, rowspan=5, sticky="nw", padx=16, pady=4)
        self.status_label.grid(row=4, column=0, columnspan=4, sticky="ew", padx=8, pady=4)

        self.text_frame.grid(row=5, column=0, columnspan=5, sticky="nsew", padx=8, pady=8)
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.rowconfigure(0, weight=1)
        self.text_box.grid(row=0, column=0, sticky="nsew")
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        self.update_text_wrap()

    def bind_shortcuts(self):
        self.filter_entry.bind("<Return>", lambda _event: self.apply_filter())
        self.filter_entry.bind("<KeyRelease>", lambda _event: self.mark_filter_dirty())
        self.filter_entry.bind("<<ComboboxSelected>>", lambda _event: self.select_filter())
        self.search_entry.bind("<Return>", lambda _event: self.find_next())
        self.row_offset_spinbox.bind("<KeyRelease>", lambda _event: self.mark_filter_dirty())
        self.row_offset_spinbox.bind("<Return>", lambda _event: self.apply_filter())
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

    def mark_filter_dirty(self):
        pending_filter_text = self.filter_entry.get().strip()
        pending_row_offset = self.get_row_offset()
        is_dirty = (
            pending_filter_text != self.applied_filter_text
            or (
                (pending_filter_text or self.applied_filter_text)
                and pending_row_offset != self.applied_row_offset
            )
        )
        self.update_status(
            self.last_matching_count,
            self.last_total_count,
            self.applied_filter_text,
            match_count=self.last_match_count,
            row_offset=self.applied_row_offset,
            is_dirty=is_dirty,
        )

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

    def compile_highlight_rules(self):
        compiled_rules = []
        for index, (pattern, light_color, dark_color) in enumerate(self.highlight_rules, start=1):
            try:
                compiled_rules.append((
                    f"highlight_{index}",
                    re.compile(pattern, re.IGNORECASE),
                    light_color,
                    dark_color,
                ))
            except re.error:
                continue

        self.compiled_highlight_rules = compiled_rules

    def toggle_theme(self):
        self.apply_theme()
        self.save_config()

    def get_text_wrap_mode(self) -> str:
        return "word" if self.text_wrap_var.get() else "none"

    def get_row_offset(self) -> int:
        try:
            row_offset = int(self.row_offset_var.get())
        except ValueError:
            row_offset = 0

        row_offset = max(0, row_offset)
        self.row_offset_var.set(str(row_offset))
        return row_offset

    def toggle_text_wrap(self):
        self.update_text_wrap()
        self.save_config()

    def update_text_wrap(self):
        self.text_box.configure(wrap=self.get_text_wrap_mode())
        if self.text_wrap_var.get():
            self.horizontal_scrollbar.grid_remove()
        else:
            self.horizontal_scrollbar.grid()

    def find_first(self):
        self.last_search_text = ""
        self.last_search_end = "1.0"
        self.find_next()

    def find_next(self):
        search_text = self.search_entry.get().strip()
        if not search_text:
            self.clear_search_match()
            return

        if search_text != self.last_search_text:
            start_index = "1.0"
        else:
            start_index = self.last_search_end

        self.clear_search_match()
        match_index = self.search_visible_text(search_text, start_index, tk.END)
        if not match_index and start_index != "1.0":
            match_index = self.search_visible_text(search_text, "1.0", start_index)

        self.last_search_text = search_text
        if not match_index:
            self.last_search_end = "1.0"
            self.show_search_status(f'Search not found: {search_text}', is_error=True)
            return

        end_index = f"{match_index}+{len(search_text)}c"
        self.text_box.tag_add("search_match", match_index, end_index)
        self.text_box.mark_set(tk.INSERT, end_index)
        self.text_box.see(match_index)
        self.last_search_end = end_index
        self.show_search_status(f"Search: line {match_index.split('.')[0]}")

    def search_visible_text(self, search_text: str, start_index: str, stop_index: str) -> str:
        return self.text_box.search(
            search_text,
            start_index,
            stopindex=stop_index,
            nocase=not self.case_sensitive_var.get(),
        )

    def clear_search_match(self):
        self.text_box.tag_remove("search_match", "1.0", tk.END)

    def show_search_status(self, search_text: str, is_error: bool = False):
        self.mark_filter_dirty()
        theme = DARK_THEME if self.dark_mode_var.get() else LIGHT_THEME
        if is_error:
            self.configure_widget(self.status_label, fg=theme["status_dirty_fg"])

        self.status_var.set(f"{self.status_var.get()} {search_text}")

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
                    pady=1,
                )
            elif isinstance(widget, tk.Entry):
                self.configure_widget(
                    widget,
                    bg=theme["input_bg"],
                    fg=theme["text_fg"],
                    insertbackground=theme["text_fg"],
                    relief="flat",
                )

        self.configure_widget(
            self.row_offset_spinbox,
            bg=theme["input_bg"],
            fg=theme["text_fg"],
            buttonbackground=theme["button_bg"],
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
                    elif isinstance(child, tk.Label):
                        self.configure_widget(child, bg=theme["panel_bg"], fg=theme["status_fg"])
                    elif isinstance(child, tk.Button):
                        self.configure_widget(
                            child,
                            bg=theme["button_bg"],
                            fg=theme["button_fg"],
                            activebackground=theme["active_bg"],
                            activeforeground=theme["button_fg"],
                            relief="flat",
                            padx=8,
                            pady=1,
                        )
                    elif isinstance(child, tk.Entry):
                        self.configure_widget(
                            child,
                            bg=theme["input_bg"],
                            fg=theme["text_fg"],
                            insertbackground=theme["text_fg"],
                            relief="flat",
                        )
                    elif isinstance(child, tk.Spinbox):
                        self.configure_widget(
                            child,
                            bg=theme["input_bg"],
                            fg=theme["text_fg"],
                            buttonbackground=theme["button_bg"],
                            insertbackground=theme["text_fg"],
                            relief="flat",
                        )

        self.configure_widget(self.regex_help, bg=theme["panel_bg"], fg=theme["status_fg"])
        self.configure_widget(self.status_label, bg=theme["panel_bg"])
        self.mark_filter_dirty()
        self.configure_widget(
            self.text_box,
            bg=theme["text_bg"],
            fg=theme["text_fg"],
            insertbackground=theme["text_fg"],
            selectbackground=theme["active_bg"],
            relief="flat",
            borderwidth=8,
        )
        self.text_box.tag_configure(
            "search_match",
            background=theme["search_bg"],
            foreground=theme["search_fg"],
        )
        self.configure_highlight_tags()

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
            self.highlight_rules,
            self.dark_mode_var.get(),
            self.text_wrap_var.get(),
            self.get_row_offset(),
        )

    def clear_filter(self):
        self.filter_entry.set("")
        self.apply_filter()

    def apply_filter(self):
        filter_text = self.filter_entry.get().strip()
        if filter_text == FILTER_SEPARATOR:
            self.filter_entry.set(self.last_filter_text)
            return

        lines = self.loaded_text.splitlines()
        row_offset = self.get_row_offset()

        if not filter_text:
            visible_text = self.loaded_text
            matching_count = len(lines)
            match_count = matching_count
        else:
            try:
                flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
                pattern = re.compile(filter_text, flags)
                matching_indices = [
                    index for index, line in enumerate(lines)
                    if bool(pattern.search(line)) != self.invert_match_var.get()
                ]
                visible_lines, matching_count = self.build_context_lines(lines, matching_indices, row_offset)
                visible_text = "\n".join(visible_lines)
                match_count = len(matching_indices)
            except re.error as error:
                messagebox.showerror("Regex Error", str(error))
                return

        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", tk.END)
        self.text_box.insert(tk.END, visible_text)
        self.last_search_text = ""
        self.last_search_end = "1.0"
        self.clear_search_match()
        self.apply_highlights(visible_text)
        self.text_box.configure(state="disabled")
        self.applied_filter_text = filter_text
        self.applied_row_offset = row_offset
        self.last_matching_count = matching_count
        self.last_match_count = match_count
        self.last_total_count = len(lines)
        self.update_status(
            matching_count,
            len(lines),
            filter_text,
            match_count=match_count,
            row_offset=row_offset,
            is_dirty=False,
        )
        self.remember_filter(filter_text)

    @staticmethod
    def build_context_lines(
        lines: list[str],
        matching_indices: list[int],
        row_offset: int,
    ) -> tuple[list[str], int]:
        if not matching_indices:
            return [], 0

        last_index = len(lines) - 1
        context_ranges = []
        for index in matching_indices:
            start_index = max(0, index - row_offset)
            end_index = min(last_index, index + row_offset)
            context_ranges.append((start_index, end_index))

        merged_ranges = []
        for start_index, end_index in context_ranges:
            if not merged_ranges or start_index > merged_ranges[-1][1] + 1:
                merged_ranges.append([start_index, end_index])
            else:
                merged_ranges[-1][1] = max(merged_ranges[-1][1], end_index)

        visible_lines = []
        original_line_count = 0
        for range_index, (start_index, end_index) in enumerate(merged_ranges):
            if range_index > 0:
                visible_lines.append(CONTEXT_SEPARATOR)

            block_lines = lines[start_index:end_index + 1]
            visible_lines.extend(block_lines)
            original_line_count += len(block_lines)

        return visible_lines, original_line_count

    def configure_highlight_tags(self):
        use_dark_mode = self.dark_mode_var.get()
        for tag_name, _pattern, light_color, dark_color in self.compiled_highlight_rules:
            color = dark_color if use_dark_mode else light_color
            self.text_box.tag_configure(tag_name, foreground=color)

    def apply_highlights(self, visible_text: str):
        if not visible_text or not self.compiled_highlight_rules:
            return

        self.configure_highlight_tags()
        for tag_name, _pattern, _light_color, _dark_color in self.compiled_highlight_rules:
            self.text_box.tag_remove(tag_name, "1.0", tk.END)

        for line_number, line in enumerate(visible_text.splitlines(), start=1):
            for tag_name, pattern, _light_color, _dark_color in self.compiled_highlight_rules:
                if pattern.search(line):
                    self.text_box.tag_add(tag_name, f"{line_number}.0", f"{line_number}.end")
                    break

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

    def update_status(
        self,
        matching_count: int,
        total_count: int,
        filter_text: str | None = None,
        match_count: int | None = None,
        row_offset: int = 0,
        is_dirty: bool = False,
    ):
        theme = DARK_THEME if self.dark_mode_var.get() else LIGHT_THEME

        if not self.loaded_text:
            self.status_var.set("Open a log or text file to begin.")
            self.configure_widget(self.status_label, fg=theme["status_fg"])
            return

        status_text = f"Showing {matching_count} of {total_count} lines."
        if filter_text:
            status_text += f" Filter: {filter_text}"
            if row_offset > 0 and match_count is not None:
                status_text += f" Matches: {match_count}. Rows: +/-{row_offset}"

        if is_dirty:
            status_text += " (pending input not applied)"
            self.configure_widget(self.status_label, fg=theme["status_dirty_fg"])
        else:
            self.configure_widget(self.status_label, fg=theme["status_applied_fg"])

        self.status_var.set(status_text)

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
