#!/usr/bin/env python3
"""Keep Xingtu tool-sheet content interactive with a top-center resize handle."""
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

# Open the secondary panel at 200dp. Users resize it from the dedicated
# top-center handle, keeping the bottom edge clear of system navigation.
old_height = "toolPanelHeightDp = if (panel == EditorPanel.TEXT2) 330f else 180f"
new_height = "toolPanelHeightDp = 200f"
if old_height in s:
    s = s.replace(old_height, new_height)
elif new_height not in s:
    raise SystemExit("Could not locate the primary-menu panel-height assignments")

# Hide the persistent primary dock while the secondary panel is open.
dock_visibility_old = """// Persistent primary navigation: keep it in the editor's main Box, not only inside the tool Dialog.
            if (!previewMode) {"""
dock_visibility_new = """// Persistent primary navigation is hidden while the secondary tool sheet is open.
            if (!previewMode && !showToolPopup) {"""
if dock_visibility_old in s:
    s = s.replace(dock_visibility_old, dock_visibility_new, 1)
elif dock_visibility_new not in s:
    raise SystemExit("Could not locate the persistent primary navigation visibility condition")


# Move the resize handle from the sheet footer to the top center, before the
# title/close row. Keep its gesture math unchanged: dragging upward increases
# the panel height, while the bottom edge remains free of back-navigation taps.
handle_pattern = re.compile(
    r"(?ms)^                    Box\(\n"
    r"                        Modifier\.fillMaxWidth\(\)\.height\(26\.dp\).*?"
    r"^                    \}\n"
)
handle_match = handle_pattern.search(s)
if handle_match:
    handle_block = handle_match.group(0)
    s = s[:handle_match.start()] + s[handle_match.end():]
    header_anchor = '                    Row(Modifier.fillMaxWidth().height(48.dp).padding(horizontal = 9.dp)'
    sheet_start = s.find("if (showToolPopup && activePanel")
    header_pos = s.find(header_anchor, sheet_start)
    if header_pos < 0:
        raise SystemExit("Could not locate the tool-sheet header to position the top resize handle")
    s = s[:header_pos] + handle_block + s[header_pos:]
elif s.count("Modifier.fillMaxWidth().height(26.dp)") != 1:
    raise SystemExit("Could not safely locate the existing resize handle for relocation")

# Start at 200dp and clamp both the animated height and drag range to 200–400dp.
s = s.replace("var toolPanelHeightDp by remember { mutableFloatStateOf(100f) }", "var toolPanelHeightDp by remember { mutableFloatStateOf(200f) }", 1)

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

# The overlay must occupy only the actual sheet bounds. A full-screen
# transparent layer sits above the WebView and prevents canvas hit testing.
overlay_old = "Box(Modifier.fillMaxSize().zIndex(100f), contentAlignment = Alignment.BottomCenter) {"
overlay_new = "Box(Modifier.fillMaxWidth().wrapContentHeight().zIndex(100f), contentAlignment = Alignment.BottomCenter) {"
if overlay_old in s:
    s = s.replace(overlay_old, overlay_new, 1)
elif overlay_new not in s:
    raise SystemExit("Could not locate the full-screen sheet overlay")

inner_old = "Box(Modifier.fillMaxWidth().zIndex(100f), contentAlignment = Alignment.BottomCenter) {"
inner_new = "Box(Modifier.fillMaxWidth().wrapContentHeight().zIndex(100f), contentAlignment = Alignment.BottomCenter) {"
if inner_old in s:
    s = s.replace(inner_old, inner_new, 1)
elif inner_new not in s:
    raise SystemExit("Could not locate the sheet's inner layout container")

# Keep the sheet height and drag range aligned with the requested 200dp–400dp range.
s = s.replace("coerceIn(100f, 400f)", "coerceIn(200f, 400f)")

checks = {
    "single independent primary dock": s.count("height(50.dp)") >= 1 and s.count(dock_marker) == 0,
    "inline non-modal bottom sheet": "if (showToolPopup && activePanel != EditorPanel.CANVAS)" in s,
    "sheet overlay is bounded to its own height without invalid parent-scope alignment": overlay_new in s and overlay_old not in s and ".wrapContentHeight().align(Alignment.BottomCenter)" not in s,
    "inner sheet container wraps content": inner_new in s,
    "canvas touch area is not covered by a full-screen overlay": "Box(Modifier.fillMaxSize().zIndex(100f)" not in s,
    "panel itself consumes touches only inside panel bounds": ".height(animatedToolPanelHeight)" in s and ".clickable(" in s,
    "200dp initial panel height": "toolPanelHeightDp = 200f" in s and "var toolPanelHeightDp by remember { mutableFloatStateOf(200f) }" in s,
    "200dp collapsed minimum and 400dp maximum": "coerceIn(200f, 400f)" in s and "val animatedToolPanelHeight = toolPanelHeightDp.coerceIn(200f, 400f).dp" in s,
    "no parent gesture interception on content": "toolPanelNestedScrollConnection" not in s and ".nestedScroll(" not in s,
    "content scroll is independent": ".verticalScroll(toolPanelScrollState)" in s,
    "remembered content scroll state": content_state in s,
    "top-center drag handle": handle_marker in s and s.find(handle_marker) < s.find('Row(Modifier.fillMaxWidth().height(48.dp).padding(horizontal = 9.dp)') and "toolPanelHeightDp = (toolPanelHeightDp - deltaDp.value).coerceIn(200f, 400f)" in s,
    "primary navigation hidden while secondary panel is open": "if (!previewMode && !showToolPopup)" in s,
    "text style updates are sent to the live canvas immediately": "NativeEditor.changed(root.innerHTML);" in s[s.index("function applyText2Style"):s.index("function applyText2Command")],
    "canvas redraw bridge remains connected": "NativeEditor.previewChanged==='function'" in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    ERROR.write_text("Xingtu bottom-sheet validation failed: " + ", ".join(failed) + "\n", encoding="utf-8")
    raise SystemExit("Xingtu bottom-sheet validation failed: " + ", ".join(failed))

EDITOR.write_text(s, encoding="utf-8")
print("Xingtu bottom sheet fixed: panel-specific initial heights, independent content taps/selection/scrolling, dedicated top-center handle resizing and separate primary dock.")
