# Arc the Lad 2 Korean Translation Project

## Project Structure

```
atl2_korean_translation/
├── python/                      # Tools
│   ├── decode/                  # Text extraction tools
│   │   ├── decode_text.py       # Core decoder (--stg, --scan, --find modes)
│   │   ├── decode_all_stg.py    # Batch decode all 19 STG files
│   │   ├── decode_all_bin.py    # Decode BIN files (BEAM.DAT, SDIC, etc.)
│   │   ├── decode_yend.py       # Decode YEND.BIN ASCII credits (special)
│   │   └── generate_invalid_reports.py  # Generate invalid entry reports for all STG files
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
│   ├── translation/             # Batch translation pipeline
│   │   ├── translate_batch_prep.py   # Prepare batches of 30 lines
│   │   ├── translate_batch_run.py    # Instructions for batch translation
│   │   ├── translate_batch_merge.py  # Merge completed batches
│   │   └── extract_unique_korean.py  # Extract unique Hangul syllables
│   │
│   └── patch/                   # Patching tools
│       ├── patch_workflow.py        # Orchestrator: runs complete patch workflow
│       ├── patch_all.py             # Font + fixed-length patching
│       ├── patch_variable_length_multi.py  # Variable-length VLUT patching
│       ├── patch_korean.py          # Core patching functions
│       ├── apply_hook.py            # Apply variable-length hook to EXE
│       └── patch_bin.py             # Apply patches to disc image
│
├── scripts/                     # One-off translation scripts (legacy)
│   └── stg_translators/         # Stage-specific translation attempts
│
├── output/                      # Generated output (git-ignored)
│   ├── decoded/
│   │   ├── stg/                 # Decoded STG dialogue files
│   │   │   └── *_invalid_report.txt  # Invalid entries reports
│   │   └── bin/                 # Decoded BIN file text
│   ├── font/
│   │   ├── korean_chars/        # Generated Korean glyph PNGs
│   │   ├── COMM_IMG_KR.IMG      # Modified font with Korean
│   │   └── *.png                # Font visualizations
│   ├── patched/
│   │   ├── translation/         # Copy of translation files used for patching
│   │   ├── Arc the Lad II (Japan)/  # Patched disc image
│   │   ├── *.STG                # Patched stage files
│   │   ├── COMM.IMG             # Patched font
│   │   └── unified_charmap.txt  # Korean character mapping
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

### 4. Apply Patches (Recommended)

Use the orchestrator script to run the complete patch workflow:

```bash
# Patch S100 and SG00 (default)
python python/patch/patch_workflow.py

# Patch specific stages
python python/patch/patch_workflow.py S100 SG00 S200

# Patch all available stages
python python/patch/patch_workflow.py --all

