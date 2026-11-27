#!/usr/bin/env python3
"""Unify WebView canvas history with Compose image-panel state and use 5dp slider tracks."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
s = P.read_text(encoding="utf-8")


def once(old: str, new: str, label: str):
    global s
    if new in s:
        return
    count = s.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, got {count}")
    s = s.replace(old, new, 1)


# Use a thin 5dp track for every editor slider without shrinking its touch target.
slider_calls = len(re.findall(r"(?<![A-Za-z0-9_])Slider\(", s))
if slider_calls < 5:
    raise SystemExit(f"Unexpected Slider count: {slider_calls}")
if "track = { sliderState ->" not in s:
    s = re.sub(
        r"(?<![A-Za-z0-9_])Slider\(",
        "Slider(\n        track = { sliderState -> val range = sliderState.valueRange; val fraction = if (range.endInclusive > range.start) ((sliderState.value - range.start) / (range.endInclusive - range.start)).coerceIn(0f, 1f) else 0f; Canvas(Modifier.fillMaxWidth().height(5.dp)) { val centerY = size.height / 2f; drawLine(Color(0xFF4A4A4A), Offset(0f, centerY), Offset(size.width, centerY), strokeWidth = size.height, cap = androidx.compose.ui.graphics.StrokeCap.Round); drawLine(Color(0xFF4A91FF), Offset(0f, centerY), Offset(size.width * fraction, centerY), strokeWidth = size.height, cap = androidx.compose.ui.graphics.StrokeCap.Round) } },",
        s,
    )

# Record DOM-backed edits as well as input events. Preview-only CSS classes are excluded.
old_history = """                            function commitHistory(){const value=root.innerHTML;if(snapshots[historyIndex]===value)return;snapshots=snapshots.slice(0,historyIndex+1);snapshotChars=snapshots.reduce((n,item)=>n+item.length,0);snapshots.push(value);snapshotChars+=value.length;while((snapshots.length>40||snapshotChars>8*1024*1024)&&snapshots.length>2){const removed=snapshots.shift();snapshotChars-=removed.length;historyIndex=Math.max(0,historyIndex-1);}historyIndex=snapshots.length-1;}
                            function restoreHistoryCaret(){root.focus();const r=document.createRange();r.selectNodeContents(root);r.collapse(false);const sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);saveSelection();}
                            function undoEditor(){commitHistory();if(historyIndex<=0)return;historyIndex--;root.innerHTML=snapshots[historyIndex];restoreHistoryCaret();NativeEditor.changed(root.innerHTML);}
                            function redoEditor(){if(historyIndex>=snapshots.length-1)return;historyIndex++;root.innerHTML=snapshots[historyIndex];restoreHistoryCaret();NativeEditor.changed(root.innerHTML);}
                            function setEditorHtml(v){root.innerHTML=v||'<p><br></p>';snapshots=[root.innerHTML];historyIndex=0;snapshotChars=snapshots[0].length;activeImage=null;NativeEditor.imageSelected('');NativeEditor.blockSelected('');saveSelection();}
