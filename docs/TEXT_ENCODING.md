# Arc the Lad 2 -- Text Encoding Reference

This document describes how Arc the Lad 2 (PS1) encodes in-game dialogue and menu text. The font is stored in `COMM.IMG` as a 4bpp bitplane texture, and text strings use a variable-length byte encoding to reference individual characters by ID.

## Font Layout in COMM.IMG

The font occupies a 256x256 pixel region in the top-left of `COMM.IMG`, organized as a 21x21 grid of 12x12 pixel cells (11x11 glyph + 1px right/bottom margin).

Each cell contains **4 characters overlaid** across 4 bitplanes of the 4bpp pixel data. At runtime, the PS1 GPU's CLUT (Color Look-Up Table) selects which bitplane is visible, allowing 4 characters to share one cell.

| Property | Value |
|---|---|
| Grid size | 21 columns x 21 rows = 441 cells |
| Cell size | 12x12 pixels: 11x11 glyph + 1px margin (cell 440 is 16x16) |
| Bitplanes per cell | 4 |
| Total character slots | 441 x 4 = 1,764 |
| Non-empty characters | ~1,704 |
| File row width | 896 bytes per scanline |
| 4bpp encoding | Low nibble = left pixel, high nibble = right pixel |

### Character ID Formula

Each character is addressed by a single integer **charID** (1-based):

```
charID = 1 + (row * 21 + col) * 4 + bitplane
```

Inverse (charID to grid position):

```
adjusted = charID - 1
cell     = adjusted / 4
bitplane = adjusted % 4
row      = cell / 21
col      = cell % 21
```

The rendering code in `SDIC.BIN` uses an equivalent formulation dividing by 84 (= 21 columns x 4 bitplanes):

```
adjusted = charID - 1
row      = adjusted / 84
col_rem  = adjusted % 84
col      = col_rem / 4
bitplane = col_rem % 4
u        = col * 12      (texture X)
v        = row * 12      (texture Y)
```

## Text Byte Encoding

Text strings are null-terminated byte streams using a variable-length encoding:

| Byte Range | Encoding | CharID Range | Description |
|---|---|---|---|
| `0x00` | -- | -- | Null terminator |
| `0x01`-`0xEE` | Single byte | 1-238 | Direct charID lookup |
| `0xEF` | Control code | -- | Choice option prefix |
| `0xF0 XX`-`0xFF XX` | Two bytes | 239-4304 | Extended charID |

### Two-Byte Encoding

For characters with charID >= 239:

```
first_byte  = 0xF0 + (charID - 239) / 255
second_byte = (charID - 239) % 255
```

Decoding:

```
charID = (first_byte - 0xF0) * 255 + second_byte + 239
```

### Control Codes

All control sequences use the `FF` prefix byte followed by a sub-command byte and two parameter bytes (4 bytes total). The dispatcher is at RAM `0x8015178C` in the main executable, indexing into a 16-entry jump table at `0x800C1C40`.

| Byte(s) | Meaning |
|---|---|
| `00` | Null / string terminator |
| `EF` | Choice option prefix (next bytes are the selectable option text) |

#### FF Control Sequences (4 bytes: `FF sub param1 param2`)

| Code | Meaning | Occurrences |
|---|---|---|
| `FF 01 XX XX` | Set text timing / delay mode | -- |
| `FF 02 XX XX` | Load named string by ID | -- |
| `FF 03 XX 01` | Text delay (XX = frame count: 0B=short, 15=medium, 1F=long) | 238 |
| `FF 04 XX XX` | Menu option marker | -- |
| `FF 05 01 01` | Newline (Y += line height, reset X to left margin) | ~5,000+ |
| `FF 06 XX XX` | Display controller button icon | -- |
| `FF 07 XX XX` | Display number from variable (e.g., gold amount) | -- |
| `FF 08 XX XX` | Dialogue box command (see sub-types below) | ~2,600 |
| `FF 09 XX XX` | Load reference by ID | -- |
| `FF 0A XX XX` | Set variable / flag | -- |
| `FF 0B XX XX` | Insert item name string | -- |
| `FF 0C XX XX` | Insert stat level glyph (+1..+9) | 10 |
| `FF 0D XX XX` | Insert variable name string | -- |
| `FF 0E XX XX` | Insert formatted runtime string | -- |
| `FF 0F XX XX` | Insert inline sprite/graphic | -- |
| `FF 10 XX XX` | Insert character name (e.g., battle arena commentary) | -- |

