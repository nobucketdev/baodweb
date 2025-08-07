import io
import re
import sys
import shutil, unicodedata
from textwrap import wrap
from wcwidth import wcswidth
import requests
from core.braillify import braillify
from core.image_render import image_to_terminal_art
from core.ansi import *


class Box:
    # Unicode border characters
    # Style 1: Thin
    BORDER_CHARS_THIN = {
        'top_left': '╭', 'top_right': '╮',
        'bottom_left': '╰', 'bottom_right': '╯',
        'horizontal': '─', 'vertical': '│'
    }
    # Style 2: Thick
    BORDER_CHARS_THICK = {
        'top_left': '┏', 'top_right': '┓',
        'bottom_left': '┗', 'bottom_right': '┛',
        'horizontal': '━', 'vertical': '┃'
    }
    # Style 0: No border
    BORDER_CHARS_NONE = {
        'top_left': '', 'top_right': '',
        'bottom_left': '', 'bottom_right': '',
        'horizontal': '', 'vertical': ''
    }

    def __init__(self, elements, tag_type, box_title=None,
                start_x=0, start_y=0, end_x=None, end_y=None,
                border_color_code=WHITE_FG,
                element_alignment='left', # 'left', 'center', 'right'
                padding_x=1, padding_y=0, # internal padding (between content and border)
                margin_x=0, margin_y=0, # external margin (outside border)
                border_style=1): # New: 0=none, 1=thin, 2=thick
        """
        Initializes a BoxedContent element for terminal UI rendering.
        This class creates a customizable box with content, borders, padding, and margins,
        rendering it as a multi-line string for display in a terminal.
        Args:
            elements (list): A list of objects that have a `render()` method
                            (e.g., other BoxedContent instances, _StringElement).
                            These are the child elements whose rendered output
                            will be placed inside the box.
            tag_type (str): A string representing the type or purpose of the box
                            (e.g., 'header', 'footer', 'widget').
            box_title (str, optional): An optional title to display in the top border
                                        of the box. Defaults to None.
            start_x (int, optional): The starting X-coordinate (column) for the
                                     **outermost left edge** of the element,
                                    including its left margin. Defaults to 0.
            start_y (int, optional): The starting Y-coordinate (row) for the
                                     **outermost top edge** of the element,
                                    including its top margin. Defaults to 0.
            end_x (int, optional): The ending X-coordinate (column) for the
                                   **outermost right edge** of the element,
                                    including its right margin. If None, the box
                                    will extend to the terminal's right edge
                                    minus its right margin. Defaults to None.
            end_y (int, optional): The ending Y-coordinate (row) for the
                                   **outermost bottom edge** of the element,
                                    including its bottom margin. If None, the box's
                                    height will be dynamically calculated to fit its
                                    content, padding, and borders. Defaults to None.
            border_color_code (str, optional): ANSI escape code for the color
                                                of the box's borders and title.
                                                Defaults to WHITE_FG.
            element_alignment (str, optional): Horizontal alignment of the content
                                                within the box. Can be 'left',
                                                'center', or 'right'. Defaults to 'left'.
            padding_x (int, optional): The number of empty spaces to add horizontally
                                       **inside** the box, between the content and
                                        the vertical borders. Applied to both left and
                                        right sides. Defaults to 1.
            padding_y (int, optional): The number of empty lines to add vertically
                                       **inside** the box, between the content and
                                        the horizontal borders. Applied to both top and
                                        bottom sides. Defaults to 0.
            margin_x (int, optional): The number of empty spaces to add horizontally
                                      **outside** the box's borders. Applied to both
                                        left and right sides. This space is included
                                        in the `start_x` and `end_x` calculations.
                                        Defaults to 0.
            margin_y (int, optional): The number of empty lines to add vertically
                                      **outside** the box's borders. Applied to both
                                        top and bottom sides. This space is included
                                        in the `start_y` and `end_y` calculations.
                                        Defaults to 0.
            border_style (int, optional): The style of the box borders.
                                        - 0: No border (borders are invisible spaces).
                                        - 1: Thin Unicode border (e.g., '╭─╮').
                                        - 2: Thick Unicode border (e.g., '┏━┓').
                                        Defaults to 1.
        Raises:
            ValueError: If `element_alignment` is not 'left', 'center', or 'right'.
            ValueError: If `border_style` is not 0, 1, or 2.
        """
        self.elements = elements
        self.tag_type = tag_type
        self.box_title = box_title

        self._start_x_init = start_x
        self._start_y_init = start_y
        self._end_x_init = end_x
        self._end_y_init = end_y

        self.border_color_code = border_color_code
        self.element_alignment = element_alignment

        self.padding_x = max(0, padding_x)
        self.padding_y = max(0, padding_y)
        self.margin_x = max(0, margin_x)
        self.margin_y = max(0, margin_y)

        if self.element_alignment not in ['left', 'center', 'right']:
            raise ValueError("element_alignment must be 'left', 'center', or 'right'.")

        if border_style not in [0, 1, 2]:
            raise ValueError("border_style must be 0 (none), 1 (thin), or 2 (thick).")
        self.border_style = border_style

        # Select border characters based on style
        if self.border_style == 1:
            self._border_chars = self.BORDER_CHARS_THIN
        elif self.border_style == 2:
            self._border_chars = self.BORDER_CHARS_THICK
        else: # border_style == 0
            self._border_chars = self.BORDER_CHARS_NONE

    def _visible_width(self, text):
        """
        Calculates the visible width of a string:
        - Strips ANSI escape codes
        - Properly accounts for wide/fullwidth Unicode characters
        - Ignores zero-width characters
        """
        # Remove ANSI codes
        no_ansi = ANSI_ESCAPE.sub('', text)

        # Normalize the string and filter out non-visible characters
        cleaned = ''.join(
            ch for ch in no_ansi
            if unicodedata.category(ch)[0] != 'C'  # Skip control characters
            and not unicodedata.combining(ch)      # Skip diacritics/zero-width
        )

        # Calculate display width
        return wcswidth(cleaned)

    def render(self, enable_color=True):
        terminal_width, terminal_height = shutil.get_terminal_size(fallback=(100, 20))
        border_color = self.border_color_code if enable_color else ""
        reset = RESET if enable_color else ""

        actual_start_x_with_margin = self._start_x_init if self._start_x_init is not None else 0
        actual_start_y_with_margin = self._start_y_init if self._start_y_init is not None else 0
        actual_end_x_with_margin = self._end_x_init if self._end_x_init is not None else terminal_width - 1

        box_start_x = actual_start_x_with_margin + self.margin_x
        box_start_y = actual_start_y_with_margin + self.margin_y

        if self._end_x_init is not None:
            box_end_x = actual_end_x_with_margin - self.margin_x
        else:
            box_end_x = terminal_width - 1 - self.margin_x

        if box_start_x > box_end_x:
            box_start_x = box_end_x
        box_start_x = max(0, box_start_x)
        box_end_x = min(terminal_width - 1, box_end_x)

        box_width = box_end_x - box_start_x + 1

        total_horizontal_overhead = (
            (2 if self.border_style in [1, 2] else 0)
            + (2 * self.padding_x)
        )
        
        min_box_width_required = total_horizontal_overhead
        if self.box_title:
            min_title_width = self._visible_width(self.box_title) + 2 + total_horizontal_overhead
            min_box_width_required = max(min_box_width_required, min_title_width)

        # --- Step 1: Render all children to find max content width and height ---
        max_child_content_width = 0
        rendered_child_lines = []
        for element in self.elements:
            child_output = element.render(enable_color).rstrip('\n')
            child_lines = child_output.split('\n')
            rendered_child_lines.extend(child_lines)
            for line in child_lines:
                max_child_content_width = max(max_child_content_width, self._visible_width(line))

        # --- Step 2: Calculate final box width and content area width ---
        min_box_width_for_children = max_child_content_width + total_horizontal_overhead
        
        # Determine the final width of the content area
        content_area_width = max(
            box_width - total_horizontal_overhead,
            max_child_content_width,
            (min_box_width_required - total_horizontal_overhead) if min_box_width_required > 0 else 0
        )
        
        box_width = content_area_width + total_horizontal_overhead
        
        # Ensure box doesn't exceed terminal width
        if box_start_x + box_width > terminal_width:
            box_width = terminal_width - box_start_x
            content_area_width = box_width - total_horizontal_overhead
            if content_area_width < 0: content_area_width = 0
        
        box_end_x = box_start_x + box_width - 1
        
        # --- Step 3: Align and pad the pre-rendered child lines ---
        processed_padded_lines = []
        for line in rendered_child_lines:
            line_width = self._visible_width(line)
            additional_padding_needed = max(0, content_area_width - line_width)
            
            dynamic_left_pad = 0
            dynamic_right_pad = 0

            if self.element_alignment == 'center':
                dynamic_left_pad = additional_padding_needed // 2
                dynamic_right_pad = additional_padding_needed - dynamic_left_pad
            elif self.element_alignment == 'right':
                dynamic_left_pad = additional_padding_needed
                dynamic_right_pad = 0

            line_to_add_inner = (
                ' ' * self.padding_x +
                ' ' * dynamic_left_pad +
                line +
                ' ' * dynamic_right_pad +
                ' ' * self.padding_x
            )

            current_line_rendered_width = self._visible_width(line_to_add_inner)
            if current_line_rendered_width < (box_width - total_horizontal_overhead):
                line_to_add_inner += ' ' * ((box_width - total_horizontal_overhead) - current_line_rendered_width)
            elif current_line_rendered_width > (box_width - total_horizontal_overhead):
                # We need to truncate from the end, but be careful with ANSI codes
                visible_chars_to_keep = box_width - total_horizontal_overhead
                truncated_line = ""
                visible_count = 0
                
                # Create a list of (character, is_ansi) tuples
                parts = []
                last_end = 0
                for match in ANSI_ESCAPE.finditer(line_to_add_inner):
                    if match.start() > last_end:
                        for char in line_to_add_inner[last_end:match.start()]:
                            parts.append((char, False))
                    parts.append((match.group(0), True))
                    last_end = match.end()
                if last_end < len(line_to_add_inner):
                    for char in line_to_add_inner[last_end:]:
                        parts.append((char, False))

                current_width = 0
                for char, is_ansi in parts:
                    if is_ansi:
                        truncated_line += char
                    else:
                        char_width = wcswidth(char)
                        if current_width + char_width <= visible_chars_to_keep:
                            truncated_line += char
                            current_width += char_width
                        else:
                            break
                line_to_add_inner = truncated_line

            processed_padded_lines.append(line_to_add_inner)

        if not processed_padded_lines:
            processed_padded_lines = [" " * (content_area_width)]

        # --- Step 4: Calculate final box height and vertical padding ---
        calculated_content_lines_count = len(processed_padded_lines)
        required_content_height = calculated_content_lines_count + (2 * self.padding_y)

        if self._end_y_init is None:
            box_height = required_content_height + (2 if self.border_style in [1, 2] else 0)
            box_end_y = box_start_y + box_height - 1
            actual_end_y_with_margin = box_end_y + self.margin_y
        else:
            actual_end_y_with_margin = self._end_y_init if self._end_y_init is not None else terminal_height - 1
            box_end_y = actual_end_y_with_margin - self.margin_y
            box_height = box_end_y - box_start_y + 1
        
        box_height = max(box_height, 2 if self.border_style in [1, 2] else 0)
        
        vertical_content_area_height = box_height - (2 if self.border_style in [1, 2] else 0)

        vertical_pad_top_inner = 0
        vertical_pad_bottom_inner = 0
        if vertical_content_area_height > required_content_height:
            extra_vertical_space = vertical_content_area_height - required_content_height
            vertical_pad_top_inner = extra_vertical_space // 2
            vertical_pad_bottom_inner = extra_vertical_space - vertical_pad_top_inner
            
        selected_chars = self._border_chars

        # --- Step 5: Construct the final output lines ---
        output_lines_for_box_rendering = []
        
        horizontal_fill_width = box_width - (2 if self.border_style in [1, 2] else 0)

        for _ in range(self.padding_y + vertical_pad_top_inner):
            output_lines_for_box_rendering.append(
                f"{border_color}{selected_chars['vertical']}{' ' * horizontal_fill_width}{selected_chars['vertical']}{reset}"
            )

        for line_content_padded in processed_padded_lines:
            # Re-ensure padding and alignment is correct just before adding borders
            line_width = self._visible_width(line_content_padded)
            padding_right = max(0, horizontal_fill_width - line_width)
            final_content_line = line_content_padded + ' ' * padding_right
            
            output_lines_for_box_rendering.append(
                f"{border_color}{selected_chars['vertical']}{reset}{final_content_line}{border_color}{selected_chars['vertical']}{reset}"
            )
            
        for _ in range(self.padding_y + vertical_pad_bottom_inner):
            output_lines_for_box_rendering.append(
                f"{border_color}{selected_chars['vertical']}{' ' * horizontal_fill_width}{selected_chars['vertical']}{reset}"
            )
            
        top_border_fill = selected_chars['horizontal'] * horizontal_fill_width
        
        if self.box_title and self.border_style in [1, 2]:
            title_text = self.box_title
            title_width = self._visible_width(title_text)
            title_space_around = 2
            
            if title_width + title_space_around > horizontal_fill_width:
                title_text = title_text[:self._visible_width(title_text) - (title_width + title_space_around - horizontal_fill_width)]

            left_dashes = (horizontal_fill_width - self._visible_width(title_text) - 2) // 2
            right_dashes = horizontal_fill_width - self._visible_width(title_text) - 2 - left_dashes
            
            top_border = (
                f"{border_color}{selected_chars['top_left']}"
                f"{selected_chars['horizontal'] * left_dashes}"
                f" {title_text} "
                f"{selected_chars['horizontal'] * right_dashes}"
                f"{selected_chars['top_right']}{reset}"
            )
        else:
            top_border = f"{border_color}{selected_chars['top_left']}{top_border_fill}{selected_chars['top_right']}{reset}"

        bottom_border = f"{border_color}{selected_chars['bottom_left']}{selected_chars['horizontal'] * horizontal_fill_width}{selected_chars['bottom_right']}{reset}"

        # If borders are enabled, add them
        if self.border_style in [1, 2]:
            full_box_output = [top_border] + output_lines_for_box_rendering + [bottom_border]
        else:
            full_box_output = output_lines_for_box_rendering

        final_rendered_block = []
        
        if self.margin_y > 0:
            margin_line_width = box_width + 2 * self.margin_x
            for _ in range(self.margin_y):
                final_rendered_block.append(' ' * margin_line_width)

        for line in full_box_output:
            final_rendered_block.append(' ' * self.margin_x + line + ' ' * self.margin_x)

        if self.margin_y > 0:
            margin_line_width = box_width + 2 * self.margin_x
            for _ in range(self.margin_y):
                final_rendered_block.append(' ' * margin_line_width)

        return "\n".join(final_rendered_block) + "\n"
    
