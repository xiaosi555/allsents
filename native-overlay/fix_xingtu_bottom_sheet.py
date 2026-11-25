#!/usr/bin/env python3
"""Correct the Xingtu editor's non-modal expandable bottom tool sheet."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "xingtu_bottom_sheet_patch_error.txt"

if not EDITOR.is_file():
    raise SystemExit(f"Xingtu editor source missing: {EDITOR}")

s = EDITOR.read_text(encoding="utf-8")

# The primary dock is rendered once in the editor's main layout. Remove only
# the duplicate Row itself; keep the three surrounding scope-closing braces.
dock_marker = "                // Fixed primary navigation dock, as a sibling of the expandable sheet."
handle_marker = "                    Box(\n                        Modifier.fillMaxWidth().height(26.dp)"
row_tail = "\n                }\n\n                    }\n                    }\n                    }\n                    Box(\n                        Modifier.fillMaxWidth().height(26.dp)"

dock_count = s.count(dock_marker)
if dock_count == 1:
    dock_start = s.index(dock_marker)
    row_start = s.find("Row(", dock_start)
    anchor = s.find("height(50.dp)", row_start)
elif dock_count == 0:
    dock_heights = [m.start() for m in re.finditer(r"height\(50\.dp\)", s)]
    if len(dock_heights) == 2:
        anchor = dock_heights[1]
        row_start = s.rfind("Row(", 0, anchor)
        dock_start = s.rfind("\n", 0, row_start) + 1
    elif len(dock_heights) == 1:
        anchor = -1
        row_start = -1
        dock_start = -1
    else:
        raise SystemExit(f"Unexpected dock structure without marker: {len(dock_heights)} height anchors")
else:
    raise SystemExit(f"Expected at most one duplicate dock marker, found {dock_count}")

if dock_start >= 0:
    if row_start < 0 or anchor < 0:
        raise SystemExit("Could not safely locate the duplicate primary dock")
    tail_start = s.find(row_tail, anchor)
    if tail_start < 0:
        raise SystemExit("Could not locate the end of the duplicate dock Row without consuming surrounding scope braces")
    # row_tail begins with the outer Row's closing brace. Keep the following
    # three scope braces and the drag handle exactly where they were.
    end = tail_start + len("\n                }")
    s = s[:dock_start] + s[end:]

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
