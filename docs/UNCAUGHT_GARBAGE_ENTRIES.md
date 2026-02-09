# Uncaught Garbage Entries (2026-02-09)

123 entries (30 unique strings) across 11 STG files that pass all decoder filters
and invalid report patterns. These are shared code block artifacts, not real dialogue.

## Summary

| # | Pattern | Count | STG Files | Script Tag |
|---|---------|-------|-----------|------------|
| 1 | めあ団 (+ variants) | 15 | S700, SB00, SD00, SE00 | mixed |
| 2 | やあ団C | 19 | SB00, SD00 | mixed |
| 3 | オゼヲ | 11 | S200, S700, S800, SB00, SD00, SG00 | always 55 87 |
| 4 | あわしあ | 24 | S700 only | always 81 28 |
| 5 | めありジマ (+ いギ prefix) | 7 | S200, S700, S800, SI00 | 06 00 / FE 5A / 47 00 |
| 6 | オいめあげグI/J | 4 | S200, S700, S800 | always AA 00 |
| 7 | ぴしぷしよ | 4 | S700, S800 | 20 80 / 80 80 |
| 8 | ぷずぷずせ | 1 | S200 | 36 36 |
| 9 | しけしけせ | 1 | S800 | A0 08 |
| 10 | げいう | 20 | S700, S800, SA00, SB00, SC00, SD00, SE00, SF00 | always AC 00 |
| 11 | えおよ | 2 | SB00, SD00 | always A9 00 |
| 12 | ぴおよ | 1 | S800 | A9 00 |
| 13 | えあを | 3 | S200, S700, SD00 | always FF FF |
| 14 | ぎしを | 1 | S700 | FF FF |
| 15 | へつけ | 1 | S700 | A2 00 |
| 16 | 渡みギC | 2 | S700, S800 | always F5 8B |
| 17 | カじあギじ | 1 | S200 | 44 8C |
| 18 | ウえあギじ | 1 | S700 | 44 8C |
| 19 | ヘおあギじ | 1 | S700 | 44 8C |
| 20 | てギめあカゼI | 1 | S700 | 01 00 |
| 21 | 火そ火そボ | 1 | SA00 | A9 0F |
| 22 | 火み火みボ | 1 | SF00 | A9 20 |
| 23 | ョぬョぬボ | 1 | SA00 | 67 17 |

## By STG File

| STG | Count | Top Patterns |
|-----|-------|-------------|
| S700 | 44 | あわしあ x24, めあ団 x6, めありジマ x3, げいう x2 |
| SD00 | 22 | やあ団C x9, めあ団 x6, オゼヲ x3, げいう x2 |
| SB00 | 14 | やあ団C x10, オゼヲ x2, めあ団 x1, げいう x1 |
| SF00 | 10 | げいう x9, 火み火みボ x1 |
| S800 | 10 | めありジマ x2, ぴしぷしよ x2, オゼヲ x1, オいめあ x1, ... |
| S200 | 7 | オゼヲ x3, めありジマ x1, オいめあ x1, ぷずぷずせ x1, ... |
| SA00 | 5 | げいう x3, 火そ火そボ x1, ョぬョぬボ x1 |
| SE00 | 3 | めあ団 x2, げいう x1 |
| SG00 | 1 | オゼヲ x1 |
| SC00 | 1 | げいう x1 |
| SI00 | 1 | めありジマ x1 |

Clean: S100, S300, S400, S500, S600, S900, SH00, SJ00

## Notable Patterns

- **げいう** (20 entries, 8 STGs): Always `[script:AC 00]`. Most widespread — likely a
  shared code block decoded as text. Appears near shop/inn NPC dialogue.
- **オゼヲ** (11 entries, 6 STGs): Always `[script:55 87]`. Another shared block artifact.
- **あわしあ** (24 entries, S700 only): Always `[script:81 28]`. Chunk-specific in S700
  chunk 29 (offsets 0x01611835-0x01614705). Likely a localized MIPS data table.
- **めあ団ぷあれギ** (10 exact matches): NOR+LWL block artifacts that survived the
  exclusion zone — these instances are in chunks where the block signature doesn't have
  the LW parameter table at the expected offset, so validation failed.
- **火X火Xボ / ョぬョぬボ**: Shop sound effect data tables decoded as text.

## Full Entry List

