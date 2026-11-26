#!/usr/bin/env python3
"""Implement object-safe selection, whitespace reset, component floating tools and image controls."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "editor_functional_v3_patch_error.txt"
if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")
s = EDITOR.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        ERROR.write_text(f"{label}: expected one anchor, found {count}\n", encoding="utf-8")
        raise SystemExit(f"Functional v3 patch anchor mismatch [{label}]: {count}")
    s = s.replace(old, new, 1)

replace_once(
    'if (state.kind == EditorSelectionKind.NONE) floatingMenu = ""',
    'if (state.kind == EditorSelectionKind.NONE) { floatingMenu = ""; floatingToolbarRequest = "" }',
    "close contextual floating tool on blank canvas"
)
replace_once(
    'listOf(Triple("文字", "✎", "text"), Triple("图片", "▧", "image")).forEach',
    'listOf(Triple("文字", "✎", "text"), Triple("图片", "▧", "image"), Triple("组件", "▦", "component")).forEach',
    "component launcher item"
)
replace_once(
    'floatingToolbarRequest == "image" -> "图片工具"\n                                    floatingToolbarRequest == "text" -> "文字工具"',
    'floatingToolbarRequest == "image" -> "图片工具"\n                                    floatingToolbarRequest == "text" -> "文字工具"\n                                    floatingToolbarRequest == "component" -> "组件工具"',
    "component floating toolbar title"
)
replace_once(
    'if (!previewMode && (floatingToolbarRequest.isNotBlank() || selectedBlockHtml.isNotBlank() ||',
    'if (!previewMode && (floatingToolbarRequest.isNotBlank() || selectedImageHtml.isNotBlank() || selectedTextActive || selectedBlockHtml.isNotBlank() ||',
    "show toolbar for selected text and image"
)
s = s.replace(
    '                            TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { floatingToolbarRequest = "component"; floatingMenu = "" }) { Text("组件", color = AppColors.Theme, fontSize = 11.sp) }\n',
    '',
    1
)

replace_once("let activeImage=null;", "let activeImage=null;let activeTextBlock=null;", "active text block state")
replace_once(
    "if(!r||r.collapsed||!root.contains(r.commonAncestorContainer))return !!root.querySelector('.text2-selection-preview');",
    "if(!r||r.collapsed||!root.contains(r.commonAncestorContainer)){if(activeTextBlock&&root.contains(activeTextBlock)){root.querySelectorAll('.text2-selection-preview').forEach(el=>el.classList.remove('text2-selection-preview'));activeTextBlock.classList.add('text2-selection-preview');savedRange=null;if(s)s.removeAllRanges();notifyCanvasPreview();return true;}return !!root.querySelector('.text2-selection-preview');}",
    "text2 applies to whole tapped paragraph"
)
replace_once(
    "function enableSelectedTextEditing(){root.contentEditable='true';restoreSelection();root.focus();if(typeof saveSelection==='function')saveSelection();}",
    "function enableSelectedTextEditing(){root.contentEditable='true';if(activeTextBlock&&root.contains(activeTextBlock)){const r=document.createRange();r.selectNodeContents(activeTextBlock);r.collapse(false);const sel=window.getSelection();if(sel){sel.removeAllRanges();sel.addRange(r);}savedRange=r.cloneRange();}else restoreSelection();root.focus();if(typeof saveSelection==='function')saveSelection();}",
    "edit button focuses selected paragraph caret"
)
replace_once(
    "target=topLevelAt(node)||node;\n                                 if(!collapsed)kind='TEXT_RANGE';\n                                 else if(target&&/^(P|H1|H2|H3|H4|BLOCKQUOTE|PRE|UL|OL)$/.test(target.tagName))kind='CARET';",
    "target=(collapsed&&activeTextBlock&&root.contains(activeTextBlock))?activeTextBlock:(topLevelAt(node)||node);\n                                 if(!collapsed)kind='TEXT_RANGE';\n                                 else if(activeTextBlock&&root.contains(activeTextBlock)){kind='TEXT_BLOCK';target=activeTextBlock;}\n                                 else if(target&&/^(P|H1|H2|H3|H4|BLOCKQUOTE|PRE|UL|OL)$/.test(target.tagName))kind='CARET';",
    "prefer active text block over stale caret"
)
replace_once(
    "                               }else if(blocks.length===1){\n                                 target=blocks[0];",
    "                               }else if(activeTextBlock&&root.contains(activeTextBlock)){\n                                 kind='TEXT_BLOCK';target=activeTextBlock;\n                               }else if(blocks.length===1){\n                                 target=blocks[0];",
    "text block fallback selection"
)

click_token = "root.addEventListener('click',function(ev){"
click_start = s.find(click_token)
click_end_token = "function clearDragTarget(){"
click_end = s.find(click_end_token, click_start)
if click_start < 0 or click_end < 0:
    raise SystemExit("Could not locate the canvas click listener boundaries")
click_start = s.rfind("\n", 0, click_start) + 1
click_end = s.rfind("\n", 0, click_end) + 1
new_click = r"""                            root.addEventListener('click',function(ev){
                              const imageNode=ev.target&&ev.target.closest?ev.target.closest('img'):(ev.target&&ev.target.tagName==='IMG'?ev.target:null);
                              const textNode=ev.target&&ev.target.closest?ev.target.closest('p,h1,h2,h3,h4,h5,h6,li,blockquote,pre'):null;
                              const clickedImage=!!(imageNode&&root.contains(imageNode));
                              const clickedText=!!(textNode&&root.contains(textNode));
                              const top=topLevelAt(ev.target);
                              const blankTarget=!clickedImage&&!clickedText&&(!top||top===root||(!top.textContent.trim()&&!top.querySelector('img,table,svg,video,iframe,canvas,details')));
                              const clearBlockSelection=()=>{
                                root.querySelectorAll('.selected-block').forEach(x=>{x.classList.remove('selected-block');x.draggable=false;});
                                NativeEditor.blockSelected('');
                              };
                              const clearImageSelection=()=>{
                                if(activeImage)activeImage.classList.remove('selected-image');
                                activeImage=null;
                                NativeEditor.imageSelected('');
                              };
                              if(multiSelectMode&&(clickedImage||clickedText)){
                                clearImageSelection();activeTextBlock=null;
                                const selected=topLevelAt(clickedImage?imageNode:textNode);
                                if(selected){selected.classList.toggle('selected-block');updateMultiDragHandle(selected);}
                                NativeEditor.textSelected('0');
                                NativeEditor.blockSelected(Array.from(root.querySelectorAll('.selected-block')).map(x=>cleanBlockHtml(x)).join(''));
                              }else if(clickedImage){
                                clearBlockSelection();activeTextBlock=null;root.contentEditable='true';
                                clearImageSelection();activeImage=imageNode;
                                if(activeImage.dataset.originalWidth===undefined){activeImage.dataset.originalWidth=activeImage.style.width;activeImage.dataset.originalHeight=activeImage.style.height;activeImage.dataset.originalObjectFit=activeImage.style.objectFit;activeImage.dataset.originalObjectPosition=activeImage.style.objectPosition;}
                                activeImage.classList.add('selected-image');
                                NativeEditor.imageSelected(activeImage.outerHTML);NativeEditor.textSelected('0');
                              }else if(clickedText){
                                clearImageSelection();clearBlockSelection();activeTextBlock=textNode;
                                NativeEditor.textSelected('1');
                              }else if(blankTarget){
                                clearImageSelection();clearBlockSelection();activeTextBlock=null;root.contentEditable='true';
                                savedRange=null;const sel=window.getSelection();if(sel)sel.removeAllRanges();
                                NativeEditor.textSelected('0');
                              }else{
                                clearImageSelection();activeTextBlock=null;NativeEditor.textSelected('0');
                                const selected=top;
                                if(selected&&selected!==root){
                                  if(multiSelectMode){selected.classList.toggle('selected-block');updateMultiDragHandle(selected);}
                                  else{clearBlockSelection();selected.classList.add('selected-block');selected.draggable=true;}
                                  NativeEditor.blockSelected(Array.from(root.querySelectorAll('.selected-block')).map(x=>cleanBlockHtml(x)).join(''));
                                }else clearBlockSelection();
                              }
                              reportSelection();
                            });"""
s = s[:click_start] + new_click + s[click_end:]

pointer_old = """                            let lastTextTapId='',lastTextTapAt=0;
                            root.addEventListener('pointerdown',function(ev){
                              const hit=ev.target&&ev.target.closest?ev.target.closest('p,h1,h2,h3,h4,h5,h6,li,blockquote,pre'):null;
                              if(!hit||!root.contains(hit))return;
                              const id=ensureEditorId(hit),now=Date.now(),second=(id===lastTextTapId&&now-lastTextTapAt<850);
                              if(second){root.contentEditable='true';}
                              else{root.contentEditable='false';lastTextTapId=id;lastTextTapAt=now;}
                            },true);
