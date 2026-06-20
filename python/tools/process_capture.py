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


def find_offsets(raw: bytes) -> list:
    """Every (stage, file_offset) where these exact bytes occur in an original STG."""
    hits = []
    for stage in STAGES:
        p = GAME_DIR / f"{stage}.STG"
        if not p.exists():
            continue
        data = p.read_bytes()
        pos = data.find(raw)
        while pos != -1:
            hits.append((stage, pos))
            pos = data.find(raw, pos + 1)
    return hits


def process(log_path: Path) -> dict:
    table = dt.build_decode_table()
    entries = parse_capture_log(log_path)
    seen = set()
    missed = []
    total = 0
    matched = 0
    for _addr, raw in entries:
        total += 1
        # MISSED gate: the captured bytes appear verbatim in an original STG,
        # i.e. this displayed line is still the untranslated original. A
        # translated (Korean-remapped) line will NOT match the original.
        hits = find_offsets(raw)
        if not hits:
            continue
        matched += 1
        text = decode_line(raw, table).strip()   # readable JP for the worklist
        # Filter: must have meaningful text and contain actual Japanese hiragana/katakana
        if not text or text in seen or not contains_japanese(text):
            continue
        seen.add(text)
        stage, off = hits[0]
        missed.append({"text": text, "stage": stage, "offset": off,
                       "all_hits": hits})
    return {"missed": missed,
            "stats": {"total": total, "matched_original": matched,
                      "unique_missed": len(missed)}}


def write_worklist(result: dict) -> Path:
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    path = CAPTURE_DIR / "missed_displayed.txt"
    s = result["stats"]
    lines = [
        "# Missed displayed dialogue (captured at runtime)",
        f"# total hits={s['total']}  matched_original={s['matched_original']}  unique={s['unique_missed']}",
        "# Each entry: <id> / JP / KO (fill KO).  id = STAGE:0xOFFSET or UNMAPPED:n",
        "",
    ]
    for i, m in enumerate(result["missed"]):
        idtok = (f"{m['stage']}:0x{m['offset']:08X}" if m["stage"] is not None
                 else f"UNMAPPED:{i}")
        lines += [f"  {idtok}", f"    JP: {m['text']}", f"    KO: "]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    log_path = Path(argv[0]) if argv else (CAPTURE_DIR / "capture.log")
    if not log_path.exists():
        print(f"ERROR: capture log not found: {log_path}", file=sys.stderr)
        return 1
    result = process(log_path)
    out = write_worklist(result)
    s = result["stats"]
    print(f"hits={s['total']} matched_original={s['matched_original']} unique missed={s['unique_missed']}")
    print(f"worklist -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