### Pattern 1: めあ団 (15 entries)

```
SD00 0x00D3EB0C [0x800A] [script:24 1D]めあ団ぷあれギ
SD00 0x00D3EB50 [0x800A] [script:6A FF]めあ団ぷあれギ
SD00 0x00D3EB84 [0x800A] [script:01 80]あギてそめあ団めあ団ぷあれギ
SD00 0x00D3EB40 [0x800A] [script:01 80]あギ管めあ団じ
SD00 0x00D3EBE8 [0x800A] [script:02 80]あギぷそめあ団I
SD00 0x00D3D92A [0x8000] [script:05 80]あギ＋おめあ団I
SB00 0x0075866A [0x8013] [script:05 80]あギやしめあ団ジ
S700 0x01268098 [0x00B4] [script:F3 11]めあ団ぷあれギ
S700 0x016102E2 [0x00B4] [script:68 0C]めあ団ぷあれギ
S700 0x01610430 [0x00B4] [script:0F 0D]めあ団ぷあれギ
S700 0x016105A6 [0x00B4] [script:DE 0D]めあ団ぷあれギ
S700 0x01611A1E [0x8001] [script:2C 8C]めあ団ぷあれギ
S700 0x016155EC [0x0006] [script:93 35]めあ団ぷあれギ
SE00 0x00C83DBA [0x00B4] [script:3C 06]めあ団ぷあれギ
SE00 0x00D40770 [0x00B4] [script:41 06]めあ団ぷあれギ
```

### Pattern 2: やあ団C (19 entries)

```
SB00 0x007585B8 [0x8013] [script:AD 0A]やあ団C
SB00 0x007585E0 [0x8013] [script:CA 0A]やあ団C
SB00 0x00758608 [0x8013] [script:E7 0A]やあ団C
SB00 0x00758630 [0x8013] [script:F2 0A]やあ団C
SB00 0x00758658 [0x8013] [script:A0 0A]やあ団C
SB00 0x00758900 [0x8013] [script:9B 13]やあ団C
SB00 0x00758928 [0x8013] [script:B4 13]やあ団C
SB00 0x00758950 [0x8013] [script:C3 13]やあ団C
SB00 0x00758978 [0x8013] [script:DE 13]やあ団C
SB00 0x007589A0 [0x8013] [script:62 13]やあ団C
SD00 0x00D3D878 [0x8000] [script:72 19]やあ団C
SD00 0x00D3D8A0 [0x8000] [script:72 19]やあ団C
SD00 0x00D3D8C8 [0x8000] [script:72 19]やあ団C
SD00 0x00D3D8F0 [0x8000] [script:72 19]やあ団C
SD00 0x00D3D918 [0x8000] [script:72 19]やあ団C
SD00 0x00D3EB2E [0x800A] [script:24 18]やあ団C
SD00 0x00D3EB72 [0x800A] [script:2D 18]やあ団C
SD00 0x00D3EBAE [0x800A] [script:3C 18]やあ団C
SD00 0x00D3EBD6 [0x800A] [script:40 18]やあ団C
```

### Pattern 3: オゼヲ (11 entries)

```
S200 0x003AB7B4 [0x8005] [script:55 87]オゼヲ
S200 0x00C84288 [0x8014] [script:55 87]オゼヲ
S200 0x00C84368 [0x8014] [script:55 87]オゼヲ
S700 0x005E31DA [0x800A] [script:55 87]オゼヲ
S800 0x005230D2 [0x8006] [script:55 87]オゼヲ
SB00 0x00757814 [0x8013] [script:55 87]オゼヲ
SB00 0x00758584 [0x8013] [script:55 87]オゼヲ
SD00 0x00D3D750 [0x8000] [script:55 87]オゼヲ
SD00 0x00D3EF06 [0x800A] [script:55 87]オゼヲ
SD00 0x00D3FA26 [0x800A] [script:55 87]オゼヲ
SG00 0x0069F860 [0x8006] [script:55 87]オゼヲ
```

### Pattern 4: あわしあ (24 entries, all S700 chunk 29)

