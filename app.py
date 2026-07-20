"""InfoBuilder Studio desktop application.

This file intentionally delays importing CustomTkinter until the app starts.
That lets `import app` succeed even before the UI dependency is installed.
"""

from __future__ import annotations

import ast
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = PROJECT_ROOT / "config.py"
TOPICS_PATH = PROJECT_ROOT / "topics.txt"
VISUAL_MODE_PATH = PROJECT_ROOT / "visual_mode.json"
UI_LOG_FOLDER = PROJECT_ROOT / "logs" / "ui"

REQUIRED_FOLDERS = [
    "approval",
    "completed",
    "exports",
    "generators",
    "logs",
    "output",
    "posted",
    "prompts",
    "rejected",
    "utils",
]

CORE_SCRIPTS = [
    "main.py",
    "run_pipeline.py",
    "approve.py",
    "review_videos.py",
    "project_status.py",
]

OPTIONAL_SCRIPTS = {
    "add_topic.py": "Add Topic",
    "trend_topic_ideas.py": "Generate Trend Topic Ideas",
    "run_until_scenes.py": "Run Until Scenes",
    "run_pipeline.py": "Run Full Pipeline",
    "generate_images.py": "Generate Images",
    "generate_video.py": "Generate Videos",
    "complete_videos.py": "Complete Videos",
    "approve.py": "Approve Scripts",
    "review_videos.py": "Review Videos",
    "export_videos.py": "Export Videos",
    "refresh_export_info.py": "Refresh Export Info",
    "upload_to_youtube.py": "Upload One Video",
    "upload_all_to_youtube.py": "Upload All Videos",
    "youtube_setup_check.py": "YouTube Setup Check",
    "upload_checklist.py": "Upload Checklist",
    "instagram_uploader.py": "Instagram Uploader",
    "tiktok_uploader.py": "TikTok Uploader",
    "zernio_setup_check.py": "Zernio Setup Check",
    "zernio_accounts_check.py": "Zernio Account Check",
    "project_status.py": "Project Status",
    "clear_cycle_cache.py": "Clear Cycle Cache",
    "reset_stage.py": "Reset Stage",
    "pexels_setup_check.py": "Pexels Setup Check",
}

CONFIG_FIELDS = {
    "OPENAI_MODEL": "str",
    "VOICE_MODEL": "str",
    "VOICE_NAME": "str",
    "VOICE_SPEED": "float",
    "IMAGE_MODEL": "str",
    "IMAGE_SIZE": "str",
    "IMAGE_QUALITY": "str",
    "IMAGE_STYLE": "str",
    "ENABLE_IMAGE_MOTION": "bool",
    "IMAGE_MOTION_ZOOM": "float",
    "MAX_TOPICS": "optional_int",
    "FORCE_REGENERATE_SCENES": "bool",
    "FORCE_REGENERATE_VIDEO": "bool",
}

ctk = None
theme = None
dialogs = None
ProcessRunner = None
ProcessEvent = None
StatusCard = None
count_project_status = None


def collect_startup_warnings() -> list[str]:
    warnings = []

    for folder_name in REQUIRED_FOLDERS:
        if not (PROJECT_ROOT / folder_name).exists():
            warnings.append(f"Missing folder: {folder_name}/")

    if not CONFIG_PATH.exists():
        warnings.append("Missing config.py")

    if not TOPICS_PATH.exists():
        warnings.append("Missing topics.txt")

    for script_name in CORE_SCRIPTS:
        if not (PROJECT_ROOT / script_name).exists():
            warnings.append(f"Missing core script: {script_name}")

    return warnings


def show_customtkinter_missing_error() -> None:
    message = (
        "InfoBuilder Studio needs customtkinter.\n\n"
        "Install project requirements first:\n"
        "py -m pip install -r requirements.txt\n\n"
        "On Mac, use:\n"
        "python3 -m pip install -r requirements.txt"
    )

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Missing Dependency", message)
        root.destroy()
    except Exception:
        print(message)


