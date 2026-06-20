# Translation Coverage Checker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a static checker that reports untranslated and decoder-missed dialogue across all 19 STG stages, in honest confidence tiers, without ever claiming false completeness.

**Architecture:** A single standalone tool, `python/tools/check_translation_coverage.py`, that reuses `python/decode/decode_text.py` (scan-based decoder) rather than reinventing filters. Three tiers — Tier 1 DEFINITE (translation entries with residual kana), Tier 2 DECODER-REJECT (candidates `scan_stg` discards, found by toggling its `filter_garbage` flag), Tier 3 REVIEW (advisory) — plus a text-region byte-accountability metric. Per-stage reports + a stdout summary; exit non-zero on any Tier 1/2 finding.

**Tech Stack:** Python 3.10 (stdlib only). Tests use stdlib `unittest` (no pytest in this repo). Reuses `decode_text.py` functions.

## Global Constraints

- Python 3.10, standard library only. No new third-party dependencies.
- No hardcoded absolute paths — use `Path(__file__).resolve().parents[2]` for the repo root (project convention).
- Reuse `decode_text.py`; do not duplicate decode/garbage logic. Available functions: `build_decode_table()`, `decode_string(data, offset, decode_table, prefix=0) -> (text, consumed)`, `_is_garbage_text(text) -> bool`, `_find_templates(data) -> [(off, opcode, ptr_a, ptr_b, ptr_c)]`, `_get_chunk_text_regions(file_size) -> [(start, end, chunk_idx)]`, `scan_stg(data, decode_table, use_heuristics=True, filter_garbage=True) -> (dialogues, templates, stats)` where `dialogues = [(offset, consumed, text, context_opcode), ...]`.
- Japanese-kana detection uses ranges U+3041–U+3096 (hiragana) and U+30A1–U+30FA plus U+30FC (katakana). These exclude, by construction, `・` (U+30FB) and `「」、。…`.
- `output/` is gitignored; coverage reports write to `output/coverage/`. The tool itself and its tests are tracked.
- 19 stages: S100, S200, S300, S400, S500, S600, S700, S800, S900, SA00, SB00, SC00, SD00, SE00, SF00, SG00, SH00, SI00, SJ00.
- Exit 0 never asserts completeness (spec). Reports always show byte accountability + Tier-3 count.
- Scan-rule discovery (spec section) is OUT OF SCOPE for this plan — deferred to a phase-2 plan.

**Paths:**
- Original binaries: `<repo>/../{stg}.STG` (game files live in the parent dir of the repo, e.g. `/Users/kyounghun/workspace/ps1_game_translation/Arc_The_Lad2/{stg}.STG`). Resolve via `GAME_DIR = Path(__file__).resolve().parents[3]`.
- Decoded: `<repo>/output/decoded/stg/{stg}_STG.txt`
- Invalid report: `<repo>/output/decoded/stg/{stg}_STG_invalid_report.txt`
- Translation: `<repo>/translated/ko/{stg}_STG.txt`

---

## File Structure

- `python/tools/check_translation_coverage.py` — the tool. Sections: path constants + decoder import; small pure helpers (kana detection, parsers); tier functions; `check_stage`; report writer; `main`.
- `python/tools/test_check_translation_coverage.py` — unittest suite (pure-function unit tests + synthetic-buffer tier tests + one real-data integration test).

Both files are created by this plan. No existing files are modified.

---

### Task 1: Scaffolding, decoder import, and kana detection

**Files:**
- Create: `python/tools/check_translation_coverage.py`
- Test: `python/tools/test_check_translation_coverage.py`

**Interfaces:**
- Produces: `contains_japanese(text: str) -> bool`; module-level `REPO_ROOT`, `GAME_DIR`, `DECODED_DIR`, `TRANS_DIR`, `COVERAGE_DIR`, `STAGES` (list[str]); imported decoder module accessible as `dt`.

- [ ] **Step 1: Write the failing test**

```python
# python/tools/test_check_translation_coverage.py
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_translation_coverage as cov


class TestContainsJapanese(unittest.TestCase):
    def test_hiragana_detected(self):
        self.assertTrue(cov.contains_japanese("おはよう"))

    def test_katakana_detected(self):
        self.assertTrue(cov.contains_japanese("ベンチ"))

    def test_korean_only_not_detected(self):
        self.assertFalse(cov.contains_japanese("안녕하세요"))

    def test_middle_dot_not_detected(self):
        # ・ (U+30FB) is intentional punctuation, not untranslated kana
        self.assertFalse(cov.contains_japanese("그렇군・・・"))

    def test_jp_punctuation_not_detected(self):
        self.assertFalse(cov.contains_japanese("「안녕」、반가워。…"))

    def test_mixed_flags_true(self):
        self.assertTrue(cov.contains_japanese("베조아、みつかった"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest python.tools.test_check_translation_coverage -v` (from repo root) — or `cd python/tools && python -m unittest test_check_translation_coverage -v`
