# STG Decoder Fixes (decode_text.py)

## Overview

The STG dialogue decoder (`python/decode/decode_text.py`) extracts Japanese dialogue from
Arc the Lad 2's STG stage files. Because the decoder scans binary data that includes
MIPS machine code alongside text, it must distinguish real dialogue from garbage produced
by misinterpreted opcodes.

**Final stats** (2026-02-09): 26,775 dialogues across 20,947 templates in 19 STG files.
Category 1 garbage: **0**. Category 2 single-char fragments: **0**. Partial decodes: **0**.

## Remaining Items

### Missed Gaps: 76 total (down from 362) — all correctly missed

Template gaps where none of the 5 search strategies found dialogue.
Investigation (2026-02-09) confirmed **all 76 contain no translatable text**.

| Category | Count | What's in the gap |
|----------|-------|-------------------|
| Script opcodes only | 59 (77.6%) | `28 01` event script machine code, no text |
| Binary data | 9 (11.8%) | Empty placeholders, register operands, sentinels |
| Structural menus | 8 (10.5%) | Pure `[opt][br]` grids with zero visible text |

| File | Missed | Root cause |
|------|--------|-----------|
| SI00.STG | 62 | 57 script-only (trimmed to bare prefix) + 5 binary data |
| S900.STG | 8 | 3x3 menu grid templates — `[box:close][opt][opt][opt][br]...` with no text |
| S200.STG | 4 | 2 script opcodes + 2 MIPS register data |
| S100.STG | 2 | Empty dialogue placeholders (A9 00 markers with null text) |

65/76 gaps don't contain the expected prefix bytes at all — the template's
`ptr_a` points to script code, not dialogue. 11/76 have the prefix but
decoding correctly fails (empty payloads or single-char fragments).
The "missed" counter effectively counts "gaps with no dialogue" rather than
"dialogue we failed to find." Zero coverage loss.

### Debug / Developer Messages: 9 in S200

Real strings left by developers for internal testing, correctly classified
as Category 3 by `generate_invalid_reports.py`. Examples:

- `デバック用だよ` ("it's for debugging")
- `修正しましたので感想をください` ("we fixed it, please give feedback")
- `バグレポートだけでなく感想などもどんどん教えてほしいわ` ("send us impressions, not just bug reports")

These are decoded correctly but not player-facing. Excluded from translation.

## Garbage Filter Rules (`_is_garbage_text()`)

### Core Rules (1-6)

| Rule | What it catches | Example |
|------|----------------|---------|
| 1 | Unknown charID `[?XXXX]` beyond font table | `[?1A2B]けど` |
| 2 | Invalid FF control codes (not 01,03-0B,0D,0F) | `[FF:B2 0F 2F]` |
| 3 | Lowercase ASCII in Japanese text | `しaとbう` |
| 4 | Uppercase+kana without kanji (≤6: always; ≥7: ≥2 isolated uppercase; exempt rank patterns) | `ゾァびJダIゥゾ` |
| 5 | Short mixed hira/kata without repetition (len ≤ 4) | `みギづ` |
| 6 | Repeating 2-char pair at regular intervals (≥4 apart, ≥3 times, no punctuation) | `もあがデもあをデもあんデ` |
| 8 | Digit+kana mix in short text (≤8 chars, scattered digits = garbage, grouped digits = real) | `3ざよ`, `サデリく1` |
| 9 | Fullwidth `＊` in short text (≤5 chars) — data table marker | `どと＊`, `！と＊` |
| 10 | Starts with small kana `ぉ/ゅ/ょ` (≤8 chars, no kanji) — unusual word start | `ぉとす`, `ぉあさ` |
| 11 | Starts with fullwidth `。` (≤5 chars) — data reference marker | `。つし` |
| 12 | Ends with `もあ` (≤8 chars, no kanji) — MIPS opcode terminator | `ずぞもあ` |

### Rule 7: MIPS Opcode Detection (sub-rules 7a-7i)

#### Why MIPS opcodes appear as text

The STG chunk structure (0xBC800 = 772,096 bytes per chunk):

| Offset Range | Content |
|-------------|---------|
| 0x00000-0x70000 | Graphics |
| 0x77000-0x80000 | MIPS code (scene) |
| 0x80000-0xA0000 | MIPS code (main) |
| 0xA0000-0xB0000 | Padding (VLUT + Korean text) |
| 0xB0000-0xB4000 | Event scripts |
| 0xB4000-0xBC800 | Text region |

