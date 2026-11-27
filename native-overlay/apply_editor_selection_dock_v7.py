#!/usr/bin/env python3
"""Object-specific text/image docks with one-purpose dialogs."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "editor_selection_dock_v7_patch_error.txt"
s = EDITOR.read_text(encoding="utf-8")
def once(old, new, label):
    global s
    if new in s:
        return
    n = s.count(old)
    if n != 1:
        ERROR.write_text(f"{label}: expected 1, found {n}\n", encoding="utf-8")
        raise SystemExit(f"v7 anchor mismatch [{label}]: {n}")
    s = s.replace(old, new, 1)

once(
'    var imageRadius by remember { mutableFloatStateOf(0f) }',
'''    var imageRadius by remember { mutableFloatStateOf(0f) }
    var textOpacity by remember { mutableFloatStateOf(100f) }
    var activeObjectDialog by remember { mutableStateOf("") }''',
"dialog state")

once(
"function styleSelectedParagraph(prop,value){restoreSelection();const e=selectedParagraph();if(!e)return;e.style[prop]=value;commitHistory();NativeEditor.changed(root.innerHTML);}",
"""function styleSelectedParagraph(prop,value){restoreSelection();const e=activeTextBlock||selectedParagraph();if(!e||e.dataset.editorLocked==='1')return;e.style[prop]=value;commitHistory();NativeEditor.changed(root.innerHTML);}
                            function previewSelectedTextOpacity(v){const e=activeTextBlock||selectedParagraph();if(!e||e.dataset.editorLocked==='1')return;e.style.opacity=String(Math.max(0,Math.min(100,Number(v)))/100);}
                            function commitSelectedTextOpacity(){const e=activeTextBlock||selectedParagraph();if(!e||e.dataset.editorLocked==='1')return;commitHistory();NativeEditor.changed(root.innerHTML);}""",
"text opacity preview")

# Existing v2/v3 image action functions are retained and receive lock guards below.
def guard_image_function(name):
    global s
    pattern = re.compile(r"(function " + re.escape(name) + r"\\([^)]*\\)\\{)")
    match = pattern.search(s)
    if not match:
        raise SystemExit("Could not locate image handler " + name)
    body = s[match.end():match.end()+420]
    if "activeImage.dataset.editorLocked==='1'" in body:
        return
    if body.startswith("if(!activeImage)return;"):
        old_guard = "if(!activeImage)return;"
        s = s[:match.end()] + "if(!activeImage||activeImage.dataset.editorLocked==='1')return;" + s[match.end()+len(old_guard):]
    else:
        s = s[:match.end()] + "if(!activeImage||activeImage.dataset.editorLocked==='1')return;" + s[match.end():]

for name in [
    "setSelectedImageBorder", "setSelectedImageOpacity", "setSelectedImageShadow",
    "flipSelectedImage", "alignSelectedImage", "setSelectedImageAsBackground",
    "setSelectedImageWidth", "setSelectedImageObjectPosition", "rotateSelectedImage",
    "setSelectedImageRadius", "cropSelectedImage", "resetSelectedImageCrop",
    "replaceSelectedImage", "deleteSelectedImage", "setSelectedImageAlt",
    "commitSelectedImageStyle"
]:
    guard_image_function(name)

constAnchor = "@Composable\nprivate fun EditorTool(label: String, selected: Boolean = false, onClick: () -> Unit) {"
helper = """@Composable
private fun SelectionDockItem(label: String, glyph: String, onClick: () -> Unit) {
    Column(
        modifier = Modifier.width(62.dp).height(52.dp).clip(RoundedCornerShape(8.dp))
            .clickable(onClick = onClick).padding(horizontal = 2.dp, vertical = 3.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(glyph, color = AppColors.TextMain, fontSize = 19.sp, lineHeight = 21.sp, fontWeight = FontWeight.Medium)
        Text(label, color = AppColors.TextMain, fontSize = 9.sp, maxLines = 1, softWrap = false, overflow = TextOverflow.Ellipsis)
    }
}

"""
once(constAnchor, helper + constAnchor, "selection dock composable")

floating_old = 'if (!previewMode && (floatingToolbarRequest.isNotBlank() || selectedImageHtml.isNotBlank() || selectedTextActive || selectedBlockHtml.isNotBlank() ||'
floating_new = 'if (!previewMode && (floatingToolbarRequest.isNotBlank() || selectedBlockHtml.isNotBlank() ||'
if floating_old in s:
    s = s.replace(floating_old, floating_new, 1)
elif floating_new not in s:
    raise SystemExit("floating toolbar selection anchor missing")

rowAnchor = "Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 4.dp),"
rs = s.find(rowAnchor)
if rs < 0: raise SystemExit("v7 cannot find primary horizontal dock")
ob = s.find("{", rs)
depth = 0
cb = -1
for i in range(ob, len(s)):
    if s[i] == "{": depth += 1
    elif s[i] == "}":
        depth -= 1
        if depth == 0:
            cb = i
            break
if cb < 0: raise SystemExit("v7 cannot balance primary dock row")
defaultBody = s[ob+1:cb]
defaultBody = defaultBody.replace(
    'Text(item, color = if (item in listOf("编辑", "字体", "样式", "排版", "透明度", "加图", "加字")) AppColors.Theme else Color(0xFFDDDDDD), fontSize = 11.sp, maxLines = 1)',
    '''Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                                    Text(editorToolGlyph(item), color = Color(0xFFDDDDDD), fontSize = 18.sp, lineHeight = 20.sp)
                                    Text(item, color = if (item in listOf("编辑", "字体", "样式", "排版", "透明度", "加图", "加字")) AppColors.Theme else Color(0xFFDDDDDD), fontSize = 9.sp, maxLines = 1)
                                }'''
)
body = r"""
                    if (selectedTextActive || selectedDockMode == "TEXT") {
                        listOf(
                            Triple("编辑", "✎", "edit"), Triple("字体", "A", "font"),
                            Triple("样式", "◈", "style"), Triple("排版", "≡", "layout"),
                            Triple("透明度", "◐", "text-opacity"), Triple("存为模板", "☆", "save-template"),
                            Triple("顺序", "↕", "order"), Triple("对齐", "☷", "text-align"),
                            Triple("创建副本", "▣", "duplicate"), Triple("复制", "▢", "copy"),
                            Triple("复制样式", "◩", "copy-style"), Triple("粘贴", "▤", "paste"),
                            Triple("多选", "⊞", "multi"), Triple("锁定", "▣", "lock")
                        ).forEach { (label, glyph, action) ->
                            SelectionDockItem(label, glyph) {
                                when (action) {
                                    "edit" -> {
                                        runJs("setText2SelectionPreview(false);enableSelectedTextEditing()")
                                        editor?.let { target ->
                                            target.requestFocus()
                                            target.post {
                                                val imm = context.getSystemService(Context.INPUT_METHOD_SERVICE) as? android.view.inputmethod.InputMethodManager
                                                imm?.showSoftInput(target, android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT)
                                            }
                                        }
                                    }
                                    "font", "style", "layout", "text-opacity" -> {
                                        text2MainTab = when (action) { "font" -> "字体"; "style" -> "样式"; "layout" -> "排版"; else -> "透明度" }
                                        activePanel = EditorPanel.TEXT2
                                        showToolPopup = true
                                        showCanvasPopup = false
                                        toolPanelHeightDp = 200f
                                        runJs("setText2SelectionPreview(true);")
                                    }
                                    "text-align" -> activeObjectDialog = action
                                    "save-template" -> editor?.evaluateJavascript("selectedObjectHtml()") { raw ->
                                        val saved = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull().orEmpty()
                                        if (saved.isNotBlank()) {
                                            vm.saveStyle(StyleModule(vm.newId(), "文字模板", "文字模板", saved, System.currentTimeMillis().toString(), type = "text", isFavorite = true))
                                            vm.toast("已保存到图文收藏")
                                        } else vm.toast("请先选择文字段落")
                                    }
                                    "order" -> { floatingToolbarRequest = "component"; floatingMenu = "" }
                                    "duplicate" -> runJs("duplicateSelectedTextParagraph()")
                                    "copy" -> runJs("copySelectedTextBlock()")
                                    "copy-style" -> runJs("copySelectedTextStyle()")
                                    "paste" -> runJs("pasteTextClipboard()")
                                    "multi" -> { multiSelectMode = !multiSelectMode; runJs("setMultiSelectMode(${multiSelectMode})") }
                                    "lock" -> runJs("toggleSelectedObjectLock()")
                                }
                            }
                        }
                    } else if (selectedImageHtml.isNotBlank() || selectedDockMode == "IMAGE") {
                        listOf(
                            Triple("替换", "↻", "image-replace"), Triple("裁剪", "⛶", "crop"),
                            Triple("调色", "◒", "color"), Triple("透明度", "◐", "image-opacity"),
                            Triple("边框", "▣", "border"), Triple("圆角", "◔", "radius"),
                            Triple("阴影", "◌", "shadow"), Triple("翻转", "⇋", "flip"),
                            Triple("对齐", "☷", "image-align"), Triple("复制", "▢", "image-copy"),
                            Triple("复制样式", "◩", "image-copy-style"), Triple("粘贴", "▤", "image-paste"),
                            Triple("设为背景图", "▧", "background")
                        ).forEach { (label, glyph, action) ->
                            SelectionDockItem(label, glyph) {
                                when (action) {
                                    "image-copy" -> runJs("copySelectedImageObject()")
                                    "image-copy-style" -> runJs("copySelectedImageStyle()")
                                    "image-paste" -> runJs("pasteImageClipboard()")
                                    else -> activeObjectDialog = action
                                }
                            }
                        }
                    } else {
""" + defaultBody + """
                    }
"""
s = s[:ob+1] + body + s[cb:]

dialogAnchor = "    if (showBlockProperties) {"
dialog = r'''
    if (activeObjectDialog.isNotBlank()) {
        Dialog(onDismissRequest = { activeObjectDialog = "" }) {
            Surface(Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp), color = Color(0xFF242424), shadowElevation = 18.dp) {
                Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 15.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text(when (activeObjectDialog) {
                            "font" -> "字体"; "style" -> "文字样式"; "layout" -> "文字排版"
                            "text-opacity" -> "文字透明度"; "text-align" -> "文字对齐"
                            "image-replace" -> "替换图片"; "crop" -> "图片裁剪"; "color" -> "图片调色"
                            "image-opacity" -> "图片透明度"; "border" -> "图片边框"; "radius" -> "图片圆角"
                            "shadow" -> "图片阴影"; "flip" -> "图片翻转"; "image-align" -> "图片对齐"
                            "background" -> "设为背景图"; else -> "编辑"
                        }, color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                        IconButton(onClick = { activeObjectDialog = "" }) { Icon(Icons.Outlined.Close, contentDescription = "关闭", tint = Color.LightGray) }
                    }
                    when (activeObjectDialog) {
                        "font" -> {
                            Text("字号", color = Color.LightGray, fontSize = 12.sp)
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                                listOf("14", "16", "18", "20", "24", "28", "32").forEach { size ->
                                    TextButton(onClick = { runJs("styleSelectionOrParagraph('fontSize','${size}px')") }) { Text(size, color = Color.White) }
                                }
                            }
                            listOf("PingFang SC" to "苹方", "Microsoft YaHei" to "微软雅黑", "SimSun" to "宋体", "SimHei" to "黑体", "KaiTi" to "楷体").forEach { (font, name) ->
                                TextButton(onClick = { runJs("styleSelectionOrParagraph('fontFamily',${JSONObject.quote(font)})"); activeObjectDialog = "" }) { Text(name, color = Color.White) }
                            }
                        }
                        "style" -> {
                            listOf("加粗" to "fontWeight", "斜体" to "fontStyle", "下划线" to "textDecoration").forEach { (label, prop) ->
                                TextButton(onClick = { when (prop) {
                                    "fontWeight" -> runJs("styleSelectionOrParagraph('fontWeight','bold')")
                                    "fontStyle" -> runJs("styleSelectionOrParagraph('fontStyle','italic')")
                                    else -> runJs("styleSelectionOrParagraph('textDecoration','underline')")
                                } }) { Text(label, color = Color.White) }
                            }
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                listOf("#222222", "#666666", "#159765", "#C84B4B", "#3978B7", "#D69A35").forEach { hex ->
                                    Box(Modifier.size(28.dp).clip(CircleShape).background(Color(android.graphics.Color.parseColor(hex))).clickable { runJs("styleSelectionOrParagraph('color','$hex')") })
                                }
                            }
                        }
                        "layout", "text-align" -> {
                            listOf("左对齐" to "left", "居中" to "center", "右对齐" to "right", "两端对齐" to "justify").forEach { (label, value) ->
                                TextButton(onClick = { runJs("styleSelectedParagraph('textAlign','$value')"); if (activeObjectDialog == "text-align") activeObjectDialog = "" }) { Text(label, color = Color.White) }
                            }
                            if (activeObjectDialog == "layout") listOf("行距 1.6" to "1.6", "行距 1.8" to "1.8", "行距 2.0" to "2").forEach { (label, value) ->
                                TextButton(onClick = { runJs("styleSelectedParagraph('lineHeight','$value')") }) { Text(label, color = Color.White) }
                            }
                        }
                        "text-opacity" -> {
                            Text("透明度 ${textOpacity.toInt()}%", color = Color.LightGray, fontSize = 12.sp)
                            Slider(value = textOpacity, onValueChange = { textOpacity = it; runJs("previewSelectedTextOpacity($it)") }, onValueChangeFinished = { runJs("commitSelectedTextOpacity()") }, valueRange = 0f..100f)
                        }
                        "image-replace" -> {
                            Text("选择本地图片替换当前图片", color = Color.LightGray, fontSize = 12.sp)
                            TextButton(onClick = { activeObjectDialog = ""; imageReplacementPicker.launch(arrayOf("image/*")) }) { Text("从相册选择", color = AppColors.Theme) }
                        }
                        "crop" -> {
                            listOf("1:1", "4:3", "16:9").forEach { ratio -> TextButton(onClick = { runJs("cropSelectedImage('$ratio')"); activeObjectDialog = "" }) { Text("裁剪为 $ratio", color = Color.White) } }
                            TextButton(onClick = { runJs("resetSelectedImageCrop()"); activeObjectDialog = "" }) { Text("恢复原始比例", color = Color.LightGray) }
                        }
                        "color" -> {
                            Text("亮度 ${imageBrightness.toInt()}%", color = Color.LightGray, fontSize = 12.sp)
                            Slider(value = imageBrightness, onValueChange = { imageBrightness = it; runJs("previewSelectedImageFilters($it,$imageContrast,$imageSaturation)") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..200f)
                            Text("对比度 ${imageContrast.toInt()}%", color = Color.LightGray, fontSize = 12.sp)
                            Slider(value = imageContrast, onValueChange = { imageContrast = it; runJs("previewSelectedImageFilters($imageBrightness,$it,$imageSaturation)") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..200f)
                            Text("饱和度 ${imageSaturation.toInt()}%", color = Color.LightGray, fontSize = 12.sp)
                            Slider(value = imageSaturation, onValueChange = { imageSaturation = it; runJs("previewSelectedImageFilters($imageBrightness,$imageContrast,$it)") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..200f)
                        }
                        "image-opacity" -> {
                            Text("透明度 ${imageOpacity.toInt()}%", color = Color.LightGray, fontSize = 12.sp)
                            Slider(value = imageOpacity, onValueChange = { imageOpacity = it; runJs("previewSelectedImageOpacity($it)") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..100f)
                        }
                        "radius" -> {
                            Text("圆角 ${imageRadius.toInt()}px", color = Color.LightGray, fontSize = 12.sp)
                            Slider(value = imageRadius, onValueChange = { imageRadius = it; runJs("previewSelectedImageRadius('${it}px')") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..40f)
                            TextButton(onClick = { imageRadius = 0f; runJs("previewSelectedImageRadius('0px');commitSelectedImageStyle()") }) { Text("直角", color = AppColors.Theme) }
                        }
                        "border" -> listOf("无边框" to "0", "细边框" to "1px solid #dfe5e1", "主题色边框" to "2px solid #159765").forEach { (label, value) ->
                            TextButton(onClick = { runJs("setSelectedImageBorder('$value')"); activeObjectDialog = "" }) { Text(label, color = Color.White) }
                        }
                        "shadow" -> listOf("无阴影" to "none", "轻阴影" to "0 2px 6px rgba(0,0,0,.14)", "中阴影" to "0 4px 14px rgba(0,0,0,.22)", "强阴影" to "0 8px 24px rgba(0,0,0,.28)").forEach { (label, value) ->
                            TextButton(onClick = { runJs("setSelectedImageShadow(${JSONObject.quote(value)})"); activeObjectDialog = "" }) { Text(label, color = Color.White) }
                        }
                        "flip" -> {
                            TextButton(onClick = { runJs("flipSelectedImage('horizontal')") }) { Text("水平翻转", color = Color.White) }
                            TextButton(onClick = { runJs("flipSelectedImage('vertical')") }) { Text("垂直翻转", color = Color.White) }
                        }
                        "image-align" -> listOf("左对齐" to "left", "居中" to "center", "右对齐" to "right").forEach { (label, value) ->
                            TextButton(onClick = { runJs("alignSelectedImage('$value')"); activeObjectDialog = "" }) { Text(label, color = Color.White) }
                        }
                        "background" -> {
                            Text("将图片转换为段落背景图", color = Color.LightGray, fontSize = 12.sp)
                            TextButton(onClick = { runJs("setSelectedImageAsBackground()"); activeObjectDialog = "" }) { Text("设为背景图", color = AppColors.Theme) }
                        }
                    }
                }
            }
        }
    }

'''
once(dialogAnchor, dialog + dialogAnchor, "separate text and image dialogs")

required = [
    'Triple("编辑", "✎", "edit")', 'Triple("锁定", "▣", "lock")',
    'Triple("替换", "↻", "image-replace")', 'Triple("圆角", "◔", "radius")',
    'Triple("设为背景图", "▧", "background")', 'function previewSelectedTextOpacity(v)',
    'function setSelectedImageShadow(v)', 'function setSelectedImageAsBackground()'
]
missing = [x for x in required if x not in s]
if missing:
    ERROR.write_text("Missing v7 features: " + ", ".join(missing) + "\n", encoding="utf-8")
    raise SystemExit("v7 validation failed: " + ", ".join(missing))
EDITOR.write_text(s, encoding="utf-8")
print("Selection dock v7 applied.")
