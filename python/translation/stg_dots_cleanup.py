#!/usr/bin/env python3
"""Convert Japanese middle-dot ellipsis (・・・) to Korean ellipsis (…) across STG files."""

from __future__ import annotations
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
TRANSLATED_DIR = BASE_DIR / "translated" / "ko"

DIALOGUE_RE = re.compile(
    r"^(\s+0x[0-9A-Fa-f]+\s+\[0x[0-9A-Fa-f]+\]\s+\[script:[0-9A-Fa-f]+ [0-9A-Fa-f]+\])(.*)"
)

# Map Japanese text → Korean text
# Only for entries that contain ・ patterns and are not MIPS garbage
S100_T = {
    "・・・・・・・": "……",
    "・・・・・": "……",
    "・・・・・・": "……",
    "・・・・・・・？": "……？",
    "・・・": "…",
    # Dramatic dot-by-dot with delays - convert dots individually
    "・[delay:0B]・[delay:0B]・[delay:0B]・": "·[delay:0B]·[delay:0B]·[delay:0B]·",
}

S200_T = {
    "・・・・・": "……",
    "・・・": "…",
    # Dramatic dot with delays and question mark
    "・[delay:0B]・[delay:0B]・[delay:0B]？": "·[delay:0B]·[delay:0B]·[delay:0B]？",
    # Dots with game control sequences
    "[FF:08 0F 01]・・・・・・[delay:3D][box:speech]！？": "[FF:08 0F 01]……[delay:3D][box:speech]！？",
}

SG00_T = {
    "[box:speech]・・・・・": "[box:speech]……",
    "・・・": "…",
}


def apply(stage: str, translations: dict) -> int:
    filepath = TRANSLATED_DIR / f"{stage}_STG.txt"
    text = filepath.read_text(encoding="utf-8")
    count = 0
    lines = text.split("\n")
    new_lines = []
    for line in lines:
        m = DIALOGUE_RE.match(line)
        if m:
            prefix, body = m.group(1), m.group(2)
            if body in translations:
                new_lines.append(prefix + translations[body])
                count += 1
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    filepath.write_text("\n".join(new_lines), encoding="utf-8")
    return count


def main():
    for stage, t in [("S100", S100_T), ("S200", S200_T), ("SG00", SG00_T)]:
        n = apply(stage, t)
        print(f"{stage}: {n} dot entries converted")


if __name__ == "__main__":
    main()
