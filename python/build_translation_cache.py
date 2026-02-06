#!/usr/bin/env python3
"""
Build translation cache from source (Japanese) and translated (Korean) files.
Maps Japanese text -> Korean text for reuse when new dialogues are found.
"""

import re
import json
import os
from pathlib import Path

# Pattern to extract offset and text from dialogue lines
# Format: 0x{offset} [0x{speaker}] [script:{id}]{text}
DIALOGUE_PATTERN = re.compile(
    r'^\s*(0x[0-9A-Fa-f]+)\s+\[0x[0-9A-Fa-f]+\]\s+\[script:[0-9A-Fa-f ]+\](.+)$'
)

def extract_offset_and_text(line: str) -> tuple[str, str] | None:
    """Extract offset and dialogue text from a line."""
    match = DIALOGUE_PATTERN.match(line)
    if match:
        return match.group(1), match.group(2).strip()
    return None

def normalize_text(text: str) -> str:
    """Normalize text for comparison (remove variable parts)."""
    # Remove [delay:XX] tags for comparison as timing may differ
    normalized = re.sub(r'\[delay:[0-9A-Fa-f]+\]', '[delay]', text)
    # Remove [script:XX XX] variations
    normalized = re.sub(r'\[script:[0-9A-Fa-f ]+\]', '', normalized)
    return normalized.strip()

def build_cache(source_file: str, translated_file: str) -> dict:
    """Build translation cache from source and translated files."""
    cache = {}

    # Read source file (Japanese) - map offset -> text
    source_by_offset = {}
    with open(source_file, 'r', encoding='utf-8') as f:
        for line in f:
            result = extract_offset_and_text(line)
            if result:
                offset, text = result
                if offset not in source_by_offset:
                    source_by_offset[offset] = text

    # Read translated file (Korean) - map offset -> text
    translated_by_offset = {}
    with open(translated_file, 'r', encoding='utf-8') as f:
        for line in f:
            result = extract_offset_and_text(line)
            if result:
                offset, text = result
                if offset not in translated_by_offset:
                    translated_by_offset[offset] = text

    # Build cache: Japanese -> {korean, offsets} by matching offsets
    for offset, japanese in source_by_offset.items():
        if offset in translated_by_offset:
            korean = translated_by_offset[offset]
            # Store mapping with offset info
            if japanese not in cache:
                cache[japanese] = {"korean": korean, "offsets": [offset]}
            else:
                # Add offset if this text appears at multiple locations
                if offset not in cache[japanese]["offsets"]:
                    cache[japanese]["offsets"].append(offset)

    return cache

def save_cache(cache: dict, output_file: str):
    """Save cache to file in multiple formats."""
    base_path = Path(output_file).with_suffix('')

    # Save as JSON (for programmatic use)
    json_file = str(base_path) + '.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON cache: {json_file} ({len(cache)} entries)")

    # Save as TSV (tab-separated, for human reading)
    # Format: Japanese\tKorean\tOffsets
    tsv_file = str(base_path) + '.tsv'
    with open(tsv_file, 'w', encoding='utf-8') as f:
        f.write("# Japanese\tKorean\tOffsets\n")
        for jp, data in sorted(cache.items()):
            # Escape tabs and newlines for TSV format
            jp_escaped = jp.replace('\t', '\\t').replace('\n', '\\n')
            ko_escaped = data["korean"].replace('\t', '\\t').replace('\n', '\\n')
            offsets_str = ",".join(data["offsets"])
            f.write(f"{jp_escaped}\t{ko_escaped}\t{offsets_str}\n")
    print(f"Saved TSV cache: {tsv_file} ({len(cache)} entries)")

