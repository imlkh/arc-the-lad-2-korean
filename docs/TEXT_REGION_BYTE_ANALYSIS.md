# Text Region Byte Sequence Analysis

Analysis of all byte sequence types in the STG text region (0xB4000-0xBC7FF)
for improved MIPS/binary garbage detection.

## Byte Sequence Types in Text Region

The 34,816-byte text region contains **7 distinct byte sequence types**:

### Type 1: Template Structures (48 bytes each)

Dialogue trigger structures with known 4-byte signatures.

```
Signature: 23 01 F0 8B (primary, offset +0x00)
           45 01 F0 8B (secondary, offset +0x10)
```

Example:
```
23 01 F0 8B 05 80 28 01 F0 0B 04 00 00 80 2E 09
45 01 F0 8B 05 80 28 01 F0 0B 00 00 00 80 2E 09
00 63 05 80 A9 00 2D 00 30 00 62 00 02 80 A9 00
```

Reliably detected by signature bytes. The decoder uses these as anchors.

### Type 2: Script Opcode Blocks (10 bytes each)

Control flow commands between dialogue strings and templates.

```
Signature: 28 01 (first 2 bytes)
```

Example:
```
28 01 F0 0B 04 00 00 80 A0 09
```

Reliably detected by signature. The decoder trims these from gap boundaries.

### Type 3: Dialogue Strings (variable length, null-terminated)

Actual game dialogue text encoded as CharID sequences with control codes.

```
Structure: [prefix bytes] [CharIDs + control codes] [00 null]
```

**Key feature: Almost always contain 0xFF control codes** (box, br, cursor, etc.)

Examples:
```
AE 01 FF 08 01 01 5D 52 A0 61 2F 01 28 1F 0D FF 05 ...  (has FF×3)
F8 09 14 16 06 08 F0 3F F2 61 16 20 0E 15 08 11 4D     (has F0/F2)
D7 09 01 01 E4 F3 29 F3 E8 24 3E 02 F2 47 2D FF 05 ... (has F3/F2/FF)
```

Byte distribution (from S200 first 3 chunks):
| Range | % | Description |
|-------|-----|-------------|
| 0x01-0x50 | 52.9% | Hiragana CharIDs |
| 0x51-0xA0 | 26.6% | Katakana CharIDs |
| 0xA1-0xD4 | 7.8% | ASCII letters |
| 0xD5-0xEE | 2.5% | Numbers, symbols, kanji |
| 0xEF-0xFF | **10.2%** | **Control codes (FF, EF, F0-FE)** |

### Type 4: Event Trigger Commands (~14 bytes each)

Event system commands that control dialogue flow. **Structurally detected** by
`_find_event_trigger_ranges()` since 2026-02-09 (see DECODER_FIXES.md).

```
Structure: 67 00 [spk1 80] [spk2 80] [spk3 80] [ctx 80] [ref 00] [param]
           ^^^^^ ^^^^^^^^^ ^^^^^^^^^ ^^^^^^^^^ ^^^^^^^^ ^^^^^^^^ ^^^^^^^
           CMD    Speaker1   Speaker2  Speaker3  Context   RefID   Extra
```

The defining feature is the `XX 80` repeating pattern — speaker opcodes are
16-bit values in the 0x80XX range (little-endian: `XX 80`).

Examples from S200 chunk 7 (0xB8A52+):
```
67 00  16 80  23 80  14 80  02 80  A9 00  BD 02   → speakers 8016,8023,8014 ctx=8002 ref=00A9
67 00  16 80  23 80  14 80  03 80  A9 00  BD 02   → speakers 8016,8023,8014 ctx=8003 ref=00A9
67 00  16 80  23 80  14 80  04 80  AA 00  6A 02   → speakers 8016,8023,8014 ctx=8004 ref=00AA
```

**Why the decoder picks these up**: The scanner splits `67 00` (67=ぱ, 00=null)
from the speaker bytes. The remaining `16 80 23 80 14 80 02 80 A9` becomes
an "unknown" run in the gap between templates. The gap search then finds
prefix-matching bytes within this run and decodes them as dialogue.

