from __version__ import __version__
import re
from bs4 import BeautifulSoup, Comment, Doctype
import sys
from PIL import Image
import requests
import io
import os # Import the os module for path manipulation
import random # Import random for HTML generation
import numpy as np
import shutil
from wcwidth import wcswidth
from textwrap import wrap
from functools import lru_cache

print(f"BaodWeb Terminal Browser version {__version__}")
# --- PyInstaller Path Handling ---
# This function helps PyInstaller locate bundled resources.
# When the script is bundled, sys._MEIPASS will contain the path to the temporary
# directory where PyInstaller extracts all bundled files.
# If not bundled (e.g., running directly from Python), it uses the current script's directory.
def resource_path(relative_path):
    if getattr(sys, 'frozen', False):  # Running in PyInstaller .exe
        base_path = sys._MEIPASS
    else:  # Running in .py script
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

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

class Anchor:
    def __init__(self, text, href, current_anchors, next_anchor_id): #
        self.text = text
        self.href = href
        self.tag_type = 'a'
        
        # Assign an ID and register self with the browser's anchor list
        self.anchor_id = next_anchor_id[0] #
        current_anchors[self.anchor_id] = self #
        next_anchor_id[0] += 1 #

    def render(self, enable_color=True):
        if enable_color:
            # Removed leading/trailing spaces.
            # The color and underline styling will now apply *only* to the text content.
            return f"[{self.anchor_id}] {BLUE_FG}{UNDERLINE}{self.text.strip()}{RESET}" #
        # Also remove spaces from the non-colored fallback.
        return f"[{self.anchor_id}] {self.text.strip()} [{self.href}]" #
    
class TextNode:
    def __init__(self, text):
        self.text = text
        self.tag_type = 'text' # Added tag_type

    def render(self, enable_color=True):
        return self.text

class Paragraph:
    def __init__(self, content_parts):
        self.content_parts = content_parts
        self.tag_type = 'p' # Added tag_type

    def render(self, enable_color=True):
        rendered_parts = []
        for part in self.content_parts:
            rendered_parts.append(part.render(enable_color))

        return "".join(rendered_parts) + "\n"

class Heading:
    def __init__(self, text, level=1):
        self.text = text
        self.level = level
        self.tag_type = f'h{level}' # Added tag_type

    def render(self, enable_color=True):
        style = ""
        if enable_color:
            if self.level == 1:
                style = f"{BOLD}{BLUE_FG}"
            elif self.level == 2:
                style = f"{BOLD}{GREEN_FG}"
            else:
                style = f"{BOLD}{YELLOW_FG}"

        return f"\n{style}{'#' * self.level} {self.text}{RESET}\n"

class ListElement:
    def __init__(self, items_content_parts):
        self.items_content_parts = items_content_parts
        self.tag_type = 'ul' # Added tag_type

    def render(self, enable_color=True):
        bullet_style = f"{CYAN_FG}" if enable_color else ""
        rendered_items = []
        for item_parts in self.items_content_parts:
            # Render the content of each list item
            item_text = "".join(part.render(enable_color) for part in item_parts)
            rendered_items.append(f"{bullet_style}•{RESET if enable_color else ''} {item_text}")

        return "\n".join(rendered_items) + "\n"

class NumberedListElement:
    def __init__(self, items_content_parts):
        self.items_content_parts = items_content_parts
        self.tag_type = 'ol' # Added tag_type

    def render(self, enable_color=True):
        numbered_style = f"{MAGENTA_FG}" if enable_color else ""
        rendered_items = []
        for i, item_parts in enumerate(self.items_content_parts, 1):
            item_text = "".join(part.render(enable_color) for part in item_parts)
            rendered_items.append(f"{numbered_style}{i}.{RESET if enable_color else ''} {item_text}")
        return "\n".join(rendered_items) + "\n"

