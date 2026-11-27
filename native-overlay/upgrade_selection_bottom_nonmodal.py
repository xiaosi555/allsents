#!/usr/bin/env python3
"""Convert selected text/image secondary controls into a non-modal bottom popup."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "selection_bottom_nonmodal_patch_error.txt"
if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")
s = EDITOR.read_text(encoding="utf-8")

def once(old, new, label):
    global s
    if new in s:
        return
    count = s.count(old)
    if count != 1:
        ERROR.write_text(f"{label}: expected one anchor, found {count}\n", encoding="utf-8")
        raise SystemExit(f"Bottom non-modal panel patch [{label}]: {count}")
    s = s.replace(old, new, 1)

old_text_action = '''                                    "font", "style", "layout", "text-opacity" -> {
                                        text2MainTab = when (action) { "font" -> "字体"; "style" -> "样式"; "layout" -> "排版"; else -> "透明度" }
                                        activePanel = EditorPanel.TEXT2
                                        showToolPopup = true
                                        showCanvasPopup = false
                                        toolPanelHeightDp = 200f
                                        runJs("setText2SelectionPreview(true);")
                                    }'''
new_text_action = '''                                    "font", "style", "layout", "text-opacity" -> {
                                        text2MainTab = when (action) { "font" -> "字体"; "style" -> "样式"; "layout" -> "排版"; else -> "样式" }
                                        activePanel = EditorPanel.TEXT2
                                        showToolPopup = true
                                        showCanvasPopup = false
                                        toolPanelHeightDp = 200f
                                        runJs("setText2SelectionPreview(true);")
                                    }'''
once(old_text_action, new_text_action, "unify selected text secondary panel")
once(
    '                                    "text-align" -> activeObjectDialog = action',
    '''                                    "text-align" -> {
                                        text2MainTab = "排版"
                                        activePanel = EditorPanel.TEXT2
                                        showToolPopup = true
                                        showCanvasPopup = false
                                        toolPanelHeightDp = 200f
                                        runJs("setText2SelectionPreview(true);")
                                    }''',
    "route text alignment through full Text2 panel"
)


old_dialog = '        Dialog(onDismissRequest = { activeObjectDialog = "" }) {'
new_popup = '''        androidx.compose.ui.window.Popup(
            alignment = Alignment.BottomCenter,
            properties = androidx.compose.ui.window.PopupProperties(
                focusable = false,
                dismissOnBackPress = false,
                dismissOnClickOutside = false
            )
        ) {'''
once(old_dialog, new_popup, "replace modal dialog with non-modal bottom popup")

old_surface = '            Surface(Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp), color = Color(0xFF242424), shadowElevation = 18.dp) {'
new_surface = '''            Surface(
                Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 6.dp).heightIn(max = 390.dp),
                shape = RoundedCornerShape(topStart = 18.dp, topEnd = 18.dp, bottomStart = 8.dp, bottomEnd = 8.dp),
                color = Color(0xFF242424),
                shadowElevation = 18.dp
            ) {'''
once(old_surface, new_surface, "bottom popup surface layout")

old_column = '                Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 15.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {'
new_column = '''                Column(
                    Modifier.fillMaxWidth().heightIn(max = 390.dp)
                        .verticalScroll(rememberScrollState())
                        .padding(horizontal = 18.dp, vertical = 10.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Box(
                        Modifier.align(Alignment.CenterHorizontally).width(38.dp).height(4.dp)
                            .clip(CircleShape).background(Color(0xFF777777))
                    )'''
once(old_column, new_column, "scrollable bottom panel content")


checks = [
    ("non-modal popup", "PopupProperties(" in s and "focusable = false" in s),
    ("bottom anchoring", "alignment = Alignment.BottomCenter" in s),
    ("selected text unified", 'activeObjectDialog = action' in s),
    ("live image radius", "imageRadiusTL" in s and "previewSelectedImageRadius(\" + it + \",\" + it" in s),
    ("image adjustment preview", "previewSelectedImageFilters(" in s),
    ("text opacity preview", "previewSelectedTextOpacity($it)" in s),
    ("canvas pass-through", "dismissOnClickOutside = false" in s),
]
failed = [name for name, ok in checks if not ok]
if failed:
    ERROR.write_text("Missing required bottom-panel behavior: " + ", ".join(failed) + "\n", encoding="utf-8")
    raise SystemExit("Bottom panel verification failed: " + ", ".join(failed))

EDITOR.write_text(s, encoding="utf-8")
print("Selected text/image secondary panels now use a bottom-anchored non-modal popup with live canvas previews.")
