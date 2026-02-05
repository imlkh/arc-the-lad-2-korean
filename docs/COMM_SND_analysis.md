# COMM.SND Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `COMM.SND` |
| Size | 329,728 bytes (322.0 KB, 0x50800) |
| Sectors | 161 CD-ROM sectors (2,048 bytes each) |
| Type | PS1 VAB sound bank (combined VH+VB) |
| Magic | `pBAV` (standard PS1 VAB header) |
| Contains text | **No** -- instrument definitions + SPU ADPCM audio samples |

## Verdict: No Translatable Text

COMM.SND is a **common sound bank** -- a PS1 VAB (Voice Application Bank) file containing instrument/SFX definitions and compressed audio waveforms. "COMM" stands for "common" -- this bank is loaded across multiple game scenes for shared sound effects, battle audio, and musical instrument samples. There are **0 text strings**.

## Purpose

COMM.SND provides the game's shared audio resources:
- Battle sound effects (weapon hits, spell casting, UI clicks)
- Common musical instrument samples (for battle jingles, victory themes, stingers)
- Multi-sample pitched instruments with chromatic key-splitting
- The bank is loaded into PS1 SPU (Sound Processing Unit) RAM alongside scene-specific sound banks

## File Layout

| Offset Range | Size | Region | Description |
|-------------|------|--------|-------------|
| `0x00000`-`0x0001F` | 32 bytes | **VAB Header** | Magic, version, bank ID, program/tone/VAG counts |
| `0x00020`-`0x0081F` | 2,048 bytes | **Program Attributes** | 128 program slots (21 active) |
| `0x00820`-`0x1081F` | 65,536 bytes (64 KB) | **Tone Attributes** | 2,048 tone slots (92 active) |
| `0x10820`-`0x10A1F` | 512 bytes | **VAG Size Table** | 256 x 16-bit sample size entries |
| `0x10A20`-`0x507FF` | 261,600 bytes (255.5 KB) | **Waveform Data** | SPU ADPCM compressed audio samples |

### Shannon Entropy

| Region | Entropy | Interpretation |
|--------|---------|----------------|
| Full file | 5.73 bits/byte | Moderate (mix of structured headers and compressed audio) |
| VAB Header + Programs | ~4.0 bits/byte | Structured header data |
| Tone Attributes | ~2.5 bits/byte | Many zero slots |
| Waveform Data | ~7.0 bits/byte | High -- compressed ADPCM audio |

## VAB Header (0x00000 - 0x0001F)

| Offset | Size | Field | Value | Description |
|--------|------|-------|-------|-------------|
| 0x00 | 4 | Magic | `pBAV` | PS1 VAB format identifier |
| 0x04 | 4 | Version | 7 | VAB format version |
| 0x08 | 4 | VAB ID | 0 | Bank identifier |
| 0x0C | 4 | VB Size | 303,520 | Declared waveform data size |
| 0x10 | 2 | Reserved | `0xEEEE` | Game-specific flag (non-standard) |
| 0x12 | 2 | Programs | 21 | Active instrument/SFX programs |
| 0x14 | 2 | Tones | 92 | Active sample-to-key mappings |
| 0x16 | 2 | VAGs | 92 | Declared ADPCM sample count |
| 0x18 | 1 | Master Vol | 127 | Maximum volume |
| 0x19 | 1 | Master Pan | 64 | Center pan |
| 0x1A-0x1F | 6 | Reserved | 0 | Padding |

### VB Size Discrepancy

The declared waveform size (303,520 bytes) exceeds the actual available data (261,600 bytes) by 41,920 bytes. This indicates the file may be **truncated** or the VB size field includes padding that extends beyond the file boundary. The last ~21 VAG samples (indices 71-92) may be missing or incomplete.

## Program Attributes (0x00020 - 0x0081F)

128 program slots, each 16 bytes. Only 21 are active (programs 0-20):

### Program Summary

| Program | Tones | Type | Description |
|---------|-------|------|-------------|
| 0 | 1 | Single-sample SFX | Short sound effect |
| 1 | 1 | Single-sample SFX | Short sound effect |
| 2 | 16 | Multi-sample instrument | Full MIDI key range (0-127), 8-note key splits |
| 3 | 15 | Multi-sample instrument | Per-note samples (MIDI 60-74 range) |
| 4 | 15 | Multi-sample instrument | Per-note samples |
| 5 | 15 | Multi-sample instrument | Per-note samples |
| 6-13 | 1 each | Single-sample SFX | Individual sound effects |
| 14 | 6 | Multi-sample | 6-zone key-split |
| 15 | 1 | Single-sample SFX | Sound effect |
| 16 | 10 | Multi-sample | 10-zone key-split |
| 17-20 | 1 each | Single-sample SFX | Individual sound effects |

