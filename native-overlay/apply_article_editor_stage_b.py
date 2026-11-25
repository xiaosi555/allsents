#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
UI = JAVA / "ui"
EDITOR = UI / "ArticleEditorScreen.kt"

def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        detail = f"Stage B patch anchor mismatch [{label}]: expected 1, found {count}"
        (ROOT / "article_editor_stage_b_patch_error.txt").write_text(detail + "\\n", encoding="utf-8")
        raise SystemExit(detail)
    print("Stage B applied:", label)
    return source.replace(old, new, 1)

s = EDITOR.read_text(encoding="utf-8")

s = replace_once(
    s,
    '''private class ArticleEditorBridge(private val onChange: (String) -> Unit, private val onBlock: (String) -> Unit, private val onImage: (String) -> Unit, private val onText: (Boolean) -> Unit) {
    private val main = Handler(Looper.getMainLooper())
    @JavascriptInterface fun changed(value: String) { main.post { onChange(value) } }
    @JavascriptInterface fun blockSelected(value: String) { main.post { onBlock(value) } }
    @JavascriptInterface fun imageSelected(value: String) { main.post { onImage(value) } }
    @JavascriptInterface fun textSelected(value: String) { main.post { onText(value == "1") } }
}

private enum class EditorPanel(val label: String) {''',
    '''private enum class EditorSelectionKind {
    NONE, TEXT_BLOCK, TEXT_RANGE, CARET, IMAGE, COMPONENT, TABLE, LAYOUT, MULTI_BLOCK, PREVIEW
}

private data class EditorSelectionState(
    val kind: EditorSelectionKind = EditorSelectionKind.NONE,
    val objectId: String = "",
    val collapsed: Boolean = true,
    val x: Float = 0f,
    val y: Float = 0f,
    val width: Float = 0f,
    val height: Float = 0f,
    val selectedIds: List<String> = emptyList()
)

private class ArticleEditorBridge(
    private val onChange: (String) -> Unit,
    private val onBlock: (String) -> Unit,
    private val onImage: (String) -> Unit,
    private val onText: (Boolean) -> Unit,
    private val onSelection: (EditorSelectionState) -> Unit
) {
    private val main = Handler(Looper.getMainLooper())
    @JavascriptInterface fun changed(value: String) { main.post { onChange(value) } }
    @JavascriptInterface fun blockSelected(value: String) { main.post { onBlock(value) } }
    @JavascriptInterface fun imageSelected(value: String) { main.post { onImage(value) } }
    @JavascriptInterface fun textSelected(value: String) { main.post { onText(value == "1") } }
    @JavascriptInterface fun selectionChanged(value: String) {
        val state = runCatching {
            val json = JSONObject(value)
            val kind = runCatching { EditorSelectionKind.valueOf(json.optString("kind", "NONE")) }
                .getOrDefault(EditorSelectionKind.NONE)
            val idsJson = json.optJSONArray("selectedIds")
            val ids = if (idsJson == null) emptyList() else
                (0 until idsJson.length()).mapNotNull { index -> idsJson.optString(index).takeIf { it.isNotBlank() } }
            EditorSelectionState(
                kind = kind,
                objectId = json.optString("objectId", ""),
                collapsed = json.optBoolean("collapsed", true),
                x = json.optDouble("x", 0.0).toFloat(),
                y = json.optDouble("y", 0.0).toFloat(),
                width = json.optDouble("width", 0.0).toFloat(),
                height = json.optDouble("height", 0.0).toFloat(),
                selectedIds = ids
            )
        }.getOrDefault(EditorSelectionState())
        main.post { onSelection(state) }
    }
}

private enum class EditorPanel(val label: String) {''',
    "structured selection state and bridge"
)

