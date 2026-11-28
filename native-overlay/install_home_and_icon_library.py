#!/usr/bin/env python3
from pathlib import Path
import re
import shutil

ROOT = Path(".")
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
OVERLAY = ROOT / "native-overlay/app/src/main/java/com/shiwanju/app/ui/HomeAndIconLibrary.kt"
TARGET = JAVA / "ui/HomeAndIconLibrary.kt"
MAIN = JAVA / "MainActivity.kt"

if not OVERLAY.is_file() or not MAIN.is_file():
    raise SystemExit("Home/icon-library source or MainActivity is missing.")
shutil.copy2(OVERLAY, TARGET)
source = MAIN.read_text(encoding="utf-8")

def add_import(name):
    global source
    line = "import com.shiwanju.app.ui." + name
    if line not in source:
        anchor = "import com.shiwanju.app.ui.LayoutScreen"
        if anchor not in source:
            raise SystemExit("Cannot locate MainActivity UI import anchor.")
        source = source.replace(anchor, anchor + "\n" + line, 1)

add_import("ShiWanJuHomeScreen")
add_import("AppIconLibraryScreen")

# Extend the existing screen dispatcher without disturbing the editor routes.
layout_route = '"layout" -> LayoutScreen(vm)'
if source.count(layout_route) != 1:
    raise SystemExit("Expected exactly one layout route in MainActivity.")
source = source.replace(layout_route, '"home" -> ShiWanJuHomeScreen { vm.screen = it }\n                        "icon_library" -> AppIconLibraryScreen { vm.screen = "home" }\n                        ' + layout_route, 1)

my_route = '"my" -> MyScreen(vm)'
if my_route not in source:
    fallback = "else -> MyScreen(vm)"
    if source.count(fallback) != 1:
        raise SystemExit("Cannot uniquely locate MyScreen fallback route.")
    source = source.replace(fallback, my_route + "\n                        else -> ShiWanJuHomeScreen { vm.screen = it }", 1)

# Make the new portal the first landing screen while preserving all subsequent in-app navigation.
anchor = "setContent {"
if "vm.screen = \"home\"" not in source:
    if source.count(anchor) != 1:
        raise SystemExit("Cannot uniquely locate MainActivity setContent.")
    source = source.replace(anchor, anchor + '\n            androidx.compose.runtime.LaunchedEffect(Unit) {\n                if (vm.screen == "layout") vm.screen = "home"\n            }', 1)

required = [
    '"home" -> ShiWanJuHomeScreen',
    '"icon_library" -> AppIconLibraryScreen',
    '"layout" -> LayoutScreen(vm)',
    '"my" -> MyScreen(vm)',
    '"xiumi_article_layout" -> XiumiArticleLayoutScreen(vm)',
    '"xingtu_article_editor" -> ArticleEditorScreen(vm)',
    '"xingtu_editor_v2" -> XingtuEditorV2Screen'
]
for token in required:
    if token not in source:
        raise SystemExit("Home route verification failed: " + token)

MAIN.write_text(source, encoding="utf-8")
print("Installed the new home portal and icon-library route; verified layout, Xiumi, classic Xingtu, Xingtu 2.0 and My routes remain present.")
