#!/usr/bin/env python3
"""Expose the independent Xingtu Editor V2 from the main layout landing toolbar."""
from pathlib import Path

ROOT = Path(".")
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
LAYOUT = JAVA / "ui/LayoutScreen.kt"
MAIN = JAVA / "MainActivity.kt"

for path in (LAYOUT, MAIN):
    if not path.is_file():
        raise SystemExit(f"Required source missing: {path}")

layout = LAYOUT.read_text(encoding="utf-8")
main = MAIN.read_text(encoding="utf-8")

route = '"xingtu_editor_v2" -> XingtuEditorV2Screen { vm.screen = "layout" }'
if main.count(route) != 1:
    raise SystemExit("The isolated Xingtu V2 route must exist exactly once before adding its home entry.")

legacy = '            onClick = { vm.screen = "xingtu_article_editor" },'
if layout.count(legacy) != 1:
    raise SystemExit("Cannot uniquely locate the existing classic Xingtu home-toolbar entry.")

entry = '''        IconButton(
            onClick = { vm.screen = "xingtu_editor_v2" },
            modifier = Modifier.size(42.dp)
        ) {
            Text("2.0", color = AppColors.TextMain, fontSize = 12.sp)
        }
'''
if 'onClick = { vm.screen = "xingtu_editor_v2" }' not in layout:
    layout = layout.replace(legacy, entry + legacy, 1)

if layout.count('onClick = { vm.screen = "xingtu_editor_v2" }') != 1:
    raise SystemExit("Xingtu V2 home entry verification failed.")
if layout.find('onClick = { vm.screen = "xingtu_editor_v2" }') > layout.find(legacy):
    raise SystemExit("Xingtu V2 entry must appear beside and before the classic Xingtu entry.")

LAYOUT.write_text(layout, encoding="utf-8")
print("Added a visible 2.0 entry beside the classic Xingtu entry; legacy entry unchanged.")
