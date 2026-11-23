#!/usr/bin/env python3
"""Generate 拾万句 launcher icons using the exact reference sprite composition."""
from pathlib import Path
from io import BytesIO
import xml.etree.ElementTree as ET
import cairosvg
from PIL import Image, ImageOps

ROOT = Path(".")
SOURCE = ROOT / "拾万句_简_淡黄色.svg"
SPRITE = ROOT / "native-overlay/assets/launcher-sprite.svg"
RES = ROOT / "source/ShiWanJu-Android/app/src/main/res"
NS = "{http://www.w3.org/2000/svg}"

# 拾万句 theme -> (reference symbol, solid logo color, number of background-only decorations)
# Logo is always rendered as three SOLID filled paths. No hollow/outline conversion.
STYLES = {
    "original": ("original", "#FFFFFF", 0, "#01CC7A"),
    "classic": ("original", "#FFFFFF", 0, "#1769C2"),
    "cowboy": ("ceramic", "#E8D7B6", 1),
    "code": ("graphite", "#61FF91", 1),
    "line": ("minimal", "#263B42", 1),
    "plush": ("plush", "#FFF0D9", 1),
    "sky": ("ocean", "#FFFFFF", 1),
    "space": ("glass", "#D8E7FF", 1),
    "graffiti": ("flat", "#165CC5", 2),
    "playful": ("ivory", "#2364C7", 0),
    "8bit": ("violet", "#F7E8C8", 0),
    "sketch": ("manuscript", "#E7E0BE", 1),
}

if not SOURCE.is_file() or not SPRITE.is_file():
    raise SystemExit("Missing original 拾万句 logo or exact reference launcher sprite")

logo_tree = ET.parse(SOURCE)
logo_paths = [node.attrib["d"] for node in logo_tree.findall(".//" + NS + "path")]
if len(logo_paths) != 3:
    raise SystemExit(f"Expected 3 original 拾万句 logo paths, found {len(logo_paths)}")

sprite_tree = ET.parse(SPRITE)
symbols = {node.attrib["id"]: node for node in sprite_tree.findall(NS + "symbol")}
if len(symbols) != 11:
    raise SystemExit(f"Expected 11 reference symbols, found {len(symbols)}")

def serialize(node):
    return ET.tostring(node, encoding="unicode")

def build_background(style, symbol_id, decoration_count, background_color=None):
    symbol = symbols[symbol_id]
    rect = next((node for node in list(symbol) if node.tag == NS + "rect"), None)
    group = next((node for node in list(symbol) if node.tag == NS + "g"), None)
    if rect is None or group is None:
        raise SystemExit("Invalid reference symbol: " + symbol_id)

    # Retain every background accent in its original location and transform.
    # The mountain/logo and sound-wave paths from the reference are intentionally
    # excluded, so the new logo never erases or replaces the background artwork.
    if background_color:
        rect = ET.fromstring(serialize(rect))
        rect.set("fill", background_color)
    decorations = list(group)[:decoration_count]
    decor_svg = "".join(serialize(node) for node in decorations)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">'
        + serialize(rect)
        + f'<g transform="{group.attrib.get("transform", "")}">{decor_svg}</g>'
        + '</svg>'
    )

def build_logo(color, pixelated=False, width_ratio=0.66):
    # Reference sprite's complete logo+sound-wave bounds after its transform:
    # x=17.74..90.26, y=32.54..87.30 (center x=54, y=59.92).
    # Fit 拾万句's original aspect ratio to the same reference width and center.
    source_width = 865.26
    source_center_x = 432.66
    source_center_y = (90.0 + 777.86) / 2.0
    reference_width = 108.0 * width_ratio
    reference_center_y = 14.04 + ((25.0 + 99.0) / 2.0) * 0.74
    scale = reference_width / source_width
    tx = 54.0 - source_center_x * scale
    ty = reference_center_y - source_center_y * scale
    transform = f"translate({tx:.6f} {ty:.6f}) scale({scale:.9f})"

    # All three original logo components remain filled. This prevents the
    # ring/arch from becoming hollow due to accidental stroke-only rendering.
    paths = "".join(f'<path fill="{color}" d="{d}"/>' for d in logo_paths)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">'
        + f'<g transform="{transform}">{paths}</g></svg>'
    )