class TableElement:
    def __init__(self, headers, rows, max_width=None):
        self.headers = headers
        self.rows = rows
        self.max_width = max_width or shutil.get_terminal_size((100, 20)).columns
        self.tag_type = 'table' # Added tag_type

    def _visible_width(self, text):
        """Compute display width excluding ANSI codes."""
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        return wcswidth(clean_text)

    def _wrap_cell(self, text, width):
        """Wrap text to fit in the given display width, preserving ANSI codes."""
        # This regex matches an ANSI escape sequence.
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')

        lines = []
        current_line_parts = []
        current_line_visible_width = 0

        # Preserve the initial ANSI state if any, to apply to subsequent wrapped lines.
        # This is a simplification; a full solution would track active styles.
        initial_ansi_codes = "".join(re.findall(ansi_escape, text))
        
        # Split the text into parts: (text_segment, ansi_code_before_it)
        # This regex splits before an ANSI escape sequence, but keeps the escape sequence.
        parts = re.split(r'(\x1b\[[0-9;]*m)', text)
        # Filter out empty strings from the split and pair them up.
        processed_parts = []
        current_text = ""
        for part in parts:
            if not part:
                continue
            if ansi_escape.match(part):
                if current_text:
                    processed_parts.append(('text', current_text))
                    current_text = ""
                processed_parts.append(('ansi', part))
            else:
                current_text += part
        if current_text:
            processed_parts.append(('text', current_text))


        for part_type, part_content in processed_parts:
            if part_type == 'ansi':
                current_line_parts.append(part_content)
            else: # It's a text segment
                for char in part_content:
                    char_width = wcswidth(char)
                    if current_line_visible_width + char_width > width:
                        # Current line is full, add it to lines
                        lines.append("".join(current_line_parts) + RESET) # Ensure reset at end of line
                        current_line_parts = [initial_ansi_codes] # Start new line, try to preserve initial style
                        current_line_visible_width = 0

                    current_line_parts.append(char)
                    current_line_visible_width += char_width
        
        if current_line_parts:
            lines.append("".join(current_line_parts) + RESET) # Ensure reset at end of the last line

        return lines

    def render(self, enable_color=True):
        if not self.headers and not self.rows:
            return ""

        # Collect all cell contents
        all_cells = [self.headers] + self.rows
        num_cols = max(len(row) for row in all_cells)
        column_widths = [0] * num_cols

        cell_texts = []

        for row in all_cells:
            row_texts = []
            for i, cell_parts in enumerate(row):
                # Pass enable_color to inline content rendering
                text = "".join(part.render(enable_color) for part in cell_parts)
                width = self._visible_width(text)
                if i < num_cols and width > column_widths[i]: # Ensure index is within bounds
                    column_widths[i] = width
                row_texts.append(text)
            cell_texts.append(row_texts)

        # Add padding
        column_widths = [w + 2 for w in column_widths]

        total_width = sum(column_widths) + len(column_widths) + 1

        # Shrink table if too wide
        if total_width > self.max_width:
            available = self.max_width - (len(column_widths) + 1)
            min_col_width = 6
            flexible_cols = [max(min_col_width, int(w * available / sum(column_widths))) for w in column_widths]
            column_widths = flexible_cols

        # Unicode borders
        def make_border(left, mid, right, fill):
            return left + mid.join(fill * w for w in column_widths) + right

        top_border = make_border("╭", "┬", "╮", "─")
        middle_border = make_border("├", "┼", "┤", "─")
        bottom_border = make_border("╰", "┴", "╯", "─")

        output_lines = [top_border]

        def render_row(cells, is_header=False):
            wrapped_lines = []
            max_lines = 0
            for i, text in enumerate(cells):
                wrapped = self._wrap_cell(text, column_widths[i] - 2)
                wrapped_lines.append(wrapped)
                max_lines = max(max_lines, len(wrapped))

            for line_num in range(max_lines):
                line_cells = []
                for i, lines in enumerate(wrapped_lines):
                    if line_num < len(lines):
                        txt = lines[line_num]
                    else:
                        txt = ""

                    pad_len = column_widths[i] - self._visible_width(txt) - 1
                    if is_header and enable_color: # Apply bold only if color is enabled
                        cell = f" {BOLD}{txt}{RESET}" + " " * pad_len
                    else:
                        cell = f" {txt}" + " " * pad_len
                    line_cells.append(cell)
                output_lines.append("│" + "│".join(line_cells) + "│")

        # Render header
        if self.headers:
            render_row(cell_texts[0], is_header=True)
            output_lines.append(middle_border)

        # Render rows
        for row in cell_texts[1:]:
            render_row(row)

        output_lines.append(bottom_border)
        return "\n".join(output_lines) + "\n"



class Button:
    def __init__(self, label):
        self.label = label
        self.tag_type = 'button'

    def render(self, enable_style=True):
        style = f"{BOLD}{WHITE_FG}" if enable_style else ""
        reset = RESET if enable_style else ""

        padded = f"  {self.label}  "
        top = f"╭{'─' * len(padded)}╮"
        middle = f"│{style}{padded}{reset}│"
        bottom = f"╰{'─' * len(padded)}╯"

        return f"{top}\n{middle}\n{bottom}\n"
class Div:
    def __init__(self, *elements):
        self.elements = elements
        self.tag_type = 'div' # Added tag_type

    def render(self, enable_color=True):
        # Join elements with a single newline, and then add surrounding newlines
        # This prevents excessive blank lines between paragraphs or other block elements
        rendered_children = []
        for element in self.elements:
            rendered_child = element.render(enable_color)
            if rendered_child.endswith('\n'):
                rendered_children.append(rendered_child)
            else:
                rendered_children.append(rendered_child + '\n') # Ensure consistent newlines for blocks

        # Remove any leading/trailing newlines that might cause double spacing
        # and then add a single blank line before and after the div content.
        content = "".join(rendered_children).strip()
        if content:
            return f"\n{content}\n"
        return ""


class ImageElement:
    def __init__(self, src, width=None, height=None, base_url=None, max_width=80, alt=""):
        self.src = src
        self.width = width
        self.height = height
        self.base_url = base_url  # Pass this when creating ImageElement
        self.max_width = max_width
        self.tag_type = 'img' # Added tag_type
        self.alt = alt # Store the alt text

    def render(self, enable_color=True):
        try:
            image_url = self.src
            if self.src.startswith("/"):
                if self.base_url:
                    image_url = self.base_url.rstrip("/") + self.src
                else:
                    image_url = "https://www.google.com" + self.src

            response = requests.get(image_url, timeout=5)
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            image_file = io.BytesIO(response.content)

            # Calculate target dimensions
            target_w = int(self.width) // 4 if self.width else None
            target_h = int(self.height) // 5 if self.height else None

            # Capture image output as string
            output = io.StringIO()
            sys_stdout_backup = sys.stdout
            sys.stdout = output
            image_to_terminal_art(
                image_file,
                target_width_pixels=target_w,
                target_height_pixels=target_h,
                max_width_chars=self.max_width
            )
            sys.stdout = sys_stdout_backup

            return f"\n{output.getvalue()}[Image: {self.alt if self.alt else self.src}]\n"

        except Exception as e:
            return f"\n[Error rendering image {self.src}: {e}]\n"
