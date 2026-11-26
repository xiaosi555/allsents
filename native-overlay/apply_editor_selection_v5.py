#!/usr/bin/env python3
"""Make WebView canvas hit-testing authoritative for text/image/component docks."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "editor_selection_v5_patch_error.txt"

if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")

s = EDITOR.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global s
    count = s.count(old)
    if count != 1:
        ERROR.write_text(f"{label}: expected one anchor, found {count}\n", encoding="utf-8")
        raise SystemExit(f"Selection v5 patch anchor mismatch [{label}]: {count}")
    s = s.replace(old, new, 1)
    print("Selection v5 applied:", label)


# The text selection outline is visual feedback only; it does not alter article markup.
replace_once(
    "#editor img.selected-image{outline:2px solid #159765;outline-offset:2px}",
    "#editor img.selected-image{outline:2px solid #159765;outline-offset:2px}#editor .selected-text-block{outline:2px solid #159765;outline-offset:2px;border-radius:2px}",
    "visible text object selection"
)

# Remove editor-only selection classes when cloning a block for storage or duplication.
replace_once(
    "function cleanBlockHtml(e){const c=e.cloneNode(true);c.classList.remove('selected-block');c.draggable=false;return c.outerHTML;}",
    "function cleanBlockHtml(e){const c=e.cloneNode(true);c.classList.remove('selected-block','selected-text-block','selected-image');c.querySelectorAll('.selected-block,.selected-text-block,.selected-image').forEach(n=>n.classList.remove('selected-block','selected-text-block','selected-image'));c.draggable=false;return c.outerHTML;}",
    "strip editor selection decorations from copied HTML"
)

pointer_start_token = "let lastTextTapId='',lastTextTapAt=0;"
click_token = "root.addEventListener('click',function(ev){"
click_end_token = "function clearDragTarget(){"
pointer_start = s.find(pointer_start_token)
click_start = s.find(click_token, pointer_start)
if pointer_start < 0 or click_start < 0:
    ERROR.write_text("Could not locate the v3 text pointer/click handlers\n", encoding="utf-8")
    raise SystemExit("Selection v5 could not locate the v3 canvas event handlers")

# Replace the old text-only pointerdown handler with one hit-test path for all canvas objects.
new_pointer = r"""function editorHitElement(node){
                               if(!node)return null;
                               return node.nodeType===1?node:(node.parentElement||null);
                             }
                             function findEditorTextBlock(node){
                               const el=editorHitElement(node);
                               if(!el||!root.contains(el))return null;
                               if(el.closest&&el.closest('img,svg,video,iframe,canvas'))return null;
                               const semantic=el.closest?el.closest('p,h1,h2,h3,h4,h5,h6,li,blockquote,pre,figcaption,td,th'):null;
                               if(semantic&&root.contains(semantic)&&semantic.textContent.trim())return semantic;
                               let current=el;
                               while(current&&current!==root){
                                 if(/^(DIV|SECTION|SPAN|A|STRONG|B|EM|I|U)$/.test(current.tagName)){
                                   const ownsText=Array.from(current.childNodes).some(n=>n.nodeType===3&&n.nodeValue.trim());
                                   if(ownsText&&current.textContent.trim())return current;
                                 }
                                 current=current.parentElement;
                               }
                               return null;
                             }
                             function clearSelectedText(){
                               if(activeTextBlock)activeTextBlock.classList.remove('selected-text-block');
                               root.querySelectorAll('.selected-text-block').forEach(e=>e.classList.remove('selected-text-block'));
                               activeTextBlock=null;
                             }
                             function clearSelectedBlocks(){
                               root.querySelectorAll('.selected-block').forEach(e=>{e.classList.remove('selected-block');e.draggable=false;});
                               NativeEditor.blockSelected('');
                             }
                             function clearSelectedImage(){
                               if(activeImage)activeImage.classList.remove('selected-image');
                               root.querySelectorAll('.selected-image').forEach(e=>e.classList.remove('selected-image'));
                               activeImage=null;
                               NativeEditor.imageSelected('');
                             }
                             function setCanvasTextSelection(block,ev){
                               clearSelectedImage();clearSelectedBlocks();clearSelectedText();
                               activeTextBlock=block;
                               activeTextBlock.classList.add('selected-text-block');
                               NativeEditor.imageSelected('');NativeEditor.blockSelected('');NativeEditor.textSelected('1');
                               const id=ensureEditorId(block),now=Date.now(),second=(id===lastTextTapId&&now-lastTextTapAt<1150);
                               lastTextTapId=id;lastTextTapAt=now;
                               if(second&&block.dataset.editorLocked!=='1'&&!componentDragMode){
                                 root.contentEditable='true';
                                 let range=null;
                                 if(document.caretRangeFromPoint&&ev&&Number.isFinite(ev.clientX)&&Number.isFinite(ev.clientY)){
                                   try{range=document.caretRangeFromPoint(ev.clientX,ev.clientY);}catch(e){}
                                 }
                                 if(!range&&document.caretPositionFromPoint&&ev&&Number.isFinite(ev.clientX)&&Number.isFinite(ev.clientY)){
                                   try{const pos=document.caretPositionFromPoint(ev.clientX,ev.clientY);if(pos){range=document.createRange();range.setStart(pos.offsetNode,pos.offset);range.collapse(true);}}catch(e){}
                                 }
                                 if(!range||!block.contains(range.startContainer)){
                                   range=document.createRange();range.selectNodeContents(block);range.collapse(false);
                                 }
                                 const selection=window.getSelection();
                                 if(selection){selection.removeAllRanges();selection.addRange(range);}
                                 savedRange=range.cloneRange();
                                 root.focus();
                                 if(typeof saveSelection==='function')saveSelection();
                               }else{
                                 root.contentEditable='false';
                                 savedRange=null;
                                 const selection=window.getSelection();if(selection)selection.removeAllRanges();
                               }
                               reportSelection();
                             }
                             function handleCanvasSelection(ev,fromPointer){
                               if(componentDragMode)return;
                               let hit=editorHitElement(ev&&ev.target);
                               if(fromPointer&&ev&&typeof document.elementFromPoint==='function'&&Number.isFinite(ev.clientX)&&Number.isFinite(ev.clientY)){
                                 const pointHit=document.elementFromPoint(ev.clientX,ev.clientY);
                                 if(pointHit&&root.contains(pointHit))hit=pointHit;
                               }
                               if(!hit||!root.contains(hit))return;
                               const image=hit.closest?hit.closest('img'):null;
                               if(image&&root.contains(image)){
                                 clearSelectedText();clearSelectedBlocks();clearSelectedImage();
                                 activeImage=image;
                                 if(activeImage.dataset.originalWidth===undefined){
                                   activeImage.dataset.originalWidth=activeImage.style.width;
                                   activeImage.dataset.originalHeight=activeImage.style.height;
                                   activeImage.dataset.originalObjectFit=activeImage.style.objectFit;
                                   activeImage.dataset.originalObjectPosition=activeImage.style.objectPosition;
                                 }
                                 activeImage.classList.add('selected-image');
                                 root.contentEditable='false';
                                 savedRange=null;
                                 const selection=window.getSelection();if(selection)selection.removeAllRanges();
                                 NativeEditor.imageSelected(activeImage.outerHTML);NativeEditor.textSelected('0');NativeEditor.blockSelected('');
                                 reportSelection();
                                 return;
                               }
                               const textBlock=findEditorTextBlock(hit);
                               if(textBlock){setCanvasTextSelection(textBlock,ev);return;}
                               const structural=hit.closest?hit.closest('table,svg,video,iframe,canvas,details,hr,[data-editor-component="1"]'):null;
                               if(structural&&root.contains(structural)){
                                 clearSelectedImage();clearSelectedText();clearSelectedBlocks();
                                 const selected=topLevelAt(structural)||structural;
                                 selected.classList.add('selected-block');
                                 selected.draggable=selected.dataset.editorLocked!=='1';
                                 root.contentEditable='false';
                                 savedRange=null;
                                 const selection=window.getSelection();if(selection)selection.removeAllRanges();
                                 NativeEditor.imageSelected('');NativeEditor.textSelected('0');NativeEditor.blockSelected(cleanBlockHtml(selected));
                                 reportSelection();
                                 return;
                               }
                               // Every remaining point inside the article canvas is blank canvas,
                               // not an implicit selection of its outer paragraph/section wrapper.
                               clearSelectedImage();clearSelectedText();clearSelectedBlocks();
                               root.contentEditable='true';
                               savedRange=null;
                               const selection=window.getSelection();if(selection)selection.removeAllRanges();
                               NativeEditor.imageSelected('');NativeEditor.textSelected('0');NativeEditor.blockSelected('');
                               reportSelection();
                             }
                             let lastTextTapId='',lastTextTapAt=0,lastCanvasPointerAt=0;
                             root.addEventListener('pointerdown',function(ev){
                               if(ev.button!==undefined&&ev.button!==0)return;
                               lastCanvasPointerAt=Date.now();
                               handleCanvasSelection(ev,true);
                             },true);
                             """
s = s[:pointer_start] + new_pointer + s[click_start:]

# Native/synthetic keyboard clicks have no preceding pointerdown; route them through the same resolver.
click_start = s.find(click_token, pointer_start)
click_end = s.find(click_end_token, click_start)
if click_start < 0 or click_end < 0:
    ERROR.write_text("Could not locate the canvas click listener end marker\n", encoding="utf-8")
    raise SystemExit("Selection v5 could not delimit the canvas click listener")
click_start = s.rfind("\n", 0, click_start) + 1
click_end = s.rfind("\n", 0, click_end) + 1
new_click = r"""                             root.addEventListener('click',function(ev){
                               if(ev.detail===0||Date.now()-lastCanvasPointerAt>700)handleCanvasSelection(ev,false);
                             });
