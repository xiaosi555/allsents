#!/usr/bin/env python3
"""Stage D: standardize modal dialog chrome on the redesigned Xingtu editor only.

The patch intentionally changes presentation parameters, not dialog state,
callbacks, field values, validation, import/export, crop, or layout logic.
"""
from pathlib import Path
import re

ROOT = Path(".")
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorRedesignedScreen.kt"
ERROR = ROOT / "xingtu_stage_d_patch_error.txt"

def fail(message: str):
    ERROR.write_text(message + "\n", encoding="utf-8")
    raise SystemExit(message)

if not EDITOR.is_file():
    fail("Redesigned editor source missing; Stage D must run after Stage C")

source = EDITOR.read_text(encoding="utf-8")

def matching_delimiter(text: str, start: int, opening: str, closing: str) -> int:
    depth = 0
    quote = None
    triple = False
    escaped = False
    line_comment = False
    block_comment = False
    i = start
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if line_comment:
            if ch == "\n":
                line_comment = False
            i += 1
            continue
        if block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                i += 2
            else:
                i += 1
            continue
        if quote:
            if triple:
                if text.startswith('"""', i):
                    quote = None
                    triple = False
                    i += 3
                else:
                    i += 1
                continue
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            i += 1
            continue
        if ch == "/" and nxt == "/":
            line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            block_comment = True
            i += 2
            continue
        if text.startswith('"""', i):
            quote = '"'
            triple = True
            i += 3
            continue
        if ch in ('"', "'"):
            quote = ch
            i += 1
            continue
        if ch == opening:
            depth += 1
        elif ch == closing:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f"Unclosed Kotlin delimiter {opening} at {start}")

def split_top_level_args(args: str):
    parts, start = [], 0
    paren = brace = bracket = 0
    quote = None
    triple = False
    escaped = False
    i = 0
    while i < len(args):
        ch = args[i]
        if quote:
            if triple:
                if args.startswith('"""', i):
                    quote = None
                    triple = False
                    i += 3
                    continue
            elif escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            i += 1
            continue
        if args.startswith('"""', i):
            quote = '"'
            triple = True
            i += 3
            continue
        if ch in ('"', "'"):
            quote = ch
        elif ch == "(":
            paren += 1
        elif ch == ")":
            paren -= 1
        elif ch == "{":
            brace += 1
        elif ch == "}":
            brace -= 1
        elif ch == "[":
            bracket += 1
        elif ch == "]":
            bracket -= 1
        elif ch == "," and paren == brace == bracket == 0:
            parts.append(args[start:i])
            start = i + 1
        i += 1
    tail = args[start:]
    if tail.strip():
        parts.append(tail)
    return parts

def named_argument_names(args: str):
    names = set()
    for part in split_top_level_args(args):
        match = re.match(r"\s*([A-Za-z_]\w*)\s*=", part)
        if match:
            names.add(match.group(1))
    return names

def call_spans(text: str, name: str):
    spans = []
    pattern = re.compile(r"\b" + re.escape(name) + r"\s*\(")
    for match in pattern.finditer(text):
        opening = text.find("(", match.start(), match.end())
        closing = matching_delimiter(text, opening, "(", ")")
        spans.append((match.start(), opening, closing))
    return spans

def normalize_call_arguments(text: str, name: str, defaults: dict, force: dict | None = None):
    force = force or {}
    spans = call_spans(text, name)
    for call_start, opening, closing in reversed(spans):
        args = text[opening + 1:closing]
        parts = split_top_level_args(args)
        current = {}
        for part in parts:
            m = re.match(r"\s*([A-Za-z_]\w*)\s*=(.*)$", part, re.S)
            if m:
                current[m.group(1)] = m.group(2).strip()
        additions = []
        for key, value in defaults.items():
            if key not in current:
                additions.append(f"{key} = {value}")
        for key, value in force.items():
            if key in current:
                replaced = False
                new_parts = []
                for part in parts:
                    m = re.match(r"(\s*)" + re.escape(key) + r"(\s*=\s*)(.*)$", part, re.S)
                    if m and not replaced:
                        new_parts.append(m.group(1) + key + m.group(2) + value)
                        replaced = True
                    else:
                        new_parts.append(part)
                parts = new_parts
            else:
                additions.append(f"{key} = {value}")
        if additions:
            prefix = ", ".join(additions)
            existing = ", ".join(p.strip() for p in parts if p.strip())
            replacement = prefix + (", " + existing if existing else "")
        elif force:
            replacement = ", ".join(p.strip() for p in parts if p.strip())
        else:
            continue
        text = text[:opening + 1] + replacement + text[closing:]
    return text, len(spans)

