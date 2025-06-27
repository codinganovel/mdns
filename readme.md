# mdns

A standalone markdown file explorer and editor that integrates with optional productivity modules — built for fast navigation and seamless note-taking.

## 📄 How it Works

**mdns** (Markdown Notes Studio) is a terminal-based file manager designed specifically for text files and markdown notes. It provides a clean interface for browsing directories, previewing files, and editing with a built-in markdown editor. The real power comes from its module launcher system that lets you quickly switch between different productivity tools.

---

## 📦 Installation

Run the install script or move the Python file manually:

```bash
chmod +x mdns.py
sudo mv mdns.py /usr/local/bin/mdns
```

Optional dependencies for enhanced features:
```bash
pip install pyperclip fuzzywuzzy
```

---

## 🚀 Usage

Launch the file explorer:
```bash
mdns
```

Or run a specific module directly:
```bash
mdns stampt    # Launch stampt module
mdns blipt     # Launch blipt module
mdns ql        # Launch ql module
```

---

## ⌨️ Keyboard Shortcuts

### Navigation
| Key           | Action                        |
|---------------|-------------------------------|
| `↑ ↓` / `j k` | Navigate files                |
| `Enter`       | Open file/directory           |
| `p`           | Preview file (read-only)      |
| `Escape`      | Clear search / Go to parent   |
| `Backspace`   | Always go to parent           |
| `/`           | Search files                  |

### File Operations
| Key      | Action                        |
|----------|-------------------------------|
| `n`      | New timestamped note          |
| `N`      | New untitled note             |
| `d`      | Delete file (with confirmation)|
| `r`      | Refresh file list             |
| `.`      | Toggle hidden files           |

### Editor Commands
| Key      | Action                        |
|----------|-------------------------------|
| `Ctrl+S` | Save file                     |
| `Ctrl+X` | Exit editor (with save check) |
| `Ctrl+C` | Copy all/selected text        |
| `Escape` | Exit editor (with save check) |

### Module Launcher
| Key      | Action                        |
|----------|-------------------------------|
| `m`      | Show modules menu             |
| `Ctrl+S` | Launch stampt (timestamped notes) |
| `Ctrl+B` | Launch blipt (scratchpad)     |
| `Ctrl+T` | Launch smallt (task manager)  |
| `Ctrl+O` | Launch templet (template manager) |
| `Ctrl+G` | Launch gitnot (version control) |
| `Ctrl+L` | Launch ql (quick command launcher) |

### General
| Key      | Action                        |
|----------|-------------------------------|
| `?`      | Show help screen              |
| `q`      | Quit application              |

---

## 🔧 Module Integration

**mdns** works as both a standalone tool and a launcher for productivity modules. Install any of these modules in the same directory as mdns:

- **stampt** - Timestamped notes with dashboard
- **blipt** - Quick scratchpad with numbered entries
- **smallt** - Simple task manager
- **templet** - Lightweight template manager
- **gitnot** - Lightweight version control
- **ql** - Quick command launcher

Modules are detected automatically and can be launched with keyboard shortcuts or through the modules menu (`m`).

---

## 💡 Features

- **Smart File Detection** - Automatically recognizes text files and markdown
- **Live Search** - Filter files by name and content with fuzzy matching
- **Preview Cache** - Fast file previews with intelligent caching
- **Save Protection** - Three-option dialog prevents accidental data loss
- **Vim-style Navigation** - `j/k` keys for familiar movement
- **Clipboard Integration** - Copy text with pyperclip support

---

## ✍️ Made with 💙 by Sam

MIT License