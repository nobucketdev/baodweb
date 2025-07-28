import sys
from bs4 import BeautifulSoup, Comment, Doctype
import re
from core.elements import *

SUPPORTED_TAGS = {'html', 'body', 'section', 'article', 'main', 'div',
                'h1', 'h2', 'h3', 'p', 'ul', 'ol', 'li', 'a', 'button', 'img', 'nav',
                'table', 'thead', 'tbody', 'tr', 'th', 'td', 'strong', 'b', 'em', 'i', 'u', 'del', 'ins', 'mark', 'sub', 'sup', 'span',
                'widget'} # Added 'widget' and 'title' here


class Parser:
    def __init__(self, dashboard_generator=None): # Pass dashboard_generator to parser
        self.dashboard_generator = dashboard_generator

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
        soup = BeautifulSoup(html, 'lxml')
        elements = []
        page_title = "No Title"

        title_tag = soup.find('title')
        if title_tag:
            page_title = title_tag.get_text(strip=True)
            # Add the Title object to the elements list for rendering
            elements.append(Title(page_title)) 

        root = soup.find('html') or soup
        # Filter out the 'title' tag from being parsed as a generic text node
        # We handle it specifically above.
        for child in root.children:
            if child.name == 'title':
                continue
            elements.extend(self.parse_element(child, current_anchors, next_anchor_id)) 
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

        if tag_name in ['style', 'script', 'noscript']:
            # Ignore content inside these tags completely
            return []
        
        if tag_name == 'title': # Handle title tag specifically for rendering
            title_text = tag.get_text(strip=True)
            return [Title(title_text)]

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
        
        # New widget tag handling
        elif tag_name == 'widget':
            widget_type = tag.get('type')
            if widget_type and self.dashboard_generator:
                return [WidgetElement(widget_type, self.dashboard_generator)]
            else:
                print(f"Warning: <widget> tag found without 'type' attribute or dashboard_generator not provided.", file=sys.stderr)
                return []

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

                if tag_name in {'script', 'style', 'noscript', 'title'}: # Ensure title is skipped here too
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
                # Handle widget tag in inline content (though typically block-level, good for robustness)
                elif tag_name == 'widget':
                    widget_type = content_node.get('type')
                    if widget_type and self.dashboard_generator:
                        parsed_inline_elements.append(WidgetElement(widget_type, self.dashboard_generator))
                    else:
                        # Fallback to text if widget cannot be rendered
                        text = content_node.get_text(strip=True)
                        if text:
                            parsed_inline_elements.append(TextNode(text))
                else:
                    # For other unsupported inline tags, just get their text content
                    # Keep strip=True here, as it's typically for the text content within the tag.
                    text = content_node.get_text(strip=True)
                    if text:
                        parsed_inline_elements.append(TextNode(text))

        return parsed_inline_elements