```
S700 0x01611835 [0x0006] [script:81 28]あわしあ
S700 0x016118BB [0x8001] [script:81 28]あわしあ
S700 0x016119E3 [0x0006] [script:81 28]あわしあ
S700 0x01612081 [0x0006] [script:81 28]あわしあ
S700 0x016121AD [0x0006] [script:81 28]あわしあ
S700 0x016122EB [0x0006] [script:81 28]あわしあ
S700 0x01612375 [0x8001] [script:81 28]あわしあ
S700 0x016125DB [0x0006] [script:81 28]あわしあ
S700 0x01612743 [0x8001] [script:81 28]あわしあ
S700 0x01612853 [0x0006] [script:81 28]あわしあ
S700 0x0161298B [0x0006] [script:81 28]あわしあ
S700 0x01612A4D [0x0006] [script:81 28]あわしあ
S700 0x01612B0F [0x0006] [script:81 28]あわしあ
S700 0x01612C87 [0x0006] [script:81 28]あわしあ
S700 0x01612E13 [0x0006] [script:81 28]あわしあ
S700 0x01612FA7 [0x0006] [script:81 28]あわしあ
S700 0x01613055 [0x0006] [script:81 28]あわしあ
S700 0x016131F5 [0x0006] [script:81 28]あわしあ
S700 0x01613359 [0x0006] [script:81 28]あわしあ
S700 0x01613477 [0x0006] [script:81 28]あわしあ
S700 0x016135F5 [0x0006] [script:81 28]あわしあ
S700 0x01613715 [0x0006] [script:81 28]あわしあ
S700 0x01613901 [0x0006] [script:81 28]あわしあ
S700 0x01614705 [0x0006] [script:81 28]あわしあ
```

### Pattern 5: めありジマ (7 entries)

```
S200 0x003AB892 [0x8005] [script:06 00]めありジマ
S700 0x005E2EC8 [0x800A] [script:06 00]めありジマ
S700 0x005E30FC [0x800A] [script:06 00]めありジマ
S700 0x005E358C [0x800A] [script:47 00]いギめありジマ
S800 0x00522F10 [0x8006] [script:06 00]めありジマ
S800 0x00523484 [0x8006] [script:47 00]いギめありジマ
SI00 0x0022F9CC [0x8007] [script:FE 5A]めありジマ
```

### Pattern 6: オいめあげグI/J (4 entries)

```
S200 0x003AB8AA [0x8005] [script:AA 00]オいめあげグJ
S700 0x005E2EE0 [0x800A] [script:AA 00]オいめあげグI
S700 0x005E3114 [0x800A] [script:AA 00]オいめあげグJ
S800 0x00522F28 [0x8006] [script:AA 00]オいめあげグI
```

### Pattern 7-9: Repeating kana pairs (6 entries)

```
S700 0x005E3406 [0x800A] [script:20 80]ぴしぷしよ
S700 0x005E3520 [0x800A] [script:80 80]ぴしぷしよ
S800 0x005232FE [0x8006] [script:20 80]ぴしぷしよ
S800 0x00523418 [0x8006] [script:80 80]ぴしぷしよ
S200 0x003ABA2E [0x8005] [script:36 36]ぷずぷずせ
S800 0x005236CA [0x8006] [script:A0 08]しけしけせ
```

### Pattern 10: げいう (20 entries)

```
SB00 0x00233BA8 [0x8015] [script:AC 00]げいう
SC00 0x00234C6E [0x8015] [script:AC 00]げいう
SD00 0x00234616 [0x800A] [script:AC 00]げいう
SD00 0x0075BC6C [0x800A] [script:AC 00]げいう
SE00 0x0023191C [0x8006] [script:AC 00]げいう
S700 0x002F0B30 [0x8015] [script:AC 00]げいう
S700 0x005E3916 [0x800A] [script:AC 00]げいう
S800 0x0052381A [0x8006] [script:AC 00]げいう
SA00 0x00173F84 [0x8006] [script:AC 00]げいう
SA00 0x00174F00 [0x8006] [script:AC 00]げいう
SA00 0x0017684E [0x8006] [script:AC 00]げいう
SF00 0x0149CA7C [0xFFFE] [script:AC 00]げいう
SF00 0x0149CC76 [0xFFFE] [script:AC 00]げいう
SF00 0x0178E2C6 [0xFFFE] [script:AC 00]げいう
SF00 0x01BF98AA [0x8001] [script:AC 00]げいう
SF00 0x01BF9BC4 [0x8001] [script:AC 00]げいう
SF00 0x01BF9E88 [0x8001] [script:AC 00]げいう
SF00 0x01BFA0D6 [0x8001] [script:AC 00]げいう
SF00 0x01BFAB8E [0xFFFE] [script:AC 00]げいう
SF00 0x01EEBEDE [0x8000] [script:AC 00]げいう
```