class Nav:
    def __init__(self, elements):
        self.elements = elements
        self.tag_type = 'nav'

    def _visible_width(self, text):
        """Compute display width excluding ANSI codes."""
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        return wcswidth(clean_text)

    def render(self, enable_color=True):
        if not self.elements:
            return ""

        # Render each element and store its visible width
        rendered_parts_info = []
        for element in self.elements:
            rendered_text = element.render(enable_color).strip()
            visible_w = self._visible_width(rendered_text)
            rendered_parts_info.append((rendered_text, visible_w))

        # Define the desired padding (2 characters on each side)
        padding_chars_per_side = 2
        total_padding_per_cell = padding_chars_per_side * 2

        # Determine maximum width for each "column" (each nav item)
        # Add the total_padding_per_cell to the content width, with a minimum overall width
        padded_column_widths = [max(info[1] + total_padding_per_cell, 9) for info in rendered_parts_info] # Min width 5 + 4 padding = 9

        # Calculate total width of the "table" for the borders
        # This calculation relies on `padded_column_widths` representing the full width including separators
        total_width = sum(padded_column_widths) + (len(padded_column_widths) - 1) + 2 # Sum of widths + (num_cols - 1) for inner separators + 2 for outer borders (left/right)

        # Construct border lines using Unicode characters
        def make_border(left_char, mid_char, right_char, fill_char):
            # Corrected: fill_char repeated by its full padded width (w)
            # The mid_char joins these full-width segments.
            return left_char + mid_char.join(fill_char * w for w in padded_column_widths) + right_char

        top_border = make_border("╭", "┬", "╮", "─")
        bottom_border = make_border("╰", "┴", "╯", "─")

        output_lines = [top_border]

        # Render content row (this will always be a single row)
        content_cells = []
        for i, (text, visible_w) in enumerate(rendered_parts_info):
            # Calculate padding needed for the right side
            # Total cell width - visible text width - padding on left side
            right_pad_len = padded_column_widths[i] - visible_w - padding_chars_per_side

            # Apply color to the text within the cell
            cell_text = f"{YELLOW_FG if enable_color else ''}{text}{RESET if enable_color else ''}"

            # Pad the cell and add to list of content cells for this row
            content_cells.append(f"{' ' * padding_chars_per_side}{cell_text}{' ' * right_pad_len}")

        # Join the content cells with the vertical separator
        output_lines.append("│" + "│".join(content_cells) + "│")
        output_lines.append(bottom_border)

        return "\n".join(output_lines) + "\n"
SUPPORTED_TAGS = {'html', 'body', 'section', 'article', 'main', 'div',
                  'h1', 'h2', 'h3', 'p', 'ul', 'ol', 'li', 'a', 'button', 'img', 'nav',
                  'table', 'thead', 'tbody', 'tr', 'th', 'td', 'strong', 'b', 'em', 'i', 'u', 'del', 'ins', 'mark', 'sub', 'sup', 'span'} # Added inline tags here

