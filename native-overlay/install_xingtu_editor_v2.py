#!/usr/bin/env python3
"""Install independent Xingtu Editor V2 sources and a hidden route into generated Android project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
UI = JAVA / "ui"
MAIN = JAVA / "MainActivity.kt"
FILES = {
    ROOT / "native-overlay/app/src/main/java/com/shiwanju/app/ui/XingtuV2Model.kt": UI / "XingtuV2Model.kt",
    ROOT / "native-overlay/app/src/main/java/com/shiwanju/app/ui/XingtuEditorV2Screen.kt": UI / "XingtuEditorV2Screen.kt",
}
for source, target in FILES.items():
    if not source.is_file():
        raise SystemExit(f"Missing independent editor source: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

if not MAIN.is_file():
    raise SystemExit(f"MainActivity source missing: {MAIN}")
main = MAIN.read_text(encoding="utf-8")
import_line = "import com.shiwanju.app.ui.XingtuEditorV2Screen"
if import_line not in main:
    anchor = "import com.shiwanju.app.ui.ArticleEditorScreen"
    if anchor not in main:
        raise SystemExit("Cannot locate existing ArticleEditorScreen import for isolated V2 route.")
    main = main.replace(anchor, anchor + "\n" + import_line, 1)
route_line = '                        "xingtu_editor_v2" -> XingtuEditorV2Screen { vm.screen = "layout" }'
if route_line not in main:
    anchor = '                        "xingtu_article_editor" -> ArticleEditorScreen(vm) { vm.screen = "layout" }'
    if main.count(anchor) != 1:
        raise SystemExit("Cannot locate existing 醒图 route to add the isolated V2 route.")
    main = main.replace(anchor, anchor + "\n" + route_line, 1)
if main.count(import_line) != 1 or main.count(route_line) != 1:
    raise SystemExit("V2 route verification failed: duplicate or missing import/route.")
MAIN.write_text(main, encoding="utf-8")
print("Installed independent Xingtu Editor V2 sources and isolated route (legacy route unchanged).")
