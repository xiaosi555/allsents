#!/usr/bin/env python3
"""Create the redesigned Xingtu screen from the fully patched legacy editor.

The existing ArticleEditorScreen is intentionally kept intact and remains routable.
This script runs after every legacy editor patch so the redesigned copy inherits the
complete feature set, then applies only new-screen interaction changes.
"""
from pathlib import Path
import re
import shutil

ROOT = Path(".")
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
UI = JAVA / "ui"
MAIN = JAVA / "MainActivity.kt"
LEGACY = UI / "ArticleEditorScreen.kt"
REDESIGNED = UI / "ArticleEditorRedesignedScreen.kt"
ERROR = ROOT / "xingtu_redesign_patch_error.txt"

def fail(message: str):
    ERROR.write_text(message + "\n", encoding="utf-8")
    raise SystemExit(message)

for path in (MAIN, LEGACY):
    if not path.is_file():
        fail("Required source missing: " + str(path))

# The clone is made only after the existing feature patches have completed.
source = LEGACY.read_text(encoding="utf-8")
if "fun ArticleEditorScreen(vm: AppViewModel, onBack: () -> Unit)" not in source:
    fail("Legacy editor composable signature not found")
redesigned = source.replace(
    "fun ArticleEditorScreen(vm: AppViewModel, onBack: () -> Unit)",
    "fun ArticleEditorRedesignedScreen(vm: AppViewModel, onBack: () -> Unit)",
    1
)

# Keep the established visual language. Only normalize the new screen's panel
# geometry and interaction; do not replace its page/background/theme surfaces.
if "import androidx.compose.ui.platform.LocalSoftwareKeyboardController" not in redesigned:
    anchor = "import androidx.compose.ui.platform.LocalContext"
    if anchor not in redesigned:
        fail("LocalContext import anchor missing")
    redesigned = redesigned.replace(
        anchor,
        anchor + "\nimport androidx.compose.ui.platform.LocalSoftwareKeyboardController",
        1
    )

anchor = "    val context = LocalContext.current\n"
if anchor not in redesigned:
    fail("Editor context anchor missing")
redesigned = redesigned.replace(
    anchor,
    anchor + "    val keyboardController = LocalSoftwareKeyboardController.current\n",
    1
)

# New screen has a 200dp minimum panel. Preserve each panel's existing preferred
# height while clamping it to the agreed 200..400dp range.
redesigned = redesigned.replace(
    "var toolPanelHeightDp by remember { mutableFloatStateOf(100f) }",
    "var toolPanelHeightDp by remember { mutableFloatStateOf(200f) }",
    1
)
redesigned = redesigned.replace(
    "toolPanelHeightDp.coerceIn(100f, 400f)",
    "toolPanelHeightDp.coerceIn(200f, 400f)"
)
redesigned = redesigned.replace(
    ".coerceIn(100f, 400f)",
    ".coerceIn(200f, 400f)"
)
redesigned = redesigned.replace("toolPanelHeightDp = 180f", "toolPanelHeightDp = 200f")
redesigned = redesigned.replace("toolPanelHeightDp = 100f", "toolPanelHeightDp = 200f")

# The handle is a small, transparent drag target while collapsed. Its visible
# grip is revealed only after the user starts dragging upward.
state_anchor = "    var showToolPopup by remember { mutableStateOf(false) }\n"
if state_anchor not in redesigned:
    fail("Secondary panel state anchor missing")
if "var showPanelDragHandle by remember" not in redesigned:
    redesigned = redesigned.replace(
        state_anchor,
        state_anchor + "    var showPanelDragHandle by remember { mutableStateOf(false) }\n",
        1
    )

handle_old = """                    Box(
                        Modifier.fillMaxWidth().height(26.dp)
                            .pointerInput(Unit) {
                                detectDragGestures { change, dragAmount ->
                                    change.consume()
                                    val deltaDp = with(toolPanelDensity) { dragAmount.y.toDp() }
                                    toolPanelHeightDp = (toolPanelHeightDp - deltaDp.value).coerceIn(200f, 400f)
                                }
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Box(Modifier.width(42.dp).height(4.dp).background(Color(0xFF777777), RoundedCornerShape(50)))
                    }"""
