# Arc the Lad 2 Korean Translation Progress

**Last Updated**: 2026-02-07

## Overall Statistics

| Metric | Count |
|--------|-------|
| Total STG files | 19 |
| Fully translated | 5 |
| In progress | 14 |
| Total dialogues | 20,484 |
| Translated dialogues | ~7,500 |
| Remaining dialogues | ~13,192 |
| Batch progress | 34/434 (7.8%) |

## Decoder Improvements (2026-02-06)

### Paired Signature Validation

Every valid template has TWO signatures:
- Primary: `0x8BF00123` at bytes 0-3
- Secondary: `0x8BF00145` at bytes 16-19 (always paired at +16)

The decoder now validates that both signatures are present, filtering out ~47 false positives from binary data that only matches the primary signature.

### Rule-Based Garbage Filter

Replaced the complex heuristic garbage filter with a simple 4-rule system:

1. **Unknown charID** `[?XXXX]`: CharID > 1764 is beyond font table (441 cells × 4 bitplanes)
2. **Invalid FF opcode**: Valid opcodes are 01, 03, 04, 05, 06, 07, 08, 09, 0A, 0B, 0D, 0F only
3. **Lowercase ASCII in Japanese**: Game text uses uppercase only (HP, MP, BGM, etc.)
4. **Short uppercase+kana**: Text ≤6 chars with uppercase + kana but no kanji
5. **Short mixed kana**: Text ≤4 chars with mixed hiragana/katakana without repetition

**Results**: 20,484 dialogues extracted (filtered 47 false positive templates, 177 garbage strings)

### Valid FF Control Codes

| Opcode | Count | Purpose |
|--------|-------|---------|
| 01 | 10 | Text highlight |
| 03 | common | Delay |
| 04 | 38 | Menu marker |
| 05 | common | Newline |
| 06 | 25 | Button icon |
| 07 | common | Number display |
| 08 | 90 | Box control |
| 09 | 4 | Emphasis |
| 0A | 25 | Currency format |
| 0B | common | Item name |
| 0D | common | Character name |
| 0F | 1 | Unknown effect |

### Chunk-Boundary Scanning Fix

Fixed an issue where dialogues appearing at the start of chunk text regions were missed
when template-to-template gaps crossed chunk boundaries. The decoder now:

- **Chunk-boundary scanning**: For each 772KB chunk, scans the text region start
  (chunk_start + 0xB4000) for dialogues that appear before the first template in
  that chunk. This captures ~305 additional dialogues that were previously missed.

### Bare Dialogue Detection (2026-02-07)

Added detection for "bare dialogues" - A9 00 marker texts with kanji content but no template or [opt] tag:
- Location names (コルボ平原, ラウス平野)
- Battle messages (戦闘に参加するキャラクターを選んで下さい)
- Scene announcements (持ち場につけ！)
- Context opcode: `0x00B4`

**Results**: S100.STG has 40 bare dialogues, SG00.STG has 377 bare dialogues.

### Pointer-Based Extraction + Heuristic Fallback (2026-02-05)

The decoder uses a multi-phase extraction approach:

1. **Pointer-based extraction** (primary): Uses template Ptr_A field to deterministically
   locate dialogue prefixes (Ptr_A - 0x10 = dialogue script prefix offset)

2. **Heuristic fallback**: For gaps where pointer-based method fails (multiple dialogues
   per gap, non-standard prefix locations), scans for null-terminated strings

3. **Garbage filter**: Rule-based filter removes false positives from binary data

### Command-Line Options
- Default: Heuristic mode with garbage filtering
- `--strict`: Pointer-based only (no heuristic fallback)
- `--no-filter`: Disable garbage filtering (for debugging)

## Per-File Status

