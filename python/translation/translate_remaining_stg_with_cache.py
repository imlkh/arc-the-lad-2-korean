#!/usr/bin/env python3
"""Generate missing STG translation files from existing translation memory.

Strategy:
1) Build exact Japanese->Korean cache from already translated STG files.
2) For missing STG files, apply exact cache match first.
3) Apply glossary replacements for names/terms as fallback.
4) Keep unresolved text in Japanese (explicitly reported in stats).
"""

from __future__ import annotations

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = BASE_DIR / "output" / "decoded" / "stg"
KO_DIR = BASE_DIR / "translated" / "ko"

STG_NAMES = [
    "S100",
    "S200",
    "S300",
    "S400",
    "S500",
    "S600",
    "S700",
    "S800",
    "S900",
    "SA00",
    "SB00",
    "SC00",
    "SD00",
    "SE00",
    "SF00",
    "SG00",
    "SH00",
    "SI00",
    "SJ00",
]

DIALOGUE_RE = re.compile(
    r"^(\s*0x[0-9A-Fa-f]+\s+\[0x[0-9A-Fa-f]+\]\s+\[script:[0-9A-Fa-f ]+\])(.+)$"
)
OFFSET_RE = re.compile(r"^\s*(0x[0-9A-Fa-f]+)")

GLOSSARY = {
    "エルク": "엘크",
    "リーザ": "리자",
    "シャンテ": "샨테",
    "ポコ": "포코",
    "トッシュ": "토슈",
    "ゴーゲン": "고겐",
    "シュウ": "슈우",
    "ククル": "쿠쿠루",
    "グルガ": "그루가",
    "イーガ": "이가",
    "サニア": "사니아",
    "アーク": "아크",
    "ちょこ": "쵸코",
    "チョコ": "쵸코",
    "ヂークベック": "지크벡",
    "ガルアーノ": "갈아노",
    "ヤグン": "야군",
    "アンデル": "안델",
    "クライブ": "크라이브",
    "ロマリア": "로말리아",
    "アルディア": "알디아",
    "プロディアス": "프로디아스",
    "ミルマーナ": "밀마나",
    "スメリア": "스메리아",
    "パレンシア": "팔렌시아",
    "シルバーノア": "실버노아",
    "インディゴス": "인디고스",
    "ホルン": "호른",
    "精霊": "정령",
    "魔物": "마물",
    "聖柩": "성궤",
    "闘技場": "투기장",
    "封印": "봉인",
}


def read_dialogue_by_offset(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = DIALOGUE_RE.match(line)
        if not m:
            continue
        off = OFFSET_RE.match(line)
        if not off:
            continue
        mapping[off.group(1).upper()] = m.group(2)
    return mapping


def build_exact_cache() -> dict[str, str]:
    cache: dict[str, str] = {}
    for ko_path in sorted(KO_DIR.glob("*_STG.txt")):
        stage = ko_path.name[:4]
        src_path = SRC_DIR / f"{stage}_STG.txt"
        if not src_path.exists():
            continue

        src_by_offset = read_dialogue_by_offset(src_path)
        ko_by_offset = read_dialogue_by_offset(ko_path)

        for off, jp in src_by_offset.items():
            ko = ko_by_offset.get(off)
            if not ko:
                continue
            if jp == ko:
                continue
            cache.setdefault(jp, ko)
    return cache


def apply_glossary(text: str) -> str:
    out = text
    for jp, ko in GLOSSARY.items():
        out = out.replace(jp, ko)
    return out


def translate_missing_stgs() -> int:
    cache = build_exact_cache()
    print(f"[info] exact cache entries: {len(cache)}")

    existing = {p.name[:4] for p in KO_DIR.glob("*_STG.txt")}
    missing = [s for s in STG_NAMES if s not in existing]

    if not missing:
        print("[info] no missing STG translation files")
        return 0

    for stage in missing:
        src_path = SRC_DIR / f"{stage}_STG.txt"
        out_path = KO_DIR / f"{stage}_STG.txt"
        if not src_path.exists():
            print(f"[skip] missing source: {src_path}")
            continue

        total = 0
        exact_hits = 0
        glossary_hits = 0
        unresolved = 0
        out_lines: list[str] = []

        for line in src_path.read_text(encoding="utf-8").splitlines():
            m = DIALOGUE_RE.match(line)
            if not m:
                out_lines.append(line)
                continue

            total += 1
            prefix, jp_text = m.group(1), m.group(2)

            ko_text = cache.get(jp_text)
            if ko_text is not None:
                exact_hits += 1
                out_lines.append(prefix + ko_text)
                continue

            replaced = apply_glossary(jp_text)
            if replaced != jp_text:
                glossary_hits += 1
                out_lines.append(prefix + replaced)
            else:
                unresolved += 1
                out_lines.append(prefix + jp_text)

        out_path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
        coverage = (exact_hits + glossary_hits) / total if total else 1.0
        print(
            f"[done] {stage}: total={total}, exact={exact_hits}, "
            f"glossary={glossary_hits}, unresolved={unresolved}, "
            f"coverage={coverage:.1%}"
        )

    print("[info] generated missing STG files under translated/ko/")
    return 0


if __name__ == "__main__":
    raise SystemExit(translate_missing_stgs())
