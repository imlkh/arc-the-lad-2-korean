# Text Region Byte Sequence Examples

Annotated hex dumps from the STG text region (0xB4000–0xBC7FF), showing how
raw bytes map to dialogue, templates, control codes, and other structures.

All examples are from **S100.STG** (original, unpatched).

## Encoding Quick Reference

| Byte(s) | Meaning |
|----------|---------|
| `00` | Null terminator (end of string) |
| `01`–`EE` | Single-byte charID → 1 character |
| `EF` | Menu option prefix `[opt]` |
| `F0 XX`–`FE XX` | Two-byte charID (kanji, symbols, Korean) |
| `FF XX YY ZZ` | 4-byte control code (box, line break, delay, etc.) |

See `TEXT_ENCODING.md` for the full charID table and control code reference.

---

## 1. Dialogue String with Line Break

**Source**: S100.STG chunk 1, offset `0x172EC6`

This is a two-line dialogue: `炎使いのエルクか` / `遅かったじゃないか`

### Raw hex

```
Offset    Hex                                         ASCII
────────  ──────────────────────────────────────────  ──────
172EC4:   83 26                                       .&
172EC6:   F4 D5 F2 2D 02 19 54 79 58 06              ....-..TyX.
172ED0:   FF 05 01 01                                 ....
172ED4:   F3 8A 06 50 10 35 4D 15 02 06              ...P.5M...
172EDE:   00                                          .
```

### Byte-by-byte annotation

```
83 26           ← 2-byte script prefix (offset 0x2683 into event script)
                  Not displayed; used by event engine for sequencing

F4 D5           ← Two-byte charID: (0xF4-0xF0)×255 + 0xD5 + 239 = 1259+213-239+239 → 炎
F2 2D           ← Two-byte charID: (0xF2-0xF0)×255 + 0x2D + 239 → 使
02              ← Single-byte charID 2 → い
19              ← Single-byte charID 25 → の
54              ← Single-byte charID 84 → エ
79              ← Single-byte charID 121 → ル
58              ← Single-byte charID 88 → ク
06              ← Single-byte charID 6 → か

FF 05 01 01     ← Control code: [br] (line break)
                  FF=control prefix, 05=newline sub-command

F3 8A           ← Two-byte charID → 遅
06              ← か
50              ← っ (charID 80)
10              ← た
35              ← じ
4D              ← ゃ
15              ← な
02              ← い
06              ← か

00              ← Null terminator (end of string)
```

### Decoded text

```
炎使いのエルクか
遅かったじゃないか
```

("Elk, the fire user? / You're late, aren't you?")

---

## 2. Dialogue with Box Control and Kanji

**Source**: S100.STG chunk 1, offset `0x172F56`

A longer dialogue with `[br]` and many two-byte kanji characters.

### Raw hex

```
Offset    Hex
────────  ──────────────────────────────────────────────────────────────
172F54:   D4 26                                         ← script prefix
172F56:   F2 BA F2 94 1A 51 79 8C 99 51 F3 46 F4 F4   ← line 1
172F64:   39                                            ← だ
172F65:   FF 05 01 01                                   ← [br]
172F69:   05 0E 0C 15 F2 8B 2D F2 2D 03                ← line 2 start
172F73:   F5 20 2F F4 C6 2A 13 02 29 27 0C 02          ← line 2 cont
172F7F:   00                                            ← null
```

### Byte-by-byte annotation

```
D4 26           ← Script prefix

── Line 1 ──
F2 BA           ← 場 (two-byte kanji)
F2 94           ← 所
1A              ← は (single-byte hiragana)
51              ← ア (single-byte katakana, charID 81)
79              ← ル
8C              ← デ (charID 140)
99              ← ィ (charID 153, small katakana)
51              ← ア
F3 46           ← 空 (two-byte kanji)
F4 F4           ← 港
39              ← だ

FF 05 01 01     ← [br] line break

── Line 2 ──
05              ← お
0E              ← せ
0C              ← し
15              ← な
F2 8B           ← 術
2D              ← を
F2 2D           ← 使
03              ← う
F5 20           ← 奴
2F              ← が
F4 C6           ← 暴
2A              ← れ
13              ← て
02              ← い
29              ← る
27              ← ら
0C              ← し
02              ← い

00              ← Null terminator
```

### Decoded text

```
場所はアルディアア空港だ
おせしな術を使う奴が暴れているらしい
```

("The location is Aldia Airport / Apparently someone using strange magic is causing trouble")

---

## 3. Event Script Template (48 bytes)

**Source**: S100.STG chunk 1, offset `0x172E80`

Templates are 48-byte control structures that anchor dialogue strings. The
game engine reads these to determine who speaks, which box style to use,
and where the dialogue text is located.

### Raw hex

