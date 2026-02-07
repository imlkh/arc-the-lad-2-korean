#!/usr/bin/env python3
"""
Compare patched and unpatched COMM.IMG font files.

Shows which character slots were modified and displays the Korean characters
that replaced the original glyphs.

Usage:
    python compare_font.py                    # Summary of changes
    python compare_font.py --export           # Export comparison images
    python compare_font.py --char-id 500      # Show specific character
"""

import os
import sys
import argparse

# === Paths ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_DIR = os.path.dirname(SCRIPT_DIR)
BASE_DIR = os.path.dirname(PYTHON_DIR)
GAME_DIR = os.path.dirname(BASE_DIR)

# === COMM.IMG constants ===
ROW_WIDTH = 896       # bytes per scanline
CHAR_W = 12           # cell width in pixels
CHAR_H = 12           # cell height in pixels
GRID_COLS = 21        # cells per row


def get_pixel(data, x, y):
    """Get 4bpp pixel value at (x, y)."""
    byte_offset = y * ROW_WIDTH + x // 2
    byte_val = data[byte_offset]
    if x % 2 == 0:
        return byte_val & 0x0F
    else:
        return (byte_val >> 4) & 0x0F


def extract_glyph(data, char_id):
    """Extract a single glyph as a 12x12 array of pixel values (0 or 1)."""
    adjusted = char_id - 1
    cell = adjusted // 4
    bitplane = adjusted % 4
    row = cell // GRID_COLS
    col = cell % GRID_COLS

    x0 = col * CHAR_W
    y0 = row * CHAR_H
    mask = 1 << bitplane

    glyph = []
    for dy in range(CHAR_H):
        row_pixels = []
        for dx in range(CHAR_W):
            px = x0 + dx
            py = y0 + dy
            pixel = get_pixel(data, px, py)
            # Check if this bitplane is set
            row_pixels.append(1 if (pixel & mask) else 0)
        glyph.append(row_pixels)
    return glyph


def glyph_to_ascii(glyph):
    """Convert glyph to ASCII art representation."""
    lines = []
    for row in glyph:
        line = ''.join('█' if p else '·' for p in row)
        lines.append(line)
    return '\n'.join(lines)


def glyphs_equal(glyph1, glyph2):
    """Check if two glyphs are identical."""
    for y in range(CHAR_H):
        for x in range(CHAR_W):
            if glyph1[y][x] != glyph2[y][x]:
                return False
    return True


def glyph_is_empty(glyph):
    """Check if glyph is completely empty (no pixels)."""
    for row in glyph:
        if any(row):
            return False
    return True