| File | Status | Translated | Total | Remaining | Batches |
|------|--------|------------|-------|-----------|---------|
| S100 | **DONE** | 1,151 | 1,321 | 170 | 34/34 |
| S200 | Partial | 351 | ~1,900 | ~1,550 | 0/65 |
| S300 | **DONE** | 316 | ~350 | ~34 | - |
| S400 | Partial | 767 | ~850 | ~83 | - |
| S500 | Partial | 520 | ~580 | ~60 | - |
| S600 | Partial | 119 | ~830 | ~711 | 0/28 |
| S700 | Partial | 933 | ~2,800 | ~1,867 | 0/94 |
| S800 | Partial | 267 | ~1,030 | ~763 | 0/35 |
| S900 | Partial | 131 | ~1,020 | ~889 | 0/34 |
| SA00 | Partial | 75 | ~1,400 | ~1,325 | 0/47 |
| SB00 | Partial | 769 | ~850 | ~81 | - |
| SC00 | **DONE** | 680 | ~750 | ~70 | - |
| SD00 | Partial | 650 | ~730 | ~80 | - |
| SE00 | Partial | 143 | ~1,340 | ~1,197 | 0/45 |
| SF00 | Partial | 134 | ~2,760 | ~2,626 | 0/92 |
| SG00 | Partial | 1,466 | 2,445 | 979 | - |
| SH00 | Partial | 44 | ~60 | ~16 | - |
| SI00 | Partial | 137 | ~2,330 | ~2,193 | 0/78 |
| SJ00 | **DONE** | 0 | 0 | 0 | - |

**Note**: Total counts now include all dialogue types (template, bare, orphan menu, event script, padding). Counts with ~ are estimates pending full re-scan.

## Translation Workflow

### Batch System

The translation uses a batch system for large files:

1. **Prep**: `python/translation/translate_batch_prep.py`
   - Splits untranslated dialogues into ~30-line batches
   - Creates `translated/ko/batches/<STG>_batch_NNN.txt`
   - Generates `manifest.json` for tracking

2. **Translate**: Manual or automated translation
   - Input: `<STG>_batch_NNN.txt` (Japanese)
   - Output: `<STG>_batch_NNN_ko.txt` (Korean)
   - Must preserve all formatting (offsets, opcodes, tags)

3. **Merge**: `python/translation/translate_batch_merge.py`
   - Updates `manifest.json` batch status to "done"
   - Merges completed batches into `translated/ko/<STG>_STG.txt`

### Translation Rules

1. **Preserve formatting**:
   - Hex offsets: `0x00172EC6`
   - Opcodes: `[0x8009]`
   - Script codes: `[script:83 26]`
   - Delay tags: `[delay:0B]`
   - Box types: `[box:speech]`, `[box:close]`
   - Line breaks: `[br]`
   - Context lines: `--- context: 0x8009 -> 0x8001 ---`

2. **Character name mappings**:
   | Japanese | Korean |
   |----------|--------|
   | エルク | 엘크 |
   | リーザ | 리자 |
   | シャンテ | 샨테 |
   | ポコ | 포코 |
   | トッシュ | 토슈 |
   | ゴーゲン | 고겐 |
   | シュウ | 슈우 |
   | ククル | 쿠쿠루 |
   | グルガ | 그루가 |
   | イーガ | 이가 |
   | サニア | 사니아 |
   | アーク | 아크 |
   | ちょんがら | 총가라 |

3. **Place name mappings**:
   | Japanese | Korean |
   |----------|--------|
   | ロマリア | 로말리아 |
   | アルディア | 알디아 |
   | プロディアス | 프로디아스 |
   | スメリア | 스메리아 |
   | パレンシア | 팔렌시아 |
   | ニーデル | 니델 |
   | ブラキア | 브라키아 |

## Files Location

- **Source (Japanese)**: `output/decoded/stg/*.txt`
- **Translated (Korean)**: `translated/ko/*.txt`
- **Batch files**: `translated/ko/batches/`
- **Manifest**: `translated/ko/batches/manifest.json`
- **Unique chars**: `translated/ko/unique_korean_chars.txt`

## Completion History

| Date | File | Dialogues | Method |
|------|------|-----------|--------|
| 2026-02-06 | Rule-based filter | +10 | Replaced heuristic with 4-rule filter |
| 2026-02-06 | Decoder fix | +324 | Chunk-boundary scanning |
| 2026-02-05 | S100 | 1,167 | Batch (34 batches) |
| Prior | S300 | 320 | Manual |
| Prior | SC00 | 702 | Manual |
| Prior | SG00 | 1,492 | Manual |
| Prior | SJ00 | 0 | Empty |

## Next Priority

Files by remaining dialogue count (largest first):

1. **SF00**: 2,376 remaining (84 batches)
2. **SI00**: 1,981 remaining (71 batches)
3. **S700**: 1,621 remaining (86 batches)
4. **S200**: 1,401 remaining (59 batches)
5. **SA00**: 1,196 remaining (43 batches)
6. **SE00**: 1,072 remaining (41 batches)
