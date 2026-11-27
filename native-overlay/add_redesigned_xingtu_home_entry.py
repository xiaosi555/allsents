#!/usr/bin/env python3
"""Expose the redesigned Xingtu editor as a first-class Home entry."""
from pathlib import Path

ROOT = Path(".")
MY = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/MyScreens.kt"
if not MY.is_file():
    raise SystemExit("MyScreens.kt is missing; cannot add the Home entry")

s = MY.read_text(encoding="utf-8")
anchor = '        HomeGroupRow("文章", "共 ${d.files.text.size} 个文案模块") { go("texts") }'
entry = '        HomeGroupRow("醒图", "新版画布式文章编辑器") { vm.screen = "xingtu_article_editor" }\n        Spacer(Modifier.height(8.dp))\n'
if entry.strip() not in s:
    if s.count(anchor) != 1:
        raise SystemExit("Home article group anchor missing or ambiguous; no entry inserted")
    s = s.replace(anchor, entry + anchor, 1)

if 'HomeGroupRow("醒图", "新版画布式文章编辑器") { vm.screen = "xingtu_article_editor" }' not in s:
    raise SystemExit("Redesigned Xingtu Home entry verification failed")
MY.write_text(s, encoding="utf-8")
print("Home entry added: 醒图 opens the redesigned editor route.")
