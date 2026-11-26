#!/usr/bin/env python3
"""Apply v2 object-aware bottom navigation after the existing editor patches."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "editor_bottom_nav_v2_patch_error.txt"

if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")

s = EDITOR.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        ERROR.write_text(f"{label}: expected one anchor, found {count}\n", encoding="utf-8")
        raise SystemExit(f"Bottom navigation v2 patch anchor mismatch [{label}]: {count}")
    s = s.replace(old, new, 1)

def block_end(source: str, open_pos: int, left="{", right="}"):
    depth = 0
    quote = None
    escaped = False
    for i in range(open_pos, len(source)):
        ch = source[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch == left:
            depth += 1
        elif ch == right:
            depth -= 1
            if depth == 0:
                return i + 1
    raise SystemExit("Could not find matching Kotlin block end")

# A single dock state is derived from the structured WebView selection.
replace_once(
    "    var selectionState by remember { mutableStateOf(EditorSelectionState()) }",
    "    var selectionState by remember { mutableStateOf(EditorSelectionState()) }\n    var selectedDockMode by remember { mutableStateOf(\"DEFAULT\") }",
    "dock state"
)

old_callback = """                            { state ->
                                selectionState = state
                                selectedTextActive = state.kind == EditorSelectionKind.TEXT_BLOCK ||
                                    state.kind == EditorSelectionKind.TEXT_RANGE || state.kind == EditorSelectionKind.CARET
                                if (state.kind == EditorSelectionKind.NONE) floatingMenu = ""
                            }"""
new_callback = """                            { state ->
                                selectionState = state
                                selectedTextActive = state.kind == EditorSelectionKind.TEXT_BLOCK ||
                                    state.kind == EditorSelectionKind.TEXT_RANGE || state.kind == EditorSelectionKind.CARET
                                selectedDockMode = when (state.kind) {
                                    EditorSelectionKind.TEXT_BLOCK, EditorSelectionKind.TEXT_RANGE, EditorSelectionKind.CARET -> "TEXT"
                                    EditorSelectionKind.IMAGE -> "IMAGE"
                                    EditorSelectionKind.COMPONENT, EditorSelectionKind.TABLE, EditorSelectionKind.LAYOUT, EditorSelectionKind.MULTI_BLOCK -> "COMPONENT"
                                    else -> "DEFAULT"
                                }
                                if (state.kind == EditorSelectionKind.NONE) floatingMenu = ""
                            }"""
replace_once(old_callback, new_callback, "selection-to-dock routing")

# Text2 now has four explicit destinations. The existing layout controls remain in 排版.
replace_once(
    'listOf("字体", "样式", "排版").forEach { tab ->',
    'listOf("字体", "样式", "排版", "透明度").forEach { tab ->',
    "text2 four tabs"
)
replace_once(
    """            } else {
                val alignItems = listOf("居左", "居中", "居右", "水平对齐", "居顶", "居中", "居底", "垂直对齐")""",
    """            } else if (mainTab == "透明度") {
                Text("文字整体透明度", color = Color(0xFFAAAAAA), fontSize = 11.sp)
                Text2ParameterRow("透明度", textOpacity, 0f, 100f, "%") { textOpacity = it; onApplyCss("opacity", (it / 100f).toString()) }
            } else {
                val alignItems = listOf("居左", "居中", "居右", "水平对齐", "居顶", "居中", "居底", "垂直对齐")""",
    "text2 opacity panel"
)

# Add object-aware image, text and component commands to the existing WebView command layer.
image_anchor = "function setSelectedImageBorder(v){if(!activeImage)return;activeImage.style.border=v;commitHistory();NativeEditor.changed(root.innerHTML);}"
image_helpers = """function setSelectedImageBorder(v){if(!activeImage)return;activeImage.style.border=v;commitHistory();NativeEditor.changed(root.innerHTML);}
                            let editorObjectClipboard=null,editorImageStyleClipboard=null;
                            function setSelectedImageOpacity(v){if(!activeImage)return;activeImage.style.opacity=String(Math.max(0,Math.min(100,Number(v)))/100);commitHistory();NativeEditor.changed(root.innerHTML);}
                            function setSelectedImageShadow(v){if(!activeImage)return;activeImage.style.boxShadow=v;commitHistory();NativeEditor.changed(root.innerHTML);}
                            function flipSelectedImage(axis){if(!activeImage)return;if(axis==='vertical')activeImage.dataset.flipY=activeImage.dataset.flipY==='1'?'0':'1';else activeImage.dataset.flipX=activeImage.dataset.flipX==='1'?'0':'1';const r=parseInt(activeImage.dataset.rotation||'0');activeImage.style.transform='rotate('+r+'deg) scaleX('+(activeImage.dataset.flipX==='1'?-1:1)+') scaleY('+(activeImage.dataset.flipY==='1'?-1:1)+')';commitHistory();NativeEditor.changed(root.innerHTML);}
                            function setSelectedImageFilter(v){if(!activeImage)return;activeImage.style.filter=v||'none';commitHistory();NativeEditor.changed(root.innerHTML);}
                            function alignSelectedImage(v){if(!activeImage)return;activeImage.style.display='block';activeImage.style.marginLeft=v==='left'?'0':'auto';activeImage.style.marginRight=v==='right'?'0':'auto';if(v==='center'){activeImage.style.marginLeft='auto';activeImage.style.marginRight='auto';}commitHistory();NativeEditor.changed(root.innerHTML);}
                            function copySelectedImageObject(){if(!activeImage)return;editorObjectClipboard=activeImage.outerHTML;}
                            function copySelectedImageStyle(){if(!activeImage)return;editorImageStyleClipboard={width:activeImage.style.width,height:activeImage.style.height,objectFit:activeImage.style.objectFit,objectPosition:activeImage.style.objectPosition,border:activeImage.style.border,borderRadius:activeImage.style.borderRadius,boxShadow:activeImage.style.boxShadow,opacity:activeImage.style.opacity,filter:activeImage.style.filter,transform:activeImage.style.transform};}
                            function pasteSelectedImageStyle(){if(!activeImage||!editorImageStyleClipboard)return;Object.keys(editorImageStyleClipboard).forEach(k=>activeImage.style[k]=editorImageStyleClipboard[k]);commitHistory();NativeEditor.changed(root.innerHTML);}
                            function setSelectedImageAsBackground(){if(!activeImage)return;const p=activeImage.parentElement;if(!p)return;const rect=activeImage.getBoundingClientRect();p.style.backgroundImage='url('+JSON.stringify(activeImage.src)+')';p.style.backgroundSize='cover';p.style.backgroundPosition='center';p.style.backgroundRepeat='no-repeat';p.style.minHeight=Math.max(1,Math.round(rect.height))+'px';activeImage.style.visibility='hidden';commitHistory();NativeEditor.changed(root.innerHTML);}
                            function selectedEditableObject(){return activeImage||selectedBlock()||selectedParagraph();}
                            function toggleSelectedObjectLock(){const e=selectedEditableObject();if(!e)return;const locked=e.dataset.editorLocked!=='1';e.dataset.editorLocked=locked?'1':'0';if(e.tagName==='IMG')e.draggable=!locked;else e.contentEditable=locked?'false':'true';e.style.outline=locked?'1px dashed #999':'';commitHistory();NativeEditor.changed(root.innerHTML);}
                            function selectedTextBlockHtml(){const e=selectedParagraph()||selectedTextElement();if(!e||!root.contains(e))return '';const c=e.cloneNode(true);c.removeAttribute('data-editor-id');c.classList.remove('selected-block','selected-text-block');return c.outerHTML;}
                            function duplicateSelectedTextParagraph(){const e=selectedParagraph()||selectedTextElement();if(!e||!root.contains(e))return;const c=e.cloneNode(true);c.querySelectorAll('[data-editor-id]').forEach(n=>n.removeAttribute('data-editor-id'));c.removeAttribute('data-editor-id');c.classList.remove('selected-block','selected-text-block');e.insertAdjacentElement('afterend',c);commitHistory();NativeEditor.changed(root.innerHTML);}
                            function copySelectedTextBlock(){const h=selectedTextBlockHtml();if(h)editorObjectClipboard=h;}
                            function pasteEditorObjectClipboard(){if(!editorObjectClipboard)return;const box=document.createElement('div');box.innerHTML=editorObjectClipboard;const node=box.firstElementChild;if(!node)return;node.querySelectorAll('[data-editor-id]').forEach(n=>n.removeAttribute('data-editor-id'));node.removeAttribute('data-editor-id');const anchor=selectedParagraph()||selectedBlock()||(activeImage&&activeImage.parentElement);if(anchor&&anchor.parentElement)anchor.insertAdjacentElement('afterend',node);else root.appendChild(node);commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();}
                            function enableSelectedTextEditing(){root.contentEditable='true';restoreSelection();root.focus();if(typeof saveSelection==='function')saveSelection();}
                            function moveSelectedBlockHorizontal(dir){const e=selectedEditableObject();if(!e||e.dataset.editorLocked==='1')return;const cell=e.closest&&e.closest('td,th');if(cell){const peer=dir<0?cell.previousElementSibling:cell.nextElementSibling;if(peer){peer.appendChild(e);commitHistory();NativeEditor.changed(root.innerHTML);}return;}const parent=e.parentElement;if(!parent||parent===root)return;const peer=dir<0?e.previousElementSibling:e.nextElementSibling;if(peer){if(dir<0)parent.insertBefore(e,peer);else parent.insertBefore(peer,e);commitHistory();NativeEditor.changed(root.innerHTML);}}
"""
replace_once(image_anchor, image_helpers, "image and object commands")

# First tap on text selects; a second tap on the same paragraph enables content editing.
pointer_anchor = "                            root.addEventListener('click',function(ev){"
pointer_code = """                            let lastTextTapId='',lastTextTapAt=0;
                            root.addEventListener('pointerdown',function(ev){
                              const hit=ev.target&&ev.target.closest?ev.target.closest('p,h1,h2,h3,h4,h5,h6,li,blockquote,pre'):null;
                              if(!hit||!root.contains(hit))return;
                              const id=ensureEditorId(hit),now=Date.now(),second=(id===lastTextTapId&&now-lastTextTapAt<850);
                              if(second){root.contentEditable='true';}
                              else{root.contentEditable='false';lastTextTapId=id;lastTextTapAt=now;}
                            },true);
                            root.addEventListener('click',function(ev){"""
replace_once(pointer_anchor, pointer_code, "two-tap text editing")

# Keep the existing floating contextual window as an auxiliary tool and expose its component mode.
header_anchor = """                            Text(
                                when {
                                    floatingToolbarRequest == "image" -> "图片工具"""
if header_anchor in s:
    s=s.replace(header_anchor, """                            TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { floatingToolbarRequest = "component"; floatingMenu = "" }) { Text("组件", color = AppColors.Theme, fontSize = 11.sp) }
                            Text(
                                when {
                                    floatingToolbarRequest == "image" -> "图片工具""", 1)
else:
    raise SystemExit("Could not locate floating toolbar title for component shortcut")

# Replace the generic primary dock with the seven requested default entries and the three object-specific docks.
dock_comment = "// Persistent primary navigation is hidden while the secondary tool sheet is open."
comment_pos = s.find(dock_comment)
if comment_pos < 0:
    raise SystemExit("Could not locate persistent primary dock")
row_start = s.find("                Row(", comment_pos)
if row_start < 0:
    raise SystemExit("Could not locate primary dock Row")
open_pos = s.find("{", row_start)
if open_pos < 0:
    raise SystemExit("Primary dock Row has no content block")
row_end = block_end(s, open_pos)
new_dock = """                Row(
                    Modifier.fillMaxWidth().height(50.dp).background(Color(0xFF181818)),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceAround
                ) {
                    Row(
                        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceAround
                    ) {
                        val dockItems = when (selectedDockMode) {
                            "TEXT" -> listOf("编辑", "字体", "样式", "排版", "透明度", "存为模板", "顺序", "对齐", "创建副本", "复制", "复制样式", "粘贴", "多选", "锁定")
                            "IMAGE" -> listOf("替换", "裁剪", "调色", "透明度", "边框", "圆角", "阴影", "翻转", "对齐", "复制", "复制样式", "粘贴", "设为背景图")
                            "COMPONENT" -> listOf("组件", "左移", "右移", "上移", "下移", "对齐", "复制", "复制样式", "粘贴", "存为模板", "多选", "锁定/解锁", "删除")
                            else -> listOf("加图", "加字", "图文模板", "图文收藏", "文档", "画布", "图层")
                        }
                        dockItems.forEach { item ->
                            TextButton(
                                onClick = {
                                    when (selectedDockMode) {
                                        "DEFAULT" -> when (item) {
                                            "加图" -> imagePicker.launch(arrayOf("image/*"))
                                            "加字" -> { insert("<p><br></p>"); runJs("enableSelectedTextEditing()") }
                                            "图文模板" -> { showTemplateSubnav = true; activePanel = templateSubPanel; showCanvasPopup = false; toolPanelHeightDp = 200f; showToolPopup = true }
                                            "图文收藏" -> { activePanel = EditorPanel.STYLE; showTemplateSubnav = false; showCanvasPopup = false; toolPanelHeightDp = 200f; showToolPopup = true }
                                            "文档" -> { activePanel = EditorPanel.DOCUMENT; showTemplateSubnav = false; showCanvasPopup = false; toolPanelHeightDp = 200f; showToolPopup = true }
                                            "画布" -> { showToolPopup = false; showCanvasPopup = true; toolPopupOffset = Offset.Zero }
                                            "图层" -> { activePanel = EditorPanel.LAYER; showTemplateSubnav = false; showCanvasPopup = false; toolPanelHeightDp = 200f; showToolPopup = true; refreshLayerItems() }
                                        }
                                        "TEXT" -> when (item) {
                                            "编辑" -> runJs("enableSelectedTextEditing()")
                                            "字体", "样式", "排版", "透明度" -> {
                                                text2MainTab = item; activePanel = EditorPanel.TEXT2; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f; runJs("setText2SelectionPreview(true);")
                                            }
                                            "存为模板" -> editor?.evaluateJavascript("selectedTextBlockHtml()") { raw ->
                                                val block = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull().orEmpty()
                                                if (block.isNotBlank()) { vm.saveStyle(StyleModule(vm.newId(), "文字模板", "文字模板", block, System.currentTimeMillis().toString(), type = "component")); vm.toast("已保存到图文收藏") }
                                                else vm.toast("请先选中一个文字段落")
                                            }
                                            "顺序" -> { activePanel = EditorPanel.COMPONENT; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }
                                            "对齐" -> { text2MainTab = "排版"; activePanel = EditorPanel.TEXT2; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f; runJs("setText2SelectionPreview(true);") }
                                            "创建副本" -> runJs("duplicateSelectedTextParagraph()")
                                            "复制" -> runJs("copySelectedTextBlock()")
                                            "复制样式" -> runJs("restoreSelection();copyTextFormat();saveSelection();")
                                            "粘贴" -> runJs("pasteEditorObjectClipboard()")
                                            "多选" -> { multiSelectMode = !multiSelectMode; runJs("setMultiSelectMode(" + multiSelectMode + ")") }
                                            "锁定" -> runJs("toggleSelectedObjectLock()")
                                        }
                                        "IMAGE" -> when (item) {
                                            "替换" -> imageReplacementPicker.launch(arrayOf("image/*"))
                                            "裁剪", "调色", "边框", "圆角", "阴影" -> { activePanel = EditorPanel.IMAGE; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }
                                            "透明度" -> runJs("setSelectedImageOpacity(70)")
                                            "翻转" -> runJs("flipSelectedImage('horizontal')")
                                            "对齐" -> runJs("alignSelectedImage('center')")
                                            "复制" -> runJs("copySelectedImageObject()")
                                            "复制样式" -> runJs("copySelectedImageStyle()")
                                            "粘贴" -> runJs("pasteSelectedImageStyle()")
                                            "设为背景图" -> runJs("setSelectedImageAsBackground()")
                                        }
                                        "COMPONENT" -> when (item) {
                                            "组件" -> { floatingToolbarRequest = "component"; floatingMenu = "" }
                                            "左移" -> runJs("moveSelectedBlockHorizontal(-1)")
                                            "右移" -> runJs("moveSelectedBlockHorizontal(1)")
                                            "上移" -> runJs("moveSelectedBlock(-1)")
                                            "下移" -> runJs("moveSelectedBlock(1)")
                                            "对齐" -> showBlockProperties = true
                                            "复制" -> runJs("copySelectedTextBlock()")
                                            "复制样式" -> runJs("copyTextFormat()")
                                            "粘贴" -> runJs("pasteEditorObjectClipboard()")
                                            "存为模板" -> {
                                                val htmlToSave = selectedBlockHtml
                                                if (htmlToSave.isNotBlank()) { vm.saveStyle(StyleModule(vm.newId(), "组件模板", "组件模板", htmlToSave, System.currentTimeMillis().toString(), type = "component")); vm.toast("已保存到图文收藏") }
                                                else vm.toast("当前对象暂不支持保存为组件模板")
                                            }
                                            "多选" -> { multiSelectMode = !multiSelectMode; runJs("setMultiSelectMode(" + multiSelectMode + ")") }
                                            "锁定/解锁" -> runJs("toggleSelectedObjectLock()")
                                            "删除" -> runJs("deleteSelectedBlock()")
                                        }
                                    }
                                },
                                contentPadding = PaddingValues(horizontal = 7.dp, vertical = 3.dp)
                            ) {
                                Text(item, color = if (item in listOf("编辑", "字体", "样式", "排版", "透明度", "加图", "加字")) AppColors.Theme else Color(0xFFDDDDDD), fontSize = 11.sp, maxLines = 1)
                            }
                        }
                    }
                }"""
s = s[:row_start] + new_dock + s[row_end:]

# Ensure text selection and image manipulation commands are present in the final synthesized source.
required = [
    'selectedDockMode = when (state.kind)',
    'listOf("加图", "加字", "图文模板", "图文收藏", "文档", "画布", "图层")',
    'listOf("编辑", "字体", "样式", "排版", "透明度", "存为模板"',
    'listOf("替换", "裁剪", "调色", "透明度", "边框", "圆角", "阴影", "翻转"',
    'function setSelectedImageOpacity(v)',
    'function flipSelectedImage(axis)',
    'function selectedTextBlockHtml()',
    "root.addEventListener('pointerdown'",
    'listOf("字体", "样式", "排版", "透明度").forEach'
]
missing = [x for x in required if x not in s]
if missing:
    ERROR.write_text("Missing v2 features: " + ", ".join(missing) + "\n", encoding="utf-8")
    raise SystemExit("Bottom navigation v2 validation failed: " + ", ".join(missing))

EDITOR.write_text(s, encoding="utf-8")
print("Editor bottom navigation v2 applied: default/text/image/component docks, two-tap text activation, text opacity tab, image controls and component shortcut.")
