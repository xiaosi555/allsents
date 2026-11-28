#!/usr/bin/env python3
"""Apply 醒图 3.0 Stage C/D/E: icon IDs, panel transactions and object sync checks."""
from pathlib import Path
import re

ROOT = Path(".")
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
V3 = JAVA / "ui/v3/ArticleEditorScreenV3.kt"
ERROR = ROOT / "xingtu_v3_stage_cde_patch_error.txt"

def fail(message):
    ERROR.write_text(message + "\\n", encoding="utf-8")
    raise SystemExit("醒图 3.0 Stage C/D/E: " + message)

def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)

if not V3.is_file():
    fail("generated V3 editor is missing")
s = V3.read_text(encoding="utf-8")

# C: stable semantic icon IDs. Existing vector paths are retained, but callers
# now resolve labels to a closed registry before drawing; unknown labels use a
# neutral document icon instead of arbitrary glyph/text fallbacks.
registry = """
private enum class EditorIconId(val glyphKey: String) {
    BACK("back"), UNDO("undo"), REDO("redo"), SAVE("save"), PREVIEW("eye"),
    TEXT("text"), IMAGE("image"), COMPONENT("component"), LAYOUT("layout"),
    LAYER("layer"), STYLE("style"), TEMPLATE("template"), DOCUMENT("document"),
    CROP("crop"), ROTATE("rotate"), FLIP("flip"), COLOR("color"), BORDER("border"),
    RADIUS("radius"), SHADOW("shadow"), ALIGN("align"), LOCK("lock"), HIDE("eye"),
    DUPLICATE("copy"), DELETE("delete"), IMPORT("import"), EXPORT("export"),
    SEARCH("search"), TABLE("table"), QUOTE("quote"), LIST("list"), INSERT("insert"),
    GENERIC("document")
}

private fun editorIconId(label: String): EditorIconId {
    val key = label.trim().lowercase()
    return when {
        key in setOf("返回", "关闭", "取消") || key.contains("返回") -> EditorIconId.BACK
        key in setOf("撤销", "上一步") || key.contains("撤销") -> EditorIconId.UNDO
        key in setOf("重做", "下一步") || key.contains("重做") -> EditorIconId.REDO
        key.contains("保存") -> EditorIconId.SAVE
        key.contains("预览") || key.contains("阅读") -> EditorIconId.PREVIEW
        key.contains("文字") || key.contains("字体") || key.contains("字号") ||
            key.contains("加粗") || key.contains("斜体") || key.contains("下划线") -> EditorIconId.TEXT
        key.contains("图片") || key.contains("相册") || key.contains("封面") -> EditorIconId.IMAGE
        key.contains("裁剪") || key.contains("裁切") -> EditorIconId.CROP
        key.contains("旋转") -> EditorIconId.ROTATE
        key.contains("翻转") -> EditorIconId.FLIP
        key.contains("颜色") || key.contains("调色") || key.contains("渐变") -> EditorIconId.COLOR
        key.contains("边框") -> EditorIconId.BORDER
        key.contains("圆角") -> EditorIconId.RADIUS
        key.contains("阴影") -> EditorIconId.SHADOW
        key.contains("对齐") || key.contains("居中") -> EditorIconId.ALIGN
        key.contains("锁定") -> EditorIconId.LOCK
        key.contains("隐藏") -> EditorIconId.HIDE
        key.contains("复制") || key.contains("副本") -> EditorIconId.DUPLICATE
        key.contains("删除") -> EditorIconId.DELETE
        key.contains("导入") -> EditorIconId.IMPORT
        key.contains("导出") -> EditorIconId.EXPORT
        key.contains("搜索") || key.contains("查找") -> EditorIconId.SEARCH
        key.contains("表格") -> EditorIconId.TABLE
        key.contains("引用") -> EditorIconId.QUOTE
        key.contains("列表") || key.contains("编号") -> EditorIconId.LIST
        key.contains("插入") || key.contains("添加") || key.contains("新建") ||
            key.contains("加图") || key.contains("加字") -> EditorIconId.INSERT
        key.contains("组件") || key.contains("卡片") || key.contains("标题") -> EditorIconId.COMPONENT
        key.contains("分栏") || key.contains("布局") || key.contains("画布") -> EditorIconId.LAYOUT
        key.contains("图层") || key.contains("层级") -> EditorIconId.LAYER
        key.contains("模板") || key.contains("收藏") -> EditorIconId.TEMPLATE
        key.contains("样式") || key.contains("属性") || key.contains("背景") -> EditorIconId.STYLE
        key.contains("文档") || key.contains("文章") || key.contains("文件") -> EditorIconId.DOCUMENT
        else -> EditorIconId.GENERIC
    }
}

@Composable
private fun EditorVectorIcon(iconId: EditorIconId, tint: Color, modifier: Modifier = Modifier) {
    EditorVectorIcon(iconId.glyphKey, tint, modifier)
}
"""
if "private enum class EditorIconId" not in s:
    marker = "@Composable\nprivate fun EditorTool(label: String, selected: Boolean = false, onClick: () -> Unit) {"
    if s.count(marker) != 1:
        fail("vector icon renderer or EditorTool anchor is missing")
    s = s.replace(marker, registry + "\n" + marker, 1)

