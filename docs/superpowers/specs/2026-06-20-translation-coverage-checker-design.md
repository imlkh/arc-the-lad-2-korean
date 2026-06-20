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
- Modeling every byte of the binary. Tier 3 is the safety net for un-modeled
  references.

## Approach: Hybrid, ground-truth-validated (chosen over broad-heuristic-only and pointer-only)

Reuse existing code; do not reinvent filters:
- `python/decode/decode_text.py`: `build_decode_table`, `decode_string`,
  `is_garbage`, `_find_templates`, and region constants
  (`STG_CHUNK_SIZE`, `STG_TEXT_REGION_OFFSET/SIZE`,
  `STG_EVENT_SCRIPT_OFFSET/SIZE`, `STG_PADDING_OFFSET/SIZE`).
- `python/decode/generate_invalid_reports.py`: invalid-offset loading (to exclude
  known-invalid / garbage / debug entries).

**Ground-truth principle (core to honesty).** The set of dialogue we have already
found and translated is a high-quality corpus of *known-real* dialogue offsets
(call it **K**). K is used two ways:

1. **Measure the blind spot.** Whatever reference set **R** we can enumerate (from
   `_find_templates` + scanners + any discovered rules), we compute
   `recall = |R ∩ K| / |K|` — the fraction of known dialogue our references
   rediscover. This number *quantifies* how much a clean result can be trusted and
   is printed with every run. It is the antidote to silent over-claiming.
2. **Discover and validate new reference rules.** A hypothesized template/pointer
   rule is accepted only if, applied to the binary, its targets land on K with high
   precision (mostly known-real dialogue, rarely garbage). Validated rules expand R
   toward K, shrinking the blind spot. See "Reference-rule discovery" below.

**Exit 0 is explicitly NOT a proof of completeness.** It means "no findings in the
definite and validated-reference checks, at the measured recall." The run always
reports recall and the Tier-3 review count so a clean gate can never be mistaken
for "no missing dialogue exists."

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

Findings are grouped by **confidence tier**, not by a misleading "exact" label.
The exit code reflects only what each tier can actually guarantee (see Output).

### Tier 1 — DEFINITE (always gate)

- **Decoded-but-untranslated.** Parse the translation file; flag entries whose text
  contains Japanese kana in ranges U+3041–U+3096 (hiragana) and U+30A1–U+30FA plus
  U+30FC (katakana). These ranges **exclude**, by construction, the intentional
  middle dot `・` (U+30FB, the gap between U+30FA and U+30FC) and the punctuation
  chars `「」、。…` (U+300C/U+300D/U+3001/U+3002/U+2026), all of which lie outside
  the kana ranges. A translation entry containing kana is *unambiguously*
  untranslated — zero false positives. Report `offset [opcode] text`.

### Tier 2 — VALIDATED REFERENCE (gate, bounded by recall)

- **Referenced-but-missing.** Build the reference set **R** from `_find_templates`,
  the bare/orphan/event scanners, and any rules accepted by reference-rule
  discovery. For each referenced target: decode it; if it contains Japanese, is
  **absent from the decoded output**, and is **not in the invalid report**, report
  it. A validated pointer aiming at a filtered-out Japanese string is strong
  evidence of genuine missed dialogue.
- This tier is **not exact** — its completeness is bounded by R. That bound is made
  visible by the `recall = |R ∩ K| / |K|` metric printed every run. A finding here
  is high-confidence; the *absence* of findings only means "complete among modeled
  references," which is why recall is always reported alongside.

  *Implementation note:* `_find_templates` is directly reusable. The bare/orphan/
  event scanning currently lives inline in `decode_text.py`'s main path; reusing it
  may require light refactoring to expose those routines as callable functions. Any
  reference type not modeled is **not** silently dropped: it shows up as reduced
  recall and its targets remain visible in Tier 3.

### Reference-rule discovery (grows R using K as ground truth)

Implements the user's insight — leverage found dialogue to validate new template
rules:

1. **Hypothesize.** For each known-real offset in K not already explained by R,
   look backward/around for recurring byte structures that could be a pointer to it
   (e.g., a little-endian offset field at a fixed stride, a record header preceding
   the pointer). Cluster these into candidate rules (structure + pointer-field
   location/encoding).