"""
s = s[:click_start] + new_click + s[click_end:]

# Text template/copy/duplicate helpers already prefer activeTextBlock in functional v3.

# Complete the two text-dock actions that were still routed to legacy controls.
replace_once(
    '"复制样式" -> runJs("restoreSelection();copyTextFormat();saveSelection();")',
    '"复制样式" -> runJs("copySelectedTextStyle()")',
    "text dock copy style uses typed text-style clipboard"
)
replace_once(
    '"顺序" -> { activePanel = EditorPanel.COMPONENT; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }',
    '"顺序" -> { floatingToolbarRequest = "component"; floatingMenu = ""; showToolPopup = false; showCanvasPopup = false }',
    "text order opens selected-object component tools"
)
replace_once(
    "if(!node||!(/^(P|H1|H2|H3|H4|H5|H6|LI|BLOCKQUOTE|PRE)$/.test(node.tagName))||node.querySelector('img'))return;",
    "if(!node||!(/^(P|H1|H2|H3|H4|H5|H6|LI|BLOCKQUOTE|PRE|DIV|SECTION|SPAN|STRONG|B|EM|I|U|TD|TH)$/.test(node.tagName))||node.querySelector('img'))return;",
    "text paste supports every hit-tested text container"
)

# The dock is a pure projection of selectionChanged. Blank means DEFAULT; text/image/component
# selection must never be inferred from a stale toolbar boolean.
callback_old = """                            { state ->
                                selectionState = state
                                selectedTextActive = state.kind == EditorSelectionKind.TEXT_BLOCK ||
                                    state.kind == EditorSelectionKind.TEXT_RANGE || state.kind == EditorSelectionKind.CARET
                                selectedDockMode = when (state.kind) {
                                    EditorSelectionKind.TEXT_BLOCK, EditorSelectionKind.TEXT_RANGE, EditorSelectionKind.CARET -> "TEXT"
                                    EditorSelectionKind.IMAGE -> "IMAGE"
                                    EditorSelectionKind.COMPONENT, EditorSelectionKind.TABLE, EditorSelectionKind.LAYOUT, EditorSelectionKind.MULTI_BLOCK -> "COMPONENT"
                                    else -> "DEFAULT"
                                }
                                if (state.kind == EditorSelectionKind.NONE) { floatingMenu = ""; floatingToolbarRequest = "" }
                            }"""
callback_new = """                            { state ->
                                selectionState = state
                                selectedTextActive = state.kind == EditorSelectionKind.TEXT_BLOCK ||
                                    state.kind == EditorSelectionKind.TEXT_RANGE || state.kind == EditorSelectionKind.CARET
                                selectedDockMode = when (state.kind) {
                                    EditorSelectionKind.TEXT_BLOCK, EditorSelectionKind.TEXT_RANGE, EditorSelectionKind.CARET -> "TEXT"
                                    EditorSelectionKind.IMAGE -> "IMAGE"
                                    EditorSelectionKind.COMPONENT, EditorSelectionKind.TABLE, EditorSelectionKind.LAYOUT, EditorSelectionKind.MULTI_BLOCK -> "COMPONENT"
                                    else -> "DEFAULT"
                                }
                                if (state.kind == EditorSelectionKind.NONE) {
                                    selectedTextActive = false
                                    floatingMenu = ""
                                    floatingToolbarRequest = ""
                                }
                            }"""
replace_once(callback_old, callback_new, "selection callback is the single dock state source")

required = [
    "function handleCanvasSelection(ev,fromPointer)",
    "function findEditorTextBlock(node)",
    "selectedDockMode = when (state.kind)",
    "if (state.kind == EditorSelectionKind.NONE)",
    "lastCanvasPointerAt=Date.now()",
    "selected-text-block"
]
missing = [token for token in required if token not in s]
if missing:
    ERROR.write_text("Missing final selection tokens: " + ", ".join(missing) + "\n", encoding="utf-8")
    raise SystemExit("Selection v5 final validation failed: " + ", ".join(missing))

EDITOR.write_text(s, encoding="utf-8")
print("Editor selection v5 applied: pointer hit-testing, text/image/component routing, blank-canvas reset and dock-state synchronization.")
