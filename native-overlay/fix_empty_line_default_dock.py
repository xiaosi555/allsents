#!/usr/bin/env python3
"""Route a caret in an empty canvas paragraph to the default editor dock."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "editor_empty_line_dock_patch_error.txt"

if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")

s = EDITOR.read_text(encoding="utf-8")
helper_anchor = "                             function reportSelection(){"
helper = """                             function isEmptyCanvasCaretLine(node){
                               if(!node)return false;
                               const element=node.nodeType===1?node:node.parentElement;
                               if(!element||!element.closest)return false;
                               const line=element.closest('p,h1,h2,h3,h4,h5,h6,li,blockquote,pre');
                               return !!(line&&root.contains(line)&&!(line.textContent||'').trim());
                             }
                             function reportSelection(){"""
if s.count(helper_anchor) != 1:
    ERROR.write_text(f"reportSelection anchor count: {s.count(helper_anchor)}\n", encoding="utf-8")
    raise SystemExit("Empty-line dock patch: reportSelection anchor mismatch")
s = s.replace(helper_anchor, helper, 1)
old = "                                 else if(target&&/^(P|H1|H2|H3|H4|BLOCKQUOTE|PRE|UL|OL)$/.test(target.tagName))kind='CARET';"
new = """                                 else if(collapsed&&isEmptyCanvasCaretLine(node)){kind='NONE';target=null;}
                                 else if(target&&/^(P|H1|H2|H3|H4|BLOCKQUOTE|PRE|UL|OL)$/.test(target.tagName))kind='CARET';"""
if s.count(old) != 1:
    ERROR.write_text(f"empty caret classification anchor count: {s.count(old)}\\n", encoding="utf-8")
    raise SystemExit("Empty-line dock patch: caret classification anchor mismatch")
s = s.replace(old, new, 1)
required = ["function isEmptyCanvasCaretLine(node)", "else if(collapsed&&isEmptyCanvasCaretLine(node)){kind='NONE';target=null;}"]
missing = [item for item in required if item not in s]
if missing:
    ERROR.write_text("Missing expected patch output: " + ", ".join(missing) + "\\n", encoding="utf-8")
    raise SystemExit("Empty-line dock patch validation failed")
EDITOR.write_text(s, encoding="utf-8")
print("Empty canvas lines now report selection kind NONE; the default bottom dock is restored.")
