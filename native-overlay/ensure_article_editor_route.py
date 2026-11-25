#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
MAIN = JAVA / "MainActivity.kt"
LAYOUT = JAVA / "ui/LayoutScreen.kt"
EDITOR = JAVA / "ui/ArticleEditorScreen.kt"

if not EDITOR.is_file():
    raise SystemExit("ArticleEditorScreen.kt is missing; refusing to build without the destination screen.")

main = MAIN.read_text(encoding="utf-8")
if "import com.shiwanju.app.ui.XiumiArticleEditorScreen" not in main:
    anchor = "import com.shiwanju.app.ui.LayoutScreen"
    if anchor not in main:
        raise SystemExit("Cannot add XiumiArticleEditorScreen import: LayoutScreen import anchor missing.")
    main = main.replace(anchor, anchor + "\nimport com.shiwanju.app.ui.XiumiArticleEditorScreen", 1)

route = """when (vm.screen) {
                        "article_editor" -> XiumiArticleEditorScreen(vm) { vm.screen = "layout" }
                        "layout" -> LayoutScreen(vm)
                        else -> MyScreen(vm)
                    }"""
if '"article_editor" -> XiumiArticleEditorScreen(vm)' not in main:
    patterns = [
        re.compile(r'if\s*\(vm\.screen\s*==\s*"layout"\)\s*LayoutScreen\(vm\)\s*else\s*MyScreen\(vm\)'),
        re.compile(r'if\s*\(vm\.screen\s*==\s*"layout"\)\s*\{\s*LayoutScreen\(vm\)\s*\}\s*else\s*\{\s*MyScreen\(vm\)\s*\}', re.S),
    ]
    match = next((m for pattern in patterns if (m := pattern.search(main))), None)
    if not match:
        raise SystemExit("Cannot find the MainActivity screen dispatcher. Actual screen lines: " + repr([x.strip() for x in main.splitlines() if "LayoutScreen(vm)" in x or "MyScreen(vm)" in x]))
    main = main[:match.start()] + route + main[match.end():]

MAIN.write_text(main, encoding="utf-8")

layout = LAYOUT.read_text(encoding="utf-8")
if 'contentDescription = "文章编辑器"' not in layout:
    raise SystemExit("Layout page article editor icon is missing.")
if 'onClick = { vm.screen = "article_editor" }' not in layout:
    raise SystemExit("Layout page article editor icon has no navigation click handler.")
if 'ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing)' not in layout:
    raise SystemExit("Layout page Edit action anchor missing.")
icon_at = layout.find('contentDescription = "文章编辑器"')
edit_at = layout.find('ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing)')
if icon_at < 0 or edit_at < 0 or icon_at > edit_at:
    raise SystemExit("Article editor icon must be positioned immediately before the Edit action.")
if 'vm.screen = "article_editor"' not in layout:
    raise SystemExit("Layout page article editor route target is missing.")

check = MAIN.read_text(encoding="utf-8")
if '"article_editor" -> XiumiArticleEditorScreen(vm)' not in check:
    raise SystemExit("MainActivity article_editor route verification failed.")
if '"layout" -> LayoutScreen(vm)' not in check:
    raise SystemExit("MainActivity layout return route verification failed.")
if "import com.shiwanju.app.ui.XiumiArticleEditorScreen" not in check:
    raise SystemExit("MainActivity XiumiArticleEditorScreen import verification failed.")
if 'fun XiumiArticleEditorScreen(vm: AppViewModel, onBack: () -> Unit)' not in EDITOR.read_text(encoding="utf-8"):
    raise SystemExit("Dedicated Xiumi editor screen entry is missing.")
print("Article editor navigation verified: visible icon LEFT of Edit -> click -> XiumiArticleEditorScreen -> back to LayoutScreen.")
