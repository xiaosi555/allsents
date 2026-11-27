#!/usr/bin/env python3
"""Route selected-image appearance tools through the complete image tool sheet."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "unify_image_selection_panels_patch_error.txt"
if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")

s = EDITOR.read_text(encoding="utf-8")
old = '                                    else -> activeObjectDialog = action'
new = '''                                    else -> {
                                        activeObjectDialog = action
                                        showToolPopup = false
                                        showCanvasPopup = false
                                    }'''
if new not in s:
    count = s.count(old)
    if count != 1:
        ERROR.write_text(f"Expected one image action fallback, found {count}\\n", encoding="utf-8")
        raise SystemExit(f"Image panel route anchor mismatch: {count}")
    s = s.replace(old, new, 1)

checks = {
    "each image function opens its own popup": "else -> activeObjectDialog = action" in s and "else -> {\n                                        activePanel = EditorPanel.IMAGE" not in s,
    "dedicated crop panel remains available": "EditorPanel.IMAGE_CROP -> ImageCropColorPanel" in s,
    "dedicated color panel remains available": "EditorPanel.IMAGE_COLOR -> ImageCropColorPanel" in s,
    "image function popup closes combined sheet": "showToolPopup = false" in s and "showCanvasPopup = false" in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    ERROR.write_text("Image panel validation failed: " + ", ".join(failed) + "\\n", encoding="utf-8")
    raise SystemExit("Image panel validation failed: " + ", ".join(failed))

EDITOR.write_text(s, encoding="utf-8")
print("Each image function now opens its own bottom non-modal popup; crop and color retain dedicated panels.")
