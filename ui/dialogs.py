"""Dialogs and platform helpers used by the desktop UI."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from ui.theme import COLORS, CORNER_RADIUS, FONTS, SPACING


class Tooltip:
    """Small hover tooltip for disabled or unfamiliar controls."""

    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.window = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _event=None) -> None:
        if not self.text or self.window is not None:
            return

        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.window = tk.Toplevel(self.widget)
        self.window.wm_overrideredirect(True)
        self.window.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.window,
            text=self.text,
            bg="#0f172a",
            fg="#f8fafc",
            padx=8,
            pady=5,
            font=("Segoe UI", 9),
        )
        label.pack()

    def hide(self, _event=None) -> None:
        if self.window is not None:
            self.window.destroy()
            self.window = None


def show_info(title: str, message: str) -> None:
    messagebox.showinfo(title, message)


def show_error(title: str, message: str) -> None:
    messagebox.showerror(title, message)


def show_warning(title: str, message: str) -> None:
    messagebox.showwarning(title, message)


def confirm(title: str, message: str) -> bool:
    return messagebox.askyesno(title, message)


def open_folder(path: Path) -> None:
    path = Path(path)

    if not path.exists():
        show_error("Missing Folder", f"This folder does not exist:\n{path}")
        return

    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError as error:
        show_error("Open Folder Failed", str(error))


class AddTopicDialog(ctk.CTkToplevel):
    """Simple dialog that safely appends one topic to topics.txt."""

    def __init__(self, parent, topics_path: Path, on_success: Callable[[], None]):
        super().__init__(parent)
        self.topics_path = topics_path
        self.on_success = on_success
        self.title("Add Topic")
        self.geometry("520x220")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.configure(fg_color=COLORS["background"])
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Add a new video topic",
            font=FONTS["section"],
            text_color=COLORS["text"],
        ).grid(row=0, column=0, padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["sm"]), sticky="w")

        self.topic_entry = ctk.CTkEntry(
            self,
            placeholder_text="Type one topic...",
            height=42,
            corner_radius=CORNER_RADIUS,
        )
        self.topic_entry.grid(row=1, column=0, padx=SPACING["lg"], pady=SPACING["sm"], sticky="ew")
        self.topic_entry.focus_set()
        self.topic_entry.bind("<Return>", lambda _event: self.add_topic())

        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.grid(row=2, column=0, padx=SPACING["lg"], pady=SPACING["lg"], sticky="e")

        ctk.CTkButton(
            button_row,
            text="Cancel",
            fg_color=COLORS["surface_light"],
            hover_color=COLORS["border"],
            corner_radius=CORNER_RADIUS,
            command=self.destroy,
        ).pack(side="left", padx=(0, SPACING["sm"]))

        ctk.CTkButton(
            button_row,
            text="Add",
            fg_color=COLORS["green"],
            hover_color="#16a34a",
            corner_radius=CORNER_RADIUS,
            command=self.add_topic,
        ).pack(side="left")

    def add_topic(self) -> None:
        topic = self.topic_entry.get().strip()

        if not topic:
            show_warning("Empty Topic", "Type a topic before adding it.")
            return

        self.topics_path.touch(exist_ok=True)
        current_text = self.topics_path.read_text(encoding="utf-8")
        existing_topics = [
            line.strip()
            for line in current_text.splitlines()
            if line.strip()
        ]

        if topic in existing_topics:
            show_warning("Duplicate Topic", "That exact topic already exists.")
            return

        with open(self.topics_path, "a", encoding="utf-8") as topics_file:
            if current_text and not current_text.endswith("\n"):
                topics_file.write("\n")
            topics_file.write(topic + "\n")

        show_info("Topic Added", f"Added topic:\n{topic}")
        self.on_success()
        self.destroy()
