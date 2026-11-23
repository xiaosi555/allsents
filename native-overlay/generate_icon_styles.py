#!/usr/bin/env python3
"""Render the approved 11 icon compositions and Android adaptive/legacy assets.
The three original logo paths are copied verbatim from 拾万句_简_淡黄色.svg.
Only the background treatment and logo fill color vary between styles.
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
STYLES = {
 "original": ("#FFF1D2", """<rect width="108" height="108" fill="#4D4638"/><rect x="4" y="4" width="100" height="100" rx="23" fill="#63563F"/><path d="M8 25H100M8 83H100" stroke="#8D7956" stroke-width=".6" opacity=".65"/>"""),
 "cowboy": ("#F8E7C8", """<rect width="108" height="108" fill="#315B78"/><path d="M0 12L108 0V108H0Z" fill="#3E7190"/><path d="M8 0V108M100 0V108" stroke="#A9C7D6" stroke-width=".8" stroke-dasharray="2 2" opacity=".7"/><path d="M0 17H108M0 91H108" stroke="#23475F" stroke-width="2" opacity=".55"/><circle cx="12" cy="12" r="2" fill="#D7B78C"/><circle cx="96" cy="96" r="2" fill="#D7B78C"/>"""),
 "code": ("#C6FFE8", """<rect width="108" height="108" fill="#101B20"/><path d="M0 12H108M0 24H108M0 36H108M0 48H108M0 60H108M0 72H108M0 84H108M0 96H108M12 0V108M24 0V108M36 0V108M48 0V108M60 0V108M72 0V108M84 0V108M96 0V108" stroke="#1C3940" stroke-width=".45"/><rect x="6" y="6" width="96" height="96" rx="17" fill="none" stroke="#2C6B62" stroke-width="1.2"/><circle cx="13" cy="13" r="1.5" fill="#61E6B2"/><circle cx="19" cy="13" r="1.5" fill="#61E6B2" opacity=".6"/>"""),
 "line": ("#34383A", """<rect width="108" height="108" fill="#F8F7F2"/><rect x="7" y="7" width="94" height="94" rx="21" fill="#FFFDF8" stroke="#D7D5CD" stroke-width="1"/><path d="M16 23Q54 13 92 23M16 86Q54 96 92 86" fill="none" stroke="#E6E2D8" stroke-width="1"/>"""),
 "plush": ("#FFF0E5", """<rect width="108" height="108" fill="#C98D83"/><rect x="4" y="4" width="100" height="100" rx="24" fill="#E7B4A7"/><path d="M9 17l4 -3m3 8l4 -3m68 63l4 -3m-3 10l4 -3M16 92l4 -3m67 -69l4 -3" stroke="#F8D8C9" stroke-width="2" stroke-linecap="round"/><rect x="10" y="10" width="88" height="88" rx="20" fill="none" stroke="#F5D0C2" stroke-width="1.5" opacity=".8"/>"""),
 "sky": ("#F8FFFF", """<rect width="108" height="108" fill="#80C8E8"/><path d="M0 78Q26 68 54 78T108 78V108H0Z" fill="#A8DDF0"/><g fill="#EAF8FF" opacity=".95"><ellipse cx="21" cy="24" rx="13" ry="6"/><ellipse cx="31" cy="21" rx="10" ry="8"/><ellipse cx="41" cy="25" rx="12" ry="5"/><ellipse cx="77" cy="83" rx="12" ry="5"/><ellipse cx="86" cy="80" rx="9" ry="7"/><ellipse cx="95" cy="84" rx="10" ry="4"/></g><circle cx="86" cy="24" r="7" fill="#FFE8A8"/>"""),
 "space": ("#FFF1D2", """<rect width="108" height="108" fill="#15172F"/><circle cx="54" cy="54" r="48" fill="#20264B"/><circle cx="54" cy="54" r="42" fill="#252D59"/><g fill="#D9D9FF"><circle cx="17" cy="25" r="1"/><circle cx="88" cy="19" r="1.2"/><circle cx="91" cy="73" r=".9"/><circle cx="23" cy="83" r="1.1"/><circle cx="75" cy="94" r=".8"/><circle cx="11" cy="60" r=".7"/></g><path d="M16 45L18 40L20 45L25 47L20 49L18 54L16 49L11 47Z" fill="#8EA9FF"/><path d="M87 42L89 38L91 42L95 44L91 46L89 50L87 46L83 44Z" fill="#8EA9FF"/>"""),
 "graffiti": ("#FFF9E9", """<rect width="108" height="108" fill="#F5D94E"/><path d="M-5 23L28 0L42 8L12 39ZM70 108L108 70V91L91 108Z" fill="#F16A5B"/><path d="M0 76L24 58L36 69L12 91Z" fill="#4B9BCB"/><path d="M76 0H108V26L91 36Z" fill="#6E58B5"/><path d="M6 50Q17 38 28 49T50 49" fill="none" stroke="#232323" stroke-width="2.2" stroke-linecap="round"/><path d="M68 82l5 -8 5 8 8 2 -8 4 -5 8 -5 -8 -8 -4Z" fill="#232323"/>"""),
 "playful": ("#8C5960", """<rect width="108" height="108" fill="#F8DCE7"/><rect x="5" y="5" width="98" height="98" rx="25" fill="#FFF0D9"/><circle cx="18" cy="22" r="7" fill="#A9DCCB"/><circle cx="91" cy="25" r="6" fill="#F6B8A6"/><path d="M13 82Q25 69 37 82T61 82" fill="none" stroke="#A8C8E9" stroke-width="3" stroke-linecap="round"/><path d="M79 75l4 -7 4 7 7 3 -7 3 -4 7 -4 -7 -7 -3Z" fill="#E8B85C"/>"""),
 "8bit": ("#E2FFF1", """<rect width="108" height="108" fill="#1E2940"/><path d="M0 0H18V6H30V0H48V6H60V0H78V6H90V0H108V18H102V30H108V48H102V60H108V78H102V90H108V108H90V102H78V108H60V102H48V108H30V102H18V108H0V90H6V78H0V60H6V48H0V30H6V18H0Z" fill="#2D4561"/><path d="M8 8H100V100H8Z" fill="none" stroke="#6DE0B1" stroke-width="2" stroke-dasharray="5 3"/>"""),
 "sketch": ("#5B4931", """<rect width="108" height="108" fill="#D8C49D"/><rect x="5" y="5" width="98" height="98" rx="7" fill="#F1E4C7"/><path d="M12 18H96M12 90H96" stroke="#C8B58E" stroke-width=".8"/><path d="M13 12V96M95 12V96" stroke="#D5C39D" stroke-width=".6" stroke-dasharray="1 2"/><circle cx="14" cy="14" r="1.5" fill="#B59A6C"/><circle cx="94" cy="94" r="1.5" fill="#B59A6C"/>""")
}

# Read the exact authoritative paths; do not redraw or approximate the logo.
tree = ET.parse(SOURCE)
ns = {"s": "http://www.w3.org/2000/svg"}
paths = [node.attrib["d"] for node in tree.findall(".//s:path", ns)]
if len(paths) != 3:
    raise SystemExit(f"Expected exactly 3 original logo paths, found {len(paths)}")
logo_d = "".join('<path fill="__COLOR__" d="' + d + '"/>' for d in paths)

def logo_svg(color):
    # Use a single finished icon bitmap for both launcher and folder contexts.
    # Artwork occupies 52% of the full canvas; no adaptive foreground layer
    # is allowed to enlarge it independently at runtime.
    logo_width = 108 * 0.66
    scale = logo_width / 865.26
    translate_x = (108 - logo_width) / 2
    # Center the original path geometry (y=0.29..804.62) on the canvas.
    translate_y = 54 - ((0.29 + 804.62) / 2) * scale
    transform = f"translate({translate_x:.5f} {translate_y:.5f}) scale({scale:.8f})"
    return f'<g transform="{transform}">' + logo_d.replace("__COLOR__", color) + '</g>'

def render(svg, size):
    return Image.open(BytesIO(cairosvg.svg2png(bytestring=svg.encode("utf-8"), output_width=size, output_height=size))).convert("RGBA")

def save_png(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, optimize=True)

for name, (logo_color, background) in STYLES.items():
    full_svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">{background}{logo_svg(logo_color)}</svg>'
    bg_svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">{background}</svg>'
    fg_svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">{logo_svg(logo_color)}</svg>'
    full = render(full_svg, 512)
    bg = render(bg_svg, 512)
    # No separately-scaled adaptive foreground: the launcher receives the
    # exact same complete square composition shown in the in-app selector.

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

    # Remove the adaptive-icon XML override. Android launchers can independently
    # scale a foreground layer, and folder previews may apply a different zoom.
    # A density-specific complete PNG is intentional for consistent rendering.
    adaptive_xml = RES / "mipmap-anydpi-v26" / f"ic_launcher_style_{name}.xml"
    if adaptive_xml.exists():
        adaptive_xml.unlink()

print(f"Generated {len(STYLES)} approved icon compositions from the exact 3-path source logo.")