# --- Helper for WidgetElement to convert content to an "element" ---
class _StringElement:
    def __init__(self, text):
        self._text = text
    def render(self, enable_color=True):
        return self._text


class Anchor:
    def __init__(self, text, href, current_anchors, next_anchor_id):
        self.text = text
        self.href = href
        self.tag_type = 'a'

        self.anchor_id = next_anchor_id[0]
        current_anchors[self.anchor_id] = self
        next_anchor_id[0] += 1

    def render(self, enable_color=True):
        if enable_color:
            return f"[{self.anchor_id}] {BLUE_FG}{UNDERLINE}{self.text.strip()}{RESET}"
        return f"[{WHITE_FG}{self.anchor_id}] {self.text.strip()} [{self.href}]"


class TextNode:
    def __init__(self, text):
        self.text = text
        self.tag_type = 'text'

    def render(self, enable_color=True):
        return self.text

class Title:
    def __init__(self, text):
        self.text = text
        self.tag_type = 'title'

    def _visible_width(self, text):
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        return wcswidth(clean_text)

    def render(self, enable_color=True):
        terminal_width = shutil.get_terminal_size((80, 20)).columns

        fixed_width_for_box = 6
        max_text_width = terminal_width - fixed_width_for_box - 2

        styled_text = f"{BOLD}{CYAN_FG}{self.text}{RESET}" if enable_color else self.text
        text_visible_width = self._visible_width(styled_text)

        wrapped_lines = wrap(styled_text, max_text_width, drop_whitespace=False, break_long_words=False)

        actual_content_width = 0
        if wrapped_lines:
            actual_content_width = max(self._visible_width(line) for line in wrapped_lines)

        min_box_width = 10
        box_inner_width = max(actual_content_width, min_box_width)

        top_border = f"╭{'─' * (box_inner_width + 4)}╮"
        bottom_border = f"╰{'─' * (box_inner_width + 4)}╯"

        middle_lines = []
        for line in wrapped_lines:
            current_line_visible_width = self._visible_width(line)
            padding_right = box_inner_width - current_line_visible_width + 2
            middle_lines.append(f"│  {line}{' ' * padding_right}│")

        if not middle_lines:
            middle_lines.append(f"│{' ' * (box_inner_width + 4)}│")

        return f"{top_border}\n" + "\n".join(middle_lines) + f"\n{bottom_border}\n"


