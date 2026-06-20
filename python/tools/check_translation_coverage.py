#!/usr/bin/env python3
"""Translation coverage checker for Arc the Lad 2 STG stages.

Reports untranslated/decoder-missed dialogue in honest confidence tiers.
Exit 0 never asserts completeness (see docs/superpowers/specs).
"""
import sys
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
