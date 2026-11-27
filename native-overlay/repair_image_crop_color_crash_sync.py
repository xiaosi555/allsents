#!/usr/bin/env python3
"""Repair selected-image crop/color runtime actions and keep live WebView preview synchronized."""
from pathlib import Path
import re

P = Path(__file__).resolve().parents[1] / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
s = P.read_text(encoding="utf-8")

# Keep all image preview edits in the WebView's live document, and notify the native
# canvas bridge using the same path already used by the working text-style editor.
anchor = "function resetSelectedImageColor(){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.filter='';commitHistory();NativeEditor.changed(root.innerHTML);}"
if anchor not in s:
    raise SystemExit("image color reset anchor missing")
replacement = r"""
                            function selectedImageTarget(){
                              if(activeImage&&root.contains(activeImage)&&activeImage.dataset.editorLocked!=='1')return activeImage;
                              const el=root.querySelector('.selected-image,.selected-image-block img,.selected-block img');
                              if(el&&el.tagName==='IMG'&&el.dataset.editorLocked!=='1'){activeImage=el;return el;}
                              return null;
                            }
                            function syncSelectedImageLive(){
                              try{if(typeof NativeEditor!=='undefined'&&NativeEditor.changed)NativeEditor.changed(root.innerHTML);}catch(e){}
                              try{if(typeof notifyCanvasPreview==='function')notifyCanvasPreview();}catch(e){}
                            }
                            function selectedImageTransform(el){
                              const rot=Number(el.dataset.editorRotation||0);
                              const sx=Number(el.dataset.editorFlipX||1);
                              const sy=Number(el.dataset.editorFlipY||1);
                              el.style.transform='rotate('+rot+'deg) scale('+sx+','+sy+')';
                              el.style.transformOrigin='center center';
                            }
                            function previewSelectedImageFilters(b,c,sat){
                              const el=selectedImageTarget();if(!el)return;
                              el.style.filter='brightness('+Math.max(0,Math.min(300,Number(b)||100))+'%) contrast('+Math.max(0,Math.min(300,Number(c)||100))+'%) saturate('+Math.max(0,Math.min(300,Number(sat)||100))+'%)';
                              syncSelectedImageLive();
                            }
                            function previewSelectedImageAdvanced(b,c,sat,temp,tint,hue,gray,sepia,blur,rotation){
                              const el=selectedImageTarget();if(!el)return;
                              const f=['brightness('+Math.max(0,Math.min(300,Number(b)||100))+'%)','contrast('+Math.max(0,Math.min(300,Number(c)||100))+'%)','saturate('+Math.max(0,Math.min(300,Number(sat)||100))+'%)','hue-rotate('+((Number(hue)||0)+(Number(tint)||0)*.12)+'deg)'];
                              if(Number(gray)>0)f.push('grayscale('+Math.max(0,Math.min(100,Number(gray)))+'%)');
                              if(Number(sepia)>0||Number(temp)!==0)f.push('sepia('+Math.max(0,Math.min(100,Number(sepia)+Math.abs(Number(temp))*.22))+'%)');
                              if(Number(blur)>0)f.push('blur('+Math.max(0,Math.min(12,Number(blur)))+'px)');
                              el.style.filter=f.join(' ');
                              const rot=Number(rotation)||0;
                              el.dataset.editorRotation=String(rot);selectedImageTransform(el);
                              syncSelectedImageLive();
                            }
                            function previewSelectedImageTransform(deg){
                              const el=selectedImageTarget();if(!el)return;
                              el.dataset.editorRotation=String(Number(deg)||0);selectedImageTransform(el);syncSelectedImageLive();
                            }
                            function rotateSelectedImage(){
                              const el=selectedImageTarget();if(!el)return;
                              el.dataset.editorRotation=String((Number(el.dataset.editorRotation)||0)+90);
                              selectedImageTransform(el);syncSelectedImageLive();
                            }
                            function flipSelectedImage(axis){
                              const el=selectedImageTarget();if(!el)return;
                              if(axis==='vertical')el.dataset.editorFlipY=String(-(Number(el.dataset.editorFlipY)||1));
                              else el.dataset.editorFlipX=String(-(Number(el.dataset.editorFlipX)||1));
                              selectedImageTransform(el);syncSelectedImageLive();
                            }
                            function cropSelectedImageCustom(w,h){
                              const el=selectedImageTarget();if(!el)return;
                              w=Math.max(1,Number(w)||1);h=Math.max(1,Number(h)||1);
                              el.style.width='100%';el.style.height='auto';el.style.aspectRatio=w+'/'+h;
                              el.style.objectFit='cover';el.style.maxWidth='100%';el.style.objectPosition=el.style.objectPosition||'50% 50%';
                              el.dataset.editorCropRatio=w+':'+h;syncSelectedImageLive();
                            }
                            function resetSelectedImageCrop(){
                              const el=selectedImageTarget();if(!el)return;
                              el.style.width='';el.style.height='';el.style.aspectRatio='';el.style.objectFit='';el.style.objectPosition='';
                              delete el.dataset.editorCropRatio;syncSelectedImageLive();
                            }
                            function previewSelectedImagePosition(x,y){
                              const el=selectedImageTarget();if(!el)return;
                              el.style.objectPosition=Math.max(0,Math.min(100,Number(x)||50))+'% '+Math.max(0,Math.min(100,Number(y)||50))+'%';
                              syncSelectedImageLive();
                            }
                            function resetSelectedImageColor(){
                              const el=selectedImageTarget();if(!el)return;
                              el.style.filter='';syncSelectedImageLive();
                            }
                            function commitSelectedImageStyle(){
                              const el=selectedImageTarget();if(!el)return;
                              try{if(typeof commitHistory==='function')commitHistory();}catch(e){}
                              syncSelectedImageLive();
                            }
"""
s = s.replace(anchor, replacement.strip(), 1)

# The old crop helper committed on every ratio selection and changed the image's
# intrinsic height in a way that could distort the canvas. Ensure the panel's reset
# and apply actions are always backed by the safe functions above.
for fn in ("resetSelectedImageCrop", "flipSelectedImage", "rotateSelectedImage", "commitSelectedImageStyle", "syncSelectedImageLive"):
    if "function " + fn + "(" not in s:
        raise SystemExit("missing repaired image function: " + fn)

P.write_text(s, encoding="utf-8")
print("Image crop/color runtime actions repaired; preview updates now notify the native canvas.")