handle_new = """                    Box(
                        Modifier.fillMaxWidth().height(if (showPanelDragHandle) 20.dp else 8.dp)
                            .pointerInput(Unit) {
                                detectDragGestures(
                                    onDragStart = { showPanelDragHandle = true },
                                    onDrag = { change, dragAmount ->
                                        change.consume()
                                        val deltaDp = with(toolPanelDensity) { dragAmount.y.toDp() }
                                        toolPanelHeightDp = (toolPanelHeightDp - deltaDp.value).coerceIn(200f, 400f)
                                    }
                                )
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        if (showPanelDragHandle) {
                            Box(Modifier.width(36.dp).height(3.dp).background(Color(0xFF888888), RoundedCornerShape(50)))
                        }
                    }"""
if handle_old in redesigned:
    redesigned = redesigned.replace(handle_old, handle_new, 1)
else:
    # The prior bottom-sheet patch may have altered formatting. Fail closed rather
    # than silently shipping a handle that does not follow the new rule.
    fail("Expandable panel drag handle anchor missing; no unsafe partial rewrite applied")

# Hide the IME whenever either native secondary work panel is presented. The
# current selection and WebView Range are intentionally not cleared here.
effect_anchor = "    BackHandler {\n        when {"
effect_insert = """    LaunchedEffect(showToolPopup, showCanvasPopup) {
        if (showToolPopup || showCanvasPopup) keyboardController?.hide()
    }

"""
if effect_insert.strip() not in redesigned:
    if effect_anchor not in redesigned:
        fail("BackHandler anchor missing for IME synchronization")
    redesigned = redesigned.replace(effect_anchor, effect_insert + effect_anchor, 1)

# Track the explicit transition from selected text into keyboard editing so
# Back can return to the selected state before clearing the selection.
state_anchor = "    var selectedTextActive by remember { mutableStateOf(false) }\n"
if state_anchor not in redesigned:
    fail("Selected text state anchor missing")
if "var textEditingActive by remember" not in redesigned:
    redesigned = redesigned.replace(
        state_anchor,
        state_anchor + "    var textEditingActive by remember { mutableStateOf(false) }\n",
        1
    )
edit_command = 'runJs("setText2SelectionPreview(false);enableSelectedTextEditing()")'
if edit_command in redesigned:
    redesigned = redesigned.replace(edit_command, "textEditingActive = true; " + edit_command, 1)
else:
    fail("Text edit command anchor missing")

back_old = """    BackHandler {
        when {
            showArticleList -> showArticleList = false
            previewMode -> {
                previewMode = false
                editor?.evaluateJavascript("setEditable(true);setPreviewInfo('','','','');", null)
            }
            else -> saveDocument(onComplete = onBack)
        }
    }"""
back_new = """    fun handleEditorBack() {
        when {
            showTextColorPicker -> showTextColorPicker = false
            showDeleteConfirm != null -> showDeleteConfirm = null
            revisionPreview != null -> revisionPreview = null
            templatePreview != null -> templatePreview = null
            previewAsset != null -> previewAsset = null
            editingTemplateContent != null -> editingTemplateContent = null
            editingTemplate != null -> editingTemplate = null
            deletingTemplate != null -> deletingTemplate = null
            fullTemplateConfirm != null -> fullTemplateConfirm = null
            showCustomImageCrop -> showCustomImageCrop = false
            showImageAlt -> showImageAlt = false
            showArticlePackagePreview -> showArticlePackagePreview = false
            showHtmlImportPreview -> showHtmlImportPreview = false
            showFindReplace -> showFindReplace = false
            showCompatibilityReport -> showCompatibilityReport = false
            showArticleInfo -> showArticleInfo = false
            showRevisionList -> showRevisionList = false
            showLink -> showLink = false
            showImage -> showImage = false
            showArticleList -> showArticleList = false
            showInsertLauncherMenu -> showInsertLauncherMenu = false
            showMoreTools -> showMoreTools = false
            showTemplateSubnav -> showTemplateSubnav = false
            showCanvasPopup -> showCanvasPopup = false
            showToolPopup -> {
                showToolPopup = false
                showPanelDragHandle = false
                runJs("setText2SelectionPreview(false);")
            }
            previewMode -> {
                previewMode = false
                editor?.evaluateJavascript("setEditable(true);setPreviewInfo('','','','');", null)
            }
            textEditingActive -> {
                textEditingActive = false
                keyboardController?.hide()
                editor?.evaluateJavascript("restoreSelection();", null)
                selectionState = selectionState.copy(kind = EditorSelectionKind.TEXT_BLOCK, collapsed = true)
            }
            selectedTextActive || selectionState.kind == EditorSelectionKind.TEXT_RANGE ||
                selectionState.kind == EditorSelectionKind.TEXT_BLOCK || selectionState.kind == EditorSelectionKind.CARET -> {
                selectedTextActive = false
                floatingToolbarRequest = ""
                floatingMenu = ""
                selectionState = EditorSelectionState()
                runJs("clearSelectedText();")
            }
            selectedImageHtml.isNotBlank() || selectedBlockHtml.isNotBlank() ||
                selectionState.kind != EditorSelectionKind.NONE || multiSelectMode -> {
                selectedImageHtml = ""
                selectedBlockHtml = ""
                multiSelectMode = false
                floatingToolbarRequest = ""
                floatingMenu = ""
                selectionState = EditorSelectionState()
                runJs("root.querySelectorAll('.selected-image,.selected-block,.selected-text-block').forEach(e=>e.classList.remove('selected-image','selected-block','selected-text-block'));activeImage=null;NativeEditor.imageSelected('');NativeEditor.textSelected('0');NativeEditor.blockSelected('');")
            }
            else -> saveDocument(onComplete = onBack)
        }
    }

    BackHandler { handleEditorBack() }"""
