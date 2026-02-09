# Garbage/MIPS Artifacts in STG Translation Files

**Date**: 2026-02-09 (updated)
**Status**: **ALL RESOLVED** — 0 remaining garbage entries in decoded output
**Previous total**: 62 entries across 13 STG files (out of 26,631 decoded dialogues)
**Current total**: 26,591 dialogues across 19 STG files, 0 garbage in invalid reports

All 62 entries documented below are now caught by the decoder's expanded garbage
filter (`_is_garbage_text()` Rules 17-19 + expanded SHARED_BLOCK_ARTIFACTS blocklist).
They are no longer present in decoded output or translation files. This document
is preserved as a historical reference of the artifacts that were identified and
the patterns used to eliminate them.

## Summary by STG File

| STG | Count | Top Patterns |
|-----|-------|-------------|
| SI00 | 15 | XxXxせ pointer tables ×7, short fragments ×3, padding ×1 |
| S800 | 7 | Repeating MIPS block (トにトに…) ×4, mixed ASCII+kana ×2, pointer table ×1 |
| S700 | 7 | あわし (script:81 28) ×3, short fragments ×4 |
| SF00 | 7 | XxXxボ pointer tables ×7 |
| SD00 | 6 | Pointer table ×1, MIPS fragments ×5 |
| S200 | 5 | Partial decode ×2, short fragments ×3 |
| SE00 | 4 | Pointer table ×1, MIPS fragments ×3 |
| SA00 | 3 | Pointer table ×1, pure hiragana MIPS ×1, fragment ×1 |
| SG00 | 3 | Padding region ×2, short fragment ×1 |
| S400 | 2 | 水あ (ADDIU instruction) ×2 |
| S900 | 1 | MIPS kanji fragment |
| SB00 | 1 | MIPS register fragment |
| SH00 | 1 | Long MIPS block |

## Classification

| Category | Count | Description |
|----------|-------|-------------|
| **XxXxY pointer table** | 18 | Two repeated 2-byte values + terminator (ボ/せ/チ) |
| **Short fragment (≤3 chars)** | 22 | Nonsensical 2-3 character strings from data bytes |
| **MIPS script prefix** | 14 | Script prefix bytes are known MIPS patterns (00 00, FF FF, XX 80, 81 28, etc.) |
| **Mixed ASCII+kana** | 11 | Random mix of ASCII letters and Japanese kana (never occurs in real dialogue) |
| **Repeating pattern** | 5 | Long strings with 2-char repeating subsequences (e.g., トにトにトに) |
| **Known MIPS substring** | 4 | Contains known MIPS-decoded substrings (水あ, 団ぷあれギ, 地お) |
| **Padding region** | 3 | From opcode 0x00A0 (padding/VLUT region, not text) |
| **Partial decode** | 2 | Truncated real dialogue (first characters eaten as prefix bytes) |
| **Unclassified** | 8 | Garbage by context but no single strong signal |

Note: Entries may have multiple classifications (e.g., both "short fragment" and "MIPS script prefix").

## Full Listing

### S200 (5 entries)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x003ABB4A | 0x8005 | 05 80 | ずもよ | MIPS register prefix; short fragment |
| 0x003ABC02 | 0x8005 | A9 00 | ベぞあ、みつかった | Partial decode (ベぞあ = garbage prefix, みつかった = real tail) |
| 0x003ABC65 | 0x8005 | 00 26 | ろしくおねがいしまーす』 | Partial decode (truncated よろしくおねがいしまーす) |
| 0x00C84160 | 0x8014 | FF FF | げどを | MIPS (script:FF FF); short fragment |
| 0x00C842B2 | 0x8014 | A2 00 | せばい | MIPS data prefix; short fragment |

### S400 (2 entries)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x000B1CA0 | 0x00B0 | 1B 15 | 水あ | ADDIU instruction (0xDF 0x01 = 水あ); repeated across files |
| 0x000B3F86 | 0x00B0 | 8E 26 | 水あ | Same ADDIU pattern |

