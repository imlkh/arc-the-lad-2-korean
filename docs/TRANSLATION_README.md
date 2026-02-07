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

### STG Files (Main Story)

| File | Strings | Mode | Patched | Status |
|------|---------|------|---------|--------|
| S100.STG | 1,261 | variable | 1,053 | **Translated** |
| SG00.STG | 1,470 | variable | 685 | **Translated** |
| Other STG (17 files) | ~17,000 | - | - | Pending |

### Non-STG Files

| File | Total Strings | Menu [opt] | Description | Status |
|------|---------------|------------|-------------|--------|
| **BEAM.DAT** | 2,753 | 686 | Battle/event dialogues | **Missing** |
| **YGUILD.BIN** | 352 | 109 | Guild quest descriptions | **Missing** |
| **SMITH.BIN** | 598 | 15 | Equipment effects | **Missing** |
| **SDIC.BIN** | 220 | 0 | Profiles, monster descriptions | **Missing** |
| SCPS_100.26 | 84 | 3 | System messages | Partial (22 translated) |
| YSHOP.BIN | 1 | 0 | Shop/item text | Pending |
| YPROP.BIN | 5 | 0 | Item descriptions | Pending |
| YSEG.BIN | 2 | 0 | Character text | Pending |
| YEND.BIN | 155 | 0 | ASCII credits (English) | N/A |
| CHA.BIN | 0 | 0 | Character data | N/A |

**High priority for menu translation:** BEAM.DAT (686 menu options), YGUILD.BIN (109 quest menus)

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

## STG Translation File Format

Translation files for STG dialogues (`translated/ko/S*_STG.txt`) must mirror the decoded source format exactly, with only the Japanese text replaced by Korean.

### Format Specification

```
# S100.STG — 1165 dialogues, 1087 templates (...)    <- Header comment
                                                      <- Blank line
  0x000B4516 [0x8006] [script:16 07]큰 도시네          <- Dialogue line
  0x000B4564 [0x8006] [script:44 07]알디아의 수도니까
  --- context: 0x8006 -> 0x8005 ---                   <- Context change marker
  0x000B45C8 [0x8005] [script:72 07]여기가 내 아파트야
```

### Dialogue Line Components

| Component | Format | Example | Description |
|-----------|--------|---------|-------------|
| Indent | 2 spaces | `  ` | Fixed indentation |
| Offset | `0xXXXXXXXX` | `0x000B4516` | File byte offset (uppercase hex) |
| Speaker | `[0xXXXX]` | `[0x8006]` | Speaker opcode |
| Script | `[script:XX XX]` | `[script:16 07]` | Script bytecode reference |
| Text | Korean text | `큰 도시네` | Translated dialogue with control codes |

### Speaker Opcodes

| Opcode | Speaker |
|--------|---------|
| `0x8005` | Elk (엘크) |
| `0x8006` | Lieza (리자) |
| `0x8007-0x800E` | Various NPCs |
| `0x00A0` | Padding region dialogue |
| `0x00A9` | Orphan menu |
| `0x00B0` | Event script dialogue |
| `0x00B4` | Bare dialogue (location, battle msg) |
| `0xFFFE` | Generic NPC/narrator |

### Control Codes (preserved in Korean text)

| Code | Meaning | Example |
|------|---------|---------|
| `[br]` | Line break | `안녕[br]반가워` |
| `[opt]` | Menu option | `[opt]예[br][opt]아니오` |
| `[delay:XX]` | Pause | `[delay:15]잠깐…` |
| `[box:system]` | System dialog | `[box:system]저장할까요?` |
| `[box:close]` | Close box | `[box:close]알겠습니다` |

## Translation Guidelines

### Special Characters - KEEP UNCHANGED

When translating Japanese text to Korean, **preserve the original Japanese special characters** instead of converting them to ASCII equivalents. This saves bytes and ensures proper display with the game's font glyphs.

