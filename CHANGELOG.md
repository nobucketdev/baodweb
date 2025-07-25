# Changelog

All notable changes to **BaodWeb** will be documented in this file.

---

## 1.0.0 — Initial Release

**Release Date:** July 25, 2025

### ✦ Core Features

- Implemented full HTML parser using `BeautifulSoup`
- Terminal-based rendering of:
  - Headings: `<h1>`, `<h2>`, `<h3>`
  - Paragraphs: `<p>`, inline tags (`<b>`, `<i>`, `<u>`, `<mark>`, `<del>`, etc.)
  - Lists: `<ul>`, `<ol>`, `<li>`
  - Tables: supports headers, multiline rows, wrapping, and Unicode borders
  - Links: interactive navigation with `click <id>` support
  - Images: rendered in terminal using `Pillow` and ANSI blocks
  - Navigation bars: styled `<nav>` rendering
  - Buttons, divs, sections, articles, and other semantic elements

### ✦ Interactivity

- `click <id>` to follow links
- `go <url>` to fetch pages
- `back` command for browser-like navigation
- Configurable display behavior using `config` commands

### ✦ Configuration System

- `config` command to edit runtime rendering settings
- `enable-color`, per-tag render toggles, and language control
- Reads/writes from a local `config` file

### ✦ Testing & Development Tools

- `test <page>` to load static HTML test pages
- `generate <tag>` to create dynamic pages for supported tags
- Language-aware test/start pages (`start-page-en.html`, `test-button-vi.html`, etc.)
- Automatic fallback logic for localized resources

### ✦ Rendering Engine Details

- ANSI color with graceful fallback
- Accurate visual-width calculations using `wcwidth`
- ANSI-safe word wrapping for table cells and paragraphs
- Optional truecolor or 256-color support

### ✦ Architecture & Structure

- Modular class-based design: `Browser`, `Renderer`, `Parser`, `ConfigManager`, `HtmlGenerator`
- PyInstaller-compatible file access (`resource_path`)
- Built-in version handling via `__version__ = "1.0.0"`

---

## Notes

This is the first public, production-ready version. Backward compatibility will be considered from here onward.

For older experimental versions or internal prototypes, see project history or commit logs.
