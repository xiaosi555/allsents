#!/usr/bin/env python3
"""Centralize every Compose Material icon used by the app and expose it in Icon Library."""
from pathlib import Path
import re

ROOT = Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app")
UI = ROOT / "ui"
LIBRARY = UI / "HomeAndIconLibrary.kt"
if not LIBRARY.is_file():
    raise SystemExit("HomeAndIconLibrary.kt must be installed before icon centralization.")

files = sorted(UI.rglob("*.kt"))
pattern = re.compile(r"Icons\.(Outlined|Default|Filled|Rounded|TwoTone)\.([A-Za-z][A-Za-z0-9_]*)")
found = set()
for path in files:
    source = path.read_text(encoding="utf-8")
    found.update(pattern.findall(source))
if not found:
    raise SystemExit("No Compose Material icon references found; refusing an empty registry.")

style_package = {"Outlined": "outlined", "Default": "filled", "Filled": "filled", "Rounded": "rounded", "TwoTone": "twotone"}
style_order = {"Outlined": 0, "Default": 1, "Filled": 2, "Rounded": 3, "TwoTone": 4}
items = sorted(found, key=lambda x: (style_order[x[0]], x[1]))
imports = []
properties = []
extra_entries = []
category_words = {
    "导航": ("Home", "Arrow", "Menu", "Dashboard", "Apps", "Grid", "View"),
    "素材": ("Image", "Photo", "Camera", "Folder", "File", "Video", "Audio", "Music", "Attachment"),
    "编辑": ("Edit", "Text", "Format", "Brush", "Crop", "Rotate", "Layers", "Palette", "Color", "Filter", "Opacity", "Border", "Align", "Transform", "Undo", "Redo", "Content", "Cut", "Copy", "Paste", "Delete", "Lock", "Visibility"),
    "文件": ("Save", "Download", "Upload", "Share", "Cloud", "History", "Print", "Export", "Import"),
}
def category(name):
    for group, words in category_words.items():
        if any(word.lower() in name.lower() for word in words):
            return group
    return "通用"
def humanize(name):
    return re.sub(r"(?<!^)(?=[A-Z])", " ", name).strip()

for style, name in items:
    prop = style + name
    package = style_package[style]
    imports.append(f"import androidx.compose.material.icons.{package}.{name}")
    properties.append(f"    val {prop} = Icons.{style}.{name}")
    key = "material-" + style.lower() + "-" + re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name).lower()
    title = humanize(name)
    extra_entries.append(f'    AppIconItem("{key}", "{title}", "{category(name)}", AppIconVectors.{prop})')

source = LIBRARY.read_text(encoding="utf-8")
# The registry uses explicit imports; keep existing Icons import for the single source mapping.
source = re.sub(r"import androidx\.compose\.material\.icons\.(outlined|filled|rounded|twotone)\.\*\n", "", source)
source = source.replace("import androidx.compose.material.icons.Icons\n", "import androidx.compose.material.icons.Icons\n")
for line in imports:
    if line not in source:
        source = source.replace("import androidx.compose.material.icons.Icons\n", "import androidx.compose.material.icons.Icons\n" + line + "\n", 1)
registry = "internal object AppIconVectors {\n" + "\n".join(properties) + "\n}\n\n"
marker = "private data class AppIconItem"
if "internal object AppIconVectors {" in source:
    source = re.sub(r"private object AppIconVectors \{.*?\n\}\n\n", registry, source, count=1, flags=re.S)
else:
    if marker not in source:
        raise SystemExit("Cannot locate icon library registry insertion point.")
    source = source.replace(marker, registry + marker, 1)

# All screens now reference the shared vector registry rather than importing icons ad hoc.
for path in files:
    text = path.read_text(encoding="utf-8")
    if path == LIBRARY:
        registry_start = text.find("internal object AppIconVectors {")
        registry_end = text.find("\\n}\\n\\n", registry_start)
        if registry_start < 0 or registry_end < 0:
            raise SystemExit("Generated icon vector registry is malformed.")
        registry_end += len("\\n}\\n\\n")
        text = text[:registry_start] + text[registry_start:registry_end] + pattern.sub(lambda m: "AppIconVectors." + m.group(1) + m.group(2), text[registry_end:])
        updated = text
    else:
        updated = pattern.sub(lambda m: "AppIconVectors." + m.group(1) + m.group(2), text)
    if path == LIBRARY:
        # The library list also contains its own icons; append every icon used elsewhere.
        start = updated.find("private val appIconItems = listOf(")
        if start < 0:
            raise SystemExit("Cannot locate appIconItems declaration.")
        end = updated.find("\n)", start)
        if end < 0:
            raise SystemExit("Cannot locate end of appIconItems declaration.")
        updated = updated[:end] + "\n) + listOf(\n" + ",\n".join(extra_entries) + "\n" + updated[end+2:]
    path.write_text(updated, encoding="utf-8")

# Verify there are no remaining direct vector references and that every icon is represented.
remaining = []
for path in files:
    text = path.read_text(encoding="utf-8")
    if pattern.search(text):
        remaining.append(str(path))
if remaining:
    raise SystemExit("Direct Material icon references remain: " + ", ".join(remaining))
print(f"Centralized {len(items)} distinct Material icon variants and added them to the searchable icon library.")