### S700 (7 entries)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x01613F65 | 0x8001 | 81 28 | あわし | Shared code block fragment (script:81 28 = あわしあ block) |
| 0x01614533 | 0x0006 | 81 28 | あわし | Same shared code block fragment |
| 0x01614EE3 | 0x0006 | 81 28 | あわし | Same shared code block fragment |
| 0x0178E216 | 0x8016 | 07 00 | ぁぁぁ | Small-あ repeat; not real dialogue (no context) |
| 0x0178E3E2 | 0x8016 | A9 00 | ！こ～ | Incomplete exclamation fragment |
| 0x0178F204 | 0x8016 | A2 00 | ！ちい | MIPS data prefix; short fragment |
| 0x0183164E | 0x8013 | B8 06 | ♠ざた | Non-dialogue symbol (♠); short fragment |

### S800 (7 entries)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x00177F66 | 0x8016 | 00 00 | ぼたザとEね－みるるデじぎぼモぅがばモぺにトにトにトにトにト | Large MIPS data block; repeating トに pattern |
| 0x00178167 | 0x8016 | 00 42 | たザとEね－みるるデじぎぼモぅがばモぺにトにトにトにトにト | Same block, offset +0x200 |
| 0x00178367 | 0x8016 | 00 42 | たザとEね－みるるデじぎぼモぅがばモぺにトにトにトにトにト | Same block, offset +0x400 |
| 0x00178567 | 0x8016 | 00 42 | たザとEね－みるるデじぎぼモぅがばモぺにトにトにトにトにト | Same block, offset +0x600 |
| 0x001786FC | 0x8016 | 42 00 | テえトくザしEた | Mixed ASCII+kana; MIPS data |
| 0x00178854 | 0x8016 | 04 00 | タギタザタギタザG | Repeating MIPS katakana (タギタザ = register ops) |
| 0x00523926 | 0x8006 | CE 09 | かこかこボ | XxXxボ pointer table |

### S900 (1 entry)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x0046AFF8 | 0x00B4 | 7E 0E | 鉛えほさギ | MIPS kanji fragment (鉛 = known MIPS-decoded kanji) |

### SA00 (3 entries)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x0017695A | 0x8006 | 0E 24 | ぺやぺやボ | XxXxボ pointer table |
| 0x00462180 | 0x00B0 | 97 04 | くきけなしたこそあこうちいて | Pure hiragana MIPS (ADDIU sequence, no grammar) |
| 0x0069E17C | 0x8005 | 05 80 | がゆせ | MIPS register prefix; short fragment |

### SB00 (1 entry)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x007585D6 | 0x8013 | 02 80 | 火さI | MIPS register prefix; known MIPS kanji (火) |

### SC00 — no garbage entries

### SD00 (6 entries)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x0075BD78 | 0x800A | 37 0A | マこマこボ | XxXxボ pointer table |
| 0x00D3D857 | 0x8000 | 80 22 | あ団ぷあれギ | Known MIPS substring (団ぷあれギ) |
| 0x00D3D90E | 0x8000 | 04 80 | 地おI | MIPS register prefix; known MIPS kanji (地) |
| 0x00D3EEEC | 0x800A | A9 00 | 地たよ | MIPS kanji fragment; short fragment |
| 0x00D3F950 | 0x800A | A2 00 | てにい | MIPS data prefix; short fragment |
| 0x00D3FA86 | 0x800A | AD 00 | ュにりあぷし | MIPS data prefix |

### SE00 (4 entries)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x00231A28 | 0x8006 | 11 06 | ぃかぃかボ | XxXxボ pointer table |
| 0x004649B1 | 0x8005 | 00 00 | ギシよよ | MIPS data prefix (script:00 00) |
| 0x0046AFF8 | 0x00B4 | 2D 10 | りあ汎さギ | MIPS kanji fragment (汎 = rare kanji in MIPS data) |
| 0x00DF5EA3 | 0x0006 | 00 0A | ぼじ | Short fragment |

### SF00 (7 entries)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x0178E3D2 | 0x800A | B2 16 | ～に～にボ | XxXxボ pointer table |
| 0x0178E636 | 0x800A | E4 17 | ふねふねボ | XxXxボ pointer table |
| 0x01BF99B6 | 0x801E | 3C 10 | ヤたヤたボ | XxXxボ pointer table |
| 0x01BF9CD0 | 0x801E | C9 11 | あつあつボ | XxXxボ pointer table |
| 0x01BF9F94 | 0x801E | 2B 13 | テてテてボ | XxXxボ pointer table |
| 0x01BFA1E2 | 0x801E | 52 14 | ヂとヂとボ | XxXxボ pointer table |
| 0x01BFAC9A | 0x800A | AE 19 | ＋の＋のボ | XxXxボ pointer table |

