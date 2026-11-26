#!/usr/bin/env python3
"""Finalize text/image dock routing and synchronize image controls in the synthesized editor."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "editor_functional_v4_patch_error.txt"
if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")
s = EDITOR.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        ERROR.write_text(f"{label}: expected one anchor, found {count}\n", encoding="utf-8")
        raise SystemExit(f"Functional v4 patch anchor mismatch [{label}]: {count}")
    s = s.replace(old, new, 1)

# The four Text2 tabs are now the only entry points for this secondary panel.
# Keep the panel internal; do not expose the legacy "文字2" as a peer first-level item.
legacy_nav = "EditorPanel.values().filterNot { it in templateSubPanels }"
new_nav = "EditorPanel.values().filterNot { it in templateSubPanels || it == EditorPanel.TEXT2 }"
if new_nav not in s:
    if legacy_nav in s:
        s = s.replace(legacy_nav, new_nav, 1)
    else:
        import re
        pattern = re.compile(r"EditorPanel\.values\(\)\.filterNot\s*\{[^}]*templateSubPanels[^}]*\}\s*\.forEach\s*\{\s*panel\s*->")
        match = pattern.search(s)
        if not match:
            # The bottom-navigation synthesis may already have removed the peer navigation loop.
            # The authoritative overlay and Stage C2 validation also filter TEXT2.
            print("No legacy TEXT2 first-level navigation loop remains after dock synthesis.")
        else:
            replacement = new_nav + ".forEach { panel ->"
            s = s[:match.start()] + replacement + s[match.end():]

# Explicitly request the Android IME after restoring the selected paragraph's caret.
replace_once(
    '"编辑" -> runJs("enableSelectedTextEditing()")',
    '''"编辑" -> {
                                                runJs("setText2SelectionPreview(false);enableSelectedTextEditing()")
                                                val web = editor
                                                web?.let { target ->
                                                    target.requestFocus()
                                                    target.post {
                                                        val imm = context.getSystemService(Context.INPUT_METHOD_SERVICE) as? android.view.inputmethod.InputMethodManager
                                                        imm?.showSoftInput(target, android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT)
                                                    }
                                                }
                                            }''',
    "explicit text editor keyboard request"
)

# Read the selected image's actual computed values instead of leaving the adjustment
# sliders at stale defaults when the user changes the selected image.
replace_once(
    "function commitSelectedImageStyle(){if(!activeImage||activeImage.dataset.editorLocked==='1')return;commitHistory();NativeEditor.changed(root.innerHTML);}",
    """function commitSelectedImageStyle(){if(!activeImage||activeImage.dataset.editorLocked==='1')return;commitHistory();NativeEditor.changed(root.innerHTML);}
                            function getSelectedImageControls(){
                              if(!activeImage||!root.contains(activeImage))return '';
                              const css=getComputedStyle(activeImage),filter=css.filter||'none';
                              const read=(name,fallback)=>{
                                const match=filter.match(new RegExp(name+'\\\\(([-+]?\\\\d*\\\\.?\\\\d+)(%?)\\\\)'));
                                if(!match)return fallback;
                                const value=Number(match[1]);
                                return match[2]==='%'?value:value*100;
                              };
                              return JSON.stringify({
                                brightness:read('brightness',100),
                                contrast:read('contrast',100),
                                saturation:read('saturate',100),
                                opacity:Math.round(Number(css.opacity||1)*100),
                                radius:Math.max(0,parseFloat(css.borderTopLeftRadius)||0)
                              });
                            }""",
    "selected image control state reader"
)

replace_once(
    "function pasteSelectedImageStyle(){if(!activeImage||activeImage.dataset.editorLocked==='1'||!editorImageStyleClipboard)return;Object.keys(editorImageStyleClipboard).forEach(k=>activeImage.style[k]=editorImageStyleClipboard[k]);commitHistory();NativeEditor.changed(root.innerHTML);}",
    "function pasteSelectedImageStyle(){if(!activeImage||activeImage.dataset.editorLocked==='1'||!editorImageStyleClipboard)return;Object.keys(editorImageStyleClipboard).forEach(k=>activeImage.style[k]=editorImageStyleClipboard[k]);commitHistory();NativeEditor.changed(root.innerHTML);NativeEditor.imageSelected(activeImage.outerHTML);}",
    "sync controls after image style paste"
)

# Selecting/replacing an image updates every Compose slider from the image's real styles.
replace_once(
    '{ value -> selectedImageHtml = value; floatingToolbarRequest = "" },',
    """{ value ->
                                selectedImageHtml = value
                                floatingToolbarRequest = ""
                                if (value.isNotBlank()) {
                                    editor?.evaluateJavascript("getSelectedImageControls()") { raw ->
                                        runCatching {
                                            val encoded = org.json.JSONTokener(raw ?: "null").nextValue() as? String ?: return@runCatching
                                            if (encoded.isBlank()) return@runCatching
                                            val controls = JSONObject(encoded)
                                            imageBrightness = controls.optDouble("brightness", 100.0).toFloat().coerceIn(0f, 200f)
                                            imageContrast = controls.optDouble("contrast", 100.0).toFloat().coerceIn(0f, 200f)
                                            imageSaturation = controls.optDouble("saturation", 100.0).toFloat().coerceIn(0f, 200f)
                                            imageOpacity = controls.optDouble("opacity", 100.0).toFloat().coerceIn(0f, 100f)
                                            imageRadius = controls.optDouble("radius", 0.0).toFloat().coerceIn(0f, 40f)
                                        }
                                    }
                                }
                            },""",
    "sync selected image adjustment controls"
)

# A pasted image becomes the active image immediately, while style paste remains a separate type.
replace_once(
    """                            function pasteImageClipboard(){
                              if(editorClipboardType==='IMAGE_STYLE'){pasteSelectedImageStyle();return;}
                              if(editorClipboardType!=='OBJECT'||!editorObjectClipboard||!activeImage||activeImage.dataset.editorLocked==='1')return;
                              const box=document.createElement('div');box.innerHTML=editorObjectClipboard;
                              const node=box.firstElementChild;
                              if(!node||node.tagName!=='IMG')return;
                              activeImage.insertAdjacentElement('afterend',node);
                              commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();
                            }""",
    """                            function pasteImageClipboard(){
                              if(editorClipboardType==='IMAGE_STYLE'){pasteSelectedImageStyle();return;}
                              if(editorClipboardType!=='OBJECT'||!editorObjectClipboard||!activeImage||activeImage.dataset.editorLocked==='1')return;
                              const box=document.createElement('div');box.innerHTML=editorObjectClipboard;
                              const node=box.firstElementChild;
                              if(!node||node.tagName!=='IMG')return;
                              node.removeAttribute('data-editor-id');node.classList.remove('selected-image','selected-block','selected-text-block');
                              if(activeImage)activeImage.classList.remove('selected-image');
                              activeImage.insertAdjacentElement('afterend',node);
                              node.dataset.originalWidth=node.style.width||'';
                              node.dataset.originalHeight=node.style.height||'';
                              node.dataset.originalObjectFit=node.style.objectFit||'';
                              node.dataset.originalObjectPosition=node.style.objectPosition||'';
                              activeImage=node;node.classList.add('selected-image');
                              commitHistory();NativeEditor.changed(root.innerHTML);NativeEditor.imageSelected(node.outerHTML);reportSelection();
                            }""",
    "activate pasted image object"
)

# Ensure the selected object cannot be mistaken for a style clipboard after a copy/paste cycle.
required = [
    'EditorPanel.values().filterNot { it in templateSubPanels || it == EditorPanel.TEXT2 }',
    'imm?.showSoftInput(web, android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT)',
    'function getSelectedImageControls()',
    'imageBrightness = controls.optDouble("brightness", 100.0)',
    'function pasteImageClipboard()',
    'activeImage=node;node.classList.add(\'selected-image\')'
]
missing = [item for item in required if item not in s]
if missing:
    ERROR.write_text("Missing v4 features: " + ", ".join(missing) + "\n", encoding="utf-8")
    raise SystemExit("Functional v4 validation failed: " + ", ".join(missing))

EDITOR.write_text(s, encoding="utf-8")
print("Editor functional v4 applied: IME request, four-tab-only Text2 access, image slider synchronization and active image paste.")
