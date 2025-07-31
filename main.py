import os
import random
import re
import shutil
import sys
from datetime import datetime
import requests
from core.configman import ConfigManager
from core.parser import SUPPORTED_TAGS, Parser

if os.name == "nt":
    import msvcrt
else:
    import termios
    import tty
print("------ BaodWeb Terminal Browser -------")
print(f"BaodWeb Terminal Browser version 1.2.0")


def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)


# --- Renderer with Paging/Scrolling ---
class Renderer:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.lines_buffer = []
        self._previous_frame_buffer = (
            []
        )  # New: Stores the last rendered frame for diffing
        self.current_title = ""  # Added: To store the title

    def render_to_buffer(self, elements, title="No Title"):
        self.current_title = title  # Store the title
        enable_color = self.config_manager.is_color_enabled()

        # The title formatting is moved to render_page or handled there directly
        # based on self.current_title. Here, we only prepare the content buffer.

        lines = [""]  # Start with an empty line to account for the title line
        other_elements = [
            e
            for e in elements
            if not (hasattr(e, "tag_type") and e.tag_type == "title")
        ]
        for element in other_elements:
            if hasattr(
                element, "tag_type"
            ) and not self.config_manager.should_render_tag(element.tag_type):
                continue
            if hasattr(element, "elements"):
                rendered_self = element.render(enable_color)
                if rendered_self:
                    lines.extend(rendered_self.splitlines())
            else:
                lines.extend(element.render(enable_color).splitlines())
        self.lines_buffer = lines

    def clear(self):
        """Clears the entire terminal screen and resets the previous frame buffer."""
        print("\033c", end="")
        self._previous_frame_buffer = (
            []
        )  # Clear the buffer when the screen is fully cleared

    def render_page(self, scroll_offset=0):
        """
        Renders the current page to the terminal, using a diffing approach
        to reduce flickering.
        """
        term_height = shutil.get_terminal_size((80, 24)).lines

        # Calculate usable height considering 1 line for title and 2 for input/prompt
        usable_height = term_height - 3

        total_lines = len(self.lines_buffer)

        # Ensure scroll_offset is within valid bounds
        scroll_offset = max(0, min(scroll_offset, max(0, total_lines - usable_height)))

        visible_lines = self.lines_buffer[scroll_offset : scroll_offset + usable_height]

        # Move cursor to home position
        sys.stdout.write("\033[H")

        # --- Render Title Bar ---
        enable_color = self.config_manager.is_color_enabled()
        CYAN_BOLD = "\033[1;36m" if enable_color else ""
        RESET = "\033[0m" if enable_color else ""
        # MODIFICATION START
        # Set the terminal window title
        terminal_title = f"baodweb - {self.current_title}"
        sys.stdout.write(f"\x1b]0;{terminal_title}\a")
        # MODIFICATION END
        title_text = f"  {self.current_title}  "
        box_width = shutil.get_terminal_size(
            (80, 24)
        ).columns  # Use full terminal width for title bar

        # Truncate title if it's too long
        if len(title_text) > box_width:
            title_text = title_text[: box_width - 3] + "..."

        # Center the title within the available width
        padding_left = (box_width - len(title_text)) // 2
        padding_right = box_width - len(title_text) - padding_left

        sys.stdout.write(
            f"{CYAN_BOLD}{' ' * padding_left}{title_text}{' ' * padding_right}{RESET}\n"
        )
        sys.stdout.write(f"{CYAN_BOLD}{'─' * box_width}{RESET}\n")

        # Move cursor to the start of the content area (after the title bar)
        sys.stdout.write(
            f"\033[4;1H"
        )  # Line 4 (1-indexed) is where content starts after title bar

        # Compare current visible lines with the previous frame buffer
        max_len = max(len(visible_lines), len(self._previous_frame_buffer))
        for i in range(max_len):
            current_line = visible_lines[i] if i < len(visible_lines) else ""
            previous_line = (
                self._previous_frame_buffer[i]
                if i < len(self._previous_frame_buffer)
                else ""
            )

            if current_line != previous_line:
                # Move cursor to the start of the current content line
                # +3 because content starts on line 3 (after 2 title lines)
                sys.stdout.write(f"\033[{i + 3};1H")
                sys.stdout.write(current_line)
                # Clear to end of line if the new line is shorter than the old one
                if len(current_line) < len(previous_line):
                    sys.stdout.write("\033[K")

            # If we're past the end of current_line but there was a previous_line, clear it
            elif i >= len(visible_lines) and i < len(self._previous_frame_buffer):
                sys.stdout.write(f"\033[{i + 4};1H")  # +4 as above
                sys.stdout.write("\033[K")  # Clear the line

        # If the new frame has fewer lines than the previous, clear the extra lines at the bottom
        if len(visible_lines) < len(self._previous_frame_buffer):
            for i in range(len(visible_lines), len(self._previous_frame_buffer)):
                sys.stdout.write(f"\033[{i + 4};1H")  # +4 as above
                sys.stdout.write("\033[K")

        sys.stdout.flush()  # Ensure changes are immediately visible

        # Update the previous frame buffer for the next render
        self._previous_frame_buffer = list(visible_lines)  # Make a copy

        return scroll_offset, usable_height, total_lines

