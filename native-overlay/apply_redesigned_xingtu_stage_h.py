#!/usr/bin/env python3
"""Stage H: redesign the Xingtu workspace and separate selected-object tools into live bottom popups."""
from pathlib import Path
import re

EDITOR = Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorRedesignedScreen.kt")
ERROR = Path("xingtu_stage_h_patch_error.txt")

def fail(message):
    ERROR.write_text(message + "\n", encoding="utf-8")
    raise SystemExit(message)

if not EDITOR.is_file():
    fail("Redesigned editor source missing; Stage H must run after Stage E")
s = EDITOR.read_text(encoding="utf-8")

def once(old, new, label):
    global s
    if new in s:
        return
    count = s.count(old)
    if count != 1:
        fail(f"Stage H anchor mismatch [{label}]: expected 1, found {count}")
    s = s.replace(old, new, 1)

# A distinct compact workspace header; keep the existing palette, title editor,
# undo/redo behavior and preview action.
once(
    'Modifier.fillMaxWidth().height(58.dp).background(AppColors.Panel)\n                .padding(horizontal = 8.dp),',
    'Modifier.fillMaxWidth().height(64.dp).background(pageBg)\n                .padding(horizontal = 10.dp),',
    "workspace header geometry"
)
once(
    'IconButton(onClick = { handleEditorBack() }) {',
    'IconButton(onClick = { handleEditorBack() }, modifier = Modifier.size(40.dp).clip(CircleShape).background(AppColors.Panel)) {',
    "workspace back control"
)
once(
    'IconButton(onClick = { runJs("undoEditor()") }, modifier = Modifier.size(36.dp))',
    'IconButton(onClick = { runJs("undoEditor()") }, modifier = Modifier.size(36.dp).clip(CircleShape).background(AppColors.Panel))',
    "workspace undo control"
)
once(
    'IconButton(onClick = { runJs("redoEditor()") }, modifier = Modifier.size(36.dp))',
    'IconButton(onClick = { runJs("redoEditor()") }, modifier = Modifier.size(36.dp).clip(CircleShape).background(AppColors.Panel))',
    "workspace redo control"
)

# Put the document on a softly separated work surface without changing the
# document's white page or its existing HTML content.
once(
    '            BoxWithConstraints(Modifier.weight(1f).fillMaxWidth().background(pageBg)) {',
    '            BoxWithConstraints(Modifier.weight(1f).fillMaxWidth().background(Color(0xFFEDEFEF)).padding(horizontal = 10.dp, vertical = 8.dp).clip(RoundedCornerShape(14.dp)).background(Color.White)) {',
    "canvas workspace surface"
)
once(
    '                modifier = Modifier.fillMaxSize(),\n                update = { editor = it }',
    '                modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(10.dp)).background(Color.White),\n                update = { editor = it }',
    "paper canvas clipping"
)

# Replace the text-only primary dock with an icon-first dock. All original
# navigation targets, callbacks, and panel contents are preserved.
old_nav = '''                        RedesignedEditorPanel.values().filterNot { it in templateSubPanels || it == RedesignedEditorPanel.TEXT2 }.forEach { panel ->
                            TextButton(
                                onClick = {
                                    showTemplateSubnav = panel == RedesignedEditorPanel.TEMPLATE
                                    if (activePanel == RedesignedEditorPanel.TEXT2 && panel != RedesignedEditorPanel.TEXT2) runJs("setText2SelectionPreview(false);")
                                    activePanel = if (panel == RedesignedEditorPanel.TEMPLATE) templateSubPanel else panel
                                    floatingMenu = ""
                                    if (panel == RedesignedEditorPanel.CANVAS) {
                                        showToolPopup = false
                                        showCanvasPopup = true
                                        toolPopupOffset = Offset.Zero
                                    } else {
                                        showCanvasPopup = false
                                        showToolPopup = true
                                         if (panel == RedesignedEditorPanel.TEXT2) runJs("setText2SelectionPreview(true);")
                                        toolPanelHeightDp = if (panel == RedesignedEditorPanel.TEXT2) 330f else 180f
                                    }
                                    if (panel == RedesignedEditorPanel.LAYER) refreshLayerItems()
                                },
                                contentPadding = PaddingValues(horizontal = 9.dp, vertical = 3.dp)
                            ) {
                                Text(
                                    panel.label,
                                    color = if ((activePanel == panel || (panel == RedesignedEditorPanel.TEMPLATE && showTemplateSubnav)) && (showToolPopup || showCanvasPopup)) Color.White else Color(0xFF777777),
                                    fontSize = if (activePanel == panel) 15.sp else 13.sp,
                                    fontWeight = if (activePanel == panel) FontWeight.Bold else FontWeight.Normal,
                                    maxLines = 1
                                )
                            }
                        }'''