"""
new_history = """                            let historyObserver=null,historyCommitTimer=null,historyRestoring=false;
                            function commitHistory(){const value=root.innerHTML;if(snapshots[historyIndex]===value)return;snapshots=snapshots.slice(0,historyIndex+1);snapshotChars=snapshots.reduce((n,item)=>n+item.length,0);snapshots.push(value);snapshotChars+=value.length;while((snapshots.length>40||snapshotChars>8*1024*1024)&&snapshots.length>2){const removed=snapshots.shift();snapshotChars-=removed.length;historyIndex=Math.max(0,historyIndex-1);}historyIndex=snapshots.length-1;}
                            function scheduleHistoryCommit(){if(historyRestoring)return;if(historyCommitTimer)clearTimeout(historyCommitTimer);historyCommitTimer=setTimeout(()=>{historyCommitTimer=null;commitHistory();try{NativeEditor.changed(root.innerHTML);}catch(e){}},480);}
                            function flushHistoryCommit(){if(timer){clearTimeout(timer);timer=null;}if(historyCommitTimer){clearTimeout(historyCommitTimer);historyCommitTimer=null;}commitHistory();}
                            function installHistoryObserver(){if(typeof MutationObserver==='undefined')return;if(historyObserver)historyObserver.disconnect();historyObserver=new MutationObserver(records=>{if(historyRestoring)return;const meaningful=records.some(r=>{if(r.type==='attributes')return r.attributeName!=='class'&&r.attributeName!=='contenteditable'&&r.attributeName!=='spellcheck';if(r.type==='childList'){if(r.target&&r.target.closest&&r.target.closest('.text2-selection-preview'))return false;const nodes=[...r.addedNodes,...r.removedNodes];if(nodes.some(n=>n.nodeType===1&&n.classList&&n.classList.contains('text2-selection-preview')))return false;}return true;});if(meaningful)scheduleHistoryCommit();});historyObserver.observe(root,{subtree:true,childList:true,characterData:true,attributes:true});}
                            function restoreHistoryCaret(){root.focus();const r=document.createRange();r.selectNodeContents(root);r.collapse(false);const sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);saveSelection();}
                            function restoreHistorySnapshot(html){const imgs=Array.from(root.querySelectorAll('img'));const selectedImageIndex=activeImage?imgs.indexOf(activeImage):imgs.findIndex(e=>e.classList.contains('selected-image'));const children=Array.from(root.children);const selectedBlockIndex=activeTextBlock?children.indexOf(activeTextBlock):children.findIndex(e=>e.classList.contains('selected-block')||e.classList.contains('selected-text-block'));historyRestoring=true;if(historyCommitTimer){clearTimeout(historyCommitTimer);historyCommitTimer=null;}if(historyObserver)historyObserver.disconnect();root.innerHTML=html;installHistoryObserver();historyRestoring=false;const nextImgs=root.querySelectorAll('img');activeImage=selectedImageIndex>=0?(nextImgs[selectedImageIndex]||null):null;if(activeImage)activeImage.classList.add('selected-image');const nextChildren=Array.from(root.children);activeTextBlock=selectedBlockIndex>=0?(nextChildren[selectedBlockIndex]||null):null;if(activeTextBlock)activeTextBlock.classList.add('selected-text-block');restoreHistoryCaret();try{NativeEditor.imageSelected(activeImage?activeImage.outerHTML:'');NativeEditor.blockSelected(activeTextBlock?activeTextBlock.outerHTML:'');NativeEditor.changed(root.innerHTML);if(typeof notifyCanvasPreview==='function')notifyCanvasPreview();}catch(e){}}
                            function undoEditor(){flushHistoryCommit();if(historyIndex<=0)return;historyIndex--;restoreHistorySnapshot(snapshots[historyIndex]);}
                            function redoEditor(){flushHistoryCommit();if(historyIndex>=snapshots.length-1)return;historyIndex++;restoreHistorySnapshot(snapshots[historyIndex]);}
                            function setEditorHtml(v){historyRestoring=true;if(timer){clearTimeout(timer);timer=null;}if(historyCommitTimer){clearTimeout(historyCommitTimer);historyCommitTimer=null;}if(historyObserver)historyObserver.disconnect();root.innerHTML=v||'<p><br></p>';snapshots=[root.innerHTML];historyIndex=0;snapshotChars=snapshots[0].length;activeImage=null;activeTextBlock=null;NativeEditor.imageSelected('');NativeEditor.blockSelected('');saveSelection();installHistoryObserver();historyRestoring=false;}
