#!/usr/bin/env python3
"""Apply exact Japanese->Korean cache matches to existing STG translations.

This script is intentionally conservative:
- Only replaces a line when source JP text exactly matches a cached JP key.
- Skips offsets listed in each stage invalid report.
- Keeps line prefixes/metadata untouched.
"""

from __future__ import annotations

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = BASE_DIR / "output" / "decoded" / "stg"
KO_DIR = BASE_DIR / "translated" / "ko"

DIALOGUE_RE = re.compile(
    r"^(\s*0x[0-9A-Fa-f]+\s+\[0x[0-9A-Fa-f]+\]\s+\[script:[0-9A-Fa-f ]+\])(.+)$"
)
OFFSET_RE = re.compile(r"^\s*(0x[0-9A-Fa-f]+)")
JP_RE = re.compile(r"[ぁ-ゖァ-ヺ一-龯]")
INVALID_OFFSET_RE = re.compile(r"offset\s+(0x[0-9A-Fa-f]+)")


def read_dialogue_by_offset(path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = DIALOGUE_RE.match(line)
        if not m:
            continue
        off = OFFSET_RE.match(line)
        if not off:
            continue
        mapping[off.group(1).upper()] = m.group(2)
    return mapping


def load_invalid_offsets(stage: str) -> set[str]:
    report = SRC_DIR / f"{stage}_STG_invalid_report.txt"
    if not report.exists():
        return set()
    out: set[str] = set()
    for line in report.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = INVALID_OFFSET_RE.search(line)
        if m:
            out.add(m.group(1).upper())
    return out


def build_exact_cache() -> dict[str, str]:
    cache: dict[str, str] = {}
    for ko_path in sorted(KO_DIR.glob("S*_STG.txt")):
        src_path = SRC_DIR / ko_path.name
        if not src_path.exists():
            continue

        src_by_offset = read_dialogue_by_offset(src_path)
        ko_by_offset = read_dialogue_by_offset(ko_path)

        for off, jp in src_by_offset.items():
            ko = ko_by_offset.get(off)
            if not ko or ko == jp:
                continue
            cache.setdefault(jp, ko)
    return cache


def apply_cache_to_file(path: Path, cache: dict[str, str]) -> tuple[int, int, int]:
    stage = path.name[:4]
    src_path = SRC_DIR / path.name
    if not src_path.exists():
        return (0, 0, 0)

    src_by_offset = read_dialogue_by_offset(src_path)
    invalid_offsets = load_invalid_offsets(stage)

    candidates = 0
    replaced = 0
    skipped_invalid = 0
    out_lines: list[str] = []

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = DIALOGUE_RE.match(line)
        if not m:
            out_lines.append(line)
            continue

        prefix, cur_text = m.group(1), m.group(2)
        off_m = OFFSET_RE.match(line)
        if not off_m:
            out_lines.append(line)
            continue
        off = off_m.group(1).upper()

        if not JP_RE.search(cur_text):
            out_lines.append(line)
            continue

        candidates += 1
        if off in invalid_offsets:
            skipped_invalid += 1
            out_lines.append(line)
            continue

        src_jp = src_by_offset.get(off)
        if src_jp is None:
            out_lines.append(line)
            continue

        ko = cache.get(src_jp)
        if ko is not None and ko != cur_text:
            replaced += 1
            out_lines.append(prefix + ko)
        else:
            out_lines.append(line)

    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return (candidates, replaced, skipped_invalid)


def main() -> int:
    cache = build_exact_cache()
    print(f"[info] exact cache entries: {len(cache)}")

    total_candidates = 0
    total_replaced = 0
    total_skipped_invalid = 0

    for ko_path in sorted(KO_DIR.glob("S*_STG.txt")):
        candidates, replaced, skipped_invalid = apply_cache_to_file(ko_path, cache)
        if candidates == 0:
            continue
        total_candidates += candidates
        total_replaced += replaced
        total_skipped_invalid += skipped_invalid
        if replaced:
            print(
                f"[done] {ko_path.name[:4]}: candidates={candidates}, "
                f"replaced={replaced}, skipped_invalid={skipped_invalid}"
            )

    print(
        f"[summary] candidates={total_candidates}, replaced={total_replaced}, "
        f"skipped_invalid={total_skipped_invalid}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
