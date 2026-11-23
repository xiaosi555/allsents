#!/usr/bin/env python3
"""Render the approved 11 icon compositions and Android adaptive/legacy assets.
The three original logo paths are copied verbatim from 拾万句_简_淡黄色.svg.
Backgrounds and logo treatments follow the matching reference icon styles.
"""
from pathlib import Path
from io import BytesIO
import xml.etree.ElementTree as ET
import cairosvg
from PIL import Image, ImageOps

ROOT = Path(".")
SOURCE = ROOT / "拾万句_简_淡黄色.svg"
RES = ROOT / "source/ShiWanJu-Android/app/src/main/res"
if not SOURCE.is_file():
    raise SystemExit("Missing authoritative logo SVG")

# Approved visual language from the 11-style design preview.
# Reference backgrounds are adapted from shengyu-offline-tts/app/src/main/assets/launcher-icons.
# Mapping keeps each 拾万句 style aligned with the closest material language.
STYLES = {
 "original": ("#FFFFFF", """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#1769C2"/><stop offset="1" stop-color="#62D9F5"/></linearGradient></defs><rect width="108" height="108" rx="22" fill="url(#bg)"/>"""),
 "cowboy": ("#E8D7B6", """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#173B58"/><stop offset="1" stop-color="#7896A8"/></linearGradient><pattern id="p" width="7" height="7" patternUnits="userSpaceOnUse"><path d="M0 0L7 7M-2 2L2 -2M5 9L9 5" stroke="#B8C9D5" stroke-opacity=".28"/></pattern></defs><rect width="108" height="108" rx="22" fill="url(#bg)"/><rect width="108" height="108" fill="url(#p)"/>"""),
 "code": ("#61FF91", """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#06140E"/><stop offset="1" stop-color="#B4FFC9"/></linearGradient><pattern id="p" width="12" height="12" patternUnits="userSpaceOnUse"><path d="M0 0H12M0 0V12" stroke="#39FF79" stroke-opacity=".18"/><text x="2" y="9" font-size="7" fill="#5CFF8F" opacity=".55">01</text></pattern></defs><rect width="108" height="108" rx="22" fill="url(#bg)"/><rect width="108" height="108" fill="url(#p)"/>"""),
 "line": ("#263B42", """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#F8F7F1"/><stop offset="1" stop-color="#73949A"/></linearGradient></defs><rect width="108" height="108" rx="22" fill="url(#bg)"/><path d="M8 14L18 8M88 8L100 17M8 92L18 100M92 96L101 88" stroke="#263B42" stroke-opacity=".2" stroke-width="1.4"/>"""),
 "plush": ("#FFF0D9", """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#C77D91"/><stop offset="1" stop-color="#F3B5C8"/></linearGradient><pattern id="p" width="9" height="9" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.5" fill="#fff" opacity=".2"/><circle cx="7" cy="6" r="2" fill="#7B3D59" opacity=".12"/></pattern></defs><rect width="108" height="108" rx="22" fill="url(#bg)"/><rect width="108" height="108" fill="url(#p)"/>"""),
 "sky": ("#FFFFFF", """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#79C7EF"/><stop offset="1" stop-color="#B4E6F8"/></linearGradient></defs><rect width="108" height="108" rx="22" fill="url(#bg)"/><g fill="#fff" opacity=".55"><path d="M10 26c-1-7 6-11 13-8 4-10 20-8 23 2 9-1 12 11 3 14H18c-5 0-8-3-8-8Z"/></g>"""),
 "space": ("#D8E7FF", """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#050812"/><stop offset="1" stop-color="#8D75FF"/></linearGradient></defs><rect width="108" height="108" rx="22" fill="url(#bg)"/><g fill="#D8E7FF" opacity=".8"><circle cx="18" cy="18" r="1.2"/><circle cx="83" cy="19" r="1"/><circle cx="92" cy="49" r="1.5"/><circle cx="21" cy="82" r="1"/><circle cx="74" cy="91" r="1.3"/></g>"""),
 "graffiti": ("#165CC5", """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#DCEEFF"/><stop offset="1" stop-color="#FF6B8A"/></linearGradient></defs><rect width="108" height="108" rx="22" fill="url(#bg)"/><path d="M0 22L26 0H55L28 32ZM73 108L108 78V108Z" fill="#fff" opacity=".75"/><path d="M11 11l7 5m-9 4 9 5M89 15l8 7m-8 2 8 7" stroke="#FF6B8A" stroke-width="2" stroke-linecap="round"/>"""),
 "playful": ("#2364C7", """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#FFD95D"/><stop offset="1" stop-color="#FF7B75"/></linearGradient></defs><rect width="108" height="108" rx="22" fill="url(#bg)"/><g fill="#FF7B75"><circle cx="29" cy="28" r="4"/><circle cx="79" cy="28" r="4"/></g>"""),
 "8bit": ("#F7E8C8", """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#77718D"/><stop offset="1" stop-color="#E2A9D0"/></linearGradient><pattern id="p" width="9" height="9" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#fff" opacity=".1"/><rect x="4" y="4" width="4" height="4" fill="#15152B" opacity=".12"/></pattern></defs><rect width="108" height="108" rx="22" fill="url(#bg)"/><rect width="108" height="108" fill="url(#p)"/>"""),
 "sketch": ("#E7E0BE", """<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#123B2D"/><stop offset="1" stop-color="#91B78C"/></linearGradient><pattern id="p" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M10 0H0V10" fill="none" stroke="#D8E4C4" stroke-opacity=".25" stroke-width=".65"/></pattern></defs><rect width="108" height="108" rx="22" fill="url(#bg)"/><rect width="108" height="108" fill="url(#p)"/>""")
}

