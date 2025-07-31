import shutil
from core.font import font_8x6, font_5x8  # Import both fonts

braille_lookup = [
    [0x01, 0x08],
    [0x02, 0x10],
    [0x04, 0x20],
    [0x40, 0x80],
]

def to_braille_block(block):
    bits = 0
    for y in range(4):
        for x in range(2):
            if block[y][x]:
                bits |= braille_lookup[y][x]
    return chr(0x2800 + bits)

def render_braille_bitmap(bitmap, color_func=None):
    h = len(bitmap)
    w = max(len(row) for row in bitmap) if h else 0

    for row in bitmap:
        row.extend([0] * (w - len(row)))

    if h % 4 != 0:
        bitmap += [[0] * w for _ in range(4 - h % 4)]
        h += (4 - h % 4)

    if w % 2 != 0:
        for row in bitmap:
            row.append(0)
        w += 1

    out_lines = []
    for by in range(0, h, 4):
        line = []
        for bx in range(0, w, 2):
            block = [[0]*2 for _ in range(4)]
            for y in range(4):
                for x in range(2):
                    block[y][x] = bitmap[by + y][bx + x]
            braille_char = to_braille_block(block)
            if color_func:
                color = color_func(by // 4, bx // 2)
                braille_char = f"\x1b[38;5;{color}m{braille_char}\x1b[0m"
            line.append(braille_char)
        out_lines.append("".join(line))
    return "\n".join(out_lines)

# Added font_mode parameter
def braillify(text, color=None, font_mode='6x8'): # Default to 6x8
    term_cols = shutil.get_terminal_size().columns

    if font_mode == '5x8':
        selected_font = font_5x8
        letter_w, letter_h, spacing = 5, 8, 1 # Adjusted letter_w for 5x8
    else: # Default or '6x8'
        selected_font = font_8x6
        letter_w, letter_h, spacing = 6, 8, 1

    char_w = letter_w + spacing
    chars_per_line = max(1, (term_cols * 2) // char_w)

    lines = [text[i:i+chars_per_line] for i in range(0, len(text), chars_per_line)]

    full_bitmap = []
    max_width = 0
    bitmaps = []

    for line in lines:
        width = len(line) * char_w
        max_width = max(max_width, width)
        bitmap = [[0] * width for _ in range(letter_h)]

        for i, ch in enumerate(line):
            glyph = selected_font.get(ch) # Use selected_font
            if not glyph:
                continue
            x_off = i * char_w
            for y in range(letter_h):
                for x in range(letter_w): # Use letter_w from selected font
                    bitmap[y][x_off + x] = glyph[y][x]
        bitmaps.append(bitmap)

    for bitmap in bitmaps:
        for row in bitmap:
            row.extend([0] * (max_width - len(row)))
            full_bitmap.append(row)

    # Default color mode: horizontal rainbow
    if color is True:
        def default_color(y, x):
            return 27
        color = default_color

    return render_braille_bitmap(full_bitmap, color_func=color)

if __name__ == "__main__":
    try:
        while True:
            text = input("Enter text to braillify (or 'exit'): ")
            if text.lower() == 'exit':
                break
            # Example of how to use both modes
            print("Using 6x8 font:")
            print(braillify(text, color=True, font_mode='6x8'))
            print("\nUsing 5x8 font:")
            print(braillify(text, color=True, font_mode='5x8')) # Added 5x8 example
    except KeyboardInterrupt:
        print("\nExiting.")