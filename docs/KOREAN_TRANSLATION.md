# Arc the Lad 2 -- Korean Translation Feasibility Analysis

This document analyzes the feasibility of translating Arc the Lad 2 from Japanese to Korean, given the constraints of the PS1 font system.

## Font System Constraints

The game's font is stored in `COMM.IMG` as a 4bpp bitplane texture (see `TEXT_ENCODING.md` for full details).

| Property | Value |
|---|---|
| Usable cells | 440 (cell 440 is the 16x16 cursor, not available for text) |
| Bitplanes per cell | 4 |
| Total character slots | 440 x 4 = **1,760** |
| Cell size | 11x11 pixels |
| Cell stride | 12 pixels (11px + 1px padding) |

Each bitplane of each cell holds one character glyph. At runtime, the PS1 GPU's CLUT selects which bitplane to render, allowing 4 characters to share one cell.

## Japanese Character Usage (STG Dialogues)

Analysis of all 19 STG stage files extracted via `--stg` mode (19,568 dialogue strings, ~356K characters):

| Category | Unique Chars | Occurrences | Notes |
|---|---|---|---|
| Hiragana | 80 | 227,147 | Full set (あ-ん + voiced/small variants) |
| Katakana | 82 | 37,176 | Full set (ア-ン + voiced/small variants) |
| Kanji | 1,094 | 58,802 | Long tail: 88 appear only once |
| Latin uppercase | 26 | 1,083 | A-Z |
| Latin lowercase | 26 | 756 | a-z |
| Digits | 10 | 776 | 0-9 |
| Symbols/punctuation | 26 | 23,264 | 、。！？…ー etc. |
| **Total** | **1,344** | **~349K** | |

The font contains ~1,704 character entries, but STG dialogues only reference 1,344 unique characters. The remaining ~360 entries include characters used in non-STG files (SCPS_100.26, SDIC.BIN, SMITH.BIN, etc.) or unused slots.

### Most Frequent Kanji (Top 20)

| Rank | Kanji | Count | | Rank | Kanji | Count |
|---|---|---|---|---|---|---|
| 1 | 地 | 8,226 | | 11 | 大 | 305 |
| 2 | 人 | 912 | | 12 | 力 | 280 |
| 3 | 何 | 714 | | 13 | 行 | 279 |
| 4 | 前 | 671 | | 14 | 王 | 267 |
| 5 | 私 | 598 | | 15 | 方 | 261 |
| 6 | 来 | 402 | | 16 | 言 | 256 |
| 7 | 事 | 400 | | 17 | 思 | 251 |
| 8 | 気 | 371 | | 18 | 分 | 244 |
| 9 | 者 | 331 | | 19 | 見 | 232 |
| 10 | 中 | 312 | | 20 | 世 | 227 |

Note: 地 count is inflated because it doubles as an element icon (地水火風) in battle-related text.

## Korean Font Budget

For a Korean translation, the 1,760 font slots must be divided between Hangul syllable blocks and all other characters:

| Purpose | Slots | Notes |
|---|---|---|
| Latin uppercase A-Z | 26 | Character names, abbreviations |
| Latin lowercase a-z | 26 | Item names, proper nouns |
| Digits 0-9 | 10 | Amounts, stats |
| UI glyphs | 12 | +1..+9, SS, element icons (地水火風) |
| Symbols & punctuation | 30 | 、。！？…ー（）「」／＊～ etc. |
| **Reserved subtotal** | **104** | |
| **Available for Hangul** | **1,656** | |

The reserved count of 104 is conservative. Reducing symbols (e.g., dropping rarely-used arrows or card suits) could free additional slots.

## Korean Hangul Coverage Analysis

Modern Korean has 11,172 possible syllable blocks (19 initial consonants x 21 medial vowels x 28 final consonant options). However, real Korean text uses a heavily skewed subset:

| Syllable Count | Coverage | Fits Budget? | Assessment |
|---|---|---|---|
| 500 | ~93% | Yes | Barely functional -- common words missing |
| 800 | ~97% | Yes | Basic -- occasional awkward rewording needed |
| 1,000 | ~98.5% | Yes | Good -- only rare words affected |
| 1,200 | ~99.3% | Yes | Very good -- exotic terms only |
| 1,500 | ~99.8% | Yes | Excellent -- nearly all text representable |
| **1,656** | **~99.9%** | **Yes** | **Budget limit -- near-complete coverage** |
| 2,000 | ~99.97% | No | Essentially complete for any Korean text |

At 1,656 Hangul slots, approximately 99.9% of general Korean text is representable. For reference, Korean PS1 and SNES fan translations have typically required 1,000-1,500 unique syllable blocks for full RPG scripts.

## Feasibility Assessment

**The translation is feasible** using the existing font system without modifying any game code. Only the font texture (`COMM.IMG`) and text data (STG/BIN files) need to change.

### What Works

- **Slot count**: 1,656 Hangul slots provide ~99.9% coverage, well above the 1,000-1,500 typically needed for RPG translations.
- **No code changes**: The rendering engine (`SDIC.BIN`) treats characters as opaque charID lookups. Replacing the Japanese glyphs with Korean glyphs in `COMM.IMG` and updating the text byte sequences in data files is sufficient.
- **Control codes are language-agnostic**: All FF-prefix control codes (newlines, dialogue boxes, delays, name insertions) work identically regardless of which glyphs the charIDs map to.