#### FF 08: Dialogue Box Sub-Types

The `FF 08` command controls dialogue box lifecycle. The first parameter byte selects the sub-type:

| Code | Sub-Type | Occurrences | Description |
|---|---|---|---|
| `FF 08 01 01` | System box | 1,626 | Opens a system text box (items, menus, switches) |
| `FF 08 02 01` | Close / transition | 291 | Closes the current dialogue box |
| `FF 08 03 01` | Character speech | 622 | Opens a character speech bubble (story dialogue) |
| `FF 08 05 01` | Narration | 42 | Centered narration text (cutscenes) |
| `FF 08 07 01` | **Page break / cursor wait** | 60 | Shows cursor glyph, waits for button press, then continues |

#### FF 0C: Insert Stat Level Glyph

The `FF 0C` handler constructs a single two-byte character string from the UI glyph region of the font (cells 420–429: +1 through +9, SS). It writes a 3-byte inline string `[0xF5, computed_byte, 0x00]` into the dialogue struct's text buffer.

The charID is computed as: `charID = 1680 + param1` (when param2 = 0x01).

| Code | CharID | Glyph |
|---|---|---|
| `FF 0C 01 01` | 1681 | +1 |
| `FF 0C 05 01` | 1685 | +2 |
| `FF 0C 09 01` | 1689 | +3 |

Since all 4 bitplanes of cells 420–428 are identical, every 4 consecutive charIDs map to the same visual glyph. This code appears **only as standalone string table entries** (10 entries at file offset `0x0D4F40` in SCPS_100.26), not inline in dialogue. The battle/level-up system indexes into this table to display stat modifier values.

#### FF 0E: Insert Formatted Runtime String

The `FF 0E` handler reads a pointer chain from the dialogue context structure (`context[100]->field[136]`), then copies a string from a runtime lookup table (RAM `0x801AE5B0`) into the text buffer. If the pointer is null, a default string from global data is used instead.

This code does **not appear in any dialogue text**. It is used by subsystems (likely the battle arena commentary or menu system) to insert dynamic game-state text that only exists at runtime — such as the current arena name, player rank, or similar context-dependent information.

Handler address: `0x80151A5C` → calls subroutine at `0x80151F14`.

#### FF 0F: Insert Inline Sprite/Graphic

The `FF 0F` handler allocates a sprite object (via `0x80134A58`), positions it relative to the current text rendering coordinates, and registers a render callback (`0x8014F810`) with data from a lookup table at RAM `0x801B70A6`. The parameter value selects which graphic to display, with a ±32 offset transformation (bit 5 toggle).

This code does **not appear in any dialogue text**. Like `FF 0E`, it is used by subsystems to embed small graphical elements (icons, indicators) within rendered text at runtime.

Handler address: `0x80151A74` → calls subroutine at `0x80151D70`.

#### Cursor Glyph (Cell 440)

The cursor icon is stored in cell 440 (row 20, col 20) of the COMM.IMG font grid at 16x16 pixels (larger than the standard 12x12 cells). It is identical across all 4 bitplanes.

The cursor is **not referenced by charID in text data**. Instead, the dialogue box system renders it automatically as a UI overlay when:

1. **End of string** -- After the last character is displayed, the cursor appears at the bottom-right of the box until the player presses a button.
2. **Page break** (`FF 08 07 01`) -- When a sentence is too long for a single dialogue box, this control code splits it. The cursor appears, the player presses a button, the box clears, and the remaining text continues in a fresh box.

Most multi-page conversations are handled by the **event script engine** sequencing separate null-terminated strings. The `FF 08 07 01` inline page break is used sparingly for dramatic effect, often paired with trailing dots:

```
エルクよ [FF 08 07 01] ・・・・・
```
(Displays "Elk..." with cursor, waits, then continues on next page.)

