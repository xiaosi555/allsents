#!/usr/bin/env python3
"""Final UI consistency pass for the native article editor.

Runs after all editor feature patches so it does not invalidate their source anchors.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "article_editor_ui_unification_error.txt"

if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")

s = EDITOR.read_text(encoding="utf-8")


def once(old: str, new: str, label: str) -> None:
    global s
    if new in s:
        return
    count = s.count(old)
    if count != 1:
        ERROR.write_text(f"{label}: expected one anchor, found {count}\n", encoding="utf-8")
        raise SystemExit(f"Article editor UI unification failed [{label}]: {count}")
    s = s.replace(old, new, 1)


# Keep all confirmation/form AlertDialogs on one light dialog surface. The
# editing canvas and non-modal editing sheets retain their dedicated dark UI.
dialog_style = """AlertDialog(
            shape = RoundedCornerShape(16.dp),
            containerColor = Color(0xFFFDFDFD),
            iconContentColor = Color(0xFF333333),
            titleContentColor = Color(0xFF222222),
            textContentColor = Color(0xFF555555),
            tonalElevation = 2.dp,
"""
if "containerColor = Color(0xFFFDFDFD)" not in s:
    count = s.count("AlertDialog(\n")
    if count < 1:
        raise SystemExit("No AlertDialog calls found for styling")
    s = s.replace("AlertDialog(\n", dialog_style)

# Standardize the custom white dialog cards without changing the dark
# non-modal object-editing popup surfaces.
s = s.replace(
    "Surface(shape = RoundedCornerShape(14.dp), color = Color.White",
    "Surface(shape = RoundedCornerShape(16.dp), color = Color(0xFFFDFDFD)"
)

# The bottom editor sheet uses a semantic close action on the left and
# confirmation action on the right, with category tabs centered between them.
left_check = 'IconButton(onClick = { if (activePanel == EditorPanel.TEXT2) runJs("setText2SelectionPreview(false);"); showToolPopup = false }) { Icon(Icons.Outlined.Check, contentDescription = "确定", tint = AppColors.Theme) }'
left_close = 'IconButton(onClick = { if (activePanel == EditorPanel.TEXT2) runJs("setText2SelectionPreview(false);"); showToolPopup = false }) { Icon(Icons.Outlined.Close, contentDescription = "关闭功能窗口", tint = Color.White) }'
right_close = left_close
right_check = 'IconButton(onClick = { if (activePanel == EditorPanel.TEXT2) runJs("setText2SelectionPreview(false);"); showToolPopup = false }) { Icon(Icons.Outlined.Check, contentDescription = "确定", tint = AppColors.Theme) }'
if left_check in s:
    if s.count(left_check) != 1 or s.count(right_close) != 1:
        raise SystemExit("Could not uniquely locate both secondary-panel header actions")
    s = s.replace(left_check, left_close, 1)
    right_pos = s.rfind(right_close)
    s = s[:right_pos] + right_check + s[right_pos + len(right_close):]
elif left_close not in s or right_check not in s:
    raise SystemExit("Secondary-panel header actions are in an unexpected state")

# Make the persistent category dock use the same vector icon language as the
# selection tools, while retaining its existing labels and click behavior.
old_dock_item = '                                Text(item, color = if (item in listOf("编辑", "字体", "样式", "排版", "透明度", "加图", "加字")) AppColors.Theme else Color(0xFFDDDDDD), fontSize = 11.sp, maxLines = 1)'
new_dock_item = """                                val itemTint = if (item in listOf("编辑", "字体", "样式", "排版", "透明度", "加图", "加字")) AppColors.Theme else Color(0xFFDDDDDD)
                                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                                    EditorVectorIcon(item, tint = itemTint, modifier = Modifier.size(18.dp))
                                    Text(item, color = itemTint, fontSize = 10.sp, maxLines = 1)
                                }"""
once(old_dock_item, new_dock_item, "vector icons in primary dock")

# Fail fast if a future patch changes the contract unexpectedly.
required = [
    'toolPanelHeightDp.coerceIn(200f, 400f)',
    'toolPanelHeightDp = 200f',
    'contentDescription = "关闭功能窗口"',
    'contentDescription = "确定"',
    'containerColor = Color(0xFFFDFDFD)',
    'EditorVectorIcon(item, tint = itemTint',
    'alignment = Alignment.BottomCenter',
    'focusable = false',
]
missing = [token for token in required if token not in s]
if missing:
    ERROR.write_text("Missing UI consistency requirements: " + ", ".join(missing) + "\n", encoding="utf-8")
    raise SystemExit("Article editor UI unification validation failed: " + ", ".join(missing))

EDITOR.write_text(s, encoding="utf-8")
print("Article editor UI unification passed: consistent dialog surfaces, semantic panel actions, 200–400dp sheet and vector dock icons.")
