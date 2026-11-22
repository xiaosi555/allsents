#!/usr/bin/env python3
"""Generate eleven launcher icon variants from the authoritative repository SVG.
The SVG paths are never redrawn: only background material, color and surface treatment vary.
"""
from pathlib import Path
import math, random
import cairosvg
from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = Path(".")
SVG = ROOT / "拾万句_简_淡黄色.svg"
OUT = ROOT / "source/ShiWanJu-Android/app/src/main/res"
if not SVG.is_file():
    raise SystemExit("Missing authoritative logo SVG")
S = 512
raw = cairosvg.svg2png(url=str(SVG), output_width=430, output_height=400)
from io import BytesIO
mark = Image.open(BytesIO(raw)).convert("RGBA")
mark_canvas = Image.new("RGBA", (S, S), (0,0,0,0))
mark_canvas.alpha_composite(mark, ((S-mark.width)//2, (S-mark.height)//2))
alpha = mark_canvas.getchannel("A")
# Crop only transparent SVG margins, then fit the complete original path to the
# Android 66/108 safe-area ratio. This keeps the icon visually consistent.
bbox = alpha.getbbox()
if not bbox:
    raise SystemExit("Original SVG contains no visible artwork")
mark_crop = mark_canvas.crop(bbox)

names = ["original","cowboy","code","line","plush","sky","space","graffiti","playful","8bit","sketch"]
random.seed(23)

def gradient(top, bottom):
    im=Image.new("RGB",(S,S)); p=im.load()
    for y in range(S):
        t=y/(S-1)
        c=tuple(round(top[i]*(1-t)+bottom[i]*t) for i in range(3))
        for x in range(S): p[x,y]=c
    return im.convert("RGBA")

def texture(kind):
    palettes={
      "original":((86,210,116),(86,210,116)),
      "cowboy":((19,55,91),(39,91,132)),
      "code":((2,18,19),(0,48,36)),
      "line":((250,246,230),(238,229,204)),
      "plush":((246,139,177),(222,91,143)),
      "sky":((58,168,245),(126,211,255)),
      "space":((5,10,43),(32,24,89)),
      "graffiti":((255,142,39),(24,181,180)),
      "playful":((255,220,87),(255,125,174)),
      "8bit":((10,28,75),(40,39,112)),
      "sketch":((245,238,217),(228,217,190))
    }
    im=gradient(*palettes[kind]); d=ImageDraw.Draw(im,"RGBA")
    if kind=="cowboy":
      for x in range(-S,S,9): d.line((x,0,x+S,S),fill=(130,190,220,28),width=2)
      for y in range(0,S,12): d.line((0,y,S,y),fill=(5,20,40,24),width=1)
      d.rounded_rectangle((15,15,497,497),radius=28,outline=(210,160,100,210),width=7)
    elif kind=="code":
      for y in range(20,S,28):
        d.rounded_rectangle((18,y,random.randint(100,470),y+5),radius=2,fill=(20,255,125,55))
      for x in range(28,S,48): d.line((x,0,x,S),fill=(20,255,125,18),width=1)
    elif kind in ("line","sketch"):
      for i in range(1000):
        x=random.randrange(S); y=random.randrange(S)
        d.point((x,y),fill=(90,70,45,random.randrange(8,28)))
      if kind=="sketch":
        for i in range(80):
          x=random.randrange(S); y=random.randrange(S)
          d.line((x,y,x+random.randrange(15,70),y+random.randrange(-10,10)),fill=(90,75,55,25),width=1)
    elif kind=="plush":
      for i in range(14000):
        x=random.randrange(S); y=random.randrange(S)
        d.ellipse((x,y,x+2,y+2),fill=(255,255,255,random.randrange(8,36)))
    elif kind=="sky":
      for x,y,r in [(60,80,48),(430,140,62),(110,440,55),(400,430,45)]:
        for dx,dy,rr in [(-r//2,0,r//2),(0,-r//3,r),(r//2,0,r//2)]:
          d.ellipse((x+dx-rr,y+dy-rr/2,x+dx+rr,y+dy+rr/2),fill=(255,255,255,105))
    elif kind=="space":
      for i in range(650):
        x=random.randrange(S); y=random.randrange(S); r=random.choice([1,1,2,3])
        d.ellipse((x-r,y-r,x+r,y+r),fill=(210,210,255,random.randrange(90,240)))
    elif kind=="graffiti":
      cols=[(255,50,120,95),(255,210,20,100),(0,220,200,95),(40,80,255,95)]
      for i in range(80):
        x=random.randrange(S); y=random.randrange(S); r=random.randrange(12,65)
        d.ellipse((x-r,y-r,x+r,y+r),fill=random.choice(cols))
    elif kind=="playful":
      for box,col in [((-80,-40,210,180),(255,239,91,255)),((320,-40,590,190),(103,198,255,255)),((-80,350,200,590),(100,205,255,255)),((320,340,600,590),(255,111,174,255))]:
        d.ellipse(box,fill=col)
    elif kind=="8bit":
      for y in range(0,S,24):
        for x in range(0,S,24):
          if random.random()<.48:
            col=random.choice([(24,190,230,100),(150,60,230,100),(20,100,190,110)])
            d.rectangle((x,y,x+22,y+22),fill=col)
    return im

def recolor(mask, color):
    layer=Image.new("RGBA",(S,S),color)
    layer.putalpha(mask)
    return layer

for name in names:
    bg=texture(name)
    if name=="original": color=(255,241,210,255)
    elif name in ("code","space"): color=(120,255,210,255) if name=="code" else (220,210,255,255)
    elif name in ("line","sketch"): color=(63,57,49,255)
    elif name=="plush": color=(255,250,245,255)
    else: color=(255,248,232,255)
    safe_size = round(S * 66 / 108)
    fitted = ImageOps.contain(mark_crop, (safe_size, safe_size), method=Image.Resampling.LANCZOS)
    fitted_mask = fitted.getchannel("A")
    if name=="8bit":
        pix = fitted_mask.resize((max(1,safe_size//7), max(1,safe_size//7)),Image.Resampling.LANCZOS)
        fitted_mask = pix.resize((safe_size,safe_size),Image.Resampling.NEAREST)
    mask = Image.new("L",(S,S),0)
    mask.paste(fitted_mask,((S-fitted.width)//2,(S-fitted.height)//2))
    logo=recolor(mask,color)
    if name=="plush":
        shadow=Image.new("RGBA",(S,S),(0,0,0,0)); shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(7)))
        bg.alpha_composite(shadow,(0,4))
    bg.alpha_composite(logo)
    # Rounded-square launcher previews; actual launcher adaptive resources retain transparent safe margins.
    bg=bg.convert("RGBA")
    d=ImageDraw.Draw(bg)
    d.rounded_rectangle((2,2,S-3,S-3),radius=86,outline=(255,255,255,30),width=2)
    folder=OUT/"drawable-nodpi"; folder.mkdir(parents=True,exist_ok=True)
    bg.save(folder/f"icon_style_{name}.png",optimize=True)
    # 108x108 transparent foreground for adaptive launcher icon.
    fg=Image.new("RGBA",(108,108),(0,0,0,0))
    fgmark=Image.new("RGBA",fitted_mask.size,color)
    fgmark.putalpha(fitted_mask)
    iconmark=ImageOps.contain(fgmark,(66,66),method=Image.Resampling.LANCZOS)
    fg.alpha_composite(iconmark,((108-iconmark.width)//2,(108-iconmark.height)//2))
    fg.save(folder/f"launcher_{name}_foreground.png",optimize=True)
print("Generated 11 icon styles from the original SVG silhouette.")