```
Offset    Hex                                          Field
────────  ─────────────────────────────────────────    ─────
172E80:   23 01 F0 8B                                  Signature (Block 1)
172E84:   09 80                                        Speaker: 0x8009
172E86:   28 01                                        Ptr_A: 0x0128
172E88:   F0 0B                                        Ptr_B: 0x0BF0
172E8A:   04 00                                        Ptr_C: 0x0004 (primary)
172E8C:   00 80                                        Unknown
172E8E:   62 26                                        Line index

172E90:   45 01 F0 8B                                  Signature (Block 2)
172E94:   09 80                                        Speaker: 0x8009
172E96:   28 01                                        Ptr_A: 0x0128
172E98:   F0 0B                                        Ptr_B: 0x0BF0
172E9A:   00 00                                        Ptr_C: 0x0000 (secondary)
172E9C:   00 80                                        Unknown
172E9E:   67 26                                        Line index

172EA0:   63 00                                        Box command: 0x0063
172EA2:   09 80                                        Speaker (mirror)
172EA4:   4D 26                                        Timing offset
172EA6:   2D 00                                        Box type: 0x002D
172EA8:   30 00                                        Box height: 48px
172EAA:   62 00                                        Box Y position: 98px
172EAC:   02 80                                        Dialog flags: 0x8002
172EAE:   0E 00                                        Animation ID: 0x000E
```

### Structure summary

```
┌────────────────────────────────────────────────────────────────┐
│ Block 1 (16 bytes): 23 01 F0 8B [speaker] [Ptr_A] [Ptr_B]... │
│ Block 2 (16 bytes): 45 01 F0 8B [speaker] [Ptr_A] [Ptr_B]... │
│ Box Control (16 bytes): 63 00 [speaker] [timing] [style]...   │
└────────────────────────────────────────────────────────────────┘
```

- **Signature** `23 01 F0 8B` / `45 01 F0 8B` = little-endian for `0x8BF00123` / `0x8BF00145`
- **Speaker** `09 80` = opcode `0x8009` (party member)
- **Ptr_A** `28 01` = text pointer; the dialogue string starts at `Ptr_A - 0x10` from the text region base
- **Block 1 vs Block 2**: identical except Ptr_C (`04 00` vs `00 00`), suggesting a dual-operation pattern

---

## 4. Yes/No Choice Prompt

**Source**: Typical system prompt pattern found across all STG files

A choice dialogue: "Switch found. Turn it ON?" with はい/いいえ options.

### Raw hex (reconstructed from decoded pattern)

```
XX XX           ← Script prefix
FF 08 01 01     ← [box:system] — open system text box
5D 52 A0 61     ← スイッチ (switch)
2F 01 28 1F     ← がありま
0D              ← す
FF 05 01 01     ← [br] — line break
55 7E 16 0C     ← ONにし
13 20 1F 0D     ← てみます
06 EE           ← か？
FF 05 01 01     ← [br]
EF              ← [opt] — option prefix
1A 02           ← はい (yes)
FF 05 01 01     ← [br]
EF              ← [opt] — option prefix
02 02 04        ← いいえ (no)
FF 08 02 01     ← [box:close] — close dialogue box
00              ← Null terminator
```

### Decoded text

```
[box:system]スイッチがあります
ONにしてみますか？
[opt]はい
[opt]いいえ
[box:close]
```

### Key patterns

- `FF 08 01 01` opens a system box (blue/neutral style)
- `FF 08 03 01` opens a speech bubble (character dialogue)
- `FF 08 02 01` closes any open box
- `EF` marks each selectable menu option
- Options are separated by `[br]` (`FF 05 01 01`)

---

## 5. Script Opcode Blocks (10 bytes)

**Source**: S100.STG chunk 1, offset `0x172EB0`

These event script commands appear in gaps between templates. They control
dialogue flow (scene transitions, speaker assignment).

### Raw hex

```
Offset    Hex                        Decoded
────────  ─────────────────────────  ────────────────────────
172EB0:   28 01 AC 04 01 00 00 80   opcode block (pair 1a)
172EB8:   65 27                      pointer
172EBA:   A9 00                      ref ID: 0x00A9

172EBC:   83 26                      ← This is actually the script prefix
                                       of the next dialogue string
```

### Annotation

```
28 01       ← Fixed opcode signature (always 28 01)
AC 04       ← Parameter: 0x04AC
01 00       ← Flags: 0x0001 (second in pair)
00 80       ← Context group: 0x8000
65 27       ← Pointer
A9 00       ← Reference ID: 0x00A9
```

**Why the decoder must exclude these**: `28` = charID for `り`, `01` = charID
for `あ` — so the gap search would decode these as the text `りあ...`, which
is nonsense. The decoder detects the structural signature (`28 01` + byte[5]=`00`
+ byte[7]>=`0x80`) and builds exclusion ranges.

---

## 6. Event Trigger Commands (14 bytes)

**Source**: S100.STG chunk 0, offset `0xB40A0` region

These control which speakers are active for upcoming dialogue. They are the
primary source of "garbage text" when misinterpreted.

### Raw hex

```
Offset    Hex                                    Meaning
────────  ─────────────────────────────────────  ───────────────────────
0B40A0:   26 00 01 80 23 00 40 80 20 80 40 87   Event trigger cmd
          ^^    ^^ ^^       ^^ ^^       ^^ ^^
          CMD   Spk1=8001  Spk2=8040  Spk3=8020  (speakers in 0x80XX)
```

### Why these become garbage

The repeating `XX 80` pattern decodes as katakana:

| Bytes | CharID | Character |
|-------|--------|-----------|
| `01 80` | 1, 128 | あギ |
| `23 00` | 35, null | も(end) |
| `40 80` | 64, 128 | ぶギ |
| `20 80` | 32, 128 | みギ |

The decoder's garbage filter (Rule 7d) catches the high density of `ギ`/`デ`
characters, which is characteristic of MIPS speaker opcodes decoded as text.

---

## 7. MIPS Code Fragments in Text Region