def load_cache(cache_file: str) -> dict:
    """Load cache from JSON file.

    Returns dict mapping Japanese text -> {"korean": str, "offsets": [str]}
    """
    with open(cache_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def lookup_translation(cache: dict, japanese_text: str) -> dict | None:
    """Look up Korean translation for Japanese text.

    Returns dict with 'korean' and 'offsets' keys, or None if not found.
    """
    # Try exact match first
    if japanese_text in cache:
        return cache[japanese_text]

    # Try normalized match
    normalized = normalize_text(japanese_text)
    for jp, data in cache.items():
        if normalize_text(jp) == normalized:
            return data

    return None

def build_cache_from_bin(source_file: str, translated_file: str) -> dict:
    """Build cache from BIN decoded file and translation file.

    Source format: 0x{offset} [{length}] {japanese_text}
    Translated format: 0x{offset},{korean_text}
    """
    cache = {}

    # Pattern for source BIN file - allow spaces in length field
    bin_pattern = re.compile(r'^\s*(0x[0-9A-Fa-f]+)\s+\[\s*\d+\]\s+(.+)$')

    # Read source file (Japanese)
    source_by_offset = {}
    with open(source_file, 'r', encoding='utf-8') as f:
        for line in f:
            match = bin_pattern.match(line)
            if match:
                offset, text = match.group(1), match.group(2).strip()
                if offset not in source_by_offset:
                    source_by_offset[offset] = text

    # Read translated file (Korean) - format: offset,korean_text
    translated_by_offset = {}
    with open(translated_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    offset, text = parts[0].strip(), parts[1].strip()
                    if offset not in translated_by_offset:
                        translated_by_offset[offset] = text

    # Build cache with offset info
    for offset, japanese in source_by_offset.items():
        if offset in translated_by_offset:
            korean = translated_by_offset[offset]
            if japanese not in cache:
                cache[japanese] = {"korean": korean, "offsets": [offset]}
            else:
                if offset not in cache[japanese]["offsets"]:
                    cache[japanese]["offsets"].append(offset)

    return cache

def main():
    base_dir = Path(__file__).parent.parent

    # Define STG file pairs to process
    stg_file_pairs = [
        ('SG00', 'output/decoded/stg/SG00_STG.txt', 'translated/ko/SG00_STG.txt'),
        ('S100', 'output/decoded/stg/S100_STG.txt', 'translated/ko/S100_STG.txt'),
    ]

    # Define BIN file pairs to process
    bin_file_pairs = [
        ('SDIC', 'output/decoded/bin/SDIC_BIN.txt', 'translated/ko/SDIC_BIN.txt'),
        ('YGUILD', 'output/decoded/bin/YGUILD_BIN.txt', 'translated/ko/YGUILD_BIN.txt'),
        ('SCPS', 'output/decoded/bin/SCPS_100_26.txt', 'translated/ko/SCPS_100_26.txt'),
    ]

    cache_dir = base_dir / 'cache'
    cache_dir.mkdir(exist_ok=True)

    # Combined cache for all files
    combined_cache = {}

    # Process STG files
    for name, source_rel, translated_rel in stg_file_pairs:
        source_file = base_dir / source_rel
        translated_file = base_dir / translated_rel

        if not source_file.exists():
            print(f"Source file not found: {source_file}")
            continue
        if not translated_file.exists():
            print(f"Translated file not found: {translated_file}")
            continue

        print(f"\nProcessing STG {name}...")
        cache = build_cache(str(source_file), str(translated_file))

        # Save individual cache
        save_cache(cache, str(cache_dir / f'{name}_translation_cache'))

        # Merge into combined cache
        for jp, data in cache.items():
            if jp not in combined_cache:
                combined_cache[jp] = {"korean": data["korean"], "offsets": list(data["offsets"])}
            else:
                # Merge offsets from multiple files
                for offset in data["offsets"]:
                    if offset not in combined_cache[jp]["offsets"]:
                        combined_cache[jp]["offsets"].append(offset)

    # Process BIN files
    for name, source_rel, translated_rel in bin_file_pairs:
        source_file = base_dir / source_rel
        translated_file = base_dir / translated_rel

        if not source_file.exists():
            print(f"Source file not found: {source_file}")
            continue
        if not translated_file.exists():
            print(f"Translated file not found: {translated_file}")
            continue

        print(f"\nProcessing BIN {name}...")
        cache = build_cache_from_bin(str(source_file), str(translated_file))

        # Save individual cache
        save_cache(cache, str(cache_dir / f'{name}_translation_cache'))

        # Merge into combined cache
        for jp, data in cache.items():
            if jp not in combined_cache:
                combined_cache[jp] = {"korean": data["korean"], "offsets": list(data["offsets"])}
            else:
                # Merge offsets from multiple files
                for offset in data["offsets"]:
                    if offset not in combined_cache[jp]["offsets"]:
                        combined_cache[jp]["offsets"].append(offset)

    # Save combined cache
    if combined_cache:
        print(f"\nSaving combined cache...")
        save_cache(combined_cache, str(cache_dir / 'combined_translation_cache'))
        print(f"\nTotal unique translations: {len(combined_cache)}")

if __name__ == '__main__':
    main()
