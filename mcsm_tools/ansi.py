"""Shared ANSI escape parsing for the tkinter and PyQt consoles."""

import re

from .theme import Nord

ANSI_RE = re.compile(r'\x1b\[([\d;]*)m')


def parse_ansi(text: str) -> list[tuple[str | None, str | None, bool, str]]:
    """Split text into ``(fg, bg, bold, text)`` segments using the Nord palette."""
    parts = ANSI_RE.split(text)
    segments = []
    fg = None
    bg = None
    bold = False
    for i, part in enumerate(parts):
        if i % 2 == 0:
            segments.append((fg, bg, bold, part))
        else:
            codes = part.split(';') if part else []
            for c in codes:
                if c == '' or c == '0':
                    fg = bg = None
                    bold = False
                elif c == '1':
                    bold = True
                elif c == '22':
                    bold = False
                elif c in Nord.ansi_colors:
                    fg = Nord.ansi_colors[c]
                elif c in Nord.ansi_bg:
                    bg = Nord.ansi_bg[c]
    return segments