class Parser:
    def __init__(self):
        pass

    SUBSCRIPT_MAP = {
        '0': '\u2080', '1': '\u2081', '2': '\u2082', '3': '\u2083', '4': '\u2084',
        '5': '\u2085', '6': '\u2086', '7': '\u2087', '8': '\u2088', '9': '\u2089',
        '+': '\u208a', '-': '\u208b', '=': '\u208c', '(': '\u208d', ')': '\u208e',
        'a': '\u2090', 'e': '\u2091', 'o': '\u2092', 'x': '\u2093' # Add common letters if needed
    }

    SUPERSCRIPT_MAP = {
        '0': '\u2070', '1': '\u00b9', '2': '\u00b2', '3': '\u00b3', '4': '\u2074',
        '5': '\u2075', '6': '\u2076', '7': '\u2077', '8': '\u2078', '9': '\u2079',
        '+': '\u207a', '-': '\u207b', '=': '\u207c', '(': '\u207d', ')': '\u207e',
        'i': '\u2071', 'n': '\u207f' # Add common letters if needed
    }

    def _convert_to_unicode_sub_sup(self, text, is_subscript):
        converted_chars = []
        mapping = self.SUBSCRIPT_MAP if is_subscript else self.SUPERSCRIPT_MAP
        for char in text:
            # If a character has a unicode equivalent, use it; otherwise, keep the original character
            converted_chars.append(mapping.get(char, char))
        return "".join(converted_chars)

    def parse(self, html, current_anchors=None, next_anchor_id=None): #
        soup = BeautifulSoup(html, 'html.parser')
        elements = []
        page_title = "No Title"

        title_tag = soup.find('title')
        if title_tag:
            page_title = title_tag.get_text(strip=True)

        root = soup.find('html') or soup
        elements.extend(self.parse_element(root, current_anchors, next_anchor_id)) #
        return elements, page_title

    def parse_element(self, tag, current_anchors=None, next_anchor_id=None): #
        # Handle plain text nodes
        if isinstance(tag, str):
            text = tag.strip()
            if text:
                return [TextNode(text)]
            else:
                return []

        # Handle comments or other types
        if not hasattr(tag, 'name'):
            return []

        if isinstance(tag, (Comment, Doctype)):
            return []

        # Handle elements by tag name
        tag_name = tag.name.lower()

        if tag.name.lower() in ['style', 'script', 'noscript']:
            # Ignore content inside these tags completely
            return []

        if tag_name in ['h1', 'h2', 'h3']:
            return [Heading(tag.get_text(strip=True), level=int(tag_name[1]))]

        elif tag_name == 'p':
            return [Paragraph(self._parse_inline_content(tag, current_anchors, next_anchor_id))] #

        elif tag_name == 'ul':
            list_items = []
            for li in tag.find_all('li', recursive=False):
                list_items.append(self._parse_inline_content(li, current_anchors, next_anchor_id)) #
            return [ListElement(list_items)]

        elif tag_name == 'ol': # Handle ordered list
            list_items = []
            for li in tag.find_all('li', recursive=False):
                list_items.append(self._parse_inline_content(li, current_anchors, next_anchor_id)) #
            return [NumberedListElement(list_items)]

        elif tag_name == 'a':
            href = tag.get('href', '#')
            text = tag.get_text(strip=True)
            # Pass current_anchors and next_anchor_id to Anchor constructor
            return [Anchor(text, href, current_anchors, next_anchor_id)] #

        elif tag_name == 'button':
            label = tag.get_text(strip=True)
            return [Button(label)]

        elif tag_name == 'img':
            src = tag.get('src')
            width = tag.get('width')
            height = tag.get('height')
            alt = tag.get('alt', '') # Extract alt attribute, default to empty string
            if src:
                return [ImageElement(src, width=width, height=height, alt=alt)] # Pass alt
            else:
                return []

        elif tag_name == 'table': # Handle table
            headers = []
            rows = []
            # Find headers (th) in thead or directly in tr
            thead = tag.find('thead')
            if thead:
                for th in thead.find_all('th'):
                    headers.append(self._parse_inline_content(th, current_anchors, next_anchor_id)) #
            else: # Try to find headers in the first row if no thead
                first_tr = tag.find('tr')
                if first_tr and first_tr.find('th'):
                    for th in first_tr.find_all('th'):
                        headers.append(self._parse_inline_content(th, current_anchors, next_anchor_id)) #

            # Find rows (tr) in tbody or directly in table
            tbody = tag.find('tbody')
            if tbody:
                for tr in tbody.find_all('tr'):
                    row_cells = []
                    for td in tr.find_all(['td', 'th']): # Can have th in tbody as well
                        row_cells.append(self._parse_inline_content(td, current_anchors, next_anchor_id)) #
                    rows.append(row_cells)
            else: # No tbody, look for tr directly in table, skipping the potential header row
                trs = tag.find_all('tr')
                start_index = 1 if headers and trs and trs[0].find('th') else 0 # Skip first row if it was used for headers
                for tr in trs[start_index:]:
                    row_cells = []
                    for td in tr.find_all(['td', 'th']):
                        row_cells.append(self._parse_inline_content(td, current_anchors, next_anchor_id)) #
                    rows.append(row_cells)

            return [TableElement(headers, rows)]

        elif tag_name in ['div', 'body', 'html', 'section', 'article', 'main']:
            elements = []
            for child in tag.contents:
                elements.extend(self.parse_element(child, current_anchors, next_anchor_id)) #
            # For these container tags, we want to preserve their tag_type if they are the top-level element
            # that is being rendered. However, if they are just nested, the Div class handles the rendering.
            # For the purpose of filtering, we need to know their original tag.
            # So, we'll create a Div element and assign it the specific tag_type.
            if tag_name == 'div':
                return [Div(*elements)]
            elif tag_name == 'body':
                body_div = Div(*elements)
                body_div.tag_type = 'body'
                return [body_div]
            elif tag_name == 'html':
                html_div = Div(*elements)
                html_div.tag_type = 'html'
                return [html_div]
            elif tag_name == 'section':
                section_div = Div(*elements)
                section_div.tag_type = 'section'
                return [section_div]
            elif tag_name == 'article':
                article_div = Div(*elements)
                article_div.tag_type = 'article'
                return [article_div]
            elif tag_name == 'main':
                main_div = Div(*elements)
                main_div.tag_type = 'main'
                return [main_div]
            return [Div(*elements)]


        elif tag_name == 'nav':
            elements = []
            for child in tag.contents:
                elements.extend(self.parse_element(child, current_anchors, next_anchor_id)) #
            return [Nav(elements)]

        else:
            # For unsupported tags, try to parse children recursively
            elements = []
            for child in tag.contents:
                elements.extend(self.parse_element(child, current_anchors, next_anchor_id)) #
            if not elements:
                text = tag.get_text(strip=True)
                if text:
                    elements.append(TextNode(text))
            return elements

    def _parse_inline_content(self, parent_tag, current_anchors=None, next_anchor_id=None): #
        parsed_inline_elements = []

        for content_node in parent_tag.contents:
            if isinstance(content_node, (Comment, Doctype)):
                continue

            if isinstance(content_node, str):
                # Normalize internal whitespace: replace newlines and multiple spaces with a single space.
                # IMPORTANT: Removed .strip() at the end to preserve single spaces around tags.
                text = re.sub(r'\s+', ' ', content_node)
                if not text or "endif" in text.lower() or "[if" in text.lower() or "<!" in text:
                    continue
                parsed_inline_elements.append(TextNode(text))

            elif hasattr(content_node, 'name'):
                tag_name = content_node.name.lower()

                if tag_name in {'script', 'style', 'noscript'}:
                    continue

                elif tag_name == 'a':
                    href = content_node.get('href', '#')
                    # Keep strip=True here, as anchor text should be trimmed
                    text = content_node.get_text(strip=True)
                    if text:
                        parsed_inline_elements.append(Anchor(text, href, current_anchors, next_anchor_id)) #

                elif tag_name == 'img':
                    src = content_node.get('src')
                    width = content_node.get('width')
                    height = content_node.get('height')
                    if src:
                        parsed_inline_elements.append(ImageElement(src, width=width, height=height))

                # Handling for text formatting tags
                elif tag_name == 'strong' or tag_name == 'b':
                    inner_content = "".join(part.render() for part in self._parse_inline_content(content_node, current_anchors, next_anchor_id)) #
                    if inner_content:
                        parsed_inline_elements.append(TextNode(f"{BOLD}{inner_content}{RESET}"))
                elif tag_name == 'em' or tag_name == 'i':
                    inner_content = "".join(part.render() for part in self._parse_inline_content(content_node, current_anchors, next_anchor_id)) #
                    if inner_content:
                        parsed_inline_elements.append(TextNode(f"{ITALIC}{inner_content}{RESET}"))
                elif tag_name == 'u':
                    inner_content = "".join(part.render() for part in self._parse_inline_content(content_node, current_anchors, next_anchor_id)) #
                    if inner_content:
                        parsed_inline_elements.append(TextNode(f"{UNDERLINE}{inner_content}{RESET}"))
                elif tag_name == 'del':
                    inner_content = "".join(part.render() for part in self._parse_inline_content(content_node, current_anchors, next_anchor_id)) #
                    if inner_content:
                        parsed_inline_elements.append(TextNode(f"{STRIKETHROUGH}{inner_content}{RESET}"))
                elif tag_name == 'ins':
                    inner_content = "".join(part.render() for part in self._parse_inline_content(content_node, current_anchors, next_anchor_id)) #
                    if inner_content:
                        parsed_inline_elements.append(TextNode(f"{UNDERLINE}{inner_content}{RESET}"))
                elif tag_name == 'mark':
                    inner_content = "".join(part.render() for part in self._parse_inline_content(content_node, current_anchors, next_anchor_id)) #
                    if inner_content:
                        parsed_inline_elements.append(TextNode(f"{YELLOW_BG}{inner_content}{RESET}"))
                elif tag_name == 'sub':
                    inner_text = "".join(part.render() for part in self._parse_inline_content(content_node, current_anchors, next_anchor_id)) #
                    # Convert content to unicode subscript characters
                    converted_text = self._convert_to_unicode_sub_sup(inner_text, is_subscript=True)
                    if converted_text:
                        parsed_inline_elements.append(TextNode(converted_text))
                elif tag_name == 'sup':
                    inner_text = "".join(part.render() for part in self._parse_inline_content(content_node, current_anchors, next_anchor_id)) #
                    # Convert content to unicode superscript characters
                    converted_text = self._convert_to_unicode_sub_sup(inner_text, is_subscript=False)
                    if converted_text:
                        parsed_inline_elements.append(TextNode(converted_text))
                elif tag_name == 'span':
                    parsed_inline_elements.extend(self._parse_inline_content(content_node, current_anchors, next_anchor_id)) #

                else:
                    # For other unsupported inline tags, just get their text content
                    # Keep strip=True here, as it's typically for the text content within the tag.
                    text = content_node.get_text(strip=True)
                    if text:
                        parsed_inline_elements.append(TextNode(text))

        return parsed_inline_elements