if back_old not in redesigned:
    fail("Original BackHandler block changed; cannot install ordered back stack safely")
redesigned = redesigned.replace(back_old, back_new, 1)

# The visible back icon uses the same coordinator as the system/gesture Back.
arrow_old = "IconButton(onClick = { saveDocument(onComplete = onBack) }) {"
if arrow_old not in redesigned:
    fail("Editor top-bar back button anchor missing")
redesigned = redesigned.replace(
    arrow_old,
    "IconButton(onClick = { handleEditorBack() }) {",
    1
)

# Guard that all required changes are actually present before writing the clone.
checks = {
    "new screen composable": "fun ArticleEditorRedesignedScreen(" in redesigned,
    "IME hide on secondary panels": "if (showToolPopup || showCanvasPopup) keyboardController?.hide()" in redesigned,
    "200dp minimum": "toolPanelHeightDp.coerceIn(200f, 400f)" in redesigned,
    "drag handle initially hidden": "if (showPanelDragHandle) {" in redesigned,
    "ordered back coordinator": "fun handleEditorBack()" in redesigned,
    "text edit returns to selection": "textEditingActive ->" in redesigned,
    "top back uses coordinator": "IconButton(onClick = { handleEditorBack() })" in redesigned,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    fail("Redesigned Xingtu validation failed: " + ", ".join(failed))

REDESIGNED.write_text(redesigned, encoding="utf-8")

# Keep a distinct, explicit legacy route. The default Xingtu entry now opens the
# redesigned screen; the legacy screen remains available as a safe comparison path.
main = MAIN.read_text(encoding="utf-8")
if "import com.shiwanju.app.ui.ArticleEditorRedesignedScreen" not in main:
    anchor = "import com.shiwanju.app.ui.ArticleEditorScreen"
    if anchor not in main:
        fail("Legacy editor import missing from MainActivity")
    main = main.replace(anchor, anchor + "\nimport com.shiwanju.app.ui.ArticleEditorRedesignedScreen", 1)

old_route = '"xingtu_article_editor" -> ArticleEditorScreen(vm) { vm.screen = "layout" }'
new_route = '"xingtu_article_editor" -> ArticleEditorRedesignedScreen(vm) { vm.screen = "layout" }'
if old_route in main:
    main = main.replace(old_route, new_route, 1)
elif new_route not in main:
    fail("Xingtu route anchor missing in MainActivity")

legacy_route = '"xingtu_article_editor_legacy" -> ArticleEditorScreen(vm) { vm.screen = "layout" }'
if legacy_route not in main:
    main = main.replace(new_route, new_route + "\n                        " + legacy_route, 1)

if new_route not in main or legacy_route not in main:
    fail("Separate redesigned and legacy routes were not installed")
MAIN.write_text(main, encoding="utf-8")

print("Redesigned Xingtu screen generated from the fully patched editor; legacy route preserved; panel/IME/back behavior normalized.")
