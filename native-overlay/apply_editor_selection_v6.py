#!/usr/bin/env python3
"""Repair malformed canvas event wiring, object dock routing and local image import."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "editor_selection_v6_patch_error.txt"
if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")
s = EDITOR.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        ERROR.write_text(f"{label}: expected one anchor, found {count}\n", encoding="utf-8")
        raise SystemExit(f"Selection v6 patch anchor mismatch [{label}]: {count}")
    s = s.replace(old, new, 1)
    print("Selection v6 applied:", label)

# V5's click-listener splice retained the previous listener's closing token.
# That extra }); makes the entire inline editor JavaScript fail to parse, so no
# selection handlers, editor commands, or import-image insertion helpers execute.
replace_once(
    "                       });                             function clearDragTarget(){",
    "                       function clearDragTarget(){",
    "remove stray click-listener terminator left by v5 splice"
)

# Keep explicit activeTextBlock selection in reportSelection. It is essential because
# the first tap intentionally clears the browser Range to prevent opening the keyboard.
report_start = s.find("function reportSelection(){")
if report_start < 0:
    raise SystemExit("Selection v6 cannot find reportSelection")
report_end = s.find("\n                             }", report_start)
report = s[report_start:report_end if report_end >= 0 else report_start + 4000]
if "else if(activeTextBlock&&root.contains(activeTextBlock))" not in report:
    replace_once(
        "else if(blocks.length>1){kind='MULTI_BLOCK';target=blocks[blocks.length-1];}",
        "else if(activeTextBlock&&root.contains(activeTextBlock)){kind=activeTextBlock.dataset.editorLocked==='1'?'COMPONENT':'TEXT_BLOCK';target=activeTextBlock;}\n                               else if(blocks.length>1){kind='MULTI_BLOCK';target=blocks[blocks.length-1];}",
        "report active text block without relying on browser Range"
    )

# Update native callbacks immediately as a second path to the same dock state.
replace_once(
    "{ value -> selectedBlockHtml = value },",
    """{ value ->
                                selectedBlockHtml = value
                                if (value.isNotBlank() && selectedImageHtml.isBlank() && !selectedTextActive) {
                                    selectedDockMode = "COMPONENT"; showToolPopup = false; showCanvasPopup = false
                                } else if (value.isBlank() && selectedImageHtml.isBlank() && !selectedTextActive) {
                                    selectedDockMode = "DEFAULT"; showToolPopup = false; showCanvasPopup = false
                                }
                            },""",
    "component callback routes the dock immediately"
)
replace_once(
    "                                floatingToolbarRequest = \"\"\n                                if (value.isNotBlank()) {",
    """                                floatingToolbarRequest = ""
                                if (value.isNotBlank()) {
                                    selectedDockMode = "IMAGE"; showToolPopup = false; showCanvasPopup = false""",
    "image callback routes the dock immediately"
)
replace_once(
    "{ value -> selectedTextActive = value; floatingToolbarRequest = \"\"; if (value) floatingMenu = \"\" },",
    """{ value ->
                                selectedTextActive = value; floatingToolbarRequest = ""
                                if (value) {
                                    selectedDockMode = "TEXT"; floatingMenu = ""; showToolPopup = false; showCanvasPopup = false
                                } else if (selectedImageHtml.isBlank() && selectedBlockHtml.isBlank()) {
                                    selectedDockMode = "DEFAULT"; showToolPopup = false; showCanvasPopup = false
                                }
                            },""",
    "text callback routes the dock immediately"
)

# Importing a local image should be one WebView transaction and immediately select
# the inserted image. The previous generic insert() depended on a still-valid
# browser selection after returning from the Android document picker.
replace_once(
    "function insertHtml(v){restoreSelection();const s=window.getSelection();",
    """function insertImportedImage(src,alt){
                               const p=document.createElement('p'),img=document.createElement('img');
                               img.src=src;img.alt=alt||'';img.style.cssText='max-width:100%;height:auto;display:block;margin:14px auto';
                               p.appendChild(img);
                               const anchor=activeImage&&activeImage.parentElement?activeImage.parentElement:(activeTextBlock&&activeTextBlock.parentElement?activeTextBlock.parentElement:null);
                               let inserted=false;
                               if(savedRange&&root.contains(savedRange.commonAncestorContainer)){
                                 try{const r=savedRange.cloneRange();r.deleteContents();r.insertNode(p);inserted=true;}
                                 catch(e){}
                               }
                               if(!inserted){if(anchor&&anchor.parentElement)anchor.insertAdjacentElement('afterend',p);else root.appendChild(p);}
                               clearSelectedImage();clearSelectedText();clearSelectedBlocks();
                               activeImage=img;ensureEditorId(img);img.classList.add('selected-image');
                               root.contentEditable='false';savedRange=null;
                               const sel=window.getSelection();if(sel)sel.removeAllRanges();
                               NativeEditor.imageSelected(img.outerHTML);NativeEditor.textSelected('0');NativeEditor.blockSelected('');
                               commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();
                             }
                             function insertHtml(v){restoreSelection();const s=window.getSelection();""",
    "insert image as a selected object and update native dock"
)

# Use the Android content picker action accepted by both gallery apps and document providers.
# Keep multi-select support while normalizing the MIME type from the provider or file name.
picker_start = s.find("    val imagePicker = rememberLauncherForActivityResult(")
picker_end = s.find("    val layoutImagePicker =", picker_start)
if picker_start < 0 or picker_end < 0:
    raise SystemExit("Selection v6 cannot delimit the local image picker block")
new_picker = r'''    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents()) { uris ->
        if (uris.isNotEmpty()) {
            var imported = 0
            uris.forEach { uri ->
                var target: File? = null
                var assetSaved = false
                runCatching {
                    val resolver = context.contentResolver
                    val displayName = resolver.query(uri, arrayOf(android.provider.OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
                        if (cursor.moveToFirst()) cursor.getString(0) else null
                    }?.takeIf { it.isNotBlank() } ?: "image.jpg"
                    val rawMime = resolver.getType(uri)?.lowercase(Locale.ROOT).orEmpty()
                    val extension = displayName.substringAfterLast('.', "").lowercase(Locale.ROOT)
                    val ext = when {
                        rawMime == "image/png" || extension == "png" -> "png"
                        rawMime == "image/webp" || extension == "webp" -> "webp"
                        rawMime == "image/gif" || extension == "gif" -> "gif"
                        rawMime == "image/heic" || rawMime == "image/heif" || extension in setOf("heic", "heif") -> "heic"
                        rawMime == "image/avif" || extension == "avif" -> "avif"
                        rawMime == "image/bmp" || extension == "bmp" -> "bmp"
                        rawMime == "image/jpeg" || extension in setOf("jpg", "jpeg") -> "jpg"
                        else -> error("无法识别图片格式：$displayName")
                    }
                    val mime = when (ext) {
                        "png" -> "image/png"; "webp" -> "image/webp"; "gif" -> "image/gif"
                        "heic" -> "image/heic"; "avif" -> "image/avif"; "bmp" -> "image/bmp"; else -> "image/jpeg"
                    }
                    var id = vm.newId()
                    while (vm.data.mediaAssets.any { it.id == id }) id = vm.newId()
                    val dir = File(context.filesDir, "article_media").apply { if (!exists() && !mkdirs()) error("无法创建图片素材目录") }
                    target = File(dir, "$id.$ext")
                    resolver.openInputStream(uri)?.use { input -> target!!.outputStream().use { output -> input.copyTo(output) } }
                        ?: error("无法读取图片文件")
                    if (target!!.length() <= 0L) error("图片文件为空")
                    val asset = MediaAsset(id, target!!.name, mime, "article_media/${target!!.name}", target!!.length(), System.currentTimeMillis().toString())
                    if (!vm.saveMediaAsset(asset)) error("图片素材保存失败")
                    assetSaved = true
                    runJs("insertImportedImage('https://editor.local/assets/$id',${JSONObject.quote(displayName)})")
                    imported++
                }.onFailure {
                    if (!assetSaved) target?.delete()
                    vm.toast("图片导入失败：${it.message ?: "未知错误"}")
                }
            }
            if (imported > 0) vm.toast("已导入 $imported 张图片")
        }
    }
'''
s = s[:picker_start] + new_picker + s[picker_end:]
count = s.count('imagePicker.launch(arrayOf("image/*"))')
if count != 2:
    raise SystemExit(f"Selection v6 expected two imagePicker launches, found {count}")
s = s.replace('imagePicker.launch(arrayOf("image/*"))', 'imagePicker.launch("image/*")')

required = [
    "function insertImportedImage(src,alt)",
    "ActivityResultContracts.GetMultipleContents()",
    'imagePicker.launch("image/*")',
    'selectedDockMode = "TEXT"',
    'selectedDockMode = "IMAGE"',
    'selectedDockMode = "COMPONENT"',
    "function reportSelection()"
]
missing = [token for token in required if token not in s]
if missing:
    ERROR.write_text("Missing final v6 tokens: " + ", ".join(missing) + "\n", encoding="utf-8")
    raise SystemExit("Selection v6 validation failed: " + ", ".join(missing))
EDITOR.write_text(s, encoding="utf-8")
print("Selection v6 applied: valid editor JavaScript, reliable object docks and gallery-compatible local image import.")