# --- HTML Generator ---
class HtmlGenerator:
    def generate_random_page_with_tag(self, tag_name):
        title = f"Test {tag_name.capitalize()}"
        header_text = f"Test {tag_name.capitalize()} Page"

        body_content = []

        # Add a heading
        body_content.append(f"<h1>{header_text}</h1>")

        # Add a paragraph
        body_content.append("<p>This is a dynamically generated page featuring the "
                            f"<code>&lt;{tag_name}&gt;</code> tag.</p>")

        # Add the specific tag with some generic content
        if tag_name == 'p':
            body_content.append("<p>This is a paragraph generated dynamically. "
                                "Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>")
        elif tag_name == 'a':
            body_content.append("<p><a href='https://www.example.com'>Click me - a dynamically generated link!</a></p>")
            body_content.append("<p>Another link: <a href='https://www.google.com'>Google</a></p>")
        elif tag_name == 'ul':
            items = [f"<li>Item {i} {random.choice(['Alpha', 'Beta', 'Gamma'])}</li>" for i in range(1, random.randint(3, 6))]
            body_content.append(f"<ul>{''.join(items)}</ul>")
        elif tag_name == 'ol':
            items = [f"<li>Ordered Item {i} {random.choice(['One', 'Two', 'Three'])}</li>" for i in range(1, random.randint(3, 6))]
            body_content.append(f"<ol>{''.join(items)}</ol>")
        elif tag_name == 'button':
            body_content.append("<button>Dynamic Button</button>")
        elif tag_name == 'img':
            # Use a placeholder image URL
            body_content.append('<img src="https://via.placeholder.com/150" alt="Placeholder Image" width="150" height="150">')
        elif tag_name == 'table':
            num_rows = random.randint(2, 4)
            num_cols = random.randint(2, 3)
            table_html = "<table><thead><tr>"
            for c in range(num_cols):
                table_html += f"<th>Header {c+1}</th>"
            table_html += "</tr></thead><tbody>"
            for r in range(num_rows):
                table_html += "<tr>"
                for c in range(num_cols):
                    table_html += f"<td>Row {r+1}, Col {c+1}</td>"
                table_html += "</tr>"
            table_html += "</tbody></table>"
            body_content.append(table_html)
        elif tag_name == 'h1':
            body_content.append("<h1>This is a dynamically generated H1 heading.</h1>")
        elif tag_name == 'h2':
            body_content.append("<h2>This is a dynamically generated H2 heading.</h2>")
        elif tag_name == 'h3':
            body_content.append("<h3>This is a dynamically generated H3 heading.</h3>")
        elif tag_name == 'strong' or tag_name == 'b':
            body_content.append("<p>This sentence contains <strong>bold text</strong> generated.</p>")
        elif tag_name == 'em' or tag_name == 'i':
            body_content.append("<p>This sentence contains <em>italic text</em> generated.</p>")
        elif tag_name == 'u':
            body_content.append("<p>This sentence contains <u>underlined text</u> generated.</p>")
        elif tag_name == 'del':
            body_content.append("<p>This sentence contains <del>deleted text</del> generated.</p>")
        elif tag_name == 'ins':
            body_content.append("<p>This sentence contains <ins>inserted text</ins> generated.</p>")
        elif tag_name == 'mark':
            body_content.append("<p>This sentence contains <mark>highlighted text</mark> generated.</p>")
        elif tag_name == 'sub':
            body_content.append("<p>This is H<sub>2</sub>O with a subscript.</p>")
        elif tag_name == 'sup':
            body_content.append("<p>This is X<sup>2</sup> + Y<sup>3</sup> with superscripts.</p>")
        elif tag_name == 'div':
            body_content.append("<div>A dynamically generated div with a <p>paragraph inside.</p></div>")
        elif tag_name == 'nav':
            body_content.append("<nav><a href='#'>Nav Link 1</a> <a href='#'>Nav Link 2</a></nav>")
        elif tag_name == 'section':
            body_content.append("<section><h2>Dynamic Section</h2><p>Content within a section.</p></section>")
        elif tag_name == 'article':
            body_content.append("<article><h2>Dynamic Article</h2><p>Content within an article.</p></article>")
        elif tag_name == 'main':
            body_content.append("<main><h2>Dynamic Main Content</h2><p>Content within the main tag.</p></main>")
        elif tag_name == 'li': # For direct li generation, mostly for internal use, but can be added
            body_content.append("<li>A standalone list item. Usually found in ul/ol.</li>")
        elif tag_name == 'th': # For direct th generation, mostly for internal use
            body_content.append("<th>A standalone table header cell.</th>")
        elif tag_name == 'td': # For direct td generation, mostly for internal use
            body_content.append("<td>A standalone table data cell.</td>")
        else:
            # For other unsupported or generic tags, just add a simple instance of it
            body_content.append(f"<{tag_name}>Content for {tag_name} tag.</{tag_name}>")

        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
</head>
<body>
    {''.join(body_content)}