The decoder scans multiple regions to find dialogue, but some scanners
(bare, event script, gap search) can encounter MIPS instructions instead of text.
When decoded through the game's character table, MIPS byte patterns produce
characteristic Japanese text:

| Byte pattern | Decoded as | MIPS meaning |
|-------------|-----------|-------------|
| `XX 01` | "Xあ" | STORE, CALL, SET, COMPARE opcodes |
| `XX 8C` | "Xデ" | Memory reference operands (LW instruction) |
| `XX 80` | "Xギ" | Register operands |
| `0x46 XX` | "ぺX" | Coprocessor instruction (c.eq.s) |
| `0x24 XX` | "地X" | ADDIU instruction |

MIPS byte sequences also frequently produce kanji: 地, 水, 火, 風, 煙, 術, 関, 際, 鉛, 径.

#### Sub-rules

| Sub-rule | Pattern | Example | Count |
|----------|---------|---------|-------|
| **7a** | `もあ.{0,3}[デゲギグゼダヅヂゾ]` | もあをデタギもあんデ喚J | ~98 |
| **7b** | `もあ煙` anywhere in text | もあ煙デもあ煙デ | ~56 |
| **7c** | `煙煙` anywhere in text | 煙煙地デ煙煙 | ~15 |
| **7d** | High デ/ギ density (≥25%, 4-30 chars, no kanji exemption) | ぺデぴしデギ | ~23 |
| **7d2** | Wider MIPS density (デギグダズヌ水, ≥25%, 3-30 chars, with kanji exemption via MIPS_KANJI set) | タデりギ水ゲあギ | ~18 |
| **7e** | 2+ distinct predecessors of あ/デ/ギ markers (no kanji/punct) | めああグりあいああ | legacy |
| **7f** | 3-5 char all-katakana from MIPS character set (≥2 distinct chars) | グゼノ, クゼゼ, シゼニ | 16 |
| **7g** | Starts with ぺデ, ≤8 chars | ぺデデ, ぺデぴしダ | 6 |
| **7h** | Starts with 地 + all hiragana + ≥1 あ | 地えあきあつくと | 4 |
| **7i** | Pure hiragana 12+ chars, no grammatical structure | おつあきけなこたかそいちちて | 2 |

**MIPS_KATA character set** (Rule 7f): {ギ, デ, ゲ, グ, ゼ, ノ, ク, シ, ニ, ダ, ヅ, ヂ, ゾ, ジ, ッ, タ}
- ジ added to catch ジッグ, ジッゲ patterns found in S700 template scanning
- ッ and タ added for MIPS patterns like クゼゼ, タギデ
- Requires `len(set(stripped)) >= 2` — exempts all-same-char strings (e.g., ククク = villainous laugh)
- No real Japanese words are composed entirely of 2+ distinct characters from this set

**Grammar safeguard** (Rules 7d, 7i): Before flagging as garbage, checks for
Japanese grammar patterns to avoid false positives:
```
ます|です|ない|する|した|ている|てる|こと|もの|だろう|って|けど|から|まで|
なら|んだ|のか|のは|には|ので|やっぱ|おぬし|じゃの|かもしれ|みんな|もどる...
```
Plus onomatopoeia detection (repeated-half check, e.g., `ぴょこぴょこ`).

#### Rule 7 development history

| Phase | Date | Result |
|-------|------|--------|
| Original | 2026-02-07 | Rule 7 = predecessor check only, with kanji exemption that missed ~154 entries |
| Expansion | 2026-02-08 | Replaced kanji exemption with Rules 7a-7e. Category 1: 271 → 40 |
| Completion | 2026-02-08 | Added Rules 7f-7i + Rule 4 extension. Category 1: 40 → **0** |
| Post-filter | 2026-02-09 | Split 7d → 7d/7d2, expanded 7f (ッタ, distinct chars), lowered 7h threshold. Applied via post-filter |

## Region-Based Post-Filter (`scan_stg()`)

A structural filter applied before garbage text analysis rejects any dialogue
entry found in non-text regions of the STG chunk:

```python
chunk_offset = offset % STG_CHUNK_SIZE  # 0xBC800
if chunk_offset < 0xA0000:
    continue  # In graphics (0-0x70000) or MIPS code (0x77000-0xA0000)
```

