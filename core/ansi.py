from functools import lru_cache

# --- ANSI Escape Codes (for easier reference) ---
RESET = "\x1b[0m"
BOLD = "\x1b[1m"
UNDERLINE = "\x1b[4m"
ITALIC = "\x1b[3m"
STRIKETHROUGH = "\x1b[9m"

# Foreground Colors
BLACK_FG = "\x1b[30m"
RED_FG = "\x1b[31m"
GREEN_FG = "\x1b[32m"
YELLOW_FG = "\x1b[33m"
BLUE_FG = "\x1b[34m"
MAGENTA_FG = "\x1b[35m"
CYAN_FG = "\x1b[36m"
WHITE_FG = "\x1b[37m"

# Background Colors
BLACK_BG = "\x1b[40m"
RED_BG = "\x1b[41m"
GREEN_BG = "\x1b[42m"
YELLOW_BG = "\x1b[43m"
BLUE_BG = "\x1b[34m"
MAGENTA_BG = "\x1b[45m"
CYAN_BG = "\x1b[46m"
WHITE_BG = "\x1b[47m"

@lru_cache(maxsize=4096)
def rgb_to_256_ansi(r, g, b):
    # This function is highly optimized due to lru_cache.
    # The logic itself is already efficient for its purpose.
    if r == g == b:
        if r < 8: return 16
        if r > 248: return 231
        return 232 + (r * 23) // 255
    return 16 + 36 * ((r * 5) // 255) + 6 * ((g * 5) // 255) + ((b * 5) // 255)
