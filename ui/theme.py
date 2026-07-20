"""Centralized visual styling for InfoBuilder Studio."""

COLORS = {
    "background": "#08111f",
    "surface": "#101c2f",
    "surface_light": "#172640",
    "sidebar": "#0b1628",
    "text": "#f4f7fb",
    "muted": "#9aa8bd",
    "purple": "#8b5cf6",
    "blue": "#38bdf8",
    "green": "#22c55e",
    "amber": "#f59e0b",
    "red": "#ef4444",
    "border": "#24344f",
    "console": "#050b14",
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 14,
    "lg": 20,
    "xl": 28,
}

FONTS = {
    "title": ("Segoe UI", 28, "bold"),
    "subtitle": ("Segoe UI", 14),
    "nav": ("Segoe UI", 14, "bold"),
    "section": ("Segoe UI", 20, "bold"),
    "card_title": ("Segoe UI", 14, "bold"),
    "card_value": ("Segoe UI", 34, "bold"),
    "body": ("Segoe UI", 13),
    "small": ("Segoe UI", 11),
    "console": ("Consolas", 12),
}

CORNER_RADIUS = 8
CARD_HEIGHT = 112
SIDEBAR_WIDTH = 230
CONSOLE_HEIGHT = 230


def apply_theme(ctk) -> None:
    """Apply CustomTkinter's dark mode before widgets are created."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")


def status_color(status: str) -> str:
    normalized = status.lower()

    if normalized in {"running", "waiting for input"}:
        return COLORS["blue"]

    if normalized in {"completed", "success"}:
        return COLORS["green"]

    if normalized in {"failed", "error"}:
        return COLORS["red"]

    if normalized in {"stopped", "canceled"}:
        return COLORS["amber"]

    return COLORS["muted"]