# AlertDialogs share the same dark editor surface and hierarchy. Existing custom
# action lambdas and all dialog state transitions remain untouched.
source, alert_count = normalize_call_arguments(
    source,
    "AlertDialog",
    {
        "shape": "RoundedCornerShape(16.dp)",
        "containerColor": "Color(0xFF242424)",
        "titleContentColor": "Color(0xFFF5F5F5)",
        "textContentColor": "Color(0xFFD0D0D0)",
        "tonalElevation": "0.dp",
    },
    {"shape": "RoundedCornerShape(16.dp)"},
)
if alert_count < 1:
    fail("No AlertDialog calls found; source shape changed unexpectedly")

# Dropdown menus remain lightweight menus, not modal cards. Keep any existing
# theme-specific container color and standardize only missing surface defaults.
source, menu_count = normalize_call_arguments(
    source,
    "DropdownMenu",
    {
        "containerColor": "Color(0xFF242424)",
        "shape": "RoundedCornerShape(12.dp)",
        "tonalElevation": "0.dp",
        "shadowElevation": "8.dp",
    },
    {"shape": "RoundedCornerShape(12.dp)"},
)

# Custom Dialog windows retain their own surface colors and specialized content.
# Normalize the first Surface inside each Dialog body to a shared 16dp radius.
dialog_spans = call_spans(source, "Dialog")
surface_updates = 0
for _, opening, closing in reversed(dialog_spans):
    cursor = closing + 1
    while cursor < len(source) and source[cursor].isspace():
        cursor += 1
    if cursor >= len(source) or source[cursor] != "{":
        continue
    body_end = matching_delimiter(source, cursor, "{", "}")
    body = source[cursor:body_end + 1]
    surface = re.search(r"\bSurface\s*\(", body)
    if not surface:
        continue
    surface_open = body.find("(", surface.start(), surface.end())
    surface_close = matching_delimiter(body, surface_open, "(", ")")
    args = body[surface_open + 1:surface_close]
    names = named_argument_names(args)
    if "shape" in names:
        args_parts = split_top_level_args(args)
        rewritten = []
        for part in args_parts:
            if re.match(r"\s*shape\s*=", part):
                rewritten.append(re.sub(r"^(\s*shape\s*=\s*).*$", r"\1RoundedCornerShape(16.dp)", part, count=1, flags=re.S))
            else:
                rewritten.append(part)
        new_args = ", ".join(p.strip() for p in rewritten if p.strip())
    else:
        new_args = "shape = RoundedCornerShape(16.dp)" + (", " + args.strip() if args.strip() else "")
    body = body[:surface_open + 1] + new_args + body[surface_close:]
    source = source[:cursor] + body + source[body_end + 1:]
    surface_updates += 1

# Guard the shared input dialog and specialized editor windows against accidental
# deletion/rewiring. These names are stable business entry points.
required = {
    "shared input dialog retained": "private fun EditorInputDialog(" in source,
    "custom crop dialog retained": "if (showCustomImageCrop" in source,
    "layout builder retained": "if (showLayoutBuilder" in source,
    "article info retained": "if (showArticleInfo" in source,
    "compatibility report retained": "if (showCompatibilityReport" in source,
    "article package preview retained": "if (showArticlePackagePreview" in source,
    "revision preview retained": "revisionPreview" in source,
    "template preview retained": "templatePreview" in source,
}
missing = [name for name, ok in required.items() if not ok]
if missing:
    fail("Stage D preservation validation failed: " + ", ".join(missing))

# Re-scan every AlertDialog to ensure the standard frame is present.
for _, opening, closing in call_spans(source, "AlertDialog"):
    args = source[opening + 1:closing]
    names = named_argument_names(args)
    for required_name in ("shape", "containerColor", "titleContentColor", "textContentColor", "tonalElevation"):
        if required_name not in names:
            fail(f"AlertDialog missing shared style argument: {required_name}")

EDITOR.write_text(source, encoding="utf-8")
print(
    "Stage D dialog chrome normalized: "
    f"{alert_count} AlertDialog calls, {menu_count} DropdownMenu calls, "
    f"{surface_updates} custom Dialog surfaces; all editor actions preserved."
)