"""
once(old_history, new_history, "history manager core")

old_input = "                            root.addEventListener('input',()=>{saveSelection();clearTimeout(timer);timer=setTimeout(()=>{commitHistory();NativeEditor.changed(root.innerHTML);},300);});"
new_input = "                            installHistoryObserver();\n                            root.addEventListener('input',()=>{saveSelection();clearTimeout(timer);timer=setTimeout(()=>{flushHistoryCommit();NativeEditor.changed(root.innerHTML);},300);});"
once(old_input, new_input, "install history observer")

# Hydrate the crop/color panel from the selected image's serialized style state.
old_panel = """private fun ImageCropColorPanel(kind: String, tab: String, onJs: (String) -> Unit, onPixelCrop: (Float) -> Unit = {}, onCustomCrop: () -> Unit = {}) {
 var a by remember { mutableFloatStateOf(100f) }; var b by remember { mutableFloatStateOf(100f) }; var c by remember { mutableFloatStateOf(100f) }
 var angle by remember { mutableFloatStateOf(0f) }; var x by remember { mutableFloatStateOf(50f) }; var y by remember { mutableFloatStateOf(50f) }
 var exposure by remember { mutableFloatStateOf(0f) }; var highlights by remember { mutableFloatStateOf(0f) }; var shadows by remember { mutableFloatStateOf(0f) }
 var tint by remember { mutableFloatStateOf(0f) }; var vibrance by remember { mutableFloatStateOf(0f) }; var hue by remember { mutableFloatStateOf(0f) }
 var gray by remember { mutableFloatStateOf(0f) }; var sepia by remember { mutableFloatStateOf(0f) }; var blur by remember { mutableFloatStateOf(0f) }
"""
new_panel = '''private fun ImageCropColorPanel(kind: String, tab: String, selectedImageHtml: String, onJs: (String) -> Unit, onPixelCrop: (Float) -> Unit = {}, onCustomCrop: () -> Unit = {}) {
 fun imageValue(key: String, fallback: Float): Float = Regex("""data-$key=[\"']([^\"']+)[\"']""").find(selectedImageHtml)?.groupValues?.getOrNull(1)?.toFloatOrNull() ?: fallback
 var a by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-brightness", 100f)) }; var b by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-contrast", 100f)) }; var c by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-saturation", 100f)) }
 var angle by remember(selectedImageHtml) { mutableFloatStateOf(if (kind == "color") imageValue("color-temperature", 0f) else imageValue("editor-rotation", 0f)) }; var x by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("editor-crop-x", 50f)) }; var y by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("editor-crop-y", 50f)) }
 var exposure by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-exposure", 0f)) }; var highlights by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-highlights", 0f)) }; var shadows by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-shadows", 0f)) }
 var tint by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-tint", 0f)) }; var vibrance by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-vibrance", 0f)) }; var hue by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-hue", 0f)) }
 var gray by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-grayscale", 0f)) }; var sepia by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-sepia", 0f)) }; var blur by remember(selectedImageHtml) { mutableFloatStateOf(imageValue("color-blur", 0f)) }