class Paragraph:
    def __init__(self, content_parts):
        self.content_parts = content_parts
        self.tag_type = 'p'

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

    def render(self, enable_color=True, inline=False):
        # Add 'inline' parameter to handle rendering within other elements
        if inline or self.level != 1: # If inline or not h1, use text styling
            style = ""
            if enable_color:
                if self.level == 1:
                    style = f"{BOLD}{BLUE_FG}" # Blue for h1 in inline contexts
                elif self.level == 2:
                    style = f"{BOLD}{MINT_GREEN_FG}"
                elif self.level == 3:
                    style = f"{BOLD}{SUNNY_YELLOW_FG}"
                else:
                    style = f"{BOLD}{LIGHT_BRICK_FG}"
            return f"\n{style}{'#' * self.level} {self.text}{RESET}"
        else: # Original h1 braille art rendering
            braille = braillify(self.text, color=enable_color)
            return f"\n{braille}\n\n"

class ListElement:
    def __init__(self, items_content_parts):
        self.items_content_parts = items_content_parts
        self.tag_type = 'ul'

    def render(self, enable_color=True, inline=False):
        bullet_style = f"{CYAN_FG}" if enable_color else ""
        rendered_items = []
        for item_parts in self.items_content_parts:
            item_text = "".join(
                part.render(enable_color, inline=True) if hasattr(part, "render") and "inline" in part.render.__code__.co_varnames
                else part.render(enable_color) if hasattr(part, "render")
                else str(part)
                for part in item_parts
            )
            rendered_items.append(f"{bullet_style}•{RESET if enable_color else ''} {item_text}")

        if inline:
            return ", ".join(rendered_items)
        return "\n".join(rendered_items) + "\n"