</body>
</html>
        """
        return html_template

# --- ConfigManager ---
class ConfigManager:
    CONFIG_FILE_NAME = "config"
    # Define default configuration values
    DEFAULT_CONFIG = {
        "enable-color": "1",
        "language": "EN", # New default language setting
    }
    # Add default render settings for all supported tags
    for tag in SUPPORTED_TAGS:
        DEFAULT_CONFIG[f"render-{tag}"] = "1" # Default to rendering all tags

    def __init__(self):
        self.config_path = resource_path(self.CONFIG_FILE_NAME)
        self.config = {}
        self._load_config()

    def _load_config(self):
        """Loads configuration from the config file, creating it if it doesn't exist."""
        if not os.path.exists(self.config_path):
            self._create_default_config()
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): # Ignore empty lines and comments
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        self.config[key.strip()] = value.strip()
        except Exception as e:
            print(f"Error loading config file: {e}. Using default configuration.", file=sys.stderr)
            self.config = self.DEFAULT_CONFIG.copy() # Fallback to default if loading fails

        # Ensure all default keys are present in case config file is incomplete
        for key, value in self.DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = value

    def _create_default_config(self):
        """Creates the default config file."""
        print(f"Creating default config file at: {self.config_path}")
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write("# TUI Web Browser Configuration\n")
                f.write("# Set options to 1 to enable, 0 to disable\n")
                f.write("# Set language (e.g., EN, FR, ES) to control localized page loading\n\n") #
                for key, value in self.DEFAULT_CONFIG.items():
                    f.write(f"{key} = {value}\n")
            self.config = self.DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error creating default config file: {e}", file=sys.stderr)
            self.config = self.DEFAULT_CONFIG.copy() # Ensure config is initialized even if write fails

    def _save_config(self):
        """Saves the current configuration to the config file."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.write("# TUI Web Browser Configuration\n")
                f.write("# Set options to 1 to enable, 0 to disable\n")
                f.write("# Set language (e.g., EN, FR, ES) to control localized page loading\n\n")
                for key, value in self.config.items():
                    f.write(f"{key} = {value}\n")
            print(f"Configuration saved to {self.config_path}")
        except Exception as e:
            print(f"Error saving config file: {e}", file=sys.stderr)

    def set(self, key, value):
        """Sets a configuration value and saves it. Includes validation."""
        if key not in self.DEFAULT_CONFIG:
            print(f"Error: Unknown configuration option '{key}'.", file=sys.stderr)
            return False

        # Type validation for specific keys
        if key == "enable-color" and value not in ["0", "1"]:
            print(f"Error: 'enable-color' must be 0 or 1. Received '{value}'.", file=sys.stderr)
            return False
        
        if key == "language":
            # Basic validation: check if it's an alphanumeric string
            if not re.fullmatch(r"^[a-zA-Z]{2}$", value): # Assuming 2-letter language codes
                print(f"Warning: Language code '{value}' might be invalid. Use standard 2-letter codes (e.g., EN, VI).", file=sys.stderr)
            value = value.upper() # Store language codes as uppercase

        if key.startswith("render-") and value not in ["0", "1"]:
            print(f"Error: Render setting for '{key}' must be 0 or 1. Received '{value}'.", file=sys.stderr)
            return False

        # Update and save
        old_value = self.config.get(key)
        self.config[key] = value
        self._save_config()
        print(f"Configuration updated: '{key}' changed from '{old_value}' to '{value}'.")
        return True

    def get(self, key, default=None):
        """Gets a configuration value."""
        return self.config.get(key, default)

    def is_color_enabled(self):
        """Checks if color output is enabled."""
        return self.get("enable-color", "1") == "1"

    def should_render_tag(self, tag_name):
        """Checks if a specific HTML tag should be rendered."""
        # Special handling for 'text' nodes, which are always rendered if their parent is.
        if tag_name == 'text':
            return True
        return self.get(f"render-{tag_name}", "1") == "1"

# --- Renderer ---
class Renderer:
    def __init__(self, config_manager):
        self.config_manager = config_manager # Pass config_manager to renderer

    def render(self, elements, title=None):
        enable_color = self.config_manager.is_color_enabled()

        if title:
            if enable_color:
                print(f"{UNDERLINE}{BOLD}{CYAN_FG}{' ' * (len(title) + 13)}{RESET}")
                print(f"{UNDERLINE}{BOLD}{CYAN_FG}|     {title}     |{RESET}")
            else:
                print(f"--- {title} ---")


        # Recursively render elements, applying tag filtering
        self._render_elements_recursive(elements, enable_color)


    def _render_elements_recursive(self, elements, enable_color):
        for element in elements:
            # Check if the element's tag_type should be rendered
            if hasattr(element, 'tag_type') and not self.config_manager.should_render_tag(element.tag_type):
                continue # Skip rendering this element and its children

            # If it's a container element (like Div, Nav), recursively render its children
            if hasattr(element, 'elements'):
                # Render the container itself (e.g., Div might add newlines)
                rendered_self = element.render(enable_color)
                if rendered_self:
                    print(rendered_self, end='')
                # Then recursively render its children, which will also be filtered
                # Note: The children are already passed to the Div/Nav constructor,
                # so we don't need to pass them again here. The render method of
                # Div/Nav will handle calling render on its own elements.
            else:
                # For non-container elements, just render them
                print(element.render(enable_color), end='')

    def clear(self):
        print("\033c", end="")

    def refresh(self, elements, title=None):
        self.clear()
        self.render(elements, title)

# --- Browser ---
class Browser:
    def __init__(self):
        self.history = []
        self.current_url = None
        self.current_title = "Loading..."
        self.parser = Parser()
        self.config_manager = ConfigManager() # Initialize ConfigManager
        self.renderer = Renderer(self.config_manager) # Pass ConfigManager to Renderer
        self.html_generator = HtmlGenerator() # Initialize the HTML generator
        self.last_html = ""
        self._current_anchors = {} #
        self._next_anchor_id = [1] # # Use a list to make it mutable for passing by reference

    def navigate(self, url):
        self.current_url = url
        self.history.append(url)
        self.load_content(url)

    def load_content(self, url, is_config_page=False):
        html_content = ""
        current_lang = self.config_manager.get("language", "EN").lower() # Get current language, default to EN, convert to lowercase for filenames

        self._current_anchors = {} # Clear anchors for new page
        self._next_anchor_id = [1] # Reset anchor ID counter

        try:
            if url == "home":
                # Try language-specific home page first
                lang_home_path = resource_path(f"start-page-{current_lang}.html") #
                if os.path.exists(lang_home_path):
                    with open(lang_home_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                else:
                    # Fallback to default home page
                    default_home_path = resource_path("start-page.html") #
                    if os.path.exists(default_home_path):
                        with open(default_home_path, "r", encoding="utf-8") as f:
                            html_content = f.read()
                    else:
                        raise FileNotFoundError(f"Neither {lang_home_path} nor {default_home_path} found.")
            elif url.startswith("test:"):
                test_page_base_name = url[len("test:"):].strip()
                
                # Try language-specific test page first
                lang_test_page_filename = f"{test_page_base_name}-{current_lang}.html" #
                lang_test_page_path = resource_path(os.path.join("test-pages", lang_test_page_filename)) #

                if os.path.exists(lang_test_page_path):
                    with open(lang_test_page_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                else:
                    # Fallback to default test page name
                    default_test_page_filename = f"{test_page_base_name}.html" #
                    default_test_page_path = resource_path(os.path.join("test-pages", default_test_page_filename)) #
                    if os.path.exists(default_test_page_path):
                        with open(default_test_page_path, "r", encoding="utf-8") as f:
                            html_content = f.read()
                    else:
                        raise FileNotFoundError(f"Neither {lang_test_page_path} nor {default_test_page_path} found.")
            elif is_config_page: # For internally generated config page HTML
                html_content = url # In this case, 'url' is the HTML content itself
            else:
                # --- NEW: Fetch content from a real URL ---
                # Ensure the URL has a scheme (e.g., http:// or https://)
                if not url.startswith("http://") and not url.startswith("https://"):
                    # Attempt to prepend http:// if no scheme is present
                    # In a real browser, you might try https:// first, then http://
                    url = "https://" + url

                print(f"Fetching {url}...")
                response = requests.get(url, timeout=10) # Added a timeout
                response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
                html_content = response.text
                print(f"Successfully fetched {url}")
                # --- END NEW ---

        except FileNotFoundError:
            html_content = f"""
                <title>404 File Not Found</title>
                <h1>Error: File Not Found</h1>
                <p>Could not find the local file: {url}</p>
            """
            print(f"Error: Local file '{url}' not found.", file=sys.stderr)
        except requests.exceptions.RequestException as e:
            try:
                with open(resource_path('error/403.html'), 'r', encoding='utf-8') as file: #
                    template = file.read()
                html_content = template.replace("{error}", str(e)).replace("{url}", url)
            except FileNotFoundError:
                html_content = f"<title>Error</title><h1>Error: {e}</h1><p>Failed to load error page template for {url}</p>"
            print(f"Error fetching {url}: {e}", file=sys.stderr)

        except Exception as e:
            try:
                with open(resource_path('error/unexpected.html'), 'r', encoding='utf-8') as file: #
                    template = file.read()
                html_content = f"{template}".replace("{error}", str(e))
            except FileNotFoundError:
                html_content = f"<title>Error</title><h1>An unexpected error occurred: {e}</h1>"
            print(f"An unexpected error occurred: {e}", file=sys.stderr)

        self.last_html = html_content
        elements, page_title = self.parser.parse(html_content, self._current_anchors, self._next_anchor_id) #
        self.current_title = page_title
        self.renderer.refresh(elements, self.current_title)

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            self.current_url = self.history[-1]
            # Need to re-parse the content from the history to apply config filtering.
            # If the content was a URL, refetch it. If it was local, reload.
            # For simplicity, if it's a generated page, we'll just regenerate it.
            # A more robust solution would cache the parsed elements or the raw HTML.
            if self.current_url.startswith("config-page:"): # Check if it's our special config page URL
                self._show_config_page(add_to_history=False) # Regenerate and display without adding to history again
            else:
                self.load_content(self.current_url)
        else:
            print("No history to go back to.")

    def list_test_pages(self):
        # Use resource_path for the test-pages directory
        test_pages_dir = resource_path("test-pages") #
        if not os.path.exists(test_pages_dir):
            print(f"Error: The '{test_pages_dir}' directory does not exist.")
            return

        print(f"\nAvailable test pages in '{test_pages_dir}':")
        found_pages = False
        all_test_files_base_names = set() # Use a set to store unique base names (e.g., "my-page" from "my-page.html" or "my-page-fr.html")

        # Define a pattern to match language codes in filenames
        lang_code_pattern = re.compile(r"^(.*?)-(en|fr|es|de|cn|jp)\.html$", re.IGNORECASE) # Add more common language codes as needed

        for filename in os.listdir(test_pages_dir): #
            if filename.endswith(".html"): #
                match = lang_code_pattern.match(filename) #
                if match:
                    all_test_files_base_names.add(match.group(1)) # Add the part before -lang.html
                else:
                    all_test_files_base_names.add(filename[:-5]) # Add as is if no lang code

        if all_test_files_base_names:
            for page_name in sorted(list(all_test_files_base_names)): #
                print(f"- {page_name}") #
            found_pages = True

        if not found_pages:
            print("No .html test pages found.") #
        
        current_lang_setting = self.config_manager.get("language", "EN").upper() #
        print(f"\nCurrently configured language for pages is: {current_lang_setting}") #
        print(f"When using 'test <page-name>', the browser will try to load '<page-name>-{current_lang_setting.lower()}.html' first.") #
        print("If not found, it will fall back to '<page-name>.html'.") #
        print("\nTo load a test page, use: test <page-name>")

    def list_available_languages(self):
        """Lists all available language codes based on existing start-page-<lang>.html files."""
        base_resource_dir = resource_path("")
        if not os.path.exists(base_resource_dir):
            print(f"Error: The resource directory '{base_resource_dir}' does not exist.")
            return

        print(f"\nAvailable languages for start pages:")
        found_languages = set()
        lang_file_pattern = re.compile(r"start-page-(.*?)\.html$", re.IGNORECASE)

        for filename in os.listdir(base_resource_dir):
            match = lang_file_pattern.match(filename)
            if match:
                found_languages.add(match.group(1).upper()) # Store language code in uppercase

        if found_languages:
            for lang_code in sorted(list(found_languages)):
                print(f"- {lang_code}")
            print(f"\nCurrently configured language is: {self.config_manager.get('language', 'EN').upper()}")
            print("To change language, modify the 'language' setting in the 'config' file.")
        else:
            print("No language-specific start pages found (e.g., 'start-page-en.html').")


    def _show_config_page(self, add_to_history=True):
        """Generates and displays an HTML page with the current configuration."""
        config_html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Current Configuration</title>
</head>
<body>
    <h1>TUI Browser Configuration</h1>
    <p>This page displays the current settings loaded from your 'config' file.</p>

    <h2>General Settings</h2>
    <ul>
        <li><b>Enable Color:</b> {}</li>
        <li><b>Language:</b> {}</li>
    </ul>

    <h2>Render Settings (1 = Enabled, 0 = Disabled)</h2>
    <table>
        <thead>
            <tr>
                <th>Tag Name</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
        {}
        </tbody>
    </table>
</body>
</html>
        """
        enable_color_status = "Enabled" if self.config_manager.is_color_enabled() else "Disabled"
        current_language_setting = self.config_manager.get("language", "EN").upper() # Get and display language

        render_settings_rows = []
        # Sort tags for consistent display
        sorted_supported_tags = sorted(list(SUPPORTED_TAGS))
        for tag in sorted_supported_tags:
            status = self.config_manager.get(f"render-{tag}", "1")
            render_settings_rows.append(f"<tr><td>&lt;{tag}&gt;</td><td>{status}</td></tr>")

        # Pass current_language_setting to format
        final_html = config_html_content.format(enable_color_status, current_language_setting, "\n".join(render_settings_rows)) #

        # Use a special "URL" to indicate this is an internally generated page
        if add_to_history:
            self.current_url = "config-page:current"
            self.history.append(self.current_url)
        
        self.load_content(final_html, is_config_page=True)


    def handle_input(self, user_input):
        if user_input.startswith("go "):
            url = user_input[3:].strip()
            self.navigate(url)
        elif user_input.startswith("test "):
            test_page = user_input[5:].strip()
            self.navigate(f"test:{test_page}")
        elif user_input.startswith("generate "): # New command to generate HTML
            tag_name = user_input[len("generate "):].strip().lower()
            if tag_name in SUPPORTED_TAGS:
                generated_html = self.html_generator.generate_random_page_with_tag(tag_name)
                elements, page_title = self.parser.parse(generated_html, self._current_anchors, self._next_anchor_id) #
                self.current_title = page_title
                self.renderer.refresh(elements, self.current_title)
            else:
                print(f"Cannot generate content for unsupported tag: '{tag_name}'.")
                print(f"Supported tags for generation: {', '.join(sorted(list(SUPPORTED_TAGS)))}")
        elif user_input.startswith("click "): # Handle click command
            try:
                anchor_id = int(user_input[len("click "):].strip()) #
                if anchor_id in self._current_anchors: #
                    anchor = self._current_anchors[anchor_id] #
                    print(f"Clicking link [{anchor_id}]: {anchor.text} -> {anchor.href}") #
                    self.navigate(anchor.href) #
                else:
                    print(f"Error: No link found with ID {anchor_id}. Please check the displayed link IDs.") #
            except ValueError:
                print("Error: Invalid link ID. Please enter a number after 'click'.") #
        elif user_input == "back":
            self.go_back()
        elif user_input == "list-tests": # New command
            self.list_test_pages()
        elif user_input == "list-languages": # New command for listing languages
            self.list_available_languages()
        elif user_input.startswith("config"): # Modified command to show/set configuration
            parts = user_input.split(maxsplit=2)
            if len(parts) == 1: # Just "config"
                self._show_config_page()
            elif len(parts) == 3: # "config <option> <value>"
                option = parts[1].strip()
                value = parts[2].strip()
                if self.config_manager.set(option, value):
                    # If config was successfully set, refresh the current page or show config page
                    if self.current_url and self.current_url.startswith("config-page:"):
                        self._show_config_page(add_to_history=False) # Refresh config page
                    elif self.current_url:
                        self.load_content(self.current_url) # Reload current page to apply changes
                    else:
                        self.load_content("home") # If no current URL, load home page
                else:
                    print("Failed to update configuration. Please check your input")
            else:
                print("Usage: config [option] [value]")
                print("  config              - Show current configuration")
                print("  config <option> <value> - Set a configuration option (e.g., config enable-color 0)")
        else:
            print("Unknown command. Commands: go <url>, test <test-page-name>, back, list-tests, list-languages, generate <tag>, config, click <id>, quit") # Updated help text

    def start(self):
        print("Welcome to the TUI Web Browser!")
        print("Commands: go <url>, test <test-page-name>, back, list-tests, list-languages, generate <tag>, config [option] [value], click <id>, quit") # Updated help text
        self.load_content("home") # Load the start-page.html
        while True:
            user_input = input("> ")
            if user_input == "quit":
                print("Exiting browser.")
                break
            self.handle_input(user_input)

# --- Main ---

def main():
    args = sys.argv[1:]

    if not args:
        browser = Browser()
        browser.start()
        return

    arg = args[0].lower()

    if arg in ("--version", "-v"):
        print(f"baodweb version {__version__}")
        return

    if arg in ("--help", "-h"):
        print("Usage: baodweb [options]")
        print("Options:")
        print("  --version, -v         Show version info")
        print("  --help, -h            Show this help message")
        print("  --debug               Enable debug mode")
        print("  --open <path>         Open a local HTML file")
        return

    if arg == "--debug":
        browser = Browser(debug=True)
        browser.start()
        return

    if arg == "--open":
        if len(args) < 2:
            print("Error: Missing file path for --open")
            return
        file_path = args[1]
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found.")
            return
        with open(file_path, "r", encoding="utf-8") as f:
            html = f.read()
        browser = Browser()
        browser.load_content(html)
        browser.start()
        return

    print(f"Unknown argument: {arg}")
    print("Try 'baodweb --help' for a list of options.")


if __name__ == "__main__":
    main()