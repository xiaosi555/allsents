#!/usr/bin/env python3
"""Stage F: static feature-parity and interaction-structure audit for Xingtu."""
from collections import Counter
from pathlib import Path
import re

ROOT = Path(".")
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui"
LEGACY = JAVA / "ArticleEditorScreen.kt"
REDESIGNED = JAVA / "ArticleEditorRedesignedScreen.kt"
ERROR = ROOT / "xingtu_stage_f_patch_error.txt"

def fail(message: str):
    ERROR.write_text(message + "\n", encoding="utf-8")
    raise SystemExit(message)

if not LEGACY.is_file() or not REDESIGNED.is_file():
    fail("Legacy or redesigned editor source missing; Stage F must run after Stage E")

legacy = LEGACY.read_text(encoding="utf-8")
new = REDESIGNED.read_text(encoding="utf-8")

def tool_inventory(source: str):
    # Compare visible tool labels as a multiset so duplicate/intentional labels
    # are preserved as well as the unique set.
    return Counter(re.findall(r'EditorTool\(\s*"((?:\\.|[^"\\])*)"', source))

def panel_cases(source: str):
    # Capture grouped when branches such as
    # EditorPanel.CARD, EditorPanel.COMPONENT -> { ... } as well as singles.
    case_groups = re.findall(
        r"((?:EditorPanel\.[A-Z0-9_]+\s*,\s*)*EditorPanel\.[A-Z0-9_]+)\s*->",
        source
    )
    return {
        panel
        for group in case_groups
        for panel in re.findall(r"EditorPanel\.([A-Z0-9_]+)", group)
    }

def remembered_states(source: str):
    return set(re.findall(r"(?m)^\s*var\s+(\w+)\s+by\s+remember\s*\{", source))

def call_count(source: str, name: str):
    return len(re.findall(r"\b" + re.escape(name) + r"\s*\(", source))

# The redesigned screen is generated from the fully patched legacy screen.
# Presentation-only changes may add state, but must not remove business state.
legacy_tools = tool_inventory(legacy)
new_tools = tool_inventory(new)
missing_tools = legacy_tools - new_tools
if missing_tools:
    fail("Redesigned editor lost EditorTool labels: " + repr(dict(missing_tools)))

legacy_panels = panel_cases(legacy)
new_panels = panel_cases(new)
missing_panels = legacy_panels - new_panels
required_panels = {
    "TEXT", "IMAGE", "TEXT2", "TITLE", "LAYOUT", "CARD", "COMPONENT",
    "SVG", "STYLE", "LAYER", "CANVAS", "DOCUMENT", "TEMPLATE"
}
if missing_panels or not required_panels.issubset(new_panels):
    fail(
        "EditorPanel branch mismatch; missing from redesigned="
        + repr(sorted(missing_panels | (required_panels - new_panels)))
    )

legacy_states = remembered_states(legacy)
new_states = remembered_states(new)
missing_states = legacy_states - new_states
if missing_states:
    fail("Redesigned editor lost remembered state variables: " + repr(sorted(missing_states)))

# All native dialog/menu call sites must survive the visual normalization pass.
for name in ("AlertDialog", "DropdownMenu", "Dialog"):
    if call_count(legacy, name) != call_count(new, name):
        fail(
            f"{name} call count changed: legacy={call_count(legacy, name)}, "
            f"redesigned={call_count(new, name)}"
        )

# Protect important business-entry points and WebView editing bridge contracts.
required_markers = [
    "fun ArticleEditorRedesignedScreen(",
    "fun handleEditorBack()",
    "BackHandler(enabled = !editorImeVisible) { handleEditorBack() }",
    "WindowInsets.ime.getBottom(LocalDensity.current)",
    "restoreSelection();setText2SelectionPreview(true);",
    "else -> saveDocument(onComplete = onBack)",
    "NativeEditor.selectionChanged",
    "function reportSelection()",
    "function saveSelection()",
    "function restoreSelection()",
    "showCustomImageCrop",
    "showImageAlt",
    "showFindReplace",
    "showArticleInfo",
    "showRevisionList",
    "showLayoutBuilder",
    "showCompatibilityReport",
    "showArticlePackagePreview",
    "revisionPreview",
    "templatePreview",
]
missing_markers = [marker for marker in required_markers if marker not in new]
if missing_markers:
    fail("Redesigned editor is missing required interaction markers: " + ", ".join(missing_markers))

# Check the coordinator's actual branch order and uniqueness of the image picker.
start = new.find("    fun handleEditorBack()")
end = new.find("\n    BackHandler", start)
if start < 0 or end < 0:
    fail("Unable to isolate redesigned Back coordinator")
handler = new[start:end]
ordered = [
    "floatingMenu.isNotBlank() ->",
    "showDeleteConfirm != null ->",
    "showToolPopup -> {",
    "previewMode ->",
    "textEditingActive ->",
    "selectedTextActive || selectionState.kind",
    "selectedImageHtml.isNotBlank()",
    "else -> saveDocument(onComplete = onBack)",
]
positions = [handler.find(item) for item in ordered]
if any(pos < 0 for pos in positions) or positions != sorted(positions):
    fail("Back coordinator layer order is invalid: " + repr(dict(zip(ordered, positions))))
if handler.count("showImage -> showImage = false") != 1:
    fail("Image picker must have exactly one independent Back dismissal branch")

# The legacy route must remain available; the new route must be independent.
main = (ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/MainActivity.kt")
# MainActivity may live in the package root in some source archive versions.
if not main.is_file():
    main = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/MainActivity.kt"
if not main.is_file():
    fail("MainActivity source missing; cannot verify redesigned/legacy editor routes")
main_source = main.read_text(encoding="utf-8")
if "ArticleEditorRedesignedScreen" not in main_source or "xingtu_article_editor_legacy" not in main_source:
    fail("Redesigned and legacy editor routes are not both registered")

print(
    "Stage F static audit passed: "
    f"{sum(legacy_tools.values())} legacy EditorTool entries retained, "
    f"{len(new_panels)} panel cases present, "
    f"{len(legacy_states)} legacy remembered states retained, "
    "dialog/menu call counts and required editing/back contracts preserved. "
    "This is source-level parity only; it does not replace Kotlin compilation or device testing."
)