# Read the exact authoritative paths; do not redraw or approximate the logo.
tree = ET.parse(SOURCE)
ns = {"s": "http://www.w3.org/2000/svg"}
paths = [node.attrib["d"] for node in tree.findall(".//s:path", ns)]
if len(paths) != 3:
    raise SystemExit(f"Expected exactly 3 original logo paths, found {len(paths)}")
logo_d = "".join('<path fill="__COLOR__" d="' + d + '"/>' for d in paths)

def logo_svg(color, style=None):
    # Fixed approved geometry and scale: the original logo always occupies 66% of the canvas width.
    # Only the visual treatment changes to match the selected reference material.
    logo_width = 108 * 0.66
    scale = logo_width / 865.26
    translate_x = (108 - logo_width) / 2
    translate_y = 54 - ((0.29 + 804.62) / 2) * scale
    transform = f"translate({translate_x:.5f} {translate_y:.5f}) scale({scale:.8f})"
    if style in ("line", "sketch"):
        paths_markup = "".join(
            '<path fill="none" stroke="' + color + '" stroke-width="28" stroke-linejoin="round" stroke-linecap="round" d="' + d + '"/>'
            for d in paths
        )
    else:
        paths_markup = logo_d.replace("__COLOR__", color)
    return f'<g transform="{transform}">' + paths_markup + '</g>'

def render(svg, size):
    return Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=size, output_height=size))).convert("RGBA")

def save_png(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)

def material_background(name, bg):
    # Reference SVG backgrounds already contain their gradients, patterns and decorative details.
    # Do not layer the former custom textures on top of them.
    return bg

for name, (logo_color, background) in STYLES.items():
    full_svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">{background}{logo_svg(logo_color, name)}</svg>'
    bg_svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">{background}</svg>'
    fg_svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">{logo_svg(logo_color, name)}</svg>'
    bg = material_background(name, render(bg_svg, 512))
    logo = render(f'<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">{logo_svg(logo_color, name)}</svg>', 512)
    full = Image.alpha_composite(bg, logo)
    if name == "8bit":
        full = full.resize((64,64), Image.Resampling.NEAREST).resize((512,512), Image.Resampling.NEAREST)
    # One finished bitmap is shared by the selector, launcher and app drawer.

    # Compose preview and resources from the same SVG definition.
    drawable = RES / "drawable-nodpi"
    save_png(full, drawable / f"icon_style_{name}.png")
    # Remove stale two-layer adaptive assets from earlier builds.
    for stale in [drawable / f"icon_style_{name}_background.png", drawable / f"icon_style_{name}_foreground.png"]:
        if stale.exists():
            stale.unlink()

    # Desktop, folder, and selector all use this same finished composition.
    for density, size in [("mdpi",48),("hdpi",72),("xhdpi",96),("xxhdpi",144),("xxxhdpi",192)]:
        folder = RES / f"mipmap-{density}"
        save_png(ImageOps.fit(full, (size,size), method=Image.Resampling.LANCZOS), folder / f"ic_launcher_style_{name}.png")

    # Android 8+ uses the exact same finished composition as a full-bleed
    # adaptive-icon background layer. A transparent foreground avoids a second
    # inset/safe-area shrink and prevents white/transparent padding.
    adaptive_dir = RES / "mipmap-anydpi-v26"
    adaptive_dir.mkdir(parents=True, exist_ok=True)
    transparent = Image.new("RGBA", (108, 108), (0, 0, 0, 0))
    save_png(transparent, drawable / "launcher_transparent_foreground.png")
    xml = f'''<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/icon_style_{name}" />
    <foreground android:drawable="@drawable/launcher_transparent_foreground" />
    </adaptive-icon>'''
    (adaptive_dir / f"ic_launcher_style_{name}.xml").write_text(xml, encoding="utf-8")

    # The package/install identity uses the original icon and therefore matches
    # the default launcher alias, folder preview and in-app selector.
    if name == "original":
        for density, size in [("mdpi",48),("hdpi",72),("xhdpi",96),("xxhdpi",144),("xxxhdpi",192)]:
            folder = RES / f"mipmap-{density}"
            save_png(ImageOps.fit(full, (size,size), method=Image.Resampling.LANCZOS), folder / "ic_launcher.png")
            save_png(ImageOps.fit(full, (size,size), method=Image.Resampling.LANCZOS), folder / "ic_launcher_round.png")
        base_xml = '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android"><background android:drawable="@drawable/icon_style_original" /><foreground android:drawable="@drawable/launcher_transparent_foreground" /></adaptive-icon>'
        (adaptive_dir / "ic_launcher.xml").write_text(base_xml, encoding="utf-8")
        (adaptive_dir / "ic_launcher_round.xml").write_text(base_xml, encoding="utf-8")

print(f"Generated {len(STYLES)} approved icon compositions from the exact 3-path source logo.")