### Pattern 11-15: Short 3-char nonsense (8 entries)

```
SB00 0x007577FA [0x8013] [script:A9 00]えおよ
SD00 0x00D3D736 [0x8000] [script:A9 00]えおよ
S800 0x00523008 [0x8006] [script:A9 00]ぴおよ
SD00 0x00D3F6CE [0x800A] [script:FF FF]えあを
S200 0x005E1706 [0x8005] [script:FF FF]えあを
S700 0x0178EF82 [0x8016] [script:FF FF]えあを
S700 0x0178E6F0 [0x8016] [script:FF FF]ぎしを
S700 0x0178E8D8 [0x8016] [script:A2 00]へつけ
```

### Pattern 16-20: Mixed MIPS register patterns (5 entries)

```
S700 0x005E2F32 [0x800A] [script:F5 8B]渡みギC
S800 0x00522F7A [0x8006] [script:F5 8B]渡みギC
S200 0x003AB882 [0x8005] [script:44 8C]カじあギじ
S700 0x005E2EB8 [0x800A] [script:44 8C]ウえあギじ
S700 0x005E30EC [0x800A] [script:44 8C]ヘおあギじ
S700 0x0178E8EE [0x8016] [script:01 00]てギめあカゼI
```

### Pattern 21-23: Sound/data table artifacts (3 entries)

```
SA00 0x00174090 [0x8006] [script:A9 0F]火そ火そボ
SF00 0x0149CB88 [0x800A] [script:A9 20]火み火みボ
SA00 0x0017500C [0x8006] [script:67 17]ョぬョぬボ
```

## Byte-Level Analysis

All 123 entries come from **3 types of shared code blocks** replicated identically
into every chunk's text region. The raw bytes are constant across all instances.

### Type A: Command Dispatch Table (CDT) — 26 entries

Structure: `A2 00 [ptr] 00 00 00 00 | A9 00 [ptr] 00 00 00 00 | AC 00 32 02 03 00 ...`

A table of event handler opcodes (A2→A9→AC→AA). The `AC 00` entry's parameter
bytes `32 02 03` decode as "げいう". The `A9 00` entry's parameters decode as
えおよ/ぴおよ. A variant with `AC 00 32 01 03 00` produces 火X火Xボ entries.

**Key byte signature**: `AC 00 32 02 03 00` (6 bytes, 100% constant across all 20
げいう entries). Always preceded by `A9 00 XX XX 00 00 00 00`.

| Artifact | Count | From bytes |
|----------|-------|-----------|
| げいう | 20 | `AC 00` + `32 02 03 00` |
| えおよ | 2 | `A9 00` + `04 05 26 00` |
| ぴおよ | 1 | `A9 00` + `44 05 26 00` (variant) |
| 火そ火そボ | 1 | `A9 0F` + `E1 0F E1 0F 92 00` |
| 火み火みボ | 1 | `A9 20` + `E1 20 E1 20 92 00` |
| ョぬョぬボ | 1 | `67 17` + `9F 17 9F 17 92 00` (variant) |

### Type B: Template Parameter Block — 34 entries

Structure: `... 24 01 F3 81 A3 00 | 24 01 F3 81 AE 00 | ... 22 01 F3 81 45 01 2A 80 ...`

Template control data with opcode variants `22 01`/`24 01`/`26 01` (close to `23 01`
template signature). The bytes `F3 81` decode as kanji 団 via 2-byte charmap encoding.

**Key byte signatures**:
- `22 01 F3 81 45 01 2A 80` (8 bytes, constant) → めあ団ぷあれギ
- `24 01 F3 81 A3 00` (6 bytes, constant) → やあ団C

| Artifact | Count | From bytes |
|----------|-------|-----------|
| めあ団ぷあれギ | 10 | `22 01 F3 81 45 01 2A 80 00 80 28 01 2A 00` |
| やあ団C | 19 | `24 01 F3 81 A3 00` |
| あギ＋おめあ団I | 1 | `01 80` prefix + `22 01 F3 81` |
| あギやしめあ団ジ | 1 | (variant) |
| あギ管めあ団じ | 1 | (variant) |
| あギてそめあ団めあ団ぷあれギ | 1 | (double block) |
| あギぷそめあ団I | 1 | (variant) |