Expected: FAIL with `ModuleNotFoundError`/`AttributeError: module 'check_translation_coverage' has no attribute 'contains_japanese'`.

- [ ] **Step 3: Write minimal implementation**

```python
# python/tools/check_translation_coverage.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python/tools && python -m unittest test_check_translation_coverage -v`
Expected: PASS (6 tests in TestContainsJapanese).

- [ ] **Step 5: Commit**

```bash
git add python/tools/check_translation_coverage.py python/tools/test_check_translation_coverage.py
git commit -m "feat(coverage): scaffolding + Japanese kana detection"
```

---

### Task 2: File parsers and invalid-offset loader

**Files:**
- Modify: `python/tools/check_translation_coverage.py`
- Test: `python/tools/test_check_translation_coverage.py`

**Interfaces:**
- Consumes: `REPO_ROOT`, `DECODED_DIR`, `TRANS_DIR` (Task 1).
- Produces: `parse_translation_file(path: Path) -> dict[int, str]` (offset → korean text, body after the `]` tag); `parse_decoded_offsets(path: Path) -> set[int]`; `load_invalid_offsets(stage: str) -> set[int]`.

Entry-line format (both decoded and translation files): `  0x003ABB32 [0x8005] [script:BB 36]기간한정`. The leading `0x...` is the offset; the visible text is everything after the final `]`. Non-entry lines (`#`, `---`, blank) are skipped.

- [ ] **Step 1: Write the failing test**

```python
# add to test file
import tempfile, os

class TestParsers(unittest.TestCase):
    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".txt")
        os.close(fd)
        Path(path).write_text(text, encoding="utf-8")
        return Path(path)

    def test_parse_translation_file(self):
        p = self._write(
            "# header\n"
            "  0x003ABB32 [0x8005] [script:BB 36]기간한정\n"
            "  --- context ---\n"
            "  0x003ABC02 [0x8005] [script:A9 00]베조아\n"
        )
        out = cov.parse_translation_file(p)
        self.assertEqual(out[0x003ABB32], "기간한정")
        self.assertEqual(out[0x003ABC02], "베조아")
        self.assertEqual(len(out), 2)

    def test_parse_decoded_offsets(self):
        p = self._write(
            "  0x000B4000 [0xFFFE] [script:01 02]text\n"
            "  0x000B4050 [0x8005] [script:03 04]more\n"
        )
        self.assertEqual(cov.parse_decoded_offsets(p), {0x000B4000, 0x000B4050})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python/tools && python -m unittest test_check_translation_coverage.TestParsers -v`
Expected: FAIL with `AttributeError: ... has no attribute 'parse_translation_file'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to check_translation_coverage.py
import re

_ENTRY_RE = re.compile(r"^\s*0x([0-9A-Fa-f]+)\s")


def _entry_offset(line: str):
    m = _ENTRY_RE.match(line)
    return int(m.group(1), 16) if m else None


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


def load_invalid_offsets(stage: str) -> set:
    """Offsets the decoder marked invalid (garbage/debug/single-char).

    Reads the generated invalid report; returns empty set if absent.
    """
    report = DECODED_DIR / f"{stage}_STG_invalid_report.txt"
    if not report.exists():
        return set()
    out = set()
    for line in report.read_text(encoding="utf-8").splitlines():
        off = _entry_offset(line.split("Line", 1)[-1] if "Line" in line else line)
        if off is not None:
            out.add(off)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python/tools && python -m unittest test_check_translation_coverage.TestParsers -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/tools/check_translation_coverage.py python/tools/test_check_translation_coverage.py
git commit -m "feat(coverage): translation/decoded/invalid file parsers"
```

---

### Task 3: Tier 1 — decoded-but-untranslated

**Files:**
- Modify: `python/tools/check_translation_coverage.py`
- Test: `python/tools/test_check_translation_coverage.py`

