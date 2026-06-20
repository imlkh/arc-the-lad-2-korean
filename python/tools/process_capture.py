#!/usr/bin/env python3
"""Post-process PCSX-Redux capture logs: decode, flag still-Japanese (missed)
displayed lines, map each to its STG offset by searching the original binaries.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GAME_DIR = Path(__file__).resolve().parents[3]
CAPTURE_DIR = REPO_ROOT / "output" / "capture"
STAGES = [f"S{c}00" for c in
          ["1","2","3","4","5","6","7","8","9","A","B","C","D","E","F","G","H","I","J"]]

sys.path.insert(0, str(REPO_ROOT / "python" / "decode"))
import decode_text as dt  # noqa: E402

_LINE = re.compile(r"^addr=0x([0-9A-Fa-f]+)\s+bytes=([0-9A-Fa-f ]+)$")


def parse_capture_log(path: Path) -> list:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        raw = bytes(int(b, 16) for b in m.group(2).split())
        out.append((addr, raw))
    return out


def contains_japanese(text: str) -> bool:
    for ch in text:
        cp = ord(ch)
        if 0x3041 <= cp <= 0x3096 or 0x30A1 <= cp <= 0x30FA:
            return True
    return False


def decode_line(raw: bytes, table) -> str:
    """Japanese-table decode of captured bytes — for human-readable display only.
    NOT a missed/translated classifier (patched Korean bytes mis-decode here)."""
    text, _consumed = dt.decode_string(raw + b"\x00", 0, table)
    return text