"""
pointer_new = """                            let lastTextTapId='',lastTextTapAt=0;
                            root.addEventListener('pointerdown',function(ev){
                              const hit=ev.target&&ev.target.closest?ev.target.closest('p,h1,h2,h3,h4,h5,h6,li,blockquote,pre'):null;
                              if(!hit||!root.contains(hit))return;
                              const id=ensureEditorId(hit),now=Date.now(),second=(id===lastTextTapId&&now-lastTextTapAt<850);
                              activeTextBlock=hit;
                              if(second){root.contentEditable='true';root.focus();}
                              else{root.contentEditable='false';lastTextTapId=id;lastTextTapAt=now;}
                            },true);
"""
replace_once(pointer_old, pointer_new, "two tap selection and editing")

replace_once(
    "let editorObjectClipboard=null,editorImageStyleClipboard=null;",
    "let editorObjectClipboard=null,editorImageStyleClipboard=null,editorTextStyleClipboard=null,editorClipboardType='';",
    "typed clipboard state"
)
replace_once(
    "function copySelectedImageObject(){if(!activeImage)return;editorObjectClipboard=activeImage.outerHTML;}",
    "function copySelectedImageObject(){if(!activeImage||activeImage.dataset.editorLocked==='1')return;editorObjectClipboard=activeImage.outerHTML;editorClipboardType='OBJECT';}",
    "copy image object"
)
replace_once(
    "function copySelectedImageStyle(){if(!activeImage)return;editorImageStyleClipboard={width:activeImage.style.width,height:activeImage.style.height,objectFit:activeImage.style.objectFit,objectPosition:activeImage.style.objectPosition,border:activeImage.style.border,borderRadius:activeImage.style.borderRadius,boxShadow:activeImage.style.boxShadow,opacity:activeImage.style.opacity,filter:activeImage.style.filter,transform:activeImage.style.transform};}",
    "function copySelectedImageStyle(){if(!activeImage)return;editorImageStyleClipboard={width:activeImage.style.width,height:activeImage.style.height,objectFit:activeImage.style.objectFit,objectPosition:activeImage.style.objectPosition,border:activeImage.style.border,borderRadius:activeImage.style.borderRadius,boxShadow:activeImage.style.boxShadow,opacity:activeImage.style.opacity,filter:activeImage.style.filter,transform:activeImage.style.transform};editorClipboardType='IMAGE_STYLE';}",
    "copy image style"
)
replace_once(
    "function pasteSelectedImageStyle(){if(!activeImage||!editorImageStyleClipboard)return;Object.keys(editorImageStyleClipboard).forEach(k=>activeImage.style[k]=editorImageStyleClipboard[k]);commitHistory();NativeEditor.changed(root.innerHTML);}",
    "function pasteSelectedImageStyle(){if(!activeImage||activeImage.dataset.editorLocked==='1'||!editorImageStyleClipboard)return;Object.keys(editorImageStyleClipboard).forEach(k=>activeImage.style[k]=editorImageStyleClipboard[k]);commitHistory();NativeEditor.changed(root.innerHTML);}",
    "paste image style guard"
)
replace_once(
    "function selectedEditableObject(){return activeImage||selectedBlock()||selectedParagraph();}",
    "function selectedEditableObject(){return activeImage||activeTextBlock||selectedBlock()||selectedParagraph();}",
    "generic selected object"
)
replace_once(
    "function selectedTextBlockHtml(){const e=selectedParagraph()||selectedTextElement();",
    "function selectedTextBlockHtml(){const e=activeTextBlock||selectedParagraph()||selectedTextElement();",
    "selected text html"
)
replace_once(
    "function duplicateSelectedTextParagraph(){const e=selectedParagraph()||selectedTextElement();",
    "function duplicateSelectedTextParagraph(){const e=activeTextBlock||selectedParagraph()||selectedTextElement();",
    "duplicate selected text paragraph"
)
replace_once(
    "function copySelectedTextBlock(){const h=selectedTextBlockHtml();if(h)editorObjectClipboard=h;}",
    "function copySelectedTextBlock(){const h=selectedTextBlockHtml();if(h){editorObjectClipboard=h;editorClipboardType='OBJECT';}}",
    "copy text object"
)
replace_once(
    "function copySelectedTextBlock(){const h=selectedTextBlockHtml();if(h){editorObjectClipboard=h;editorClipboardType='OBJECT';}}",
    "function copySelectedTextBlock(){const h=selectedTextBlockHtml();if(h){editorObjectClipboard=h;editorClipboardType='OBJECT';}}\n                            function copySelectedObject(){if(activeImage){copySelectedImageObject();return;}const e=activeTextBlock||selectedParagraph()||selectedBlock();if(!e)return;editorObjectClipboard=e.outerHTML;editorClipboardType='OBJECT';}",
    "copy selected text/image/component object"
)
replace_once(
    "function pasteEditorObjectClipboard(){if(!editorObjectClipboard)return;const box=document.createElement('div');box.innerHTML=editorObjectClipboard;const node=box.firstElementChild;if(!node)return;node.querySelectorAll('[data-editor-id]').forEach(n=>n.removeAttribute('data-editor-id'));node.removeAttribute('data-editor-id');const anchor=selectedParagraph()||selectedBlock()||(activeImage&&activeImage.parentElement);if(anchor&&anchor.parentElement)anchor.insertAdjacentElement('afterend',node);else root.appendChild(node);commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();}",
    "function copySelectedTextStyle(){const e=activeTextBlock||selectedParagraph();if(!e)return;editorTextStyleClipboard={cssText:e.style.cssText};editorClipboardType='TEXT_STYLE';}\n                            function pasteSelectedTextStyle(){const e=activeTextBlock||selectedParagraph();if(!e||e.dataset.editorLocked==='1'||!editorTextStyleClipboard)return;e.style.cssText=editorTextStyleClipboard.cssText;commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();}\n                            function copySelectedObjectStyle(){if(activeImage)copySelectedImageStyle();else copySelectedTextStyle();}\n                            function selectedObjectHtml(){const e=selectedEditableObject();if(!e||!root.contains(e))return '';const c=e.cloneNode(true);c.classList.remove('selected-block','selected-image','selected-text-block');c.removeAttribute('data-editor-id');return c.outerHTML;}\n                            function pasteEditorObjectClipboard(){if(editorClipboardType==='IMAGE_STYLE'){pasteSelectedImageStyle();return;}if(editorClipboardType==='TEXT_STYLE'){pasteSelectedTextStyle();return;}if(!editorObjectClipboard)return;const box=document.createElement('div');box.innerHTML=editorObjectClipboard;const node=box.firstElementChild;if(!node)return;node.querySelectorAll('[data-editor-id]').forEach(n=>n.removeAttribute('data-editor-id'));node.removeAttribute('data-editor-id');const anchor=activeTextBlock||selectedParagraph()||selectedBlock()||activeImage;if(anchor&&anchor.parentElement)anchor.insertAdjacentElement('afterend',node);else root.appendChild(node);commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();}",
    "typed paste routing"
)

# Paste is deliberately type-gated in the text and image docks; only the component tool is generic.
paste_guard = """
                            function pasteTextClipboard(){
                              if(editorClipboardType==='TEXT_STYLE'){pasteSelectedTextStyle();return;}
                              if(editorClipboardType!=='OBJECT'||!editorObjectClipboard)return;
                              const box=document.createElement('div');box.innerHTML=editorObjectClipboard;
                              const node=box.firstElementChild;
                              if(!node||!(/^(P|H1|H2|H3|H4|H5|H6|LI|BLOCKQUOTE|PRE)$/.test(node.tagName))||node.querySelector('img'))return;
                              const anchor=activeTextBlock||selectedParagraph();
                              if(!anchor||anchor.dataset.editorLocked==='1')return;
                              anchor.insertAdjacentElement('afterend',node);
                              commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();
                            }
                            function pasteImageClipboard(){
                              if(editorClipboardType==='IMAGE_STYLE'){pasteSelectedImageStyle();return;}
                              if(editorClipboardType!=='OBJECT'||!editorObjectClipboard||!activeImage||activeImage.dataset.editorLocked==='1')return;
                              const box=document.createElement('div');box.innerHTML=editorObjectClipboard;
                              const node=box.firstElementChild;
                              if(!node||node.tagName!=='IMG')return;
                              activeImage.insertAdjacentElement('afterend',node);
                              commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();
                            }
