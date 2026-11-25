#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
MAIN = JAVA / "MainActivity.kt"
LAYOUT = JAVA / "ui/LayoutScreen.kt"
EDITOR = JAVA / "ui/ArticleEditorScreen.kt"
XIUMI = JAVA / "ui/XiumiArticleLayoutScreen.kt"

for required in (MAIN, LAYOUT, EDITOR, XIUMI):
    if not required.is_file():
        raise SystemExit("Required editor source missing: " + str(required))

# Keep the two editors as genuinely separate screens and route targets.
main = MAIN.read_text(encoding="utf-8")
main = main.replace(
    "import com.shiwanju.app.ui.XiumiArticleEditorScreen",
    "import com.shiwanju.app.ui.ArticleEditorScreen"
)
if "import com.shiwanju.app.ui.ArticleEditorScreen" not in main:
    anchor = "import com.shiwanju.app.ui.LayoutScreen"
    if anchor not in main:
        raise SystemExit("Cannot add the 醒图 ArticleEditorScreen import.")
    main = main.replace(anchor, anchor + "\nimport com.shiwanju.app.ui.ArticleEditorScreen", 1)
if "import com.shiwanju.app.ui.XiumiArticleLayoutScreen" not in main:
    anchor = "import com.shiwanju.app.ui.LayoutScreen"
    main = main.replace(anchor, anchor + "\nimport com.shiwanju.app.ui.XiumiArticleLayoutScreen", 1)

main = re.sub(
    r'"article_editor"\s*->\s*XiumiArticleEditorScreen\(vm\) \{ vm\.screen = "layout" \}',
    '"article_editor" -> ArticleEditorScreen(vm) { vm.screen = "layout" }',
    main
)
if '"xingtu_article_editor" -> ArticleEditorScreen(vm) { vm.screen = "layout" }' not in main:
    legacy = '                        "article_editor" -> ArticleEditorScreen(vm) { vm.screen = "layout" }'
    if legacy in main:
        main = main.replace(legacy, '                        "xingtu_article_editor" -> ArticleEditorScreen(vm) { vm.screen = "layout" }\n' + legacy, 1)
    else:
        route = '                        "xiumi_article_layout" -> XiumiArticleLayoutScreen(vm) { vm.screen = "layout" }'
        if route not in main:
            raise SystemExit("Cannot locate Xiumi route in MainActivity.")
        main = main.replace(route, route + '\n                        "xingtu_article_editor" -> ArticleEditorScreen(vm) { vm.screen = "layout" }', 1)

# Remove the old misleading wrapper that made the classic editor look like a Xiumi screen.
editor = EDITOR.read_text(encoding="utf-8")
wrapper_pattern = re.compile(
    r'\n// 独立秀米式文章编辑页面入口：.*?\n@Composable\nfun XiumiArticleEditorScreen\(vm: AppViewModel, onBack: \(\) -> Unit\) \{\n    ArticleEditorScreen\(vm = vm, onBack = onBack\)\n\}\n',
    re.S
)
editor, removed = wrapper_pattern.subn("\\n", editor)
if removed > 1:
    raise SystemExit("Found multiple legacy XiumiArticleEditorScreen wrappers.")
if "fun XiumiArticleEditorScreen" in editor:
    raise SystemExit("Legacy XiumiArticleEditorScreen alias remains in ArticleEditorScreen.kt.")
# Make the restored editor visibly identify itself as 醒图.
editor = editor.replace(
    'Text(if (saved) "已保存" else "自动保存中", color = AppColors.TextDim, fontSize = 10.sp, modifier = Modifier.padding(start = 5.dp))',
    'Text("醒图 · " + if (saved) "已保存" else "自动保存中", color = AppColors.TextDim, fontSize = 10.sp, modifier = Modifier.padding(start = 5.dp))'
)
EDITOR.write_text(editor, encoding="utf-8")

# Add the camera entry immediately LEFT of Edit; keep the Xiumi palette entry RIGHT of Edit.
layout = LAYOUT.read_text(encoding="utf-8")
if "import androidx.compose.material.icons.outlined.PhotoCamera" not in layout:
    anchor = "import androidx.compose.material.icons.Icons"
    if anchor not in layout:
        raise SystemExit("Cannot add the camera icon import.")
    layout = layout.replace(anchor, anchor + "\nimport androidx.compose.material.icons.outlined.PhotoCamera", 1)

camera = '''        IconButton(
            onClick = { vm.screen = "xingtu_article_editor" },
            modifier = Modifier.size(42.dp)
        ) {
            Icon(Icons.Outlined.PhotoCamera, contentDescription = "醒图文章编辑器", tint = AppColors.TextMain, modifier = Modifier.size(22.dp))
        }
        Spacer(Modifier.width(2.dp))
'''
if 'contentDescription = "醒图文章编辑器"' not in layout:
    anchor = '        ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing) { vm.toggleEditing() }'
    if layout.count(anchor) != 1:
        raise SystemExit("Expected exactly one Edit button in LayoutScreen TopBar.")
    layout = layout.replace(anchor, camera + anchor, 1)

# Confirm the existing Xiumi entry remains to the RIGHT of Edit.
edit_at = layout.find('ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing)')
xiumi_at = layout.find('contentDescription = "秀米式文章排版"')
camera_at = layout.find('contentDescription = "醒图文章编辑器"')
if min(camera_at, edit_at, xiumi_at) < 0 or not (camera_at < edit_at < xiumi_at):
    raise SystemExit("Editor entry order must be 醒图 camera -> Edit -> 秀米 palette.")
if 'onClick = { vm.screen = "xingtu_article_editor" }' not in layout:
    raise SystemExit("醒图 camera entry does not open its own route.")
if 'onClick = { vm.screen = "xiumi_article_layout" }' not in layout:
    raise SystemExit("秀米 palette entry does not open its own route.")

LAYOUT.write_text(layout, encoding="utf-8")
MAIN.write_text(main, encoding="utf-8")

# Verify distinct routes and composables, with a legacy route retained only for compatibility.
check_main = MAIN.read_text(encoding="utf-8")
for token in (
    '"xiumi_article_layout" -> XiumiArticleLayoutScreen(vm)',
    '"xingtu_article_editor" -> ArticleEditorScreen(vm)',
    '"article_editor" -> ArticleEditorScreen(vm)',
):
    if token not in check_main:
        raise SystemExit("Independent editor route verification failed: " + token)
if "fun ArticleEditorScreen(vm: AppViewModel, onBack: () -> Unit)" not in EDITOR.read_text(encoding="utf-8"):
    raise SystemExit("醒图 ArticleEditorScreen composable is missing.")
if "fun XiumiArticleLayoutScreen(vm: AppViewModel, onBack: () -> Unit)" not in XIUMI.read_text(encoding="utf-8"):
    raise SystemExit("Independent XiumiArticleLayoutScreen composable is missing.")
print("Verified separate editors: 醒图 camera -> ArticleEditorScreen; 秀米 palette -> XiumiArticleLayoutScreen; Edit remains between them.")
