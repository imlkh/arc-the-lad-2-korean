# Translation Coverage Checker — Design

**Date:** 2026-06-20
**Status:** Approved (pending spec review)

## Problem

Some in-game dialogue is untranslated (observed in S200, likely present in other
stages). Two structurally different gaps cause this:

1. **Decoded-but-untranslated** — an entry exists in `translated/ko/{stg}_STG.txt`
   but its text still holds Japanese. A scan of `translated/ko/*.txt` already
   shows ~265 such entries across 14 stages (S300–SI00); S200 has 0.
2. **Decoder-missed ("missing") dialogue** — Japanese strings exist in the `.STG`
   binary but the decoder's region/opcode filters never extracted them, so no
   entry exists to translate. This is S200's symptom (translation file is clean,
   yet in-game text is Japanese). The project has already manually patched 31
   such entries, confirming the category is real.

A naive "scan the binary for Japanese and diff against decoded output" produces
~22,800 candidates in S200 alone — almost all MIPS code/data decoded as text
(e.g., `あギめけ2`, `オゼオゼヲ`). The decoder's ~20 garbage-filter rules exist
precisely because of this. Certainty about "no missing dialogue" can only come
from the **pointer side** (what the game actually references/renders), not from
scanning text bytes.

## Goal

A checker that reports, per stage and across all 19 stages, where translation is
incomplete — split into a high-confidence (gate-worthy) layer and an advisory
review layer.

## Non-goals

- Proving 100% completeness by text scanning alone (impossible — see above).
- Auto-translating or auto-fixing gaps. This tool only **reports**.
- Modeling every byte of the binary. Layer 2 is the safety net for un-modeled
  references.

## Approach: Hybrid (chosen over broad-heuristic-only and pointer-only)

Reuse existing code; do not reinvent filters:
- `python/decode/decode_text.py`: `build_decode_table`, `decode_string`,
  `is_garbage`, `_find_templates`, and region constants
  (`STG_CHUNK_SIZE`, `STG_TEXT_REGION_OFFSET/SIZE`,
  `STG_EVENT_SCRIPT_OFFSET/SIZE`, `STG_PADDING_OFFSET/SIZE`).
- `python/decode/generate_invalid_reports.py`: invalid-offset loading (to exclude
  known-invalid / garbage / debug entries).

## Components

### `python/tools/check_translation_coverage.py`

Invocation:
```
python python/tools/check_translation_coverage.py          # all 19 stages
python python/tools/check_translation_coverage.py S200     # one stage
```

Inputs per stage:
- Original binary: `<GAME_DIR>/{stg}.STG`
- Decoded output: `output/decoded/stg/{stg}_STG.txt`
- Translation file: `translated/ko/{stg}_STG.txt`
- Invalid report offsets: via `generate_invalid_reports.py` logic /
  `output/decoded/stg/{stg}_STG_invalid_report.txt`

### Layer 1 — EXACT (gate-worthy)

- **1a. Decoded-but-untranslated.** Parse the translation file; flag entries whose
  text contains Japanese kana in ranges U+3041–U+3096 (hiragana) and
  U+30A1–U+30FA plus U+30FC (katakana). These ranges are chosen to **exclude**,
  by construction, the intentional middle dot `・` (U+30FB, the gap between
  U+30FA and U+30FC) and the punctuation chars `「」、。…` (U+300C/U+300D/
  U+3001/U+3002/U+2026), all of which lie outside the kana ranges. Report
  `offset [opcode] text`.
- **1b. Referenced-but-missing.** Collect every offset the game references via
  `_find_templates` plus the bare/orphan/event scanners. For each referenced
  target: decode it; if it contains Japanese, is **absent from the decoded
  output**, and is **not in the invalid report**, report it. A real pointer
  aiming at a filtered-out Japanese string is strong evidence of genuine missed
  dialogue.

  *Implementation note:* `_find_templates` is directly reusable. The bare/orphan/
  event scanning currently lives inline in `decode_text.py`'s main path; reusing
  it may require light refactoring to expose those routines as callable functions.
  If a reference type proves hard to factor out cleanly, it falls back to Layer 2
  coverage rather than blocking this layer.

### Layer 2 — REVIEW (advisory)

- Exhaustively scan the text and event-script regions; decode each candidate
  string; drop those `is_garbage` rejects; diff against decoded offsets. Rank
  remaining candidates by confidence: Japanese-char count + presence of grammar
  particles (は/が/を/に/の/…) + valid `[script:..]` prefix. Output ranked list.

## Data flow

1. Load decode table once.
2. For each stage:
   a. Parse decoded file → `{offset: text}` and offset set.
   b. Parse translation file → `{offset: korean}`.
   c. Load invalid offsets.
   d. Layer 1a: translation entries with residual Japanese.
   e. Layer 1b: referenced targets not decoded ∧ Japanese ∧ not invalid.
   f. Layer 2: exhaustive scan, garbage-filtered, ranked.
3. Write per-stage report; accumulate summary counts.
4. Print summary table.

## Output

- Per-stage report → `output/coverage/{stg}_coverage.txt` (gitignored,
  regenerated). Three sections: 1a / 1b / 2.
- Summary table to stdout across all 19 stages:
  `Stage | Untranslated | Missing(exact) | Candidates(review)` + total row.
- Exit code non-zero iff any Layer 1 (1a or 1b) gaps exist. Layer 2 never affects
  exit code. Enables later wiring into `patch_workflow.py` validation as a gate
  (out of scope for this iteration).

## Error handling

- Missing decoded file, translation file, or binary for a stage → print a warning,
  mark the stage `SKIPPED` in the summary, continue with other stages. Never crash
  the whole run because one stage is absent (e.g., SJ00 has 0 dialogues).
- Use `Path(__file__).resolve().parents[2]` for all paths (project convention; no
  hardcoded absolute paths).

## Testing / validation

- **S200**: Layer 1b should surface decoder-missed lines (the observed symptom).
- **S700 / SI00**: Layer 1a should surface the 43 / 100 residual-Japanese entries.
- **S100**: a well-translated stage should report 0 in Layer 1 (sanity / low false
  positives).
- Confirm the `0x003ABC02` garbage entry (now in the invalid report) does **not**
  appear in Layer 1b (proves invalid-report exclusion works).

## Open questions

None at design time. Gate-integration into `patch_workflow.py` is deferred to a
later iteration by explicit choice.