### SG00 (3 entries)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x00162931 | 0x00A0 | 34 36 | ぞビぼニぷゴミよ気グ | Padding region; random kana/kanji mix |
| 0x005151EE | 0x00A0 | 81 00 | と疑わエEZ[opt]リXクじギ | Padding region; mixed ASCII+kana |
| 0x02295C36 | 0x8000 | A9 00 | りちよ | Short fragment |

### SH00 (1 entry)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x0015F2BE | 0x8008 | D0 19 | バなれちテデイちすすゾたロヌモぅ[opt]だぅるEと | Large MIPS data block; mixed ASCII+kana |

### SI00 (15 entries)

| Offset | Opcode | Script | Decoded Text | Classification |
|--------|--------|--------|-------------|---------------|
| 0x001742B0 | 0x8006 | 0E 00 | おギ！めせ | MIPS opcode fragment |
| 0x00233AE8 | 0x8006 | 2B 55 | ぢオぢオせ | XxXxせ pointer table |
| 0x00233BB0 | 0x8006 | 8F 55 | ュオュオせ | XxXxせ pointer table |
| 0x00233C78 | 0x8006 | F3 55 | いカいカせ | XxXxせ pointer table |
| 0x00233D40 | 0x8006 | 57 56 | ニカニカせ | XxXxせ pointer table |
| 0x00233ED0 | 0x8006 | 1F 57 | んキんキせ | XxXxせ pointer table |
| 0x00233F98 | 0x8006 | 83 57 | ボキボキせ | XxXxせ pointer table |
| 0x00234128 | 0x8006 | 4B 58 | コクコクせ | XxXxせ pointer table |
| 0x0023421A | 0x8006 | A9 00 | ユク水 | Short fragment; MIPS kanji (水) |
| 0x0023484C | 0x8005 | E3 5B | …シ…シーサ…サーサーサーサ…シI | Repeating pattern; mixed ASCII+kana |
| 0x0044F035 | 0x8000 | E2 04 | みぴブゥホろルげト | Random kana mix |
| 0x0050FDF9 | 0x00A0 | 34 36 | ぞビぼニぷゴミよ気グ | Padding region; same as SG00 entry |
| 0x01B3CB30 | 0x8005 | FF FF | ねけを | MIPS (script:FF FF); short fragment |
| 0x01B3CC12 | 0x8005 | 02 80 | がなせ | MIPS register prefix; short fragment |
| 0x01B3CC84 | 0x8005 | A9 00 | キよ逃ゲルッス | Mixed kana+kanji; contains real word 逃ゲル but in MIPS context |

## How These Were Eliminated

The decoder's `_is_garbage_text()` was expanded from 16 to 19 rules, and the
`SHARED_BLOCK_ARTIFACTS` blocklist was expanded from 43 to 70 entries:

| Method | Entries caught | Description |
|--------|---------------|-------------|
| Rule 17 (XxXxY pointer tables) | 18 | 5-char pair+terminator pattern |
| Rule 18 (trailing uppercase ASCII) | ~8 | Kana/kanji followed by isolated uppercase |
| Rule 19 (padding mixed-script) | ~3 | `[opt]` + lowercase ASCII + kana |
| Extended Rule 9 (♠ symbol) | 1 | Data marker character |
| Extended Rule 13 (水あ) | 2 | ADDIU instruction artifact |
| Extended Rule 14 (kanji+hira+upper) | ~4 | Register operand pattern |
| SHARED_BLOCK_ARTIFACTS Type F | ~19 | Residual MIPS artifacts (exact match) |
| SHARED_BLOCK_ARTIFACTS Type G | 8 | Short hiragana fragments (exact match) |

Two partial decode entries (ベぞあ、みつかった and ろしくおねがいしまーす) were also
eliminated — they were reclassified during the decode count adjustment.

## Historical Reference (original analysis below)
