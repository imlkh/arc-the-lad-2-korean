#!/usr/bin/env python3
"""
Reflow Korean translations to match Japanese line lengths.

This script:
1. Reads original Japanese dialogues to get line break positions
2. Calculates max line length from Japanese (typically ~14-18 chars)
3. Reformats Korean translations to fit within similar line lengths
4. Adds [br] line breaks where needed

Usage:
    python reflow_lines.py [STG_NAME]

    STG_NAME: S100, SG00, etc. (default: S100)
"""

import os
import re
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
GAME_DIR = os.path.dirname(BASE_DIR)

# Maximum characters per line (based on Japanese dialogue box width)
# 96.5% of Japanese lines are <= 18 chars
MAX_LINE_LENGTH = 18


def parse_translation_file(path):
    """Parse a translation file and return list of (offset, speaker, script, text) tuples."""
    entries = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('---'):
                continue

            # Parse format: 0x000B4516 [0x8006] [script:16 07]큰 도시네
            match = re.match(r'0x([0-9A-Fa-f]+)\s+\[0x([0-9A-Fa-f]+)\]\s+\[script:([^\]]+)\](.*)', line)
            if match:
                offset = int(match.group(1), 16)
                speaker = int(match.group(2), 16)
                script = match.group(3)
                text = match.group(4)
                entries.append((offset, speaker, script, text))

    return entries


def count_visible_chars(text):
    """Count visible characters, excluding control tags."""
    # Remove all [...] tags
    clean = re.sub(r'\[[^\]]+\]', '', text)
    return len(clean)


def get_line_lengths(text):
    """Get the length of each line in the text."""
    lines = text.split('[br]')
    return [count_visible_chars(line) for line in lines]


def reflow_text(text, max_length=MAX_LINE_LENGTH):
    """Reflow text to fit within max_length per line.

    Uses a balanced approach: tries to split lines evenly rather than
    filling each line to the max.
    """
    # Split by existing line breaks
    lines = text.split('[br]')

    result_lines = []
    for line in lines:
        line_len = count_visible_chars(line)

        # Check if line needs to be split
        if line_len <= max_length:
            result_lines.append(line)
            continue

        # Need to split this line
        # Calculate optimal number of output lines
        num_lines = (line_len + max_length - 1) // max_length
        target_length = line_len // num_lines + 1

        # Split by spaces (Korean uses spaces between words)
        words = line.split(' ')
        current_line = []
        current_length = 0

        for i, word in enumerate(words):
            word_len = count_visible_chars(word)
            space_len = 1 if current_line else 0

            # Check if we should break here
            new_length = current_length + space_len + word_len

            # Break if: exceeds max, OR we're past target and there are more words
            should_break = (new_length > max_length) or \
                          (current_length >= target_length and i < len(words) - 1 and current_line)

            if should_break and current_line:
                result_lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_len
            else:
                current_line.append(word)
                current_length = new_length

        if current_line:
            result_lines.append(' '.join(current_line))

    return '[br]'.join(result_lines)


def reflow_translation_file(input_path, output_path, max_length=MAX_LINE_LENGTH):
    """Reflow all translations in a file."""
    entries = parse_translation_file(input_path)

    reflowed = 0
    unchanged = 0

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Reflowed translation (max {max_length} chars per line)\n")
        f.write(f"# Original: {os.path.basename(input_path)}\n\n")

        prev_speaker = None
        for offset, speaker, script, text in entries:
            # Write context change markers
            if prev_speaker is not None and speaker != prev_speaker:
                f.write(f"  --- context: 0x{prev_speaker:04X} -> 0x{speaker:04X} ---\n")
            prev_speaker = speaker

            # Check if reflow needed
            original_lengths = get_line_lengths(text)
            needs_reflow = any(l > max_length for l in original_lengths)

            if needs_reflow:
                new_text = reflow_text(text, max_length)
                reflowed += 1
            else:
                new_text = text
                unchanged += 1

            f.write(f"  0x{offset:08X} [0x{speaker:04X}] [script:{script}]{new_text}\n")

    return reflowed, unchanged


def main():
    parser = argparse.ArgumentParser(description="Reflow Korean translations")
    parser.add_argument("stg_name", nargs="?", default="S100",
                        help="STG file name without extension (default: S100)")
    parser.add_argument("--max-length", type=int, default=MAX_LINE_LENGTH,
                        help=f"Maximum characters per line (default: {MAX_LINE_LENGTH})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be changed without modifying files")
    args = parser.parse_args()

    stg_name = args.stg_name.upper()

    input_path = os.path.join(BASE_DIR, "translated", "ko", f"{stg_name}_STG.txt")
    output_path = os.path.join(BASE_DIR, "translated", "ko", f"{stg_name}_STG_reflowed.txt")

    print(f"=== Reflow Korean Translations ===")
    print(f"Max line length: {args.max_length} characters")
    print()

    if not os.path.exists(input_path):
        print(f"ERROR: {input_path} not found!")
        return 1

    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print()

    if args.dry_run:
        # Just analyze
        entries = parse_translation_file(input_path)
        needs_reflow = 0
        examples = []

        for offset, speaker, script, text in entries:
            lengths = get_line_lengths(text)
            if any(l > args.max_length for l in lengths):
                needs_reflow += 1
                if len(examples) < 5:
                    new_text = reflow_text(text, args.max_length)
                    examples.append((text, new_text, max(lengths)))

        print(f"Total entries: {len(entries)}")
        print(f"Need reflow: {needs_reflow}")
        print()

        if examples:
            print("Examples of changes:")
            print("-" * 60)
            for orig, new, max_len in examples:
                print(f"Original (max {max_len} chars):")
                print(f"  {orig}")
                print(f"Reflowed:")
                print(f"  {new}")
                print()
    else:
        reflowed, unchanged = reflow_translation_file(input_path, output_path, args.max_length)
        print(f"Reflowed: {reflowed}")
        print(f"Unchanged: {unchanged}")
        print()
        print(f"Saved: {output_path}")
        print()
        print("To use the reflowed translations:")
        print(f"  1. Review {output_path}")
        print(f"  2. If satisfied, replace {input_path}")
        print("  3. Run patch_all.py again")

    return 0


if __name__ == "__main__":
    exit(main())