new_nav = '''                        RedesignedEditorPanel.values().filterNot { it in templateSubPanels || it == RedesignedEditorPanel.TEXT2 }.forEach { panel ->
                            val isSelected = (activePanel == panel || (panel == RedesignedEditorPanel.TEMPLATE && showTemplateSubnav)) && (showToolPopup || showCanvasPopup)
                            Column(
                                Modifier.width(58.dp).fillMaxHeight().clip(RoundedCornerShape(11.dp))
                                    .background(if (isSelected) AppColors.Theme.copy(alpha = 0.14f) else Color.Transparent)
                                    .clickable {
                                        showTemplateSubnav = panel == RedesignedEditorPanel.TEMPLATE
                                        if (activePanel == RedesignedEditorPanel.TEXT2 && panel != RedesignedEditorPanel.TEXT2) runJs("setText2SelectionPreview(false);")
                                        activePanel = if (panel == RedesignedEditorPanel.TEMPLATE) templateSubPanel else panel
                                        floatingMenu = ""
                                        if (panel == RedesignedEditorPanel.CANVAS) {
                                            showToolPopup = false
                                            showCanvasPopup = true
                                            toolPopupOffset = Offset.Zero
                                        } else {
                                            showCanvasPopup = false
                                            showToolPopup = true
                                            if (panel == RedesignedEditorPanel.TEXT2) runJs("setText2SelectionPreview(true);")
                                            toolPanelHeightDp = if (panel == RedesignedEditorPanel.TEXT2) 330f else 180f
                                        }
                                        if (panel == RedesignedEditorPanel.LAYER) refreshLayerItems()
                                    }
                                    .padding(vertical = 4.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.Center
                            ) {
                                EditorVectorIcon(panel.label, if (isSelected) AppColors.Theme else Color(0xFF858D88), Modifier.size(20.dp))
                                Text(
                                    panel.label,
                                    color = if (isSelected) AppColors.Theme else AppColors.TextDim,
                                    fontSize = 9.sp,
                                    fontWeight = if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                                    maxLines = 1
                                )
                            }
                        }'''
once(old_nav, new_nav, "icon-first primary navigation")
once(
    '                    Modifier.fillMaxWidth().height(50.dp)\n                        .background(Color(0xFF181818)),',
    '                    Modifier.fillMaxWidth().height(68.dp)\n                        .background(AppColors.Panel)\n                        .border(androidx.compose.foundation.BorderStroke(1.dp, AppColors.Line)),',
    "primary dock surface"
)

# Do not allow a selected-object action to fall back into the combined Text2 or
# IMAGE panel. Every tool owns one Popup; crop and color keep dedicated panels.
text_action = re.search(r'"font", "style", "layout", "text-opacity" -> \{(.*?)\n\s*\}', s, re.S)
if not text_action or "activeObjectDialog = action" not in text_action.group(1):
    fail("Selected text actions are still routed into a combined panel")
if "activePanel = RedesignedEditorPanel.TEXT2" in text_action.group(1) or "showToolPopup = true" in text_action.group(1):
    fail("Selected text action still opens the combined Text2 panel")
if not re.search(r'"text-align"\s*->\s*activeObjectDialog\s*=\s*action', s):
    fail("Text alignment does not open its own popup")
if not re.search(r"else -> \\{\\s*activeObjectDialog = action", s):
    fail("Selected image actions do not open their individual popup")
if 'activePanel = RedesignedEditorPanel.IMAGE_CROP' not in s or 'activePanel = RedesignedEditorPanel.IMAGE_COLOR' not in s:
    fail("Dedicated image crop/color panels were lost")

# Dismiss the individual popup before parent layers when system Back is pressed.
once(
    '            floatingMenu.isNotBlank() -> floatingMenu = ""\n            showDeleteConfirm != null -> showDeleteConfirm = null',
    '            floatingMenu.isNotBlank() -> floatingMenu = ""\n            activeObjectDialog.isNotBlank() -> activeObjectDialog = ""\n            showDeleteConfirm != null -> showDeleteConfirm = null',
    "popup-first Back handling"
)

