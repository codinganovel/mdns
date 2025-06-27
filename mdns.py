#!/usr/bin/env python3
"""
mdns - Markdown Notes Studio
A standalone markdown file explorer and editor that integrates with optional modules
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
import argparse

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.screen import Screen
from textual.widgets import (
    Header, Footer, Static, Input, TextArea, Label, 
    ListView, ListItem, Button
)
from textual.message import Message

# Try to import optional dependencies
try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

try:
    from rapidfuzz import fuzz
    HAS_FUZZY = True
except ImportError:
    HAS_FUZZY = False

# Constants
KNOWN_MODULES = ["stampt", "blipt", "smallt", "templet", "gitnot", "ql"]
TEXT_EXTENSIONS = {'.md', '.txt', '.text', '.markdown', '.rst', '.org', '.todo'}
PREVIEW_CACHE_SIZE = 100  # Max number of previews to cache


# ============================================================================
# Module Integration
# ============================================================================

class ModuleManager:
    """Manages integration with standalone modules"""
    
    @staticmethod
    def get_module_path(module_name: str) -> Optional[Path]:
        """Find module in same directory as mdns"""
        mdns_dir = Path(sys.argv[0]).resolve().parent
        
        # Check for executable without extension first
        module_path = mdns_dir / module_name
        if module_path.exists() and module_path.is_file():
            return module_path
            
        # Fallback to .py extension
        module_path = mdns_dir / f"{module_name}.py"
        if module_path.exists():
            return module_path
            
        return None
    
    @staticmethod
    def check_module(module_name: str) -> Tuple[bool, str]:
        """Check if module is available"""
        module_path = ModuleManager.get_module_path(module_name)
        
        if module_path:
            return True, f"Found: {module_path.name}"
        else:
            mdns_dir = Path(sys.argv[0]).resolve().parent
            return False, (
                f"Module '{module_name}' not found!\n\n"
                f"To install, place {module_name} in:\n"
                f"{mdns_dir}/\n\n"
                f"Make sure it's executable:\n"
                f"chmod +x {mdns_dir}/{module_name}"
            )
    
    @staticmethod
    def run_module(module_name: str) -> None:
        """Run a standalone module"""
        module_path = ModuleManager.get_module_path(module_name)
        
        if not module_path:
            exists, message = ModuleManager.check_module(module_name)
            print(message)
            sys.exit(1)
        
        try:
            if os.access(module_path, os.X_OK):
                subprocess.run([str(module_path)], check=True)
            else:
                subprocess.run([sys.executable, str(module_path)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running {module_name}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Failed to run {module_name}: {e}")
            sys.exit(1)


# ============================================================================
# File Management
# ============================================================================

class FileItem(ListItem):
    """Custom ListItem that stores file path and metadata"""
    def __init__(self, path: Path, preview: str, is_dir: bool = False):
        icon = "📁" if is_dir else "📄"
        # Format with better alignment
        name = path.name[:40] + "..." if len(path.name) > 40 else path.name
        label_text = f"{icon} {name:<45} {preview}"
        super().__init__(Label(label_text))
        self.path = path
        self.preview = preview
        self.is_dir = is_dir


class FileExplorer(ListView):
    """File explorer with preview support"""
    
    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.show_hidden = False
        self.current_filter = ""
        self._preview_cache: Dict[Tuple[Path, float], str] = {}
        
    def get_preview(self, file_path: Path, max_length: int = 40) -> str:
        """Get a preview of file content with caching"""
        if file_path.is_dir():
            try:
                count = len(list(file_path.iterdir()))
                return f"<{count} items>"
            except:
                return "<folder>"
        
        # Check cache first
        try:
            mtime = file_path.stat().st_mtime
        except:
            mtime = 0
            
        cache_key = (file_path, mtime)
        if cache_key in self._preview_cache:
            return self._preview_cache[cache_key]
        
        # Limit cache size
        if len(self._preview_cache) > PREVIEW_CACHE_SIZE:
            # Remove oldest entries
            self._preview_cache = dict(
                list(self._preview_cache.items())[-PREVIEW_CACHE_SIZE//2:]
            )
            
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(200).strip()
                if not content:
                    preview = "<empty>"
                else:
                    # Clean up for preview
                    content = content.replace('\n', ' ')
                    content = ' '.join(content.split())
                    preview = content[:max_length] + "..." if len(content) > max_length else content
                    
            self._preview_cache[cache_key] = preview
            return preview
        except:
            return "<unable to read>"
            
    def refresh_files(self, search_term: str = ""):
        """Refresh the file list"""
        self.clear()
        self.current_filter = search_term
        
        try:
            current_dir = Path.cwd()
            items = []
            
            # Get all items
            for item in sorted(current_dir.iterdir()):
                # Skip hidden files unless enabled
                if not self.show_hidden and item.name.startswith('.'):
                    continue
                
                # Include directories and text files
                if item.is_dir():
                    items.append((item, self.get_preview(item), True))
                elif item.is_file() and (item.suffix.lower() in TEXT_EXTENSIONS or item.suffix == ''):
                    # Check files without extension if they might be text
                    if item.suffix == '':
                        try:
                            # Quick check if it's text
                            with open(item, 'rb') as f:
                                chunk = f.read(512)
                                if b'\0' not in chunk:  # No null bytes = likely text
                                    items.append((item, self.get_preview(item), False))
                        except:
                            pass
                    else:
                        items.append((item, self.get_preview(item), False))
                    
            # Apply search filter
            if search_term:
                filtered_items = []
                search_lower = search_term.lower()
                
                for path, preview, is_dir in items:
                    searchable = f"{path.name} {preview}".lower()
                    
                    if HAS_FUZZY:
                        score = fuzz.partial_ratio(search_lower, searchable)
                        if score > 60:
                            filtered_items.append((path, preview, is_dir, score))
                    else:
                        if search_lower in searchable:
                            filtered_items.append((path, preview, is_dir, 100))
                
                # Sort by score
                filtered_items.sort(key=lambda x: x[3], reverse=True)
                items = [(p, pv, d) for p, pv, d, _ in filtered_items]
                        
            # Add items to list
            if not items:
                if search_term:
                    self.append(ListItem(Label("No files found matching your search")))
                else:
                    self.append(ListItem(Label("No text files in this directory")))
            else:
                for path, preview, is_dir in items:
                    self.append(FileItem(path, preview, is_dir))
                    
        except PermissionError:
            self.append(ListItem(Label("⚠️  Permission denied")))
        except Exception as e:
            self.append(ListItem(Label(f"⚠️  Error: {str(e)}")))


# ============================================================================
# Dialogs
# ============================================================================

class SaveConfirmDialog(Screen):
    """Save confirmation dialog with three options"""
    
    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
        Binding("left", "focus_previous", "Previous", show=False, priority=True),
        Binding("right", "focus_next", "Next", show=False, priority=True),
    ]
    
    CSS = """
    SaveConfirmDialog {
        align: center middle;
    }
    
    #dialog {
        width: 60;
        height: 11;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #message {
        height: 5;
        content-align: center middle;
    }
    
    #buttons {
        height: 3;
        layout: horizontal;
        align: center middle;
    }
    
    #buttons Button {
        margin: 0 1;
        min-width: 16;
    }
    """
    
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Static("You have unsaved changes.\nDo you want to save them?", id="message")
            with Container(id="buttons"):
                yield Button("Save", variant="success", id="save")
                yield Button("Don't Save", variant="warning", id="dont_save")
                yield Button("Cancel", variant="primary", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss()
        if event.button.id == "save":
            self.callback("save")
        elif event.button.id == "dont_save":
            self.callback("dont_save")
        else:  # cancel
            self.callback("cancel")
    
    def action_cancel(self):
        """Handle escape key"""
        self.dismiss()
        self.callback("cancel")
    
    def action_focus_next(self):
        """Move focus to next button"""
        self.focus_next()
        
    def action_focus_previous(self):
        """Move focus to previous button"""
        self.focus_previous()
    
    def on_mount(self):
        """Set initial focus to Cancel button"""
        cancel_button = self.query_one("#cancel", Button)
        cancel_button.focus()


class ConfirmDialog(Screen):
    """Simple yes/no confirmation dialog"""
    
    CSS = """
    ConfirmDialog {
        align: center middle;
    }
    
    #dialog {
        width: 60;
        height: 11;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    
    #message {
        height: 5;
        content-align: center middle;
    }
    
    #buttons {
        height: 3;
        align: center middle;
    }
    
    Button {
        margin: 0 1;
    }
    """
    
    def __init__(self, message: str, action_callback):
        super().__init__()
        self.message = message
        self.action_callback = action_callback
        
    def compose(self) -> ComposeResult:
        with Container(id="dialog"):
            yield Static(self.message, id="message")
            with Container(id="buttons"):
                yield Button("Yes", variant="error", id="yes")
                yield Button("No", variant="primary", id="no")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.action_callback()
        self.app.pop_screen()


# ============================================================================
# Screens
# ============================================================================

class EditorScreen(Screen):
    """Editor screen for editing files"""
    
    BINDINGS = [
        Binding("ctrl+s", "save", "Save", priority=True),
        Binding("ctrl+x", "close_with_check", "Exit", priority=True),
        Binding("ctrl+c", "copy_all", "Copy All", priority=True),
        Binding("escape", "close_with_check", "Exit", priority=True),
    ]
    
    def __init__(self, file_path: Optional[Path] = None):
        super().__init__()
        self.file_path = file_path
        self.original_content = ""
        self.is_modified = False
        
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            TextArea(id="editor", language="markdown", tab_behavior="indent"),
            id="editor-container"
        )
        yield Footer()
        
    def on_mount(self):
        """Load file content when mounted"""
        editor = self.query_one("#editor", TextArea)
        
        if self.file_path and self.file_path.exists():
            try:
                content = self.file_path.read_text(encoding='utf-8')
                self.original_content = content
                editor.text = content
                self.sub_title = str(self.file_path.name)
            except Exception as e:
                editor.text = f"Error loading file: {e}"
                editor.read_only = True
        else:
            self.sub_title = "new file"
            
        editor.focus()
    
    def on_text_area_changed(self, event: TextArea.Changed):
        """Track modifications"""
        editor = self.query_one("#editor", TextArea)
        if editor.text != self.original_content:
            if not self.is_modified:
                self.is_modified = True
                if self.sub_title and not self.sub_title.endswith(" *"):
                    self.sub_title = self.sub_title + " *"
        else:
            if self.is_modified:
                self.is_modified = False
                if self.sub_title and self.sub_title.endswith(" *"):
                    self.sub_title = self.sub_title[:-2]
        
    def action_save(self):
        """Save the file"""
        editor = self.query_one("#editor", TextArea)
        
        if editor.read_only:
            self.notify("Cannot save: file is read-only", severity="error")
            return
        
        if not self.file_path:
            timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
            self.file_path = Path(f"{timestamp}.md")
            
        try:
            self.file_path.write_text(editor.text, encoding='utf-8')
            self.original_content = editor.text
            self.is_modified = False
            self.sub_title = str(self.file_path.name)
            self.notify(f"Saved: {self.file_path.name}", severity="information")
        except Exception as e:
            self.notify(f"Error saving: {e}", severity="error")
            
    def action_copy_all(self):
        """Copy all content or selection to clipboard"""
        if not HAS_CLIPBOARD:
            self.notify("Install pyperclip for clipboard support", severity="warning")
            return
            
        editor = self.query_one("#editor", TextArea)
        selected = editor.selected_text
        
        try:
            if selected:
                pyperclip.copy(selected)
                self.notify("Copied selection to clipboard", severity="information")
            else:
                pyperclip.copy(editor.text)
                self.notify("Copied all text to clipboard", severity="information")
        except Exception as e:
            self.notify(f"Clipboard error: {e}", severity="error")
            
    def action_close_with_check(self):
        """Close editor with save check"""
        if self.is_modified:
            # Show save dialog with three options
            def handle_save_choice(choice):
                if choice == "save":
                    self.action_save()
                    self._close_editor()
                elif choice == "dont_save":
                    self._close_editor()
                # else: cancel - do nothing
            
            self.app.push_screen(SaveConfirmDialog(handle_save_choice))
        else:
            # No changes, just close
            self._close_editor()
    
    def _close_editor(self):
        """Actually close the editor"""
        self.dismiss()


class PreviewScreen(Screen):
    """Preview screen for viewing files without editing"""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("e", "edit", "Edit"),
    ]
    
    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = file_path
        
    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Static(id="preview-content"),
            id="preview-container"
        )
        yield Footer()
        
    def on_mount(self):
        """Load file content"""
        self.sub_title = f"Preview: {self.file_path.name}"
        content_widget = self.query_one("#preview-content", Static)
        
        try:
            content = self.file_path.read_text(encoding='utf-8')
            # Limit preview length for performance
            if len(content) > 100000:
                content = content[:100000] + "\n\n... (truncated)"
            content_widget.update(content)
        except Exception as e:
            content_widget.update(f"Error loading file: {e}")
            
    def action_close(self):
        """Close preview"""
        self.app.pop_screen()
        
    def action_edit(self):
        """Switch to edit mode"""
        self.app.pop_screen()
        self.app.push_screen(EditorScreen(self.file_path))


class ModulesScreen(Screen):
    """Screen showing available modules"""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
        Binding("s", "launch_stampt", "Launch stampt"),
        Binding("b", "launch_blipt", "Launch blipt"),
        Binding("t", "launch_smallt", "Launch smallt"),
        Binding("o", "launch_templet", "Launch templet"),
        Binding("g", "launch_gitnot", "Launch gitnot"),
        Binding("l", "launch_ql", "Launch ql"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(id="modules-content"),
            id="modules-container"
        )
        yield Footer()
        
    def on_mount(self):
        """Load modules information"""
        self.sub_title = "Modules"
        content = self.query_one("#modules-content", Static)
        
        # Module configurations
        module_configs = [
            ("stampt", "s", "Timestamped notes with dashboard"),
            ("blipt", "b", "Quick scratchpad with numbered entries"),
            ("smallt", "t", "Simple task manager"),
            ("templet", "o", "Lightweight template manager"),
            ("gitnot", "g", "Lightweight version control"),
            ("ql", "l", "Quick command launcher"),
        ]
        
        # Build content
        lines = ["# Available Modules\n",
                "Press the key shown to launch a module.\n\n"]
        
        for module, key, description in module_configs:
            exists, _ = ModuleManager.check_module(module)
            status = "✓" if exists else "✗"
            status_color = "green" if exists else "dim"
            lines.append(f"[{status_color}]{status}[/] [{key}] {module:<10} - {description}\n")
        
        lines.extend([
            "\n## Installation\n\n",
            f"Missing modules? Download to: {Path(sys.argv[0]).resolve().parent}\n",
            "Make executable: chmod +x <module>\n\n",
            "## Keyboard Shortcuts\n\n",
            "From main screen:\n",
            "- m: Show this menu\n",
            "- Ctrl+S/B/T/O/G/L: Quick launch modules\n"
        ])
        
        content.update("".join(lines))
    
    def _launch_module(self, module_name: str):
        """Launch a module and exit mdns"""
        exists, _ = ModuleManager.check_module(module_name)
        if exists:
            self.app._module_to_launch = module_name
            self.app.exit()
        else:
            self.notify(f"{module_name} not installed", severity="error")
    
    def action_launch_stampt(self): self._launch_module("stampt")
    def action_launch_blipt(self): self._launch_module("blipt")
    def action_launch_smallt(self): self._launch_module("smallt")
    def action_launch_templet(self): self._launch_module("templet")
    def action_launch_gitnot(self): self._launch_module("gitnot")
    def action_launch_ql(self): self._launch_module("ql")
    
    def action_close(self):
        """Close modules screen"""
        self.app.pop_screen()


class HelpScreen(Screen):
    """Help screen showing all shortcuts"""
    
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
    ]
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Static(id="help-content"),
            id="help-container"
        )
        yield Footer()
        
    def on_mount(self):
        """Load help content"""
        self.sub_title = "Help"
        
        help_text = """# mdns Help

