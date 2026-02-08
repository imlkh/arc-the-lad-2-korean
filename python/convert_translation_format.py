#!/usr/bin/env python3
"""
Convert translation file from simplified format to full decoded format.

Input format (simplified):
  0x000B3794,괜찮아?

Output format (full):
  0x000B3794 [0x8005] [script:EC 04]괜찮아?
  --- context: 0x8005 -> 0x8007 ---
"""

import re
import sys
from pathlib import Path

def parse_simplified_translations(filepath):
    """Parse simplified format: offset,korean_text"""
    translations = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            # Skip comments and empty lines
            if line.startswith('#') or not line.strip():
                continue
            # Match: offset,text
            match = re.match(r'\s*(0x[0-9A-Fa-f]+),(.+)$', line)
            if match:
                offset = match.group(1).upper()
                text = match.group(2)
                translations[offset] = text
    return translations

def convert_file(stg_name):
    """Convert translation file to full format."""
    base_dir = Path(__file__).parent.parent

    decoded_path = base_dir / 'output' / 'decoded' / 'stg' / f'{stg_name}_STG.txt'
    trans_path = base_dir / 'translated' / 'ko' / f'{stg_name}_STG.txt'
    output_path = base_dir / 'translated' / 'ko' / f'{stg_name}_STG_new.txt'

    if not decoded_path.exists():
        print(f"Error: Decoded file not found: {decoded_path}")
        return False

    if not trans_path.exists():
        print(f"Error: Translation file not found: {trans_path}")
        return False

    # Load translations
    translations = parse_simplified_translations(trans_path)
    print(f"Loaded {len(translations)} translations from {trans_path}")

    # Process decoded file and apply translations
    output_lines = []
    translated_count = 0
    untranslated_count = 0

    with open(decoded_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')

            # Keep header comments and context markers as-is
            if line.startswith('#') or line.strip().startswith('---'):
                output_lines.append(line)
                continue

            # Empty lines
            if not line.strip():
                output_lines.append(line)
                continue

            # Parse dialogue line: "  0xOFFSET [0xSPEAKER] [script:XX XX]Japanese text"
            match = re.match(r'(\s*)(0x[0-9A-Fa-f]+)(\s+\[0x[0-9A-Fa-f]+\]\s+\[script:[0-9A-Fa-f]+ [0-9A-Fa-f]+\])(.+)$', line)
            if match:
                indent = match.group(1)
                offset = match.group(2).upper()
                metadata = match.group(3)
                japanese_text = match.group(4)

                # Check if we have a Korean translation
                if offset in translations:
                    korean_text = translations[offset]
                    # Keep original offset format from source
                    output_lines.append(f"{indent}{match.group(2)}{metadata}{korean_text}")
                    translated_count += 1
                else:
                    # Keep original Japanese if no translation
                    output_lines.append(line)
                    untranslated_count += 1
            else:
                # Unknown format, keep as-is
                output_lines.append(line)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines) + '\n')

    print(f"Output written to: {output_path}")
    print(f"Translated: {translated_count}, Untranslated: {untranslated_count}")

    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python convert_translation_format.py <STG_NAME>")
        print("Example: python convert_translation_format.py S200")
        sys.exit(1)

    stg_name = sys.argv[1]
    success = convert_file(stg_name)
    sys.exit(0 if success else 1)
