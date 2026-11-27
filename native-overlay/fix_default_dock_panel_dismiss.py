#!/usr/bin/env python3
"""Keep default-dock secondary panels open when the WebView reports an empty selection."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "editor_default_dock_panel_patch_error.txt"
if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")
s = EDITOR.read_text(encoding="utf-8")
old = '''                                if (state.kind == EditorSelectionKind.NONE) {
                                    selectedTextActive = false
                                    floatingMenu = ""
                                    floatingToolbarRequest = ""
                                    showToolPopup = false
                                    showCanvasPopup = false
                                } else if (typeChanged) {
                                    // A different canvas object takes focus; reveal its matching dock.
                                    showToolPopup = false
                                    showCanvasPopup = false
                                }'''
new = '''                                if (state.kind == EditorSelectionKind.NONE) {
                                    selectedTextActive = false
                                    floatingMenu = ""
                                    floatingToolbarRequest = ""
                                }
                                // Selection callbacks can arrive after a default-dock tap (for
                                // example, when WebView loses focus). They must not dismiss the
                                // secondary panel that the user has just opened. Only route the
                                // dock automatically when no tool/canvas panel is being shown.
                                if (!showToolPopup && !showCanvasPopup) {
                                    if (state.kind == EditorSelectionKind.NONE) {
                                        showToolPopup = false
                                        showCanvasPopup = false
                                    } else if (typeChanged) {
                                        // A different canvas object takes focus; reveal its matching dock.
                                        showToolPopup = false
                                        showCanvasPopup = false
                                    }
                                }'''
count = s.count(old)
if count != 1:
    ERROR.write_text(f"selection callback dismissal block count: {count}\\n", encoding="utf-8")
    raise SystemExit(f"Default dock panel patch anchor mismatch: expected 1, found {count}")
s = s.replace(old, new, 1)
required = [
    "if (!showToolPopup && !showCanvasPopup) {",
    "Selection callbacks can arrive after a default-dock tap",
    "selectedTextActive = false"
]
missing = [item for item in required if item not in s]
if missing:
    ERROR.write_text("Missing output: " + ", ".join(missing) + "\\n", encoding="utf-8")
    raise SystemExit("Default dock panel patch validation failed: " + ", ".join(missing))
EDITOR.write_text(s, encoding="utf-8")
print("Default dock secondary panels are now protected from asynchronous empty-selection callbacks.")
