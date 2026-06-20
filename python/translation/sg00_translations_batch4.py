#!/usr/bin/env python3
"""SG00 remaining translations - batch 4 (final cleanup)."""

from __future__ import annotations
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
TRANSLATED_DIR = BASE_DIR / "translated" / "ko"

DIALOGUE_RE = re.compile(
    r"^(\s+0x[0-9A-Fa-f]+\s+\[0x[0-9A-Fa-f]+\]\s+\[script:[0-9A-Fa-f]+ [0-9A-Fa-f]+\])(.*)"
)

T = {
    # Dots - convert to ellipsis
    "[box:speech]・・・・・": "[box:speech]……",
    "・・・": "…",
    # Arena rules (missed from batch 3)
    '[box:speech]この「内魔陣」ゲームではまず、規定賞金が[br]\u201C200セウム\u201Cということ、上限ターンが[br]\u201C20ターン\u201Cということが決まっています':
        '[box:speech]이 「내마진」 게임에서는 우선, 규정 상금이[br]\u201C200세움\u201C이라는 것, 상한 턴이[br]\u201C20턴\u201C이라는 것이 정해져 있습니다',
    # Item name
    "うつせみの玉": "우츠세미의 구슬",
    # Dialogue with garbled prefix - translate the real part
    "尖[box:speech]そんなにあせってはダメだ…": "尖[box:speech]그렇게 서두르면 안 돼…",
    # Children's game (daruma-san ga koronda)
    "こーろんだ": "무궁화꽃이",
}


def main():
    filepath = TRANSLATED_DIR / "SG00_STG.txt"
    text = filepath.read_text(encoding="utf-8")
    count = 0
    lines = text.split("\n")
    new_lines = []
    for line in lines:
        m = DIALOGUE_RE.match(line)
        if m:
            prefix, body = m.group(1), m.group(2)
            if body in T:
                new_lines.append(prefix + T[body])
                count += 1
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    filepath.write_text("\n".join(new_lines), encoding="utf-8")
    print(f"SG00 batch 4: {count} entries translated")


if __name__ == "__main__":
    main()