class NumberedListElement:
    def __init__(self, items_content_parts):
        self.items_content_parts = items_content_parts
        self.tag_type = 'ol'

    def render(self, enable_color=True, inline=False):
        numbered_style = f"{MAGENTA_FG}" if enable_color else ""
        rendered_items = []
        for i, item_parts in enumerate(self.items_content_parts, 1):
            item_text = "".join(
                part.render(enable_color, inline=True) if hasattr(part, "render") and "inline" in part.render.__code__.co_varnames
                else part.render(enable_color) if hasattr(part, "render")
                else str(part)
                for part in item_parts
            )
            rendered_items.append(f"{numbered_style}{i}.{RESET if enable_color else ''} {item_text}")
        if inline:
            return ", ".join(rendered_items)
        return "\n".join(rendered_items) + "\n"

class TableElement:
    def __init__(self, headers, rows, max_width=None):
        self.headers = headers
        self.rows = rows
        self.max_width = max_width or shutil.get_terminal_size((100, 20)).columns
        self.tag_type = 'table'

    def _visible_width(self, text):
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        return wcswidth(clean_text)

    def _wrap_cell(self, text, width):
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')

        lines = []
        current_line_parts = []
        current_line_visible_width = 0

        initial_ansi_codes = "".join(re.findall(ansi_escape, text))
        parts = re.split(r'(\x1b\[[0-9;]*m)', text)
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
            else:
                for char in part_content:
                    char_width = wcswidth(char)
                    if current_line_visible_width + char_width > width:
                        lines.append("".join(current_line_parts) + RESET)
                        current_line_parts = [initial_ansi_codes]
                        current_line_visible_width = 0
                    current_line_parts.append(char)
                    current_line_visible_width += char_width

        if current_line_parts:
            lines.append("".join(current_line_parts) + RESET)

        return lines

    def render(self, enable_color=True):
        if not self.headers and not self.rows:
            return ""

        all_cells = [self.headers] + self.rows
        num_cols = max(len(row) for row in all_cells)
        column_widths = [0] * num_cols

        cell_texts = []

        for row in all_cells:
            row_texts = []
            for i, cell_parts in enumerate(row):
                # Modified: Pass inline=True to render for all table cell contents
                text = "".join(
                    part.render(enable_color, inline=True) if hasattr(part, "render") and "inline" in part.render.__code__.co_varnames
                    else part.render(enable_color) if hasattr(part, "render")
                    else str(part)
                    for part in cell_parts
                )
                width = self._visible_width(text)
                if i < num_cols and width > column_widths[i]:
                    column_widths[i] = width
                row_texts.append(text)
            cell_texts.append(row_texts)

        column_widths = [w + 2 for w in column_widths]
        total_width = sum(column_widths) + len(column_widths) + 1

        if total_width > self.max_width:
            available = self.max_width - (len(column_widths) + 1)
            min_col_width = 6
            flexible_cols = [max(min_col_width, int(w * available / sum(column_widths))) for w in column_widths]
            column_widths = flexible_cols

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
                    if is_header and enable_color:
                        cell = f" {BOLD}{txt}{RESET}" + " " * pad_len
                    else:
                        cell = f" {txt}" + " " * pad_len
                    line_cells.append(cell)
                output_lines.append("│" + "│".join(line_cells) + "│")

        if self.headers:
            render_row(cell_texts[0], is_header=True)
            output_lines.append(middle_border)

        for row in cell_texts[1:]:
            render_row(row)

        output_lines.append(bottom_border)
        return "\n".join(output_lines) + "\n"