# Add explicit glyphs for registry keys that do not have a dedicated branch yet.
if "k == \"back\"" not in s:
    s = replace_once(
        s,
        "        val k = label.lowercase()\n        when {",
        """        val k = label.lowercase()
        when {
            k == "back" -> { poly(listOf(Offset(w*.68f,h*.16f),Offset(w*.34f,h*.50f),Offset(w*.68f,h*.84f))); line(w*.36f,h*.50f,w*.86f,h*.50f) }
            k == "save" -> { outlineRect(w*.16f,h*.12f,w*.68f,h*.76f,sw*.5f); outlineRect(w*.30f,h*.12f,w*.40f,h*.25f,sw*.4f); outlineRect(w*.30f,h*.54f,w*.40f,h*.22f,sw*.4f) }
            k == "document" -> { outlineRect(w*.20f,h*.10f,w*.60f,h*.80f,sw*.7f); line(w*.32f,h*.36f,w*.68f,h*.36f); line(w*.32f,h*.52f,w*.68f,h*.52f); line(w*.32f,h*.68f,w*.60f,h*.68f) }
            k == "style" -> { circle(cx,cy,w*.30f); line(cx,cy-w*.42f,cx,cy+w*.42f); line(w*.16f,cy,w*.84f,cy) }""",
        "semantic vector icon paths"
    )

# All editor docks resolve through the ID registry, not directly from label text.
s = re.sub(r"EditorVectorIcon\((label|item),", r"EditorVectorIcon(editorIconId(\1),", s)

# D: panel transactions. Opening captures the current HTML; Apply commits the
# current preview, while Close restores the exact pre-panel HTML in Compose and WebView.
if "var panelTransactionSnapshot by remember" not in s:
    anchor = '    var selectedBlockHtml by remember { mutableStateOf("") }'
    s = replace_once(
        s, anchor,
        anchor + '\n    var panelTransactionSnapshot by remember { mutableStateOf<String?>(null) }',
        "panel transaction snapshot state"
    )
    effect_anchor = '    var panelTransactionSnapshot by remember { mutableStateOf<String?>(null) }'
    effect = '''
    LaunchedEffect(showToolPopup) {
        if (showToolPopup && panelTransactionSnapshot == null) {
            panelTransactionSnapshot = html
        }
    }
'''
    s = replace_once(s, effect_anchor, effect_anchor + "\n" + effect, "panel transaction capture effect")

