import os
import re
import sys
import configparser
from core.parser import SUPPORTED_TAGS


def resource_path(relative_path):
    """
    Determines the correct path for resources, whether running as a script or a PyInstaller executable.
    """
    if getattr(sys, 'frozen', False):  # Running in PyInstaller .exe
        base_path = sys._MEIPASS
    else:  # Running in .py script
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

# --- ConfigManager ---
class ConfigManager:
    # Change the config file name to use .ini extension
    CONFIG_FILE_NAME = "config.ini"
    # Define the default section name for the .ini file
    CONFIG_SECTION = "SETTINGS"

    # Define default configuration values
    DEFAULT_CONFIG = {
        "enable-color": "1",
        "language": "EN",
        "first_run": "1",
        "weather_api_key": "",
        "weather_location": "New York",
    }
    # Add default render settings for all supported tags
    for tag in SUPPORTED_TAGS:
        DEFAULT_CONFIG[f"render-{tag}"] = "1" # Default to rendering all tags

    def __init__(self):
        self.config_path = resource_path(self.CONFIG_FILE_NAME)
        # Initialize configparser instance
        self.parser = configparser.ConfigParser()
        self._load_config()

    def _load_config(self):
        """Loads configuration from the .ini file, creating it if it doesn't exist."""
        # Check if the config file exists
        if not os.path.exists(self.config_path):
            self._create_default_config()
        
        try:
            # Read the config file
            self.parser.read(self.config_path, encoding="utf-8")

            # Ensure the default section exists, if not, create it
            if self.CONFIG_SECTION not in self.parser:
                self.parser.add_section(self.CONFIG_SECTION)
                print(f"Warning: Section '{self.CONFIG_SECTION}' not found in config file. Creating it.", file=sys.stderr)

            # Populate self.config dictionary from the parser, ensuring all defaults are present
            self.config = {}
            for key, default_value in self.DEFAULT_CONFIG.items():
                # Use .get() with a fallback to the default value if the key is not found
                self.config[key] = self.parser.get(self.CONFIG_SECTION, key, fallback=default_value)
                # If a key was missing in the file, it's now added to the parser's internal structure
                # This ensures it gets written back when _save_config is called
                if not self.parser.has_option(self.CONFIG_SECTION, key):
                    self.parser.set(self.CONFIG_SECTION, key, default_value)

        except Exception as e:
            print(f"Error loading config file: {e}. Using default configuration.", file=sys.stderr)
            # Fallback to default if loading fails entirely
            self.config = self.DEFAULT_CONFIG.copy()
            # Re-initialize parser with defaults to ensure it's in a consistent state
            self.parser = configparser.ConfigParser()
            self.parser[self.CONFIG_SECTION] = self.DEFAULT_CONFIG.copy()
            self._save_config() # Attempt to save the default config

    def _create_default_config(self):
        """Creates the default .ini config file."""
        print(f"Creating default config file at: {self.config_path}")
        try:
            # Clear existing sections and add the default one
            self.parser = configparser.ConfigParser()
            self.parser[self.CONFIG_SECTION] = {}

            # Add comments and default values to the parser
            # configparser doesn't directly support comments per key, so general comments go at the top
            self.parser.set(self.CONFIG_SECTION, '; TUI Web Browser Configuration')
            self.parser.set(self.CONFIG_SECTION, '; Set options to 1 to enable, 0 to disable')
            self.parser.set(self.CONFIG_SECTION, '; Set language (e.g., EN, FR, ES) to control localized page loading')
            self.parser.set(self.CONFIG_SECTION, '; first_run: 1 if it\'s the first time the browser is launched, 0 otherwise.')
            self.parser.set(self.CONFIG_SECTION, '; weather_api_key: Your API key for WeatherAPI.com (get from weatherapi.com)')
            self.parser.set(self.CONFIG_SECTION, '; weather_location: Default location for weather data (e.g., \'London\', \'New York\', \'Can Tho\')')

            for key, value in self.DEFAULT_CONFIG.items():
                self.parser.set(self.CONFIG_SECTION, key, value)
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                self.parser.write(f)
            
            self.config = self.DEFAULT_CONFIG.copy() # Update internal config dict
        except Exception as e:
            print(f"Error creating default config file: {e}", file=sys.stderr)
            self.config = self.DEFAULT_CONFIG.copy() # Ensure config is initialized even if write fails

    def _save_config(self):
        """Saves the current configuration to the .ini config file."""
        try:
            # Ensure the section exists before writing
            if self.CONFIG_SECTION not in self.parser:
                self.parser.add_section(self.CONFIG_SECTION)

            # Update the parser's internal state with the current self.config values
            for key, value in self.config.items():
                self.parser.set(self.CONFIG_SECTION, key, value)

            with open(self.config_path, "w", encoding="utf-8") as f:
                # Add general comments at the top of the file before writing the sections
                f.write("# TUI Web Browser Configuration\n")
                f.write("# Set options to 1 to enable, 0 to disable\n")
                f.write("# Set language (e.g., EN, FR, ES) to control localized page loading\n\n")
                f.write("# first_run: 1 if it's the first time the browser is launched, 0 otherwise.\n")
                f.write("# weather_api_key: Your API key for WeatherAPI.com (get from weatherapi.com)\n")
                f.write("# weather_location: Default location for weather data (e.g., 'London', 'New York', 'Can Tho')\n\n")
                self.parser.write(f)
            print(f"Configuration saved to {self.config_path}")
        except Exception as e:
            print(f"Error saving config file: {e}", file=sys.stderr)

    def set(self, key, value):
        """Sets a configuration value and saves it. Includes validation."""
        if key not in self.DEFAULT_CONFIG:
            print(f"Error: Unknown configuration option '{key}'.", file=sys.stderr)
            return False

        # Type validation for specific keys
        if key in ["enable-color", "first_run"] and value not in ["0", "1"]:
            print(f"Error: '{key}' must be 0 or 1. Received '{value}'.", file=sys.stderr)
            return False
        
        if key == "language":
            if not re.fullmatch(r"^[a-zA-Z]{2}$", value):
                print(f"Warning: Language code '{value}' might be invalid. Use standard 2-letter codes (e.g., EN, VI).", file=sys.stderr)
            value = value.upper() # Store language codes as uppercase

        if key.startswith("render-") and value not in ["0", "1"]:
            print(f"Error: Render setting for '{key}' must be 0 or 1. Received '{value}'.", file=sys.stderr)
            return False

        # Update and save
        old_value = self.config.get(key)
        self.config[key] = value
        # Also update the parser's internal state
        if self.CONFIG_SECTION not in self.parser:
            self.parser.add_section(self.CONFIG_SECTION)
        self.parser.set(self.CONFIG_SECTION, key, value)
        self._save_config()
        print(f"Configuration updated: '{key}' changed from '{old_value}' to '{value}'.")
        return True

    def get(self, key, default=None):
        """Gets a configuration value."""
        # First, try to get from the internal config dictionary
        # If not found there, fall back to the parser (which has defaults)
        # If still not found, use the provided default argument
        return self.config.get(key, self.parser.get(self.CONFIG_SECTION, key, fallback=default))

    def is_color_enabled(self):
        """Checks if color output is enabled."""
        return self.get("enable-color", "1") == "1"

    def should_render_tag(self, tag_name):
        """Checks if a specific HTML tag should be rendered."""
        if tag_name == 'text':
            return True
        return self.get(f"render-{tag_name}", "1") == "1"

    def is_first_run(self):
        """Checks if this is the first time the browser is run."""
        return self.get("first_run", "1") == "1"

    def mark_as_not_first_run(self):
        """Marks the browser as having been run before."""
        if self.get("first_run") == "1":
            self.set("first_run", "0")
            print("Marked as not first run.")

