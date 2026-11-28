#!/usr/bin/env python3
"""Apply Xingtu 3.0 Stage F: image transforms, stable layer identity and layout consistency."""
from pathlib import Path

ROOT = Path(".")
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
V3 = JAVA / "ui/v3/ArticleEditorScreenV3.kt"
ERROR = ROOT / "xingtu_v3_stage_f_patch_error.txt"

def fail(message):
    ERROR.write_text(message + "\\n", encoding="utf-8")
    raise SystemExit("醒图 3.0 Stage F: " + message)

def once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)

if not V3.is_file():
    fail("generated V3 editor is missing")
s = V3.read_text(encoding="utf-8")

# F1: retain and verify the dedicated image crop/color panels already applied
# to the base editor before the isolated V3 copy. Do not add duplicate controls.
required_image = [
    "ImageCropColorPanel",
    "previewSelectedImageAdvanced",
    "flipSelectedImage('horizontal')",
    "previewSelectedImageFilters",
    "resetSelectedImageColor",
]
missing_image = [token for token in required_image if token not in s]
if missing_image:
    fail("existing image editing panels were not carried into V3: " + ", ".join(missing_image))

# F2: editor IDs must remain unique after duplicating a layer. Cloning DOM
# otherwise duplicates data-editor-id and causes selection/reorder to target
# the wrong layer.
old_ensure = """function ensureEditorId(el){
                               if(!el)return '';
                               if(!el.dataset.editorId)el.dataset.editorId='ed_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,9);
                               return el.dataset.editorId;
                             }"""
new_ensure = """function ensureEditorId(el){
                               if(!el)return '';
                               let id=el.dataset.editorId||'';
                               if(id&&Array.from(root.querySelectorAll('[data-editor-id]')).some(n=>n!==el&&n.dataset.editorId===id))id='';
                               if(!id){id='ed_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,9);el.dataset.editorId=id;}
                               return id;
                             }
                             function regenerateEditorIds(el){
                               if(!el)return;
                               const nodes=[el,...Array.from(el.querySelectorAll('*'))];
                               nodes.forEach(n=>n.removeAttribute('data-editor-id'));
                               nodes.forEach(n=>ensureEditorId(n));
                             }"""
s = once(s, old_ensure, new_ensure, "unique editor object IDs")

old_dup = """function duplicateSelectedBlock(){const e=selectedBlock();if(!e)return;const c=e.cloneNode(true);c.classList.remove('selected-block');e.insertAdjacentElement('afterend',c);c.classList.add('selected-block');NativeEditor.blockSelected(c.outerHTML);commitHistory();NativeEditor.changed(root.innerHTML);}"""
stage_b_dup = """function duplicateSelectedBlock(){const e=selectedBlock();if(!e)return;const c=e.cloneNode(true);c.querySelectorAll('[data-editor-id]').forEach(n=>n.removeAttribute('data-editor-id'));c.removeAttribute('data-editor-id');c.classList.remove('selected-block');e.insertAdjacentElement('afterend',c);c.classList.add('selected-block');ensureEditorId(c);NativeEditor.blockSelected(cleanBlockHtml(c));reportSelection();commitHistory();NativeEditor.changed(root.innerHTML);}"""
new_dup = """function duplicateSelectedBlock(){const e=selectedBlock();if(!e)return;const c=e.cloneNode(true);c.classList.remove('selected-block');c.querySelectorAll('.selected-block').forEach(n=>n.classList.remove('selected-block'));regenerateEditorIds(c);e.insertAdjacentElement('afterend',c);c.classList.add('selected-block');NativeEditor.blockSelected(cleanBlockHtml(c));if(typeof reportSelection==='function')reportSelection();commitHistory();NativeEditor.changed(root.innerHTML);}"""
if old_dup in s:
    s = once(s, old_dup, new_dup, "duplicate layer identity repair")
elif stage_b_dup in s:
    s = once(s, stage_b_dup, new_dup, "duplicate layer identity repair after Stage B")
else:
    fail("duplicateSelectedBlock anchor missing or changed")

