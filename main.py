from __version__ import __version__
import re
import sys
import requests
import os # Import the os module for path manipulation
import random # Import random for HTML generation
from datetime import datetime # Added for local time
from core.parser import Parser, SUPPORTED_TAGS # Import the Parser class from core.parser
from core.configman import ConfigManager # Import the ConfigManager class to manage configuration settings

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


# --- Renderer ---
class Renderer:
    def __init__(self, config_manager):
        self.config_manager = config_manager # Pass config_manager to renderer

    def render(self, elements, title="No Title"):
        enable_color = self.config_manager.is_color_enabled()

        # Unicode rounded box styling for the page title, all cyan, bold, 2px padding
        CYAN_BOLD = "\033[1;36m" if enable_color else ""
        RESET = "\033[0m" if enable_color else ""
        title_text = f"  {title}  "  # 2 spaces padding left and right
        box_width = len(title_text)
        print(f"\n{CYAN_BOLD}╭{'─' * box_width}╮")
        print(f"│{title_text}│")
        print(f"╰{'─' * box_width}╯{RESET}\n")

        # Filter out <title> elements so they are not rendered twice
        other_elements = []
        for element in elements:
            if hasattr(element, 'tag_type') and element.tag_type == 'title':
                continue  # Skip rendering <title>
            other_elements.append(element)

        # Then render the rest of the elements
        self._render_elements_recursive(other_elements, enable_color)

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

    def refresh(self, elements, title="No Title"):
        self.clear()
        self.render(elements, title)