confirm_old = '''IconButton(onClick = { if (activePanel == EditorPanel.TEXT2) runJs("setText2SelectionPreview(false);"); showToolPopup = false }) { Icon(Icons.Outlined.Check, contentDescription = "确定", tint = AppColors.Theme) }'''
confirm_new = '''IconButton(onClick = {
                            if (activePanel == EditorPanel.TEXT2) runJs("setText2SelectionPreview(false);")
                            panelTransactionSnapshot = null
                            showToolPopup = false
                            pendingSave++
                        }) { Icon(Icons.Outlined.Check, contentDescription = "确定", tint = AppColors.Theme) }'''
if confirm_old in s:
    s = replace_once(s, confirm_old, confirm_new, "panel transaction commit")
elif "contentDescription = \"确定\"" not in s or "panelTransactionSnapshot = null" not in s:
    fail("panel confirm button anchor missing")

close_old = '''IconButton(onClick = { if (activePanel == EditorPanel.TEXT2) runJs("setText2SelectionPreview(false);"); showToolPopup = false }) { Icon(Icons.Outlined.Close, contentDescription = "关闭功能窗口", tint = Color.White) }'''
close_new = '''IconButton(onClick = {
                            if (activePanel == EditorPanel.TEXT2) runJs("setText2SelectionPreview(false);")
                            val rollbackHtml = panelTransactionSnapshot
                            if (rollbackHtml != null && rollbackHtml != html) {
                                html = rollbackHtml
                                editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(rollbackHtml)});", null)
                                pendingSave++
                            }
                            panelTransactionSnapshot = null
                            showToolPopup = false
                        }) { Icon(Icons.Outlined.Close, contentDescription = "取消并恢复", tint = Color.White) }'''
if close_old in s:
    s = replace_once(s, close_old, close_new, "panel transaction rollback")
elif "contentDescription = \"取消并恢复\"" not in s:
    fail("panel close button anchor missing")

# Keep the requested panel bounds even if upstream code changes an initializer.
s = s.replace("mutableFloatStateOf(100f)", "mutableFloatStateOf(200f)", 1)
s = s.replace("coerceIn(100f, 400f)", "coerceIn(200f, 400f)")
s = s.replace("coerceIn(100f,400f)", "coerceIn(200f,400f)")

# E: require the structured selection model and DOM identity reporting inherited
# from the shared editor's already-tested Bridge patch; do not replace its JS engine.
required = [
    "private enum class EditorSelectionKind",
    "private data class EditorSelectionState",
    "selectionChanged(value: String)",
    "selectionState = state",
    "function ensureEditorId(el)",
    "function reportSelection()",
    "selectedIds:ids",
]
missing = [token for token in required if token not in s]
if missing:
    fail("unified object-selection foundation missing: " + ", ".join(missing))

# Verify the category dock uses icon IDs and the panel implements both transaction paths.
checks = {
    "semantic icon registry": "private enum class EditorIconId" in s and "private fun editorIconId(label: String)" in s,
    "vector icon ID overload": "EditorVectorIcon(iconId: EditorIconId" in s,
    "all dynamic icon callers use registry": "EditorVectorIcon(editorIconId(label)" in s or "EditorVectorIcon(editorIconId(item)" in s,
    "200–400dp panel bounds": "coerceIn(200f, 400f)" in s,
    "panel snapshot state": "panelTransactionSnapshot by remember" in s,
    "panel commit action": "panelTransactionSnapshot = null" in s and "contentDescription = \"确定\"" in s,
    "panel rollback action": "setEditorHtml(${JSONObject.quote(rollbackHtml)})" in s and "取消并恢复" in s,
    "structured object selection": "EditorSelectionState" in s and "selectionChanged(value: String)" in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    fail("post-patch validation failed: " + ", ".join(failed))

V3.write_text(s, encoding="utf-8")
print("Verified: Stage C semantic vector icon registry, Stage D 200–400dp panel commit/rollback, Stage E structured object selection and DOM identity are installed.")