## Navigation
  ↑/↓ or j/k    Navigate files
  Enter         Open file/directory
  p             Preview file (read-only)
  Escape        Clear search / Go to parent
  Backspace     Always go to parent
  /             Search files

## File Operations  
  n             New timestamped note
  N             New untitled note  
  d             Delete file (with confirmation)
  r             Refresh file list
  .             Toggle hidden files

## Editor Commands
  Ctrl+S        Save file
  Ctrl+X        Exit editor (with save check)
  Ctrl+C        Copy all/selected text
  Escape        Exit editor (with save check)

## Module Launcher
  m             Show modules menu
  Ctrl+S        Launch stampt (timestamped notes)
  Ctrl+B        Launch blipt (scratchpad)
  Ctrl+T        Launch smallt (task manager)
  Ctrl+O        Launch templet (template manager)
  Ctrl+G        Launch gitnot (version control)
  Ctrl+L        Launch ql (quick command launcher)

## General
  ?             Show this help
  q             Quit application (main screen only)

## Tips
- Search looks at both filename and content
- Press 'p' to preview without editing
- All modules work in your current directory
- Install modules to: ~/.local/bin/"""
        
        self.query_one("#help-content", Static).update(help_text)
        
    def action_close(self):
        """Close help"""
        self.app.pop_screen()


# ============================================================================
# Main Application
# ============================================================================

class MDNSApp(App):
    """Main mdns application"""
    
    TITLE = "mdns - markdown notes studio"
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    Header {
        background: #0066cc;
    }
    
    Footer {
        background: #004499;
    }
    
    #file-list {
        height: 100%;
        border: solid #0066cc;
    }
    
    #search-container {
        height: 3;
        border: solid #0066cc;
        margin: 0 1 1 1;
        padding: 0 1;
    }
    
    #search-input {
        background: transparent;
        border: none;
    }
    
    ListView:focus > ListItem.--highlight {
        background: #0066cc;
    }
    
    TextArea {
        border: solid #0066cc;
    }
    
    TextArea:focus {
        border: solid #0099ff;
    }
    
    #editor-container {
        padding: 1;
        height: 100%;
    }
    
    #preview-container, #help-container, #modules-container {
        padding: 1 2;
        height: 100%;
    }
    """
    
    BINDINGS = [
        Binding("n", "new_note", "New Note"),
        Binding("N", "new_untitled", "New Untitled"),
        Binding("/", "search", "Search"),
        Binding("escape", "clear_search", "Clear", show=False),
        Binding("backspace", "go_parent", "Back", show=False),
        Binding(".", "toggle_hidden", "Hidden"),
        Binding("q", "quit", "Quit"),
        Binding("?", "help", "Help"),
        Binding("r", "refresh", "Refresh"),
        Binding("d", "delete_file", "Delete"),
        Binding("p", "preview", "Preview"),
        Binding("m", "show_modules", "Modules"),
        # Module shortcuts
        Binding("ctrl+s", "launch_stampt", "Stampt", show=False),
        Binding("ctrl+b", "launch_blipt", "Blipt", show=False),
        Binding("ctrl+t", "launch_smallt", "Smallt", show=False),
        Binding("ctrl+o", "launch_templet", "Templet", show=False),
        Binding("ctrl+g", "launch_gitnot", "Gitnot", show=False),
        Binding("ctrl+l", "launch_ql", "QL", show=False),
    ]
    
    def __init__(self):
        super().__init__()
        self._module_to_launch = None
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(
                Input(placeholder="Search files... (press / to focus)", id="search-input"),
                id="search-container"
            ),
            FileExplorer(id="file-list"),
            id="main-container"
        )
        yield Footer()
        
    def on_mount(self):
        """Initialize the app"""
        file_list = self.query_one("#file-list", FileExplorer)
        file_list.refresh_files()
        file_list.focus()
        self.sub_title = str(Path.cwd())
        
    def on_input_changed(self, event: Input.Changed):
        """Handle search input changes"""
        if event.input.id == "search-input":
            file_list = self.query_one("#file-list", FileExplorer)
            file_list.refresh_files(event.value)
        
    def action_new_note(self):
        """Create new timestamped note"""
        timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        self.push_screen(EditorScreen(Path(f"{timestamp}.md")))
        
    def action_new_untitled(self):
        """Create new untitled note"""
        i = 1
        while Path(f"untitled-{i}.md").exists():
            i += 1
        self.push_screen(EditorScreen(Path(f"untitled-{i}.md")))
        
    def action_search(self):
        """Focus search input"""
        self.query_one("#search-input", Input).focus()
        
    def action_clear_search(self):
        """Clear search or go to parent"""
        search = self.query_one("#search-input", Input)
        if search.value:
            search.value = ""
            self.query_one("#file-list", FileExplorer).focus()
        else:
            self.action_go_parent()
        
    def action_toggle_hidden(self):
        """Toggle hidden files"""
        file_list = self.query_one("#file-list", FileExplorer)
        file_list.show_hidden = not file_list.show_hidden
        file_list.refresh_files(file_list.current_filter)
        self.notify(f"Hidden files: {'shown' if file_list.show_hidden else 'hidden'}")
        
    def action_refresh(self):
        """Refresh file list"""
        file_list = self.query_one("#file-list", FileExplorer)
        file_list.refresh_files(file_list.current_filter)
        self.notify("Refreshed")
        
    def action_preview(self):
        """Preview selected file"""
        file_list = self.query_one("#file-list", FileExplorer)
        if highlighted := file_list.highlighted_child:
            if isinstance(highlighted, FileItem) and highlighted.path.is_file():
                self.push_screen(PreviewScreen(highlighted.path))
                
    def action_delete_file(self):
        """Delete selected file with confirmation"""
        file_list = self.query_one("#file-list", FileExplorer)
        if highlighted := file_list.highlighted_child:
            if isinstance(highlighted, FileItem) and highlighted.path.is_file():
                def do_delete():
                    try:
                        highlighted.path.unlink()
                        file_list.refresh_files(file_list.current_filter)
                        self.notify(f"Deleted: {highlighted.path.name}")
                    except Exception as e:
                        self.notify(f"Error: {e}", severity="error")
                
                self.push_screen(
                    ConfirmDialog(
                        f"Delete '{highlighted.path.name}'?\nThis cannot be undone.",
                        do_delete
                    )
                )
                    
    def action_help(self):
        """Show help screen"""
        self.push_screen(HelpScreen())
        
    def action_go_parent(self):
        """Go to parent directory"""
        try:
            os.chdir("..")
            self.sub_title = str(Path.cwd())
            file_list = self.query_one("#file-list", FileExplorer)
            file_list.refresh_files()
            self.query_one("#search-input", Input).value = ""
        except Exception as e:
            self.notify(f"Cannot go to parent directory: {e}", severity="error")
    def action_show_modules(self):
        """Show modules screen"""
        self.push_screen(ModulesScreen())
    
    def _launch_module(self, module_name: str):
        """Launch a module and exit mdns"""
        exists, _ = ModuleManager.check_module(module_name)
        if exists:
            self._module_to_launch = module_name
            self.exit()
        else:
            self.notify(f"{module_name} not installed", severity="error")
    
    # Module launch actions
    def action_launch_stampt(self): self._launch_module("stampt")
    def action_launch_blipt(self): self._launch_module("blipt")
    def action_launch_smallt(self): self._launch_module("smallt")
    def action_launch_templet(self): self._launch_module("templet")
    def action_launch_gitnot(self): self._launch_module("gitnot")
    def action_launch_ql(self): self._launch_module("ql")
        
    @on(ListView.Selected) 
    def on_list_view_selected(self, event: ListView.Selected):
        """Handle item selection"""
        if isinstance(event.item, FileItem):
            item = event.item
            if item.path.is_dir():
                try:
                    os.chdir(item.path)
                    self.sub_title = str(Path.cwd())
                    file_list = self.query_one("#file-list", FileExplorer)
                    file_list.refresh_files()
                    self.query_one("#search-input", Input).value = ""
                except Exception as e:
                    self.notify(f"Cannot enter: {e}", severity="error")
            else:
                self.push_screen(EditorScreen(item.path))


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="mdns - Markdown Notes Studio",
        epilog="Run without arguments for interactive mode, or specify a module to run."
    )
    parser.add_argument(
        "module", 
        nargs="?",
        help="Optional module to run (e.g., stampt, blipt, smallt, templet, gitnot, ql)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="mdns v32"
    )
    
    args = parser.parse_args()
    
    if args.module:
        ModuleManager.run_module(args.module)
    else:
        try:
            app = MDNSApp()
            app.run()
            
            # Launch module after exit if requested
            if hasattr(app, '_module_to_launch') and app._module_to_launch:
                ModuleManager.run_module(app._module_to_launch)
                
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()