s = replace_once(
    s,
    '''    var selectedTextActive by remember { mutableStateOf(false) }
    var floatingMenu by remember { mutableStateOf("") }''',
    '''    var selectedTextActive by remember { mutableStateOf(false) }
    var selectionState by remember { mutableStateOf(EditorSelectionState()) }
    var floatingMenu by remember { mutableStateOf("") }''',
    "Compose selection state"
)

s = replace_once(
    s,
    '''                            { value -> selectedTextActive = value; if (value) floatingMenu = "" }
                        ), "NativeEditor")''',
    '''                            { value -> selectedTextActive = value; if (value) floatingMenu = "" },
                            { state ->
                                selectionState = state
                                selectedTextActive = state.kind == EditorSelectionKind.TEXT_BLOCK ||
                                    state.kind == EditorSelectionKind.TEXT_RANGE || state.kind == EditorSelectionKind.CARET
                                if (state.kind == EditorSelectionKind.NONE) floatingMenu = ""
                            }
                        ), "NativeEditor")''',
    "Bridge selection callback wiring"
)

selection_helpers = '''                             function ensureEditorId(el){
                               if(!el)return '';
                               if(!el.dataset.editorId)el.dataset.editorId='ed_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,9);
                               return el.dataset.editorId;
                             }
                             function reportSelection(){
                               const sel=window.getSelection(),range=sel&&sel.rangeCount?sel.getRangeAt(0):null;
                               const blocks=Array.from(root.querySelectorAll('.selected-block'));
                               let kind='NONE',target=null,collapsed=true,rect=null;
                               if(activeImage){kind='IMAGE';target=activeImage;}
                               else if(blocks.length>1){kind='MULTI_BLOCK';target=blocks[blocks.length-1];}
                               else if(range&&root.contains(range.commonAncestorContainer)){
                                 collapsed=range.collapsed;
                                 const node=range.startContainer.nodeType===1?range.startContainer:range.startContainer.parentElement;
                                 target=topLevelAt(node)||node;
                                 if(!collapsed)kind='TEXT_RANGE';
                                 else if(target&&/^(P|H1|H2|H3|H4|BLOCKQUOTE|PRE|UL|OL)$/.test(target.tagName))kind='CARET';
                                 else if(blocks.length===1){
                                   target=blocks[0];
                                   if(target.tagName==='TABLE'||target.querySelector('table'))kind='TABLE';
                                   else kind='COMPONENT';
                                 }else kind='CARET';
                               }else if(blocks.length===1){
                                 target=blocks[0];
                                 if(target.tagName==='TABLE'||target.querySelector('table'))kind='TABLE';
                                 else if(/^(P|H1|H2|H3|H4|BLOCKQUOTE|PRE|UL|OL)$/.test(target.tagName))kind='TEXT_BLOCK';
                                 else kind='COMPONENT';
                               }
                               if(!target&&activeImage){kind='IMAGE';target=activeImage;}
                               if(range&&root.contains(range.commonAncestorContainer))rect=range.getBoundingClientRect();
                               if((!rect||(!rect.width&&!rect.height))&&target)rect=target.getBoundingClientRect();
                               const ids=blocks.map(el=>ensureEditorId(el));
                               NativeEditor.selectionChanged(JSON.stringify({
                                 kind:kind,objectId:ensureEditorId(target),collapsed:collapsed,
                                 x:rect?rect.left:0,y:rect?rect.top:0,width:rect?rect.width:0,height:rect?rect.height:0,
                                 selectedIds:ids
                               }));
                             }
'''
s = replace_once(
    s,
    '''                            function duplicateSelectedBlock(){const e=selectedBlock();if(!e)return;const c=e.cloneNode(true);c.classList.remove('selected-block');e.insertAdjacentElement('afterend',c);c.classList.add('selected-block');NativeEditor.blockSelected(c.outerHTML);commitHistory();NativeEditor.changed(root.innerHTML);}''',
    '''                             function duplicateSelectedBlock(){const e=selectedBlock();if(!e)return;const c=e.cloneNode(true);c.querySelectorAll('[data-editor-id]').forEach(n=>n.removeAttribute('data-editor-id'));c.removeAttribute('data-editor-id');c.classList.remove('selected-block');e.insertAdjacentElement('afterend',c);c.classList.add('selected-block');ensureEditorId(c);NativeEditor.blockSelected(cleanBlockHtml(c));reportSelection();commitHistory();NativeEditor.changed(root.innerHTML);}''',
    "regenerate stable IDs when duplicating blocks"
)