# Layer data includes selected state; selection from the canvas is reflected in
# the layer list and selecting a layer updates the same canvas object.
s = once(
    s,
    """    val locked: Boolean
)""",
    """    val locked: Boolean,
    val selected: Boolean
)""",
    "layer item selected field"
)
s = once(
    s,
    """                    locked = item.optBoolean("locked", false)
                )""",
    """                    locked = item.optBoolean("locked", false),
                    selected = item.optBoolean("selected", false)
                )""",
    "layer JSON selected parsing"
)
s = once(
    s,
    """return {id:id,tag:e.tagName.toLowerCase(),name:text.slice(0,42),visible:getComputedStyle(e).display!=='none',locked:e.dataset.editorLocked==='1'};""",
    """return {id:id,tag:e.tagName.toLowerCase(),name:text.slice(0,42),visible:getComputedStyle(e).display!=='none',locked:e.dataset.editorLocked==='1',selected:e.classList.contains('selected-block')};""",
    "layer JSON selected serialization"
)
s = once(
    s,
    """LaunchedEffect(activePanel, webReady) {
        if (activePanel == EditorPanel.LAYER && webReady) refreshLayerItems()
    }""",
    """LaunchedEffect(activePanel, webReady, html) {
        if (activePanel == EditorPanel.LAYER && webReady) refreshLayerItems()
    }""",
    "refresh layers after canvas changes"
)
old_row = """.background(if (index % 2 == 0) AppColors.Field else AppColors.Panel)
                                        .padding(horizontal = 7.dp, vertical = 5.dp),"""
new_row = """.background(if (layer.selected) accent.copy(alpha = 0.14f) else if (index % 2 == 0) AppColors.Field else AppColors.Panel)
                                        .clickable { editor?.evaluateJavascript("selectLayer(${JSONObject.quote(layer.id)})") { refreshLayerItems() } }
                                        .padding(horizontal = 7.dp, vertical = 5.dp),"""
s = once(s, old_row, new_row, "layer row selection state")

old_select = '''TextButton(onClick = { editor?.evaluateJavascript("selectLayer(${JSONObject.quote(layer.id)})", null) }, contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp)) { Text("选中", color = accent, fontSize = 9.sp) }'''
new_select = '''TextButton(onClick = { editor?.evaluateJavascript("selectLayer(${JSONObject.quote(layer.id)})") { refreshLayerItems() } }, contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp)) { Text(if (layer.selected) "已选" else "选中", color = accent, fontSize = 9.sp) }'''
s = once(s, old_select, new_select, "layer selection callback")

# Keep layout column percentages summing to exactly 100 after rounding, so
# 2/3/4-column templates do not accumulate a width gap or overflow.
old_widths = """val widths = ratios.map { (it / total * 10000).toInt() / 100f }"""
new_widths = """val widths = ratios.map { (it / total * 10000).toInt() / 100f }.toMutableList()
                                widths[widths.lastIndex] = 100f - widths.dropLast(1).sum()"""
s = once(s, old_widths, new_widths, "layout percentage normalization")

checks = {
    "image crop and color panels retained": "ImageCropColorPanel" in s and "previewSelectedImageAdvanced" in s,
    "unique IDs after duplicate": "function regenerateEditorIds(el)" in s and "regenerateEditorIds(c)" in s,
    "selected layer metadata": "selected=e.classList.contains('selected-block')" in s and "selected = item.optBoolean(\"selected\", false)" in s,
    "layer list refresh after HTML updates": "LaunchedEffect(activePanel, webReady, html)" in s,
    "layer percentage sum normalization": "widths[widths.lastIndex] = 100f - widths.dropLast(1).sum()" in s,
}
failed = [k for k,v in checks.items() if not v]
if failed:
    fail("post-patch validation failed: " + ", ".join(failed))

V3.write_text(s, encoding="utf-8")
print("Verified Stage F: existing image crop/color/flip panels retained; unique DOM IDs for duplicated layers; selected layer state synchronized; layout column percentages normalized.")
