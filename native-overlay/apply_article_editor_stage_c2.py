#!/usr/bin/env python3
"""Stage C2: keep selection tools IME-safe and validate the bottom tool sheet
plus the separate draggable Canvas-tools dialog. The article canvas itself
remains the normal central editing surface.
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

s = replace_once(
    s,
    """                    Modifier.fillMaxWidth().height(50.dp)
                        .background(Color(0xFF181818)),""",
    """                    Modifier.fillMaxWidth().height(50.dp)
                        .align(Alignment.BottomCenter)
                        .background(Color(0xFF181818)),""",
    "anchor bottom-level category dock to the canvas bottom"
)

required = [
    "modifier = Modifier.fillMaxSize()",
    "Dialog(onDismissRequest = { showCanvasPopup = false })",
    "detectDragGestures",
    "Text(\"画布工具\"",
    "heightIn(min = 100.dp, max = 300.dp)",
    "CompositionLocalProvider(LocalEditorToolDark provides true)",
    "EditorPanel.values().forEach { panel ->",
    "height(50.dp)",
    "WindowInsets.ime.getBottom(this).toDp()",
    "val selectionTopDp = selectionState.y.dp",
    "if (!previewMode) {",
]
missing = [item for item in required if item not in s]
if missing:
    ERROR.write_text("Stage C2 validation failed: " + ", ".join(missing) + "\\n", encoding="utf-8")
    raise SystemExit("Stage C2 validation failed: " + ", ".join(missing))

EDITOR.write_text(s, encoding="utf-8")
print("Stage C2 validation passed: draggable Canvas-tools dialog, adaptive bottom tool sheet, fixed bottom category dock and IME-safe selection toolbar.")
