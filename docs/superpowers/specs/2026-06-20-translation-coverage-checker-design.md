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

**Ground-truth principle — and its hard limit.** The dialogue we have already found
and translated is a corpus of *known-real* offsets (call it **K**). K is the set of
**survivors** — dialogue that made it through the decoder. This makes K useless as a
denominator for measuring *misses*: a missed line is, by definition, not in K, so
any `recall = |R ∩ K| / |K|` measures only "do we re-find what we already found."
It can read 1.0 while real missed dialogue sits entirely outside the measurement.
**K must not be used as a completeness or trust signal.** (Earlier drafts did this;
it was circular.)

To detect the failure class, a metric's **denominator must be able to contain
misses**. K cannot; these two can, so they replace recall as the trust signals:

1. **Reference coverage.** Build **R** structurally — every offset the binary's own
   pointer structures dereference (`_find_templates`, scanner refs, discovered
   rules). A pointer exists in R whether or not its target ever decoded, so a
   *referenced-but-undecoded* target is visible: it lowers `referenced targets
   resolved / |R|` and becomes a Tier-2 finding. Bounded only by which pointer
   *mechanisms* we model — a narrower, more honest claim than "all dialogue."
2. **Text-region byte accountability.** In each chunk's text region, classify every
   non-zero byte run as decoded-dialogue, known-garbage/code (`is_garbage`),
   invalid-report, or **unaccounted**. Unaccounted runs that decode to Japanese are
   miss candidates — visible regardless of K. Report `accounted bytes / total
   text-region string bytes` per stage.

   *Caveat:* a run that `is_garbage` wrongly rejects (a false negative — exactly the
   S200 cause) is classed as known-garbage and thus counts as *accounted*, hiding
   it. So byte accountability shares `is_garbage`'s false-negative blind spot. The
   metrics therefore see a miss **unless** it is *both* reached only by an un-modeled
   mechanism *and* mis-classified as garbage. That intersection is the true
   irreducible static blind spot, closable only by reference-rule discovery (removes
   the first condition), filter improvement (removes the second), or in-game
   verification. To shrink it, Tier 3 additionally lists `is_garbage`-rejected runs
   that are *referenced* by R — the precise S200 signature — even though they are
   "accounted."

**K's only legitimate use is rule *precision*, not completeness.** In
reference-rule discovery, K (split train/held-out) checks that a candidate rule
points at real dialogue and generalizes — see "Reference-rule discovery."

**Irreducible blind spot.** Pointer mechanisms we have not modeled cannot be
measured statically — neither reference coverage nor K can see them; only byte
accountability (noisily) and in-game observation can. Therefore **exit 0 never
asserts completeness.** It asserts: no Tier-1 findings, no Tier-2 findings among
modeled references, at the reported reference-coverage and byte-accountability
figures. Closing the residual gap requires dynamic (in-game) verification, which is
out of scope for this static tool.

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

### Tier 2 — VALIDATED REFERENCE (gate on findings, bounded by modeled mechanisms)

- **Referenced-but-missing.** Build the reference set **R** structurally from
  `_find_templates`, the bare/orphan/event scanners, and any rules accepted by
  reference-rule discovery. For each referenced target: decode it; if it contains
  Japanese, is **absent from the decoded output**, and is **not in the invalid
  report**, report it. A real pointer aiming at a filtered-out Japanese string is
  strong evidence of genuine missed dialogue.
- This tier is **not exact** — its completeness is bounded by which pointer
  *mechanisms* R models. That bound is made visible by **reference coverage**
  (`referenced targets resolved / |R|`), which — unlike recall over K — *can* see a
  miss, because a referenced-but-undecoded target is in the denominator yet unresolved.
  A finding here is high-confidence; the *absence* of findings means "complete among
  modeled references," never "complete."

  *Implementation note:* `_find_templates` is directly reusable. The bare/orphan/
  event scanning currently lives inline in `decode_text.py`'s main path; reusing it
  may require light refactoring to expose those routines as callable functions. A
  reference type whose *mechanism* we have not modeled is the irreducible blind spot:
  it is not counted by reference coverage, so it is **not** claimed as covered — its
  targets remain visible only via Tier-3 byte accountability, and discovering its
  rule is the job of reference-rule discovery.

