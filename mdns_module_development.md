# mdns Module Development

A complete guide to creating and integrating new productivity modules into the mdns ecosystem — build once, launch seamlessly.

## 📄 How it Works

**mdns** uses a simple module system where any executable in the same directory becomes available as a launchable tool. Modules can be standalone Python scripts, compiled binaries, or shell scripts. The integration system provides keyboard shortcuts, menu entries, and seamless launching from within mdns.

---

## 📦 Module Requirements

Your module must meet these basic requirements:

```python
#!/usr/bin/env python3
"""
example - Example module for mdns
A sample tool that does something useful
"""

def main():
    print("Example module is running!")

if __name__ == "__main__":
    main()
```

**Essential criteria:**
- Executable file (with proper shebang)
- Works standalone when run directly
- Operates in the current working directory
- Exits cleanly to return control to mdns

---

## 🚀 Quick Setup

### Step 1: Install Your Module
```bash
# Copy to mdns directory (usually ~/.local/bin/)
cp example.py ~/.local/bin/example
chmod +x ~/.local/bin/example

# Test standalone
example
```

### Step 2: Basic Integration (Works Immediately!)
```bash
# This already works without code changes
mdns example
```

---

## ⌨️ Full Integration Guide

For complete integration with keyboard shortcuts and menu entries, modify these sections:

### 1. Add to Known Modules List
**File:** `mdns.py` **Line:** ~42
```python
KNOWN_MODULES = ["stampt", "blipt", "smallt", "templet", "gitnot", "ql", "example"]
```

### 2. Add Keyboard Shortcuts
**File:** `mdns.py` **Line:** ~520 (MDNSApp BINDINGS)
```python
Binding("ctrl+e", "launch_example", "Example", show=False),
```

**File:** `mdns.py` **Line:** ~380 (ModulesScreen BINDINGS)
```python
Binding("e", "launch_example", "Launch example"),
```

### 3. Add Module Configuration
**File:** `mdns.py` **Line:** ~415 (module_configs in ModulesScreen.on_mount)
```python
("example", "e", "Example module that does something useful"),
```

### 4. Add Launch Actions
**File:** `mdns.py` **Line:** ~480 (ModulesScreen class)
```python
def action_launch_example(self): self._launch_module("example")
```

**File:** `mdns.py` **Line:** ~620 (MDNSApp class)
```python
def action_launch_example(self): self._launch_module("example")
```

### 5. Update Help Text
**File:** `mdns.py` **Line:** ~350 (HelpScreen help_text)
```python
  Ctrl+E        Launch example (your description)
```

### 6. Update CLI Help (Optional)
**File:** `mdns.py` **Line:** ~670 (argparse help)
```python
help="Optional module to run (e.g., stampt, blipt, smallt, templet, gitnot, ql, example)"
```

---

## 🔧 Integration Results

After integration, your module appears everywhere:

### Terminal Launch
```bash
mdns example
```

### Keyboard Shortcuts
| Context      | Key      | Action           |
|--------------|----------|------------------|
| Main Screen  | `Ctrl+E` | Launch example   |
| Modules Menu | `e`      | Launch example   |

### Modules Menu Display
```
Available Modules
Press the key shown to launch a module.

✓ [e] example    - Example module that does something useful
```

---

## 💡 Development Best Practices

### Error Handling
```python
def main():
    try:
        # Your module logic
        pass
    except KeyboardInterrupt:
        print("\nCancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

### Help Support
```python
if "--help" in sys.argv or "-h" in sys.argv:
    print("example - Does something useful")
    print("Usage: example [options]")
    sys.exit(0)
```

### Directory Awareness
```python
# Always work in current directory
current_dir = Path.cwd()
print(f"Operating in: {current_dir}")
```

---

## ✅ Integration Checklist

Complete these steps for full integration:

- [ ] Create executable module with proper shebang
- [ ] Install in mdns directory (`~/.local/bin/`)
- [ ] Test standalone functionality
- [ ] Add to `KNOWN_MODULES` list
- [ ] Add main screen keyboard binding (`Ctrl+?`)
- [ ] Add modules menu keyboard binding (`?`)
- [ ] Add module configuration with description
- [ ] Add launch action methods (both classes)
- [ ] Update help text with new shortcut
- [ ] Test all launch methods: `mdns example`, `Ctrl+?`, menu

---

## 🔮 Future Enhancements

### Auto-Discovery System
```python
# Potential future feature - automatic module detection
def discover_modules():
    """Find all mdns-* executables in same directory"""
    mdns_dir = Path(sys.argv[0]).resolve().parent
    modules = []
    for file in mdns_dir.glob("mdns-*"):
        if file.is_file() and os.access(file, os.X_OK):
            modules.append(file.stem.replace("mdns-", ""))
    return modules
```

This would eliminate manual code changes for each new module!

---

## ✍️ Made with 💙 by Sam

MIT License