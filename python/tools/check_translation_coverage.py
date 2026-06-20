#!/usr/bin/env python3
"""Translation coverage checker for Arc the Lad 2 STG stages.

Reports untranslated/decoder-missed dialogue in honest confidence tiers.
Exit 0 never asserts completeness (see docs/superpowers/specs).
"""
import sys
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GAME_DIR = Path(__file__).resolve().parents[3]
DECODED_DIR = REPO_ROOT / "output" / "decoded" / "stg"
TRANS_DIR = REPO_ROOT / "translated" / "ko"
COVERAGE_DIR = REPO_ROOT / "output" / "coverage"

STAGES = [f"S{c}00" for c in
          ["1", "2", "3", "4", "5", "6", "7", "8", "9",
           "A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]]

# Reuse the scan-based decoder; do not duplicate its logic.
sys.path.insert(0, str(REPO_ROOT / "python" / "decode"))
import decode_text as dt  # noqa: E402


_ENTRY_RE = re.compile(r"^\s*0x([0-9A-Fa-f]+)\s")


def _entry_offset(line: str):
    m = _ENTRY_RE.match(line)
    return int(m.group(1), 16) if m else None


def contains_japanese(text: str) -> bool:
    """True if text contains hiragana/katakana letters (untranslated kana).

    Ranges exclude, by construction, the intentional middle dot ・ (U+30FB)
    and the punctuation 「」、。… which lie outside these ranges.
    """
    for ch in text:
        cp = ord(ch)
        if 0x3041 <= cp <= 0x3096:        # hiragana
            return True
        if 0x30A1 <= cp <= 0x30FA or cp == 0x30FC:  # katakana (skips 30FB ・)
            return True
    return False


def parse_translation_file(path: Path) -> dict:
    """Return {offset: visible_text} from a translated/ko STG file.

    Visible text is everything after the final ']' on the entry line.
    """
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        off = _entry_offset(line)
        if off is None:
            continue
        text = line.rsplit("]", 1)[-1] if "]" in line else ""
        out[off] = text.strip()
    return out


def parse_decoded_offsets(path: Path) -> set:
    """Return the set of dialogue offsets present in a decoded STG file."""
    out = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        off = _entry_offset(line)
        if off is not None:
            out.add(off)
    return out


_ADDR_RE = re.compile(r"0x([0-9A-Fa-f]+)")


def load_invalid_offsets(stage: str) -> set:
    """Offsets the decoder marked invalid (garbage/debug/single-char).

    Reads the generated invalid report; returns empty set if absent.
    Report entry lines look like '  Line 1449: 0x003ABC02 [0x8005] ...'.
    """
    report = DECODED_DIR / f"{stage}_STG_invalid_report.txt"
    if not report.exists():
        return set()
    out = set()
    for line in report.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = _ADDR_RE.search(line)
        if m:
            out.add(int(m.group(1), 16))
    return out


def tier1_untranslated(translations: dict) -> list:
    """Entries whose translated text still contains Japanese kana."""
    return sorted(
        (off, text) for off, text in translations.items()
        if contains_japanese(text)
    )
