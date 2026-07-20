"""Dashboard widgets and project status counting."""

from __future__ import annotations

import json
from pathlib import Path

import customtkinter as ctk

from ui.theme import CARD_HEIGHT, COLORS, CORNER_RADIUS, FONTS, SPACING


def _topic_folders(folder: Path) -> list[Path]:
    if not folder.exists():
        return []

    return [
        path
        for path in folder.iterdir()
        if path.is_dir() and path.name != "__pycache__"
    ]


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _approval_records(project_root: Path) -> list[dict]:
    approval_folder = project_root / "approval"

    if not approval_folder.exists():
        return []

    records = []

    for approval_path in approval_folder.rglob("approval.json"):
        data = _read_json(approval_path)

        if data:
            records.append(data)

    return records


def count_project_status(project_root: Path) -> dict[str, int]:
    topics_path = project_root / "topics.txt"

    try:
        topic_lines = [
            line.strip()
            for line in topics_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except OSError:
        topic_lines = []

    approval_records = _approval_records(project_root)
    scripts_awaiting = 0
    approved_scripts = 0
    videos_generating = 0

    for record in approval_records:
        status = record.get("status", "")
        approved = record.get("approved") is True

        if status == "pending_review" and not approved:
            scripts_awaiting += 1
        elif status == "approved" and approved:
            approved_scripts += 1
        elif approved and status not in {
            "approved",
            "completed",
            "rejected",
            "approved_final",
            "rejected_final",
        }:
            videos_generating += 1

    return {
        "Topics waiting": len(topic_lines),
        "Scripts awaiting approval": scripts_awaiting,
        "Approved scripts": approved_scripts,
        "Videos being generated": videos_generating,
        "Completed videos": len(_topic_folders(project_root / "completed")),
        "Exported videos": len(list((project_root / "exports").glob("*.mp4"))),
        "Posted videos": len(_topic_folders(project_root / "posted")),
        "Rejected items": len(_topic_folders(project_root / "rejected")),
    }


class StatusCard(ctk.CTkFrame):
    def __init__(self, parent, title: str, accent: str):
        super().__init__(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=CORNER_RADIUS,
            height=CARD_HEIGHT,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)

        self.accent_bar = ctk.CTkFrame(
            self,
            fg_color=accent,
            width=5,
            corner_radius=CORNER_RADIUS,
        )
        self.accent_bar.grid(row=0, column=0, rowspan=2, sticky="nsw")

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=FONTS["card_title"],
            text_color=COLORS["muted"],
            anchor="w",
        )
        self.title_label.grid(row=0, column=0, padx=(SPACING["lg"], SPACING["md"]), pady=(SPACING["md"], 0), sticky="ew")

        self.value_label = ctk.CTkLabel(
            self,
            text="0",
            font=FONTS["card_value"],
            text_color=COLORS["text"],
            anchor="w",
        )
        self.value_label.grid(row=1, column=0, padx=(SPACING["lg"], SPACING["md"]), pady=(0, SPACING["md"]), sticky="ew")

    def set_value(self, value: int) -> None:
        self.value_label.configure(text=str(value))