## Single-Byte Character Table (0x01-0xEE)

### Hiragana (0x01-0x50)

| ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 01 | あ | | 2 | 02 | い | | 3 | 03 | う | | 4 | 04 | え |
| 5 | 05 | お | | 6 | 06 | か | | 7 | 07 | き | | 8 | 08 | く |
| 9 | 09 | け | | 10 | 0A | こ | | 11 | 0B | さ | | 12 | 0C | し |
| 13 | 0D | す | | 14 | 0E | せ | | 15 | 0F | そ | | 16 | 10 | た |
| 17 | 11 | ち | | 18 | 12 | つ | | 19 | 13 | て | | 20 | 14 | と |
| 21 | 15 | な | | 22 | 16 | に | | 23 | 17 | ぬ | | 24 | 18 | ね |
| 25 | 19 | の | | 26 | 1A | は | | 27 | 1B | ひ | | 28 | 1C | ふ |
| 29 | 1D | へ | | 30 | 1E | ほ | | 31 | 1F | ま | | 32 | 20 | み |
| 33 | 21 | む | | 34 | 22 | め | | 35 | 23 | も | | 36 | 24 | や |
| 37 | 25 | ゆ | | 38 | 26 | よ | | 39 | 27 | ら | | 40 | 28 | り |
| 41 | 29 | る | | 42 | 2A | れ | | 43 | 2B | ろ | | 44 | 2C | わ |
| 45 | 2D | を | | 46 | 2E | ん | | 47 | 2F | が | | 48 | 30 | ぎ |
| 49 | 31 | ぐ | | 50 | 32 | げ | | 51 | 33 | ご | | 52 | 34 | ざ |
| 53 | 35 | じ | | 54 | 36 | ず | | 55 | 37 | ぜ | | 56 | 38 | ぞ |
| 57 | 39 | だ | | 58 | 3A | ぢ | | 59 | 3B | づ | | 60 | 3C | で |
| 61 | 3D | ど | | 62 | 3E | ば | | 63 | 3F | び | | 64 | 40 | ぶ |
| 65 | 41 | べ | | 66 | 42 | ぼ | | 67 | 43 | ぱ | | 68 | 44 | ぴ |
| 69 | 45 | ぷ | | 70 | 46 | ぺ | | 71 | 47 | ぽ | | 72 | 48 | ぁ |
| 73 | 49 | ぃ | | 74 | 4A | ぅ | | 75 | 4B | ぇ | | 76 | 4C | ぉ |
| 77 | 4D | ゃ | | 78 | 4E | ゅ | | 79 | 4F | ょ | | 80 | 50 | っ |

### Katakana (0x51-0xA0)

| ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 81 | 51 | ア | | 82 | 52 | イ | | 83 | 53 | ウ | | 84 | 54 | エ |
| 85 | 55 | オ | | 86 | 56 | カ | | 87 | 57 | キ | | 88 | 58 | ク |
| 89 | 59 | ケ | | 90 | 5A | コ | | 91 | 5B | サ | | 92 | 5C | シ |
| 93 | 5D | ス | | 94 | 5E | セ | | 95 | 5F | ソ | | 96 | 60 | タ |
| 97 | 61 | チ | | 98 | 62 | ツ | | 99 | 63 | テ | | 100 | 64 | ト |
| 101 | 65 | ナ | | 102 | 66 | ニ | | 103 | 67 | ヌ | | 104 | 68 | ネ |
| 105 | 69 | ノ | | 106 | 6A | ハ | | 107 | 6B | ヒ | | 108 | 6C | フ |
| 109 | 6D | ヘ | | 110 | 6E | ホ | | 111 | 6F | マ | | 112 | 70 | ミ |
| 113 | 71 | ム | | 114 | 72 | メ | | 115 | 73 | モ | | 116 | 74 | ヤ |
| 117 | 75 | ユ | | 118 | 76 | ヨ | | 119 | 77 | ラ | | 120 | 78 | リ |
| 121 | 79 | ル | | 122 | 7A | レ | | 123 | 7B | ロ | | 124 | 7C | ワ |
| 125 | 7D | ヲ | | 126 | 7E | ン | | 127 | 7F | ガ | | 128 | 80 | ギ |
| 129 | 81 | グ | | 130 | 82 | ゲ | | 131 | 83 | ゴ | | 132 | 84 | ザ |
| 133 | 85 | ジ | | 134 | 86 | ズ | | 135 | 87 | ゼ | | 136 | 88 | ゾ |
| 137 | 89 | ダ | | 138 | 8A | ヂ | | 139 | 8B | ヅ | | 140 | 8C | デ |
| 141 | 8D | ド | | 142 | 8E | バ | | 143 | 8F | ビ | | 144 | 90 | ブ |
| 145 | 91 | ベ | | 146 | 92 | ボ | | 147 | 93 | パ | | 148 | 94 | ピ |
| 149 | 95 | プ | | 150 | 96 | ペ | | 151 | 97 | ポ | | 152 | 98 | ァ |
| 153 | 99 | ィ | | 154 | 9A | ゥ | | 155 | 9B | エ | | 156 | 9C | ォ |
| 157 | 9D | ャ | | 158 | 9E | ュ | | 159 | 9F | ョ | | 160 | A0 | ッ |