s = replace_once(
    s,
    '''                            function saveSelection(){const s=window.getSelection();if(s&&s.rangeCount){savedRange=s.getRangeAt(0).cloneRange();}}
                            function restoreSelection(){root.focus();const s=window.getSelection();if(savedRange&&s){s.removeAllRanges();s.addRange(savedRange);}}''',
    selection_helpers + '''                             function saveSelection(){
                               const sel=window.getSelection();
                               if(sel&&sel.rangeCount){
                                 const range=sel.getRangeAt(0);
                                 if(root.contains(range.commonAncestorContainer))savedRange=range.cloneRange();
                               }
                             }
                             function restoreSelection(){
                               root.focus();
                               const sel=window.getSelection();
                               if(!savedRange||!sel||!root.contains(savedRange.commonAncestorContainer))return false;
                               try{sel.removeAllRanges();sel.addRange(savedRange);return true;}
                               catch(e){savedRange=null;return false;}
                             }''',
    "safe range save restore and selection payload"
)

s = replace_once(
    s,
    '''                              }
                            });
                            function clearDragTarget(){''',
    '''                               }
                               reportSelection();
                             });
                             function clearDragTarget(){''',
    "report selection after canvas click"
)

s = replace_once(
    s,
    '''                            function applyInlineStyle(styles){const sel=window.getSelection();if(!sel||!sel.rangeCount||sel.isCollapsed)return false;''',
    '''                            function applyInlineStyle(styles){restoreSelection();const sel=window.getSelection();if(!sel||!sel.rangeCount||sel.isCollapsed)return false;''',
    "restore selection before inline formatting"
)

s = replace_once(
    s,
    '''                            function styleSelectionOrParagraph(prop,value){const sel=window.getSelection();if(sel&&!sel.isCollapsed){const styles={};styles[prop]=value;applyInlineStyle(styles);}else styleSelectedParagraph(prop,value);}''',
    '''                            function styleSelectionOrParagraph(prop,value){restoreSelection();const sel=window.getSelection();if(sel&&!sel.isCollapsed){const styles={};styles[prop]=value;applyInlineStyle(styles);}else styleSelectedParagraph(prop,value);}''',
    "restore selection before selection or paragraph styling"
)

s = replace_once(
    s,
    '''                            document.addEventListener('selectionchange',()=>{if(document.activeElement===root)saveSelection();});''',
    '''                            document.addEventListener('selectionchange',()=>{if(document.activeElement===root){saveSelection();reportSelection();}});''',
    "selectionchange bridge updates"
)

# Bottom navigation remains mounted independently of the adaptive tool sheet.


EDITOR.write_text(s, encoding="utf-8")

# Guard against accidental omission of any required Stage B foundation.
result = EDITOR.read_text(encoding="utf-8")
required = [
    "enum class EditorSelectionKind",
    "data class EditorSelectionState",
    "fun selectionChanged(value: String)",
    "function ensureEditorId(el)",
    "function reportSelection()",
    "saveSelection();reportSelection();",
    "if (!previewMode) {",
    "showToolPopup && selectedImageHtml.isBlank()",
    "heightIn(min = 100.dp, max = 300.dp)",
    "root.contains(savedRange.commonAncestorContainer)"
]
missing = [token for token in required if token not in result]
if missing:
    raise SystemExit("Stage B post-patch validation failed: " + ", ".join(missing))
print("Stage B selection model, bridge payload, stable DOM IDs, safe Range restore and persistent bottom tool dock applied.")