This removed ~315 entries in a single pass — mostly MIPS code that was
misinterpreted as text by the gap search and bare dialogue scanners.

## Report Generator Fixes (generate_invalid_reports.py)

The report generator (`python/decode/generate_invalid_reports.py`) provides a
secondary classification layer on decoded output. 11 real dialogues were
initially misclassified as garbage:

| Text | Why it's real | Fix applied |
|------|--------------|-------------|
| `・・・・・・・・・` (×7 across files) | Silence/pause dialogue, common in RPGs | Pattern 6: exempt `・` from repeating check |
| `きっとそのうちみんなもとにもどるわ` | "I'm sure everyone will return to normal" | Pattern 10: added grammar patterns |
| `やれやれやっぱりおぬしはちょこじゃのう` | Archaic/elderly character speech about Choko | Pattern 10: added archaic patterns |
| `ばちがあたるかもしれんしのぉ` | Dialect: "We might get punished" | Pattern 10: added dialect patterns |
| `くるりんぴょこぴょこ[br]くるりんぴょこぴょこ` | Child NPC nursery rhyme | Pattern 10: onomatopoeia half-check |

## Dialogue Count Progression

| Stage | Total | Cat 1 | Cat 2 | Cat 4 | Change |
|-------|-------|-------|-------|-------|--------|
| Initial decode (baseline) | 27,211 | 271 | — | — | — |
| + Region filter + Rules 7a-7e | 26,896 | 40 | — | — | −315 dialogues, −231 garbage |
| + Rules 7f-7i + Rule 4 extension | 26,855 | **0** | 111 | 86 | −41 dialogues, −40 garbage |
| + Structural replay (partial decode) | 26,855 | 0 | 111 | 59 | −27 partial decodes fixed (50 total) |
| + Single-char fragment filter | **26,907** | 4 | **0** | 69 | +68 dialogues, −111 fragments |
| + Tighten report + FF/F0-FE recovery | 26,907 | 4 | 0 | 20 | −49 partial (19 fixed + 30 false positives removed) |
| + Discard unfixed [script:00 80] | 26,892 | 4 | 0 | 5 | −15 MIPS garbage discarded |
| + Continuation prefix=0 fix | **26,844** | 4 | 0 | **1** | −48 (MIPS unmasked), −4 partial fixed |
| + Cross-boundary text fix | 26,841 | 4 | 0 | **0** | −3 cross-boundary partials eliminated |
| + MIPS めあ pattern check | **26,831** | **57** | 0 | 0 | 10 MIPS entries eliminated at decoder level |
| + Garbage text rules (post-filter) | **26,775** | **0** | 0 | 0 | Ported 7 patterns from report generator; −56 dialogues, −57 garbage |

## Other Fixes

### Bare Dialogue (0x00B4) Freeze Fix (2026-02-07)

**Root cause**: Decoder false positive. Offset 0x001780CC in S100.STG contains
event script opcodes (`23 01 XX 8C` repeated 3×), not text. When patched as
dialogue, the game froze.

**Fix**: Added garbage filter Rule 6 — detects repeating 2-char pairs at
regular intervals (≥4 chars apart, ≥3 occurrences), the fingerprint of
repeated script opcodes decoded as text.