**Interfaces:**
- Consumes: `contains_japanese` (Task 1), `parse_translation_file` (Task 2).
- Produces: `tier1_untranslated(translations: dict) -> list[tuple[int, str]]` — sorted `(offset, text)` for entries whose text still contains kana.

- [ ] **Step 1: Write the failing test**

```python
class TestTier1(unittest.TestCase):
    def test_flags_only_kana_entries(self):
        translations = {
            0x10: "안녕하세요",        # translated
            0x20: "おはよう",          # untranslated hiragana
            0x30: "그렇군・・・",       # translated, middle dot OK
            0x40: "ベンチ",            # untranslated katakana
        }
        out = cov.tier1_untranslated(translations)
        self.assertEqual(out, [(0x20, "おはよう"), (0x40, "ベンチ")])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python/tools && python -m unittest test_check_translation_coverage.TestTier1 -v`
Expected: FAIL with `AttributeError: ... 'tier1_untranslated'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to check_translation_coverage.py
def tier1_untranslated(translations: dict) -> list:
    """Entries whose translated text still contains Japanese kana."""
    return sorted(
        (off, text) for off, text in translations.items()
        if contains_japanese(text)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python/tools && python -m unittest test_check_translation_coverage.TestTier1 -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/tools/check_translation_coverage.py python/tools/test_check_translation_coverage.py
git commit -m "feat(coverage): Tier 1 decoded-but-untranslated detection"
```

---

### Task 4: Tier 2 — decoder-reject capture

**Files:**
- Modify: `python/tools/check_translation_coverage.py`
- Test: `python/tools/test_check_translation_coverage.py`

**Interfaces:**
- Consumes: `dt.scan_stg`, `contains_japanese`.
- Produces: `tier2_decoder_rejects(data: bytes, decode_table, decoded_offsets: set, invalid_offsets: set) -> list[tuple[int, str]]` — sorted `(offset, text)` for candidates that the garbage filter discards but that decode to Japanese, are not already decoded, and are not invalid.

Mechanism: `scan_stg(..., filter_garbage=False)` returns all scanned candidates; `filter_garbage=True` returns the kept set. The set difference (by offset) is what the decoder rejected. Keep only Japanese, not-decoded, not-invalid ones.

- [ ] **Step 1: Write the failing test**

This is a unit test using a fake decoder injected via the module's `dt` reference, so it does not depend on real binaries.

```python
class TestTier2(unittest.TestCase):
    def setUp(self):
        self._real_scan = cov.dt.scan_stg

    def tearDown(self):
        cov.dt.scan_stg = self._real_scan

    def test_captures_rejected_japanese_only(self):
        # kept set: offset 0x10 ; full set: 0x10 + rejects 0x20(jp), 0x30(garbage ascii), 0x40(jp but invalid), 0x50(jp but already decoded)
        def fake_scan(data, table, use_heuristics=True, filter_garbage=True):
            kept = [(0x10, 4, "안녕", 0xFFFE)]
            full = kept + [
                (0x20, 6, "みつかった", 0x8005),   # real reject -> expect captured
                (0x30, 3, "Xab", 0x8005),          # not japanese -> excluded
                (0x40, 5, "ほげ", 0x8005),          # japanese but invalid offset
                (0x50, 5, "ふが", 0x8005),          # japanese but already decoded
            ]
            return (kept if filter_garbage else full), [], {}
        cov.dt.scan_stg = fake_scan

        out = cov.tier2_decoder_rejects(
            data=b"", decode_table={},
            decoded_offsets={0x50}, invalid_offsets={0x40},
        )
        self.assertEqual(out, [(0x20, "みつかった")])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python/tools && python -m unittest test_check_translation_coverage.TestTier2 -v`
Expected: FAIL with `AttributeError: ... 'tier2_decoder_rejects'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to check_translation_coverage.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python/tools && python -m unittest test_check_translation_coverage.TestTier2 -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/tools/check_translation_coverage.py python/tools/test_check_translation_coverage.py
git commit -m "feat(coverage): Tier 2 decoder-reject capture"
```

---

### Task 5: Byte accountability + Tier 3 review list

**Files:**
- Modify: `python/tools/check_translation_coverage.py`
- Test: `python/tools/test_check_translation_coverage.py`

