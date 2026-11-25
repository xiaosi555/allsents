#!/usr/bin/env python3
"""Stage C2: make the article editor selection toolbar coordinate- and IME-aware,
and improve the persistent bottom category dock without removing any tool entry.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "article_editor_stage_c2_patch_error.txt"


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        detail = f"Stage C2 patch anchor mismatch [{label}]: expected 1, found {count}"
        ERROR.write_text(detail + "\n", encoding="utf-8")
        raise SystemExit(detail)
    print("Stage C2 applied:", label)
    return source.replace(old, new, 1)


if not EDITOR.is_file():
    raise SystemExit(f"Stage C2 target missing: {EDITOR}")

s = EDITOR.read_text(encoding="utf-8")

s = replace_once(
    s,
    '''private enum class EditorPanel(val label: String) {
    TEXT("文字"), TITLE("标题"), IMAGE("图片"), LAYOUT("布局"), CARD("卡片"), COMPONENT("组件"), SVG("SVG"), LAYER("图层"), STYLE("图文收藏"), TEMPLATE("图文模板"), DOCUMENT("文档"), CANVAS("画布")
}''',
    '''private enum class EditorPanel(val label: String, val icon: String) {
    TEXT("文字", "Aa"), TITLE("标题", "T"), IMAGE("图片", "▧"), LAYOUT("布局", "▦"),
    CARD("卡片", "▣"), COMPONENT("组件", "▤"), SVG("SVG", "✧"), LAYER("图层", "▥"),
    STYLE("图文收藏", "☆"), TEMPLATE("图文模板", "▩"), DOCUMENT("文档", "≡"),
    CANVAS("画布", "▧")
}''',
    "add compact visual identifiers to all twelve tool categories"
)

s = replace_once(
    s,
    '''                    EditorTool(panel.label, activePanel == panel) { activePanel = panel; floatingMenu = "" }''',
    '''                    EditorTool("${panel.icon}  ${panel.label}", activePanel == panel) { activePanel = panel; floatingMenu = "" }''',
    "show category identifiers in the relocated top navigation without changing category actions"
)

s = replace_once(
    s,
    '''                val toolbarHeight = 88.dp
                val selectedTop = selectionState.y.dp
                val floatingY = if (selectedTop > maxHeight * 0.56f) {
                    (selectedTop - toolbarHeight - 8.dp).coerceAtLeast(8.dp)
                } else {
                    (selectedTop + selectionState.height.dp + 10.dp).coerceAtMost((maxHeight - toolbarHeight).coerceAtLeast(8.dp))
                }''',
    '''                // With the editor viewport set to device-width, WebView CSS px map to
                // Compose dp. Do not divide by display density a second time.
                // WindowInsets.ime is physical px, so only the inset is converted.
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
    "convert WebView selection coordinates to dp and avoid keyboard and canvas edges"
)

# Keep the bottom category dock permanently present while selection tools float above the canvas.
# Stage B already changes the visibility guard; fail loudly if the foundation is not applied.
if "if (!previewMode) {" not in s:
    raise SystemExit("Stage C2 requires the Stage B persistent bottom dock patch")
if "EditorPanel.values().filter { it != EditorPanel.CANVAS }.forEach" not in s:
    raise SystemExit("Stage C2 top-level category navigation anchor missing")

required = [
    'private enum class EditorPanel(val label: String, val icon: String)',
    'WindowInsets.ime.getBottom(this).toDp()',
    'val selectionTopDp = selectionState.y.dp',
    'val selectionHeightDp = selectionState.height.dp',
    'EditorTool("${panel.icon}  ${panel.label}"',
    'EditorPanel.values().filter { it != EditorPanel.CANVAS }.forEach',
    'if (!previewMode) {'
]
missing = [item for item in required if item not in s]
if missing:
    ERROR.write_text("Stage C2 validation failed: " + ", ".join(missing) + "\n", encoding="utf-8")
    raise SystemExit("Stage C2 validation failed: " + ", ".join(missing))

EDITOR.write_text(s, encoding="utf-8")
print("Stage C2 validation passed: coordinate conversion, IME boundary, twelve category labels and persistent dock.")
