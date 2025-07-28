import io
import re
import sys
import shutil
from textwrap import wrap
from wcwidth import wcswidth
import requests
from core.image_render import image_to_terminal_art
from core.ansi import *
from core.braillify import braillify 

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
        return f"[{WHITE_FG}{self.anchor_id}] {self.text.strip()} [{self.href}]" #
    

class TextNode:
    def __init__(self, text):
        self.text = text
        self.tag_type = 'text' # Added tag_type

    def render(self, enable_color=True):
        return self.text

class Title:
    def __init__(self, text):
        self.text = text
        self.tag_type = 'title'

    def _visible_width(self, text):
        """Compute display width excluding ANSI codes."""
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        return wcswidth(clean_text)

    def render(self, enable_color=True):
        # Determine the maximum width based on terminal size or a sensible default
        terminal_width = shutil.get_terminal_size((80, 20)).columns
        
        # Calculate available width for the title text within the box
        # Box borders and padding: '╭' + '─' + 2 spaces + text + 2 spaces + '─' + '╮'
        # Total fixed width = 1 (corner) + 1 (line) + 2 (padding) + 2 (padding) + 1 (line) + 1 (corner) = 8
        fixed_width_for_box = 6 # Account for '╭─  ' and '  ─╮'
        max_text_width = terminal_width - fixed_width_for_box - 2 # -2 for the side borders themselves '│'

        # Render the text with potential color and bold, and get its visible width
        styled_text = f"{BOLD}{CYAN_FG}{self.text}{RESET}" if enable_color else self.text
        text_visible_width = self._visible_width(styled_text)

        # Wrap the text if it exceeds the maximum allowed width
        wrapped_lines = wrap(styled_text, max_text_width, drop_whitespace=False, break_long_words=False)
        
        # Determine the actual width needed for the box based on the longest wrapped line
        # Use the visible width of the longest line to size the box correctly
        actual_content_width = 0
        if wrapped_lines:
            actual_content_width = max(self._visible_width(line) for line in wrapped_lines)

        # Ensure a minimum width for the box even if text is very short or empty
        min_box_width = 10 # Example minimum width
        box_inner_width = max(actual_content_width, min_box_width)

        # Construct the box components
        top_border = f"╭{'─' * (box_inner_width + 4)}╮" # 2 spaces padding on each side
        bottom_border = f"╰{'─' * (box_inner_width + 4)}╯"

        middle_lines = []
        for line in wrapped_lines:
            # Calculate padding for centering
            current_line_visible_width = self._visible_width(line)
            # Pad on the right to match the `box_inner_width`, then add the 2 spaces for visual padding
            padding_right = box_inner_width - current_line_visible_width + 2
            middle_lines.append(f"│  {line}{' ' * padding_right}│")

        # If no text, ensure at least an empty line in the middle
        if not middle_lines:
            middle_lines.append(f"│{' ' * (box_inner_width + 4)}│")

        return f"{top_border}\n" + "\n".join(middle_lines) + f"\n{bottom_border}\n"


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
        self.tag_type = f'h{level}'

    def render(self, enable_color=True):
        if self.level == 1:
            # Use Braillify to render large text
            term_cols = shutil.get_terminal_size().columns
            letter_w = 6
            spacing = 1
            glyph_px = letter_w + spacing
            braille = braillify(self.text, color=enable_color)
            return f"\n{braille}\n\n"
        else:
            style = ""
            if enable_color:
                if self.level == 2:
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

# New WidgetElement class
class WidgetElement:
    def __init__(self, widget_type, dashboard_generator):
        self.widget_type = widget_type
        self.dashboard_generator = dashboard_generator # Dependency injection for data source
        self.tag_type = 'widget'

    def render(self, enable_color=True):
        content = ""
        if self.widget_type == "time":
            time_data = self.dashboard_generator.get_local_time()
            content = f"Current Time: {BOLD}{time_data}{RESET}"
        elif self.widget_type == "weather":
            weather_data = self.dashboard_generator.get_weather_data()
            content = f"Weather: {BOLD}{weather_data}{RESET}"
        elif self.widget_type == "news":
            news_headlines = self.dashboard_generator.get_news_headlines()
            if news_headlines:
                content = f"{BOLD}Latest News:{RESET}\n" + "\n".join([f"  • {headline}" for headline in news_headlines])
            else:
                content = "No news available."
        else:
            content = f"Unknown widget type: {self.widget_type}"
        
        # Add a simple border for the widget
        border_char = "─"
        padding = 2
        lines = content.split('\n')
        max_line_width = max(wcswidth(re.sub(r'\x1b\[[0-9;]*m', '', line)) for line in lines)
        
        top_border = f"╭{border_char * (max_line_width + padding * 2)}╮"
        bottom_border = f"╰{border_char * (max_line_width + padding * 2)}╯"
        
        rendered_widget = [top_border]
        for line in lines:
            clean_line_width = wcswidth(re.sub(r'\x1b\[[0-9;]*m', '', line))
            rendered_widget.append(f"│{' ' * padding}{line}{' ' * (max_line_width - clean_line_width + padding)}│")
        rendered_widget.append(bottom_border)
        
        return "\n".join(rendered_widget) + "\n"

