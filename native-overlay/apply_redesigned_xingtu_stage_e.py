#!/usr/bin/env python3
"""Stage E: coordinate IME, editor selection and transient UI Back handling."""
from pathlib import Path

ROOT = Path(".")
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorRedesignedScreen.kt"
ERROR = ROOT / "xingtu_stage_e_patch_error.txt"

def fail(message: str):
    ERROR.write_text(message + "\n", encoding="utf-8")
    raise SystemExit(message)

if not EDITOR.is_file():
    fail("Redesigned editor source missing; Stage E must run after Stage D")

s = EDITOR.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        fail(f"Stage E anchor mismatch [{label}]: expected 1, found {count}")
    s = s.replace(old, new, 1)

# Observe IME visibility at the redesigned editor root. Compose/Android still
# gets first chance to hide the keyboard; this observer records that a text
# editing session began so the next Back can restore the saved WebView range.
keyboard_anchor = "    val keyboardController = LocalSoftwareKeyboardController.current\n"
if "val editorImeVisible = WindowInsets.ime.getBottom(LocalDensity.current) > 0" not in s:
    replace_once(
        keyboard_anchor,
        keyboard_anchor + "    val editorImeVisible = WindowInsets.ime.getBottom(LocalDensity.current) > 0\n",
        "IME visibility observer"
    )

ime_effect_anchor = """    LaunchedEffect(showToolPopup, showCanvasPopup) {
        if (showToolPopup || showCanvasPopup) keyboardController?.hide()
        if (!showToolPopup) showPanelDragHandle = false
    }

"""
ime_effect = ime_effect_anchor + """    LaunchedEffect(editorImeVisible, selectedTextActive, selectionState.kind) {
        if (editorImeVisible && (
            selectedTextActive ||
            selectionState.kind == EditorSelectionKind.TEXT_RANGE ||
            selectionState.kind == EditorSelectionKind.TEXT_BLOCK ||
            selectionState.kind == EditorSelectionKind.CARET
        )) {
            textEditingActive = true
        }
    }

"""
if "LaunchedEffect(editorImeVisible, selectedTextActive, selectionState.kind)" not in s:
    replace_once(ime_effect_anchor, ime_effect, "IME-to-text-edit state synchronization")

# Explicitly let the Android IME consume system Back first. The visible
# top-bar Back still routes through the coordinator and hides the IME itself.
replace_once(
    "    fun handleEditorBack() {\n        when {",
    "    fun handleEditorBack() {\n        if (editorImeVisible) {\n            keyboardController?.hide()\n            return\n        }\n        when {",
    "IME is the first Back layer"
)
replace_once(
    "    BackHandler { handleEditorBack() }",
    "    BackHandler(enabled = !editorImeVisible) { handleEditorBack() }",
    "system Back yields to visible IME"
)

# Nested menus/popovers must close before their parent panel. Some Compose
# DropdownMenus handle Back internally; this explicit branch covers custom
# floating menus and keeps the parent editor panel open.
floating_anchor = """            showDeleteConfirm != null -> showDeleteConfirm = null
"""
replace_once(
    floating_anchor,
    floating_anchor + """            floatingMenu.isNotBlank() -> floatingMenu = ""
""",
    "floating menu gets first local dismissal"
)

# The image library picker is a separate transient layer from the image panel.
# Closing it must not clear the selected canvas object.
image_anchor = """            showImageAlt -> showImageAlt = false
"""
replace_once(
    image_anchor,
    image_anchor + """            showImage -> showImage = false
""",
    "image picker dismissal"
)

# After keyboard dismissal, the next Back restores the original WebView
# selection, rather than clearing it or leaving a stale caret state.
old_text_edit = """            textEditingActive -> {
                textEditingActive = false
                keyboardController?.hide()
                editor?.evaluateJavascript("restoreSelection();", null)
                selectionState = selectionState.copy(kind = EditorSelectionKind.TEXT_BLOCK, collapsed = true)
            }"""
new_text_edit = """            textEditingActive -> {
                textEditingActive = false
                keyboardController?.hide()
                editor?.evaluateJavascript("restoreSelection();setText2SelectionPreview(true);", null)
                selectedTextActive = true
                selectionState = selectionState.copy(kind = EditorSelectionKind.TEXT_BLOCK, collapsed = true)
            }"""
replace_once(old_text_edit, new_text_edit, "editing returns to a stable selected-text state")

# Prevent a Back event from navigating away while a non-modal editor layer is
# still active. The final save/leave branch remains the sole exit path.
checks = {
    "IME visibility observer": "val editorImeVisible = WindowInsets.ime.getBottom(LocalDensity.current) > 0" in s,
    "IME text editing synchronization": "LaunchedEffect(editorImeVisible, selectedTextActive, selectionState.kind)" in s,
    "floating menu closes before parent": "floatingMenu.isNotBlank() -> floatingMenu = \"\"" in s,
    "image picker has its own dismissal": "showImage -> showImage = false" in s,
    "text editing restores selection": 'restoreSelection();setText2SelectionPreview(true);' in s,
    "selected text retained after edit": "selectedTextActive = true\n                selectionState = selectionState.copy(kind = EditorSelectionKind.TEXT_BLOCK, collapsed = true)" in s,
    "system Back uses coordinator": "BackHandler(enabled = !editorImeVisible) { handleEditorBack() }" in s,
    "top Back uses coordinator": "IconButton(onClick = { handleEditorBack() })" in s,
    "IME explicitly gets first Back": "if (editorImeVisible) {\n            keyboardController?.hide()\n            return\n        }" in s,
    "single terminal save/leave": "else -> saveDocument(onComplete = onBack)" in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    fail("Stage E validation failed: " + ", ".join(failed))

# Check the close order is stable and that the terminal leave branch remains
# after every transient UI and selection branch.
order = [
    "showDeleteConfirm != null ->",
    "floatingMenu.isNotBlank() ->",
    "showImage -> showImage = false",
    "showToolPopup -> {",
    "textEditingActive -> {",
    "selectedTextActive || selectionState.kind",
    "selectedImageHtml.isNotBlank()",
    "else -> saveDocument(onComplete = onBack)",
]
positions = [s.find(item, s.find("fun handleEditorBack()")) for item in order]
if any(pos < 0 for pos in positions) or positions != sorted(positions):
    fail("Back coordinator order is invalid: " + repr(dict(zip(order, positions))))

EDITOR.write_text(s, encoding="utf-8")
print("Stage E coordinator updated: IME-aware text edit state, nested menu/picker dismissal, ordered selection restoration; no build performed.")
