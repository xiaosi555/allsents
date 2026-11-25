#!/usr/bin/env python3
"""Correct the Xingtu editor's non-modal expandable bottom tool sheet."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "xingtu_bottom_sheet_patch_error.txt"

if not EDITOR.is_file():
    raise SystemExit(f"Xingtu editor source missing: {EDITOR}")

s = EDITOR.read_text(encoding="utf-8")

# The primary dock is already rendered outside the Popup. Remove the accidental
# second copy from the Popup so the sheet overlays that dock without containing it.
dock_marker = "                // Fixed primary navigation dock, as a sibling of the expandable sheet."
if s.count(dock_marker) != 1:
    raise SystemExit(f"Expected exactly one duplicate in-popup dock marker, found {s.count(dock_marker)}")
start = s.index(dock_marker)
handle_marker = "                    Box(\n                        Modifier.fillMaxWidth().height(26.dp)"
end = s.find(handle_marker, start)
if end < 0:
    raise SystemExit("Could not locate the sheet's bottom-center drag handle")
s = s[:start] + s[end:]

# Preserve the established 100dp collapsed/initial height whenever a different
# primary tool is opened. 350dp remains only the maximum expanded height.
old = """                                    } else {
                                        showCanvasPopup = false
                                        showToolPopup = true
                                    }
                                    if (panel == EditorPanel.LAYER) refreshLayerItems()"""
new = """                                    } else {
                                        showCanvasPopup = false
                                        toolPanelHeightDp = 100f
                                        showToolPopup = true
                                    }
                                    if (panel == EditorPanel.LAYER) refreshLayerItems()"""
if "toolPanelHeightDp = 100f" not in s:
    if s.count(old) != 1:
        raise SystemExit(f"Expected one primary navigation open handler, found {s.count(old)}")
    s = s.replace(old, new, 1)

# Fail the build if future edits accidentally reintroduce a dock inside the sheet,
# a modal/overlay configuration, or remove the bounded animated drag behavior.
checks = {
    "single independent primary dock": s.count("height(50.dp)") >= 1 and s.count(dock_marker) == 0,
    "non-modal popup": "PopupProperties(focusable = false" in s,
    "100dp initial height": "mutableFloatStateOf(100f)" in s and "toolPanelHeightDp = 100f" in s,
    "350dp maximum": "coerceIn(100f, 350f)" in s,
    "smooth height animation": "tween(durationMillis = 180)" in s,
    "independent content scrolling": ".verticalScroll(rememberScrollState())" in s,
    "bottom-center drag handle": handle_marker in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    ERROR.write_text("Xingtu bottom-sheet validation failed: " + ", ".join(failed) + "\\n", encoding="utf-8")
    raise SystemExit("Xingtu bottom-sheet validation failed: " + ", ".join(failed))

EDITOR.write_text(s, encoding="utf-8")
print("Xingtu bottom sheet fixed: independent dock, non-modal overlay, 100dp collapsed start, 350dp maximum, animated resize, scrollable content and bottom drag handle.")
