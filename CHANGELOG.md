# Changelog

All notable changes to **BaodWeb** will be documented in this file.

---

## 1.2.5 — Semantic Navigation Fix & Smart Layout
**Release Date:** August 2, 2025

### 🛠 Fixes
- **Nested Link Parsing in `<nav>`:**  
  Resolved an issue where non-container tags inside `<div>` or `<section>` inside a `<nav>` were ignored. Navigation bar now recursively picks up valid inline elements only.

- **Navigation Layout Overflow:**  
  Navigation bar now **dynamically adjusts width** based on actual content, preventing ugly terminal overflow or full-width stretching.


### ✅ Improvements.
- Navigation rendering accepts inline-style tags only (e.g., `<a>`, `<button>`, `<p>`, `<span>`, etc.)
- Safer, cleaner, semantic nav rendering with fallback for complex structures.

---

## 1.2.4 — URL Resolution Fixes
**Release Date:** August 2, 2025

### 🐛 Bug Fixes
- **Fixed: Relative vs Global URL Confusion**  
  Corrected the logic that was misinterpreting relative URLs as global ones (vice versa), improving navigation and resource handling.

---

## 1.2.3 — Source Polish & Layout Fixes  
**Release Date:** August 2, 2025

### ✨ Improvements  
- **Refined Source View Rendering**  
  Enhanced the `source` command output for better formatting consistency and reduced color bleed on malformed tags.  
  Now handles complex attributes and nested tags.

- **Modular Button Rendering**  
  Buttons now inherit from the `Box` base class, ensuring consistent layout and easier future structuring updates.  
  This change improves modularity across UI components.

- **Relative URL Support**  
  Link like a href="/about" can now be handle correctly.


### 🐞 Bug Fixes  
- **Navigation Duplication**  
  Fixed a bug where `<nav>` tag in header could appear twice in the rendered output.  
  Now renders only once, preserving semantic structure.

- **Complex Tags Rendering Compatibility**  
  Improved partial rendering support for tags with complex or densely packed attributes.  
  These are now displayed more cleanly instead of defaulting to raw HTML dump.

---

## 1.2.2 — View Source 
**Release Date:** August 1, 2025

### ✨ Feature Additions
- **View Raw HTML with Color Highlighting:**  
  Added a new `source` command that displays the original HTML of the current page.  
  Uses syntax-aware formatting:
  - 🟦 **Tag names** in blue  
  - 🟠 **Attributes and values** in orange
  - ⚪ **Text content** in white  
  - ⬜ **Brackets and slashes** in gray  

  This makes it easy to inspect and debug page structure directly from the terminal.

### ⚠️ Issue Raise
- Some complex tag with many attribute can be not rendered as normal, it will show full HTML code.

---

## 1.2.1 — Two Structural Semantic Tags Supported 
**Release Date:** August 1, 2025

### ✨ Feature Additions
- **Header & Footer Support:**  
  Added native handling for `<header>` and `<footer>` tags.

- **Early Access: Search Engine Integration:**  
  Introduced basic search support using a hybrid engine setup.

### ⚠️ Known Issues
- Old bugs still not fixed.

---
## 1.2.0 — Alpha Polish  
**Release Date:** July 31, 2025

### 🧼 Visual & Code Polish  
Refined the layout, cleaned up code.

### ⚠️ Known Issues

- **List-Table Layout Conflict:**  
  Lists (`<ul>`, `<ol>`) inside tables still break alignment. No fix yet — avoid if you value structure.

- **Alt Text Duplication:**  
  Long `alt` texts may still repeat when scrolling.

---


## 1.2.0-alpha — Layout & Render Overhaul  
**Release Date:** July 30, 2025

## ✦ What's New

### 📏 Just-Fit Terminal Rendering  
The browser now intelligently adjusts content rendering to *precisely fit* your terminal's height — no more chopped-off content. It’s all tight, all clean.

### 🧭 Command and Title Bars

- **Bottom Command Bar:**  
  A persistent command input bar now stick at the very bottom of the terminal.

- **Top Title Bar:**  
  A dedicated title bar is now fixed at the top of the screen, showing the current page’s title to make navigation more intuitive.

- **📝 "About" Page:**  
  New `about.html` available! Type `test about` or `click 4` on dashboard to open.

## ⚡ Performance & Stability

- **Optimized Rendering:**  
  Major speed boosts and smoother rendering.

- **Minor Issue Fixes:**  
  Patched various bugs and annoying glitches. Overall UX is now less janky and more joyful.

## ⚠️ Known Issues

- **List-Table Layout Conflict:**  
  List like `<ul>` or `<ol>` inside table cells (`<td>`) may break alignment. Expect a bit of chaos if you do that.

- **Alt Text Duplication on Scroll:**  
  Sometimes, scrolling causes long `alt` texts to show up twice.

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