Small R3000 instruction sequences appear embedded within the text region itself
(not the main MIPS regions at 0x77000–0xA0000). These are likely inlined handler
code, jump table targets, or address computation stubs. The same byte sequences
appear identically across multiple STG files.

### Example A: ADDIU instruction chain

**Source**: Found in S200, S600, SB00, SC00, SG00 (identical bytes)

```
Offset    Hex                              R3000 Disassembly
────────  ─────────────────────────────    ─────────────────────────────
+0x00:    24 04 DF 03                      ADDIU $a0, $zero, 0x03DF
+0x04:    02 07 01 12                      MULT  $s0, $a3  ;  MFLO $v0
+0x08:    04 14 00                         ...
```

#### Byte-by-byte decode as "text"

```
24          ← charID 36 → や
04          ← charID 4  → え
DF          ← charID 223 → 地
03          ← charID 3  → う
02          ← charID 2  → い
07          ← charID 7  → き
01          ← charID 1  → あ
12          ← charID 18 → つ
04          ← charID 4  → え
14          ← charID 20 → と
00          ← null terminator
```

**Decoded as garbage**: `地ういきあつえと`

The `24 04 DF` opening (`ADDIU $a0, $zero, ...`) is a telltale MIPS pattern.
The decoder catches this via Rule 7h (starts with 地 + all hiragana + contains あ).

### Example B: NOR + LWL instruction pair

**Source**: Found in S200, S700, SD00 (identical bytes)

```
Offset    Hex                              R3000 Disassembly
────────  ─────────────────────────────    ─────────────────────────────
+0x00:    80 27 01 44                      LB $a3, 0x4401($at)
+0x04:    8C 4E 0C 89                      LW $t6, 0x890C($v0)
+0x08:    00                               (null)
```

#### Byte-by-byte decode as "text"

```
80          ← charID 128 → ギ    ← 0x80 = LB opcode high byte
27          ← charID 39  → ら
01          ← charID 1   → あ    ← register field
44          ← charID 68  → ぴ
8C          ← charID 140 → デ    ← 0x8C = LW opcode high byte
4E          ← charID 78  → ゅ
0C          ← charID 12  → し
89          ← charID 137 → ダ    ← 0x89 = register encoding
00          ← null terminator
```

**Decoded as garbage**: `ギらあぴデゅしダ`

The high density of dakuten katakana (ギ, デ, ダ) is the fingerprint of
load/store instructions — `0x80`=LB, `0x8C`=LW, `0x89`=ダ register field.
Caught by Rule 7d (high デ/ギ density ≥25%).

### Example C: SPECIAL-type instructions (めあ pattern)

**Source**: Multiple STG files

```
Offset    Hex                              R3000 Disassembly
────────  ─────────────────────────────    ─────────────────────────────
+0x00:    22 01 XX XX                      SUB $zero, $s1, ... (rs=$zero)
+0x04:    22 01 XX XX                      SUB $zero, $s1, ... (rs=$zero)
```

#### Byte-by-byte decode as "text"

```
22          ← charID 34 → め
01          ← charID 1  → あ
22          ← charID 34 → め
01          ← charID 1  → あ
```

**Decoded as garbage**: `めあめあ...`

The R3000 little-endian encoding of `$zero` in the rs field combined with
SUB/ADD function codes produces `0x22 0x01` (めあ) at 4-byte intervals.
Caught by the `_has_mips_opcode_signature()` raw-byte check (めあ ×2).

### Why MIPS detection is hard

The fundamental problem: the game's charID encoding maps 238 characters to
bytes `0x01`–`0xEE`, covering **93% of the byte space**. R3000 opcode bytes
overlap heavily with valid charIDs:

| MIPS byte | CharID | Character | MIPS meaning |
|-----------|--------|-----------|-------------|
| `0x80` | 128 | ギ | LB (load byte) |
| `0x8C` | 140 | デ | LW (load word) |
| `0x89` | 137 | ダ | register encoding |
| `0x24` | 36 | や | ADDIU |
| `0x01` | 1 | あ | SPECIAL function |
| `0xDF` | 223 | 地 | immediate operand |

There are no "invalid" bytes to distinguish code from text. The decoder relies
on **text-pattern rules** (character frequency, grammar checks) rather than
byte-level MIPS validation. See `DECODER_FIXES.md` and `TEXT_REGION_BYTE_ANALYSIS.md`.

---

## 8. Mixed Byte Types in Context — Real Hex Dump

**Source**: S100.STG chunk 0, offsets `0xB8A30`–`0xB8AF0`

This region near the end of the text region shows MIPS code, event triggers,
script opcodes, and data tables all mixed together — with annotated byte types.

### Raw hex with type annotations

