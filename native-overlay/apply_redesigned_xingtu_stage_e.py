#!/usr/bin/env python3
"""Stage E: coordinate IME, editor selection and transient UI Back handling."""
from pathlib import Path
import re

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

# WindowInsets.ime is an extension property in Compose Foundation Layout.
layout_wildcard_import = "import androidx.compose.foundation.layout.*" in s
imports_to_add = []
if not layout_wildcard_import and "import androidx.compose.foundation.layout.WindowInsets" not in s:
    imports_to_add.append("import androidx.compose.foundation.layout.WindowInsets")
if not layout_wildcard_import and "import androidx.compose.foundation.layout.ime" not in s:
    imports_to_add.append("import androidx.compose.foundation.layout.ime")
if imports_to_add:
    package = re.search(r"(?m)^package [^\n]+\n", s)
    if not package:
        fail("Kotlin package declaration missing; cannot add IME imports safely")
    s = s[:package.end()] + "\n".join(imports_to_add) + "\n" + s[package.end():]

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
            selectionState.kind == RedesignedEditorSelectionKind.TEXT_RANGE ||
            selectionState.kind == RedesignedEditorSelectionKind.TEXT_BLOCK ||
            selectionState.kind == RedesignedEditorSelectionKind.CARET
        )) {
            textEditingActive = true
        }
    }

"""
if "LaunchedEffect(editorImeVisible, selectedTextActive, selectionState.kind)" not in s:
    replace_once(ime_effect_anchor, ime_effect, "IME-to-text-edit state synchronization")

# Android's IME receives system Back while visible. The top-bar Back remains
# routed through this same coordinator and explicitly hides the keyboard.
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

# A child floating menu must be dismissed before any parent dialog or panel.
replace_once(
    "        when {\n            showDeleteConfirm != null -> showDeleteConfirm = null",
    "        when {\n            floatingMenu.isNotBlank() -> floatingMenu = \"\"\n            showDeleteConfirm != null -> showDeleteConfirm = null",
    "floating menu is the topmost Back layer"
)

# The generator already includes the image-picker dismissal branch. Do not
# inject a duplicate branch; fail if the inherited coordinator lacks it.
if s.count("showImage -> showImage = false") != 1:
    fail("Expected exactly one inherited image-picker dismissal branch")

old_text_edit = """            textEditingActive -> {
                textEditingActive = false
                keyboardController?.hide()
                editor?.evaluateJavascript("restoreSelection();", null)
                selectionState = selectionState.copy(kind = RedesignedEditorSelectionKind.TEXT_BLOCK, collapsed = true)
            }"""
new_text_edit = """            textEditingActive -> {
                textEditingActive = false
                keyboardController?.hide()
                editor?.evaluateJavascript("restoreSelection();setText2SelectionPreview(true);", null)
                selectedTextActive = true
                selectionState = selectionState.copy(kind = RedesignedEditorSelectionKind.TEXT_BLOCK, collapsed = true)
            }"""
replace_once(old_text_edit, new_text_edit, "editing returns to a stable selected-text state")

checks = {
    "IME extension import": "import androidx.compose.foundation.layout.ime" in s or "import androidx.compose.foundation.layout.*" in s,
    "IME visibility observer": "val editorImeVisible = WindowInsets.ime.getBottom(LocalDensity.current) > 0" in s,
    "IME text editing synchronization": "LaunchedEffect(editorImeVisible, selectedTextActive, selectionState.kind)" in s,
    "floating menu closes before parent": "floatingMenu.isNotBlank() -> floatingMenu = \"\"" in s,
    "exactly one image picker dismissal": s.count("showImage -> showImage = false") == 1,
    "text editing restores selection": 'restoreSelection();setText2SelectionPreview(true);' in s,
    "selected text retained after edit": "selectedTextActive = true\n                selectionState = selectionState.copy(kind = RedesignedEditorSelectionKind.TEXT_BLOCK, collapsed = true)" in s,
    "system Back uses coordinator": "BackHandler(enabled = !editorImeVisible) { handleEditorBack() }" in s,
    "top Back uses coordinator": "IconButton(onClick = { handleEditorBack() })" in s,
    "IME explicitly gets first Back": "if (editorImeVisible) {\n            keyboardController?.hide()\n            return\n        }" in s,
    "single terminal save/leave": "else -> saveDocument(onComplete = onBack)" in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    fail("Stage E validation failed: " + ", ".join(failed))

# Enforce the complete coordinator order, not just a few selected anchors.
start = s.find("    fun handleEditorBack()")
end = s.find("\n    BackHandler", start)
if start < 0 or end < 0:
    fail("Unable to isolate handleEditorBack() for ordering validation")
handler = s[start:end]
order = [
    "floatingMenu.isNotBlank() ->",
    "showDeleteConfirm != null ->",
    "revisionPreview != null ->",
    "templatePreview != null ->",
    "previewAsset != null ->",
    "editingTemplateContent != null ->",
    "editingTemplate != null ->",
    "deletingTemplate != null ->",
    "fullTemplateConfirm != null ->",
    "showCustomImageCrop ->",
    "showImageAlt ->",
    "showArticlePackagePreview ->",
    "showHtmlImportPreview ->",
    "showFindReplace ->",
    "showCompatibilityReport ->",
    "showArticleInfo ->",
    "showRevisionList ->",
    "showLink ->",
    "showBlockProperties ->",
    "showLayoutBuilder ->",
    "showImage -> showImage = false",
    "showArticleList ->",
    "showInsertLauncherMenu ->",
    "showMoreTools ->",
    "showTemplateSubnav ->",
    "showCanvasPopup ->",
    "showToolPopup ->",
    "previewMode ->",
    "textEditingActive ->",
    "selectedTextActive || selectionState.kind",
    "selectedImageHtml.isNotBlank()",
    "else -> saveDocument(onComplete = onBack)",
]
positions = [handler.find(item) for item in order]
if any(pos < 0 for pos in positions) or positions != sorted(positions):
    fail("Back coordinator order is invalid: " + repr(dict(zip(order, positions))))

EDITOR.write_text(s, encoding="utf-8")
print("Stage E coordinator validated: IME first, child menu before parent layers, single image picker dismissal, selection restoration and one terminal save/leave path.")