### Challenges

1. **11x11 pixel cell size**: Korean syllable blocks (e.g., 뿟) pack 2-3 structural components into one character. At 11x11 pixels, legibility requires a carefully designed pixel font. Complex syllables with final consonants (받침) are the hardest to render clearly. This is the primary practical challenge.

2. **Translator syllable discipline**: The ~0.1% of syllables outside the top 1,656 must be avoided. The translator works against a fixed syllable inventory and rephrases lines that use rare syllables. This is standard practice for retro Korean fan translations and only affects unusual vocabulary.

3. **Non-STG text**: System menus (SCPS_100.26), item descriptions (SMITH.BIN), the dialogue dictionary (SDIC.BIN), guild/shop text (YGUILD.BIN, YSHOP.BIN), and battle text (BEAM.DAT, CHA.BIN) also need translation. These share the same font, so the syllable inventory must cover all files. Menu and item text typically uses common vocabulary, so this should not significantly expand the required syllable set.

4. **Line length**: Korean text can be more compact than Japanese (no hiragana padding) but syllable blocks are wider than kana at small pixel sizes. Line wrapping may need adjustment for some dialogue strings.

### Alternative Approach: Jamo Composition

Instead of precomposed syllable blocks, the font could store individual Hangul jamo components:

| Component | Count | Examples |
|---|---|---|
| Initial consonants (초성) | 19 | ㄱ ㄲ ㄴ ㄷ ㄸ ㄹ ㅁ ㅂ ㅃ ㅅ ㅆ ㅇ ㅈ ㅉ ㅊ ㅋ ㅌ ㅍ ㅎ |
| Medial vowels (중성) | 21 | ㅏ ㅐ ㅑ ㅒ ㅓ ㅔ ㅕ ㅖ ㅗ ㅘ ㅙ ㅚ ㅛ ㅜ ㅝ ㅞ ㅟ ㅠ ㅡ ㅢ ㅣ |
| Final consonants (종성) | 27 | ㄱ ㄲ ㄳ ㄴ ㄵ ㄶ ㄷ ㄹ ... ㅎ |
| **Total** | **67** | |

This uses only 67 slots (vs. 1,656) and gives 100% syllable coverage. However, it requires **modifying the MIPS rendering code** in `SDIC.BIN` (render function at RAM `0x80027E90`) to compose 2-3 jamo into a single character cell at draw time. This is significantly more complex but eliminates all syllable inventory constraints.

## Translation Scope

### Files to Translate

| File | Content | Priority |
|------|---------|----------|
| S*.STG (19 files) | Stage dialogue (19,568 strings) | High |
| SCPS_100.26 | System messages, menu text, item/skill names, descriptions, location names (~960 strings) | High |
| SDIC.BIN | Character profiles, monster encyclopedia (555 strings) | Medium |
| SMITH.BIN | Item/equipment descriptions (628 strings) | Medium |
| YGUILD.BIN | Guild quest text (363 strings) | Medium |
| BEAM.DAT | Battle/event text | Medium |

### Files Excluded from Translation

| File | Reason |
|------|--------|
| **YEND.BIN** | Ending credits. Contains 155 ASCII staff name/role strings in romanized English (e.g., "Producer:", "Ryoji Akagawa(SCEI)"). These are factual credits that do not need localization. Additionally, YEND.BIN uses a separate ASCII encoding system (80-byte lookup table) rather than the game's main text encoding, so translating it would require modifying the rendering code for minimal benefit. |
| YSHOP.BIN | No embedded text (pure UI code) |
| YPROP.BIN | No embedded text (pure UI code) |
| YSEG.BIN | No embedded text (pure UI code) |
| CHA.BIN | No text (sprite archive) |
| COMM.DAT | No text (battle animation/command module, loaded at `0x80010000`) |
| COMM.SND | No text (PS1 VAB sound bank -- battle SFX and instrument samples) |
| SYSTEM.CNF | No text (PS1 boot configuration -- executable path, stack pointer, kernel params) |

## Recommended Approach

1. **Build a Korean syllable frequency table** from a reference corpus (e.g., Korean National Institute of Korean Language data) and draft a translation of the first few hundred lines.
2. **Count unique syllables** in the draft translation to validate the budget estimate.
3. **Design the 11x11 pixel Korean font** -- this is the critical path item. Test legibility with complex syllables (받침-heavy words) at native PS1 resolution.
4. **Map the top ~1,656 syllables to charIDs** in the font grid, replacing the Japanese entries.
5. **Translate and encode** each dialogue file, using `decode_text.py` tooling (with a Korean encode table) to produce the binary output.

## Tools

- `python decode_text.py <file> --stg` -- extract all STG dialogues with template-driven method
- `python decode_text.py <file> --stg --find "text"` -- filter STG dialogues by content
- Extracted dialogue files: `translated/S*_STG.txt` (18 files, 19,568 strings)