```
Offset    Hex                                          Type
────────  ─────────────────────────────────────────    ──────────────────────
          ↓↓ MIPS CODE ↓↓

0B8A36:   24 01 BE 80                                  ADDIU $at,$at,-0x7F42
0B8A3A:   28 01 BE 00 04 00 3C 80 AC 29               Script opcode block
0B8A44:   22 01 BE 80                                  SUB ... (めあ pattern)
0B8A48:   24 01 BC 80                                  ADDIU $at,$at,-0x7F44
0B8A4C:   28 01 BC 00 04 00 3C 80 B5 29               Script opcode block

0B8A56:   22 01 BC 80                                  SUB ... (めあ pattern)
0B8A5A:   24 01 41 80                                  ADDIU $at,$at,-0x7FBF
0B8A5E:   28 01 41 00 04 00 70 97 BD 29               Script opcode block

          ↓↓ TEMPLATE SIGNATURE ↓↓

0B8A68:   23 01 41 80                                  Template sig (partial)
0B8A6C:   70 97                                        parameter
0B8A6E:   26 00 01 80                                  Speaker: 0x8001
0B8A72:   A9 00                                        Ref ID: 0x00A9
0B8A74:   A1 29                                        Pointer
0B8A76:   00 00                                        null padding

          ↓↓ MORE SCRIPT OPCODES + MIPS ↓↓

0B8A78:   28 01 41 00 04 00 58 82 11 2A               Script opcode block
0B8A82:   28 01 C0 00 04 00 64 80 11 2A               Script opcode block
0B8A8C:   C1 00                                        data byte
0B8A8E:   44 8C 44 8C 64 80                            LW $a0,... (MIPS load)
0B8A94:   28 01 44 0C 03 00 32 80 11 2A               Script opcode block

          ↓↓ EVENT TRIGGERS (XX 80 pattern) ↓↓

0B8A9E:   23 01 46 8C E0 80                            Template sig + LW instr
0B8AA4:   23 01 47 8C 00 80                            Template sig + LW instr
0B8AAA:   AA 00 E7 03                                  Ref ID + parameter

          ↓↓ MORE MIPS + DATA ↓↓

0B8AAE:   23 01 44 8C 45 0C                            Template sig + LW instr
0B8AB4:   28 01 44 0C 04 00 00 80 11 2A B1 00         Script opcode block

          ↓↓ NULL PADDING → END ↓↓

0B8AEE:   FF FF A9 00 11 2A E0 01                      data (FF FF marker)
0B8AF6:   00 08 01 0B 4C 15 0F 10 0F 0F               MIPS JR + dialogue?
0B8B00:   00 00 00 00 00 00 ...                         null padding to chunk end
```

### How each byte type "looks" when decoded as text

| Bytes | Decoded | Actual type | Diagnostic clue |
|-------|---------|-------------|-----------------|
| `24 01 BE 80` | `やあdギ` | MIPS ADDIU | あ at position 2, ギ at position 4 |
| `22 01 BE 80` | `めあdギ` | MIPS SUB | めあ×1 pattern |
| `28 01 BE 00` | `りあd·` | Script opcode | `28 01` signature + null at [3] |
| `44 8C 44 8C` | `ぴデぴデ` | MIPS LW pair | Repeating 2-byte pattern (Rule 6) |
| `23 01 46 8C` | `もあぺデ` | Template+MIPS | もあ prefix + デ density |
| `00 00 00 00` | `····` | Null padding | All zeros |

### Key observation

In this 192-byte stretch, **six different byte types** are interleaved with
no clear structural boundaries. The decoder must identify templates by their
`23 01 F0 8B` / `45 01 F0 8B` signatures, script opcodes by the `28 01`
pattern, and then test everything else against the garbage filter rules. Only
strings that pass all filters become accepted dialogue.

---

## 9. MIPS vs Text Comparison Side-by-Side

Showing how the same byte range looks when interpreted as MIPS instructions
versus game text:

```
Bytes:  80 27 01 44 8C 4E 0C 89 00

As MIPS R3000 (correct):
  80270144  LB    $a3, 0x4401($at)     ← load byte from memory
  8C4E0C89  LW    $t6, 0x890C($v0)     ← load word from memory

As game text (wrong):
  80=ギ 27=ら 01=あ 44=ぴ 8C=デ 4E=ゅ 0C=し 89=ダ 00=END
  → "ギらあぴデゅしダ" (nonsense)
```

```
Bytes:  F4 D5 F2 2D 02 19 54 79 58 06 00

As MIPS R3000 (wrong — misaligned, not real code):
  F4D5F22D  SDC2  $21, -0x0DD3($a2)    ← coprocessor (unlikely)
  02195479  ???                          ← invalid encoding

As game text (correct):
  F4 D5=炎 F2 2D=使 02=い 19=の 54=エ 79=ル 58=ク 06=か 00=END
  → "炎使いのエルクか" (real dialogue)
```

The key difference: MIPS code produces dakuten-heavy katakana (ギデダグゲ) with
no grammatical structure, while real dialogue has natural hiragana/kanji flow.

---

## 10. Byte-Type Distribution in a Typical Chunk

From statistical analysis of S200 chunks:

```
Text Region: 34,816 bytes (0xB4000 - 0xBC7FF)

┌──────────────────────────────────────────────────────────────┐
│  Null padding (00)           ████████████████████  25-60%    │
│  Templates (48B blocks)      ████████             4-20%     │
│  Dialogue strings            ████████             5-13%     │
│  Event triggers (XX 80)      ██████               4-18%     │
│  Script opcodes (28 01)      ███                  2-8%      │
│  MIPS code fragments         █                    <2%       │
│  Data tables / other         █                    <2%       │
└──────────────────────────────────────────────────────────────┘
```

### Fixed vs Variable Length

