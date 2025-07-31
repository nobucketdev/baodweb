import sys
from bs4 import BeautifulSoup, Comment, Doctype
import re
from core.elements import * # Assuming core.elements contains all your Element classes
import lxml

SUPPORTED_TAGS = {
    'html', 'body', 'section', 'article', 'main', 'div',
    'header', 'footer',  # <-- new structural tags
    'h1', 'h2', 'h3', 'p', 'ul', 'ol', 'li', 'a', 'button', 'img', 'nav',
    'table', 'thead', 'tbody', 'tr', 'th', 'td', 'strong', 'b', 'em', 'i', 'u', 'del', 'ins', 'mark', 'sub', 'sup', 'span',
    'widget'
}


class Parser:
    def __init__(self, dashboard_generator=None):
        self.dashboard_generator = dashboard_generator

    SUBSCRIPT_MAP = {
        '0': '\u2080', '1': '\u2081', '2': '\u2082', '3': '\u2083', '4': '\u2084',
        '5': '\u2085', '6': '\u2086', '7': '\u2087', '8': '\u2088', '9': '\u2089',
        '+': '\u208a', '-': '\u208b', '=': '\u208c', '(': '\u208d', ')': '\u208e',
        'a': '\u2090', 'e': '\u2091', 'o': '\u2092', 'x': '\u2093'
    }

    SUPERSCRIPT_MAP = {
        '0': '\u2070', '1': '\u00b9', '2': '\u00b2', '3': '\u00b3', '4': '\u2074',
        '5': '\u2075', '6': '\u2076', '7': '\u2077', '8': '\u2078', '9': '\u2079',
        '+': '\u207a', '-': '\u207b', '=': '\u207c', '(': '\u207d', ')': '\u207e',
        'i': '\u2071', 'n': '\u207f'
    }

    def _convert_to_unicode_sub_sup(self, text, is_subscript):
        mapping = self.SUBSCRIPT_MAP if is_subscript else self.SUPERSCRIPT_MAP
        return ''.join(mapping.get(char, char) for char in text)

    def parse(self, html, current_anchors=None, next_anchor_id=None):
        soup = BeautifulSoup(html, 'lxml')
        elements = []
        page_title = "No Title"

        title_tag = soup.find('title')
        if title_tag:
            page_title = title_tag.get_text(strip=True)
            elements.append(Title(page_title))

        root = soup.find('html') or soup.find('body') or soup

        # Initialize lists for different sections
        nav_elements = []
        header_elements = []
        main_elements = []
        footer_elements = []
        other_elements = []

        # Find specific sections and parse them
        nav_tag = root.find('nav', recursive=True)
        if nav_tag:
            nav_elements.extend(self.parse_element(nav_tag, current_anchors, next_anchor_id))

        header_tag = root.find('header', recursive=True)
        if header_tag:
            header_elements.extend(self.parse_element(header_tag, current_anchors, next_anchor_id))

        main_tag = root.find('main', recursive=True)
        if main_tag:
            # Parse only direct children of 'main' to avoid re-parsing nav/header/footer if they are inside main
            for child in main_tag.children:
                main_elements.extend(self.parse_element(child, current_anchors, next_anchor_id))
        else:
            # If no explicit 'main' tag, parse top-level children that are not nav, header, or footer
            for child in root.children:
                if getattr(child, 'name', None) not in ['nav', 'header', 'footer', 'title', 'script', 'style', 'noscript']:
                    other_elements.extend(self.parse_element(child, current_anchors, next_anchor_id))


        footer_tag = root.find('footer', recursive=True)
        if footer_tag:
            footer_elements.extend(self.parse_element(footer_tag, current_anchors, next_anchor_id))
            
        # Assemble elements in the desired order
        final_elements = []
        # Add page title first if it exists
        for el in elements:
            if isinstance(el, Title):
                final_elements.append(el)
                break
        
        final_elements.extend(nav_elements)
        final_elements.extend(header_elements)
        final_elements.extend(main_elements if main_elements else other_elements) # Use main_elements if present, else other
        final_elements.extend(footer_elements)


        return final_elements, page_title

    def parse_element(self, tag, current_anchors=None, next_anchor_id=None):
        if isinstance(tag, str):
            text = tag.strip()
            return [TextNode(text)] if text else []

        if not hasattr(tag, 'name') or isinstance(tag, (Comment, Doctype)):
            return []

        tag_name = tag.name.lower()

        if tag_name in {'style', 'script', 'noscript'}:
            return []

        text = tag.get_text(strip=True)

        if tag_name == 'title':
            return [Title(text)]

        if tag_name in {'h1', 'h2', 'h3'}:
            return [Heading(text, level=int(tag_name[1]))]

        if tag_name == 'p':
            return [Paragraph(self._parse_inline_content(tag, current_anchors, next_anchor_id))]

        if tag_name in {'ul', 'ol'}:
            list_class = ListElement if tag_name == 'ul' else NumberedListElement
            items = [
                self._parse_inline_content(li, current_anchors, next_anchor_id)
                for li in tag.find_all('li', recursive=False)
            ]
            return [list_class(items)]

        if tag_name == 'a':
            href = tag.get('href', '#')
            return [Anchor(text, href, current_anchors, next_anchor_id)]

        if tag_name == 'button':
            return [Button(text)]

        if tag_name == 'img':
            src = tag.get('src')
            if src:
                return [ImageElement(
                    src,
                    width=tag.get('width'),
                    height=tag.get('height'),
                    alt=tag.get('alt', '')
                )]
            return []

        if tag_name == 'table':
            headers, rows = [], []

            thead = tag.find('thead')
            if thead:
                headers = [self._parse_inline_content(th, current_anchors, next_anchor_id)
                           for th in thead.find_all('th')]
            else:
                first_tr = tag.find('tr')
                if first_tr and first_tr.find('th'):
                    headers = [self._parse_inline_content(th, current_anchors, next_anchor_id)
                               for th in first_tr.find_all('th')]

            tbody = tag.find('tbody')
            trs = tbody.find_all('tr') if tbody else tag.find_all('tr')[1 if headers else 0:]

            for tr in trs:
                cells = [self._parse_inline_content(td, current_anchors, next_anchor_id)
                         for td in tr.find_all(['td', 'th'])]
                rows.append(cells)

            return [TableElement(headers, rows)]

        if tag_name in {'div', 'body', 'html', 'section', 'article', 'main'}:
            children = [child for child in tag.contents if hasattr(child, 'name') or isinstance(child, str)]
            elements = []
            for child in children:
                elements.extend(self.parse_element(child, current_anchors, next_anchor_id))
            div = Div(*elements)
            if tag_name != 'div':
                div.tag_type = tag_name
            return [div]

        if tag_name == 'nav':
            elements = [element
                        for child in tag.contents
                        for element in self.parse_element(child, current_anchors, next_anchor_id)]
            return [Nav(elements)]
        
        if tag_name == 'header':
            elements = [element
                        for child in tag.contents
                        for element in self.parse_element(child, current_anchors, next_anchor_id)]
            return [Header(elements)]

        if tag_name == 'footer':
            elements = [element
                        for child in tag.contents
                        for element in self.parse_element(child, current_anchors, next_anchor_id)]
            return [Footer(elements)]


        if tag_name == 'widget':
            widget_type = tag.get('type')
            if widget_type and self.dashboard_generator:
                return [WidgetElement(widget_type, self.dashboard_generator)]
            else:
                print(f"Warning: <widget> tag without 'type' or missing dashboard_generator", file=sys.stderr)
                return []

        # Fallback
        elements = [element
                    for child in tag.contents
                    for element in self.parse_element(child, current_anchors, next_anchor_id)]
        if not elements and text:
            elements.append(TextNode(text))
        return elements

    def _parse_inline_content(self, parent_tag, current_anchors=None, next_anchor_id=None):
        parsed = []

        for node in parent_tag.contents:
            if isinstance(node, (Comment, Doctype)):
                continue

            if isinstance(node, str):
                text = re.sub(r'\s+', ' ', node)
                if not text.strip() or any(s in text.lower() for s in ("endif", "[if", "<!")):
                    continue
                parsed.append(TextNode(text))
                continue

            if not hasattr(node, 'name'):
                continue

            tag_name = node.name.lower()
            text = node.get_text(strip=True)

            if tag_name in {'script', 'style', 'noscript', 'title'}:
                continue

            if tag_name == 'a':
                href = node.get('href', '#')
                if text:
                    parsed.append(Anchor(text, href, current_anchors, next_anchor_id))

            elif tag_name == 'img':
                src = node.get('src')
                if src:
                    parsed.append(ImageElement(
                        src,
                        width=node.get('width'),
                        height=node.get('height')
                    ))

            elif tag_name in {'strong', 'b'} and text:
                parsed.append(TextNode(f"{BOLD}{text}{RESET}"))

            elif tag_name in {'em', 'i'} and text:
                parsed.append(TextNode(f"{ITALIC}{text}{RESET}"))

            elif tag_name in {'u', 'ins'} and text:
                parsed.append(TextNode(f"{UNDERLINE}{text}{RESET}"))

            elif tag_name == 'del' and text:
                parsed.append(TextNode(f"{STRIKETHROUGH}{text}{RESET}"))

            elif tag_name == 'mark' and text:
                parsed.append(TextNode(f"{YELLOW_BG}{text}{RESET}"))

            elif tag_name == 'sub' and text:
                parsed.append(TextNode(self._convert_to_unicode_sub_sup(text, True)))

            elif tag_name == 'sup' and text:
                parsed.append(TextNode(self._convert_to_unicode_sub_sup(text, False)))

            elif tag_name == 'span':
                parsed.extend(self._parse_inline_content(node, current_anchors, next_anchor_id))

            elif tag_name == 'widget':
                widget_type = node.get('type')
                if widget_type and self.dashboard_generator:
                    parsed.append(WidgetElement(widget_type, self.dashboard_generator))
                elif text:
                    parsed.append(TextNode(text))

            elif text:
                parsed.append(TextNode(text))

        return parsed