def load_config_values() -> dict[str, Any]:
    values = {}

    try:
        tree = ast.parse(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return values

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue

        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue

        name = node.targets[0].id

        if name not in CONFIG_FIELDS:
            continue

        try:
            values[name] = ast.literal_eval(node.value)
        except ValueError:
            values[name] = ""

    return values


def format_config_value(value: Any) -> str:
    if isinstance(value, str):
        return repr(value)

    if value is None:
        return "None"

    if isinstance(value, bool):
        return "True" if value else "False"

    return str(value)


def validate_config_value(name: str, raw_value: str, bool_value: bool | None = None) -> Any:
    field_type = CONFIG_FIELDS[name]

    if field_type == "bool":
        return bool(bool_value)

    raw_value = raw_value.strip()

    if field_type == "str":
        if not raw_value:
            raise ValueError(f"{name} cannot be empty.")
        return raw_value

    if field_type == "float":
        try:
            return float(raw_value)
        except ValueError as error:
            raise ValueError(f"{name} must be a number.") from error

    if field_type == "optional_int":
        if raw_value.lower() in {"", "none", "null"}:
            return None

        try:
            return int(raw_value)
        except ValueError as error:
            raise ValueError(f"{name} must be a whole number or None.") from error

    return raw_value


class InfoBuilderStudio:
    def __init__(self):
        UI_LOG_FOLDER.mkdir(parents=True, exist_ok=True)
        self.runner = ProcessRunner(PROJECT_ROOT)
        self.current_page_name = ""
        self.current_task_text = "Idle"
        self.config_entries: dict[str, Any] = {}
        self.config_switches: dict[str, Any] = {}
        self.status_cards: dict[str, Any] = {}
        self.recent_output = ""
        self.last_refresh_label = None
        self.dashboard_task_label = None

        self.root = ctk.CTk()
        self.root.title("InfoBuilder Studio")
        self.root.geometry("1400x850")
        self.root.minsize(1100, 700)
        self.root.configure(fg_color=theme.COLORS["background"])
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.build_layout()
        self.show_page("Dashboard")
        self.poll_process_events()

        startup_warnings = collect_startup_warnings()

        if startup_warnings:
            dialogs.show_warning(
                "Startup Checks",
                "InfoBuilder Studio started, but found:\n\n"
                + "\n".join(startup_warnings),
            )

    def build_layout(self) -> None:
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self.root,
            width=theme.SIDEBAR_WIDTH,
            fg_color=theme.COLORS["sidebar"],
            corner_radius=0,
        )
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.content = ctk.CTkFrame(
            self.root,
            fg_color=theme.COLORS["background"],
            corner_radius=0,
        )
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(1, weight=1)

        self.console_panel = ctk.CTkFrame(
            self.root,
            height=theme.CONSOLE_HEIGHT,
            fg_color=theme.COLORS["surface"],
            corner_radius=0,
        )
        self.console_panel.grid(row=1, column=1, sticky="nsew")
        self.console_panel.grid_propagate(False)

        self.build_sidebar()
        self.build_console()

    def build_sidebar(self) -> None:
        logo = ctk.CTkLabel(
            self.sidebar,
            text="InfoBuilder\nStudio",
            font=theme.FONTS["title"],
            text_color=theme.COLORS["text"],
            justify="left",
        )
        logo.pack(padx=theme.SPACING["lg"], pady=(theme.SPACING["xl"], theme.SPACING["xs"]), anchor="w")

        subtitle = ctk.CTkLabel(
            self.sidebar,
            text="AI Video Creation &\nPublishing Dashboard",
            font=theme.FONTS["subtitle"],
            text_color=theme.COLORS["muted"],
            justify="left",
        )
        subtitle.pack(padx=theme.SPACING["lg"], pady=(0, theme.SPACING["xl"]), anchor="w")

        for page_name in [
            "Dashboard",
            "Create",
            "Review",
            "Publish",
            "Maintenance",
            "Settings",
            "Logs",
        ]:
            button = ctk.CTkButton(
                self.sidebar,
                text=page_name,
                height=42,
                corner_radius=theme.CORNER_RADIUS,
                fg_color="transparent",
                hover_color=theme.COLORS["surface_light"],
                text_color=theme.COLORS["text"],
                anchor="w",
                font=theme.FONTS["nav"],
                command=lambda name=page_name: self.show_page(name),
            )
            button.pack(fill="x", padx=theme.SPACING["md"], pady=theme.SPACING["xs"])

        self.task_badge = ctk.CTkLabel(
            self.sidebar,
            text="Idle",
            fg_color=theme.COLORS["muted"],
            corner_radius=theme.CORNER_RADIUS,
            text_color=theme.COLORS["background"],
            height=30,
            font=theme.FONTS["small"],
        )
        self.task_badge.pack(fill="x", padx=theme.SPACING["md"], pady=(theme.SPACING["xl"], theme.SPACING["sm"]))

        self.script_label = ctk.CTkLabel(
            self.sidebar,
            text="No task running",
            font=theme.FONTS["small"],
            text_color=theme.COLORS["muted"],
            wraplength=180,
            justify="left",
        )
        self.script_label.pack(fill="x", padx=theme.SPACING["md"], pady=(0, theme.SPACING["lg"]))

    def build_console(self) -> None:
        self.console_panel.grid_columnconfigure(0, weight=1)
        self.console_panel.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.console_panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=theme.SPACING["md"], pady=(theme.SPACING["sm"], 0))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Built-in Console",
            font=theme.FONTS["card_title"],
            text_color=theme.COLORS["text"],
        ).grid(row=0, column=0, sticky="w")

        button_row = ctk.CTkFrame(header, fg_color="transparent")
        button_row.grid(row=0, column=1, sticky="e")

        self.make_small_button(button_row, "Clear", self.clear_console).pack(side="left", padx=3)
        self.make_small_button(button_row, "Copy", self.copy_console).pack(side="left", padx=3)
        self.make_small_button(button_row, "Save Log", self.save_console_log).pack(side="left", padx=3)
        self.make_small_button(button_row, "Stop Task", self.stop_task, danger=True).pack(side="left", padx=3)

        self.console_text = ctk.CTkTextbox(
            self.console_panel,
            fg_color=theme.COLORS["console"],
            text_color=theme.COLORS["text"],
            font=theme.FONTS["console"],
            corner_radius=theme.CORNER_RADIUS,
            wrap="word",
        )
        self.console_text.grid(row=1, column=0, sticky="nsew", padx=theme.SPACING["md"], pady=theme.SPACING["sm"])

        input_row = ctk.CTkFrame(self.console_panel, fg_color="transparent")
        input_row.grid(row=2, column=0, sticky="ew", padx=theme.SPACING["md"], pady=(0, theme.SPACING["sm"]))
        input_row.grid_columnconfigure(0, weight=1)

        self.console_input = ctk.CTkEntry(
            input_row,
            placeholder_text="Type a response for the running script...",
            height=34,
        )
        self.console_input.grid(row=0, column=0, sticky="ew", padx=(0, theme.SPACING["sm"]))
        self.console_input.bind("<Return>", lambda _event: self.send_console_input())

        ctk.CTkButton(
            input_row,
            text="Send",
            width=90,
            height=34,
            corner_radius=theme.CORNER_RADIUS,
            fg_color=theme.COLORS["blue"],
            hover_color="#0ea5e9",
            command=self.send_console_input,
        ).grid(row=0, column=1)

        self.progress_bar = ctk.CTkProgressBar(
            input_row,
            width=180,
            mode="indeterminate",
            progress_color=theme.COLORS["purple"],
        )
        self.progress_bar.grid(row=0, column=2, padx=(theme.SPACING["md"], 0))
        self.progress_bar.set(0)

    def make_small_button(self, parent, text: str, command: Callable[[], None], danger: bool = False):
        color = theme.COLORS["red"] if danger else theme.COLORS["surface_light"]
        hover = "#dc2626" if danger else theme.COLORS["border"]
        return ctk.CTkButton(
            parent,
            text=text,
            width=84,
            height=30,
            corner_radius=theme.CORNER_RADIUS,
            fg_color=color,
            hover_color=hover,
            command=command,
            font=theme.FONTS["small"],
        )

    def show_page(self, page_name: str) -> None:
        self.current_page_name = page_name
        self.last_refresh_label = None
        self.dashboard_task_label = None

        for child in self.content.winfo_children():
            child.destroy()

        self.build_page_header(page_name)
        page_frame = ctk.CTkScrollableFrame(
            self.content,
            fg_color=theme.COLORS["background"],
            corner_radius=0,
        )
        page_frame.grid(row=1, column=0, sticky="nsew", padx=theme.SPACING["lg"], pady=(0, theme.SPACING["lg"]))
        page_frame.grid_columnconfigure(0, weight=1)

        builder = {
            "Dashboard": self.build_dashboard_page,
            "Create": self.build_create_page,
            "Review": self.build_review_page,
            "Publish": self.build_publish_page,
            "Maintenance": self.build_maintenance_page,
            "Settings": self.build_settings_page,
            "Logs": self.build_logs_page,
        }[page_name]
        builder(page_frame)

    def build_page_header(self, page_name: str) -> None:
        header = ctk.CTkFrame(self.content, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=theme.SPACING["lg"], pady=theme.SPACING["lg"])
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=page_name,
            font=theme.FONTS["title"],
            text_color=theme.COLORS["text"],
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="AI Video Creation & Publishing Dashboard",
            font=theme.FONTS["subtitle"],
            text_color=theme.COLORS["muted"],
        ).grid(row=1, column=0, sticky="w")

    def make_section(self, parent, title: str, row: int):
        section = ctk.CTkFrame(parent, fg_color="transparent")
        section.grid(row=row, column=0, sticky="ew", pady=(0, theme.SPACING["lg"]))
        section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            section,
            text=title,
            font=theme.FONTS["section"],
            text_color=theme.COLORS["text"],
        ).grid(row=0, column=0, sticky="w", pady=(0, theme.SPACING["sm"]))

        return section

    def make_card(self, parent, title: str = ""):
        card = ctk.CTkFrame(
            parent,
            fg_color=theme.COLORS["surface"],
            corner_radius=theme.CORNER_RADIUS,
            border_width=1,
            border_color=theme.COLORS["border"],
        )
        card.grid_columnconfigure(0, weight=1)

        if title:
            ctk.CTkLabel(
                card,
                text=title,
                font=theme.FONTS["card_title"],
                text_color=theme.COLORS["text"],
            ).grid(row=0, column=0, sticky="w", padx=theme.SPACING["md"], pady=(theme.SPACING["md"], theme.SPACING["sm"]))

        return card

    def make_action_button(
        self,
        parent,
        text: str,
        script_name: str | None = None,
        command: Callable[[], None] | None = None,
        color: str | None = None,
        public_warning: bool = False,
        destructive_warning: str = "",
        initial_input: str = "",
    ):
        color = color or theme.COLORS["purple"]
        hover = self.hover_color(color)

        def on_click() -> None:
            if destructive_warning:
                if not dialogs.confirm("Confirm Action", destructive_warning):
                    return

            if public_warning:
                confirmed = dialogs.confirm(
                    "Public Upload Warning",
                    "This tool can publish publicly after its own confirmation prompts.\n\n"
                    "The original script will still require PUBLISH or PUBLISH ALL before posting.\n\n"
                    "Start this tool now?",
                )

                if not confirmed:
                    return

            if command:
                command()
                return

            if script_name:
                self.start_script(script_name, initial_input=initial_input)

        button = ctk.CTkButton(
            parent,
            text=text,
            height=42,
            corner_radius=theme.CORNER_RADIUS,
            fg_color=color,
            hover_color=hover,
            command=on_click,
            font=theme.FONTS["body"],
        )

        if script_name and not (PROJECT_ROOT / script_name).exists():
            button.configure(state="disabled", fg_color=theme.COLORS["border"])
            dialogs.Tooltip(button, f"Missing file: {script_name}")

        return button

    def hover_color(self, color: str) -> str:
        hover_map = {
            theme.COLORS["purple"]: "#7c3aed",
            theme.COLORS["blue"]: "#0ea5e9",
            theme.COLORS["green"]: "#16a34a",
            theme.COLORS["amber"]: "#d97706",
            theme.COLORS["red"]: "#dc2626",
        }
        return hover_map.get(color, theme.COLORS["surface_light"])

    def grid_buttons(self, parent, buttons: list[Any], columns: int = 3) -> None:
        for column in range(columns):
            parent.grid_columnconfigure(column, weight=1)

        for index, button in enumerate(buttons):
            row = index // columns
            column = index % columns
            button.grid(
                row=row,
                column=column,
                sticky="ew",
                padx=theme.SPACING["xs"],
                pady=theme.SPACING["xs"],
            )

    def build_dashboard_page(self, parent) -> None:
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, theme.SPACING["lg"]))
        top.grid_columnconfigure(0, weight=1)

        self.last_refresh_label = ctk.CTkLabel(
            top,
            text="Last refresh: never",
            font=theme.FONTS["small"],
            text_color=theme.COLORS["muted"],
        )
        self.last_refresh_label.grid(row=0, column=0, sticky="w")

        self.make_action_button(
            top,
            "Refresh",
            command=self.refresh_dashboard,
            color=theme.COLORS["blue"],
        ).grid(row=0, column=1, sticky="e")

        self.dashboard_task_label = ctk.CTkLabel(
            top,
            text=f"Current task: {self.current_task_text}",
            font=theme.FONTS["body"],
            text_color=theme.COLORS["text"],
        )
        self.dashboard_task_label.grid(row=1, column=0, sticky="w", pady=(theme.SPACING["sm"], 0))

        cards_frame = ctk.CTkFrame(parent, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="ew")

        for column in range(4):
            cards_frame.grid_columnconfigure(column, weight=1)

        accents = [
            theme.COLORS["purple"],
            theme.COLORS["blue"],
            theme.COLORS["green"],
            theme.COLORS["amber"],
            theme.COLORS["purple"],
            theme.COLORS["blue"],
            theme.COLORS["green"],
            theme.COLORS["red"],
        ]
        self.status_cards = {}

        for index, name in enumerate([
            "Topics waiting",
            "Scripts awaiting approval",
            "Approved scripts",
            "Videos being generated",
            "Completed videos",
            "Exported videos",
            "Posted videos",
            "Rejected items",
        ]):
            card = StatusCard(cards_frame, name, accents[index])
            card.grid(
                row=index // 4,
                column=index % 4,
                sticky="ew",
                padx=theme.SPACING["xs"],
                pady=theme.SPACING["xs"],
            )
            self.status_cards[name] = card

        actions = self.make_section(parent, "Quick Actions", 2)
        buttons = [
            self.make_action_button(actions, "Add Topic", command=self.open_add_topic_dialog, color=theme.COLORS["green"]),
            self.make_action_button(actions, "Generate Trend Ideas", "trend_topic_ideas.py", color=theme.COLORS["purple"]),
            self.make_action_button(actions, "Run Pipeline", "run_pipeline.py", color=theme.COLORS["blue"]),
            self.make_action_button(actions, "Review Scripts", "approve.py", color=theme.COLORS["amber"]),
            self.make_action_button(actions, "Review Videos", "review_videos.py", color=theme.COLORS["amber"]),
            self.make_action_button(actions, "Export Videos", "export_videos.py", color=theme.COLORS["green"]),
            self.make_action_button(actions, "Publish Videos", command=lambda: self.show_page("Publish"), color=theme.COLORS["red"]),
        ]
        self.grid_buttons(actions, buttons, columns=4)
        self.refresh_dashboard()

    def refresh_dashboard(self) -> None:
        if self.current_page_name != "Dashboard":
            return

        counts = count_project_status(PROJECT_ROOT)

        for name, value in counts.items():
            if name in self.status_cards:
                self.status_cards[name].set_value(value)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.last_refresh_label:
            self.last_refresh_label.configure(text=f"Last refresh: {now}")

        if self.dashboard_task_label:
            self.dashboard_task_label.configure(text=f"Current task: {self.current_task_text}")

    def build_create_page(self, parent) -> None:
        actions = self.make_section(parent, "Creation Tools", 0)
        buttons = [
            self.make_action_button(actions, "Add Topic", command=self.open_add_topic_dialog, color=theme.COLORS["green"]),
            self.make_action_button(actions, "Generate Trend Topic Ideas", "trend_topic_ideas.py", color=theme.COLORS["purple"]),
            self.make_action_button(actions, "Run Until Scenes", "run_until_scenes.py", color=theme.COLORS["blue"]),
            self.make_action_button(actions, "Run Full Pipeline", "run_pipeline.py", color=theme.COLORS["blue"]),
            self.make_action_button(actions, "Generate Images", "generate_images.py", color=theme.COLORS["purple"]),
            self.make_action_button(actions, "Generate Videos", "generate_video.py", color=theme.COLORS["amber"]),
            self.make_action_button(actions, "Complete Videos", "complete_videos.py", color=theme.COLORS["green"]),
        ]
        self.grid_buttons(actions, buttons, columns=3)

        editor_section = self.make_section(parent, "Topics Editor", 1)
        editor_section.grid_rowconfigure(2, weight=1)

        self.topics_editor = ctk.CTkTextbox(
            editor_section,
            height=260,
            fg_color=theme.COLORS["console"],
            text_color=theme.COLORS["text"],
            corner_radius=theme.CORNER_RADIUS,
            font=theme.FONTS["console"],
        )
        self.topics_editor.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, theme.SPACING["sm"]))

        self.make_action_button(editor_section, "Reload", command=self.load_topics_editor, color=theme.COLORS["blue"]).grid(row=2, column=0, sticky="ew", padx=theme.SPACING["xs"])
        self.make_action_button(editor_section, "Save", command=self.save_topics_editor, color=theme.COLORS["green"]).grid(row=2, column=1, sticky="ew", padx=theme.SPACING["xs"])
        self.make_action_button(editor_section, "Add Topic Dialog", command=self.open_add_topic_dialog, color=theme.COLORS["purple"]).grid(row=2, column=2, sticky="ew", padx=theme.SPACING["xs"])
        self.load_topics_editor()

    def load_topics_editor(self) -> None:
        if not hasattr(self, "topics_editor"):
            return

        try:
            text = TOPICS_PATH.read_text(encoding="utf-8")
        except OSError:
            text = ""

        self.topics_editor.delete("1.0", "end")
        self.topics_editor.insert("1.0", text)

    def save_topics_editor(self) -> None:
        if not dialogs.confirm(
            "Save Topics",
            "This will overwrite topics.txt with the text in the editor.\n\nContinue?",
        ):
            return

        text = self.topics_editor.get("1.0", "end-1c")
        TOPICS_PATH.write_text(text, encoding="utf-8")
        dialogs.show_info("Topics Saved", "topics.txt was saved.")
        self.refresh_dashboard()

    def open_add_topic_dialog(self) -> None:
        dialogs.AddTopicDialog(self.root, TOPICS_PATH, self.refresh_dashboard)

    def build_review_page(self, parent) -> None:
        actions = self.make_section(parent, "Review Tools", 0)
        buttons = [
            self.make_action_button(actions, "Approve Scripts", "approve.py", color=theme.COLORS["amber"]),
            self.make_action_button(actions, "Review Completed Videos", "review_videos.py", color=theme.COLORS["amber"]),
            self.make_action_button(actions, "Export Approved Videos", "export_videos.py", color=theme.COLORS["green"]),
            self.make_action_button(actions, "Refresh Export Info", "refresh_export_info.py", color=theme.COLORS["blue"]),
            self.make_action_button(actions, "Open Approval Folder", command=lambda: dialogs.open_folder(PROJECT_ROOT / "approval"), color=theme.COLORS["purple"]),
            self.make_action_button(actions, "Open Completed Folder", command=lambda: dialogs.open_folder(PROJECT_ROOT / "completed"), color=theme.COLORS["purple"]),
            self.make_action_button(actions, "Open Exports Folder", command=lambda: dialogs.open_folder(PROJECT_ROOT / "exports"), color=theme.COLORS["purple"]),
            self.make_action_button(actions, "Open Rejected Folder", command=lambda: dialogs.open_folder(PROJECT_ROOT / "rejected"), color=theme.COLORS["purple"]),
        ]
        self.grid_buttons(actions, buttons, columns=4)

    def build_publish_page(self, parent) -> None:
        row = 0
        for title, buttons in [
            ("YouTube", self.youtube_buttons),
            ("Instagram", self.instagram_buttons),
            ("TikTok", self.tiktok_buttons),
        ]:
            section = self.make_section(parent, title, row)
            card = self.make_card(section)
            card.grid(row=1, column=0, sticky="ew")
            button_widgets = buttons(card)
            self.grid_buttons(card, button_widgets, columns=2)
            row += 1

    def youtube_buttons(self, parent) -> list[Any]:
        return [
            self.make_action_button(parent, "Upload One Video", "upload_to_youtube.py", color=theme.COLORS["blue"]),
            self.make_action_button(parent, "Upload All Videos", "upload_all_to_youtube.py", color=theme.COLORS["blue"]),
            self.make_action_button(parent, "YouTube Setup Check", "youtube_setup_check.py", color=theme.COLORS["green"]),
            self.make_action_button(parent, "Upload Checklist", "upload_checklist.py", color=theme.COLORS["purple"]),
        ]

    def instagram_buttons(self, parent) -> list[Any]:
        return [
            self.make_action_button(parent, "Upload One Instagram Reel", "instagram_uploader.py", color=theme.COLORS["red"], public_warning=True, initial_input="1\n"),
            self.make_action_button(parent, "Upload All Instagram Reels", "instagram_uploader.py", color=theme.COLORS["red"], public_warning=True, initial_input="2\n"),
            self.make_action_button(parent, "Instagram Setup Check", "zernio_setup_check.py", color=theme.COLORS["green"]),
            self.make_action_button(parent, "Connected Accounts", "zernio_accounts_check.py", color=theme.COLORS["purple"]),
        ]

    def tiktok_buttons(self, parent) -> list[Any]:
        return [
            self.make_action_button(parent, "Upload One TikTok", "tiktok_uploader.py", color=theme.COLORS["red"], public_warning=True, initial_input="1\n"),
            self.make_action_button(parent, "Upload All TikToks", "tiktok_uploader.py", color=theme.COLORS["red"], public_warning=True, initial_input="2\n"),
            self.make_action_button(parent, "TikTok Setup Check", "zernio_setup_check.py", color=theme.COLORS["green"]),
            self.make_action_button(parent, "Connected Accounts", "zernio_accounts_check.py", color=theme.COLORS["purple"]),
        ]

    def build_maintenance_page(self, parent) -> None:
        actions = self.make_section(parent, "Maintenance Tools", 0)
        buttons = [
            self.make_action_button(actions, "Project Status", "project_status.py", color=theme.COLORS["blue"]),
            self.make_action_button(
                actions,
                "Clear Cycle Cache",
                "clear_cycle_cache.py",
                color=theme.COLORS["red"],
                destructive_warning=(
                    "This starts the cycle cleanup tool.\n\n"
                    "It can delete generated files from exports/, output/, posted/, and approval/ "
                    "after its own CLEAR confirmation.\n\nLaunch it?"
                ),
            ),
            self.make_action_button(
                actions,
                "Reset Stage",
                "reset_stage.py",
                color=theme.COLORS["amber"],
                destructive_warning=(
                    "This starts the reset-stage tool.\n\n"
                    "It may move a topic back to an earlier generation stage after its own prompts.\n\nLaunch it?"
                ),
            ),
            self.make_action_button(actions, "Refresh Export Info", "refresh_export_info.py", color=theme.COLORS["purple"]),
            self.make_action_button(actions, "Open Archive Folder", command=lambda: dialogs.open_folder(PROJECT_ROOT / "archive"), color=theme.COLORS["blue"]),
            self.make_action_button(actions, "Open Logs Folder", command=lambda: dialogs.open_folder(PROJECT_ROOT / "logs"), color=theme.COLORS["blue"]),
            self.make_action_button(actions, "Open Project Folder", command=lambda: dialogs.open_folder(PROJECT_ROOT), color=theme.COLORS["green"]),
        ]
        self.grid_buttons(actions, buttons, columns=3)

    def build_settings_page(self, parent) -> None:
        config_section = self.make_section(parent, "Project Configuration", 0)
        self.build_config_editor(config_section)

        visual_section = self.make_section(parent, "Visual Mode", 1)
        self.build_visual_controls(visual_section)

        api_section = self.make_section(parent, "API Checks", 2)
        buttons = [
            self.make_action_button(api_section, "OpenAI Configuration Check", command=self.check_openai_config, color=theme.COLORS["green"]),
            self.make_action_button(api_section, "Pexels Setup Check", "pexels_setup_check.py", color=theme.COLORS["green"]),
            self.make_action_button(api_section, "YouTube Setup Check", "youtube_setup_check.py", color=theme.COLORS["green"]),
            self.make_action_button(api_section, "Zernio Setup Check", "zernio_setup_check.py", color=theme.COLORS["green"]),
            self.make_action_button(api_section, "Zernio Account Check", "zernio_accounts_check.py", color=theme.COLORS["purple"]),
        ]
        self.grid_buttons(api_section, buttons, columns=3)

    def build_config_editor(self, parent) -> None:
        values = load_config_values()
        self.config_entries = {}
        self.config_switches = {}

        form = ctk.CTkFrame(parent, fg_color=theme.COLORS["surface"], corner_radius=theme.CORNER_RADIUS)
        form.grid(row=1, column=0, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        for row, (name, field_type) in enumerate(CONFIG_FIELDS.items()):
            ctk.CTkLabel(
                form,
                text=name,
                font=theme.FONTS["body"],
                text_color=theme.COLORS["text"],
            ).grid(row=row, column=0, sticky="w", padx=theme.SPACING["md"], pady=theme.SPACING["xs"])

            current_value = values.get(name, "")

            if field_type == "bool":
                switch = ctk.CTkSwitch(form, text="", progress_color=theme.COLORS["green"])
                switch.grid(row=row, column=1, sticky="w", padx=theme.SPACING["md"], pady=theme.SPACING["xs"])

                if current_value is True:
                    switch.select()
                else:
                    switch.deselect()

                self.config_switches[name] = switch
            elif name == "IMAGE_STYLE":
                textbox = ctk.CTkTextbox(form, height=80, corner_radius=theme.CORNER_RADIUS)
                textbox.insert("1.0", str(current_value))
                textbox.grid(row=row, column=1, sticky="ew", padx=theme.SPACING["md"], pady=theme.SPACING["xs"])
                self.config_entries[name] = textbox
            else:
                entry = ctk.CTkEntry(form, corner_radius=theme.CORNER_RADIUS)
                entry.insert(0, "None" if current_value is None else str(current_value))
                entry.grid(row=row, column=1, sticky="ew", padx=theme.SPACING["md"], pady=theme.SPACING["xs"])
                self.config_entries[name] = entry

        button_row = ctk.CTkFrame(parent, fg_color="transparent")
        button_row.grid(row=2, column=0, sticky="ew", pady=theme.SPACING["md"])
        self.grid_buttons(button_row, [
            self.make_action_button(button_row, "Save Settings", command=self.save_config_settings, color=theme.COLORS["green"]),
            self.make_action_button(button_row, "Reload Settings", command=lambda: self.show_page("Settings"), color=theme.COLORS["blue"]),
            self.make_action_button(button_row, "Restore Last Backup", command=self.restore_last_config_backup, color=theme.COLORS["amber"]),
        ], columns=3)

    def save_config_settings(self) -> None:
        try:
            new_values = {}

            for name in CONFIG_FIELDS:
                if CONFIG_FIELDS[name] == "bool":
                    new_values[name] = validate_config_value(
                        name,
                        "",
                        bool_value=bool(self.config_switches[name].get()),
                    )
                elif name == "IMAGE_STYLE":
                    raw_value = self.config_entries[name].get("1.0", "end-1c")
                    new_values[name] = validate_config_value(name, raw_value)
                else:
                    raw_value = self.config_entries[name].get()
                    new_values[name] = validate_config_value(name, raw_value)
        except ValueError as error:
            dialogs.show_error("Invalid Settings", str(error))
            return

        try:
            original_text = CONFIG_PATH.read_text(encoding="utf-8")
        except OSError as error:
            dialogs.show_error("Config Error", str(error))
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = PROJECT_ROOT / f"config.py.backup-{timestamp}"
        backup_path.write_text(original_text, encoding="utf-8")

        lines = original_text.splitlines()
        replaced = set()

        for index, line in enumerate(lines):
            match = re.match(r"^([A-Z0-9_]+)\s*=", line)

            if not match:
                continue

            name = match.group(1)

            if name in new_values:
                lines[index] = f"{name} = {format_config_value(new_values[name])}"
                replaced.add(name)

        for name, value in new_values.items():
            if name not in replaced:
                lines.append(f"{name} = {format_config_value(value)}")

        CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        dialogs.show_info("Settings Saved", f"Saved config.py.\nBackup created:\n{backup_path.name}")

    def restore_last_config_backup(self) -> None:
        backups = sorted(PROJECT_ROOT.glob("config.py.backup-*"))

        if not backups:
            dialogs.show_warning("No Backup", "No config.py backups were found.")
            return

        latest_backup = backups[-1]

        if not dialogs.confirm(
            "Restore Backup",
            f"Restore this backup over config.py?\n\n{latest_backup.name}",
        ):
            return

        CONFIG_PATH.write_text(latest_backup.read_text(encoding="utf-8"), encoding="utf-8")
        dialogs.show_info("Backup Restored", f"Restored {latest_backup.name}.")
        self.show_page("Settings")

    def build_visual_controls(self, parent) -> None:
        card = self.make_card(parent)
        card.grid(row=1, column=0, sticky="ew")

        self.visual_label = ctk.CTkLabel(
            card,
            text=self.get_visual_mode_text(),
            font=theme.FONTS["body"],
            text_color=theme.COLORS["text"],
        )
        self.visual_label.grid(row=0, column=0, sticky="w", padx=theme.SPACING["md"], pady=theme.SPACING["md"])

        buttons = [
            self.make_action_button(card, "OpenAI Images", "generate_images.py", color=theme.COLORS["blue"], initial_input="1\n"),
            self.make_action_button(card, "Pexels Images", command=lambda: self.save_pexels_mode("images"), color=theme.COLORS["purple"]),
            self.make_action_button(card, "Pexels Videos", command=lambda: self.save_pexels_mode("videos"), color=theme.COLORS["purple"]),
            self.make_action_button(card, "Run Visual Mode Tool", "visual_mode.py", color=theme.COLORS["amber"]),
        ]
        self.grid_buttons(card, buttons, columns=4)

    def get_visual_mode_text(self) -> str:
        if not VISUAL_MODE_PATH.exists():
            return "Current Pexels mode: images (default)"

        try:
            data = json.loads(VISUAL_MODE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return "Current Pexels mode: visual_mode.json is invalid"

        return f"Current Pexels mode: {data.get('pexels_mode', 'unknown')}"

    def save_pexels_mode(self, mode: str) -> None:
        VISUAL_MODE_PATH.write_text(
            json.dumps({"pexels_mode": mode}, indent=4),
            encoding="utf-8",
        )

        if hasattr(self, "visual_label"):
            self.visual_label.configure(text=self.get_visual_mode_text())

        dialogs.show_info("Visual Mode Saved", f"Pexels mode set to {mode}.")

    def check_openai_config(self) -> None:
        env_path = PROJECT_ROOT / ".env"

        if not env_path.exists():
            dialogs.show_warning("OpenAI Check", ".env file is missing.")
            return

        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            dialogs.show_error("OpenAI Check", "Could not read .env.")
            return

        has_key = any(
            line.strip().startswith("OPENAI_API_KEY=")
            and line.split("=", 1)[1].strip()
            for line in lines
            if not line.strip().startswith("#")
        )

        if has_key:
            dialogs.show_info("OpenAI Check", "OPENAI_API_KEY exists in .env.")
        else:
            dialogs.show_warning("OpenAI Check", "OPENAI_API_KEY is missing in .env.")

    def build_logs_page(self, parent) -> None:
        info = self.make_section(parent, "Console & UI Logs", 0)
        ctk.CTkLabel(
            info,
            text=(
                "The live console is always available at the bottom of the window. "
                "UI task logs are saved under logs/ui/."
            ),
            font=theme.FONTS["body"],
            text_color=theme.COLORS["muted"],
            wraplength=900,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, theme.SPACING["md"]))

        buttons = [
            self.make_action_button(info, "Save Current Console Log", command=self.save_console_log, color=theme.COLORS["green"]),
            self.make_action_button(info, "Clear Console", command=self.clear_console, color=theme.COLORS["amber"]),
            self.make_action_button(info, "Open UI Log Folder", command=lambda: dialogs.open_folder(UI_LOG_FOLDER), color=theme.COLORS["blue"]),
        ]
        self.grid_buttons(info, buttons, columns=3)

    def start_script(self, script_name: str, initial_input: str = "") -> None:
        if self.runner.start_script(script_name, initial_input=initial_input):
            self.current_task_text = script_name
            self.set_task_state("Running", script_name)
            self.progress_bar.start()
            self.append_console(f"\n--- Running {script_name} ---\n")

    def append_console(self, text: str) -> None:
        self.console_text.insert("end", text)
        self.console_text.see("end")

    def clear_console(self) -> None:
        self.console_text.delete("1.0", "end")

    def copy_console(self) -> None:
        text = self.console_text.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def save_console_log(self) -> None:
        UI_LOG_FOLDER.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path = UI_LOG_FOLDER / f"ui-{timestamp}.log"
        log_path.write_text(self.console_text.get("1.0", "end-1c"), encoding="utf-8")
        dialogs.show_info("Log Saved", f"Saved log:\n{log_path}")

    def send_console_input(self) -> None:
        text = self.console_input.get()

        if not text:
            return

        if self.runner.send_input(text):
            self.append_console(f"> {text}\n")
            self.console_input.delete(0, "end")

    def stop_task(self) -> None:
        self.runner.stop()

    def poll_process_events(self) -> None:
        while not self.runner.events.empty():
            event = self.runner.events.get()

            if event.kind in {"stdout", "stderr"}:
                prefix = "" if event.kind == "stdout" else "[stderr] "
                self.append_console(prefix + event.message)
                self.recent_output = (self.recent_output + event.message)[-500:]
                self.update_progress_from_output(self.recent_output)
            elif event.kind == "state":
                if event.message:
                    self.append_console(event.message + "\n")

                if event.state:
                    self.set_task_state(event.state.title(), event.script_name)

                if event.state in {"completed", "failed", "stopped"}:
                    self.progress_bar.stop()
                    self.progress_bar.set(0)
                    self.current_task_text = "Idle"
                    self.refresh_dashboard()

        self.root.after(100, self.poll_process_events)

    def update_progress_from_output(self, line: str) -> None:
        markers = [
            "Processing ",
            "Topics to process",
            "Rendering",
            "Uploading",
            "Completed",
            "Waiting",
            "Choose ",
            "Type ",
        ]

        if any(marker in line for marker in markers):
            text = line.strip()

            if text:
                self.script_label.configure(text=text[:120])

        if ("Enter " in line or "Choose " in line or "Type " in line) and ":" in line:
            self.set_task_state("Waiting For Input", self.runner.current_script)

    def set_task_state(self, state: str, script_name: str = "") -> None:
        self.task_badge.configure(
            text=state,
            fg_color=theme.status_color(state),
        )
        self.script_label.configure(text=script_name or "No task running")

    def on_close(self) -> None:
        if self.runner.is_running():
            if not dialogs.confirm(
                "Task Running",
                "A task is still running. Stop it and close the app?",
            ):
                return

            self.runner.stop()

        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    global ctk
    global theme
    global dialogs
    global ProcessRunner
    global ProcessEvent
    global StatusCard
    global count_project_status

    try:
        import customtkinter as customtkinter_module
    except ImportError:
        show_customtkinter_missing_error()
        return

    from ui import dialogs as dialogs_module
    from ui import theme as theme_module
    from ui.dashboard import StatusCard as StatusCardClass
    from ui.dashboard import count_project_status as count_status_function
    from ui.process_runner import ProcessEvent as ProcessEventClass
    from ui.process_runner import ProcessRunner as ProcessRunnerClass

    ctk = customtkinter_module
    theme = theme_module
    dialogs = dialogs_module
    ProcessRunner = ProcessRunnerClass
    ProcessEvent = ProcessEventClass
    StatusCard = StatusCardClass
    count_project_status = count_status_function

    theme.apply_theme(ctk)
    app = InfoBuilderStudio()
    app.run()


if __name__ == "__main__":
    main()