def render(svg, size=512):
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=size, output_height=size)
    return Image.open(BytesIO(png)).convert("RGBA")

def save(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)

# Adaptive icon XMLs reference a transparent foreground layer because the
# composed artwork (background + logo) is intentionally kept in one drawable.
# Always generate this resource so AAPT can resolve every launcher alias.
transparent_foreground = RES / "drawable-nodpi" / "launcher_transparent_foreground.png"
save(Image.new("RGBA", (512, 512), (0, 0, 0, 0)), transparent_foreground)

for style, style_data in STYLES.items():
    symbol_id, logo_color, decoration_count = style_data[:3]
    background_color = style_data[3] if len(style_data) > 3 else None
    background = render(build_background(style, symbol_id, decoration_count, background_color))
    # Keep two logo scales: legacy/in-app artwork is 66% of the canvas;
    # adaptive foreground is 44%, compensating for the launcher's ~1.5x
    # adaptive-icon foreground presentation scale (44% x 1.5 ~= 66%).
    logo = render(build_logo(logo_color, pixelated=(style == "8bit"), width_ratio=0.66))
    adaptive_logo = render(build_logo(logo_color, pixelated=(style == "8bit"), width_ratio=0.44))

    # Pixelate only the logo layers for 8bit; keep background details crisp.
    if style == "8bit":
        logo = logo.resize((64, 64), Image.Resampling.NEAREST).resize((512, 512), Image.Resampling.NEAREST)
        adaptive_logo = adaptive_logo.resize((64, 64), Image.Resampling.NEAREST).resize((512, 512), Image.Resampling.NEAREST)

    drawable = RES / "drawable-nodpi"
    save(background, drawable / f"icon_style_{style}_background.png")
    save(adaptive_logo, drawable / f"icon_style_{style}_foreground.png")
    composed = Image.alpha_composite(background, logo)
    save(composed, drawable / f"icon_style_{style}.png")

    for density, size in [
        ("mdpi", 48), ("hdpi", 72), ("xhdpi", 96),
        ("xxhdpi", 144), ("xxxhdpi", 192),
    ]:
        folder = RES / f"mipmap-{density}"
        save(ImageOps.fit(composed, (size, size), method=Image.Resampling.LANCZOS),
             folder / f"ic_launcher_style_{style}.png")

    adaptive = RES / "mipmap-anydpi-v26"
    adaptive.mkdir(parents=True, exist_ok=True)
    (adaptive / f"ic_launcher_style_{style}.xml").write_text(
        f'<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">'
        f'<background android:drawable="@drawable/icon_style_{style}_background" />'
        f'<foreground android:drawable="@drawable/icon_style_{style}_foreground" />'
        f'</adaptive-icon>',
        encoding="utf-8",
    )

    if style == "original":
        for density, size in [
            ("mdpi", 48), ("hdpi", 72), ("xhdpi", 96),
            ("xxhdpi", 144), ("xxxhdpi", 192),
        ]:
            folder = RES / f"mipmap-{density}"
            legacy = ImageOps.fit(composed, (size, size), method=Image.Resampling.LANCZOS)
            save(legacy, folder / "ic_launcher.png")
            save(legacy, folder / "ic_launcher_round.png")
        base_xml = (
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">'
            '<background android:drawable="@drawable/icon_style_original_background" />'
            '<foreground android:drawable="@drawable/icon_style_original_foreground" />'
            '</adaptive-icon>'
        )
        (adaptive / "ic_launcher.xml").write_text(base_xml, encoding="utf-8")
        (adaptive / "ic_launcher_round.xml").write_text(base_xml, encoding="utf-8")

print(f"Generated {len(STYLES)} icon styles: 66% legacy/in-app logo and 44% adaptive foreground (launcher-scale compensated).")
