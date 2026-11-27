#!/usr/bin/env python3
"""Give each selected-image dock action its own dedicated dialog."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "image_action_dialogs_patch_error.txt"
if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")
s = EDITOR.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        ERROR.write_text(f"{label}: expected one anchor, found {count}\n", encoding="utf-8")
        raise SystemExit(f"Image action dialog patch anchor mismatch [{label}]: {count}")
    s = s.replace(old, new, 1)
    print("Image dialog patch:", label)

state_anchor = '    var selectedDockMode by remember { mutableStateOf("DEFAULT") }'
state_new = state_anchor + '\n    var activeImageDialog by remember { mutableStateOf("") }'
if state_new not in s:
    replace_once(state_anchor, state_new, "dedicated image dialog state")

open_dialog = '{ activeImageDialog = item; showToolPopup = false; showCanvasPopup = false; floatingMenu = "" }'
replace_once(
    '"裁剪", "调色", "边框", "圆角", "阴影" -> { activePanel = EditorPanel.IMAGE; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }',
    '"裁剪", "调色", "边框", "圆角", "阴影" -> ' + open_dialog,
    "crop color border radius and shadow open independent dialogs"
)
replace_once(
    '"透明度" -> { activePanel = EditorPanel.IMAGE; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }',
    '"透明度" -> ' + open_dialog,
    "opacity opens its own dialog"
)
replace_once(
    '"翻转" -> { activePanel = EditorPanel.IMAGE; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }',
    '"翻转" -> ' + open_dialog,
    "flip opens its own dialog"
)
replace_once(
    '"对齐" -> { activePanel = EditorPanel.IMAGE; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }',
    '"对齐" -> ' + open_dialog,
    "alignment opens its own dialog"
)
replace_once(
    '"设为背景图" -> runJs("setSelectedImageAsBackground()")',
    '"设为背景图" -> ' + open_dialog,
    "background image has a confirmation dialog"
)

# The old contextual-toolbar shortcut must not reopen the mixed image property panel.
old_more = 'TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { selectedImageHtml = ""; activePanel = EditorPanel.IMAGE }) { Text("更多 ⋯", color = accent, fontSize = 11.sp) }'
new_more = 'TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { activeImageDialog = "调色"; showToolPopup = false; showCanvasPopup = false }) { Text("调色", color = accent, fontSize = 11.sp) }'
if old_more in s:
    s = s.replace(old_more, new_more, 1)

# Lock protection applies to every image-mutating bridge method, not only sliders.
def guard_function(name: str):
    global s
    pattern = re.compile(r"(function " + re.escape(name) + r"\([^)]*\)\{)if\(!activeImage\)return;")
    s2, count = pattern.subn(r"\1if(!activeImage||activeImage.dataset.editorLocked==='1')return;", s, count=1)
    if count:
        s = s2
        print("Image lock guard:", name)
        return
    existing = re.search(r"function " + re.escape(name) + r"\([^)]*\)\{[^}]{0,220}editorLocked", s)
    if not existing:
        raise SystemExit(f"Could not verify image lock protection for {name}")

for function_name in [
    "setSelectedImageBorder", "setSelectedImageOpacity", "setSelectedImageShadow",
    "flipSelectedImage", "alignSelectedImage", "setSelectedImageAsBackground",
    "setSelectedImageWidth", "setSelectedImageObjectPosition", "rotateSelectedImage",
    "setSelectedImageRadius", "cropSelectedImage", "resetSelectedImageCrop",
    "replaceSelectedImage", "deleteSelectedImage", "setSelectedImageAlt",
    "commitSelectedImageStyle"
]:
    guard_function(function_name)

paste_old = "function pasteSelectedImageStyle(){if(!activeImage||!editorImageStyleClipboard)return;"
paste_new = "function pasteSelectedImageStyle(){if(!activeImage||activeImage.dataset.editorLocked==='1'||!editorImageStyleClipboard)return;"
if paste_old in s:
    s = s.replace(paste_old, paste_new, 1)
elif paste_new not in s:
    raise SystemExit("Could not verify image-style paste lock protection")

dialog_anchor = '    if (showImageAlt) EditorInputDialog("图片替代文字"'
dialog = r'''    if (activeImageDialog.isNotBlank()) {
        val imageAction = activeImageDialog
        AlertDialog(
            onDismissRequest = { activeImageDialog = "" },
            title = { Text(imageAction, fontWeight = FontWeight.SemiBold) },
            text = {
                Column(
                    Modifier.fillMaxWidth().heightIn(max = 390.dp).verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    when (imageAction) {
                        "裁剪" -> {
                            Text("选择图片裁剪比例", color = Color.Gray, fontSize = 12.sp)
                            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                listOf("1:1", "4:3", "16:9").forEach { ratio ->
                                    TextButton(onClick = { runJs("cropSelectedImage('" + ratio + "')"); activeImageDialog = "" }) { Text(ratio) }
                                }
                            }
                            TextButton(onClick = { runJs("resetSelectedImageCrop()"); activeImageDialog = "" }) { Text("恢复原始比例") }
                        }
                        "调色" -> {
                            Text("亮度 " + imageBrightness.toInt() + "%", color = Color.Gray, fontSize = 12.sp)
                            Slider(value = imageBrightness, onValueChange = {
                                imageBrightness = it
                                runJs("previewSelectedImageFilters(" + it + "," + imageContrast + "," + imageSaturation + ")")
                            }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..200f)
                            Text("对比度 " + imageContrast.toInt() + "%", color = Color.Gray, fontSize = 12.sp)
                            Slider(value = imageContrast, onValueChange = {
                                imageContrast = it
                                runJs("previewSelectedImageFilters(" + imageBrightness + "," + it + "," + imageSaturation + ")")
                            }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..200f)
                            Text("饱和度 " + imageSaturation.toInt() + "%", color = Color.Gray, fontSize = 12.sp)
                            Slider(value = imageSaturation, onValueChange = {
                                imageSaturation = it
                                runJs("previewSelectedImageFilters(" + imageBrightness + "," + imageContrast + "," + it + ")")
                            }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..200f)
                        }
                        "透明度" -> {
                            Text("透明度 " + imageOpacity.toInt() + "%", color = Color.Gray, fontSize = 12.sp)
                            Slider(value = imageOpacity, onValueChange = {
                                imageOpacity = it
                                runJs("previewSelectedImageOpacity(" + it + ")")
                            }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..100f)
                        }
                        "边框" -> {
                            Text("选择图片边框样式", color = Color.Gray, fontSize = 12.sp)
                            FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                listOf(
                                    "无边框" to "0",
                                    "细边框" to "1px solid #dfe5e1",
                                    "主题边框" to "2px solid #159765",
                                    "深色边框" to "2px solid #333333"
                                ).forEach { (label, css) ->
                                    TextButton(onClick = { runJs("setSelectedImageBorder(" + JSONObject.quote(css) + ")"); activeImageDialog = "" }) { Text(label) }
                                }
                            }
                        }
                        "圆角" -> {
                            Text("圆角 " + imageRadius.toInt() + " px", color = Color.Gray, fontSize = 12.sp)
                            Slider(value = imageRadius, onValueChange = {
                                imageRadius = it
                                runJs("previewSelectedImageRadius(" + it + " + 'px')")
                            }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..40f)
                            TextButton(onClick = { imageRadius = 0f; runJs("previewSelectedImageRadius('0px');commitSelectedImageStyle()") }) { Text("恢复直角") }
                        }
                        "阴影" -> {
                            Text("选择图片阴影效果", color = Color.Gray, fontSize = 12.sp)
                            FlowRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                listOf(
                                    "无阴影" to "none",
                                    "轻柔" to "0 2px 6px rgba(0,0,0,.14)",
                                    "标准" to "0 4px 14px rgba(0,0,0,.22)",
                                    "强烈" to "0 8px 24px rgba(0,0,0,.28)"
                                ).forEach { (label, css) ->
                                    TextButton(onClick = { runJs("setSelectedImageShadow(" + JSONObject.quote(css) + ")"); activeImageDialog = "" }) { Text(label) }
                                }
                            }
                        }
                        "翻转" -> {
                            Text("选择翻转方向", color = Color.Gray, fontSize = 12.sp)
                            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                TextButton(onClick = { runJs("flipSelectedImage('horizontal')"); activeImageDialog = "" }) { Text("水平翻转") }
                                TextButton(onClick = { runJs("flipSelectedImage('vertical')"); activeImageDialog = "" }) { Text("垂直翻转") }
                            }
                        }
                        "对齐" -> {
                            Text("设置图片在段落中的水平位置", color = Color.Gray, fontSize = 12.sp)
                            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                TextButton(onClick = { runJs("alignSelectedImage('left')"); activeImageDialog = "" }) { Text("左对齐") }
                                TextButton(onClick = { runJs("alignSelectedImage('center')"); activeImageDialog = "" }) { Text("居中") }
                                TextButton(onClick = { runJs("alignSelectedImage('right')"); activeImageDialog = "" }) { Text("右对齐") }
                            }
                        }
                        "设为背景图" -> Text("将当前图片设置为所在段落的背景图，图片本体将隐藏。", color = Color.Gray, fontSize = 12.sp)
                    }
                }
            },
            confirmButton = {
                if (imageAction == "设为背景图") {
                    TextButton(onClick = { runJs("setSelectedImageAsBackground()"); activeImageDialog = "" }) { Text("设为背景图", color = AppColors.Theme) }
                } else {
                    TextButton(onClick = { activeImageDialog = "" }) { Text("完成", color = AppColors.Theme) }
                }
            },
            dismissButton = { TextButton(onClick = { activeImageDialog = "" }) { Text("取消") } }
        )
    }
'''
replace_once(dialog_anchor, dialog + dialog_anchor, "dedicated single-action image dialogs")

required = [
    'var activeImageDialog by remember { mutableStateOf("") }',
    '"裁剪", "调色", "边框", "圆角", "阴影" -> { activeImageDialog = item;',
    '"透明度" -> { activeImageDialog = item;',
    '"翻转" -> { activeImageDialog = item;',
    '"对齐" -> { activeImageDialog = item;',
    '"设为背景图" -> { activeImageDialog = item;',
    'if (activeImageDialog.isNotBlank())',
    '"圆角" -> {',
    'previewSelectedImageRadius(',
    '"调色" -> {',
    'previewSelectedImageFilters(',
    '"透明度" -> {',
    'previewSelectedImageOpacity(',
    'setSelectedImageBorder(',
    'setSelectedImageShadow('
]
missing = [token for token in required if token not in s]
if missing:
    ERROR.write_text("Missing image dialog features: " + ", ".join(missing) + "\n", encoding="utf-8")
    raise SystemExit("Image action dialog validation failed: " + ", ".join(missing))

EDITOR.write_text(s, encoding="utf-8")
print("Image action dialogs applied: each image dock action opens its own focused dialog; live controls retain image lock guards.")
