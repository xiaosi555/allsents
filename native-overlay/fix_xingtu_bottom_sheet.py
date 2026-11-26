#!/usr/bin/env python3
"""Keep Xingtu tool-sheet content fully interactive while retaining explicit resize handles."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "xingtu_bottom_sheet_patch_error.txt"

if not EDITOR.is_file():
    raise SystemExit(f"Xingtu editor source missing: {EDITOR}")

s = EDITOR.read_text(encoding="utf-8")

# Remove only the duplicate primary navigation row inside the sheet. The
# persistent primary menu remains a sibling of the sheet in the main layout.
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
    end = tail_start + len("\n                }")
    s = s[:dock_start] + s[end:]

# Give each tool panel a useful initial height. The primary menu only selects
# which panel opens; all editing controls remain inside the secondary panel.
old_height = "toolPanelHeightDp = if (panel == EditorPanel.TEXT2) 330f else 180f"
new_height = """toolPanelHeightDp = when (panel) {
                                            EditorPanel.TEXT -> 260f
                                            EditorPanel.TEXT2 -> 330f
                                            EditorPanel.TITLE -> 210f
                                            EditorPanel.IMAGE -> 230f
                                            EditorPanel.LAYOUT -> 220f
                                            EditorPanel.CARD -> 230f
                                            EditorPanel.COMPONENT -> 220f
                                            EditorPanel.SVG -> 210f
                                            EditorPanel.LAYER -> 240f
                                            EditorPanel.STYLE -> 260f
                                            EditorPanel.TEMPLATE -> 260f
                                            EditorPanel.DOCUMENT -> 200f
                                            EditorPanel.CANVAS -> 220f
                                        }"""
if old_height in s:
    s = s.replace(old_height, new_height, 1)
elif "EditorPanel.TEXT -> 260f" not in s:
    raise SystemExit("Could not locate the primary-menu panel-height assignment")

# Do not attach a parent NestedScrollConnection to the panel body. Such a
# parent can consume vertical gestures intended for child scrolling, sliders
# or long-press text selection. The body owns its own scroll state instead.
state_anchor = "    val toolPanelDensity = LocalDensity.current"
content_state = "    val toolPanelScrollState = rememberScrollState()"
if content_state not in s:
    if s.count(state_anchor) != 1:
        raise SystemExit("Could not locate the unique tool panel density state")
    s = s.replace(state_anchor, state_anchor + "\n" + content_state, 1)

old_scroll = 'Column((if (activePanel == EditorPanel.TEXT2) Modifier.fillMaxWidth().weight(1f) else Modifier.fillMaxWidth().weight(1f).verticalScroll(rememberScrollState())).padding(horizontal = 13.dp, vertical = 6.dp))'
new_scroll = 'Column((if (activePanel == EditorPanel.TEXT2) Modifier.fillMaxWidth().weight(1f) else Modifier.fillMaxWidth().weight(1f).verticalScroll(toolPanelScrollState)).padding(horizontal = 13.dp, vertical = 4.dp))'
if old_scroll in s:
    s = s.replace(old_scroll, new_scroll, 1)
elif new_scroll not in s:
    raise SystemExit("Could not locate the tool panel's independent content scroll container")

# Only the secondary-navigation header and the bottom handle resize the sheet.
# Taps on tabs still reach their clickable children; vertical drags on the
# content body remain available to controls and its own scroll container.
header_drag = """.pointerInput(Unit) {
                            detectDragGestures { change, dragAmount ->
                                change.consume()
                                val deltaDp = with(toolPanelDensity) { dragAmount.y.toDp().value }
                                toolPanelHeightDp = (toolPanelHeightDp - deltaDp).coerceIn(150f, 400f)
                            }
                        }"""
header_pattern = r'(Row\(Modifier\.fillMaxWidth\(\)\.height\(48\.dp\)\.padding\(horizontal = 9\.dp\))(?=,\s*verticalAlignment = Alignment\.CenterVertically, horizontalArrangement = Arrangement\.SpaceBetween\)\s*\{)'
if header_drag in s:
    header_count = 1
else:
    s, header_count = re.subn(header_pattern, r'\1' + header_drag, s, count=1)
    if header_count != 1:
        raise SystemExit("Could not locate the outer tool-sheet header for direct resizing")

checks = {
    "single independent primary dock": s.count("height(50.dp)") >= 1 and s.count(dock_marker) == 0,
    "inline non-modal bottom sheet": "if (showToolPopup && activePanel != EditorPanel.CANVAS)" in s,
    "panel-specific initial heights": "EditorPanel.TEXT -> 260f" in s and "EditorPanel.DOCUMENT -> 200f" in s,
    "secondary navigation drag surface": header_count == 1,
    "150dp collapsed minimum and 400dp maximum": "coerceIn(150f, 400f)" in s,
    "direct height update avoids opening rebound": "val animatedToolPanelHeight = toolPanelHeightDp.coerceIn(100f, 400f).dp" in s and "animateDpAsState" not in s,
    "no parent gesture interception on content": "toolPanelNestedScrollConnection" not in s and ".nestedScroll(" not in s,
    "content scroll is independent": ".verticalScroll(toolPanelScrollState)" in s,
    "remembered content scroll state": content_state in s,
    "bottom-center drag handle": handle_marker in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    ERROR.write_text("Xingtu bottom-sheet validation failed: " + ", ".join(failed) + "\n", encoding="utf-8")
    raise SystemExit("Xingtu bottom-sheet validation failed: " + ", ".join(failed))

EDITOR.write_text(s, encoding="utf-8")
print("Xingtu bottom sheet fixed: panel-specific initial heights, independent content taps/selection/scrolling, dedicated header/handle resizing and separate primary dock.")
