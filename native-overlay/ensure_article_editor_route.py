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
if "import com.shiwanju.app.ui.ArticleEditorScreen" not in main:
    anchor = "import com.shiwanju.app.ui.LayoutScreen"
    if anchor not in main:
        raise SystemExit("Cannot add ArticleEditorScreen import: LayoutScreen import anchor missing.")
    main = main.replace(anchor, anchor + "\nimport com.shiwanju.app.ui.ArticleEditorScreen", 1)

route = """when (vm.screen) {
                        "article_editor" -> ArticleEditorScreen(vm) { vm.screen = "layout" }
                        "layout" -> LayoutScreen(vm)
                        else -> MyScreen(vm)
                    }"""
if '"article_editor" -> ArticleEditorScreen(vm)' not in main:
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
if 'contentDescription = "文章编辑器"' not in layout or 'vm.screen = "article_editor"' not in layout:
    raise SystemExit("Layout page editor icon is missing or does not navigate to article_editor.")

check = MAIN.read_text(encoding="utf-8")
if '"article_editor" -> ArticleEditorScreen(vm)' not in check:
    raise SystemExit("MainActivity article_editor route verification failed.")
if "import com.shiwanju.app.ui.ArticleEditorScreen" not in check:
    raise SystemExit("MainActivity ArticleEditorScreen import verification failed.")
print("Article editor navigation verified: layout icon -> vm.screen=article_editor -> ArticleEditorScreen; back -> layout.")
