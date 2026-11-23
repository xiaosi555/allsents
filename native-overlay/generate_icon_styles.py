#!/usr/bin/env python3
"""Render 拾万句 icons from the exact shengyu launcher sprite, preserving the original logo and 66% geometry."""
from pathlib import Path
from io import BytesIO
import xml.etree.ElementTree as ET
import cairosvg
from PIL import Image, ImageOps

ROOT=Path(".")
SOURCE=ROOT/"拾万句_简_淡黄色.svg"
SPRITE=ROOT/"native-overlay/assets/launcher-sprite.svg"
RES=ROOT/"source/ShiWanJu-Android/app/src/main/res"
if not SOURCE.is_file() or not SPRITE.is_file():
    raise SystemExit("Missing original 拾万句 logo or exact reference sprite")
NS="{http://www.w3.org/2000/svg}"
STYLES={
 "original":("original","#FFFFFF","#9DEBFF","fill",0),
 "cowboy":("ceramic","#E8D7B6","#C99B5D","fill",1),
 "code":("graphite","#61FF91","#20D66B","fill",1),
 "line":("minimal","#263B42","#263B42","outline",1),
 "plush":("plush","#FFF0D9","#FFE4EE","fill",1),
 "sky":("ocean","#FFFFFF","#DDF7FF","fill",1),
 "space":("glass","#D8E7FF","#69B8FF","fill",1),
 "graffiti":("flat","#165CC5","#2A83F5","fill",2),
 "playful":("ivory","#2364C7","#FFFFFF","fill",1),
 "8bit":("violet","#F7E8C8","#B8E7D2","pixel",0),
 "sketch":("manuscript","#E7E0BE","#B8D7A3","outline",1),
}
logo_tree=ET.parse(SOURCE)
paths=[n.attrib["d"] for n in logo_tree.findall(".//"+NS+"path")]
if len(paths)!=3: raise SystemExit(f"Expected exactly 3 original logo paths, found {len(paths)}")
sprite_tree=ET.parse(SPRITE)
symbols={n.attrib["id"]:n for n in sprite_tree.findall(NS+"symbol")}
if len(symbols)!=11: raise SystemExit(f"Expected 11 reference symbols, found {len(symbols)}")

def serialize(n): return ET.tostring(n,encoding="unicode")
def background(style,meta):
    symbol_id,fill,stroke,treatment,count=meta
    sym=symbols[symbol_id]
    rect=next((n for n in list(sym) if n.tag==NS+"rect"),None)
    group=next((n for n in list(sym) if n.tag==NS+"g"),None)
    if rect is None or group is None: raise SystemExit("Invalid sprite symbol "+symbol_id)
    children=list(group)
    # Keep the ivory face as a style-specific accent; all other reference logo paths are replaced.
    decor=children[-1:] if style=="playful" else children[:count]
    return serialize(rect)+f'<g transform="{group.attrib.get("transform","")}">{"".join(serialize(n) for n in decor)}</g>'

def logo(meta):
    symbol_id,fill,stroke,treatment,count=meta
    # Approved placement math: fixed 66% logo width; do not change.
    logo_width=108*0.66
    scale=logo_width/865.26
    tx=(108-logo_width)/2
    ty=54-((0.29+804.62)/2)*scale
    transform=f"translate({tx:.5f} {ty:.5f}) scale({scale:.8f})"
    if treatment=="outline":
        body="".join(f'<path fill="none" stroke="{fill}" stroke-width="28" stroke-linejoin="round" stroke-linecap="round" d="{d}"/>' for d in paths)
    else:
        body=(f'<path fill="{fill}" d="{paths[0]}"/>'
              f'<path fill="none" stroke="{stroke}" stroke-width="28" stroke-linejoin="round" stroke-linecap="round" d="{paths[1]}"/>'
              f'<path fill="none" stroke="{stroke}" stroke-width="28" stroke-linejoin="round" stroke-linecap="round" d="{paths[2]}"/>')
    return f'<g transform="{transform}">{body}</g>'

def render(svg,size):
    data=cairosvg.svg2png(bytestring=svg.encode(),output_width=size,output_height=size)
    return Image.open(BytesIO(data)).convert("RGBA")
def save(img,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    img.save(path,optimize=True)

for name,meta in STYLES.items():
    bg=background(name,meta)
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">{bg}{logo(meta)}</svg>'
    full=render(svg,512)
    if meta[3]=="pixel":
        full=full.resize((64,64),Image.Resampling.NEAREST).resize((512,512),Image.Resampling.NEAREST)
    drawable=RES/"drawable-nodpi"
    save(full,drawable/f"icon_style_{name}.png")
    for stale in (drawable/f"icon_style_{name}_background.png",drawable/f"icon_style_{name}_foreground.png"):
        if stale.exists(): stale.unlink()
    for density,size in [("mdpi",48),("hdpi",72),("xhdpi",96),("xxhdpi",144),("xxxhdpi",192)]:
        folder=RES/f"mipmap-{density}"
        save(ImageOps.fit(full,(size,size),method=Image.Resampling.LANCZOS),folder/f"ic_launcher_style_{name}.png")
    adaptive=RES/"mipmap-anydpi-v26"
    adaptive.mkdir(parents=True,exist_ok=True)
    save(Image.new("RGBA",(108,108),(0,0,0,0)),drawable/"launcher_transparent_foreground.png")
    (adaptive/f"ic_launcher_style_{name}.xml").write_text(
        f'<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android"><background android:drawable="@drawable/icon_style_{name}" /><foreground android:drawable="@drawable/launcher_transparent_foreground" /></adaptive-icon>',encoding="utf-8")
    if name=="original":
        for density,size in [("mdpi",48),("hdpi",72),("xhdpi",96),("xxhdpi",144),("xxxhdpi",192)]:
            folder=RES/f"mipmap-{density}"
            legacy=ImageOps.fit(full,(size,size),method=Image.Resampling.LANCZOS)
            save(legacy,folder/"ic_launcher.png"); save(legacy,folder/"ic_launcher_round.png")
        base='<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android"><background android:drawable="@drawable/icon_style_original" /><foreground android:drawable="@drawable/launcher_transparent_foreground" /></adaptive-icon>'
        (adaptive/"ic_launcher.xml").write_text(base,encoding="utf-8")
        (adaptive/"ic_launcher_round.xml").write_text(base,encoding="utf-8")
print("Generated 11 icon styles using exact reference sprite backgrounds/decorations; original logo paths and 66% geometry retained.")
