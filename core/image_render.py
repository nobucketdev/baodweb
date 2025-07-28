from PIL import Image
from functools import lru_cache
import numpy as np
import sys

RESET = "\x1b[0m"

# These caches are only used when enable_true_color is False.
# For true-color, numpy vectorization is used, which is faster.
_ansi_fg_cache = {}
_ansi_bg_cache = {}

@lru_cache(maxsize=4096)
def rgb_to_256_ansi(r, g, b):
    # This function is highly optimized due to lru_cache.
    # The logic itself is already efficient for its purpose.
    if r == g == b:
        if r < 8: return 16
        if r > 248: return 231
        return 232 + (r * 23) // 255
    return 16 + 36 * ((r * 5) // 255) + 6 * ((g * 5) // 255) + ((b * 5) // 255)

def get_cached_fg(r, g, b):
    # This is called when true_color is False.
    # The true_color parameter is now removed from the signature
    # as it's handled by the calling logic.
    key = (r, g, b)
    if key not in _ansi_fg_cache:
        _ansi_fg_cache[key] = f"\x1b[38;5;{rgb_to_256_ansi(r, g, b)}m"
    return _ansi_fg_cache[key]

def get_cached_bg(r, g, b):
    # Similar to get_cached_fg, optimized for the non-true-color path.
    key = (r, g, b)
    if key not in _ansi_bg_cache:
        _ansi_bg_cache[key] = f"\x1b[48;5;{rgb_to_256_ansi(r, g, b)}m"
    return _ansi_bg_cache[key]

def generate_ansi_arrays_true_color(top_rows, bottom_rows):
    # This function is already quite optimized due to NumPy's vectorization.
    # No significant changes needed here.
    r_fg = bottom_rows[..., 0].astype(str)
    g_fg = bottom_rows[..., 1].astype(str)
    b_fg = bottom_rows[..., 2].astype(str)

    r_bg = top_rows[..., 0].astype(str)
    g_bg = top_rows[..., 1].astype(str)
    b_bg = top_rows[..., 2].astype(str)

    # Use f-strings for clarity and potentially better performance in some Python versions
    fg_codes = np.char.add("\x1b[38;2;", np.char.add(r_fg, np.char.add(";", np.char.add(g_fg, np.char.add(";", np.char.add(b_fg, "m"))))))
    bg_codes = np.char.add("\x1b[48;2;", np.char.add(r_bg, np.char.add(";", np.char.add(g_bg, np.char.add(";", np.char.add(b_bg, "m"))))))

    return fg_codes, bg_codes

def generate_ansi_arrays_256_color(top_rows, bottom_rows):
    # Vectorized approach for 256-color mode as well.
    # Apply rgb_to_256_ansi to entire arrays using np.vectorize
    # This significantly speeds up the non-true-color path by avoiding Python loops
    # for each pixel's color conversion.
    
    # We create a vectorized version of rgb_to_256_ansi.
    # The 'otypes' argument is crucial for performance, indicating the output type.
    # Since rgb_to_256_ansi returns an integer, we use int.
    v_rgb_to_256_ansi = np.vectorize(rgb_to_256_ansi, otypes=[np.int16]) # Use int16 as 256 is small

    # Apply the vectorized function to all RGB tuples in one go.
    # We reshape to (N, 3) to apply the function to each (R, G, B) triplet.
    top_256 = v_rgb_to_256_ansi(top_rows[..., 0], top_rows[..., 1], top_rows[..., 2]).astype(str)
    bottom_256 = v_rgb_to_256_ansi(bottom_rows[..., 0], bottom_rows[..., 1], bottom_rows[..., 2]).astype(str)

    # Now construct the ANSI strings using vectorized string operations.
    fg_codes = np.char.add("\x1b[38;5;", np.char.add(bottom_256, "m"))
    bg_codes = np.char.add("\x1b[48;5;", np.char.add(top_256, "m"))

    return fg_codes, bg_codes


def image_to_terminal_art(image_file_or_path, target_width_pixels=None, target_height_pixels=None,
                          max_width_chars=75, char_aspect_ratio=0.5, enable_true_color=True):
    try:
        # Use a context manager for the image to ensure it's closed
        with Image.open(image_file_or_path) as img:
            img = img.convert("RGB")
    except FileNotFoundError:
        print(f"File not found: {image_file_or_path}", file=sys.stderr)
        return
    except Exception as e:
        print(f"Error opening image: {e}", file=sys.stderr)
        return

    orig_w, orig_h = img.size

    # --- Resizing Logic Optimization ---
    # Simplified and combined calculations for target dimensions.
    # The goal is to calculate the final `width` and `height` (in pixels) for `img.resize` once.

    if target_width_pixels is not None and target_height_pixels is not None:
        width, height = target_width_pixels, target_height_pixels
    else:
        # Calculate ideal character height first based on max_width_chars
        # This prevents overshooting max_width_chars in the initial calculation
        # and then having to resize down.
        aspect_ratio_img = orig_h / orig_w
        
        # Calculate height in characters if max_width_chars is the constraint
        target_height_chars = max(1, int(max_width_chars * char_aspect_ratio * aspect_ratio_img))
        target_height_chars += target_height_chars % 2  # Ensure even for pixel pairs

        # Convert character dimensions back to pixel dimensions
        height = target_height_chars * 2
        width = int(orig_w * (height / orig_h))
        
        # If after this calculation, width is still too large, cap it
        if width > max_width_chars:
            width = max_width_chars
            height = int(orig_h * (width / orig_w))
            height += height % 2 # Ensure even

    # Final sanity checks for dimensions
    width = max(1, width)
    height = max(2, height) # Minimum height of 2 to have at least one top/bottom pair

    # Only resize once after determining final dimensions
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    arr = np.array(img)

    # --- Core Logic for ANSI Art Generation ---
    # This section has the most potential for speedup, especially by minimizing Python loops.

    # Slicing is already efficient for getting top/bottom rows.
    top_rows = arr[::2]
    bottom_rows = arr[1::2]

    output_lines = []

    if enable_true_color:
        # Already vectorized, very efficient.
        fg_codes, bg_codes = generate_ansi_arrays_true_color(top_rows, bottom_rows)
        # Combine using numpy's char functions, then join for each line.
        # This replaces the Python loop for string concatenation per pixel.
        combined_lines_np = np.char.add(np.char.add(fg_codes, bg_codes), "▄")
        for line_array in combined_lines_np:
            output_lines.append("".join(line_array) + RESET)
    else:
        # NEW: Vectorized approach for 256-color mode as well.
        # This will be significantly faster than the original Python loop calling get_cached_fg/bg
        # for each pixel, as it leverages NumPy for the bulk of the work.
        fg_codes, bg_codes = generate_ansi_arrays_256_color(top_rows, bottom_rows)
        combined_lines_np = np.char.add(np.char.add(fg_codes, bg_codes), "▄")
        for line_array in combined_lines_np:
            output_lines.append("".join(line_array) + RESET)

    # Join all lines at once for a single print call.
    # This reduces overhead compared to multiple `print` calls.
    sys.stdout.write("\n".join(output_lines) + "\n") # Add final newline


if __name__ == '__main__':
    # Example Usage:
    # Create a dummy image for testing
    dummy_image = Image.new('RGB', (200, 150), color = 'red')
    dummy_image.save('dummy.png')

    print("--- True Color Example ---")
    image_to_terminal_art('dummy.png', max_width_chars=50, enable_true_color=True)

    print("\n--- 256 Color Example ---")
    image_to_terminal_art('dummy.png', max_width_chars=50, enable_true_color=False)

    # Test with a real image path if you have one
    # image_to_terminal_art('path/to/your/image.jpg', max_width_chars=100)