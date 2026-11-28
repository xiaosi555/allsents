#!/usr/bin/env python3
"""Create an isolated 醒图 3.0 screen from the fully patched 醒图 editor."""
from pathlib import Path
import re

ROOT = Path(".")
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
EDITOR = JAVA / "ui/ArticleEditorScreen.kt"
V3_DIR = JAVA / "ui/v3"
V3 = V3_DIR / "ArticleEditorScreenV3.kt"
MAIN = JAVA / "MainActivity.kt"
LAYOUT = JAVA / "ui/LayoutScreen.kt"

for path in (EDITOR, MAIN, LAYOUT):
    if not path.is_file():
        raise SystemExit("醒图 3.0 prerequisite missing: " + str(path))

source = EDITOR.read_text(encoding="utf-8")
if source.count("package com.shiwanju.app.ui") != 1:
    raise SystemExit("Cannot uniquely identify ArticleEditorScreen package declaration.")
if source.count("fun ArticleEditorScreen(vm: AppViewModel, onBack: () -> Unit)") != 1:
    raise SystemExit("Cannot uniquely identify the complete ArticleEditorScreen composable.")

# A separate Kotlin package gives the migrated screen its own private state,
# bridge, helpers and panel types without colliding with the original editor.
source = source.replace(
    "package com.shiwanju.app.ui",
    "package com.shiwanju.app.ui.v3\n\nimport com.shiwanju.app.ui.*",
    1,
)
source = source.replace(
    "fun ArticleEditorScreen(vm: AppViewModel, onBack: () -> Unit)",
    "fun ArticleEditorScreenV3(vm: AppViewModel, onBack: () -> Unit)",
    1,
)
source = source.replace("醒图 · ", "醒图 3.0 · ")
if "fun ArticleEditorScreenV3(vm: AppViewModel, onBack: () -> Unit)" not in source:
    raise SystemExit("醒图 3.0 composable generation failed.")
if "醒图 3.0 · " not in source:
    raise SystemExit("醒图 3.0 identity label was not applied.")
V3_DIR.mkdir(parents=True, exist_ok=True)
V3.write_text(source, encoding="utf-8")

# Add an independent route and import; the classic route remains untouched.
main = MAIN.read_text(encoding="utf-8")
v3_import = "import com.shiwanju.app.ui.v3.ArticleEditorScreenV3"
if v3_import not in main:
    anchor = "import com.shiwanju.app.ui.ArticleEditorScreen"
    if anchor not in main:
        raise SystemExit("Cannot locate original 醒图 import in MainActivity.")
    main = main.replace(anchor, anchor + "\n" + v3_import, 1)
route = '"xingtu_article_editor_v3" -> ArticleEditorScreenV3(vm) { vm.screen = "layout" }'
if route not in main:
    anchor = '"xingtu_article_editor" -> ArticleEditorScreen(vm) { vm.screen = "layout" }'
    if main.count(anchor) != 1:
        raise SystemExit("Cannot uniquely locate the original 醒图 route.")
    main = main.replace(anchor, anchor + "\n                        " + route, 1)
MAIN.write_text(main, encoding="utf-8")

# Add a visibly named 3.0 entry to the existing Layout toolbar without moving
# or replacing the classic camera entry, Edit action, or Xiumi palette entry.
layout = LAYOUT.read_text(encoding="utf-8")
entry = '''        TextButton(onClick = { vm.screen = "xingtu_article_editor_v3" }) {
            Text("3.0", color = AppColors.Theme, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
        }
'''
if 'vm.screen = "xingtu_article_editor_v3"' not in layout:
    anchor = '        ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing) { vm.toggleEditing() }'
    if layout.count(anchor) != 1:
        raise SystemExit("Cannot uniquely locate the Layout Edit action for the 3.0 entry.")
    layout = layout.replace(anchor, entry + anchor, 1)
LAYOUT.write_text(layout, encoding="utf-8")

# Fail the build early if the two routes or toolbar entry are not independent.
check_main = MAIN.read_text(encoding="utf-8")
check_layout = LAYOUT.read_text(encoding="utf-8")
checks = (
    v3_import,
    '"xingtu_article_editor" -> ArticleEditorScreen(vm)',
    route,
)
for token in checks:
    if token not in check_main:
        raise SystemExit("醒图 3.0 route verification failed: " + token)
if check_layout.count('vm.screen = "xingtu_article_editor_v3"') != 1:
    raise SystemExit("排版页 must contain exactly one 醒图 3.0 entry.")
if not V3.is_file() or "fun ArticleEditorScreenV3(" not in V3.read_text(encoding="utf-8"):
    raise SystemExit("醒图 3.0 migrated source file is missing.")
print("Verified: original 醒图 remains; independent 醒图 3.0 screen, route and 排版 entry are installed.")
