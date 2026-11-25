#!/usr/bin/env python3
"""Stage C2: keep the editor's floating selection toolbar within the visible
canvas/IME-safe area. The category dock is now authored at the bottom of the
editor panel and the canvas has its own draggable floating-window title bar.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "article_editor_stage_c2_patch_error.txt"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        detail = f"Stage C2 patch anchor mismatch [{label}]: expected 1, found {count}"
        ERROR.write_text(detail + "\\n", encoding="utf-8")
        raise SystemExit(detail)
    print("Stage C2 applied:", label)
    return source.replace(old, new, 1)


if not EDITOR.is_file():
    raise SystemExit(f"Stage C2 target missing: {EDITOR}")

s = EDITOR.read_text(encoding="utf-8")

s = replace_once(
    s,
    '''                val toolbarHeight = 88.dp
                val selectedTop = selectionState.y.dp
                val floatingY = if (selectedTop > maxHeight * 0.56f) {
                    (selectedTop - toolbarHeight - 8.dp).coerceAtLeast(8.dp)
                } else {
                    (selectedTop + selectionState.height.dp + 10.dp).coerceAtMost((maxHeight - toolbarHeight).coerceAtLeast(8.dp))
                }''',
    '''                // WebView selection coordinates are CSS px at device viewport scale.
                // Convert only the IME inset; do not density-convert selection coordinates twice.
                val density = LocalDensity.current
                val toolbarHeight = 96.dp
                val selectionTopDp = selectionState.y.dp
                val selectionHeightDp = selectionState.height.dp
                val imeBottomDp = with(density) { WindowInsets.ime.getBottom(this).toDp() }
                val safeCanvasBottom = (maxHeight - imeBottomDp).coerceAtLeast(0.dp)
                val maxToolbarTop = (safeCanvasBottom - toolbarHeight - 8.dp).coerceAtLeast(8.dp)
                val belowSelection = selectionTopDp + selectionHeightDp + 10.dp
                val aboveSelection = selectionTopDp - toolbarHeight - 10.dp
                val roomBelow = safeCanvasBottom - belowSelection
                val placeBelow = roomBelow >= toolbarHeight || selectionTopDp < toolbarHeight + 12.dp
                val floatingY = if (placeBelow) {
                    belowSelection.coerceIn(8.dp, maxToolbarTop)
                } else {
                    aboveSelection.coerceIn(8.dp, maxToolbarTop)
                }''',
    "keep selection toolbar inside canvas and above the keyboard"
)

required = [
    "Modifier.width(canvasWindowWidth).height(canvasWindowHeight)",
    "detectDragGestures",
    "按住标题栏拖动",
    "CompositionLocalProvider(LocalEditorToolDark provides true)",
    "EditorPanel.values().forEach { panel ->",
    "height(50.dp)",
    "height(115.dp)",
    "WindowInsets.ime.getBottom(this).toDp()",
    "val selectionTopDp = selectionState.y.dp",
    "if (!previewMode) {",
]
missing = [item for item in required if item not in s]
if missing:
    ERROR.write_text("Stage C2 validation failed: " + ", ".join(missing) + "\\n", encoding="utf-8")
    raise SystemExit("Stage C2 validation failed: " + ", ".join(missing))

EDITOR.write_text(s, encoding="utf-8")
print("Stage C2 validation passed: draggable canvas window, layout-style bottom dock and IME-safe selection toolbar.")