# --- Dashboard Content Generator (Simulated Plugins) ---
class DashboardContentGenerator:
    def __init__(self, location="Can Tho", weather_api_key=None):
        self.location = location
        self.weather_api_key = weather_api_key
        self.WEATHER_API_BASE_URL = "http://api.weatherapi.com/v1/current.json"

    def get_local_time(self):
        """Returns the current local time."""
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")

    def get_weather_data(self):
        """Fetches or simulates local weather data."""
        if self.weather_api_key and self.location:
            params = {
                "key": self.weather_api_key,
                "q": self.location
            }
            try:
                response = requests.get(self.WEATHER_API_BASE_URL, params=params, timeout=5)
                response.raise_for_status() # Raise an exception for HTTP errors
                data = response.json()
                
                # Extract relevant weather information
                if "current" in data and "location" in data:
                    temp_c = data["current"]["temp_c"]
                    condition_text = data["current"]["condition"]["text"]
                    city = data["location"]["name"]
                    region = data["location"]["region"]
                    return f"{temp_c}°C, {condition_text} in {city}, {region}"
                else:
                    print("WeatherAPI response missing 'current' or 'location' data.", file=sys.stderr)
                    return self._get_simulated_weather_data() # Fallback
            except requests.exceptions.RequestException as e:
                print(f"Error fetching weather from WeatherAPI.com: {e}", file=sys.stderr)
                return self._get_simulated_weather_data() # Fallback to simulated
            except Exception as e:
                print(f"Unexpected error parsing weather data: {e}", file=sys.stderr)
                return self._get_simulated_weather_data() # Fallback to simulated
        else:
            return self._get_simulated_weather_data() # No API key or location, use simulated

    def _get_simulated_weather_data(self):
        """Simulates fetching local weather data."""
        temperatures = [25, 26, 27, 28, 29, 30, 31, 32] # Celsius
        conditions = ["Sunny", "Partly Cloudy", "Light Rain", "Cloudy"]
        
        temp = random.choice(temperatures)
        condition = random.choice(conditions)
        
        return f"{temp}°C, {condition} (Simulated)"

    def get_news_headlines(self):
        """Simulates fetching news headlines."""
        headlines = [
            "Local Economy Shows Growth in Q3.",
            "Community Event Draws Large Crowds.",
            "New Public Park Opens Downtown.",
            "Tech Startup Announces Expansion Plans.",
            "Sports Team Wins Regional Championship."
        ]
        return random.sample(headlines, min(len(headlines), 3)) # Get up to 3 random headlines

    def generate_dashboard_html(self):
        """Generates HTML content for the dashboard."""
        # This method is now effectively deprecated if start-page.html is used for dashboard.
        # However, it's kept for backward compatibility or if dynamic generation is still needed elsewhere.
        local_time = self.get_local_time()
        weather = self.get_weather_data()
        news_items = self.get_news_headlines()

        news_list_html = ""
        if news_items:
            news_list_html = "<ul>" + "".join([f"<li>{item}</li>" for item in news_items]) + "</ul>"
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
    def __init__(self, debug=False): # Added debug parameter
        self.history = []
        self.current_url = None
        self.current_title = "Loading..."
        self.config_manager = ConfigManager() # Initialize ConfigManager
        
        # Get API key and location from config
        weather_api_key = self.config_manager.get("weather_api_key", "")
        weather_location = self.config_manager.get("weather_location", "Can Tho")

        self.dashboard_generator = DashboardContentGenerator(
            location=weather_location,
            weather_api_key=weather_api_key
        ) # Initialize dashboard generator with API key and location
        self.parser = Parser(dashboard_generator=self.dashboard_generator) # Pass dashboard_generator to parser
        self.renderer = Renderer(self.config_manager) # Pass ConfigManager to Renderer
        self.last_html = ""
        self._current_anchors = {} #
        self._next_anchor_id = [1] # # Use a list to make it mutable for passing by reference
        self.debug = debug # Store debug mode setting

    def navigate(self, url):
        self.current_url = url
        self.history.append(url)
        self.load_content(url)

    def load_content(self, url, is_internal_html=False): # Renamed is_config_page to is_internal_html for broader use
        html_content = ""
        current_lang = self.config_manager.get("language", "EN").lower() # Get current language, default to EN, convert to lowercase for filenames

        self._current_anchors = {} # Clear anchors for new page
        self._next_anchor_id = [1] # Reset anchor ID counter

        try:
            if url == "home" or url == "dashboard": # "home" and "dashboard" now point to start-page.html
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
            elif is_internal_html: # For internally generated HTML (like config page)
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
            elif self.current_url == "dashboard" or self.current_url == "home": # Handle going back to dashboard/home
                self.load_content("home") # Load the home/dashboard page
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
        enable_color_status = "Enabled" if self.config_manager.is_color_enabled() else "Disabled"
        current_language_setting = self.config_manager.get("language", "EN").upper() # Get and display language
        first_run_status = "Yes" if self.config_manager.is_first_run() else "No" # Display first run status
        weather_api_key_status = self.config_manager.get("weather_api_key", "Not Set (Simulated)")
        weather_location_status = self.config_manager.get("weather_location", "Can Tho")

        render_settings_rows = []
        # Sort tags for consistent display
        sorted_supported_tags = sorted(list(SUPPORTED_TAGS))
        for tag in sorted_supported_tags:
            status = self.config_manager.get(f"render-{tag}", "1")
            render_settings_rows.append(f"<tr><td>&lt;{tag}&gt;</td><td>{status}</td></tr>")

        # Pass current_language_setting and first_run_status to format
        final_html = config_html_content.format(
            enable_color_status,
            current_language_setting,
            first_run_status,
            weather_api_key_status, # New: Weather API Key status
            weather_location_status, # New: Weather Location status
            "\n".join(render_settings_rows)
        ) #

        # Use a special "URL" to indicate this is an internally generated page
        if add_to_history:
            self.current_url = "config-page:current"
            self.history.append(self.current_url)
        
        self.load_content(final_html, is_internal_html=True)


    def handle_input(self, user_input):
        if user_input.startswith("go "):
            url = user_input[3:].strip()
            self.navigate(url)
        elif user_input == "dashboard": # New command for dashboard
            self.navigate("dashboard") # Now loads start-page.html
        elif user_input.startswith("test "):
            test_page = user_input[5:].strip()
            self.navigate(f"test:{test_page}")
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
                    elif self.current_url == "dashboard" or self.current_url == "home": # If on dashboard, refresh it
                        self.load_content("home")
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
        elif user_input == "help": # Added help command
            print("Commands: go <url>, dashboard, test <test-page-name>, back, list-tests, list-languages, config [option] [value], click <id>, quit, help")
        else:
            print("Unknown command. Type 'help' for a list of commands.") # Updated help text

    def start(self):
        print("Welcome to the TUI Web Browser!")
        print("Commands: go <url>, dashboard, test <test-page-name>, back, list-tests, list-languages, config [option] [value], click <id>, quit, help") # Updated help text
        
        if self.config_manager.is_first_run():
            self.navigate("home") # Load the home page for first-time users
            self.config_manager.mark_as_not_first_run()
        else:
            self.navigate("dashboard") # Load the dashboard for returning users
        
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
        browser = Browser(debug=True) # Pass debug=True
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
        browser.load_content(html, is_internal_html=True) # Mark as internal HTML
        browser.start()
        return

    print(f"Unknown argument: {arg}")
    print("Try 'baodweb --help' for a list of options.")


if __name__ == "__main__":
    main()