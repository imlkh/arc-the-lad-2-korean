# Arc the Lad 2 Korean Translation Progress

**Last Updated**: 2026-02-05

## Overall Statistics

| Metric | Count |
|--------|-------|
| Total STG files | 19 |
| Fully translated | 5 |
| In progress | 14 |
| Total dialogues | 20,199 |
| Translated dialogues | ~7,500 |
| Remaining dialogues | ~12,858 |
| Batch progress | 34/434 (7.8%) |

## Decoder Improvements (2026-02-05)

### Pointer-Based Extraction + Heuristic Fallback

The decoder now uses a two-phase extraction approach:

1. **Pointer-based extraction** (primary): Uses template Ptr_A field to deterministically
   locate dialogue prefixes (Ptr_A - 0x10 = dialogue script prefix offset)

2. **Heuristic fallback**: For gaps where pointer-based method fails (multiple dialogues
   per gap, non-standard prefix locations), scans for null-terminated strings

3. **Garbage filter**: Automatically removes false positives from binary data misinterpreted
   as text, including:
   - Strings with multiple unknown charIDs `[?XXXX]`
   - Random ASCII/digit mixing with kana
   - Repeating 2-char patterns (binary signature)
   - Excessive "ギ" characters (common in MIPS code bytes)
   - Short text ending with ASCII letters

**Results**: 20,199 clean dialogues extracted (270 garbage filtered) across all STG files.

### Command-Line Options
- Default: Heuristic mode with garbage filtering
- `--strict`: Pointer-based only (19,784 dialogues, no garbage)
- `--no-filter`: Disable garbage filtering (for debugging)

## Per-File Status

| File | Status | Translated | Total | Remaining | Batches |
|------|--------|------------|-------|-----------|---------|
| S100 | **DONE** | 1,151 | 1,151 | 0 | 34/34 |
| S200 | Partial | 351 | 1,731 | 1,380 | 0/58 |
| S300 | **DONE** | 316 | 316 | 0 | - |
| S400 | Partial | 767 | 767 | 0 | - |
| S500 | Partial | 520 | 520 | 0 | - |
| S600 | Partial | 119 | 747 | 628 | 0/25 |
| S700 | Partial | 933 | 2,502 | 1,569 | 0/84 |
| S800 | Partial | 267 | 923 | 656 | 0/31 |
| S900 | Partial | 131 | 912 | 781 | 0/31 |
| SA00 | Partial | 75 | 1,249 | 1,174 | 0/42 |
| SB00 | Partial | 769 | 769 | 0 | - |
| SC00 | **DONE** | 693 | 693 | 0 | - |
| SD00 | Partial | 650 | 650 | 0 | - |
| SE00 | Partial | 143 | 1,181 | 1,038 | 0/40 |
| SF00 | Partial | 134 | 2,478 | 2,344 | 0/83 |
| SG00 | **DONE** | 1,466 | 1,466 | 0 | - |
| SH00 | Partial | 44 | 44 | 0 | - |
| SI00 | Partial | 137 | 2,100 | 1,963 | 0/70 |
| SJ00 | **DONE** | 0 | 0 | 0 | - |

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
   - Line breaks: `\n`
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
| 2026-02-05 | S100 | 1,167 | Batch (34 batches) |
| Prior | S300 | 320 | Manual |
| Prior | SC00 | 702 | Manual |
| Prior | SG00 | 1,492 | Manual |
| Prior | SJ00 | 0 | Empty |

## Next Priority

Files by remaining dialogue count (largest first):

1. **SF00**: 2,348 remaining (79 batches)
2. **SI00**: 1,966 remaining (66 batches)
3. **S700**: 1,572 remaining (53 batches)
4. **S200**: 1,381 remaining (46 batches)
5. **SA00**: 1,175 remaining (40 batches)
6. **SE00**: 1,041 remaining (35 batches)