def load_charmap(charmap_path):
    """Load unified charmap to get Korean char -> charID mapping."""
    charmap = {}
    reverse_map = {}  # charID -> Korean char
    if os.path.exists(charmap_path):
        with open(charmap_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('#') or not line.strip():
                    continue
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    kr_char = parts[0]
                    char_id = int(parts[1])
                    charmap[kr_char] = char_id
                    reverse_map[char_id] = kr_char
    return charmap, reverse_map


def generate_overview_image(original_data, patched_data, reverse_map, output_path, show_original=True, all_chars=False):
    """Generate an overview image showing glyphs.

    Args:
        original_data: Original COMM.IMG data
        patched_data: Patched COMM.IMG data
        reverse_map: charID -> Korean char mapping
        output_path: Output image path
        show_original: If True, show original vs patched side by side
        all_chars: If True, show ALL character IDs (not just Korean)
    """
    from PIL import Image, ImageDraw, ImageFont

    max_char_id = 1764  # Based on decode table

    # Collect glyphs
    glyphs = []
    if all_chars:
        # Show all character IDs
        for char_id in range(1, max_char_id + 1):
            patched_glyph = extract_glyph(patched_data, char_id)
            orig_glyph = extract_glyph(original_data, char_id)
            kr_char = reverse_map.get(char_id, '')
            glyphs.append({
                'char_id': char_id,
                'korean': kr_char,
                'patched': patched_glyph,
                'original': orig_glyph,
            })
    else:
        # Show only Korean glyphs
        for char_id, kr_char in sorted(reverse_map.items()):
            patched_glyph = extract_glyph(patched_data, char_id)
            orig_glyph = extract_glyph(original_data, char_id)
            glyphs.append({
                'char_id': char_id,
                'korean': kr_char,
                'patched': patched_glyph,
                'original': orig_glyph,
            })

    if not glyphs:
        print("No glyphs found")
        return

    # Layout settings
    cols = 88 if all_chars else 32  # 88 chars per row for full table (1764 = 88 * 20 + 4)
    scale = 2 if all_chars else 3  # smaller scale for full table
    cell_w = CHAR_W * scale
    cell_h = CHAR_H * scale
    padding = 1 if all_chars else 2
    label_height = 10 if all_chars else 14  # smaller labels for all_chars mode

    if show_original:
        # Side by side: original | patched
        cell_total_w = (cell_w * 2 + padding * 3)
    else:
        cell_total_w = cell_w + padding * 2

    cell_total_h = cell_h + label_height + padding * 2

    # Separator settings
    separator_interval = 5  # rows between separators
    separator_height = 4 if all_chars else 0  # separator line height

    rows = (len(glyphs) + cols - 1) // cols
    num_separators = (rows - 1) // separator_interval if all_chars else 0
    img_w = cols * cell_total_w + padding
    img_h = rows * cell_total_h + padding + 40 + (num_separators * separator_height)  # extra for header and separators

    # Create image
    img = Image.new('RGB', (img_w, img_h), color=(40, 40, 40))
    draw = ImageDraw.Draw(img)

    # Header
    if all_chars:
        title = f"Arc the Lad 2 Font Table - All {len(glyphs)} CharIDs"
    else:
        title = f"Arc the Lad 2 Korean Font - {len(glyphs)} Glyphs"
    if show_original:
        title += " (Original → Patched)"
    draw.text((padding, padding), title, fill=(255, 255, 255))

    header_y = 30

    # Draw each glyph
    for idx, glyph_info in enumerate(glyphs):
        col = idx % cols
        row = idx // cols

        # Calculate separator offset for this row
        sep_offset = (row // separator_interval) * separator_height if all_chars else 0

        x0 = col * cell_total_w + padding
        y0 = row * cell_total_h + padding + header_y + sep_offset

        # Background
        bg_color = (60, 60, 60) if idx % 2 == 0 else (50, 50, 50)
        draw.rectangle([x0, y0, x0 + cell_total_w - padding, y0 + cell_total_h - padding], fill=bg_color)

        # Draw original glyph (if showing)
        glyph_x = x0 + padding
        if show_original:
            for dy, glyph_row in enumerate(glyph_info['original']):
                for dx, p in enumerate(glyph_row):
                    if p:
                        px = glyph_x + dx * scale
                        py = y0 + padding + dy * scale
                        draw.rectangle([px, py, px + scale - 1, py + scale - 1], fill=(150, 150, 150))
            glyph_x += cell_w + padding

        # Draw patched glyph
        for dy, glyph_row in enumerate(glyph_info['patched']):
            for dx, p in enumerate(glyph_row):
                if p:
                    px = glyph_x + dx * scale
                    py = y0 + padding + dy * scale
                    draw.rectangle([px, py, px + scale - 1, py + scale - 1], fill=(255, 255, 255))

        # Label: charID
        if label_height > 0:
            label = f"{glyph_info['char_id']}"
            label_x = x0 + padding
            label_y = y0 + cell_h + padding
            # Use smaller font color for all_chars mode
            label_color = (150, 150, 150) if all_chars else (200, 200, 200)
            draw.text((label_x, label_y), label, fill=label_color)

    # Draw horizontal separators every 5 rows
    if all_chars and separator_height > 0:
        for sep_idx in range(1, num_separators + 1):
            sep_row = sep_idx * separator_interval
            sep_y = header_y + sep_row * cell_total_h + (sep_idx - 1) * separator_height
            # Draw separator line
            draw.rectangle([0, sep_y, img_w, sep_y + separator_height - 1], fill=(100, 100, 100))
            # Add row label
            label = f"Row {sep_row}"
            draw.text((5, sep_y), label, fill=(200, 200, 200))

    # Save
    img.save(output_path)
    print(f"Saved overview image: {output_path}")
    print(f"  Size: {img_w} x {img_h} pixels")
    print(f"  Glyphs: {len(glyphs)} in {rows} rows x {cols} cols")


def main():
    parser = argparse.ArgumentParser(description='Compare patched and unpatched COMM.IMG fonts')
    parser.add_argument('--export', action='store_true', help='Export comparison images')
    parser.add_argument('--char-id', type=int, help='Show specific character ID')
    parser.add_argument('--show-all', action='store_true', help='Show all modified glyphs')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of glyphs to show (default: 20)')
    parser.add_argument('--overview', action='store_true', help='Generate overview image of Korean glyphs (with original comparison)')
    parser.add_argument('--overview-simple', action='store_true', help='Generate overview of Korean glyphs only')
    parser.add_argument('--all-chars', action='store_true', help='Generate overview of ALL charIDs (entire font table)')
    args = parser.parse_args()

    # Paths
    original_path = os.path.join(GAME_DIR, "COMM.IMG")
    patched_path = os.path.join(BASE_DIR, "output", "patched", "COMM.IMG")
    charmap_path = os.path.join(BASE_DIR, "output", "patched", "unified_charmap.txt")

    # Check files exist
    if not os.path.exists(original_path):
        print(f"ERROR: Original COMM.IMG not found: {original_path}")
        return 1
    if not os.path.exists(patched_path):
        print(f"ERROR: Patched COMM.IMG not found: {patched_path}")
        return 1

    # Load files
    print("Loading font files...")
    with open(original_path, 'rb') as f:
        original_data = f.read()
    with open(patched_path, 'rb') as f:
        patched_data = f.read()

    print(f"  Original: {len(original_data):,} bytes")
    print(f"  Patched:  {len(patched_data):,} bytes")

    # Load charmap for reverse lookup
    charmap, reverse_map = load_charmap(charmap_path)
    print(f"  Charmap:  {len(charmap)} Korean characters mapped")

    # Generate overview image if requested
    if args.overview or args.overview_simple or args.all_chars:
        if args.all_chars:
            output_path = os.path.join(BASE_DIR, "output", "font_table_all.png")
            show_original = False
            all_chars = True
        elif args.overview_simple:
            output_path = os.path.join(BASE_DIR, "output", "font_overview.png")
            show_original = False
            all_chars = False
        else:
            output_path = os.path.join(BASE_DIR, "output", "font_comparison.png")
            show_original = True
            all_chars = False
        generate_overview_image(original_data, patched_data, reverse_map, output_path, show_original, all_chars)
        return 0

    # If specific char-id requested
    if args.char_id:
        char_id = args.char_id
        print(f"\n=== Character ID {char_id} ===")

        orig_glyph = extract_glyph(original_data, char_id)
        patched_glyph = extract_glyph(patched_data, char_id)

        kr_char = reverse_map.get(char_id, '')
        if kr_char:
            print(f"Korean character: {kr_char} (U+{ord(kr_char):04X})")

        print("\nOriginal:")
        print(glyph_to_ascii(orig_glyph))

        print("\nPatched:")
        print(glyph_to_ascii(patched_glyph))

        if glyphs_equal(orig_glyph, patched_glyph):
            print("\n(No change)")
        else:
            print("\n(Modified)")
        return 0

    # Compare all glyphs
    print("\nComparing glyphs...")
    max_char_id = 1764  # Based on decode table

    modified = []
    unchanged = []
    orig_empty = []
    patched_empty = []

    for char_id in range(1, max_char_id + 1):
        orig_glyph = extract_glyph(original_data, char_id)
        patched_glyph = extract_glyph(patched_data, char_id)

        orig_is_empty = glyph_is_empty(orig_glyph)
        patched_is_empty = glyph_is_empty(patched_glyph)

        if orig_is_empty:
            orig_empty.append(char_id)
        if patched_is_empty:
            patched_empty.append(char_id)

        if not glyphs_equal(orig_glyph, patched_glyph):
            kr_char = reverse_map.get(char_id, '')
            modified.append({
                'char_id': char_id,
                'korean': kr_char,
                'orig_glyph': orig_glyph,
                'patched_glyph': patched_glyph,
                'orig_empty': orig_is_empty,
                'patched_empty': patched_is_empty,
            })
        else:
            unchanged.append(char_id)

    # Summary
    print(f"\n=== Font Comparison Summary ===")
    print(f"Total character slots:    {max_char_id}")
    print(f"Modified slots:           {len(modified)}")
    print(f"Unchanged slots:          {len(unchanged)}")
    print(f"Originally empty slots:   {len(orig_empty)}")
    print(f"Patched empty slots:      {len(patched_empty)}")

    # Count Korean chars
    korean_patched = sum(1 for m in modified if m['korean'])
    print(f"\nKorean glyphs added:      {korean_patched}")

    # Show modified glyphs
    if modified:
        print(f"\n=== Modified Glyphs ===")

        # Separate into Korean and non-Korean
        korean_mods = [m for m in modified if m['korean']]
        other_mods = [m for m in modified if not m['korean']]

        limit = args.limit if not args.show_all else len(modified)

        if korean_mods:
            print(f"\nKorean glyphs ({len(korean_mods)} total):")
            print("-" * 60)

            # Show sample of Korean glyphs
            for i, mod in enumerate(korean_mods[:limit]):
                char_id = mod['char_id']
                kr = mod['korean']
                print(f"\nCharID {char_id}: {kr} (U+{ord(kr):04X})")
                print("Original:".ljust(15) + "Patched:")

                orig_lines = glyph_to_ascii(mod['orig_glyph']).split('\n')
                patched_lines = glyph_to_ascii(mod['patched_glyph']).split('\n')

                for orig_line, patched_line in zip(orig_lines, patched_lines):
                    print(f"{orig_line}  {patched_line}")

            if len(korean_mods) > limit:
                print(f"\n... and {len(korean_mods) - limit} more Korean glyphs")
                print(f"(Use --show-all to see all, or --limit N to change)")

        if other_mods:
            print(f"\nOther modified glyphs ({len(other_mods)} total):")
            print("CharIDs:", ', '.join(str(m['char_id']) for m in other_mods[:20]))
            if len(other_mods) > 20:
                print(f"... and {len(other_mods) - 20} more")

    # Export if requested
    if args.export:
        try:
            from PIL import Image
            export_dir = os.path.join(BASE_DIR, "output", "font_comparison")
            os.makedirs(export_dir, exist_ok=True)

            print(f"\nExporting comparison images to {export_dir}...")

            for mod in modified[:100]:  # Limit exports
                char_id = mod['char_id']
                kr = mod['korean'] or 'unknown'

                # Create side-by-side image
                img = Image.new('L', (CHAR_W * 2 + 4, CHAR_H), color=128)

                # Draw original
                for y, row in enumerate(mod['orig_glyph']):
                    for x, p in enumerate(row):
                        img.putpixel((x, y), 255 if p else 0)

                # Draw patched
                for y, row in enumerate(mod['patched_glyph']):
                    for x, p in enumerate(row):
                        img.putpixel((x + CHAR_W + 4, y), 255 if p else 0)

                # Scale up for visibility
                img = img.resize((img.width * 4, img.height * 4), Image.NEAREST)

                filename = f"char_{char_id:04d}_{ord(kr):04X}.png" if mod['korean'] else f"char_{char_id:04d}.png"
                img.save(os.path.join(export_dir, filename))

            print(f"  Exported {min(len(modified), 100)} comparison images")
            if len(modified) > 100:
                print(f"  (Limited to 100, {len(modified) - 100} more not exported)")

        except ImportError:
            print("WARNING: PIL not available, cannot export images")

    # Show charmap table
    if charmap:
        print(f"\n=== Charmap Sample (first 30) ===")
        print("Korean | CharID | Hex")
        print("-" * 25)
        for i, (kr, cid) in enumerate(sorted(charmap.items(), key=lambda x: x[1])[:30]):
            print(f"  {kr}   |  {cid:4d}  | 0x{cid:04X}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