class Button(Box):
    def __init__(self, label,
                 border_color_code=WHITE_FG,
                 padding_x=1, padding_y=0,
                 margin_x=0, margin_y=0,
                 border_style=1):
        self.label = label
        self._label_element = _StringElement(f"{BOLD}{label}{RESET}")

        # Use dummy end_x; will override it later in render
        super().__init__(
            elements=[self._label_element],
            tag_type='button',
            box_title=None,
            start_x=0,
            end_x=10,  # placeholder, will be adjusted
            border_color_code=border_color_code,
            element_alignment='center',
            padding_x=padding_x,
            padding_y=padding_y,
            margin_x=margin_x,
            margin_y=margin_y,
            border_style=border_style
        )

    def render(self, enable_color=True):
        # Measure visible width of label (excluding ANSI)
        label_width = wcswidth(re.sub(r'\x1b\[[0-9;]*m', '', self.label))

        # Compute tight box width: borders + paddings + label
        total_width = 2 + (2 * self.padding_x) + label_width
        self._end_x_init = self._start_x_init + total_width + (2 * self.margin_x) - 1

        # Recreate element list just in case render() is reused
        self.elements = [_StringElement(f"{BOLD}{self.label}{RESET}")]

        return super().render(enable_color)

class Div:
    def __init__(self, *elements):
        self.elements = elements
        self.tag_type = 'div'

    def render(self, enable_color=True):
        rendered_children = []
        for element in self.elements:
            rendered_child = element.render(enable_color)
            if rendered_child.endswith('\n'):
                rendered_children.append(rendered_child)
            else:
                rendered_children.append(rendered_child + '\n')

        content = "".join(rendered_children).strip()
        if content:
            return f"\n{content}\n"
        return ""