**Interfaces:**
- Consumes: `dt.build_decode_table`, `dt.decode_string`, `dt._is_garbage_text`, `dt._get_chunk_text_regions`, `dt.STG_CHUNK_SIZE`, `dt.STG_TEXT_REGION_OFFSET`, `contains_japanese`.
- Produces: `byte_accountability(data, decode_table, decoded_offsets: set, invalid_offsets: set) -> tuple[float, list]` returning `(accounted_fraction, tier3_candidates)` where `tier3_candidates` is a list of `(offset, text, score)` sorted by descending score. Score = kana count + 2·(particle present) + 1·(valid decode). A run is "accounted" if its offset is decoded, invalid, or its text is `_is_garbage_text`. Unaccounted Japanese runs become Tier-3 candidates.

- [ ] **Step 1: Write the failing test**

Build a one-chunk synthetic buffer whose text region holds one decodable Japanese string at a known offset, padded to the chunk size, and assert the run is reported as unaccounted (Tier-3 candidate) and accountability < 1.0.

```python
class TestByteAccountability(unittest.TestCase):
    def test_unaccounted_japanese_run_detected(self):
        table = cov.dt.build_decode_table()
        # Pick three kana chars that round-trip through the table.
        inv = {v: k for k, v in table.items() if isinstance(k, int) and 1 <= k <= 0xEE}
        kana = [c for c in ("お", "は", "よ", "う", "み", "つ") if c in inv][:3]
        self.assertGreaterEqual(len(kana), 3, "need 3 single-byte kana in table")
        payload = bytes(inv[c] for c in kana) + b"\x00"

        chunk = cov.dt.STG_CHUNK_SIZE
        text_off = cov.dt.STG_TEXT_REGION_OFFSET
        data = bytearray(chunk)
        data[text_off:text_off + len(payload)] = payload

        frac, cands = cov.byte_accountability(
            bytes(data), table, decoded_offsets=set(), invalid_offsets=set())
        offs = [c[0] for c in cands]
        self.assertIn(text_off, offs)
        self.assertLess(frac, 1.0)

    def test_decoded_run_is_accounted(self):
        table = cov.dt.build_decode_table()
        inv = {v: k for k, v in table.items() if isinstance(k, int) and 1 <= k <= 0xEE}
        kana = [c for c in ("お", "は", "よ", "う", "み", "つ") if c in inv][:3]
        payload = bytes(inv[c] for c in kana) + b"\x00"
        chunk = cov.dt.STG_CHUNK_SIZE
        text_off = cov.dt.STG_TEXT_REGION_OFFSET
        data = bytearray(chunk)
        data[text_off:text_off + len(payload)] = payload
        # Mark that offset as already decoded -> must NOT be a Tier-3 candidate.
        _frac, cands = cov.byte_accountability(
            bytes(data), table, decoded_offsets={text_off}, invalid_offsets=set())
        self.assertNotIn(text_off, [c[0] for c in cands])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python/tools && python -m unittest test_check_translation_coverage.TestByteAccountability -v`
Expected: FAIL with `AttributeError: ... 'byte_accountability'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to check_translation_coverage.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python/tools && python -m unittest test_check_translation_coverage.TestByteAccountability -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/tools/check_translation_coverage.py python/tools/test_check_translation_coverage.py
git commit -m "feat(coverage): byte accountability + Tier 3 review list"
```

---

### Task 6: Per-stage orchestration and report writer

**Files:**
- Modify: `python/tools/check_translation_coverage.py`
- Test: `python/tools/test_check_translation_coverage.py`

**Interfaces:**
- Consumes: all tier functions, parsers, `GAME_DIR`, `DECODED_DIR`, `TRANS_DIR`, `COVERAGE_DIR`.
- Produces: `check_stage(stage: str, decode_table) -> dict` with keys `stage`, `status` (`"ok"` or `"skipped"`), `tier1` (list), `tier2` (list), `byte_acct` (float), `tier3` (list); `write_report(result: dict) -> Path|None` writing `output/coverage/{stage}_coverage.txt`.

`check_stage` returns `{"stage": stage, "status": "skipped", ...}` (empty lists, `byte_acct=0.0`) when the binary, decoded, or translation file is missing — never raises.

- [ ] **Step 1: Write the failing test**

```python
class TestCheckStage(unittest.TestCase):
    def test_missing_files_skipped(self):
        table = cov.dt.build_decode_table()
        result = cov.check_stage("ZZ99", table)  # nonexistent stage
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["tier1"], [])
        self.assertEqual(result["tier2"], [])

    def test_write_report_creates_file(self):
        result = {"stage": "TT00", "status": "ok",
                  "tier1": [(0x10, "おはよう")], "tier2": [(0x20, "みつかった")],
                  "byte_acct": 0.97, "tier3": [(0x30, "ほげ", 5)]}
        path = cov.write_report(result)
        self.assertTrue(path.exists())
        body = path.read_text(encoding="utf-8")
        self.assertIn("0x00000010", body)
        self.assertIn("byte accountability", body.lower())
        path.unlink()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python/tools && python -m unittest test_check_translation_coverage.TestCheckStage -v`