# --- Dashboard Content Generator (Simulated Plugins) ---
class DashboardContentGenerator:
    def __init__(self, location="London", weather_api_key=None):
        self.location = location
        self.weather_api_key = weather_api_key
        self.WEATHER_API_BASE_URL = "http://api.weatherapi.com/v1/current.json"

    def get_local_time(self):
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")

    def get_weather_data(self):
        if self.weather_api_key and self.location:
            params = {"key": self.weather_api_key, "q": self.location}
            try:
                response = requests.get(
                    self.WEATHER_API_BASE_URL, params=params, timeout=5
                )
                response.raise_for_status()
                data = response.json()
                if "current" in data and "location" in data:
                    temp_c = data["current"]["temp_c"]
                    condition_text = data["current"]["condition"]["text"]
                    city = data["location"]["name"]
                    region = data["location"]["region"]
                    return f"{temp_c}°C, {condition_text} in {city}, {region}"
                else:
                    print(
                        "WeatherAPI response missing 'current' or 'location' data.",
                        file=sys.stderr,
                    )
                    return self._get_simulated_weather_data()
            except requests.exceptions.RequestException as e:
                print(
                    f"Error fetching weather from WeatherAPI.com: {e}", file=sys.stderr
                )
                return self._get_simulated_weather_data()
            except Exception as e:
                print(f"Unexpected error parsing weather data: {e}", file=sys.stderr)
                return self._get_simulated_weather_data()
        else:
            return self._get_simulated_weather_data()

    def _get_simulated_weather_data(self):
        temperatures = [25, 26, 27, 28, 29, 30, 31, 32]
        conditions = ["Sunny", "Partly Cloudy", "Light Rain", "Cloudy"]
        temp = random.choice(temperatures)
        condition = random.choice(conditions)
        return f"{temp}°C, {condition} (Simulated)"

    def get_news_headlines(self):
        headlines = [
            "Local Economy Shows Growth in Q3.",
            "Community Event Draws Large Crowds.",
            "New Public Park Opens Downtown.",
            "Tech Startup Announces Expansion Plans.",
            "Sports Team Wins Regional Championship.",
        ]
        return random.sample(headlines, min(len(headlines), 3))

    def generate_dashboard_html(self):
        local_time = self.get_local_time()
        weather = self.get_weather_data()
        news_list_html = ""
        if news_items := self.get_news_headlines():
            news_list_html = (
                "<ul>" + "".join([f"<li>{item}</li>" for item in news_items]) + "</ul>"
            )
        else:
            news_list_html = "<p>No news available.</p>"
        dashboard_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard</title>
</head>
<body>
    <h1>Welcome to Your Dashboard!</h1>
    <p>Here's a quick overview of your local information.</p>
    <h2>Local Information for {self.location}</h2>
    <ul>
        <li><b>Current Time:</b> {local_time}</li>
        <li><b>Weather:</b> {weather}</li>
    </ul>
    <h2>Latest News</h2>
    {news_list_html}
    <p>Type 'go <url>' to browse the web, or 'help' for other commands.</p>
