# SYSTEM.CNF Analysis - Arc the Lad 2 (PS1, Japanese)

## File Overview

| Property | Value |
|----------|-------|
| File | `SYSTEM.CNF` |
| Size | 63 bytes |
| Type | PS1 boot configuration (ASCII text) |
| Location | CD-ROM root directory |
| Contains text | **No** -- boot parameters only (not translatable) |

## Purpose

SYSTEM.CNF is the PS1 boot configuration file, read by the BIOS before any game code executes. It specifies which executable to load, the initial stack pointer, and kernel resource limits. Every PS1 disc has this file in the root directory.

## Contents

```
BOOT = cdrom:\SCPS_100.26;1
TCB = 4
EVENT = 10
STACK = 801ffff0
```

## Fields

| Field | Value | Description |
|-------|-------|-------------|
| `BOOT` | `cdrom:\SCPS_100.26;1` | Path to the main executable on disc. `;1` is the ISO 9660 file version number. |
| `TCB` | `4` | Thread Control Block count -- maximum 4 concurrent kernel threads. PS1 default. |
| `EVENT` | `10` | Event Control Block count -- maximum 16 (`0x10`) kernel event handlers. PS1 default. |
| `STACK` | `801ffff0` | Initial stack pointer (`0x801FFFF0`). Top of PS1's 2 MB RAM minus 16 bytes. |

### BOOT Filename

The executable name `SCPS_100.26` follows Sony's PS1 naming convention:

| Component | Meaning |
|-----------|---------|
| `SC` | Sony Computer Entertainment |
| `PS` | PlayStation |
| `100.26` | Title catalog number |

This identifies the disc as a **Japanese retail release** (SCPS = Japan region). Other region prefixes include SCUS (North America) and SCES (Europe).

### Stack Pointer

The STACK value `0x801FFFF0` matches the SP field in the SCPS_100.26 PSX-EXE header exactly. This leaves 16 bytes (one word at `0x801FFFFC`) before the 2 MB RAM boundary at `0x80200000`, which is standard -- the kernel reserves the topmost word.

### TCB and EVENT

Both values are PS1 BIOS defaults. The kernel pre-allocates `TCB × 192` bytes and `EVENT × 32` bytes from low memory for thread and event management structures. At TCB=4 and EVENT=16, this consumes 896 bytes -- negligible overhead.

## Boot Sequence

Per PSX SPX, the PS1 BIOS boot sequence is:

1. BIOS reads SYSTEM.CNF from the disc root directory
2. Parses `BOOT` to determine the executable path
3. Allocates TCB and EVENT kernel structures
4. Loads the PSX-EXE file (`SCPS_100.26`) into RAM at the address specified in the EXE header (`0x800C1400`)
5. Sets the stack pointer to the STACK value (`0x801FFFF0`)
6. Jumps to the entry point specified in the EXE header (`0x80167E1C`)

## Relationship to Other Files

| File | Relationship |
|------|-------------|
| **SCPS_100.26** | The executable loaded by this boot config |

## Relevance to Korean Translation

**SYSTEM.CNF does not need to be modified for text translation.** It contains only boot parameters. If the executable filename were changed (unlikely), this file would need a corresponding update, but the standard approach is to keep the original filename.
