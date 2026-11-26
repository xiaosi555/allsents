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
    end = tail_start + len("\n                }")
    s = s[:dock_start] + s[end:]

# Give each tool panel a content-appropriate initial height, capped by the 400dp maximum.
old = """                                    } else {
                                        showCanvasPopup = false
                                        showToolPopup = true
                                    }
                                    if (panel == EditorPanel.LAYER) refreshLayerItems()"""
new = """                                    } else {
                                        showCanvasPopup = false
                                        toolPanelHeightDp = when (panel) {
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
                                        }
                                        showToolPopup = true
                                    }
                                    if (panel == EditorPanel.LAYER) refreshLayerItems()"""
if "toolPanelHeightDp = 180f" not in s and "toolPanelHeightDp = if (panel == EditorPanel.TEXT2) 330f else 180f" not in s:
    if s.count(old) != 1:
        raise SystemExit(f"Expected one primary navigation open handler, found {s.count(old)}")
    s = s.replace(old, new, 1)

# Nested scrolling lets a swipe anywhere in the sheet expand it first. Once
# expanded, the content scrolls normally; downward swipes collapse only after
# the content has returned to its top. The bottom handle remains independently draggable.
nested_imports = [
    "import androidx.compose.ui.input.nestedscroll.NestedScrollConnection",
    "import androidx.compose.ui.input.nestedscroll.NestedScrollSource",
    "import androidx.compose.ui.input.nestedscroll.nestedScroll",
]
for statement in nested_imports:
    if statement not in s:
        anchor = "import androidx.compose.ui.input.pointer.pointerInput"
        if anchor not in s:
            raise SystemExit("Could not locate Compose pointer-input imports")
        s = s.replace(anchor, statement + "\n" + anchor, 1)

state_anchor = "    val toolPanelDensity = LocalDensity.current"
nested_state = """    val toolPanelScrollState = rememberScrollState()
    val toolPanelNestedScrollConnection = remember(toolPanelScrollState, toolPanelDensity) {
        object : NestedScrollConnection {
            override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
                val deltaDp = with(toolPanelDensity) { available.y.toDp().value }
                val currentHeight = toolPanelHeightDp
                if (deltaDp < 0f && currentHeight < 400f) {
                    val consumedDp = minOf(-deltaDp, 400f - currentHeight)
                    toolPanelHeightDp = currentHeight + consumedDp
                    return Offset(0f, with(toolPanelDensity) { (-consumedDp).dp.toPx() })
                }
                if (deltaDp > 0f && toolPanelScrollState.value == 0 && currentHeight > 150f) {
                    val consumedDp = minOf(deltaDp, currentHeight - 150f)
                    toolPanelHeightDp = currentHeight - consumedDp
                    return Offset(0f, with(toolPanelDensity) { consumedDp.dp.toPx() })
                }
                return Offset.Zero
            }
        }
    }"""
if "val toolPanelNestedScrollConnection" not in s:
    if s.count(state_anchor) != 1:
        raise SystemExit("Could not locate the unique tool panel density state")
    s = s.replace(state_anchor, state_anchor + "\n" + nested_state, 1)

# Keep the panel body clear of inner navigation-bar inset padding.
# The animated body excludes the separate 26dp drag handle; keep the header and
# useful content visible at every panel's initial height.
old_panel = 'Column(Modifier.fillMaxWidth().height(animatedToolPanelHeight).background(Color(0xFF181818)).navigationBarsPadding())'
new_panel = 'Column(Modifier.fillMaxWidth().height(animatedToolPanelHeight).background(Color(0xFF181818)).nestedScroll(toolPanelNestedScrollConnection))'
if old_panel in s:
    s = s.replace(old_panel, new_panel, 1)
elif new_panel not in s:
    raise SystemExit("Could not locate the Xingtu tool panel container for nested scrolling")

old_scroll = 'Column((if (activePanel == EditorPanel.TEXT2) Modifier.fillMaxWidth().weight(1f) else Modifier.fillMaxWidth().weight(1f).verticalScroll(rememberScrollState())).padding(horizontal = 13.dp, vertical = 6.dp))'
new_scroll = 'Column((if (activePanel == EditorPanel.TEXT2) Modifier.fillMaxWidth().weight(1f) else Modifier.fillMaxWidth().weight(1f).verticalScroll(toolPanelScrollState)).padding(horizontal = 13.dp, vertical = 4.dp))'

# The secondary-navigation/header row is also a dedicated drag surface. This
# keeps the primary dock separate while allowing gestures to begin directly on
# the secondary navigation instead of requiring a swipe in the content list.
header_drag = """.pointerInput(Unit) {
                            detectDragGestures { change, dragAmount ->
                                change.consume()
                                val deltaDp = with(toolPanelDensity) { dragAmount.y.toDp().value }
                                toolPanelHeightDp = (toolPanelHeightDp - deltaDp).coerceIn(150f, 400f)
                            }
                        }"""
# Match the actual outer tool-sheet header, not the inner Text2 tab strip.
# The latter also uses a 48dp Row but lives in Text2Panel, outside the
# ArticleEditorScreen scope where toolPanelDensity/toolPanelHeightDp exist.
# Match only the Modifier prefix of the actual outer tool-sheet header.
# The Text2 tab strip also has a 48dp Row, but its parameter order differs.
header_pattern = r'(Row\(Modifier\.fillMaxWidth\(\)\.height\(48\.dp\)\.padding\(horizontal = 9\.dp\))(?=,\s*verticalAlignment = Alignment\.CenterVertically, horizontalArrangement = Arrangement\.SpaceBetween\)\s*\{)'
if header_drag not in s:
    s, header_count = re.subn(header_pattern, r'\1' + header_drag + ',', s, count=1)
    if header_count != 1:
        raise SystemExit("Could not locate the outer tool-sheet header Modifier for direct swipe resizing")

if old_scroll in s:
    s = s.replace(old_scroll, new_scroll, 1)
elif new_scroll not in s:
    raise SystemExit("Could not locate the tool panel's independent content scroll container")

checks = {
    "single independent primary dock": s.count("height(50.dp)") >= 1 and s.count(dock_marker) == 0,
    "inline non-modal bottom sheet": "Box(Modifier.fillMaxSize(), contentAlignment = Alignment.BottomCenter)" in s,
    "panel initial heights": ("EditorPanel.TEXT -> 260f" in s and "EditorPanel.DOCUMENT -> 200f" in s) or "toolPanelHeightDp = if (panel == EditorPanel.TEXT2) 330f else 180f" in s,
    "secondary navigation drag surface": header_count == 1,
    "150dp collapsed minimum and 400dp maximum": "coerceIn(150f, 400f)" in s,
    "direct height update avoids opening rebound": "val animatedToolPanelHeight = toolPanelHeightDp.coerceIn(100f, 400f).dp" in s and "animateDpAsState" not in s,
    "nested swipe resizing": "toolPanelNestedScrollConnection" in s and ".nestedScroll(toolPanelNestedScrollConnection)" in s,
    "content scroll shares nested state": ".verticalScroll(toolPanelScrollState)" in s,
    "no inner navigation inset consuming initial height": new_panel in s,
    "bottom-center drag handle": handle_marker in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    ERROR.write_text("Xingtu bottom-sheet validation failed: " + ", ".join(failed) + "\\n", encoding="utf-8")
    raise SystemExit("Xingtu bottom-sheet validation failed: " + ", ".join(failed))

EDITOR.write_text(s, encoding="utf-8")
print("Xingtu bottom sheet fixed: panel-specific initial heights, secondary-navigation drag, nested content scroll, 400dp maximum, smooth animation and separate primary dock.")