| # | Type | Length | Signature | How decoder handles it |
|---|------|--------|-----------|------------------------|
| 1 | Template | **Fixed 48 bytes** | `23 01 F0 8B` (block 1) + `45 01 F0 8B` (block 2) | Primary anchor — scanned by signature, always exactly 48 bytes. The decoder uses these as reference points to locate dialogue strings via Ptr_A. |
| 2 | Script opcode block | **Fixed 10 bytes** | `28 01` + byte[5]=`00` + byte[7]>=`0x80` | Secondary anchor — detected by structural signature. The decoder builds exclusion ranges so gap search skips these. |
| 3 | Dialogue string | **Variable** (null-terminated) | None (identified by position relative to templates) | Ranges from 2 bytes (e.g., `EE 00` = `？`) to 200+ bytes for multi-line dialogue with control codes. Terminated by `00`. |
| 4 | Event trigger command | **Variable** (~14 bytes typical) | `67 00` for the common type, but other command types exist | The `67 00` command is 14 bytes (7 × 16-bit fields), but other event commands in the same stream have different lengths. No single fixed size. |
| 5 | Null padding | **Variable** | All `00` bytes | Fills remaining space. Trivially detected. |
| 6 | MIPS code fragment | **Variable** (4-byte aligned) | No reliable signature in text context | Individual instructions are 4 bytes (R3000 fixed-width ISA), but fragments contain varying numbers of instructions. Total size varies. |
| 7 | Data table / other | **Variable** | None | Pointer tables, index arrays, parameter blocks — all different sizes. |

**Why this matters for the decoder**: Only the two fixed-length types (template
and script opcode) have reliable signatures. The decoder anchors on templates,
then scans the variable-length gaps between them. Everything found in a gap must
be classified as dialogue or garbage using heuristic rules, because the remaining
five types have no structural signatures and variable lengths — they can only be
distinguished by their **content** (byte patterns, character frequency, grammar).

### Ordering: Three-Zone Layout

The text region is **not** a simple repeating sequence. It has a three-zone
structure with variable zone sizes:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Zone 1: PRE-TEMPLATE                                               │
│   Script opcodes (28 01), event triggers (67 00), event data,      │
│   bare dialogues, MIPS fragments, data tables                      │
│   Size: 84 – 29,582 bytes (varies wildly per chunk)                │
├─────────────────────────────────────────────────────────────────────┤
│ Zone 2: TEMPLATE AREA                                              │
│   Templates interleaved with dialogue strings and script opcodes   │
│   Pattern: Template → [gap: dialogue + script ops] → Template → …  │
│   Size: 4,618 – 34,608 bytes                                      │
├─────────────────────────────────────────────────────────────────────┤
│ Zone 3: POST-TEMPLATE                                              │
│   Script opcodes, event triggers, remaining event data             │
│   Size: 124 – 4,740 bytes                                         │
└─────────────────────────────────────────────────────────────────────┘
```

**Measured zone sizes** (S100.STG, 11 chunks):

| Chunk | Zone 1 (pre-template) | Zone 2 (template area) | Zone 3 (post-template) | Templates | Evt triggers in Z1 |
|-------|----------------------|------------------------|------------------------|-----------|---------------------|
| 0 | 1,312 B | 33,374 B | 130 B | 173 | No |
| 1 | 7,330 B | 22,848 B | 4,638 B | 161 | No |
| 2 | 27,846 B | 4,618 B | 2,352 B | 22 | Yes |
| 3 | 24,384 B | 9,980 B | 452 B | 109 | Yes |
| 4 | 84 B | 34,608 B | 124 B | 308 | No |
| 5 | 17,190 B | 16,246 B | 1,380 B | 116 | Yes |
| 6 | 21,680 B | 12,454 B | 682 B | 51 | Yes |
| 7 | 29,582 B | 4,922 B | 312 B | 32 | Yes |
| 8 | 19,724 B | 14,576 B | 516 B | 75 | Yes |
| 9 | 25,446 B | 4,630 B | 4,740 B | 40 | Yes |
| 10 | *entire region* | *(none)* | *(none)* | **0** | — |

**Key observations**:

1. **Zone sizes vary wildly** — chunk 4 is almost all templates (Zone 1 = 84 B),
   while chunk 7 is almost all pre-template event data (Zone 1 = 29,582 B).
2. **Event triggers (`67 00`) cluster in Zone 1** (pre-template), not within
   the template area. They are the commands that *reference* dialogues; templates
   are the structures that *contain* dialogue pointers.
3. **Chunk 10 has no templates at all** — the entire text region is event script
   data (Zone 1 only).
4. **Within Zone 2**, the template → gap → template pattern is consistent:
   - 81/160 gaps contain dialogue only
   - 16/160 gaps contain script opcodes + dialogue
   - 55/160 gaps contain other data (event refs, MIPS fragments)
   - 8/160 gaps contain script opcodes only
5. **The order is not fixed** — there is no guaranteed sequence between byte
   types. Templates always precede their associated dialogue (Ptr_A points
   forward), but event triggers, script opcodes, MIPS fragments, and data
   tables can appear anywhere in any zone.

### Where the 57 garbage entries came from

The final decoder fix ("Garbage Elimination to Zero", 2026-02-09) eliminated
57 Category 1 garbage entries. All 57 were in the **text region**
(0xB4000–0xBC7FF) — specifically in **Zone 2 template gaps** — not from the
main MIPS code regions (0x77000–0xA0000).

```
                    Main MIPS code regions (0x77000 – 0xA0000)
                    ├── Filtered out by region-based post-filter
                    ├── chunk_offset < 0xA0000 → rejected
                    └── Removed ~315 entries in earlier fix (not these 57)

                    Text region (0xB4000 – 0xBC800)
     ┌──────────────┬──────────────────────────────┬──────────────┐
     │   Zone 1     │          Zone 2              │   Zone 3     │
     │ pre-template │ template gaps ← 57 HERE      │ post-template│
     └──────────────┴──────────────────────────────┴──────────────┘
