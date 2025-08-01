import io
import re
import sys
import shutil
from textwrap import wrap
from wcwidth import wcswidth
import requests
from core.braillify import braillify
from core.image_render import image_to_terminal_art
from core.ansi import *
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

    def render(self, enable_color=True):
        if self.level == 1:
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
                else:
                    image_url = "https://www.google.com" + self.src

            response = requests.get(image_url, timeout=5)
            response.raise_for_status()
            image_file = io.BytesIO(response.content)

            target_w = int(self.width) // 4 if self.width else None
            target_h = int(self.height) // 5 if self.height else None

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
            return f"[Image]"
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

        terminal_width = shutil.get_terminal_size((100, 20)).columns

        rendered_parts_info = []
        for element in self.elements:
            # Ensure elements within Nav (like Anchors) are rendered appropriately
            rendered_text = element.render(enable_color).strip()
            visible_w = self._visible_width(rendered_text)
            rendered_parts_info.append((rendered_text, visible_w))

        num_items = len(rendered_parts_info)
        min_padding = 2
        inner_borders = num_items - 1
        outer_borders = 2

        total_text_width = sum(w for _, w in rendered_parts_info)
        base_cell_widths = [
            w + 2 * min_padding for _, w in rendered_parts_info
        ]
        base_total = sum(base_cell_widths) + inner_borders + outer_borders

        extra_space = max(0, terminal_width - base_total)

        extra_per_cell = [0] * num_items
        for i in range(extra_space):
            extra_per_cell[i % num_items] += 1

        padded_column_widths = [
            base + extra for base, extra in zip(base_cell_widths, extra_per_cell)
        ]

        def make_border(left, mid, right, fill):
            return left + mid.join(fill * w for w in padded_column_widths) + right

        top_border = make_border("╭", "┬", "╮", "─")
        bottom_border = make_border("╰", "┴", "╯", "─")
        output_lines = [top_border]

        content_cells = []
        for i, (text, visible_w) in enumerate(rendered_parts_info):
            cell_width = padded_column_widths[i]
            total_padding = cell_width - visible_w
            left_pad = total_padding // 2
            right_pad = total_padding - left_pad
            cell_text = f"{text}{RESET if enable_color else ''}"
            content_cells.append(" " * left_pad + cell_text + " " * right_pad)

        output_lines.append("│" + "│".join(content_cells) + "│")
        output_lines.append(bottom_border)

        return "\n".join(output_lines) + "\n"

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
    # Style 0: No border (uses spaces)
    BORDER_CHARS_NONE = {
        'top_left': ' ', 'top_right': ' ',
        'bottom_left': ' ', 'bottom_right': ' ',
        'horizontal': ' ', 'vertical': ' '
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
        """Calculates the visible width of a string, ignoring ANSI escape codes."""
        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
        return wcswidth(clean_text)

    def render(self, enable_color=True):
        terminal_width, terminal_height = shutil.get_terminal_size(fallback=(100, 20))

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

        # Total fixed horizontal overhead = 2 (borders) + 2 * padding_x
        # If border_style is 0 (none), borders contribute 0 width effectively.
        # But for consistency in calculations, we can treat them as 1 char wide and then substitute with space.
        # For 'no border' style, the border characters themselves are spaces, so they still occupy a character width.
        # The key is that `box_width` is the total width, and `total_horizontal_overhead` is how much of that is taken by fixed elements.
        
        # Total fixed horizontal overhead = 2 (vertical border characters) + 2 * padding_x
        # This is the space consumed by the border characters and internal padding.
        total_horizontal_overhead = 2 + (2 * self.padding_x) 

        # Minimum width for box borders, title, and total internal padding
        min_content_area_for_title = 0
        if self.box_title:
            min_content_area_for_title = self._visible_width(self.box_title) + 2 # "─Title─"

        min_box_width_required = max(min_content_area_for_title + total_horizontal_overhead, total_horizontal_overhead)
        
        if box_width < min_box_width_required:
            box_width = min_box_width_required
            box_end_x = box_start_x + box_width - 1
            if box_end_x >= terminal_width:
                 box_width = terminal_width - box_start_x
                 box_end_x = terminal_width - 1


        rendered_children_lines = []
        for element in self.elements:
            child_output = element.render(enable_color).rstrip('\n')
            rendered_children_lines.extend(child_output.split('\n'))

        content_lines = rendered_children_lines
        if not content_lines:
            content_lines = [""] 

        border_color = self.border_color_code if enable_color else ""
        reset = RESET if enable_color else ""

        max_text_content_width = box_width - total_horizontal_overhead 
        if max_text_content_width < 0:
            max_text_content_width = 0

        processed_padded_lines = []
        for line in content_lines:
            line_stripped = re.sub(r'\x1b\[[0-9;]*m', '', line)
            line_width = self._visible_width(line_stripped)

            current_line_content = line
            
            if line_width > max_text_content_width:
                current_line_content = line_stripped[:max_text_content_width]
                line_width = self._visible_width(current_line_content)

            additional_padding_needed = max_text_content_width - line_width
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
                current_line_content +
                ' ' * dynamic_right_pad +
                ' ' * self.padding_x
            )
            
            rendered_inner_line_width = self._visible_width(re.sub(r'\x1b\[[0-9;]*m', '', line_to_add_inner))
            if rendered_inner_line_width < (box_width - 2):
                line_to_add_inner += ' ' * ((box_width - 2) - rendered_inner_line_width)
            elif rendered_inner_line_width > (box_width - 2):
                line_to_add_inner = line_to_add_inner[:(box_width - 2)] 
            
            processed_padded_lines.append(line_to_add_inner)
        
        calculated_content_height = len(processed_padded_lines) + 2 + (2 * self.padding_y) 

        if self._end_y_init is None:
            box_height = calculated_content_height
            box_end_y = box_start_y + box_height - 1
            actual_end_y_with_margin = box_end_y + self.margin_y
        else:
            actual_end_y_with_margin = self._end_y_init if self._end_y_init is not None else terminal_height - 1
            box_end_y = actual_end_y_with_margin - self.margin_y
            box_height = box_end_y - box_start_y + 1
        
        box_height = max(box_height, 2) 

        vertical_content_area_height = box_height - 2 
        required_content_lines_for_padding = len(processed_padded_lines) + (2 * self.padding_y) 
        
        vertical_pad_top_inner = 0
        vertical_pad_bottom_inner = 0
        if vertical_content_area_height > required_content_lines_for_padding:
            extra_vertical_space = vertical_content_area_height - required_content_lines_for_padding
            vertical_pad_top_inner = extra_vertical_space // 2
            vertical_pad_bottom_inner = extra_vertical_space - vertical_pad_top_inner
            
        # Select border characters for the current render
        selected_chars = self._border_chars

        # Construct the top border with the title
        top_border_fill = selected_chars['horizontal'] * (box_width - 2)
        if self.box_title:
            title_text = self.box_title
            title_width = self._visible_width(title_text)
            
            # The title string itself takes up `title_width` space.
            # We want "Corner-Dash-Title-Dash-Dashes-Corner"
            # So, `selected_chars['horizontal'] + title_text + selected_chars['horizontal']`
            # This segment has width `1 + title_width + 1 = title_width + 2`
            # Remaining dashes needed in the fill part of the border.
            dashes_after_title = (box_width - 2) - (title_width + 2)
            if dashes_after_title < 0:
                dashes_after_title = 0

            top_border = (
                f"{border_color}{selected_chars['top_left']}{selected_chars['horizontal']}{title_text}{selected_chars['horizontal']}" +
                selected_chars['horizontal'] * dashes_after_title +
                f"{selected_chars['top_right']}{reset}"
            )
        else:
            top_border = f"{border_color}{selected_chars['top_left']}{top_border_fill}{selected_chars['top_right']}{reset}"

        bottom_border = f"{border_color}{selected_chars['bottom_left']}{selected_chars['horizontal'] * (box_width - 2)}{selected_chars['bottom_right']}{reset}"
        
        output_lines_for_box_rendering = []
        
        # Add top padding_y rows and vertical center padding
        for _ in range(self.padding_y + vertical_pad_top_inner):
            output_lines_for_box_rendering.append(f"{border_color}{selected_chars['vertical']}{' ' * (box_width - 2)}{selected_chars['vertical']}{reset}")

        # Add processed content lines
        for line_content_padded in processed_padded_lines:
            output_lines_for_box_rendering.append(f"{border_color}{selected_chars['vertical']}{reset}{line_content_padded}{border_color}{selected_chars['vertical']}{reset}")

        # Add bottom padding_y rows and vertical center padding
        for _ in range(self.padding_y + vertical_pad_bottom_inner):
            output_lines_for_box_rendering.append(f"{border_color}{selected_chars['vertical']}{' ' * (box_width - 2)}{selected_chars['vertical']}{reset}")

        full_box_output = [top_border] + output_lines_for_box_rendering + [bottom_border]

        # Apply Margin
        final_rendered_block = []

        # Add top margin
        for _ in range(self.margin_y):
            # Width of the line including horizontal margins (box_width + 2 * margin_x)
            final_rendered_block.append(' ' * (box_width + 2 * self.margin_x))

        # Add box with horizontal margins
        for line in full_box_output:
            final_rendered_block.append(' ' * self.margin_x + line + ' ' * self.margin_x)

        # Add bottom margin
        for _ in range(self.margin_y):
            final_rendered_block.append(' ' * (box_width + 2 * self.margin_x))

        return "\n".join(final_rendered_block) + "\n"