'''
once(old_panel, new_panel, "image panel state hydration")
once('''EditorPanel.IMAGE_CROP -> ImageCropColorPanel("crop", imageCropMainTab, { runJs(it) }, { cropSelectedImagePixels(it) }, { openCustomImageCrop() })''','''EditorPanel.IMAGE_CROP -> ImageCropColorPanel("crop", imageCropMainTab, selectedImageHtml, { runJs(it) }, { cropSelectedImagePixels(it) }, { openCustomImageCrop() })''', "crop panel binding")
once('''EditorPanel.IMAGE_COLOR -> ImageCropColorPanel("color", imageColorMainTab, { runJs(it) })''','''EditorPanel.IMAGE_COLOR -> ImageCropColorPanel("color", imageColorMainTab, selectedImageHtml, { runJs(it) })''', "color panel binding")

# Commit slider previews to history and send selected image state back to Compose.
old_commit = "function commitSelectedImageStyle(){const el=selectedImageTarget();if(!el)return;try{if(typeof commitHistory==='function')commitHistory();}catch(e){}try{if(typeof NativeEditor!=='undefined'&&typeof NativeEditor.changed==='function')NativeEditor.changed(root.innerHTML);}catch(e){}syncSelectedImageLive();}"
new_commit = "function commitSelectedImageStyle(){const el=selectedImageTarget();if(!el)return;try{if(typeof commitHistory==='function')commitHistory();}catch(e){}try{if(typeof NativeEditor!=='undefined'&&typeof NativeEditor.changed==='function')NativeEditor.changed(root.innerHTML);if(typeof NativeEditor!=='undefined'&&typeof NativeEditor.imageSelected==='function')NativeEditor.imageSelected(el.outerHTML);}catch(e){}syncSelectedImageLive();}"
once(old_commit, new_commit, "image panel state callback")

old_filters = """                              el.style.filter='brightness('+Math.max(0,Math.min(300,Number(b)||100))+'%) contrast('+Math.max(0,Math.min(300,Number(c)||100))+'%) saturate('+Math.max(0,Math.min(300,Number(sat)||100))+'%)';
                              syncSelectedImageLive();scheduleImageColorCommit();"""
new_filters = """                              el.dataset.colorBrightness=String(Number(b)||100);el.dataset.colorContrast=String(Number(c)||100);el.dataset.colorSaturation=String(Number(sat)||100);
                              el.style.filter='brightness('+Math.max(0,Math.min(300,Number(b)||100))+'%) contrast('+Math.max(0,Math.min(300,Number(c)||100))+'%) saturate('+Math.max(0,Math.min(300,Number(sat)||100))+'%)';
                              syncSelectedImageLive();scheduleImageColorCommit();"""
once(old_filters, new_filters, "persist basic image adjustment values")

old_advanced = """                              const f=['brightness('+Math.max(0,Math.min(300,Number(b)||100))+'%)','contrast('+Math.max(0,Math.min(300,Number(c)||100))+'%)','saturate('+Math.max(0,Math.min(300,Number(sat)||100))+'%)','hue-rotate('+((Number(hue)||0)+(Number(tint)||0)*.12)+'deg)'];"""
new_advanced = """                              el.dataset.colorBrightness=String(Number(b)||100);el.dataset.colorContrast=String(Number(c)||100);el.dataset.colorSaturation=String(Number(sat)||100);el.dataset.colorTemperature=String(Number(temp)||0);el.dataset.colorTint=String(Number(tint)||0);el.dataset.colorHue=String(Number(hue)||0);el.dataset.colorGrayscale=String(Number(gray)||0);el.dataset.colorSepia=String(Number(sepia)||0);el.dataset.colorBlur=String(Number(blur)||0);
                              const f=['brightness('+Math.max(0,Math.min(300,Number(b)||100))+'%)','contrast('+Math.max(0,Math.min(300,Number(c)||100))+'%)','saturate('+Math.max(0,Math.min(300,Number(sat)||100))+'%)','hue-rotate('+((Number(hue)||0)+(Number(tint)||0)*.12)+'deg)'];"""
once(old_advanced, new_advanced, "persist advanced image adjustment values")

if "el.dataset.editorCropX=String(Math.max(0,Math.min(100,Number(x)||50)))" not in s:
    raise SystemExit("crop position data binding anchor missing")

checks = {
    "5dp slider track applied": s.count("track = { sliderState ->") == slider_calls,
    "history observer wired": "new MutationObserver(records=>" in s and "installHistoryObserver();" in s,
    "undo and redo restore selected image": "NativeEditor.imageSelected(activeImage?activeImage.outerHTML:'')" in s,
    "crop/color panel receives selected HTML": 'ImageCropColorPanel("color", imageColorMainTab, selectedImageHtml' in s,
    "image values hydrate from dataset": "remember(selectedImageHtml)" in s and "color-brightness" in s,
    "slider position state stored": "editorCropX" in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Editor state/history validation failed: " + ", ".join(failed))

P.write_text(s, encoding="utf-8")
print(f"Editor history/state synchronization applied; {slider_calls} sliders now use a 5dp track.")