**Volume**: 947-1382 runs per chunk (3,500-6,100 bytes), the largest category
of non-dialogue data in the text region.

### Type 5: Null Padding (0x00 bytes)

Zero-fill between structures and after dialogue null terminators.
Typically 8,500-20,700 bytes per chunk (25-60% of text region).

### Type 6: MIPS Code Fragments

Actual R3000 machine code embedded in the text region. These are NOT in the
main MIPS code regions (0x77000-0xA0000) — they appear as small instruction
sequences within the text region, possibly inlined handler code, jump table
targets, or address computation stubs.

All form valid R3000 instructions at 4-byte alignment. The same byte sequences
often appear identically across multiple STG files, confirming they are shared
code rather than random data.

Examples:
```
80 27 01 44 8C 4E 0C 89     → NOR $zero,$fp,$ra + LWL $t4,0x4E8C($t0)
                               Appears in S200, S700, SD00 (identical bytes)
                               Decoded as "あぴデゅしダ"

24 04 DF 03 02 07 01 12     → AND $zero,$fp,$ra + BEQ $s0,$at,...
                               Appears in S200, S600, SB00, SC00, SG00
                               Decoded as "地ういきあつえと"

07 80 06 81 16 81 9C 80     → LB $a2,0x8007($t0) + LB $gp,0x8116($a0)
                               Decoded as "かグにグォギ"

50 8C 50 8C DC 03 D6        → LW $k1,0x8C50($v0)
                               Decoded as "っデ7う1"
```

Distinguishing feature: forms valid instructions AND uses common game-code
registers ($sp, $fp, $ra, $t0-$t3, $s0-$s7, $a0-$a3).

### Type 7: Data Tables / Other Binary

Miscellaneous structured binary data: pointer/offset tables, index arrays,
parameter blocks. Unlike MIPS code, these do NOT consistently form valid
instructions — they contain event reference IDs, timing parameters, and
other non-code values.

Examples:
```
A9 00 EC 12 0C 00    → RefID 0x00A9 + parameters, decoded as "。つし"
A9 00 3D 14 E9 00    → RefID 0x00A9 + parameters, decoded as "どと＊"
FF FF D9 04 2D 00    → 0xFFFF marker + data, decoded as "4えを"
A6 21 DE 21 DE 21 92 → repeating 0xXX21 pattern, decoded as "9む9むボ"
```

## Size Distribution (typical chunk)

| # | Type | Count | Bytes | % | Detected? |
|---|------|-------|-------|---|-----------|
| 1 | Templates (48B) | 30-147 | 1,440-7,056 | 4-20% | Yes (signature) |
| 2 | Script opcodes (10B) | 80-261 | 800-2,610 | 2-8% | Yes (signature) |
| 3 | Dialogue strings | 121-388 | 1,828-4,358 | 5-13% | Target output |
| 4 | Event triggers (~14B) | 309-1,382 | 1,462-6,126 | 4-18% | **Yes** (structural, `67 00` + `XX 80` validation) |
| 5 | Null padding | — | 8,499-29,321 | 24-84% | Yes (trivial) |
| 6 | **MIPS code fragments** | misc | mixed | mixed | **No → garbage** |
| 7 | **Data tables / other** | misc | mixed | mixed | **No → garbage** |
| | **Total** | | **34,816** | 100% | |

## Garbage Entry Analysis

### Where the 57 garbage entries come from

All 57 entries are in the text region (chunk offset 0xB4000-0xBC7FF).
They come from the decoder's gap search misinterpreting Types 4, 6, and 7
as dialogue (Type 3).

| Source type | Garbage entries | Examples |
|-------------|----------------|---------|
| Type 4 (event triggers) | ~8 | A9 00 entries: "。つし", "ぉとす" |
| Type 6 (MIPS code) | ~39 | "あぴデゅしダ", "地ういきあつえと", "かグにグォギ" |
| Type 7 (data tables) | ~10 | "4えを", "9む9むボ", "＊たを" |

### Raw byte patterns of all 57 entries

**Group A — Event trigger speaker opcodes (XX 80 repeating)** (13 entries)