# --- Helper for WidgetElement to convert content to an "element" ---
class _StringElement:
    def __init__(self, text):
        self._text = text
    def render(self, enable_color=True):
        return self._text
    
class Header(Box):
    def __init__(self, elements, start_x=0, end_x=None, border_color_code=BLUE_FG, 
                 element_alignment='center', padding_x=1, padding_y=0, margin_x=0, margin_y=0):
        super().__init__(
            elements=elements, 
            tag_type='header', 
            box_title="Header", 
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
                 element_alignment='center', padding_x=1, padding_y=0, margin_x=0, margin_y=0):
        super().__init__(
            elements=elements, 
            tag_type='footer', 
            box_title="Footer", 
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
                 start_x=0, start_y=0, box_width=40, end_y=None, # box_width for convenience
                 border_color_code=WHITE_FG, element_alignment='left',
                 padding_x=1, padding_y=0, margin_x=2, margin_y=1): # Added default margin for widgets
        
        self.widget_type = widget_type
        self.dashboard_generator = dashboard_generator

        # Calculate end_x based on start_x and desired box_width, accounting for margins
        # The box_width here is the desired width *including* padding and borders, but *excluding* margin
        # So the actual end_x for BoxedContent should be start_x_with_margin + box_width + 2*margin_x - 1
        # No, the BoxedContent's start_x and end_x are where the *full rendered block including margin* starts/ends.
        # So, if we want a `box_width` (border-to-border) of 40, and margin_x=2:
        # The total width on the terminal is `2*margin_x + box_width`.
        # So, end_x for BoxedContent should be `start_x_init + (2 * margin_x) + box_width - 1`.
        
        # Let's adjust the interpretation: `start_x` and `end_x` for BoxedContent already
        # account for the margin space if they are passed. The `box_width` here should be
        # the *internal* box width that the user wants to set.
        
        # So, the actual width that BoxedContent will calculate for `box_width` (border to border)
        # from `end_x - start_x + 1` should be `(given end_x - given start_x + 1) - (2 * margin_x)`.
        
        # Let's keep `start_x` and `end_x` for BoxedContent as the *outermost* coordinates
        # (including margin). The `box_width` in WidgetElement should then define the
        # width *from border to border*.
        
        # `start_x` and `end_x` for `BoxedContent` are already for the margin-inclusive region.
        # So, if `box_width` for `WidgetElement` is specified, it means the width of the box
        # itself, excluding margin.
        
        # The `start_x` and `end_x` for BoxedContent already include the margin as the outermost bounds.
        # If `box_width` is passed, it should define the *actual content width + padding + border*.
        # So, the `end_x` passed to BoxedContent must be `start_x + box_width_desired + 2*margin_x - 1`
        
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