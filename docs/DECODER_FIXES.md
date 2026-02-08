# STG Decoder Fixes (decode_text.py)

## Overview

The STG dialogue decoder (`python/decode/decode_text.py`) extracts Japanese dialogue from
Arc the Lad 2's STG stage files. Because the decoder scans binary data that includes
MIPS machine code alongside text, it must distinguish real dialogue from garbage produced
by misinterpreted opcodes.

**Final stats** (2026-02-08): 26,907 dialogues across 20,947 templates in 19 STG files.
Category 1 garbage: **4**. Category 2 single-char fragments: **0**. Partial decodes: **20**.

## Garbage Filter Rules (`_is_garbage_text()`)

### Core Rules (1-6)

| Rule | What it catches | Example |
|------|----------------|---------|
| 1 | Unknown charID `[?XXXX]` beyond font table | `[?1A2B]けど` |
| 2 | Invalid FF control codes (not 01,03-0B,0D,0F) | `[FF:B2 0F 2F]` |
| 3 | Lowercase ASCII in Japanese text | `しaとbう` |
| 4 | Uppercase+kana without kanji (≤6: always; ≥7: ≥2 isolated uppercase) | `ゾァびJダIゥゾ`, `テしEと／ねぇむツたDと` |
| 5 | Short mixed hira/kata without repetition (len ≤ 4) | `みギづ` |
| 6 | Repeating 2-char pair at regular intervals (≥4 apart, ≥3 times) | `もあがデもあをデもあんデ` |

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
| **7d** | High デ/ギ density (≥25%, len 4-30) without grammar | ぺデぴしデギ | ~41 |
| **7e** | 2+ distinct predecessors of あ/デ/ギ markers (no kanji/punct) | めああグりあいああ | legacy |
| **7f** | 3-5 char all-katakana from MIPS character set | グゼノ, クゼゼ, シゼニ | 16 |
| **7g** | Starts with ぺデ, ≤8 chars | ぺデデ, ぺデぴしダ | 6 |
| **7h** | Starts with 地 + all hiragana + ≥2 あ | 地えあきあつくと | 4 |
| **7i** | Pure hiragana 12+ chars, no grammatical structure | おつあきけなこたかそいちちて | 2 |

**MIPS_KATA character set** (Rule 7f): {ギ, デ, ゲ, グ, ゼ, ノ, ク, シ, ニ, ダ, ヅ, ヂ, ゾ, ジ}
- Deliberately excludes ッ (small tsu) — too common in real katakana words
- ジ added to catch ジッグ, ジッゲ patterns found in S700 template scanning
- No real Japanese words are composed entirely of these characters

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
| + Tighten report + FF/F0-FE recovery | 26,907 | 4 | 0 | **20** | −49 partial (19 fixed + 30 false positives removed) |

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
20 partial decodes remain: 14 are MIPS garbage (`[script:00 80]`), 5 are
known pattern-match truncations (ュウ, ところで, ございました), 1 is a
region-boundary edge case (`[script:14 03]`).

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