2. **Validate against K.** Apply each candidate rule across the binary; compute its
   precision = fraction of its targets that are in K (or decode to clean dialogue)
   vs. that hit garbage/`is_garbage`. Accept a rule only above a precision threshold
   (e.g., ≥ 0.9) and a minimum support count, so a rule can't be accepted on a
   coincidence.
3. **Apply.** Accepted rules join R; their targets that are Japanese-and-not-decoded
   become Tier-2 findings. Accepted rules are reported (structure + precision +
   support) so they can later be promoted into `decode_text.py` proper.

This is the mechanism that *shrinks* the Tier-2 blind spot over time and raises
recall, rather than leaving un-modeled references as silent gaps.

### Tier 3 — REVIEW (advisory, never gates)

- Exhaustively scan the text and event-script regions; decode each candidate
  string; drop `is_garbage` rejects; diff against decoded offsets. Rank remaining
  candidates by confidence: Japanese-char count + presence of grammar particles
  (は/が/を/に/の/…) + valid `[script:..]` prefix. This is the catch-all for
  references R does not yet model and the raw material for the next round of rule
  discovery. Always reported; never affects exit code.

## Data flow

1. Load decode table once.
2. For each stage:
   a. Parse decoded file → `{offset: text}` and offset set.
   b. Parse translation file → `{offset: korean}`.
   c. Load invalid offsets.
   d. Build K = known-real dialogue offsets (decoded ∧ has a non-kana translation,
      minus invalid).
   e. Build R = `_find_templates` ∪ scanner refs ∪ discovered-rule refs.
   f. Compute `recall = |R ∩ K| / |K|`.
   g. Tier 1: translation entries with residual kana.
   h. Tier 2: referenced targets (in R) not decoded ∧ Japanese ∧ not invalid.
   i. Tier 3: exhaustive scan, garbage-filtered, ranked.
3. Write per-stage report; accumulate summary counts.
4. Print summary table (including recall).

## Output

- Per-stage report → `output/coverage/{stg}_coverage.txt` (gitignored,
  regenerated). Sections: Tier 1 / Tier 2 / discovered rules / Tier 3, with the
  stage's recall at the top.
- Summary table to stdout across all 19 stages:
  `Stage | Untranslated(T1) | Missing(T2) | Recall | Review(T3)` + total row.
- **Exit code:** non-zero iff any Tier 1 or Tier 2 finding exists. Tier 3 never
  affects exit code. **Exit 0 does not assert completeness** — it asserts "no
  definite or validated-reference gaps at the reported recall." The summary always
  prints recall and the Tier-3 count so a 0 cannot be read as "nothing missing."
  If recall for any stage is below a configurable floor (default 0.95), the summary
  flags that stage as LOW-RECALL even when Tier 1/2 are clean, signalling the
  result is not trustworthy there. Enables later wiring into `patch_workflow.py`
  validation as a gate (deferred).

## Error handling

- Missing decoded file, translation file, or binary for a stage → print a warning,
  mark the stage `SKIPPED` in the summary, continue with other stages. Never crash
  the whole run because one stage is absent (e.g., SJ00 has 0 dialogues).
- Use `Path(__file__).resolve().parents[2]` for all paths (project convention; no
  hardcoded absolute paths).

## Testing / validation

- **S200**: Tier 2 (or a discovered rule) should surface the decoder-missed lines
  (the observed symptom).
- **S700 / SI00**: Tier 1 should surface the 43 / 100 residual-kana entries.
- **S100**: a well-translated stage should report 0 in Tier 1/2 (sanity / low false
  positives).
- **Recall sanity**: print recall per stage; a stage with known-missed dialogue
  (S200) and no discovered rule should show recall < 1.0, proving the blind-spot
  metric is live rather than cosmetically 100%.
- **Rule discovery**: feed a rule that is known to point at K and confirm it is
  accepted (precision ≥ threshold); feed a coincidental pattern and confirm it is
  rejected (below support/precision).
- Confirm the `0x003ABC02` garbage entry (now in the invalid report) does **not**
  appear in Tier 2 (proves invalid-report exclusion works).

## Open questions

None at design time. Gate-integration into `patch_workflow.py` is deferred to a
later iteration by explicit choice. The precision threshold (≈0.9) and recall
floor (≈0.95) are starting defaults to be tuned against real data during
implementation.