# Route text edits through the Text2 bridge, which restores the selected DOM
# range, updates native HTML immediately, notifies the live canvas and groups undo.
text_replacements = [
    ("styleSelectionOrParagraph('fontSize'", "applyText2Style('font-size'"),
    ("styleSelectionOrParagraph('fontFamily'", "applyText2Style('font-family'"),
    ("styleSelectionOrParagraph('fontWeight','bold')", "applyText2Style('font-weight','700')"),
    ("styleSelectionOrParagraph('fontStyle','italic')", "applyText2Style('font-style','italic')"),
    ("styleSelectionOrParagraph('textDecoration','underline')", "applyText2Style('text-decoration-line','underline')"),
    ("styleSelectionOrParagraph('color'", "applyText2Style('color'"),
    ("styleSelectedParagraph('lineHeight'", "applyText2Style('line-height'"),
]
for old, new in text_replacements:
    if old in s:
        s = s.replace(old, new)
    elif new not in s:
        fail("Text live-preview callback anchor missing: " + old)

old_align = '''TextButton(onClick = { runJs("styleSelectedParagraph('textAlign','$value')"); if (activeObjectDialog == "text-align") activeObjectDialog = "" }) { Text(label, color = Color.White) }'''
new_align = '''TextButton(onClick = {
                                    val command = when (value) { "left" -> "justifyLeft"; "center" -> "justifyCenter"; "right" -> "justifyRight"; else -> "justifyFull" }
                                    runJs("applyText2Command(" + JSONObject.quote(command) + ",null)")
                                    if (activeObjectDialog == "text-align") activeObjectDialog = ""
                                }) { Text(label, color = Color.White) }'''
once(old_align, new_align, "paragraph alignment live preview")

# Opacity previews must notify the native live-preview bridge while dragging.
old_text_opacity = "function previewSelectedTextOpacity(v){const e=activeTextBlock||selectedParagraph();if(!e||e.dataset.editorLocked==='1')return;e.style.opacity=String(Math.max(0,Math.min(100,Number(v)))/100);}"
new_text_opacity = "function previewSelectedTextOpacity(v){const e=activeTextBlock||selectedParagraph();if(!e||e.dataset.editorLocked==='1')return;e.style.opacity=String(Math.max(0,Math.min(100,Number(v)))/100);NativeEditor.changed(root.innerHTML);notifyCanvasPreview();}"
once(old_text_opacity, new_text_opacity, "live text opacity preview")
old_text_commit = "function commitSelectedTextOpacity(){const e=activeTextBlock||selectedParagraph();if(!e||e.dataset.editorLocked==='1')return;commitHistory();NativeEditor.changed(root.innerHTML);}"
new_text_commit = "function commitSelectedTextOpacity(){const e=activeTextBlock||selectedParagraph();if(!e||e.dataset.editorLocked==='1')return;commitHistory();NativeEditor.changed(root.innerHTML);notifyCanvasPreview();}"
once(old_text_commit, new_text_commit, "text opacity commit preview")