| Japanese | Keep As-Is | DON'T Use | Reason |
|----------|------------|-----------|--------|
| `…` (ellipsis) | `…` | `...` | Saves 5 bytes, proper glyph |
| `、` (comma) | `,` or `、` | - | Both work |
| `。` (period) | `。` | - | Use for sentence endings |
| `！` (exclamation) | `！` | `!` | Both work, `！` is wider |
| `？` (question) | `？` | `?` | Both work, `？` is wider |
| `「」` (quotes) | `「」` | `""` | Japanese quote style |
| `『』` (double quotes) | `『』` | - | For nested quotes |
| `ー` (long vowel) | `ー` | `-` | For katakana words |
| `・` (middle dot) | `・` | `·` | Separator in names |

### Automatic Normalization

The patcher automatically converts some sequences, but it's better to use the correct character from the start:

| Input | Converted To | CharID | Notes |
|-------|--------------|--------|-------|
| `...` | `…` | 229 | Automatic conversion |
| `..` | `…` | 229 | Automatic conversion |

### Example Translations

**GOOD** (preserves special characters):
```
Japanese: なんで、みんなをころすんだ！
Korean:   왜, 모두를 죽이는 거야！

Japanese: そうか…やっぱりな
Korean:   그렇군…역시나

Japanese: ここは「神殿」です
Korean:   여기는「신전」입니다
```

**BAD** (uses ASCII equivalents):
```
Japanese: そうか…やっぱりな
Korean:   그렇군...역시나     <- Uses ... instead of …

Japanese: どうする？
Korean:   어떻게 할래?        <- Uses ? instead of ？
```

### Byte-Saving Tips

Korean translations often end up longer than Japanese. To stay within byte limits:

1. **Use ellipsis `…` instead of `...`** - Saves 5 bytes per occurrence
2. **Use shorter synonyms** - 하지만 → 근데, 그러나 → 허나
3. **Simplify particles** - ~하는 것이다 → ~한다
4. **Use contractions** - 것은 → 건, 것이 → 게

### Characters Available in Font

The game font includes these Japanese punctuation marks that can be used in Korean text:

| CharID | Character | Description |
|--------|-----------|-------------|
| 228 | `、` | Japanese comma |
| 229 | `…` | Ellipsis (USE THIS!) |
| 230 | `ー` | Long vowel mark |
| 231 | `「` | Left quote |
| 232 | `」` | Right quote |
| 233 | `『` | Left double quote |
| 234 | `』` | Right double quote |
| 235 | `・` | Middle dot |
| 236 | `。` | Japanese period |
| 237 | `！` | Full-width exclamation |
| 238 | `？` | Full-width question |
| 247 | `,` | ASCII comma |
| 248 | `.` | ASCII period |

### Context Change Markers

```
--- context: 0x8006 -> 0x8005 ---
```
These indicate speaker transitions and must be preserved exactly as in the decoded source.

### Converting from Simplified Format

If you have translations in simplified format (`offset,korean_text`):

```bash
python python/convert_translation_format.py S200
```

This merges translations with the decoded source metadata to produce the correct format.

### Example Complete Entry

```
  0x000BC46E [0x8014] [script:C9 1E]좋아[opt][delay:15]보물을 찾자
  --- context: 0x8003 -> 0x8005 ---
  0x000BC500 [0x8005] [script:B2 06][box:speech]정령의 힘이여!
```

All hex offsets, opcodes, script references, and control codes are preserved exactly from the decoded source.

## References

- `docs/TEXT_ENCODING.md` - Complete text encoding specification
- `docs/KOREAN_TRANSLATION.md` - Feasibility analysis and Hangul coverage
- `docs/STG_analysis.md` - Stage file format and dialogue structure
- `docs/COMM_IMG_analysis.md` - Font texture layout
- `COMM_IMG_chars.md` - Complete character mapping table (1,764 entries)
