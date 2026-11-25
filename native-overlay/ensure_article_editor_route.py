#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(".")
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
MAIN = JAVA / "MainActivity.kt"
LAYOUT = JAVA / "ui/LayoutScreen.kt"
EDITOR = JAVA / "ui/XiumiArticleLayoutScreen.kt"

if not EDITOR.is_file():
    raise SystemExit("Independent XiumiArticleLayoutScreen.kt is missing; refusing to build.")
main = MAIN.read_text(encoding="utf-8")
if "import com.shiwanju.app.ui.XiumiArticleLayoutScreen" not in main:
    anchor = "import com.shiwanju.app.ui.LayoutScreen"
    if anchor not in main:
        raise SystemExit("Cannot add XiumiArticleLayoutScreen import.")
    main = main.replace(anchor, anchor + "\nimport com.shiwanju.app.ui.XiumiArticleLayoutScreen", 1)
main = re.sub(r'import com\.shiwanju\.app\.ui\.XiumiArticleEditorScreen\n', '', main)
route = """when (vm.screen) {
                        "article_editor" -> XiumiArticleLayoutScreen(vm) { vm.screen = "layout" }
                        "layout" -> LayoutScreen(vm)
                        else -> MyScreen(vm)
                    }"""
if '"article_editor" -> XiumiArticleLayoutScreen(vm)' not in main:
    patterns = [
        re.compile(r'if\s*\(vm\.screen\s*==\s*"layout"\)\s*LayoutScreen\(vm\)\s*else\s*MyScreen\(vm\)'),
        re.compile(r'when\s*\(vm\.screen\)\s*\{[^}]*"layout"\s*->\s*LayoutScreen\(vm\)[^}]*else\s*->\s*MyScreen\(vm\)[^}]*\}', re.S)
    ]
    match = next((m for p in patterns if (m := p.search(main))), None)
    if not match:
        raise SystemExit("Cannot locate MainActivity screen dispatcher.")
    main = main[:match.start()] + route + main[match.end():]
MAIN.write_text(main, encoding="utf-8")

layout = LAYOUT.read_text(encoding="utf-8")
if 'contentDescription = "秀米式文章排版"' not in layout or 'vm.screen = "article_editor"' not in layout:
    raise SystemExit("Palette entry is missing from LayoutScreen.")
if 'ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing)' not in layout:
    raise SystemExit("Existing Edit entry missing; preserve it.")
icon_at = layout.find('contentDescription = "秀米式文章排版"')
edit_at = layout.find('ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing)')
if icon_at < edit_at:
    raise SystemExit("Palette entry must remain to the right of Edit.")
check = MAIN.read_text(encoding="utf-8")
for token in ['"article_editor" -> XiumiArticleLayoutScreen(vm)', '"layout" -> LayoutScreen(vm)', "import com.shiwanju.app.ui.XiumiArticleLayoutScreen"]:
    if token not in check: raise SystemExit("Route verification failed: " + token)
if "fun XiumiArticleLayoutScreen(vm: AppViewModel, onBack: () -> Unit)" not in EDITOR.read_text(encoding="utf-8"):
    raise SystemExit("Independent Xiumi editor composable missing.")
print("Independent Xiumi editor route verified: palette -> XiumiArticleLayoutScreen -> original layout.")