image_live_helpers = [
    ("function previewSelectedImageOpacity(v){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.opacity=String(Math.max(0,Math.min(100,Number(v)))/100);}",
     "function previewSelectedImageOpacity(v){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.opacity=String(Math.max(0,Math.min(100,Number(v)))/100);syncSelectedImageLive();}"),
    ("function previewSelectedImageRadius(tl,tr,br,bl){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.borderRadius=[tl,tr,br,bl].map(v=>Math.max(0,Math.min(120,Number(v)||0))+'px').join(' ');}",
     "function previewSelectedImageRadius(tl,tr,br,bl){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.borderRadius=[tl,tr,br,bl].map(v=>Math.max(0,Math.min(120,Number(v)||0))+'px').join(' ');syncSelectedImageLive();}"),
    ("function previewSelectedImageBorder(w,style,color){if(!activeImage||activeImage.dataset.editorLocked==='1')return;w=Math.max(0,Math.min(12,Number(w)||0));activeImage.style.border=w===0?'none':w+'px '+(style||'solid')+' '+(color||'#DDE3EA');}",
     "function previewSelectedImageBorder(w,style,color){if(!activeImage||activeImage.dataset.editorLocked==='1')return;w=Math.max(0,Math.min(12,Number(w)||0));activeImage.style.border=w===0?'none':w+'px '+(style||'solid')+' '+(color||'#DDE3EA');syncSelectedImageLive();}"),
    ("function previewSelectedImageShadow(x,y,blur,spread,color,opacity){if(!activeImage||activeImage.dataset.editorLocked==='1')return;const h=(color||'#000000').replace('#',''),r=parseInt(h.slice(0,2),16)||0,g=parseInt(h.slice(2,4),16)||0,b=parseInt(h.slice(4,6),16)||0,a=Math.max(0,Math.min(100,Number(opacity)||0))/100;activeImage.style.boxShadow=a===0?'none':(Number(x)||0)+'px '+(Number(y)||0)+'px '+Math.max(0,Number(blur)||0)+'px '+(Number(spread)||0)+'px rgba('+r+','+g+','+b+','+a+')';}",
     "function previewSelectedImageShadow(x,y,blur,spread,color,opacity){if(!activeImage||activeImage.dataset.editorLocked==='1')return;const h=(color||'#000000').replace('#',''),r=parseInt(h.slice(0,2),16)||0,g=parseInt(h.slice(2,4),16)||0,b=parseInt(h.slice(4,6),16)||0,a=Math.max(0,Math.min(100,Number(opacity)||0))/100;activeImage.style.boxShadow=a===0?'none':(Number(x)||0)+'px '+(Number(y)||0)+'px '+Math.max(0,Number(blur)||0)+'px '+(Number(spread)||0)+'px rgba('+r+','+g+','+b+','+a+')';syncSelectedImageLive();}"),
]
for old, new in image_live_helpers:
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        fail("Image live-preview helper anchor missing: " + old[:70])

checks = {
    "redesigned header": "height(64.dp).background(pageBg)" in s,
    "canvas work surface": "background(Color(0xFFEDEFEF)).padding(horizontal = 10.dp, vertical = 8.dp)" in s,
    "paper canvas clipping": "Modifier.fillMaxSize().clip(RoundedCornerShape(10.dp)).background(Color.White)" in s,
    "icon primary dock": "EditorVectorIcon(panel.label" in s and "height(68.dp)" in s,
    "selected text opens one popup": "activeObjectDialog = action" in text_action.group(1) and "showToolPopup = false" in text_action.group(1),
    "selected image opens one popup": re.search(r"else -> \\{\\s*activeObjectDialog = action", s) is not None,
    "dedicated crop panel": "RedesignedEditorPanel.IMAGE_CROP -> ImageCropColorPanel" in s,
    "dedicated color panel": "RedesignedEditorPanel.IMAGE_COLOR -> ImageCropColorPanel" in s,
    "bottom non-modal popup": "alignment = Alignment.BottomCenter" in s and "focusable = false" in s,
    "popup Back layer": 'activeObjectDialog.isNotBlank() -> activeObjectDialog = ""' in s,
    "text style live preview": "NativeEditor.changed(root.innerHTML);" in s[s.index("function applyText2Style"):s.index("function applyText2Command")] and "notifyCanvasPreview();" in s[s.index("function applyText2Style"):s.index("function applyText2Command")],
    "text opacity live preview": "e.style.opacity=String(Math.max(0,Math.min(100,Number(v)))/100);NativeEditor.changed(root.innerHTML);notifyCanvasPreview();" in s,
    "image opacity live preview": "activeImage.style.opacity=String(Math.max(0,Math.min(100,Number(v)))/100);syncSelectedImageLive();" in s,
    "image radius live preview": "syncSelectedImageLive();" in s[s.index("function previewSelectedImageRadius"):s.index("function previewSelectedImageShadow")],
    "image border live preview": "syncSelectedImageLive();" in s[s.index("function previewSelectedImageBorder"):s.index("function previewSelectedImageRadius")],
    "image shadow live preview": "syncSelectedImageLive();" in s[s.index("function previewSelectedImageShadow"):s.index("function setSelectedImageAsBackground")],
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    fail("Stage H validation failed: " + ", ".join(failed))

EDITOR.write_text(s, encoding="utf-8")
print("Stage H passed: distinct workspace header/canvas/icon dock; one bottom non-modal popup per selected-object action; text/image previews notify the live canvas.")