The prefix bytes match the first 2 text bytes because the gap search finds
a prefix match inside a repeating `XX 80` sequence:

```
50 8C | 50 8C DC 03 D6 00   "っデ7う1" — LW instruction bytes
5B 8C | 5B 8C 78 08 D6 00   "サデリく1" — LW instruction bytes
80 80 | 80 80 26 00          "ギギよ"   — LB instruction bytes
```

Diagnostic: `bytes[0:2] == bytes[2:4]` (prefix == first 2 text bytes)

**Group B — Event trigger fragments with 0x80 at odd positions** (~18 entries)

```
07 80 06 81 16 81 9C 80 00   "かグにグォギ"  — byte[1,3,5,7] = 80,81,81,80
08 80 42 81 40 81 E0 80 00   "ぼグぶグ水ギ"  — byte[1,3,5,7] = 80,81,81,80
01 80 A0 82 60 81 00         "ッゲタグ"     — byte[1,3,5] = 80,82,81
```

Diagnostic: bytes at odd positions consistently in 0x80-0x8C range

**Group C — ADDIU instruction pattern (24 04 DF...)** (5 entries)

All decode as "地..." because 0xDF = CharID 223 = 地.

```
24 04 DF 03 02 07 01 12 04 14 00   "地ういきあつえと"
24 04 DF 05 06 07 01 12 10 14 00   "地おかきあつたと"
24 04 DF 02 03 07 01 12 02 14 00   "地いうきあついと"
```

Diagnostic: starts with `24 04 DF` (ADDIU $a0,$a0,... instruction)

**Group D — NOR/LWL instruction pair** (3 entries)

```
80 27 01 44 8C 4E 0C 89 00   "あぴデゅしダ" — NOR + LWL instructions
```

Identical bytes across 3 different STG files (S200, S700, SD00).

**Group E — Short entries from A9 00 markers** (~8 entries)

```
A9 00 EC 12 0C 00   "。つし"
A9 00 3D 14 E9 00   "どと＊"
A9 00 ED 14 E9 00   "！と＊"
```

Event trigger RefID bytes (A9, AA, etc.) followed by parameter data.

**Group F — Miscellaneous data table fragments** (~10 entries)

```
FF FF D9 04 2D 00      "4えを"     — REGIMM instruction
C8 80 36 38 23 01 00   "ずぞもあ"   — XORI instruction
30 38 31 01 20 81 ...  "ぐあみグ水ゲあギよ" — data table
```

### MIPS instruction validation

**All 57 entries** form valid R3000 instructions at 4-byte alignment (100%).

However, this check has a **31.7% false positive rate** on random byte sequences
from the text region. The game's CharID encoding (0x01-0xEE) overlaps with valid
MIPS opcode byte ranges, making pure instruction validation unreliable:

- CharIDs 0x80-0x9B (ギ-ェ) = LB/LBU/LH/LHU/LW/LWL/LWR opcode bytes
- CharIDs 0xA0-0xBB (ッ-a) = SB/SH/SW/SWL/SWR opcode bytes
- CharIDs 0x00-0x0F (あ-そ) = SPECIAL/REGIMM/J/JAL/branch opcode bytes

## Key Discriminators

### Signal 1: Control code presence (strongest)

Real dialogue has **10.2%** control code bytes (FF/EF/F0-FE).
Garbage entries have only **1.2%**. Event trigger commands and data tables
never contain 0xFF/0xEF bytes because these are reserved for the text encoding.

### Signal 2: Prefix == text start (13/57, zero FP)

When `raw_bytes[0:2] == raw_bytes[2:4]`, the "prefix" is just a repeating
pattern in binary data, not an actual script reference. This never occurs
in real dialogue because script prefixes encode control references (e.g.,
`07 80` = speaker 0x8005), not text content.

### Signal 3: 0x80 at odd byte positions (18/57)

Event trigger commands have speaker opcodes at every other byte, producing
`XX 80 XX 80 XX 80...`. Real Japanese text rarely has 0x80+ at ALL odd
positions because dakuten katakana (ギグゲゴ...) rarely appears consecutively.