```

The 57 entries break down by source byte type:

| Source byte type | Count | What it is | Example garbage text |
|------------------|-------|------------|---------------------|
| Type 6: MIPS code fragments | ~39 | R3000 instructions embedded in template gaps as inlined handlers or jump table stubs | `地ういきあつえと` (ADDIU), `ギらあぴデゅしダ` (LB+LW), `かグにグォギ` (speaker opcodes) |
| Type 7: Data tables | ~10 | Pointer tables, index arrays, parameter blocks | `4えを` (REGIMM), `9む9むボ` (repeating pattern) |
| Type 4: Event triggers | ~8 | `A9 00` ref IDs + `XX 80` speaker opcodes | `。つし` (A9 00 + params), `どと＊` (A9 00 + params) |

**Why they're in the text region, not the MIPS regions**: These are not part
of the main MIPS code blocks at 0x80000–0x9FFFF. They are small code/data
fragments that the game engine places within template gaps in the text region
— likely event handler stubs, dialogue dispatch tables, or scene setup
parameters. The same byte sequences appear identically across multiple STG
files (e.g., the NOR+LWL pair `80 27 01 44 8C 4E 0C 89` in S200, S700, SD00),
confirming they are shared engine code rather than random data.

**Why the decoder picks them up**: The gap search scans all bytes between
consecutive templates looking for dialogue. Since 93% of the byte space
(`0x01`–`0xEE`) maps to valid charIDs, every MIPS instruction byte decodes
to a "valid" Japanese character. There are no invalid bytes to reject — only
text-pattern analysis (character frequency, grammar checks, MIPS fingerprints)
can distinguish code from dialogue.

### No generic MIPS start marker — but shared code blocks have fixed context

There is **no generic "MIPS code starts here" marker** in the text region.
However, the MIPS fragments are not randomly placed — they are part of
**shared event engine routines** that get replicated identically into every
chunk's text region. The entire surrounding context (event script opcodes,
parameters, and the MIPS code itself) is a fixed block that the game's build
system stamps into each chunk.

This means each specific MIPS fragment has a **consistent prefix** — not
because there's a marker protocol, but because the whole code block is copied
as a unit.

#### ADDIU block — 100% identical prefix (10 instances, 5 STG files)

All 10 instances of the ADDIU pattern (`24 04 DF`) across S200, S600, SB00,
SC00, and SG00 share an **identical 48-byte prefix**:

```
Offset    Hex                                          Content
────────  ─────────────────────────────────────────    ───────────────────
-0x30:    53 8C 01 80 D6 00 44 8C 01 80 2A 01 F8 03   event script data
-0x22:    28 01 4E 0C 00 00 00 80 03 04                script opcode block
-0x18:    99 00 FF 03 09 80 01 80                      event params
-0x10:    AB 00 C2 00 53 8C 53 8C 0C 04                event data
-0x06:    AA 00 4F 03 A9 00                            ref IDs (A9 00)
 0x00:    24 04 DF XX XX 07 01 12 XX 14 00             ← ADDIU instruction
          ^^^^^^^^^^^                                     (only 3 bytes vary)
 0x0B:    00 00 00 00 00 00 ... 00 00                  null padding to chunk end
```

The 48-byte prefix is byte-for-byte identical across all files. Only 3 bytes
within the ADDIU instruction itself vary (operand values). The MIPS code is
always followed by null padding — it sits at the very end of the active data
in the text region.

#### NOR+LWL block — consistent prefix and suffix (88+ instances, 7+ STG files)

All instances of the NOR+LWL pattern (`80 27 01 44`) share:
- An identical **15-byte prefix**: `0E 00 0F 00 43 01 0B 00 4E 0C 00`
  (only 1 byte before that varies per chunk)
- An identical **8+ bytes after**: `8C 4E 0C 89 00 0B 00 03 80 44 0C FF FF`

```
Offset    Hex                                          Content
────────  ─────────────────────────────────────────    ───────────────────
-0x20:    4E 8C 4E 8C 44 0C 28 01 4E 0C               event data + script op
-0x16:    00 00 00 80 XX XX                            context (2 bytes vary)
-0x10:    4E 00 00 80 0E 00 0F 00                      event params (fixed)
-0x08:    43 01 0B 00 4E 0C 00                         event params (fixed)
 0x00:    80 27 01 44                                  ← LB  $a3, 0x4401($at)
 0x04:    8C 4E 0C 89                                  ← LW  $t6, 0x890C($v0)
 0x08:    00                                           null
 0x09:    0B 00 03 80 44 0C FF FF 35 00 ...            more event data (fixed)