# Example Usage (for testing)
if __name__ == "__main__":
    # Ensure a dummy core.parser exists for testing purposes if it's not a real module
    if 'core.parser' not in sys.modules:
        class MockParser:
            SUPPORTED_TAGS = ["p", "a", "h1", "img"]
        sys.modules['core'] = type('module', (object,), {'parser': MockParser()})

    config_manager = ConfigManager()

    print("\n--- Initial Config ---")
    print(f"Color enabled: {config_manager.is_color_enabled()}")
    print(f"Language: {config_manager.get('language')}")
    print(f"First run: {config_manager.is_first_run()}")
    print(f"Weather API Key: {config_manager.get('weather_api_key')}")
    print(f"Render 'p' tag: {config_manager.should_render_tag('p')}")
    print(f"Render 'div' tag: {config_manager.should_render_tag('div')}") # Should be '1' by default

    print("\n--- Setting Values ---")
    config_manager.set("enable-color", "0")
    config_manager.set("language", "VI")
    config_manager.set("weather_api_key", "YOUR_API_KEY_123")
    config_manager.set("render-img", "0")
    config_manager.set("first_run", "0") # Mark as not first run

    print("\n--- Config After Changes ---")
    print(f"Color enabled: {config_manager.is_color_enabled()}")
    print(f"Language: {config_manager.get('language')}")
    print(f"First run: {config_manager.is_first_run()}")
    print(f"Weather API Key: {config_manager.get('weather_api_key')}")
    print(f"Render 'p' tag: {config_manager.should_render_tag('p')}")
    print(f"Render 'img' tag: {config_manager.should_render_tag('img')}")

    print("\n--- Invalid Set Attempts ---")
    config_manager.set("enable-color", "2") # Invalid value
    config_manager.set("non-existent-key", "value") # Unknown key
    config_manager.set("language", "abc") # Invalid language code

    # Test marking as not first run again (should do nothing)
    config_manager.mark_as_not_first_run()

    # Clean up the created config file for repeated testing
    # if os.path.exists(config_manager.config_path):
    #     os.remove(config_manager.config_path)
    #     print(f"\nCleaned up {config_manager.config_path}")
