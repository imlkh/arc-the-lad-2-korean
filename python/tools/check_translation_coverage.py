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
        if 0x30A1 <= cp <= 0x30FA:        # katakana letters (skips 30FB ・)
            return True
        # NOTE: U+30FC (ー, prolonged-sound mark) is deliberately NOT treated as
        # untranslated. The Korean translations use ー intentionally for vowel
        # elongation (e.g. "쵸코...야ー"); flagging it produced 86 false positives.
        # A genuinely untranslated Japanese line always contains real kana above.
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


def tier2_decoder_rejects(data, decode_table, decoded_offsets: set,
                          invalid_offsets: set) -> list:
    """Japanese candidates the garbage filter discarded inside scanned regions.

    Found by diffing scan_stg(filter_garbage=False) against filter_garbage=True.
    Excludes already-decoded and invalid-report offsets.
    """
    kept, _, _ = dt.scan_stg(data, decode_table, filter_garbage=True)
    full, _, _ = dt.scan_stg(data, decode_table, filter_garbage=False)
    kept_offsets = {d[0] for d in kept}
    out = []
    for off, _consumed, text, _opcode in full:
        if off in kept_offsets:
            continue
        if off in decoded_offsets or off in invalid_offsets:
            continue
        if contains_japanese(text):
            out.append((off, text))
    return sorted(set(out))


_PARTICLES = set("はがをにのへともや")


def _score(text: str) -> int:
    kana = sum(1 for c in text if contains_japanese(c))
    particle = 2 if any(c in _PARTICLES for c in text) else 0
    return kana + particle + 1  # +1: it decoded


def byte_accountability(data, decode_table, decoded_offsets: set,
                        invalid_offsets: set):
    """Fraction of text-region string bytes that are explained, plus the
    unaccounted Japanese runs (Tier-3 review candidates).

    A run is accounted if its offset is decoded, in the invalid report, or its
    decoded text is classified garbage by the decoder. Unaccounted Japanese
    runs are returned as (offset, text, score), sorted by descending score.
    """
    total_bytes = 0
    accounted_bytes = 0
    candidates = []
    for start, end, _chunk in dt._get_chunk_text_regions(len(data)):
        pos = start
        while pos < end:
            if data[pos] == 0x00:
                pos += 1
                continue
            text, consumed = dt.decode_string(data, pos, decode_table)
            run = max(consumed, 1)
            total_bytes += run
            is_known = (pos in decoded_offsets or pos in invalid_offsets
                        or dt._is_garbage_text(text))
            if is_known:
                accounted_bytes += run
            elif contains_japanese(text):
                candidates.append((pos, text, _score(text)))
            else:
                accounted_bytes += run  # non-Japanese unknown = not a miss
            pos += run
    frac = (accounted_bytes / total_bytes) if total_bytes else 1.0
    candidates.sort(key=lambda c: c[2], reverse=True)
    return frac, candidates


def check_stage(stage: str, decode_table) -> dict:
    """Run all tiers for one stage. Returns a result dict; never raises."""
    binary = GAME_DIR / f"{stage}.STG"
    decoded = DECODED_DIR / f"{stage}_STG.txt"
    translation = TRANS_DIR / f"{stage}_STG.txt"
    result = {"stage": stage, "status": "skipped",
              "tier1": [], "tier2": [], "byte_acct": 0.0, "tier3": []}
    if not (binary.exists() and decoded.exists() and translation.exists()):
        return result

    data = binary.read_bytes()
    decoded_offsets = parse_decoded_offsets(decoded)
    invalid_offsets = load_invalid_offsets(stage)
    translations = parse_translation_file(translation)

    result["status"] = "ok"
    result["tier1"] = tier1_untranslated(translations)
    result["tier2"] = tier2_decoder_rejects(
        data, decode_table, decoded_offsets, invalid_offsets)
    result["byte_acct"], result["tier3"] = byte_accountability(
        data, decode_table, decoded_offsets, invalid_offsets)
    return result


def write_report(result: dict):
    """Write a per-stage coverage report; returns the path (or None if skipped)."""
    if result["status"] == "skipped":
        return None
    COVERAGE_DIR.mkdir(parents=True, exist_ok=True)
    path = COVERAGE_DIR / f"{result['stage']}_coverage.txt"
    lines = [
        f"# {result['stage']} coverage report",
        f"# byte accountability: {result['byte_acct']:.4f}",
        f"# absence of findings is not proof of completeness; see Tier 3 below",
        "",
        f"## Tier 1 — decoded-but-untranslated ({len(result['tier1'])})",
    ]
    for off, text in result["tier1"]:
        lines.append(f"  0x{off:08X} {text}")
    lines.append("")
    lines.append(f"## Tier 2 — decoder-reject (missing) ({len(result['tier2'])})")
    for off, text in result["tier2"]:
        lines.append(f"  0x{off:08X} {text}")
    lines.append("")
    lines.append(f"## Tier 3 — review candidates ({len(result['tier3'])})")
    for off, text, score in result["tier3"]:
        lines.append(f"  0x{off:08X} [score {score}] {text}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(stages: list) -> int:
    """Check the given stages; write reports; print summary; return exit code."""
    table = dt.build_decode_table()
    rows = []
    any_findings = False
    for stage in stages:
        result = check_stage(stage, table)
        write_report(result)
        t1, t2 = len(result["tier1"]), len(result["tier2"])
        if t1 or t2:
            any_findings = True
        rows.append((stage, result["status"], t1, t2,
                     result["byte_acct"], len(result["tier3"])))

    print(f"{'Stage':<7}{'Status':<9}{'T1':>5}{'T2':>5}{'ByteAcct':>10}{'T3':>7}")
    tot1 = tot2 = tot3 = 0
    for stage, status, t1, t2, acct, t3 in rows:
        flag = " LOW-COVERAGE" if status == "ok" and acct < 0.95 else ""
        acct_s = f"{acct:.3f}" if status == "ok" else "-"
        print(f"{stage:<7}{status:<9}{t1:>5}{t2:>5}{acct_s:>10}{t3:>7}{flag}")
        tot1 += t1; tot2 += t2; tot3 += t3
    print(f"{'TOTAL':<7}{'':<9}{tot1:>5}{tot2:>5}{'':>10}{tot3:>7}")
    print("\nNote: exit 0 means no Tier 1/2 findings; it does NOT assert "
          "completeness. Review Tier 3 and LOW-COVERAGE stages.")
    return 1 if any_findings else 0


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    stages = [a.upper() for a in argv] if argv else STAGES
    return run(stages)


if __name__ == "__main__":
    sys.exit(main())
