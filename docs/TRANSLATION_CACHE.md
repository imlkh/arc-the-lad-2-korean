# Translation Cache System

## Overview

The translation cache maps Japanese text to Korean translations, enabling reuse of existing translations when new dialogues are discovered. This avoids re-translating text that has already been translated.

## Cache Location

```
cache/
├── combined_translation_cache.json   # All translations merged
├── combined_translation_cache.tsv    # Human-readable format
├── SG00_translation_cache.json       # SG00.STG only
├── SG00_translation_cache.tsv
├── S100_translation_cache.json       # S100.STG only
├── S100_translation_cache.tsv
├── SDIC_translation_cache.json       # SDIC.BIN only
├── SDIC_translation_cache.tsv
├── YGUILD_translation_cache.json     # YGUILD.BIN only
├── YGUILD_translation_cache.tsv
├── SCPS_translation_cache.json       # SCPS_100.26 only
└── SCPS_translation_cache.tsv
```

## Cache Format

### JSON Format (for programmatic use)

```json
{
  "Japanese text here": {
    "korean": "Korean translation here",
    "offsets": ["0x00123456", "0x00789ABC"]
  },
  "よし！": {
    "korean": "좋아!",
    "offsets": ["0x000BC5BA"]
  }
}
```

Each entry contains:
- **Key**: Original Japanese text (including control codes like `[br]`, `[opt]`, `[delay:XX]`)
- **korean**: The Korean translation
- **offsets**: List of file offsets where this text appears (useful for debugging)

### TSV Format (for human reading)

Tab-separated format with three columns:

```
# Japanese	Korean	Offsets
よし！	좋아!	0x000BC5BA
[FF:04 02 01]！	[FF:04 02 01]!	0x011ABA0C,0x0149DA0C,0x016D320C
```

Multiple offsets are comma-separated when the same text appears at different locations.

## Building the Cache

Run the cache builder script after updating translations:

```bash
cd atl2_korean_translation
python python/build_translation_cache.py
```

### Source Files

The cache is built from these file pairs:

| Type | Source (Japanese) | Translation (Korean) |
|------|-------------------|---------------------|
| STG | `output/decoded/stg/SG00_STG.txt` | `translated/ko/SG00_STG.txt` |
| STG | `output/decoded/stg/S100_STG.txt` | `translated/ko/S100_STG.txt` |
| BIN | `output/decoded/bin/SDIC_BIN.txt` | `translated/ko/SDIC_BIN.txt` |
| BIN | `output/decoded/bin/YGUILD_BIN.txt` | `translated/ko/YGUILD_BIN.txt` |
| BIN | `output/decoded/bin/SCPS_100_26.txt` | `translated/ko/SCPS_100_26.txt` |

## Using the Cache

### Python API

```python
from python.build_translation_cache import load_cache, lookup_translation

# Load the combined cache
cache = load_cache('cache/combined_translation_cache.json')

# Look up a translation
japanese_text = 'よし！'
result = lookup_translation(cache, japanese_text)

if result:
    print(f"Korean: {result['korean']}")
    print(f"Offsets: {result['offsets']}")
else:
    print("Translation not found - needs manual translation")
```

### Lookup Behavior

1. **Exact match**: First tries to find an exact match for the Japanese text
2. **Normalized match**: If no exact match, normalizes the text (removes `[delay:XX]` timing variations) and tries again

### Example Workflow for New Dialogues

When new dialogues are discovered:

```python
import json

# Load cache
with open('cache/combined_translation_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

# New dialogues to translate
new_dialogues = [
    "よし！",           # Already in cache
    "新しいテキスト",    # Not in cache - needs translation
]

for jp_text in new_dialogues:
    if jp_text in cache:
        ko_text = cache[jp_text]['korean']
        print(f"CACHED: {jp_text} -> {ko_text}")
    else:
        print(f"NEW: {jp_text} -> [needs translation]")
```

## Cache Statistics

Current cache contents (as of last build):

| Source | Entries |
|--------|---------|
| SG00.STG | 1,267 |
| S100.STG | 1,029 |
| SDIC.BIN | 217 |
| YGUILD.BIN | 351 |
| SCPS_100.26 | 80 |
| **Total unique** | **2,927** |

## Maintenance

### When to Rebuild

Rebuild the cache after:
- Adding new translations to any translation file
- Modifying existing translations
- Adding support for new game files

### Adding New File Types

To add a new file type to the cache, edit `python/build_translation_cache.py`:

1. For STG files, add to `stg_file_pairs` list
2. For BIN files, add to `bin_file_pairs` list

```python
# Example: Adding a new STG file
stg_file_pairs = [
    ('SG00', 'output/decoded/stg/SG00_STG.txt', 'translated/ko/SG00_STG.txt'),
    ('S100', 'output/decoded/stg/S100_STG.txt', 'translated/ko/S100_STG.txt'),
    ('NEW_FILE', 'output/decoded/stg/NEW_FILE_STG.txt', 'translated/ko/NEW_FILE_STG.txt'),  # Add here
]
```

## Notes

- Control codes (`[br]`, `[opt]`, `[delay:XX]`, `[box:system]`, etc.) are preserved in both Japanese and Korean text
- The cache uses the original Japanese text as the key, not the offset, so identical text at different offsets shares one translation
- Offsets are stored for debugging and cross-referencing with the original game files