"""
paste_pos = s.find("function pasteEditorObjectClipboard(){")
if paste_pos < 0:
    raise SystemExit("Could not locate generic clipboard paste function")
paste_end = s.find("reportSelection();}", paste_pos)
if paste_end < 0:
    raise SystemExit("Could not locate generic clipboard paste function end")
paste_end += len("reportSelection();}")
s = s[:paste_end] + paste_guard + s[paste_end:]
paste_command = '"粘贴" -> runJs("pasteEditorObjectClipboard()")'
positions = []
scan = 0
while True:
    at = s.find(paste_command, scan)
    if at < 0:
        break
    positions.append(at)
    scan = at + len(paste_command)
if len(positions) < 3:
    raise SystemExit("Expected text, image and component paste dock commands")
for at, replacement in reversed(list(zip(positions[:2], [
    '"粘贴" -> runJs("pasteTextClipboard()")',
    '"粘贴" -> runJs("pasteImageClipboard()")'
]))):
    s = s[:at] + replacement + s[at + len(paste_command):]

replace_once(
    "function moveSelectedBlockHorizontal(dir){const e=selectedEditableObject();if(!e||e.dataset.editorLocked==='1')return;const cell=e.closest&&e.closest('td,th');if(cell){const peer=dir<0?cell.previousElementSibling:cell.nextElementSibling;if(peer){peer.appendChild(e);commitHistory();NativeEditor.changed(root.innerHTML);}return;}const parent=e.parentElement;if(!parent||parent===root)return;const peer=dir<0?e.previousElementSibling:e.nextElementSibling;if(peer){if(dir<0)parent.insertBefore(e,peer);else parent.insertBefore(peer,e);commitHistory();NativeEditor.changed(root.innerHTML);}}",
    "function selectedMovableNode(){const e=selectedEditableObject();if(!e||e.dataset.editorLocked==='1')return null;if(e.tagName==='IMG')return e.closest('p,figure')||e;if(e.tagName==='TD'||e.tagName==='TH')return null;return e;}\n                            function moveSelectedObjectVertical(dir){const e=selectedMovableNode();if(!e)return;const p=e.parentElement;if(!p)return;const peer=dir<0?e.previousElementSibling:e.nextElementSibling;if(!peer||peer===e)return;if(dir<0)p.insertBefore(e,peer);else p.insertBefore(peer,e);commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();}\n                            function moveSelectedObjectHorizontal(dir){const e=selectedMovableNode();if(!e)return;const cell=e.closest&&e.closest('td,th');if(cell){const peer=dir<0?cell.previousElementSibling:cell.nextElementSibling;if(peer&&peer.parentElement===cell.parentElement){peer.appendChild(e);commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();}return;}const parent=e.parentElement;if(!parent)return;const peer=dir<0?e.previousElementSibling:e.nextElementSibling;if(peer){if(dir<0)parent.insertBefore(e,peer);else parent.insertBefore(peer,e);commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();}}\n                            function moveSelectedBlockHorizontal(dir){moveSelectedObjectHorizontal(dir);}",
    "safe component movement"
)
replace_once(
    "function toggleSelectedObjectLock(){const e=selectedEditableObject();if(!e)return;const locked=e.dataset.editorLocked!=='1';e.dataset.editorLocked=locked?'1':'0';if(e.tagName==='IMG')e.draggable=!locked;else e.contentEditable=locked?'false':'true';e.style.outline=locked?'1px dashed #999':'';commitHistory();NativeEditor.changed(root.innerHTML);}",
    "function toggleSelectedObjectLock(){const e=selectedEditableObject();if(!e)return;const locked=e.dataset.editorLocked!=='1';e.dataset.editorLocked=locked?'1':'0';if(e.tagName==='IMG')e.draggable=!locked;else e.contentEditable=locked?'false':'true';e.style.outline=locked?'1px dashed #999':'';commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();}\n                            function deleteSelectedObject(){const e=selectedEditableObject();if(!e||e.dataset.editorLocked==='1')return;if(e===activeImage){deleteSelectedImage();return;}e.remove();activeTextBlock=null;NativeEditor.blockSelected('');NativeEditor.textSelected('0');commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();}",
    "lock and delete generic object"
)

replace_once(
    "function setSelectedImageFilter(v){if(!activeImage)return;activeImage.style.filter=v||'none';commitHistory();NativeEditor.changed(root.innerHTML);}",
    "function setSelectedImageFilter(v){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.filter=v||'none';commitHistory();NativeEditor.changed(root.innerHTML);}\n                            function previewSelectedImageFilters(b,c,s){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.filter='brightness('+b+'%) contrast('+c+'%) saturate('+s+'%)';}\n                            function previewSelectedImageOpacity(v){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.opacity=String(Math.max(0,Math.min(100,Number(v)))/100);}\n                            function commitSelectedImageStyle(){if(!activeImage)return;commitHistory();NativeEditor.changed(root.innerHTML);}",
    "live image color and opacity preview"
)

replace_once(
    '    var blockOpacity by remember { mutableStateOf("100") }',
    '''    var blockOpacity by remember { mutableStateOf("100") }
    var imageBrightness by remember { mutableFloatStateOf(100f) }
    var imageContrast by remember { mutableFloatStateOf(100f) }
    var imageSaturation by remember { mutableFloatStateOf(100f) }
    var imageOpacity by remember { mutableFloatStateOf(100f) }
    var imageRadius by remember { mutableFloatStateOf(0f) }''',
    "image adjustment states"
)
replace_once(
    '                            Text("图片调整", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 7.dp))\n                            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {',
    '''                            Text("图片调整", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 7.dp))
                            Text("调色 · 亮度 " + imageBrightness.toInt() + "%", color = Color(0xFFAAAAAA), fontSize = 10.sp)
                            Slider(value = imageBrightness, onValueChange = { imageBrightness = it; runJs("previewSelectedImageFilters(" + it + "," + imageContrast + "," + imageSaturation + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..200f)
                            Text("对比度 " + imageContrast.toInt() + "%", color = Color(0xFFAAAAAA), fontSize = 10.sp)
                            Slider(value = imageContrast, onValueChange = { imageContrast = it; runJs("previewSelectedImageFilters(" + imageBrightness + "," + it + "," + imageSaturation + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..200f)
                            Text("饱和度 " + imageSaturation.toInt() + "%", color = Color(0xFFAAAAAA), fontSize = 10.sp)
                            Slider(value = imageSaturation, onValueChange = { imageSaturation = it; runJs("previewSelectedImageFilters(" + imageBrightness + "," + imageContrast + "," + it + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..200f)
                            Text("透明度 " + imageOpacity.toInt() + "%", color = Color(0xFFAAAAAA), fontSize = 10.sp)
                            Slider(value = imageOpacity, onValueChange = { imageOpacity = it; runJs("previewSelectedImageOpacity(" + it + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..100f)
                            Text("圆角 " + imageRadius.toInt() + "dp", color = Color(0xFFAAAAAA), fontSize = 10.sp)
                            Slider(value = imageRadius, onValueChange = { imageRadius = it; runJs("setSelectedImageRadius(" + it + " + 'px')") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..40f)
                            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                EditorTool("水平翻转") { runJs("flipSelectedImage('horizontal')") }
                                EditorTool("垂直翻转") { runJs("flipSelectedImage('vertical')") }
                                EditorTool("左对齐") { runJs("alignSelectedImage('left')") }
                                EditorTool("居中") { runJs("alignSelectedImage('center')") }
                                EditorTool("右对齐") { runJs("alignSelectedImage('right')") }
                                EditorTool("轻阴影") { runJs("setSelectedImageShadow('0 2px 6px rgba(0,0,0,.14)')") }
                                EditorTool("中阴影") { runJs("setSelectedImageShadow('0 4px 14px rgba(0,0,0,.22)')") }
                                EditorTool("强阴影") { runJs("setSelectedImageShadow('0 8px 24px rgba(0,0,0,.28)')") }
                                EditorTool("无阴影") { runJs("setSelectedImageShadow('none')") }
                                EditorTool("细边框") { runJs("setSelectedImageBorder('1px solid #dfe5e1')") }
                                EditorTool("强调边框") { runJs("setSelectedImageBorder('2px solid #159765')") }
                                EditorTool("无边框") { runJs("setSelectedImageBorder('0')") }
                                EditorTool("背景图") { runJs("setSelectedImageAsBackground()") }
                            }
                            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {''',
    "image panel controls"
)

replace_once(
    '"顺序" -> { activePanel = EditorPanel.COMPONENT; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }',
    '"顺序" -> { floatingToolbarRequest = "component"; showToolPopup = false; showCanvasPopup = false; floatingMenu = "" }',
    "text order opens component tool"
)
replace_once(
    '"复制样式" -> runJs("restoreSelection();copyTextFormat();saveSelection();")',
    '"复制样式" -> runJs("copySelectedTextStyle()")',
    "text copy style"
)
replace_once(
    '"粘贴" -> runJs("pasteSelectedImageStyle()")',
    '"粘贴" -> runJs("pasteEditorObjectClipboard()")',
    "image paste dispatch"
)
replace_once(
    '"透明度" -> runJs("setSelectedImageOpacity(70)")',
    '"透明度" -> { activePanel = EditorPanel.IMAGE; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }',
    "image opacity opens adjustable controls"
)
replace_once(
    '''"翻转" -> runJs("flipSelectedImage('horizontal')")''',
    '"翻转" -> { activePanel = EditorPanel.IMAGE; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }',
    "image flip opens horizontal and vertical controls"
)
replace_once(
    '''"对齐" -> runJs("alignSelectedImage('center')")''',
    '"对齐" -> { activePanel = EditorPanel.IMAGE; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }',
    "image alignment opens left center right controls"
)
copy_text_command = '"复制" -> runJs("copySelectedTextBlock()")'
if s.count(copy_text_command) != 2:
    raise SystemExit("Expected exactly two text/component copy dock commands")
copy_component_at = s.rfind(copy_text_command)
s = s[:copy_component_at] + s[copy_component_at:].replace(copy_text_command, '"复制" -> runJs("copySelectedObject()")', 1)
replace_once(
    '"上移" -> runJs("moveSelectedBlock(-1)")',
    '"上移" -> runJs("moveSelectedObjectVertical(-1)")',
    "component move up"
)
replace_once(
    '"下移" -> runJs("moveSelectedBlock(1)")',
    '"下移" -> runJs("moveSelectedObjectVertical(1)")',
    "component move down"
)
replace_once(
    '"左移" -> runJs("moveSelectedBlockHorizontal(-1)")',
    '"左移" -> runJs("moveSelectedObjectHorizontal(-1)")',
    "component move left"
)
replace_once(
    '"右移" -> runJs("moveSelectedBlockHorizontal(1)")',
    '"右移" -> runJs("moveSelectedObjectHorizontal(1)")',
    "component move right"
)
replace_once(
    '"复制样式" -> runJs("copyTextFormat()")',
    '"复制样式" -> runJs("copySelectedObjectStyle()")',
    "component copy style"
)
replace_once(
    '"删除" -> runJs("deleteSelectedBlock()")',
    '"删除" -> runJs("deleteSelectedObject()")',
    "component delete"
)

replace_once(
    '"存为模板" -> {\n                                                val htmlToSave = selectedBlockHtml\n                                                if (htmlToSave.isNotBlank()) { vm.saveStyle(StyleModule(vm.newId(), "组件模板", "组件模板", htmlToSave, System.currentTimeMillis().toString(), type = "component", isFavorite = true)); vm.toast("已保存到图文收藏") }\n                                                else vm.toast("当前对象暂不支持保存为组件模板")\n                                            }',
    '"存为模板" -> editor?.evaluateJavascript("selectedObjectHtml()") { raw ->\n                                                val htmlToSave = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull().orEmpty()\n                                                if (htmlToSave.isNotBlank()) { vm.saveStyle(StyleModule(vm.newId(), "组件模板", "组件模板", htmlToSave, System.currentTimeMillis().toString(), type = "component", isFavorite = true)); vm.toast("已保存到图文收藏") }\n                                                else vm.toast("请先选中要收藏的文字、图片或组件")\n                                            }',
    "save selected text image or component to favorites"
)

component_anchor = """                            } else {
                                when (selectionState.kind) {
                                    EditorSelectionKind.TABLE -> {"""
component_branch = """                            } else if (floatingToolbarRequest == "component") {
                                if (selectionState.kind == EditorSelectionKind.NONE && selectedBlockHtml.isBlank() && selectedImageHtml.isBlank() && !selectedTextActive) {
                                    Text("先在画布中选中一段文字、一张图片或一个组件，再使用组件工具", color = AppColors.TextDim, fontSize = 10.sp)
                                } else {
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("moveSelectedObjectVertical(-1)") }) { Text("↑ 上移", color = ink, fontSize = 11.sp) }
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("moveSelectedObjectVertical(1)") }) { Text("↓ 下移", color = ink, fontSize = 11.sp) }
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("moveSelectedObjectHorizontal(-1)") }) { Text("← 左移/移入左栏", color = ink, fontSize = 11.sp) }
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("moveSelectedObjectHorizontal(1)") }) { Text("右移/移入右栏 →", color = ink, fontSize = 11.sp) }
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("copySelectedObjectStyle()") }) { Text("复制样式", color = ink, fontSize = 11.sp) }
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("copySelectedObject()") }) { Text("复制对象", color = ink, fontSize = 11.sp) }
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("pasteEditorObjectClipboard()") }) { Text("粘贴", color = ink, fontSize = 11.sp) }
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("toggleSelectedObjectLock()") }) { Text("锁定/解锁", color = accent, fontSize = 11.sp) }
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("deleteSelectedObject()") }) { Text("删除", color = Color(0xFFCC5555), fontSize = 11.sp) }
                                }
                            } else {
                                when (selectionState.kind) {
                                    EditorSelectionKind.TABLE -> {"""
replace_once(component_anchor, component_branch, "component floating window action group")

required = [
    'Triple("组件", "▦", "component")',
    'floatingToolbarRequest == "component" -> "组件工具"',
    'selectedImageHtml.isNotBlank() || selectedTextActive',
    'const blankTarget=',
    'function moveSelectedObjectVertical(dir)',
    'function moveSelectedObjectHorizontal(dir)',
    'function copySelectedTextStyle()',
    'function pasteSelectedTextStyle()',
    'function previewSelectedImageFilters(b,c,s)',
    'function previewSelectedImageOpacity(v)',
    'EditorTool("水平翻转")',
    'EditorTool("轻阴影")',
    'EditorTool("背景图")',
    '先在画布中选中一段文字、一张图片或一个组件'
]
missing = [token for token in required if token not in s]
if missing:
    ERROR.write_text("Missing functional v3 features: " + ", ".join(missing) + "\n", encoding="utf-8")
    raise SystemExit("Functional v3 validation failed: " + ", ".join(missing))
EDITOR.write_text(s, encoding="utf-8")
print("Functional v3 applied: strict text/image/component selection, blank-canvas reset, component launcher/floating tools, typed clipboard, safe object movement, and live image controls.")
