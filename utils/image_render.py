from PIL import Image
from functools import lru_cache
import numpy as np
import sys

RESET = "\x1b[0m"

_ansi_fg_cache = {}
_ansi_bg_cache = {}

@lru_cache(maxsize=4096)
def rgb_to_256_ansi(r, g, b):
    if r == g == b:
        if r < 8: return 16
        if r > 248: return 231
        return 232 + (r * 23) // 255
    return 16 + 36 * ((r * 5) // 255) + 6 * ((g * 5) // 255) + ((b * 5) // 255)

def get_cached_fg(r, g, b, true_color):
    key = (r, g, b)
    if true_color:
        return f"\x1b[38;2;{r};{g};{b}m"
    if key not in _ansi_fg_cache:
        _ansi_fg_cache[key] = f"\x1b[38;5;{rgb_to_256_ansi(r, g, b)}m"
    return _ansi_fg_cache[key]

def get_cached_bg(r, g, b, true_color):
    key = (r, g, b)
    if true_color:
        return f"\x1b[48;2;{r};{g};{b}m"
    if key not in _ansi_bg_cache:
        _ansi_bg_cache[key] = f"\x1b[48;5;{rgb_to_256_ansi(r, g, b)}m"
    return _ansi_bg_cache[key]

def image_to_terminal_art(image_file_or_path, target_width_pixels=None, target_height_pixels=None,
                          max_width_chars=75, char_aspect_ratio=0.5, enable_true_color=True):
    try:
        img = Image.open(image_file_or_path).convert("RGB")
    except FileNotFoundError:
        print(f"File not found: {image_file_or_path}", file=sys.stderr)
        return
    except Exception as e:
        print(f"Error opening image: {e}", file=sys.stderr)
        return

    orig_w, orig_h = img.size

    if target_width_pixels and target_height_pixels:
        width, height = target_width_pixels, target_height_pixels
    else:
        target_height_chars = max(1, int((orig_h / orig_w) * max_width_chars * char_aspect_ratio))
        if target_height_chars % 2:
            target_height_chars += 1
        height = target_height_chars * 2
        width = int(orig_w * (height / orig_h))
        if width > max_width_chars:
            width = max_width_chars
            height = int(orig_h * (width / orig_w))
            if height % 2:
                height += 1

    width = max(1, width)
    height = max(2, height)

    total_pixels = width * height
    resample = Image.Resampling.NEAREST if total_pixels < 10000 else Image.Resampling.LANCZOS
    img = img.resize((width, height), resample)

    arr = np.array(img)
    top_rows = arr[::2]
    bottom_rows = arr[1::2]

    output = []
    for top, bottom in zip(top_rows, bottom_rows):
        line = []
        for t, b in zip(top, bottom):
            fg = get_cached_fg(*b, enable_true_color)
            bg = get_cached_bg(*t, enable_true_color)
            line.append(fg + bg + "▄")
        output.append("".join(line) + RESET)

    print("\n".join(output))
