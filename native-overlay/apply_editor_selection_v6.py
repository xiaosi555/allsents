#!/usr/bin/env python3
"""Repair object-to-dock reporting and make local image import reliable."""
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

# V5 creates an explicit activeTextBlock and removes the browser Range on first tap.
# reportSelection must therefore report that active object directly, not rely only on Range/selected-block.
replace_once(
    "if(activeImage){kind='IMAGE';target=activeImage;}\n                                else if(blocks.length>1)",
    "if(activeImage){kind='IMAGE';target=activeImage;}\n                                else if(activeTextBlock&&root.contains(activeTextBlock)){kind=activeTextBlock.dataset.editorLocked==='1'?'COMPONENT':'TEXT_BLOCK';target=activeTextBlock;}\n                                else if(blocks.length>1)",
    "report active text block even when editor Range is intentionally cleared"
)

# Bridge callbacks also update the dock immediately. This is a resilient fallback
# if WebView selection geometry/range reporting is delayed on a device.
replace_once(
    """                            { value -> selectedBlockHtml = value },
                            { value -> selectedImageHtml = value; floatingToolbarRequest = "" },
                            { value -> selectedTextActive = value; floatingToolbarRequest = ""; if (value) floatingMenu = "" },""",
    """                            { value ->
                                selectedBlockHtml = value
                                if (value.isNotBlank() && selectedImageHtml.isBlank() && !selectedTextActive) {
                                    selectedDockMode = "COMPONENT"; showToolPopup = false; showCanvasPopup = false
                                } else if (value.isBlank() && selectedImageHtml.isBlank() && !selectedTextActive) {
                                    selectedDockMode = "DEFAULT"; showToolPopup = false; showCanvasPopup = false
                                }
                            },
                            { value ->
                                selectedImageHtml = value; floatingToolbarRequest = ""
                                if (value.isNotBlank()) {
                                    selectedDockMode = "IMAGE"; showToolPopup = false; showCanvasPopup = false
                                } else if (!selectedTextActive && selectedBlockHtml.isBlank()) {
                                    selectedDockMode = "DEFAULT"; showToolPopup = false; showCanvasPopup = false
                                }
                            },
                            { value ->
                                selectedTextActive = value; floatingToolbarRequest = ""
                                if (value) {
                                    selectedDockMode = "TEXT"; floatingMenu = ""; showToolPopup = false; showCanvasPopup = false
                                } else if (selectedImageHtml.isBlank() && selectedBlockHtml.isBlank()) {
                                    selectedDockMode = "DEFAULT"; showToolPopup = false; showCanvasPopup = false
                                }
                            },""",
    "synchronize all three native object callbacks with visible dock"
)

# Insert imported images through one JS transaction, selecting the new image and
# reporting its selection so the image dock appears immediately after import.
replace_once(
    "function insertHtml(v){restoreSelection();const s=window.getSelection();",
    """function insertImportedImage(src,alt){
                               const p=document.createElement('p'),img=document.createElement('img');
                               img.src=src;img.alt=alt||'';img.style.cssText='max-width:100%;height:auto;display:block;margin:14px auto';
                               p.appendChild(img);
                               const anchor=activeImage&&activeImage.parentElement?activeImage.parentElement:(activeTextBlock&&activeTextBlock.parentElement?activeTextBlock.parentElement:null);
                               if(savedRange&&root.contains(savedRange.commonAncestorContainer)){
                                 try{const r=savedRange.cloneRange();r.deleteContents();r.insertNode(p);}
                                 catch(e){if(anchor&&anchor.parentElement)anchor.insertAdjacentElement('afterend',p);else root.appendChild(p);}
                               }else if(anchor&&anchor.parentElement){anchor.insertAdjacentElement('afterend',p);}
                               else{root.appendChild(p);}
                               clearSelectedImage();clearSelectedText();clearSelectedBlocks();
                               activeImage=img;ensureEditorId(img);img.classList.add('selected-image');
                               root.contentEditable='false';savedRange=null;
                               const sel=window.getSelection();if(sel)sel.removeAllRanges();
                               NativeEditor.imageSelected(img.outerHTML);NativeEditor.textSelected('0');NativeEditor.blockSelected('');
                               commitHistory();NativeEditor.changed(root.innerHTML);reportSelection();
                             }
                             function insertHtml(v){restoreSelection();const s=window.getSelection();""",
    "atomic image insertion and immediate image selection"
)

# ACTION_GET_CONTENT-backed multi-select is more widely supported by photo/gallery providers
# than ACTION_OPEN_DOCUMENT on some OEM file-picker implementations.
replace_once(
    "val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->\n        uris.forEach { uri ->\n            runCatching {\n                val mime = context.contentResolver.getType(uri) ?: \"image/jpeg\"\n                val ext = when (mime.lowercase(Locale.ROOT)) { \"image/png\" -> \"png\"; \"image/webp\" -> \"webp\"; \"image/gif\" -> \"gif\"; \"image/heic\" -> \"heic\"; else -> \"jpg\" }\n                val id = vm.newId() + (0..999).random().toString()\n                val dir = File(context.filesDir, \"article_media\").apply { mkdirs() }\n                val target = File(dir, \"$id.$ext\")\n                context.contentResolver.openInputStream(uri)?.use { input -> input.copyTo(target.outputStream()) }\n                    ?: error(\"无法读取图片\")\n                val relative = \"article_media/${target.name}\"\n                vm.saveMediaAsset(MediaAsset(id, target.name, mime, relative, target.length(), System.currentTimeMillis().toString()))\n                insert(\"<p><img src='https://editor.local/assets/$id' alt='${target.name}' style='max-width:100%;height:auto;display:block;margin:14px auto'></p>\")\n            }.onFailure { vm.toast(\"图片导入失败：${it.message ?: \"未知错误\"}\") }\n        }\n    }",
    """val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents()) { uris ->
        if (uris.isEmpty()) {
            // User cancelled or the provider returned no readable image.
        } else {
            var imported = 0
            uris.forEach { uri ->
                var target: File? = null
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
                    runJs("insertImportedImage('https://editor.local/assets/$id',${JSONObject.quote(displayName)})")
                    imported++
                }.onFailure {
                    target?.delete()
                    vm.toast("图片导入失败：${it.message ?: "未知错误"}")
                }
            }
            if (imported > 0) vm.toast("已导入 $imported 张图片")
        }
    }""",
    "use gallery-compatible picker and validate/persist imported image assets"
)

# Ensure replacement and image insertion paths both use the gallery-compatible MIME contract.
replace_once(
    'imagePicker.launch(arrayOf("image/*"))',
    'imagePicker.launch("image/*")',
    "default dock image picker contract"
)
replace_once(
    'imagePicker.launch(arrayOf("image/*"))',
    'imagePicker.launch("image/*")',
    "image panel picker contract"
)

required = [
    "else if(activeTextBlock&&root.contains(activeTextBlock))",
    'selectedDockMode = "TEXT"',
    'selectedDockMode = "IMAGE"',
    "function insertImportedImage(src,alt)",
    "ActivityResultContracts.GetMultipleContents()",
    'imagePicker.launch("image/*")'
]
missing = [token for token in required if token not in s]
if missing:
    ERROR.write_text("Missing final v6 tokens: " + ", ".join(missing) + "\n", encoding="utf-8")
    raise SystemExit("Selection v6 validation failed: " + ", ".join(missing))
EDITOR.write_text(s, encoding="utf-8")
print("Selection v6 applied: active text reporting, immediate object-dock routing and robust local image import.")