Expected: FAIL with `AttributeError: ... 'check_stage'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to check_translation_coverage.py
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
        f"# (exit 0 never asserts completeness; see Tier 3 below)",
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd python/tools && python -m unittest test_check_translation_coverage.TestCheckStage -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add python/tools/check_translation_coverage.py python/tools/test_check_translation_coverage.py
git commit -m "feat(coverage): per-stage orchestration + report writer"
```

---

### Task 7: CLI, summary table, exit code, and real-data integration test

**Files:**
- Modify: `python/tools/check_translation_coverage.py`
- Test: `python/tools/test_check_translation_coverage.py`

**Interfaces:**
- Consumes: `check_stage`, `write_report`, `STAGES`, `dt.build_decode_table`.
- Produces: `run(stages: list[str]) -> int` (returns process exit code: non-zero iff any Tier 1/2 finding); `main(argv=None) -> int`.

- [ ] **Step 1: Write the failing test (integration, gated on real files)**

```python
class TestIntegration(unittest.TestCase):
    def setUp(self):
        if not (cov.GAME_DIR / "S700.STG").exists() or \
           not (cov.TRANS_DIR / "S700_STG.txt").exists():
            self.skipTest("real S700 data not present")

    def test_s700_has_tier1_findings(self):
        table = cov.dt.build_decode_table()
        result = cov.check_stage("S700", table)
        self.assertEqual(result["status"], "ok")
        # spec: S700 has ~43 residual-kana entries (>0 is the assertion)
        self.assertGreater(len(result["tier1"]), 0)

    def test_run_nonzero_when_findings(self):
        # S700 has Tier-1 findings, so run() must return non-zero.
        code = cov.run(["S700"])
        self.assertNotEqual(code, 0)


class TestRunExitCode(unittest.TestCase):
    def test_clean_stage_exits_zero(self):
        # A skipped/clean stage list returns 0 (no findings).
        self.assertEqual(cov.run(["ZZ99"]), 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd python/tools && python -m unittest test_check_translation_coverage.TestRunExitCode -v`
Expected: FAIL with `AttributeError: ... 'run'`.

- [ ] **Step 3: Write minimal implementation**

```python
# add to check_translation_coverage.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd python/tools && python -m unittest test_check_translation_coverage -v`
Expected: PASS (integration tests run if S700 data present, else skipped).

- [ ] **Step 5: Run the real tool end-to-end**

Run: `cd <repo> && python python/tools/check_translation_coverage.py`
Expected: a summary table over 19 stages; S700/SI00 show Tier-1 counts; reports under `output/coverage/`. Spot-check `output/coverage/S200_coverage.txt` for any Tier-2 entries and confirm `0x003ABC02` is NOT listed (it is in the invalid report).

- [ ] **Step 6: Commit**

```bash
git add python/tools/check_translation_coverage.py python/tools/test_check_translation_coverage.py
git commit -m "feat(coverage): CLI, summary table, exit code + integration tests"
```

---

## Self-Review Notes

- **Spec coverage:** Tier 1 (Task 3), Tier 2 decoder-reject (Task 4), Tier 3 + byte accountability (Task 5), per-stage report + skip handling (Task 6), summary table + honest exit code + "exit 0 ≠ completeness" note + LOW-COVERAGE flag (Task 7). Kana ranges excluding ・/punctuation (Task 1). Invalid-report exclusion (Task 2, used in Tiers 2/3). Scan-rule discovery is explicitly deferred (Global Constraints) — separate phase-2 plan.
- **No recall-over-K and no RefCov** appear anywhere (removed as circular/infeasible per spec).
- **Type consistency:** `scan_stg` unpacked as `(dialogues, templates, stats)` with `dialogues` tuples `(offset, consumed, text, opcode)` (Task 4); `decode_string` returns `(text, consumed)` (Task 5); result dict keys identical across Tasks 6–7.

## Out of scope / follow-up

- **Scan-rule discovery** (spec section): a phase-2 plan — discover region/prefix locator rules from K with held-out validation, to raise byte accountability over time.
- **Gate integration** into `patch_workflow.py` validation.
