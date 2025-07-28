# Changelog

All notable changes to **BaodWeb** will be documented in this file.

---

## 1.1.2 — Style Polish & Render Boost  
**Release Date:** July 28, 2025  

### ✦ What's Improved

* **⠿ Braille-Style Headings:** Headings are now styled using simplified Braille characters.

* **🎨 Terminal UI Polish:** Refined visual styling for core elements, making the terminal output cleaner and easier to read.

* **⚡ Faster, better Image Rendering:** Minor performance boost in image rendering. Using Lanczos resampling algorithm for better image quality, less pixelated.

* **📄 Another Code Structuring Chage:** All code except `main.py` are moved to `core/` for better control.

---


## 1.1.1 — Bug Cleanup & Render Refactor  
**Release Date:** July 27, 2025  

### ✦ What's Fixed

* **🐛 Double Title Bug:** Fixed an issue where `title` elements were rendered **twice** due to overlapping logic in the main render flow and separate title rendering. Titles now appear once, clean and correct.

* **🪝 Anchor-In-Container Fix:** Anchors inside wrapped containers (like `<table>`) no longer cause layout glitches. They now behave more predictably in block and inline contexts.

### 🛠 Refactoring & Structure

* **🧩 Code Modularization:**  
  * Moved ANSI formatting to `ansi.py`  
  * Moved image rendering logic to `utils/image_render.py`  
  This makes future maintenance easier and separates concerns cleanly.

* **📄 Project Structure Enhancements:**  
  * Added missing project docs: `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, and `CODE_OF_CONDUCT.md` — making this project ready for contributors and safer for public use.

---

## 1.1.0 — Dynamic Dashboard & Clickable Magic
**Release Date:** July 26, 2025

### ✦ What's New

* **✨ Interactive Links with `click` Command:** You can now navigate directly within the terminal using **`click <id>`**. Anchor element will show its id in [] bracket. This significantly improves the user experience, making sections and widgets feel more interactive and alive.

* **Live Weather ~~and News~~ Integration:** Your homepage and dashboard now pull **real-time weather ~~and news data~~** directly from external APIs, keeping you informed right from your terminal.

* **UI Enhancements:**
    * **Improved Section Titles:** We've reworked section titles using box-drawing Unicode characters to create a stronger visual hierarchy.
    * **Layout Refinements:** You'll notice minor layout adjustments and a more polished loading experience.

### ⚠️ Known Issues

* **Anchor Element Layout in Wrapped Containers:** When using `anchor` elements inside wrapped containers (like `<table>`), you might encounter layout or styling issues due to overflow or inline-block behaviors. We recommend testing them outside of strict block structures.

* **Duplicate Title Rendering on Terminal Render:** When rendering elements with `title` headers, the title is displayed twice due to overlapping logic between the main render function and seperate title rendering logic.

* **News API isn’t working properly:** The dashboard is currently using a temporary (pseudo) text while I sort out an issue with the real one.

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
