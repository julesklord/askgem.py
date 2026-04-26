"""
Styling Architecture for mentask

This document explains how professional agents handle output styling
and how mentask implements a professional CSS-inspired theme system.
"""

# COMPARISON: How Professional Agents Handle Styling

## 1. GitHub Copilot (VS Code Extension)

- **Format**: VSCode Rich UI components (not CLI)
- **Styling**: HTML/CSS within webview
- **Colors**: Theme from VS Code settings (integrated)
- **Data**: Structured as rich text with markdown support
- **Speed**: Real-time updates with visual smoothing
- **Responsiveness**: Immediate but throttled (60fps limit)

## 2. Claude/ChatGPT (Web)

- **Format**: HTML5 + React
- **Styling**: CSS modules with Tailwind patterns
- **Colors**: Design system tokens (WCAG AAA compliant)
- **Data**: Markdown with syntax highlighting via highlight.js
- **Speed**: Stream at ~40-80ms per chunk
- **Responsiveness**: Animated with requestAnimationFrame

## 3. Google Gemini CLI (Old)

- **Format**: Terminal with Rich library (like mentask)
- **Styling**: ANSI escape codes + Rich markup
- **Colors**: Limited to 256-color palette
- **Data**: Markdown + code block detection
- **Speed**: Live updates with transient panels
- **Responsiveness**: Immediate but can feel rushed

## 4. mentask (Our Implementation)

- **Format**: Terminal with Rich library
- **Styling**: CSS-inspired theme system (themes.py)
- **Colors**: Full 24-bit color support
- **Data**: Markdown + semantic segmentation
- **Speed**: Configurable stream delay (default 10ms)
- **Responsiveness**: Smooth with proper timing control

---

# mentask Theme System Architecture

## Overview

mentask uses a CSS-inspired approach to styling:

1. **ThemeConfig**: Immutable dataclass defining all colors
2. **Style**: Individual style definition (color, bold, italic, etc.)
3. **Themes Dictionary**: Pre-configured professional color schemes
4. **CliRenderer**: Uses theme to style all output

## Theme Anatomy

```python
ThemeConfig(
    # Brand identity
    brand_primary: str      # Main brand color
    brand_secondary: str    # Accent color
    
    # Semantic colors
    success: str            # Success messages
    warning: str            # Warnings and tools
    error: str              # Errors
    info: str               # Information
    
    # Text colors
    text_primary: str       # Main text
    text_secondary: str     # Secondary text (user input)
    text_dim: str          # Dim/muted text
    
    # UI Elements
    border: str            # Border color
    background: str        # Background (for reference)
    
    # Specialized
    think_color: str       # Thinking blocks
    code_theme: str        # Syntax highlighting (monokai, etc.)
)
```

## Color Palettes

### Indigo (Default)

- Professional, calm, corporate
- Primary: #818cf8 (blue-indigo)
- Thinking: #64748b (slate)

### Emerald

- Natural, growth, renewable
- Primary: #34d399 (emerald)
- Thinking: #4b5563 (dark slate)

### Cyberpunk

- Bold, energetic, high-tech
- Primary: #f0abfc (pink)
- Thinking: #4c1d95 (deep purple)

## How to Add a New Theme

```python
THEMES = {
    "my_theme": ThemeConfig(
        brand_primary="#YOUR_COLOR",
        brand_secondary="#YOUR_COLOR",
        success="#10b981",
        warning="#f59e0b",
        error="#ef4444",
        info="#0ea5e9",
        text_primary="#f1f5f9",
        text_secondary="#94a3b8",
        text_dim="#475569",
        border="#334155",
        background="#0f172a",
        think_color="#64748b",
        code_theme="monokai",
    )
}
```

---

# Stream Speed Control

## Problem: Output Appears Rushed

- Classic generators stream at max speed (no throttling)
- Users can't parse information fast enough
- Creates jarring, overwhelming experience

## Solution: Configurable Stream Delay

```python
# Create renderer with 10ms delay (default)
renderer = CliRenderer(console, stream_delay=0.01)

# Or customize:
# 0.005 = 5ms (very fast)
# 0.01  = 10ms (default, smooth)
# 0.02  = 20ms (leisurely)
# 0.05  = 50ms (very slow)
```

## How It Works

```python
def update_stream(self, accumulated: str) -> None:
    # Record time of last update
    elapsed = time.time() - self._last_stream_time
    
    # If less time has passed than desired delay,
    # sleep the difference
    if elapsed < self._stream_delay:
        time.sleep(self._stream_delay - elapsed)
    
    # Update UI with consistent timing
    self._last_stream_time = time.time()
    self._live.update(preview)
```

## Recommended Values by Use Case

| Use Case | Delay | Notes |
|----------|-------|-------|
| Fast copy-paste | 0.005 | Minimal throttling |
| Normal reading | 0.01 | DEFAULT (smooth, natural) |
| Learning/study | 0.02 | Time to absorb |
| Demo/presentation | 0.03-0.05 | Dramatic effect |

---

# Type Hints Implementation

## Before

```python
def print_tool_call(self, tool_name: str, args: dict) -> None:
    # args could be anything - no IDE support
```

## After

```python
def print_tool_call(self, tool_name: str, args: dict[str, str]) -> None:
    # args is clearly dict[str, str] - full IDE completion
```

## Benefits

1. **LSP Support**: VS Code shows proper completions
2. **Error Detection**: Type checker catches bugs early
3. **Documentation**: Self-documenting code
4. **IDE Navigation**: Jump to definition works perfectly
5. **Refactoring**: Safe renames across codebase

---

# Configuration in settings.json

Users can customize appearance:

```json
{
    "theme": "cyberpunk",           // Theme name
    "stream_mode": "continuous",    // Historial o transient
    "stream_delay": 0.01            // Milliseconds between updates (NEW)
}
```

---

# Architecture Comparison

| Aspect | Before | After |
|--------|--------|-------|
| Color System | Hardcoded dicts | ThemeConfig dataclass |
| Type Hints | Minimal | Full coverage |
| Stream Control | Fixed speed | Configurable |
| Code Theme | Hardcoded monokai | From theme config |
| Error Handling | Basic try/except | Proper types catch early |
| IDE Support | Poor | Excellent (LSP) |
| Extensibility | Hard to add themes | Easy (dataclass) |

---

# Migration Path

1. ✅ Created `themes.py` with ThemeConfig
2. ✅ Updated CliRenderer to use ThemeConfig
3. ✅ Added stream_delay support
4. ✅ Improved type hints throughout
5. ⏭️ Update config_manager to include stream_delay
6. ⏭️ Add theme switching via `/theme` command
7. ⏭️ Document all themes in help system

---

# Professional Comparison: Why This Matters

GitHub Copilot doesn't need to think about "impresora" output because:

- It's embedded in VS Code (no terminal constraints)
- It uses VSCode's theming system
- Updates happen in a React component (auto-smoothed)
- Everything is pixel-perfect

mentask brings professional features to terminal:

- CSS-inspired system (familiar to web devs)
- Configurable speed (respects user reading pace)
- Full type safety (LSP support)
- Easy to extend (new themes, new styles)

The key insight: **Professional appearance comes from consistency,
proper typography/colors, and pacing** — not just fancy features.