### Signal 4: Specific byte sequence signatures

- `24 04 DF` = ADDIU $a0 instruction (5 entries)
- `80 27 01 44 8C 4E 0C 89` = NOR+LWL pair (3 entries)
- `22 01` × 2 = めあ pattern (already implemented, 10 entries at decoder level)

### Why pure byte-level detection fails

The fundamental problem: the game's character encoding maps **238 characters**
to bytes 0x01-0xEE, covering **93% of the byte space**. Only 0x00 (null) and
0xEF-0xFF (control codes) have fixed meaning. This leaves essentially no
"invalid" bytes that could distinguish binary data from text — every non-null
byte decodes to a valid character.

| Approach tried | Catches | False positive rate |
|---------------|---------|-------------------|
| All-valid MIPS instructions | 57/57 | **31.7%** — too high |
| 4-byte periodicity (byte[3] in opcode set) | ~45/57 | **158 real dialogues** — catastrophic |
| めあ × 2 (current) | 10/57 | **0%** — safe but limited |
| prefix == text start | 13/57 | **0%** — safe but limited |
| Text-pattern rules (is_garbage) | **57/57** | **0%** — proven over 26,831 dialogues |

## Recommended Approach — IMPLEMENTED (2026-02-09)

The proven text-pattern rules from `generate_invalid_reports.py:is_garbage()`
have been ported to the decoder's `_is_garbage_text()` function. Seven pattern
gaps were identified and closed:

| Gap | Rule added/modified | Entries eliminated |
|-----|--------------------|--------------------|
| Digit+kana mix | New Rule 8 | 16 |
| Narrow MIPS density | Rule 7d split (7d/7d2) | 23 |
| 地+kana threshold | Rule 7h (≥2 → ≥1) | 6 |
| Fullwidth ＊ | New Rule 9 | 5 |
| Small kana / 。prefix | New Rules 10, 11 | 4 |
| ッ/タ in MIPS_KATA | Rule 7f expanded | 2 |
| もあ suffix | New Rule 12 | 1 |

**Architecture**: Rules are applied via the existing `scan_stg()` post-filter
(NOT in search-path validation, which causes cascade effects — see
DECODER_FIXES.md "Garbage Elimination to Zero" section).

**Result**: Category 1 garbage: 57 → **0** across 26,775 dialogues in 19 STG files.
Zero false positives (6 FP cases identified and fixed with exemptions).

The zero-false-positive byte-level checks (prefix==text-start, めあ×2)
remain in `_has_mips_opcode_signature()` as early-exit optimizations
that reject entries before full text decoding.

## Structural Detection — Event Trigger Exclusion Zones (2026-02-09)

In addition to heuristic text-pattern rules, event trigger commands (Type 4)
are now **structurally detected** before text decoding via
`_find_event_trigger_ranges()`. These ranges are merged with script opcode
ranges into unified exclusion zones (`_build_exclusion_zones()`), which the
gap search skips entirely.

**Strict validation**: Bytes at positions +3, +5, +7 must ALL be exactly
`0x80`. This prevents false positives at dialogue boundaries where `67 00`
might appear coincidentally. The initial implementation used a looser check
(any byte >= 0x80) which caused a real dialogue ("ヴ、ヴ、ニゲミチナイ") to
be falsely excluded.

**Key finding**: Structural event trigger detection reduces MIPS pre-filter
calls by ~25 per decode run, but does NOT eliminate the need for heuristic
text-pattern rules. All 12 `_is_garbage_text()` rules remain actively used
(~5,000+ total hits), catching garbage at gap_start, continuation, fallback,
orphan menu, bare dialogue, event script, and padding scan stages. The
two-layer approach (structural pre-filter + text heuristic post-filter) is
the effective architecture.

### Catalog script

A research tool for analyzing non-dialogue byte sequences:
```bash
python python/decode/catalog_text_region.py              # scan all STG files
python python/decode/catalog_text_region.py --verbose    # show all byte runs
python python/decode/catalog_text_region.py --json       # output full JSON catalog
```