### Latin Uppercase (0xA1-0xBA)

| ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 161 | A1 | A | | 162 | A2 | B | | 163 | A3 | C | | 164 | A4 | D |
| 165 | A5 | E | | 166 | A6 | F | | 167 | A7 | G | | 168 | A8 | H |
| 169 | A9 | I | | 170 | AA | J | | 171 | AB | K | | 172 | AC | L |
| 173 | AD | M | | 174 | AE | N | | 175 | AF | O | | 176 | B0 | P |
| 177 | B1 | Q | | 178 | B2 | R | | 179 | B3 | S | | 180 | B4 | T |
| 181 | B5 | U | | 182 | B6 | V | | 183 | B7 | W | | 184 | B8 | X |
| 185 | B9 | Y | | 186 | BA | Z | | | | | | | | |

### Latin Lowercase (0xBB-0xD4)

| ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 187 | BB | a | | 188 | BC | b | | 189 | BD | c | | 190 | BE | d |
| 191 | BF | e | | 192 | C0 | f | | 193 | C1 | g | | 194 | C2 | h |
| 195 | C3 | i | | 196 | C4 | j | | 197 | C5 | k | | 198 | C6 | l |
| 199 | C7 | m | | 200 | C8 | n | | 201 | C9 | o | | 202 | CA | p |
| 203 | CB | q | | 204 | CC | r | | 205 | CD | s | | 206 | CE | t |
| 207 | CF | u | | 208 | D0 | v | | 209 | D1 | w | | 210 | D2 | x |
| 211 | D3 | y | | 212 | D4 | z | | | | | | | | |

### Digits (0xD5-0xDE)

| ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 213 | D5 | 0 | | 214 | D6 | 1 | | 215 | D7 | 2 | | 216 | D8 | 3 |
| 217 | D9 | 4 | | 218 | DA | 5 | | 219 | DB | 6 | | 220 | DC | 7 |
| 221 | DD | 8 | | 222 | DE | 9 | | | | | | | | |

### Symbols and Punctuation (0xDF-0xEE)

| ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char | | ID | Hex | Char |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 223 | DF | 地 | | 224 | E0 | 水 | | 225 | E1 | 火 | | 226 | E2 | 風 |
| 227 | E3 | ー | | 228 | E4 | 、 | | 229 | E5 | … | | 230 | E6 | ＋ |
| 231 | E7 | ー | | 232 | E8 | ／ | | 233 | E9 | ＊ | | 234 | EA | ～ |
| 235 | EB | " | | 236 | EC | 。 | | 237 | ED | ！ | | 238 | EE | ？ |

**Note:** 地水火風 are element icons used in the battle system. The two ー entries (0xE3 and 0xE7) may represent visually distinct dash/prolonged-sound marks.

## Two-Byte Character Table (0xF0+)

Characters with charID >= 239 use two-byte encoding. The first byte is the prefix (0xF0-0xF5), and the second byte is the index within that page.