### Type C: Various Control/Jump Blocks — 63 entries

**C.1: C0 Jump Table** — `C0 00 55 87 55 87 7D 00` (8 bytes, 100% constant before)

| Artifact | Count | From bytes |
|----------|-------|-----------|
| オゼヲ | 11 | `55 87 55 87 7D 00` (preceded by `C0 00`) |

**C.2: あわしあ Block** — `26 01 2C 8C 00 81 28 01 2C 0C 01 00 07 00`

| Artifact | Count | From bytes |
|----------|-------|-----------|
| あわしあ | 24 | `01 2C 0C 01 00` (bytes at +2, constant; S700 chunk 29 only) |

**C.3: MIPS LW/SW Instruction Blocks** — `D3 00 44 8C` context, `44 0C 45 0C 26 00`

| Artifact | Count | From bytes |
|----------|-------|-----------|
| めありジマ | 5 | `06 00 22 01 28 85 6F 00` (constant) |
| いギめありジマ | 2 | `47 00` prefix variant |
| オいめあげグI | 2 | `AA 00 55 02 22 01 32 81` |
| オいめあげグJ | 2 | (variant, J vs I) |
| ぴしぷしよ | 4 | `20 80 44 0C 45 0C 26 00` (constant) |
| ぷずぷずせ | 1 | (variant) |
| しけしけせ | 1 | (variant) |
| 渡みギC | 2 | `F5 8B F5 8B 20 80` |
| カじあギじ | 1 | `44 8C XX XX 01 80 35 00` |
| ウえあギじ | 1 | (variant) |
| ヘおあギじ | 1 | (variant) |
| てギめあカゼI | 1 | `01 00 13 80 22 01 56 87` |

**C.4: FF FF Boundary Blocks** — `67 00 58 80 62 80 08 80 01 80 63 00 FF FF`
(28 bytes of context 100% identical across all 3 えあを instances)

| Artifact | Count | From bytes |
|----------|-------|-----------|
| えあを | 3 | `FF FF 04 01 2D 00` (constant) |
| ぎしを | 1 | `FF FF 30 0C 2D 00` |
| へつけ | 1 | `A2 00 1D 12 09 00` |

## Recommended Fix: Exact-Match Blocklist

All 30 unique strings are nonsense — none are real Japanese words. Since the underlying
code blocks are byte-for-byte identical across chunks, the same text is always produced.

Add to `_is_garbage_text()` in `decode_text.py`:

```python
SHARED_BLOCK_ARTIFACTS = {
    # Type A: Command Dispatch Table (26 entries)
    'げいう', 'えおよ', 'ぴおよ',
    '火そ火そボ', '火み火みボ', 'ョぬョぬボ',
    # Type B: Template Parameter Block (34 entries)
    'めあ団ぷあれギ', 'やあ団C',
    'あギやしめあ団ジ', 'あギ＋おめあ団I', 'あギ管めあ団じ',
    'あギてそめあ団めあ団ぷあれギ', 'あギぷそめあ団I',
    # Type C.1: C0 Jump Table (11 entries)
    'オゼヲ',
    # Type C.2: あわしあ Block (24 entries)
    'あわしあ',
    # Type C.3: MIPS LW/SW Blocks (22 entries)
    'めありジマ', 'いギめありジマ',
    'オいめあげグI', 'オいめあげグJ',
    'ぴしぷしよ', 'ぷずぷずせ', 'しけしけせ',
    '渡みギC', 'カじあギじ', 'ウえあギじ', 'ヘおあギじ',
    'てギめあカゼI',
    # Type C.4: FF FF Boundary (5 entries)
    'えあを', 'ぎしを', 'へつけ',
}
```

This catches all 123 entries with zero false-positive risk.

For additional robustness, the top-3 byte-level exclusion zones could also be added:
1. CDT marker `AC 00 32 0[12] 03 00` → 26 entries
2. Template param `22/24 01 F3 81` → 34 entries
3. C0 jump `C0 00 55 87 55 87` → 11 entries
These 3 alone cover 71/123 entries at the byte level before decoding.