```

#### Why these are shared code blocks

The evidence that these are replicated engine routines, not random data:

1. **Identical bytes across files**: The NOR+LWL fragment `80 27 01 44 8C 4E
   0C 89` appears identically in S200, S700, SD00, SB00 — different stage files
   compiled from different source data.
2. **Fixed surrounding context**: The 48-byte prefix before ADDIU is
   byte-identical across 5 different STG files. Random data would not align.
3. **Always in the same structural position**: Both patterns appear in Zone 2
   template gaps, at consistent offsets relative to event script blocks.
4. **Followed by null padding or fixed continuations**: The ADDIU block always
   ends with null padding to the chunk boundary. The NOR+LWL block always
   continues with `0B 00 03 80 44 0C FF FF`.

These are **event engine dispatch stubs** — small code fragments that the
dialogue system uses to set up speaker contexts, load parameters, and branch
to the appropriate handler. The game's build pipeline copies the same routine
into every chunk that needs dialogue support.

### Only MIPS code blocks have unique fixed structures

Not all garbage-causing byte sequences have fixed structures. Among the 57
garbage entries eliminated in the final decoder fix, only the actual R3000
instruction blocks are fixed — the event trigger data varies per chunk.

| Group | Type | Distinct sequences | Instances | Fixed? |
|-------|------|-------------------|-----------|--------|
| **C** (ADDIU) | MIPS code | **6** | 10 | **Yes** — `24 04 DF XX XX 07 01 12 XX 14`, 3 operand bytes vary |
| **D** (NOR+LWL) | MIPS code | **4** | 146 | **Yes** — 143/146 identical: `80 27 01 44 8C 4E 0C 89` |
| **A** (LW repeats) | Event data | 4,152 | 10,496 | **No** — chunk-specific LW parameters |
| **B** (speaker opcodes) | Event data | 10,927 | 22,692 | **No** — chunk-specific speaker/context values |

**MIPS code blocks** (Groups C, D) are shared engine routines — a handful
of fixed byte sequences replicated across all chunks. Each has a recognizable
exact signature that could be matched directly.

**Event trigger data** (Groups A, B) uses a consistent _structural pattern_
(`XX 8C XX 8C` for LW pairs, `XX 80 XX 80` for speaker opcodes) but the
specific byte values change per scene. Each chunk has different speakers,
context opcodes, and parameters, producing thousands of distinct sequences.
A signature database for these is impractical.

```
MIPS code (Groups C, D):          Event trigger data (Groups A, B):

  24 04 DF 03 02 07 01 12           44 8C 44 8C 65 80 28 01
  24 04 DF 06 05 07 01 12           53 8C 53 8C 30 02 23 01
  24 04 DF 05 06 07 01 12           46 8C 46 8C 8C 02 28 01
  ^^^^^^^^^^                        ^^ ^^ ^^ ^^
  Fixed prefix (6 variants)         Same pattern, different values
                                    (4,152 variants)
```

This is why the decoder uses **text-pattern heuristics** (Rule 7d: high デ/ギ
density) rather than byte signatures. The heuristic catches _both_ the fixed
MIPS blocks and the variable event trigger data, because both produce the same
characteristic decoded text: dakuten-heavy katakana (ギ=`0x80`, デ=`0x8C`)
with no grammatical structure.

### Concrete example: MIPS in a template gap

**Source**: SB00.STG chunk 8, gap `0x69F922`–`0x69FBD4` (690 bytes)

This gap sits between two templates in Zone 2. It contains a mix of event
data, short null-terminated values, and a MIPS code fragment. The decoder's
gap search encounters the MIPS bytes and decodes them as Japanese text.

```
Offset    Hex                                          Byte type
────────  ─────────────────────────────────────────    ─────────────────────

          ┌─ TEMPLATE (before gap) ─────────────────────────────────────────┐
69F8F2:   │ 23 01 F0 8B 05 80 28 01 F0 0B 04 00 00 80 77 20  (48 bytes) │
69F902:   │ 45 01 F0 8B 05 80 28 01 F0 0B 00 00 00 80 7C 20              │
69F912:   │ 63 00 05 80 5D 20 2D 00 30 00 62 00 02 80 26 00              │
          └────────────────────────────────────────────────────────────────┘

          ┌─ GAP START (690 bytes) ─────────────────────────────────────────
          │
          │  ... event data, script opcodes, null-terminated values ...
          │
69FAE0:   │ A2 00                            ← short value + null
69FAE2:   │ 64 21 02 00                      ← data bytes + null
69FAE6:   │ 01 00                            ← data byte + null
69FAE8:   │ FF FF A3 00                      ← 0xFFFF marker + data + null
69FAEC:   │ D3 00                            ← data byte + null
          │
          │  ↓↓ MIPS FRAGMENT BEGINS ↓↓
          │
69FAEE:   │ 44 8C 58 21 02                   ← LW $a0,0x2158($v0) [tail]
69FAF3:   │ 80 27 01 44                      ← LB  $a3, 0x4401($at)
69FAF7:   │ 8C 0A 00 26                      ← LW  $t2, 0x260A($zero)
69FAFB:   │ 01 45 8C 44                      ← (cross-boundary)
69FAFF:   │ 0C 28 01 45                      ← JAL + (next instr)
69FB03:   │ 0C 04 00 05                      ← JAL  0x00140005
69FB07:   │ 80 7C 21 28                      ← LB   $gp, 0x2821($a3)
69FB0B:   │ 01 09 00 05                      ← JALR + NOP
69FB0F:   │ 00 00                            ← null (end of fragment)
          │
          │  ↑↑ MIPS FRAGMENT ENDS ↑↑
          │
          │  ... more event data, script opcodes ...
          │
          └─ GAP END ───────────────────────────────────────────────────────

          ┌─ TEMPLATE (after gap) ──────────────────────────────────────────┐
69FBD4:   │ 23 01 F0 8B F3 0B 28 01 F0 0B 04 00 00 80 E8 21  (48 bytes) │
69FBE4:   │ 45 01 F0 8B F3 0B 28 01 F0 0B 00 00 00 80 ED 21              │
69FBF4:   │ 63 00 F3 0B D6 21 2D 00 30 00 62 00 02 80 A9 00              │
          └────────────────────────────────────────────────────────────────┘