| Prefix | CharID Range | Count | Content |
|---|---|---|---|
| 0xF0 | 239-493 | 254 | Symbols (＠♦♠♥♣(）「」;), arrows, early kanji (亜-巻) |
| 0xF1 | 494-748 | 255 | Kanji (喚-才) |
| 0xF2 | 749-1003 | 255 | Kanji (災-緒) |
| 0xF3 | 1004-1258 | 255 | Kanji (切-殿) |
| 0xF4 | 1259-1513 | 255 | Kanji (虎-虫) |
| 0xF5 | 1514-1768 | 192 | Kanji (務-衛), UI glyphs (+1 through +9, SS, cursor) |

The full character-to-charID mapping is in `COMM_IMG_chars.md`. To compute the two-byte encoding for any charID >= 239:

```
first_byte  = 0xF0 + (charID - 239) / 255
second_byte = (charID - 239) % 255
```

## Dialogue Structure

### Yes/No Choice Prompts

Yes/no prompts follow a fixed byte-level pattern. Example for `ますか？` + はい/いいえ:

```
Hex                     Decoded
----                    -------
FF 08 01 01             [open system box]
...                     [question text]
1F 0D 06 EE            ますか？
FF 05 01 01             [newline]
EF                      [option prefix]
1A 02                   はい
FF 05 01 01             [newline]
EF                      [option prefix]
02 02 04                いいえ
FF 08 02 01             [close box]
00                      [null terminator]
```

This pattern was found **5,337 times** across all game files (all 19 STG stage files, BEAM.DAT, CHA.BIN, SMITH.BIN, SCPS_100.26).

### Multi-Page Dialogue

Most multi-page conversations are sequences of separate null-terminated strings, each rendered in its own dialogue box. The event script engine handles sequencing.

For inline page breaks within a single string, `FF 08 07 01` splits the text:

```
FF 08 03 01             [open character speech box]
19 25 22 19 19 24       のゆめのの + more text...
FF 05 01 01             [newline]
...                     [continued text fills box]
FF 08 07 01             [page break: show cursor, wait for input]
...                     [text continues in fresh box]
FF 08 02 01             [close box]
00                      [null terminator]
```

### Dramatic Text Delays

The `FF 03` control code inserts per-character delays for dramatic effect:

```
F0 0C 19                俺の
FF 03 0B 01             [pause 11 frames]
E5                      ・
FF 03 0B 01             [pause 11 frames]
E5                      ・
FF 03 0B 01             [pause 11 frames]
E5                      ・
```

This renders "俺の・・・" with slow trailing dots.

### Example Decoded Dialogues

| File | Offset | Japanese Text |
|---|---|---|
| SCPS_100.26 | 0x0D35B2 | メモリーカードが差されていませんが　セーブせずにゲームをしますか？ |
| SCPS_100.26 | -- | このアイテムをすてますか？ |
| SCPS_100.26 | -- | このモンスターと別れますか？ |
| SMITH.BIN | -- | はいている者にとって普段以上に歩きやすい靴 (item description) |
| S*.STG | various | スイッチがあります　ONにしてみますか？ |
| S*.STG | various | アイテムを見つけました　取りますか？ |

## Event Script Dialogue Format (STG Files)

Stage files (`S*.STG`) embed dialogue strings inside an event script bytecode stream. Each dialogue string has a **2-byte prefix** (little-endian 16-bit event script offset) before the text content, followed by a null terminator. Between consecutive dialogue strings, a **48-byte event script block** controls dialogue flow (wait for input, advance to next string).

### Dialogue String Layout

```
[2-byte script offset] [text bytes...] 00
[48-byte event script block]
[2-byte script offset] [text bytes...] 00
[48-byte event script block]
...
```

Example from S100.STG at `0x172EC6`:

```
83 26                           script offset 0x2683
F4 D5 F2 2D 02 19 54 79 58 06  炎使いのエルクか
FF 05 01 01                     [newline]
F3 8A 06 50 10 35 4D 15 02 06  遅かったじゃないか
00                              [null terminator]
```

The 2-byte prefix values increase monotonically for sequential dialogues, acting as offsets within the event script's address space.

### Inter-Dialogue Event Script Block (48 bytes)

Between each pair of dialogue strings, a fixed-structure 48-byte block handles dialogue flow control. The block contains three varying 16-bit LE fields (event script offsets) and a set of fixed opcodes:

```
Offset  Bytes       Description
------  ----------  -----------
+0      23 01       Fixed
+2      F0 8B       Fixed
+4      XX 80       Context opcode (varies by speaker group)
+6      28 01       Fixed
+8      F0 0B       Fixed
+10     04 00       Fixed (0x0004)
+12     00 80       Fixed
+14     [AA BB]     Ptr A: current_prefix + 0x10
+16     45 01       Fixed
+18     F0 8B       Fixed
+20     XX 80       Context opcode (same as +4)
+22     28 01       Fixed
+24     F0 0B       Fixed
+26     00 00       Fixed (0x0000)
+28     00 80       Fixed
+30     [CC DD]     Ptr B: Ptr A + 0x05
+32     63 00       Fixed
+34     XX 80       Context opcode (same as +4)
+36     [EE FF]     Ptr C: varies (points before current dialog)
+38     2D 00       Fixed
+40     30 00       Fixed
+42     62 00       Fixed
+44     02 80       Fixed
+46     A9 00       Fixed (typically 0x00A9)
```

The block structure repeats in a near-parallel pattern (offsets +0..+15 mirror +16..+31), differing only at +10 (`04 00` vs `00 00`), suggesting two similar operations per dialogue transition.

### Context Opcode (Speaker/Group ID)

The 16-bit LE value at template positions +4, +20, and +34 identifies the dialogue context. Different values delineate different speakers or scene states:

| Opcode | Observed Usage |
|--------|----------------|
| `0x8009` | NPC group before scene transition |
| `0x8001` | Primary dialogue group (guild master briefing) |
| `0x8000` | Alternate dialogue context |

When the context opcode changes between consecutive template blocks, there are typically additional non-template event script bytes at the transition point (e.g., 22 bytes of scene setup commands between the `0x8009` and `0x8001` groups).

### Script Opcode `28 01` Blocks (10 bytes each)

In the gaps between templates, chains of 10-byte **script opcode blocks** appear. These use the event script opcode `28 01` with various parameters:

```
Offset  Bytes       Description
------  ----------  -----------
+0      28 01       Fixed opcode (same as template +6, but with different param)
+2      PP PP       Parameter (varies: 07 00, AA 00, FF 00, E8 0A, F1 0B, etc.)
+4      XX XX       Flags: 00 00 (first in pair) or 01 00 (second in pair)
+6      YY ZZ       Context group ID (high byte >= 0x80, e.g., 09 80, 09 81, FF FF)
+8      [QQ RR]     Pointer (varies)
```

These commonly appear in **pairs** (20 bytes), mirroring the dual-operation pattern of the 48-byte template. At complex transitions, **chains of 2–12+ pairs** (20–120+ bytes) can appear. They are found at context transitions, before templates, and sometimes interleaved with dialogue strings.

Observed parameter variants and their false-text decodings:

| Param bytes | False text | Notes |
|---|---|---|
| `07 00` | りあき | Most common (context-transition preamble) |
| `AA 00` | りあJ | |
| `FF 00` | りあ[FF:...] | FF triggers control-code decoding |
| `E8 0A` | りあ／こ | |
| `F1 0B` | りあ関 | Often preceded by other garbled text |
| `CD 0B` | りあ系 | |
| `56 01` | りあ、 | |
| `57 09` | りあ。 | |

The structural signature for detection is: bytes +0..+1 = `28 01`, byte +5 = `00`, byte +7 >= `0x80`.

Example (2-pair chain from SB00.STG, immediately before a template):

```
28 01 07 00  00 00  09 80  D4 16   ← pair 1, first half  (context 0x8009)
28 01 07 00  01 00  09 81  ED 16   ← pair 1, second half
23 01 F0 8B  ...                    ← 48-byte template follows
```

**Decoder note:** Because `28 01` maps to valid character IDs (り=0x28, あ=0x01), these script blocks are misinterpreted as nonsense text if not excluded. The decoder (`python/decode/decode_text.py`) scans each gap for all `28 01` blocks matching the structural signature (P+5=0x00, P+7>=0x80), builds exclusion ranges, and rejects any dialogue candidate that overlaps a script opcode block.

## Key Functions (MIPS Disassembly)

### SDIC.BIN (System Dialogue Controller)

Loaded at RAM `0x80026000`. Renders text windows using the COMM.IMG 12x12 font cells (11x11 glyph + 1px margin).

| File Offset | RAM Address | Function |
|---|---|---|
| 0x1E90 | 0x80027E90 | `render_char(y, x, 12, 12, charID, color)` |
| 0x2078 | 0x80028078 | `render_string()` -- loops through text bytes |
| 0x3B18 | 0x80029B18 | `lookup_text(entry_id)` -- resolves text pointer |
| 0x3C18 | 0x80029C18 | `render_dict_entry(id, x, y)` -- renders full entry |

The dictionary pointer table starts at file offset `0x5B50` (RAM `0x8002BB50`).

### SCPS_100.26 (Main Executable)

SCPS_100.26 is a PSX-EXE file (PS1 executable format). Per PSX SPX, the format consists of:
- **0x800-byte header** with "PS-X EXE" magic at offset 0x000
- **Load address** at header offset +0x018 (where the code is loaded into RAM)
- **Entry point PC** at header offset +0x010 (first instruction to execute)
- **File size** at header offset +0x01C (must be a multiple of 0x800)
- **Code/data body** starting at file offset 0x800

All overlay modules (SDIC, YGUILD, YSHOP, YPROP, YSEG, SMITH) call functions in the `0x800Bxxxx`-`0x8018xxxx` range. Per PSX SPX, PS1 BIOS functions are accessed via vector calls at addresses 0x000000A0, 0x000000B0, and 0x000000C0 -- NOT via direct JAL to fixed addresses. This confirms that all `0x800Cxxxx`+ call targets in the overlay modules are **SCPS_100.26 game code**, not BIOS routines.

| File Offset | RAM Address | Function |
|---|---|---|
| 0x25800 | 0x800E6400 | Font rendering (14x14 grid, 17-column layout) |
| 0x25484 | 0x800E6084 | Page dispatch for SJIS-to-charID conversion |

The executable also contains Shift-JIS-to-charID mapping tables at file offset `0xBE534` (RAM `0x8017F134`), used when converting developer input to the internal encoding.

## File Locations of Text Data

| File | Size | Text Content |
|---|---|---|
| SCPS_100.26 | 909 KB | System messages, menu text, memory card prompts |
| SDIC.BIN | 100 KB | Dialogue window renderer + embedded text dictionary |
| SMITH.BIN | -- | Item/equipment descriptions |
| BEAM.DAT | -- | Battle/event text |
| CHA.BIN | -- | Character-related text |
| S100-SJ00.STG | 7-43 MB | Stage-specific dialogue embedded in event scripts |

## Tools

- `python/decode/decode_text.py` -- Decode text from binary game files (single offset, scan, or search)
  - `python python/decode/decode_text.py <file> <offset>` -- decode one string at offset
  - `python python/decode/decode_text.py <file> --scan` -- find and decode all text strings
  - `python python/decode/decode_text.py <file> --find "ますか"` -- find strings containing a pattern
  - `python python/decode/decode_text.py <file> --scan --prefix 2` -- STG files: mark 2-byte event script prefix
  - `python python/decode/decode_text.py <file> --stg` -- STG template-driven dialogue extraction (auto prefix)
  - `python python/decode/decode_text.py <file> --stg --find "エルク"` -- STG extraction filtered by text
- `python/decode/decode_all_stg.py` -- Batch decode all 19 STG files → `output/decoded/stg/`
- `python/decode/decode_all_bin.py` -- Batch decode BIN files → `output/decoded/bin/`
- `python/decode/decode_yend.py` -- Decode YEND.BIN ASCII credit strings (uses plain ASCII, not game encoding)
- `python/font/view_char.py` -- View individual font cells with bitplane separation
- `COMM_IMG_chars.md` -- Complete character-to-cell mapping table