class ImageElement:
    def __init__(self, src, width=None, height=None, base_url=None, max_width=80, alt=""):
        self.src = src
        self.width = width
        self.height = height
        self.base_url = base_url
        self.max_width = max_width
        self.tag_type = 'img'
        self.alt = alt

    def render(self, enable_color=True):
        try:
            image_url = self.src
            if self.src.startswith("/"):
                if self.base_url:
                    image_url = self.base_url.rstrip("/") + self.src

            response = requests.get(image_url, timeout=5)
            response.raise_for_status()
            image_file = io.BytesIO(response.content)

            target_w = int(self.width // 4) if self.width else None
            target_h = int(self.height // 5) if self.height else None

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
            return f"[Image: {self.alt if self.alt else self.src}]"

class Nav:
    def __init__(self, elements):
        self.elements = elements
        self.tag_type = 'nav'

    def _visible_width(self, text):
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        return wcswidth(clean_text)


    def render(self, enable_color=True):
        if not self.elements:
            return ""

        # === 1. Render all elements and find the maximum width ===
        rendered_parts_info = []
        max_width = 0
        min_padding = 1

        for element in self.elements:
            if hasattr(element, "render"):
                # --- NEW LOGIC: Temporarily disable button borders ---
                original_border_style = getattr(element, 'border_style', None)
                is_button = isinstance(element, Button)
                if is_button:
                    element.border_style = 0

                # --- OLD LOGIC ---
                # rendered_text = element.render(enable_color=enable_color).strip()

                # --- NEW LOGIC: Pass inline=True if the render method supports it ---
                if hasattr(element.render, '__code__') and 'inline' in element.render.__code__.co_varnames:
                    rendered_text = element.render(enable_color=enable_color, inline=True).strip()
                else:
                    rendered_text = element.render(enable_color=enable_color).strip()


                visible_w = self._visible_width(rendered_text)
                rendered_parts_info.append((rendered_text, visible_w))
                if visible_w > max_width:
                    max_width = visible_w

                # --- NEW LOGIC: Restore original border style ---
                if is_button and original_border_style is not None:
                    element.border_style = original_border_style

        # The total width of each cell, including padding and borders
        cell_total_width = max_width + 2 * min_padding
        
        final_output = []

        # === 2. Create the top border ===
        top_border = "╭" + "─" * cell_total_width + "╮"
        final_output.append(top_border)

        # === 3. Render each element with the consistent width ===
        for i, (text, w) in enumerate(rendered_parts_info):
            # Content line with padding to align text to the left
            left_pad = min_padding
            right_pad = cell_total_width - w - left_pad
            content_line = "│" + " " * left_pad + text + " " * right_pad + "│"
            final_output.append(content_line)

            # Add a middle border if it's not the last element
            if i < len(rendered_parts_info) - 1:
                middle_border = "├" + "─" * cell_total_width + "┤"
                final_output.append(middle_border)

        # === 4. Create the bottom border ===
        bottom_border = "╰" + "─" * cell_total_width + "╯"
        final_output.append(bottom_border)

        return "\n".join(final_output) + "\n"
    
class Header(Box):
    def __init__(self, elements, start_x=0, end_x=None, border_color_code=BLUE_FG,
                 element_alignment='left', padding_x=1, padding_y=0, margin_x=0, margin_y=0):
        super().__init__(
            elements=elements,
            tag_type='header',
            start_x=start_x,
            start_y=0,
            end_x=end_x,
            end_y=None, # Dynamic height
            border_color_code=border_color_code,
            element_alignment=element_alignment,
            padding_x=padding_x, padding_y=padding_y,
            margin_x=margin_x, margin_y=margin_y
        )

class Footer(Box):
    def __init__(self, elements, start_x=0, end_x=None, border_color_code=WHITE_FG,
                 element_alignment='left', padding_x=1, padding_y=0, margin_x=0, margin_y=0):
        super().__init__(
            elements=elements,
            tag_type='footer',
            start_x=start_x,
            start_y=None, # Typically positioned by a layout manager at the bottom
            end_x=end_x,
            end_y=None, # Dynamic height
            border_color_code=border_color_code,
            element_alignment=element_alignment,
            padding_x=padding_x, padding_y=padding_y,
            margin_x=margin_x, margin_y=margin_y
        )

class WidgetElement(Box):
    def __init__(self, widget_type, dashboard_generator,
                 start_x=0, start_y=0, box_width=60, end_y=None, # box_width for convenience
                 border_color_code=WHITE_FG, element_alignment='left',
                 padding_x=1, padding_y=0, margin_x=0, margin_y=1): # Added default margin for widgets

        self.widget_type = widget_type
        self.dashboard_generator = dashboard_generator

        total_rendered_width = box_width + (2 * margin_x)
        calculated_end_x = start_x + total_rendered_width - 1

        super().__init__(
            elements=[],
            tag_type='widget',
            box_title=widget_type.capitalize(),
            start_x=start_x,
            start_y=start_y,
            end_x=calculated_end_x, # This end_x now includes the margin
            end_y=end_y, # Dynamic height
            border_color_code=border_color_code,
            element_alignment=element_alignment,
            padding_x=padding_x, padding_y=padding_y,
            margin_x=margin_x, margin_y=margin_y
        )

    def render(self, enable_color=True):
        content_lines = []

        # Mocking dashboard_generator methods for demonstration
        class MockDashboardGenerator:
            def get_local_time(self):
                return "1:00 PM"
            def get_weather_data(self):
                return "Partly Cloudy, 30°C"
            def get_news_headlines(self):
                return ["Breaking News: New Feature!", "Local Sports Update", "Another headline here for testing height and width"]

        if not self.dashboard_generator:
            self.dashboard_generator = MockDashboardGenerator()

        if self.widget_type == "time":
            time_data = self.dashboard_generator.get_local_time()
            content_lines.append(f"Current Time: {BOLD}{time_data}{RESET}")
        elif self.widget_type == "weather":
            weather_data = self.dashboard_generator.get_weather_data()
            content_lines.append(f"Weather: {BOLD}{weather_data}{RESET}")
        elif self.widget_type == "news":
            news_headlines = self.dashboard_generator.get_news_headlines()
            if news_headlines:
                content_lines.append(f"{BOLD}Latest News:{RESET}")
                content_lines.extend([f"  • {headline}" for headline in news_headlines])
            else:
                content_lines.append("No news available.")
        else:
            content_lines.append(f"Unknown widget type: {self.widget_type}")

        original_elements = self.elements
        self.elements = [_StringElement("\n".join(content_lines))]

        rendered_output = super().render(enable_color)

        self.elements = original_elements
        return rendered_output
    
class HorizontalRule:
    def __init__(self):
        self.tag_type = 'hr'

    def render(self, enable_color=True):
        terminal_width, _ = shutil.get_terminal_size(fallback=(80, 20))
        line = "─" * terminal_width
        if enable_color:
            return f"{WHITE_FG}{line}{RESET}\n"
        return f"{line}\n"