```

**How the decoder misreads the MIPS bytes**:

The gap search finds bytes between null terminators (`00`) and tries to
decode them as dialogue. The MIPS fragment at `0x69FAF3` has no null bytes
until `0x69FB0F`, so it looks like a 28-byte "string":

```
Byte      CharID    Text        MIPS meaning
────────  ────────  ──────────  ──────────────────────
80        128       ギ          LB opcode (0x80)
27         39       ら          register field
01          1       あ          SPECIAL function (0x01)
44         68       ぴ          register field
8C        140       デ          LW opcode (0x8C)
0A         10       こ          register field
...       ...       ...         ...
```

**Decoded "text"**: `ギらあぴデこよあぷデぴしりあぷしえおギワむりあけお`

This is nonsense, but every byte is a valid charID. The garbage filter catches
it via Rule 7d (high デ/ギ density ≥25% — characteristic of LB/LW opcodes
`0x80`/`0x8C` decoded as katakana).

### Byte frequency in dialogue strings

| Byte Range | % of dialogue bytes | Content |
|------------|---------------------|---------|
| `01`–`50` | 52.9% | Hiragana (あ–っ) |
| `51`–`A0` | 26.6% | Katakana (ア–ッ) |
| `A1`–`D4` | 7.8% | Latin letters (A–z) |
| `D5`–`EE` | 2.5% | Digits, symbols, element kanji |
| `EF`–`FF` | **10.2%** | Control codes (FF, EF, F0–FE prefixes) |

The 10.2% control code presence is the strongest discriminator between real
dialogue and garbage — event triggers and MIPS code have only ~1.2% bytes in
the `EF`–`FF` range.

---

## 11. Interleaved Structure Walkthrough

A complete sequence from S100.STG chunk 1 showing how templates, dialogues,
and script blocks interleave:

```
Offset    Content
────────  ──────────────────────────────────────────────────────────────

          ┌─ 48-BYTE TEMPLATE ─────────────────────────────────────────┐
172E80:   │ 23 01 F0 8B 09 80 28 01 F0 0B 04 00 00 80 62 26          │
172E90:   │ 45 01 F0 8B 09 80 28 01 F0 0B 00 00 00 80 67 26          │
172EA0:   │ 63 00 09 80 4D 26 2D 00 30 00 62 00 02 80 0E 00          │
          └────────────────────────────────────────────────────────────┘

          ┌─ EVENT SCRIPT GAP (22 bytes) ────────────────────────────────┐
          │ Event data, script opcodes, and reference IDs that the    │
          │ event engine uses to sequence dialogue triggers.          │
          │                                                           │
172EB0:   │ 09 80 34 24 24 01 AC 84 A3 00  ← event trigger data      │
          │ (09 80 = speaker 0x8009, followed by parameters)          │
          │                                                           │
172EBA:   │ 28 01 AC 04 01 00 00 80 65 27  ← script opcode block     │
          │ (28 01 signature, context 0x8000, pointer 0x2765)         │
          │                                                           │
172EC4:   │ A9 00                           ← dialogue ref index      │
          │ (0x00A9 = links this trigger to the following dialogue)   │
          └────────────────────────────────────────────────────────────┘

          ┌─ DIALOGUE STRING ──────────────────────────────────────────┐
172EC6:   │ [83 26]                      ← 2-byte script prefix       │
172EC8:   │ F4 D5 F2 2D 02 19 54 79     ← 炎使いのエル               │
172ED0:   │ 58 06                        ← クか                       │
172ED0:   │ FF 05 01 01                  ← [br]                       │
172ED4:   │ F3 8A 06 50 10 35 4D 15     ← 遅かったじゃな             │
172EDC:   │ 02 06                        ← いか                       │
172EDE:   │ 00                           ← null terminator            │
          └────────────────────────────────────────────────────────────┘

          ┌─ 48-BYTE TEMPLATE (next dialogue) ─────────────────────────┐
172EDF+1: │ 23 01 F0 8B 01 80 28 01 ...                               │
          └────────────────────────────────────────────────────────────┘

          ┌─ DIALOGUE STRING ──────────────────────────────────────────┐
          │ F8 09 ... (next dialogue text)                             │
          └────────────────────────────────────────────────────────────┘

          ... pattern repeats ...
```

### Reading order

1. **Template** at 0x172E80 → Ptr_A field (`28 01` = 0x0128) tells the engine where the dialogue text is
2. **Script blocks** fill the gap between template and actual text
3. **Dialogue** starts with a 2-byte prefix, contains charIDs + control codes, ends with `00`
4. **Next template** immediately follows the null terminator (possibly with padding)

This template→gap→dialogue→template cycle repeats throughout the entire text region.

---

## See Also

- `TEXT_ENCODING.md` — Full charID table, control code reference, encoding formulas
- `TEXT_REGION_BYTE_ANALYSIS.md` — Statistical analysis of byte types and garbage detection
- `STG_STRUCTURE.md` — Overall chunk layout (graphics, MIPS code, text regions)
- `DECODER_FIXES.md` — How the decoder distinguishes real dialogue from binary garbage
- `DIALOGUE_SYSTEM_ANALYSIS.md` — Complete dialogue system reverse-engineering