### Reference-rule discovery (grows R using K as ground truth)

Implements the user's insight — leverage found dialogue to validate new template
rules:

1. **Hypothesize.** For each known-real offset in K not already explained by R,
   look backward/around for recurring byte structures that could be a pointer to it
   (e.g., a little-endian offset field at a fixed stride, a record header preceding
   the pointer). Cluster these into candidate rules (structure + pointer-field
   location/encoding).
2. **Validate against held-out K.** Split K into a discovery half and a held-out
   half. Derive the rule on the discovery half, then measure precision on the
   *held-out* half = fraction of the rule's targets that are known-real (in held-out
   K or decode to clean, non-`is_garbage` dialogue) vs. that hit garbage. Held-out
   validation prevents a rule from being "confirmed" by the very offsets that
   produced it. Accept only above a precision threshold (e.g., ≥ 0.9) and a minimum
   support count, so a rule can't be accepted on a coincidence.
3. **Apply.** Accepted rules join R; their targets that are Japanese-and-not-decoded
   become Tier-2 findings. Accepted rules are reported (structure + held-out
   precision + support) so they can later be promoted into `decode_text.py` proper.

This is the mechanism that *shrinks* the irreducible blind spot over time — it
converts un-modeled mechanisms into modeled ones (raising reference coverage),
rather than leaving them as silent gaps. Note this uses K only for rule *precision*,
never as a completeness oracle.

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
      minus invalid). Used only for rule-discovery precision, not completeness.
   e. Build R = `_find_templates` ∪ scanner refs ∪ discovered-rule refs.
   f. Compute **reference coverage** = referenced targets resolved / |R|.
   g. Tier 1: translation entries with residual kana.
   h. Tier 2: referenced targets (in R) not decoded ∧ Japanese ∧ not invalid.
   i. Tier 3: exhaustive scan, garbage-filtered, ranked; compute **byte
      accountability** = accounted text-region string bytes / total.
3. Write per-stage report; accumulate summary counts.
4. Print summary table (including the two coverage figures).

## Output

- Per-stage report → `output/coverage/{stg}_coverage.txt` (gitignored,
  regenerated). Sections: Tier 1 / Tier 2 / discovered rules / Tier 3, with the
  stage's reference coverage and byte accountability at the top.
- Summary table to stdout across all 19 stages:
  `Stage | Untranslated(T1) | Missing(T2) | RefCov | ByteAcct | Review(T3)` + total
  row. (RefCov and ByteAcct are the miss-visible coverage figures; there is no
  recall-over-K column — it was removed as circular.)
- **Exit code:** non-zero iff any Tier 1 or Tier 2 finding exists. Tier 3 never
  affects exit code. **Exit 0 does not assert completeness** — it asserts "no Tier-1
  findings and no Tier-2 findings among modeled references." The summary always
  prints reference coverage, byte accountability, and the Tier-3 count so a 0 can
  never be read as "nothing missing." If reference coverage or byte accountability
  for any stage is below a configurable floor (defaults 0.98 / 0.95), the summary
  flags that stage as LOW-COVERAGE even when Tier 1/2 are clean, signalling the
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
- **Miss-visibility sanity**: a stage with known-missed dialogue (S200) must lower
  reference coverage and/or byte accountability — proving the metrics can see a miss.
  Critically, confirm that injecting a known miss does **not** leave recall-over-K
  at 1.0 silently (the circular-metric regression this revision fixes).
- **Rule discovery**: feed a rule that is known to point at K and confirm it is
  accepted (precision ≥ threshold); feed a coincidental pattern and confirm it is
  rejected (below support/precision).
- Confirm the `0x003ABC02` garbage entry (now in the invalid report) does **not**
  appear in Tier 2 (proves invalid-report exclusion works).

## Open questions

None at design time. Gate-integration into `patch_workflow.py` is deferred to a
later iteration by explicit choice. The rule-precision threshold (≈0.9), reference-
coverage floor (≈0.98), and byte-accountability floor (≈0.95) are starting defaults
to be tuned against real data during implementation.