- `patch_korean.py`: Removed blanket SKIP_OPCODES for 0x00B4
- `patch_variable_length_multi.py`: SKIP_OPCODES = {0x00B4} still needed
  (VLUT index alignment — bare dialogues don't use sequential handler)

### Safe Truncation Fix (2026-02-07)

`safe_truncate()` in `patch_korean.py` prevents truncation from cutting
mid-sequence:
- FF XX XX XX control codes (4-byte sequences)
- F0-F8 XX 2-byte Korean characters

### Pure Kana Dialogue Fix (2026-02-08)

Event script (0x00B0) and padding (0x00A0) scanners had strict validation
requiring `has_box_tag or has_kanji or is_menu`. Pure kana dialogue like
`やめろ！！` failed all three checks and was silently dropped.

**Fix**: Added targeted acceptance criteria alongside strengthened garbage filter:
1. **is_pure_kana**: kana + punctuation (`！？…。`), ≥2 kana chars
2. **is_long_hiragana**: pure hiragana ≥13 chars

### Multi-Dialogue Gap Search (2026-02-08)

`_find_dialogue_in_gap()` uses five search strategies to find dialogue in
gaps between templates:

1. **Primary**: pointer-based prefix search (ptr_a − 0x10)
2. **Secondary**: alternate prefix (off by SCRIPT_BLOCK_SIZE)
3. **Gap-start**: direct decode from gap start (fixed 03 01 prefix)
4. **Continuation**: sequential decode after found dialogue (multi-dialogue gaps)
5. **Fallback**: null-terminated string scan

Reduced missed gaps: 362 → 40 across all 19 STG files.

### CharID 160 = ッ (not space)

CharID 160 is ッ (small katakana tsu) in the original font, NOT a space.
The `table[160] = " "` override in `build_decode_table()` was removed.

### Partial Decode Fix — Structural Replay (2026-02-08)

**Root cause**: Continuation/fallback search in `_find_dialogue_in_gap()` can
start at a `0x00` byte. This 0x00 gets consumed as prefix byte 1, and the
actual first text character becomes prefix byte 2, producing `[script:00 XX]`
where XX is the eaten character's charID.

**Example**: `[script:00 0A]んな所に何の用だい？` should be `こんな所に何の用だい？`
— charID 0x0A (こ) was consumed as prefix byte 2.

**Fix**: Structural replay in `scan_stg()` post-processing with three cases:

- **Case 1 (FF control code)**: `[script:00 FF]` — FF is always a control code
  prefix. Shift restores `FF XX XX XX` as a proper tag (e.g., `[box:system]`).
  Bypasses `pointer_validated` guard (VLUT index 0xFF00+ is impossible).
- **Case 2 (F0-FE extended char)**: 2-byte char prefix eaten. Shift restores
  `F0-FE XX` as the correct extended character. Validates `new_content[1:]
  == original_content[1:]`. Also bypasses `pointer_validated` guard.
- **Case 3 (standard)**: Single-char recovery via `endswith` check. Recovered
  char must match `decode_table[XX]`. Guarded by `pointer_validated` and
  `_A9_SOURCED` to prevent false positives.

**Guard logic**: Bytes F0-FF are always encoding prefixes, never valid VLUT
indices (would require 0xF000+ = 61,440+ entries per chunk). The
`pointer_validated` and `_A9_SOURCED` guards are bypassed for these bytes.

**Results**: 69 fixes across all STG files, zero false positives.

### Discard Unfixed [script:00 80] MIPS Garbage (2026-02-08)

**Root cause**: 15 entries with `[script:00 80]` prefix survived structural replay
because the shift loop failed to recover valid text. All 15 are MIPS register
operand bytes (0x80) consumed as script prefix byte 2. The decoded content
(`えギクけぽ`, `タゴタギ`, `あギ地ちN`, etc.) is characteristic MIPS garbage from
gap search hitting data blocks in the text region.

**Fix**: In the structural replay `else` clause (shift failed), discard entries
with `second_byte == 0x80` instead of keeping them as partial decodes.

**Results**: 15 MIPS garbage entries eliminated. Partial decodes: 20 → **5**.

### Continuation Search prefix=0 Fix (2026-02-08)

**Root cause**: The continuation search in `_find_dialogue_in_gap()` used
`prefix=2` when decoding sequential dialogues after the first found entry.
But continuation dialogues are raw null-terminated strings with **no** 2-byte
script prefix — the first 2 text characters were consumed as `[script:XX YY]`.

**Example**: `[script:0A 19]町のハンターにカッコイイ人がいるの` should be
`この町のハンターにカッコイイ人がいるの` — charIDs `0A` (こ) and `19` (の)
were consumed as the 2-byte prefix.

**Scale**: ~180 continuation entries across all 19 STG files were affected.

**Fix**: Changed `decode_string(..., prefix=0)` for continuation search.
Also adjusted `text_start`, `consumed` threshold, and
`_has_mips_opcode_signature()` prefix parameter to match.

**Results**:
- Partial decodes: 5 → **1** (4 ュウ/ところで entries now correctly decoded)
- Total dialogues: −48 (MIPS garbage unmasked when full text exposed to filters)

### Cross-Boundary Text Region Fix (2026-02-09)

**Root cause**: Some dialogue strings physically straddle the event script / text
region boundary (`chunk+0xB3FFF` → `chunk+0xB4000`). The chunk-boundary scanner's
gap-start decode starts at `0xB4000` and captures only the tail of the string,
producing a partial duplicate. The template-pair loop correctly finds the full
cross-boundary string because its gap extends into the event script region.

**Affected entries** (3 total):

| File | Partial (removed) | Full (kept by template-pair loop) |
|------|-------------------|----------------------------------|
| S200 | `ございました` at 0xB4000 | `あの…[br]ありがとうございました` at 0xB3FF4 |
| S700 | `たも、助けてもらえるまで…` at 0xB4000 | `あなたも、助けてもらえるまで…` at 0xB3FFE |
| SG00 | `丈夫か？` at 0xB4000 | `大丈夫か？` at 0xB3FFE |

**Fix**: In `_find_dialogue_in_gap()`, skip the gap-start decode fallback when
`gap_start` is at the text region boundary (`chunk+0xB4000`) and the byte before
is non-null (indicating a cross-boundary string).

**Results**: Partial decodes: 1 → **0**. Total dialogues: −3.

### MIPS めあ Register-Reference Pattern Check (2026-02-09)

**Root cause**: `_has_mips_opcode_signature()` used three payload-based checks
(density, cadence, saturation) keyed on `MIPS_OPCODE_MARKER_BYTES = {0x80, 0x8C}`.
These caught high-marker entries but missed MIPS instruction sequences where the
opcode bytes don't include 0x80/0x8C. In particular, sequences of SPECIAL-type
instructions (ADD, SUB, etc.) with rs=$zero produce the raw byte pattern
`0x22 0x01` (decoded as めあ) — the R3000 little-endian encoding of `$zero` in
the rs field combined with SUB/ADD function codes.

**Pattern**: Raw bytes `0x22 0x01` (めあ) appearing 2+ times in the dialogue
payload, with no text control bytes (FF, EF, F0-FE) present.

**Why periodicity doesn't work**: The plan originally called for a 4-byte
periodicity check (MIPS instructions are 4 bytes wide). However, the game's
character encoding overlaps heavily with MIPS opcode byte ranges:
- CharIDs 0x80-0x9B = dakuten katakana (ギ, グ, ゲ, ゴ, ザ, ジ, ズ, **デ**, **ド**, バ, ビ, ブ, ベ, ボ, パ, ピ, プ, ペ, ポ, ァ, ィ, ゥ, ェ)
- CharIDs 0xA0-0xBB = ッ, A-Z, a

These are identical to the R3000 load/store opcode byte[3] values (LB-LWR at
0x80-0x9B, SB-SWR at 0xA0-0xBB). Real dialogue like "ドッグフード" (dog food),
"ゲラゲラゲラ！" (laughter), and "クキェー、グェッグェッ" (creature sound) all
triggered false positives. Tested against 26,769 real dialogues — no parameter
combination achieved zero false positives with the periodicity approach.

**Safety guards**:
- F0-FE bytes indicate 2-byte kanji/Korean character encoding (never in MIPS)
- FF bytes indicate box/cursor control sequences (text structure)
- EF bytes indicate line break controls
- Minimum 5 raw bytes before null terminator

**Results**: 10 MIPS garbage entries eliminated at the decoder level. Cat1 report
entries: 69 → **57**. Zero false positives (verified against all 26,769 real
dialogues across 19 STG files).

### Single Character Fragment Filter (2026-02-08)

**Root cause**: 97.3% of Category 2 single-character fragments occur at exactly
`previous_template_offset + 48` (template end boundary). These are template
opcode parameter bytes at the gap start that get accepted by
`_find_dialogue_in_gap()` because the minimum text length was `len(stripped) >= 1`.

**Pattern**: Non-dialogue templates have opcode instructions after the 44-byte
header. Bytes 44-47 are opcodes, and byte 48+ are parameters. A single parameter
byte that happens to be a valid charID gets decoded as a 1-character "dialogue".

Common fragments: `I` (56), `S` (16), `し` (11), `ぱ`/`ぽ`/`ょ` (8).

**Fix**: Raised minimum accepted payload from `len(stripped) >= 1` to
`len(stripped) >= 2 or stripped in VALID_SINGLE_CHARS`. Applied in all four
acceptance paths: primary search, secondary search, gap-start search, and
first dialogue search.

**VALID_SINGLE_CHARS allowlist**:
- Punctuation/reactions: `？！…・ー。、`
- Special symbols: `♪♥♡★☆※`
- UI/directional: `→←↑↓○×△□`

**Results**: Category 2 fragments: 111 → **0**. Total dialogues: +68 (previously
masked real dialogues discovered when single-char fragments no longer block
primary search).

### Structural Byte Classification — Event Trigger Exclusion Zones (2026-02-09)

**Goal**: Structurally identify non-dialogue byte sequences in the text region
BEFORE text decoding, reducing reliance on heuristic garbage filters.

#### Event trigger detection (`_find_event_trigger_ranges()`)

Event triggers (Type 4 bytes) are the largest non-dialogue data category in
the text region (947-1,382 runs per chunk). They use command byte `0x0067`
followed by a fixed structural pattern:

```
67 00  16 80  23 80  14 80  XX 80  A9 00  B7 02   (14 bytes)
^^^^^  ^^^^^^  ^^^^^^  ^^^^^^  ^^^^^^  ^^^^^^  ^^^^^^
CMD    Spk1    Spk2    Spk3    Ctx     RefID   Param
```

**Key constraint**: Bytes at positions +3, +5, +7 must ALL be exactly `0x80`.
This strict validation prevents false positives at dialogue boundaries (e.g.,
`67 00 C0 00` at a dialogue boundary must NOT be falsely identified as an
event trigger).

The function merges consecutive 14-byte triggers into contiguous blocks,
producing exclusion zones that the gap search skips entirely.

#### Exclusion zones (`_build_exclusion_zones()`)

A new function merges script opcode ranges (`_find_script_ranges()`) and
event trigger ranges (`_find_event_trigger_ranges()`) into unified exclusion
zones. All 7 call sites that previously used `_find_script_ranges()` alone
now use `_build_exclusion_zones()`:

- `_scan_text_region_for_dialogues()` — template scanning
- `_find_dialogue_in_gap()` — gap search
- Orphan menu scan (0x00A9)
- Bare dialogue scan (0x00B4)
- Event script region scan (0x00B0)
- Padding region scan (0x00A0)

**Impact**: Event trigger zones reduce MIPS pre-filter calls by ~25
(1,105 → 1,080 in typical runs). One additional garbage entry ("ギね" in
S300) is caught as a result of changed gap dynamics, but output is unchanged
since the post-filter handles it.

#### Template preamble detection — attempted and reverted

Template preamble bytes (`92 00 44 8C 00 80 64 00 00 00`, decoded as
"XしXしボ") were tested as additional exclusion zones. This correctly
blocked one garbage pattern but caused **cascade regressions**: when a
garbage entry is rejected in the gap search, the search falls through to
more aggressive strategies that find different garbage at earlier positions
in the same gap. The template preamble approach was reverted.

#### Assessment of heuristic rule removal

All 12 `_is_garbage_text()` rules were instrumented to track hits across all
19 STG files. **All 12 rules are actively used** with ~5,000+ total hits
across all decoder call sites (gap_start, continuation, fallback, orphan
menu, bare dialogue, event script, padding scan). No rules can be safely
removed — the two-layer approach (structural pre-filter + text heuristic
post-filter) works better than trying to replace heuristics with structural
detection alone.

#### Catalog script

A research tool `python/decode/catalog_text_region.py` was created to scan
all 19 STG files and catalog every non-dialogue byte run in text regions.
It classifies runs as: event_trigger, data_table_ref, dialogue, mips_code,
short_binary, unclassified_binary. Usage:

```bash
python catalog_text_region.py              # scan all STG files
python catalog_text_region.py --verbose    # show all byte runs
python catalog_text_region.py --json       # output full JSON catalog
```

### Garbage Elimination to Zero (2026-02-09)

**Goal**: Eliminate 57 remaining Category 1 garbage entries that the report
generator (`is_garbage()`) catches but the decoder's `_is_garbage_text()` misses.

**Root cause**: Seven pattern gaps between the two garbage detection functions.
The report generator had evolved 20+ patterns over many iterations, but only
a subset had been ported to the decoder's `_is_garbage_text()`.

#### Pattern gaps identified

| Gap | Missing pattern | Entries | Example |
|-----|----------------|---------|---------|
| 1 | Digit+kana mix (no kanji) | 16 | `3ざよ`, `サデリく1` |
| 2 | Narrow MIPS density charset (デ/ギ only) | 23 | `ぺデぴしデギ`, `タデりギ水ゲ` |
| 3 | 地+kana あ threshold too strict (≥2 → ≥1) | 6 | `地おかきあつたと` |
| 4 | No fullwidth ＊ rule | 5 | `どと＊`, `！と＊` |
| 5 | No small kana start / 。prefix | 4 | `ぉとす`, `。つし` |
| 6 | ッ/タ missing from MIPS_KATA | 2 | `クゼゼ`, `タギデ` |
| 7 | No もあ suffix rule | 1 | `ずぞもあ` |

#### Architecture: post-filter, not search-path filtering

**Critical lesson**: Adding `_is_garbage_text()` directly to Primary/Secondary
search strategies causes a **cascade effect**. When a garbage entry is rejected
in Primary search, the gap search falls through to Continuation/Fallback
strategies which scan more aggressively and find hundreds of binary fragments.

Test results of search-path filtering:
- SB00: 915 → 1,660 (+745 entries) — mostly opcode 0x0BF3 binary fragments
- SD00: 947 → 1,715 (+768 entries) — same pattern

**Correct approach**: Use the existing post-filter in `scan_stg()` (line ~1573).
This applies `_is_garbage_text()` to all collected dialogues **after** the gap
search completes, avoiding cascade effects. The new rules in `_is_garbage_text()`
are automatically picked up by this existing infrastructure.

#### New rules ported to `_is_garbage_text()`

| Rule | Pattern | Conditions | Examples caught |
|------|---------|-----------|-----------------|
| 8 | Digit+kana mix | ≤8 chars, no kanji, scattered single digits | `3ざよ`, `サデリく1` |
| 9 | Fullwidth ＊ | ≤5 chars | `どと＊`, `！と＊` |
| 10 | Small kana start | ≤8 chars, starts with ぉ/ゅ/ょ, no kanji | `ぉとす`, `ぉあさ` |
| 11 | 。prefix | ≤5 chars, starts with fullwidth period | `。つし` |
| 12 | もあ suffix | ≤8 chars, ends with もあ, no kanji | `ずぞもあ` |

#### Existing rules modified

| Rule | Change | Reason |
|------|--------|--------|
| 4 (medium) | Added rank pattern exemption (`レベル/ランク/クラス/タイプ/グレード` + letter) | FP: `…レベルD、…C、…A、` |
| 6 | Exempt patterns with punctuation (`、。！？ー…っッ`) | FP: `ふぉっ、ふぉっ、ふぉっ`, `コロス、コロス、コロスー！` |
| 7d | Split into narrow (デ/ギ only, no kanji exemption) + wide 7d2 (デギグダズヌ水, with MIPS_KANJI exemption) | Gap 2: F0-FE kanji in MIPS data bypassed kanji exemption |
| 7f | Added ッ/タ to MIPS_KATA; require `len(set(stripped)) >= 2` | Gap 6 + FP: `ククク` (villainous laugh) |
| 7h | Lowered 地+hiragana あ threshold from ≥2 to ≥1 | Gap 3: `地おかきあつたと` has only 1 あ |

#### False positive investigation

| Text | Why it's real | Fix applied |
|------|--------------|-------------|
| `ふぉっ、ふぉっ、ふぉっ` (×3) | Onomatopoeia/emphasis with punctuation | Rule 6: exempt strings with `、。！？ー…っッ` |
| `コ、コロス、コロス、コロスー！` | Stammering death threat dialogue | Rule 6: same punctuation exemption |
| `くそっ、くそっ、くそっ！！` | Frustrated exclamation with punctuation | Rule 6: same punctuation exemption |
| `1000ゴッズだ` (×2) | Game currency amount (1000 Gods) | Rule 8: exempt multi-digit numbers |
| `ククク` | Villainous laugh (common trope) | Rule 7f: require ≥2 distinct characters |
| `…レベルD、…C、…A、` | Game rank/level naming | Rule 4: rank pattern exemption |

#### Results

Category 1 garbage: 57 → **0** across all 19 STG files. Total dialogues: 26,831 → **26,775**
(−57 garbage removed, +1 dialogue recovered from FP fix). Zero false positives.
