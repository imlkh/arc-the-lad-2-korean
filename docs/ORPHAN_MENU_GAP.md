# Orphan Menu Translation Gap

## Overview

There is a gap between detected orphan menus and translated orphan menus in STG files. This document explains the root causes and solutions.

## Current Status (2026-02-07)

| STG File | Orphan Menus | Padding | Event-Script | Total Non-Template | Translated | Missing |
|----------|--------------|---------|--------------|-------------------|------------|---------|
| S100.STG | 76 | 7 | 33 | 116 | 15 | 101 |
| SG00.STG | 403 | 26 | 144 | 573 | ~20 | ~553 |

**Note**: Padding region (0xA0000-0xB0000) and Event Script region (0xB0000-0xB4000) now scanned (2026-02-07).

## What Are Orphan Menus?

Orphan menus are standalone menu texts with the `[0x00A9]` opcode that are **not** tied to dialogue templates. They include:

- **Navigation prompts**: Stairs, ladders, warp zones, exits
- **Yes/No confirmations**: Take child? Write in diary?
- **Tutorial menus**: Combat basics, item usage
- **System prompts**: Switches, treasure boxes

Example:
```
0x00232242 [0x00A9] [script:E7 02][box:system]下り階段があります[br][opt]下る[br][opt]やめる[box:close]
```

## Orphan Menu Detection

### Detection Rule

Real menus are identified by the `[br][opt]` pattern (each option on its own line):

```
Real menu:    質問？[br][opt]はい[br][opt]いいえ     ← Options on separate lines
Not a menu:   名[opt]前[opt]ゴルザ                   ← Column formatting
Not a menu:   プロディアス[opt]ハンターズギルド      ← Dialogue pause
```

### Pattern Analysis

| Pattern | Type | Count (S100) | Example |
|---------|------|--------------|---------|
| `[br][opt]` | **Real Menu** | 76 | `質問？[br][opt]はい[br][opt]いいえ` |
| `[opt][opt]` | Table formatting | 7 | `名[opt]前[opt][opt]ゴルザ` |
| `漢[opt]字` | Column spacing | 5 | `報[opt]酬[opt]540G` |
| Other `[opt]` | Dialogue pause | 9 | `つい[opt]今さっきだ` |

### Implementation

In `decode_text.py`, orphan menu detection uses:

```python
# Only capture REAL menus with [br][opt] pattern
if text and '[br][opt]' in text:
    # This is a real menu with options on separate lines
    dialogues.append((pos + 2, consumed, text, 0x00A9))
```

### Filtered Out (Not Real Menus)

The `[opt]` control code has three different uses in the game. Only one is a real menu:

#### 1. Real Menus (KEEP) - `[br][opt]` pattern

Each option appears on its own line, player can select one:

```
この子供を連れて行きますか？[br][opt]はい[br][opt]いいえ
```

Displayed as:
```
┌─────────────────────────────┐
│ この子供を連れて行きますか？ │
│ ▶ はい                      │
│   いいえ                    │
└─────────────────────────────┘
```

#### 2. Table Formatting (FILTER) - Column spacing

Used like a tab character to align columns in bounty hunter info cards:

```
[box:system]名[opt]前[opt]ゴルザ[opt][opt][opt][opt]スケルトン
報[opt]酬[opt]540G
居場所[opt]インディゴス北の廃墟の町
得意技[opt]チャージ
```

Displayed as:
```
┌──────────────────────────────────┐
│ 名  前   ゴルザ      スケルトン  │  ← Name: Gorza, Type: Skeleton
│ 報  酬   540G                    │  ← Reward: 540G
│ 居場所   インディゴス北の廃墟の町 │  ← Location: Ruins north of Indigos
│ 得意技   チャージ                │  ← Special skill: Charge
└──────────────────────────────────┘
```

The `[opt]` creates spacing between "名" and "前" (which together mean "name"), and between labels and values.

#### 3. Dialogue Pauses (FILTER) - Dramatic effect

Used for speech rhythm, hesitation, or emphasis in dialogue:

```
つい[opt]今さっきだ        ← "Just... now" (hesitation)
よおっ[opt]マスター        ← "Hey... Master" (casual greeting pause)
プロディアス[opt]ハンターズギルド  ← "Prodias... Hunter's Guild" (announcement style)
```

These create a brief pause when the text is displayed, adding dramatic effect to the speech.

#### Summary

| Type | Pattern | Purpose | Action |
|------|---------|---------|--------|
| Real menu | `[br][opt]` | Selectable options on separate lines | **KEEP** |
| Table | `[opt][opt]` or `漢[opt]字` | Column alignment (like tab) | Filter |
| Pause | Other `[opt]` | Speech rhythm/dramatic effect | Filter |

## Root Causes of Translation Gap

### 1. Timeline Mismatch

Translation files were created **before** orphan menu detection was added.

### 2. Cross-File Translation Gap

System prompts are translated in `BEAM_corrections.txt` but not in STG files:

| Text | In BEAM_corrections.txt | In S100_STG.txt |
|------|------------------------|-----------------|
| 下り階段があります | Yes | Added (2026-02-07) |
| スイッチがあります | Yes | Added (2026-02-07) |
| 出口です | Yes | Added (2026-02-07) |

## Solution Applied

System prompts were added to `S100_STG.txt` for cross-chunk matching:

```
0x00811976 [0x00A9] [script:AE 01][box:system]스위치가 있습니다...
0x00811F1A [0x00A9] [script:E7 02][box:system]내려가는 계단이 있습니다...
0x00811F44 [0x00A9] [script:FC 02][box:system]올라가는 계단이 있습니다...
0x00811F6E [0x00A9] [script:12 03][box:system]출구입니다...
0x00811F9A [0x00A9] [script:25 03][box:system]사다리가 있습니다...
0x00811FE2 [0x00A9] [script:4B 03][box:system]워프존이 있습니다...
0x0017222A [0x00A9] [script:3F 20][box:system]일기장이 있습니다...
0x000BC77E [0x00A9] [script:57 48]이 아이를 데려가시겠습니까?...
```

Cross-chunk matching in `patch_variable_length_multi.py` applies these translations to identical text in all chunks.

## Remaining Work

Approximately 61 orphan menus in S100.STG still need translation:
- Tutorial menus (combat basics, item usage)
- Dialogue choices (もちろん！, やっぱり待った)
- Minor system prompts

## Files Reference

| File | Purpose |
|------|---------|
| `python/decode/decode_text.py` | Orphan menu detection (`[br][opt]` filter) + Event Script region scanning |
| `translated/ko/S100_STG.txt` | Translation file with system prompts |
| `translated/ko/BEAM_corrections.txt` | Reference translations for system prompts |
| `python/patch_variable_length_multi.py` | Patcher with cross-chunk matching |

## Technical Details

### Scanning Regions

| Region | Offset | Size | Detection Method |
|--------|--------|------|------------------|
| Text Region | 0xB4000-0xBC7FF | 34KB | Template-driven + orphan menu scan |
| Event Script | 0xB0000-0xB4000 | 16KB | A9 00 marker with strict validation |
| Padding | 0xA0000-0xB0000 | 64KB | A9 00 marker with strict validation |

### Context Opcodes

| Opcode | Meaning |
|--------|---------|
| 0x00A0 | Padding region dialogue |
| 0x00A9 | Orphan menu in Text Region |
| 0x00B0 | Event Script region dialogue |
| 0xFFFE | System (template-associated) |
| 0x80XX | Speaker-specific (template-associated) |
