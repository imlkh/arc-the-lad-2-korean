# Changelog

All notable changes to the Arc the Lad II Korean translation patch.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this
project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0-beta] - 2026-06-21

First public beta of the Korean (한국어) translation patch.

**번역 (Translation): 맹구**

### Added
- **Korean-marked title screen** — the Japanese subtitle `アークザラッドII` is
  replaced with `아크 더 래드 II` (bold gothic, gold, in `COMM.IMG`).
- **Residual-Japanese scanner** (`python/validation/scan_residual_japanese.py`) —
  finds untranslated displayable text by comparing original vs patched bytes,
  with HIGH/LOW confidence buckets and MIPS-noise filters.

### Translated
- Dialogue/text across all 19 STG stages, `SCPS_100.26`, the `.BIN` files, and
  `BEAM.DAT`.
- Decoder-missed orphan text swept (HIGH-confidence misses 152 → 63): character
  and place names, `にせ`-enemy names, kanji location labels (묘지/교회/교황/식당),
  arena/bounty UI labels (몬스터없/포스터없), the battle turn counter
  (`ターン → 턴`, all 38 incl. BEAM.DAT), and exclamations (꺄아아/도와줘/잘했다/…).

### Fixed
- SG00 intro line `やめろぉ → 그만둬` (the original "크장신디" garble).
- Title-font lookup made portable (no hard-coded macOS font; env override +
  cross-platform fallbacks + graceful skip).

### Notes
- Output disc: `Arc the Lad II (Korean Patch).bin` / `.cue`.
- **Beta:** needs in-game playtesting. Remaining untranslated items are
  non-player-facing dev/debug strings (`エラー`/`フラグエラー`/`デバック用だよ`) and a
  few byte-unfittable labels (`にせククル`).

[0.1.0-beta]: https://semver.org/
