#!/usr/bin/env python3
"""Post-patch residual-Japanese scanner.

Finds displayable text the translation pipeline MISSED -- lines that still show
the original Japanese in the patched game (rendered as garbled Korean through the
remapped font, e.g. the SG00 やめろぉ -> "크장신디" bug).

Strategy
--------
For each STG file, compare the ORIGINAL game bytes against the PATCHED output and
report every ``A9 00`` text frame that is:

  1. byte-identical between original and patched   (the patcher never touched it),
  2. decodes (via the Japanese font table) to real Japanese, and
  3. is not MIPS-opcode / structural garbage.

The "byte-identical to original" test is the crucial discriminator: a translated
line always DIFFERS from the original (it is now Korean or a relocation jump), so
Korean text can never be misreported as a miss. This is why the scan is precise
where a content-only heuristic over-counts.

The acceptance filter reuses the decoder's own ``_is_garbage_text`` and
``_has_mips_opcode_signature`` (both of which already accept short pure-kana
exclamations like やめろぉ) but DROPS the over-strict "must contain kanji / menu /
punctuation" gate that made the extractor miss the line in the first place.

Usage
-----
    python scan_residual_japanese.py                # scan all STG stages
    python scan_residual_japanese.py SG00 S700      # scan specific stages
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "decode"))

from decode_text import (  # noqa: E402
    decode_string, _is_garbage_text, _has_mips_opcode_signature,
    _build_exclusion_zones, _overlaps_script,
    STG_CHUNK_SIZE, STG_PADDING_OFFSET,
)

BASE_DIR = os.path.abspath(os.path.join(HERE, "..", ".."))
GAME_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
PATCHED_DIR = os.path.join(BASE_DIR, "output", "patched")
JP_TABLE_PATH = os.path.join(BASE_DIR, "output", "font", "analysis",
                             "jp_char_positions.json")

A9_MARKER = b"\xA9\x00"

# A real Japanese SYLLABLE/kanji (hiragana, katakana letters, CJK) -- excludes
# language-neutral punctuation like ・ ー … 。 so "・・・" runs are not flagged.
_JP_RE = re.compile(r"[ぁ-ゖァ-ヺ一-鿿]")
_KANJI_RE = re.compile(r"[一-鿿]")
_PUNCT_RE = re.compile(r"[！？…。]")
_KATA_RE = re.compile(r"[ァ-ヺ]")   # katakana letters, excludes ・ ー
_HIRA_RE = re.compile(r"[ぁ-ゖ]")


def _confidence(stripped):
    """HIGH only for strong signals: kanji, JP sentence punctuation, or
    PREDOMINANTLY katakana (a real name/UI label).

    A single katakana char inside hiragana opcode soup (e.g. ギういきいて) is
    NOT enough -- that was the source of HIGH-bucket pollution.
    """
    if _KANJI_RE.search(stripped) or _PUNCT_RE.search(stripped):
        return "high"
    kata = len(_KATA_RE.findall(stripped))
    hira = len(_HIRA_RE.findall(stripped))
    if kata >= 2 and kata >= hira:
        return "high"
    return "low"


# Event-script/MIPS operands decode to these low-charID "connective" kana
# (せ そ た ち つ て と な = 0x0E..0x15). Real words rarely stack 3+ of them; the
# opcode "rhythm" (e.g. ...き な た く そ) does. Threshold tuned to keep real
# lines (やめろぉ, にせエルク, こっちこっちー) and drop the soup.
_CONNECTIVE_BYTES = frozenset(range(0x0E, 0x16))


def _is_opcode_rhythm(run_bytes):
    return sum(1 for b in run_bytes if b in _CONNECTIVE_BYTES) >= 3


def _is_mips_xa_lead(run_bytes):
    """The 2nd payload byte being 0x01 (あ) is the documented MIPS opcode
    signature 'X あ ...' (STORE/CALL/SET/COMPARE), e.g. めあわデじ / やあミデヅ.
    Real A9-frame text never starts its 2nd char with あ in this corpus.
    """
    return len(run_bytes) >= 2 and run_bytes[1] == 0x01


def load_jp_table():
    """charID -> original Japanese glyph (the game's text encoding)."""
    with open(JP_TABLE_PATH, encoding="utf-8") as f:
        return {x["char_id"]: x["char"] for x in json.load(f)}


def _strip_tags(text):
    out = text
    for tag in ("[box:system]", "[box:close]", "[box:speech]",
                "[box:narration]", "[cursor]", "[br]", "[opt]"):
        out = out.replace(tag, "")
    out = re.sub(r"\[script:.*?\]", "", out)
    out = re.sub(r"\[.*?\]", "", out)
    return out


def scan_data(orig, patched, jp_table, chunk_size=STG_CHUNK_SIZE,
              min_within=STG_PADDING_OFFSET):
    """Scan one STG file's bytes for missed (untranslated) A9 00 text frames.

    Args:
        orig: original game STG bytes.
        patched: patched STG bytes (same length as orig).
        jp_table: charID -> Japanese glyph mapping.
        chunk_size: STG chunk size; frames are scanned per chunk.
        min_within: only scan offsets at/after this within-chunk offset
            (default: the displayable padding/event/text tail at 0xA0000+).

    Returns:
        list of {offset, chunk, text, jp_bytes} dicts, one per missed frame.
    """
    if len(orig) != len(patched):
        raise ValueError(
            f"size mismatch: orig {len(orig)} != patched {len(patched)}")

    hits = []
    n = len(orig)
    num_chunks = max(1, n // chunk_size)
    for c in range(num_chunks):
        chunk_start = c * chunk_size
        chunk_end = min(chunk_start + chunk_size, n)
        region_start = chunk_start + min_within
        # Script-opcode / event-trigger / shared-code zones to exclude. These
        # cover the MIPS bytecode that decodes to plausible-looking kana soup.
        zones = _build_exclusion_zones(orig, region_start, chunk_end)
        pos = region_start
        while pos < chunk_end - 4:
            if orig[pos:pos + 2] != A9_MARKER:
                pos += 1
                continue

            text, consumed = decode_string(orig, pos + 2, jp_table, prefix=2)
            if not text or consumed <= 4:
                pos += 1
                continue

            frame = slice(pos, pos + 2 + consumed)
            # 1. untouched by the patcher?
            if orig[frame] != patched[frame]:
                pos += 1
                continue

            stripped = _strip_tags(text)
            text_start = pos + 4   # marker(2) + prefix(2)
            text_end = pos + 2 + consumed
            run_bytes = orig[text_start:text_end - 1]  # text bytes, drop null
            # 2. real Japanese?  3. not garbage / MIPS code / script zone /
            #    opcode-operand rhythm?
            if (len(stripped) >= 2
                    and _JP_RE.search(stripped)
                    and not _is_garbage_text(text)
                    and not _is_opcode_rhythm(run_bytes)
                    and not _is_mips_xa_lead(run_bytes)
                    and not _overlaps_script(text_start, text_end, zones)
                    and not _has_mips_opcode_signature(
                        orig, pos + 2, consumed, prefix=2)):
                hits.append({
                    "offset": pos,
                    "chunk": c,
                    "text": stripped,
                    "confidence": _confidence(stripped),
                    "jp_bytes": orig[pos + 4:pos + 2 + consumed].hex(" "),
                })
                pos = pos + 2 + consumed
                continue
            pos += 1
    return hits


def scan_file(stage, jp_table):
    """Scan one stage by name; returns (hits, message)."""
    orig_path = os.path.join(GAME_DIR, f"{stage}.STG")
    patched_path = os.path.join(PATCHED_DIR, f"{stage}.STG")
    if not os.path.exists(orig_path):
        return [], f"{stage}: original not found ({orig_path})"
    if not os.path.exists(patched_path):
        return [], f"{stage}: patched not found ({patched_path})"
    orig = open(orig_path, "rb").read()
    patched = open(patched_path, "rb").read()
    if len(orig) != len(patched):
        return [], (f"{stage}: size mismatch orig={len(orig)} "
                    f"patched={len(patched)} (skipped)")
    return scan_data(orig, patched, jp_table), None


ALL_STAGES = [
    "S100", "S200", "S300", "S400", "S500", "S600", "S700", "S800",
    "S900", "SA00", "SB00", "SC00", "SD00", "SE00", "SF00", "SG00",
    "SH00", "SI00", "SJ00",
]


def _report_bucket(stage, hits):
    """Print one stage's hits deduped by decoded text; return distinct count."""
    by_text = {}
    for h in hits:
        by_text.setdefault(h["text"], []).append(h)
    for text, group in sorted(by_text.items(), key=lambda kv: -len(kv[1])):
        g0 = group[0]
        extra = f"  (x{len(group)})" if len(group) > 1 else ""
        print(f"  {stage} 0x{g0['offset']:08X} chunk{g0['chunk']:>3}  "
              f"[{g0['jp_bytes']}]  {text!r}{extra}")
    return len(by_text)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("-")]
    show_low = "--all" in argv
    stages = [s.upper() for s in args] if args else ALL_STAGES

    jp_table = load_jp_table()
    high_total = low_total = 0
    high_by_stage = {}
    low_by_stage = {}
    for stage in stages:
        hits, msg = scan_file(stage, jp_table)
        if msg:
            print(msg)
            continue
        high_by_stage[stage] = [h for h in hits if h["confidence"] == "high"]
        low_by_stage[stage] = [h for h in hits if h["confidence"] == "low"]

    print("=" * 64)
    print("HIGH-CONFIDENCE missed text (kanji/katakana/punctuation)")
    print("These are byte-identical to the original game AND real Japanese")
    print("=> genuine untranslated lines to fix.")
    print("=" * 64)
    for stage in stages:
        hits = high_by_stage.get(stage, [])
        if hits:
            high_total += len(hits)
            _report_bucket(stage, hits)

    print("\n" + "=" * 64)
    print("LOW-CONFIDENCE (bare short hiragana): mix of real exclamations")
    print("(like やめろぉ) and MIPS-opcode noise -- needs human review.")
    print("Re-run with --all to list them.")
    print("=" * 64)
    for stage in stages:
        n = len(low_by_stage.get(stage, []))
        if n:
            low_total += n
            print(f"  {stage}: {n} candidate(s)")
            if show_low:
                _report_bucket(stage, low_by_stage[stage])

    print(f"\n=== HIGH-confidence misses: {high_total} | "
          f"LOW-confidence candidates: {low_total} ===")
    return 1 if high_total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