All programs share: volume=127 (max), pan=64 (center), mode=0x13.

### Multi-Sample Instruments (Programs 2-5)

These programs use chromatic key-splitting, where different MIDI note ranges map to different base audio samples. This is characteristic of **pitched instruments** (pianos, strings, brass) or **voice/vocal samples** where different pitches need different recordings for natural sound quality.

- **Program 2**: 16 zones spanning the full MIDI range -- likely a general-purpose melodic instrument
- **Programs 3-5**: 15 zones each with per-note mapping -- likely vocal or special instrument samples used in battle music stingers

## Tone Attributes (0x00820 - 0x1081F)

2,048 tone attribute slots (32 bytes each), with 92 active entries. Each tone defines:

| Field | Description |
|-------|-------------|
| Priority | SPU voice allocation priority |
| Mode | Playback mode (one-shot, sustain, release) |
| Volume | Tone volume (0-127) |
| Pan | Tone stereo position (0-127, 64=center) |
| Center Note | MIDI note for unity-pitch playback |
| Center Fine | Fine tuning offset |
| Note Low / High | MIDI key range for this tone |
| ADSR1, ADSR2 | PS1 SPU envelope (Attack/Decay/Sustain/Release) |
| VAG Index | Index into the waveform data for this tone's sample |

## VAG Size Table (0x10820 - 0x10A1F)

256 x 16-bit entries. Per PSX SPX, this table provides the size (in 8-byte units) of each VAG sample in the waveform data region. The game's sound driver uses this table to calculate SPU RAM offsets for each sample.

## Waveform Data (0x10A20 - 0x507FF)

### SPU ADPCM Format

PS1 audio uses Sony's SPU ADPCM compression:

| Property | Value |
|----------|-------|
| Block size | 16 bytes |
| Samples per block | 28 PCM samples |
| Compression ratio | ~3.5:1 (vs 16-bit PCM) |
| Bit depth | 4-bit ADPCM |

Each 16-byte block:
```
Byte 0: Shift/range (bits 0-3) + filter (bits 4-5)
Byte 1: Flags (00=normal, 01=loop end, 02=loop+repeat, 03=loop start, 07=terminator)
Bytes 2-15: 14 bytes of packed 4-bit ADPCM data (28 samples)
```

### Sample Detection

| Metric | Value |
|--------|-------|
| Detected VAG samples (via end markers) | 71 |
| Declared VAG count | 92 |
| Unique VAG indices referenced by tones | 91 |
| Estimated total audio duration | ~21 seconds (at 22050 Hz) |
| Individual sample range | ~18 ms to ~2.7 seconds |

The discrepancy between detected (71) and declared (92) samples, combined with the VB size field exceeding the file size, suggests the waveform region is truncated. The missing samples (indices 71-91) may be provided by the game's CD-ROM streaming system or were trimmed during disc mastering.

## Relationship to Other Files

| File | Relationship |
|------|-------------|
| **COMM.DAT** | Battle animation module -- loaded alongside COMM.SND during battle scenes |
| **COMM.IMG** | Font/sprite texture atlas -- unrelated to sound |
| **SCPS_100.26** | Main executable -- contains the sound driver that loads COMM.SND into SPU RAM |
| **S*.STG** | Stage files -- may contain stage-specific sound banks that supplement COMM.SND |

## PS1 Sound Architecture Context

Per PSX SPX, the PS1 SPU has 512 KB of dedicated sound RAM. Sound banks are uploaded to SPU RAM by the CPU via DMA channel 4. The SPU can play up to 24 voices simultaneously, each reading ADPCM data from SPU RAM.

COMM.SND's waveform data (~255 KB) occupies roughly half of SPU RAM, leaving room for:
- Scene-specific sound banks (music, ambient, dialogue)
- CD-XA streaming audio buffer
- Reverb work area

## Relevance to Korean Translation

**COMM.SND does not need to be modified for text translation.** It contains only audio data (instrument definitions and compressed sound samples). The file has no text content of any kind.

If the game has voice-acted dialogue stored as VAG samples (unlikely in this bank -- COMM.SND is for effects and instruments), that would be a separate localization concern from text translation.