</body>
</html>
        """
        return dashboard_html


# --- Browser ---
class Browser:
    def __init__(self, debug=False):
        self.history = []
        self.current_url = None
        self.current_title = "Loading..."
        self.config_manager = ConfigManager()
        weather_api_key = self.config_manager.get("weather_api_key", "")
        weather_location = self.config_manager.get("weather_location", "Can Tho")
        self.dashboard_generator = DashboardContentGenerator(
            location=weather_location, weather_api_key=weather_api_key
        )
        self.parser = Parser(dashboard_generator=self.dashboard_generator)
        self.renderer = Renderer(self.config_manager)
        self.last_html = ""
        self._current_anchors = {}
        self._next_anchor_id = [1]
        self.debug = debug
        self.scroll_offset = 0

    def navigate(self, url):
        self.current_url = url
        self.history.append(url)
        self.load_content(url)

    def load_content(self, url, is_internal_html=False):
        html_content = ""
        current_lang = self.config_manager.get("language", "EN").lower()
        self._current_anchors = {}
        self._next_anchor_id = [1]
        try:
            if url == "home" or url == "dashboard":
                lang_home_path = resource_path(f"start-page-{current_lang}.html")
                if os.path.exists(lang_home_path):
                    with open(lang_home_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                else:
                    default_home_path = resource_path("start-page.html")
                    if os.path.exists(default_home_path):
                        with open(default_home_path, "r", encoding="utf-8") as f:
                            html_content = f.read()
                    else:
                        raise FileNotFoundError(
                            f"Neither {lang_home_path} nor {default_home_path} found."
                        )
            elif url.startswith("test:"):
                test_page_base_name = url[len("test:") :].strip()
                lang_test_page_filename = f"{test_page_base_name}-{current_lang}.html"
                lang_test_page_path = resource_path(
                    os.path.join("test-pages", lang_test_page_filename)
                )
                if os.path.exists(lang_test_page_path):
                    with open(lang_test_page_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                else:
                    default_test_page_filename = f"{test_page_base_name}.html"
                    default_test_page_path = resource_path(
                        os.path.join("test-pages", default_test_page_filename)
                    )
                    if os.path.exists(default_test_page_path):
                        with open(default_test_page_path, "r", encoding="utf-8") as f:
                            html_content = f.read()
                    else:
                        raise FileNotFoundError(
                            f"Neither {lang_test_page_path} nor {default_test_page_path} found."
                        )
            elif is_internal_html:
                html_content = url
            else:
                if not url.startswith("http://") and not url.startswith("https://"):
                    url = "https://" + url
                print(f"Fetching {url}...")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                html_content = response.text
                print(f"Successfully fetched {url}")
        except FileNotFoundError:
            html_content = f"""
                <title>404 File Not Found</title>
                <h1>Error: File Not Found</h1>
                <p>Could not find the local file: {url}</p>
            """
            print(f"Error: Local file '{url}' not found.", file=sys.stderr)
        except requests.exceptions.RequestException as e:
            try:
                with open(
                    resource_path("error/403.html"), "r", encoding="utf-8"
                ) as file:
                    template = file.read()
                html_content = template.replace("{error}", str(e)).replace("{url}", url)
            except FileNotFoundError:
                html_content = f"<title>Error</title><h1>Error: {e}</h1><p>Failed to load error page template for {url}</p>"
            print(f"Error fetching {url}: {e}", file=sys.stderr)
        except Exception as e:
            try:
                with open(
                    resource_path("error/unexpected.html"), "r", encoding="utf-8"
                ) as file:
                    template = file.read()
                html_content = f"{template}".replace("{error}", str(e))
            except FileNotFoundError:
                html_content = (
                    f"<title>Error</title><h1>An unexpected error occurred: {e}</h1>"
                )
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
        self.last_html = html_content
        elements, page_title = self.parser.parse(
            html_content, self._current_anchors, self._next_anchor_id
        )
        self.current_title = page_title
        self.renderer.render_to_buffer(elements, self.current_title)
        self.scroll_offset = 0
        self.renderer.clear()  # Perform a full clear and redraw when content changes
        self.renderer.render_page(self.scroll_offset)

    def scroll_up(self):
        old_scroll_offset = self.scroll_offset
        self.scroll_offset = max(0, self.scroll_offset - 1)
        if (
            old_scroll_offset != self.scroll_offset
        ):  # Only re-render if scroll position changed
            self.renderer.render_page(self.scroll_offset)

    def scroll_down(self):
        old_scroll_offset = self.scroll_offset
        _, usable_height, total_lines = self.renderer.render_page(
            self.scroll_offset
        )  # Get current state for boundary check
        if self.scroll_offset + usable_height < total_lines:
            self.scroll_offset += 1
            if (
                old_scroll_offset != self.scroll_offset
            ):  # Only re-render if scroll position changed
                self.renderer.render_page(self.scroll_offset)

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            self.current_url = self.history[-1]
            if self.current_url.startswith("config-page:"):
                self._show_config_page(add_to_history=False)
            elif self.current_url == "dashboard" or self.current_url == "home":
                self.load_content("home")
            else:
                self.load_content(self.current_url)
        else:
            print("No history to go back to.")

    def list_test_pages(self):
        test_pages_dir = resource_path("test-pages")
        if not os.path.exists(test_pages_dir):
            print(f"Error: The '{test_pages_dir}' directory does not exist.")
            return
        print(f"\nAvailable test pages in '{test_pages_dir}':")
        found_pages = False
        all_test_files_base_names = set()
        lang_code_pattern = re.compile(
            r"^(.*?)-(en|fr|es|de|cn|jp)\.html$", re.IGNORECASE
        )
        for filename in os.listdir(test_pages_dir):
            if filename.endswith(".html"):
                match = lang_code_pattern.match(filename)
                if match:
                    all_test_files_base_names.add(match.group(1))
                else:
                    all_test_files_base_names.add(filename[:-5])
        if all_test_files_base_names:
            for page_name in sorted(list(all_test_files_base_names)):
                print(f"- {page_name}")
            found_pages = True
        if not found_pages:
            print("No .html test pages found.")
        current_lang_setting = self.config_manager.get("language", "EN").upper()
        print(f"\nCurrently configured language for pages is: {current_lang_setting}")
        print(
            f"When using 'test <page-name>', the browser will try to load '<page-name>-{current_lang_setting.lower()}.html' first."
        )
        print("If not found, it will fall back to '<page-name>.html'.")
        print("\nTo load a test page, use: test <page-name>")

    def list_available_languages(self):
        base_resource_dir = resource_path("")
        if not os.path.exists(base_resource_dir):
            print(
                f"Error: The resource directory '{base_resource_dir}' does not exist."
            )
            return
        print(f"\nAvailable languages for start pages:")
        found_languages = set()
        lang_file_pattern = re.compile(r"start-page-(.*?)\.html$", re.IGNORECASE)
        for filename in os.listdir(base_resource_dir):
            match = lang_file_pattern.match(filename)
            if match:
                found_languages.add(match.group(1).upper())
        if found_languages:
            for lang_code in sorted(list(found_languages)):
                print(f"- {lang_code}")
            print(
                f"\nCurrently configured language is: {self.config_manager.get('language', 'EN').upper()}"
            )
            print(
                "To change language, modify the 'language' setting in the 'config' file."
            )
        else:
            print(
                "No language-specific start pages found (e.g., 'start-page-en.html')."
            )

    def _show_config_page(self, add_to_history=True):
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
        <li><b>First Run:</b> {}</li>
        <li><b>Weather API Key:</b> {}</li>
        <li><b>Weather Location:</b> {}</li>
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
        enable_color_status = (
            "Enabled" if self.config_manager.is_color_enabled() else "Disabled"
        )
        current_language_setting = self.config_manager.get("language", "EN").upper()
        first_run_status = "Yes" if self.config_manager.is_first_run() else "No"
        weather_api_key_status = self.config_manager.get(
            "weather_api_key", "Not Set (Simulated)"
        )
        weather_location_status = self.config_manager.get("weather_location", "Can Tho")
        render_settings_rows = []
        sorted_supported_tags = sorted(list(SUPPORTED_TAGS))
        for tag in sorted_supported_tags:
            status = self.config_manager.get(f"render-{tag}", "1")
            render_settings_rows.append(
                f"<tr><td>&lt;{tag}&gt;</td><td>{status}</td></tr>"
            )
        final_html = config_html_content.format(
            enable_color_status,
            current_language_setting,
            first_run_status,
            weather_api_key_status,
            weather_location_status,
            "\n".join(render_settings_rows),
        )
        if add_to_history:
            self.current_url = "config-page:current"
            self.history.append(self.current_url)
        self.load_content(final_html, is_internal_html=True)

    def handle_input(self, user_input):
        if user_input in ("up", "k"):
            self.scroll_up()
        elif user_input in ("down", "j"):
            self.scroll_down()
        elif user_input.startswith("go "):
            url = user_input[3:].strip()
            self.navigate(url)
        elif user_input == "dashboard":
            self.navigate("dashboard")
        elif user_input.startswith("test "):
            test_page = user_input[5:].strip()
            self.navigate(f"test:{test_page}")
        elif user_input.startswith("click "):
            try:
                anchor_id = int(user_input[len("click ") :].strip())
                if anchor_id in self._current_anchors:
                    anchor = self._current_anchors[anchor_id]
                    print(
                        f"Clicking link [{anchor_id}]: {anchor.text} -> {anchor.href}"
                    )
                    self.navigate(anchor.href)
                else:
                    print(
                        f"Error: No link found with ID {anchor_id}. Please check the displayed link IDs."
                    )
            except ValueError:
                print("Error: Invalid link ID. Please enter a number after 'click'.")
        elif user_input == "back":
            self.go_back()
        elif user_input == "list-tests":
            self.list_test_pages()
        elif user_input == "list-languages":
            self.list_available_languages()
        elif user_input.startswith("config"):
            parts = user_input.split(maxsplit=2)
            if len(parts) == 1:
                self._show_config_page()
            elif len(parts) == 3:
                option = parts[1].strip()
                value = parts[2].strip()
                if self.config_manager.set(option, value):
                    if self.current_url and self.current_url.startswith("config-page:"):
                        self._show_config_page(add_to_history=False)
                    elif self.current_url == "dashboard" or self.current_url == "home":
                        self.load_content("home")
                    elif self.current_url:
                        self.load_content(self.current_url)
                    else:
                        self.load_content("home")
                else:
                    print("Failed to update configuration. Please check your input")
            else:
                print("Usage: config [option] [value]")
                print("  config              - Show current configuration")
                print(
                    "  config <option> <value> - Set a configuration option (e.g., config enable-color 0)"
                )
        elif user_input == "help":
            print(
                "Commands: go <url>, dashboard, test <test-page-name>, back, list-tests, list-languages, config [option] [value], click <id>, up, down, quit, help"
            )
        else:
            print("Unknown command. Type 'help' for a list of commands.")

    def start(self):
        print("Welcome to the TUI Web Browser!")
        print(
            "Commands: go <url>, dashboard, test <test-page-name>, back, list-tests, list-languages, config [option] [value], click <id>, up, down, quit, help"
        )

        # Initial clear and render
        self.renderer.clear()
        if self.config_manager.is_first_run():
            self.navigate("home")
            self.config_manager.mark_as_not_first_run()
        else:
            self.navigate("dashboard")

        buffer = ""
        while True:
            term_size = shutil.get_terminal_size((80, 24))
            term_height = term_size.lines
            term_width = term_size.columns

            # NEW: Separator above the input bar
            sys.stdout.write(f"\033[{term_height - 1};1H")
            sys.stdout.write("─" * term_width)

            # Input prompt at the very bottom
            sys.stdout.write(f"\033[{term_height};1H")
            sys.stdout.write(
                "Search/Command (press up/down arrow to move, quit to exit): "
                + buffer
                + "\033[K"
            )
            sys.stdout.flush()

            key = self._get_key()
            if key in ("\r", "\n"):  # Enter
                sys.stdout.write(f"\033[{term_height};1H\033[K")
                sys.stdout.flush()

                if buffer.strip() == "quit":
                    print("Exiting browser.")
                    break
                self.handle_input(buffer.strip())
                buffer = ""
            elif key in ("\x08", "\x7f"):  # Backspace
                buffer = buffer[:-1]
            elif key == "UP":
                self.scroll_up()
            elif key == "DOWN":
                self.scroll_down()
            elif key.isprintable():
                buffer += key

    def _get_key(self):
        if os.name == "nt":
            while True:
                ch = msvcrt.getwch()
                if ch == "\x00" or ch == "\xe0":
                    ch2 = msvcrt.getwch()
                    if ch2 == "H":
                        return "UP"
                    elif ch2 == "P":
                        return "DOWN"
                    else:
                        continue
                else:
                    return ch
        else:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    ch2 = sys.stdin.read(1)
                    if ch2 == "[":
                        ch3 = sys.stdin.read(1)
                        if ch3 == "A":
                            return "UP"
                        elif ch3 == "B":
                            return "DOWN"
                    return ""
                else:
                    return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


# --- Main ---
def main():
    args = sys.argv[1:]
    if not args:
        browser = Browser()
        browser.start()
        return
    arg = args[0].lower()
    if arg in ("--version", "-v"):
        print(f"baodweb version 1.2.0-beta")
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
        browser.load_content(html, is_internal_html=True)
        browser.start()
        return
    print(f"Unknown argument: {arg}")
    print("Try 'baodweb --help' for a list of options.")


if __name__ == "__main__":
    main()
