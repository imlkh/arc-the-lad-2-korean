# Arc the Lad 2 Korean Translation Project

## Project Structure

```
atl2_korean_translation/
├── python/                      # Tools
│   ├── decode/                  # Text extraction tools
│   │   ├── decode_text.py       # Core decoder (--stg, --scan, --find modes)
│   │   ├── decode_all_stg.py    # Batch decode all 19 STG files
│   │   ├── decode_all_bin.py    # Decode BIN files (BEAM.DAT, SDIC, etc.)
│   │   └── decode_yend.py       # Decode YEND.BIN ASCII credits (special)
│   │
│   ├── font/                    # Font tools
│   │   ├── view_char.py         # View font cells by row/col or cell index
│   │   ├── generate_korean_font.py  # Generate Hangul glyph PNGs
│   │   ├── replace_kana_with_korean.py  # Replace kana→Korean in COMM.IMG
│   │   ├── compare_chars.py     # Compare extracted vs documented chars
│   │   ├── extract_jp_positions.py  # Extract JP char positions to JSON
│   │   └── show_comm_img_font.py    # Visualize COMM.IMG font area
│   │
│   ├── validation/              # Font validation tools
│   │   ├── validate_chars.py    # Validate COMM_IMG_chars.md accuracy
│   │   ├── validate_dupes.py    # Find duplicate characters
│   │   └── validate_*.py        # Other validation scripts
│   │
│   └── translation/             # Batch translation pipeline
│       ├── translate_batch_prep.py   # Prepare batches of 30 lines
│       ├── translate_batch_run.py    # Instructions for batch translation
│       ├── translate_batch_merge.py  # Merge completed batches
│       └── extract_unique_korean.py  # Extract unique Hangul syllables
│
├── scripts/                     # One-off translation scripts (legacy)
│   └── stg_translators/         # Stage-specific translation attempts
│
├── output/                      # Generated output (git-ignored)
│   ├── decoded/
│   │   ├── stg/                 # Decoded STG dialogue files
│   │   └── bin/                 # Decoded BIN file text
│   ├── font/
│   │   ├── korean_chars/        # Generated Korean glyph PNGs
│   │   ├── COMM_IMG_KR.IMG      # Modified font with Korean
│   │   └── *.png                # Font visualizations
│   └── validation/              # Validation output images
│
├── translated/                  # Korean translations
│   └── ko/
│       ├── S*_STG.txt           # Translated stage files
│       └── batches/             # Batch translation workspace
│
├── docs/                        # Documentation
│   ├── TEXT_ENCODING.md         # Game text encoding reference
│   ├── KOREAN_TRANSLATION.md    # Feasibility analysis
│   ├── STG_analysis.md          # STG file format
│   ├── COMM_IMG_analysis.md     # Font texture format
│   └── *_analysis.md            # Other file analyses
│
└── COMM_IMG_chars.md            # Complete 1,764 character mapping table
```

## Translation Workflow

### 1. Extract Japanese Text

```bash
# Decode all STG files
python python/decode/decode_all_stg.py

# Decode BIN files
python python/decode/decode_all_bin.py

# Output: output/decoded/stg/*.txt, output/decoded/bin/*.txt
```

### 2. Translate (Batch Pipeline)

```bash
# Step 1: Prepare batches (30 lines each)
python python/translation/translate_batch_prep.py

# Step 2: Translate batches (use Claude Code with translate_batch_run.py)
# Step 3: Merge completed batches
python python/translation/translate_batch_merge.py

# Output: translated/ko/*.txt
```

### 3. Generate Korean Font

```bash
# Generate Hangul glyph images
python python/font/generate_korean_font.py

# Replace kana with Korean in COMM.IMG
python python/font/replace_kana_with_korean.py

# Output: output/font/korean_chars/, output/font/COMM_IMG_KR.IMG
```

## Translation Status

| File Type | Total Strings | Status |
|-----------|---------------|--------|
| S*.STG (19 files) | 19,568 | In Progress |
| SCPS_100.26 | ~960 | Pending |
| SDIC.BIN | 555 | Pending |
| SMITH.BIN | 628 | Pending |
| YGUILD.BIN | 363 | Pending |
| BEAM.DAT | ~900-1,400 | Pending |

## Character/Place Name Mappings

### Main Characters
| Japanese | Korean | Romanization |
|----------|--------|--------------|
| エルク | 엘크 | Elk |
| リーザ | 리자 | Lieza |
| シャンテ | 샨테 | Shante |
| ポコ | 포코 | Poco |
| トッシュ | 토슈 | Tosh |
| ゴーゲン | 고겐 | Gogen |
| シュウ | 슈우 | Shu |
| ククル | 쿠쿠루 | Kukuru |
| グルガ | 그루가 | Gruga |
| アーク | 아크 | Arc |

### Places
| Japanese | Korean | Romanization |
|----------|--------|--------------|
| ロマリア | 로말리아 | Romalia |
| アルディア | 알디아 | Aldia |
| プロディアス | 프로디아스 | Prodias |
| ミルマーナ | 밀마나 | Milmana |
| スメリア | 스메리아 | Smeria |
| パレンシア | 팔렌시아 | Palencia |

### Game Terms
| Japanese | Korean | Meaning |
|----------|--------|---------|
| 精霊 | 정령 | Spirit |
| 魔物 | 마물 | Monster |
| 聖柩 | 성궤 | Holy Ark |
| 封印 | 봉인 | Seal |
| 闘技場 | 투기장 | Arena |

## Technical Constraints

### Font System
- **Total slots:** 1,764 (441 cells × 4 bitplanes)
- **Available for Hangul:** ~1,656 (after reserving Latin/digits/symbols)
- **Cell size:** 11×11 pixels (challenging for complex Korean syllables)
- **Coverage:** ~99.9% of Korean text at 1,656 syllables

### Text Encoding
- Single-byte: `0x01-0xEE` → charID
- Two-byte: `0xF0-0xF5` + `XX` → extended charID
- Control codes: `0xFF XX XX XX` (newline, box, delay, etc.)

### STG File Format
- Fixed chunk size: 772,096 bytes (0xBC800)
- Text region: offset +0xB4000 (~34 KB per chunk)
- Text is inline in event script bytecode
- Changing text length requires offset recalculation

## File Format Preserved

Translated files maintain the exact input format:
```
0x000BC46E [0x8014] [script:C9 1E]좋아[opt][delay:15]보물을 찾자
--- context: 0x8003 -> 0x8005 ---
0x000BC500 [0x8005] [script:B2 06][box:speech]정령의 힘이여!
```

All hex offsets, opcodes, script references, and control tags are preserved exactly.

## References

- `docs/TEXT_ENCODING.md` - Complete text encoding specification
- `docs/KOREAN_TRANSLATION.md` - Feasibility analysis and Hangul coverage
- `docs/STG_analysis.md` - Stage file format and dialogue structure
- `docs/COMM_IMG_analysis.md` - Font texture layout
- `COMM_IMG_chars.md` - Complete character mapping table (1,764 entries)