# Output: output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).bin
```

The workflow runs these steps automatically:
0. **Validation** - Check for truncation issues and invalid control codes
1. **Copy translations** - Copy `translated/ko/*.txt` to `output/patched/translation/`
2. **patch_all.py** - Font patching + fixed-length text patching
3. **patch_variable_length_multi.py** - Variable-length VLUT for each stage
4. **apply_hook.py** - Apply variable-length hook to SCPS_100.26
5. **patch_bin.py** - Apply all patches to disc image

The patching scripts read from `output/patched/translation/` to ensure the exact translations used are preserved alongside the patched game files.

### 4b. Manual Patching (Alternative)

If you need more control, run each step manually:

```bash
# Step 1: Font + fixed-length patching
python python/patch/patch_all.py

# Step 2: Variable-length patching (per stage)
python python/patch/patch_variable_length_multi.py S100
python python/patch/patch_variable_length_multi.py SG00

# Step 3: Apply hook
python python/patch/apply_hook.py --variable-length-multi

# Step 4: Apply to disc image
python python/patch/patch_bin.py "output/patched/Arc the Lad II (Japan)/Arc the Lad II (Japan).bin"
```

## Translation Status

### STG Files (Main Story)

| File | Strings | Translated | Invalid | Status |
|------|---------|------------|---------|--------|
| S100.STG | 1,309 | 1,309 | - | **Translated** |
| SG00.STG | 2,391 | 2,391 | - | **Translated** |
| S200.STG | 2,040 | 1,975 | 65 | **Translated** |
| Other STG (16 files) | ~15,000 | - | - | Pending |

### Non-STG Files

| File | Entries | Description | Status |
|------|---------|-------------|--------|
| SCPS_100.26 | 1,735 | System messages, monsters, skills, char names (2 tables) | **Translated** |
| SDIC.BIN | 220 | Profiles, monster descriptions | **Translated** |
| YGUILD.BIN | 352 | Guild quest descriptions | **Translated** |
| SMITH.BIN | 598 | Equipment effects | **Translated** |
| BEAM.DAT | 3,274 | Battle/event dialogues, char names (2 tables) | **Translated** |
| YSHOP.BIN | 1 | Shop/item text | Pending |
| YPROP.BIN | 5 | Item descriptions | Pending |
| YSEG.BIN | 2 | Character text | Pending |
| YEND.BIN | 155 | ASCII credits (English) | N/A |
| CHA.BIN | 0 | Character data | N/A |

**Note:** SCPS_100.26 and BEAM.DAT each contain two duplicate character name tables that must both be patched for correct display.

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
- **Available for Hangul:** ~1,682 (after reserving uppercase Latin/digits/symbols; lowercase a-z repurposed)
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

## STG Invalid Entries Report

Each decoded STG file must have an accompanying invalid entries report at `output/decoded/stg/S*_STG_invalid_report.txt`. This report documents all decoded entries that should be **excluded** from translation because they are not valid dialogue.

### Why Invalid Reports Are Required

The decoder (`decode_text.py`) extracts text from binary STG data using heuristics. Some decoded entries are false positives — MIPS opcodes, binary data, or debug messages misinterpreted as text. These must be identified, excluded from translation, and documented so that:

1. The patcher knows which entries are intentionally missing
2. Future reviewers can verify no real dialogue was accidentally skipped
3. Partial decodes (truncated first character) are tracked even when included in translation

### Report Format

```
# S200.STG Invalid Entries Report
# Total dialogues: 2040
# Invalid entries excluded from translation: 65
# Partial decodes included in translation: 15

## Category 1: Garbage / MIPS Opcodes (51 entries)
## These are misinterpreted MIPS opcodes or binary data, not actual dialogue.

  Line 302:  0x00170936 [0x00B4] [script:0F 19]もあ地ゲ
  Line 303:  0x00170A00 [0x00B4] [script:74 19]もあ水ゲ

## Category 2: Single Character Fragments (10 entries)
## Decoder artifacts — single characters with no meaningful dialogue content.

  Line 1244: 0x003A6000 [0x8005] [script:0C 39]な

## Category 3: Debug / Developer Messages (4 entries)
## Left by developers for internal testing. Not meant for players.

  Line 1467: 0x003AC4D8 [0xFFFE] [script:93 3B]修正しましたので感想をください
    → "We've made fixes, please give us your feedback"

## Category 4: Partial Decodes (15 entries)
## INCLUDED in translation with the missing character(s) restored where possible.

  Line 340:  0x001725B9 [0x800A] [script:00 0A]んな所に何の用だい？
    → Missing そ → そんな所に何の用だい？ (What business do you have here?)
```

### Invalid Entry Categories

| Category | Description | Action |
|----------|-------------|--------|
| **Garbage / MIPS Opcodes** | Binary data misinterpreted as kana (e.g., `もあ煙か`, `ギギギギ`, `ぺデデ`). Common patterns: `もあXデ`, `XギXギ`, repeating chars. | **Exclude** from translation |
| **Single Character Fragments** | Single character decoder artifacts (e.g., `な`, `J`, `ぱ`). No meaningful content. | **Exclude** from translation |
| **Debug / Developer Messages** | Internal developer notes left in the game data (e.g., `デバック用だよ` = "This is for debugging"). | **Exclude** from translation |
| **Partial Decodes** | Valid dialogue with truncated first character(s) due to decoder offset issues. The missing character can usually be inferred from context. | **Include** in translation (restore missing chars), **document** in report |

### Identifying Garbage Entries

Common signatures of garbage (MIPS opcodes decoded as text):

- `もあ` prefix followed by kanji + `デ`/`ゲ`/`ギ` (VM opcodes `XX 01` → "Xあ", `XX 8C` → "Xデ")
- Repeating katakana patterns: `ギギギギ`, `ッギッギ`, `ぺデデ`
- Random mix of kana with no grammatical structure
- `煙` (smoke kanji) mixed with kana fragments
- Single uppercase ASCII letters (`J`, `I`, `Z`) mixed with kana

### Generating Reports

```bash
# Generate invalid entry reports for all 19 STG files
python python/decode/generate_invalid_reports.py

# Output: output/decoded/stg/*_STG_invalid_report.txt
```

### Report File Naming

| Decoded File | Report File |
|-------------|-------------|
| `output/decoded/stg/S100_STG.txt` | `output/decoded/stg/S100_STG_invalid_report.txt` |
| `output/decoded/stg/S200_STG.txt` | `output/decoded/stg/S200_STG_invalid_report.txt` |
| `output/decoded/stg/SG00_STG.txt` | `output/decoded/stg/SG00_STG_invalid_report.txt` |

## Non-STG Translation File Format

Translation files for non-STG binary files (`translated/ko/*_BIN.txt`, `translated/ko/SCPS_100_26.txt`) must also mirror the decoded source format exactly.

### Non-STG Format Specification

```text
# SCPS_100.26 — 1717 strings (Korean translations)   <- Header comment
                                                      <- Blank line
  0x000D2708 [   7] 엘리멘탈                          <- Entry line
  0x000D2710 [   7] 빙염귀
  0x000D2718 [  11] 엘리멘탈 마스터
```

### Entry Line Components

| Component | Format | Example | Description |
|-----------|--------|---------|-------------|
| Indent | 2 spaces | `  ` | Fixed indentation |
| Offset | `0xXXXXXXXX` | `0x000D2708` | File byte offset (uppercase hex) |
| Length | `[NNNN]` | `[   7]` | Original Japanese byte length (right-justified, 4 chars) |
| Text | Korean text | `엘리멘탈` | Translated text |

### Important Notes

1. **Keep the length field from the decoded source** - The `[length]` value shows the original Japanese text's byte length. The patcher uses this for validation and will warn if Korean translations exceed the original slot size.

2. **Length validation** - Before patching, the patcher validates that each Korean translation fits within the original slot. If a translation is too long, a warning is shown and the text will be truncated.

3. **Preserve untranslated entries** - If a string is not translated, keep the original Japanese text.

4. **No section comments required** - Unlike the CSV format, the proper format doesn't need section headers like `# ===== MONSTERS =====`.

### Converting from CSV Format

If you have translations in simplified CSV format (`offset,korean_text`):

```bash
# Convert a specific file
python python/translation/convert_bin_format.py SDIC_BIN

# Convert all available files
python python/translation/convert_bin_format.py --all
```

This merges translations with the decoded source to produce the correct format with length fields.

Available file keys: `SCPS_100_26`, `SDIC_BIN`, `YGUILD_BIN`, `SMITH_BIN`, `BEAM_DAT`

### Example Complete File Structure

```text
# SCPS_100.26 — 1717 strings (Korean translations)

  0x000D2700 [   2] こ
  0x000D2702 [   2] ？
  0x000D2708 [   7] 엘리멘탈
  0x000D2710 [   7] 빙염귀
  ...
  0x000D7990 [  35] [opt]메모리카드를 체크합니다[br]　　잠시만 기다려주세요
```

The format mirrors the decoded file exactly, with Korean text replacing Japanese where translated.

## References

- `docs/TEXT_ENCODING.md` - Complete text encoding specification
- `docs/KOREAN_TRANSLATION.md` - Feasibility analysis and Hangul coverage
- `docs/STG_analysis.md` - Stage file format and dialogue structure
- `docs/COMM_IMG_analysis.md` - Font texture layout
- `COMM_IMG_chars.md` - Complete character mapping table (1,764 entries)
