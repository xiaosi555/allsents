#!/usr/bin/env python3
"""Add Xingtu-style image manipulation with row/column snapping to the article editor."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")
s = EDITOR.read_text(encoding="utf-8")

if "kind:'image-grid'" not in s:
    old = """                            root.addEventListener('touchstart',function(ev){if(!ev.touches||ev.touches.length!==1)return;const t=ev.touches[0],img=ev.target&&ev.target.closest?ev.target.closest('img'):null,cell=img?img.closest('td,th'):null;const block=topLevelAt(ev.target);if(cell&&activeImage&&cell.contains(activeImage)&&cell.parentElement&&cell.parentElement.children.length>1){touchDrag={kind:'group',source:cell,row:cell.parentElement,x:t.clientX,y:t.clientY,started:Date.now(),active:false};}else if(block&&block.classList.contains('selected-block')){touchDrag={kind:multiSelectMode?'blocks':'block',source:block,sources:multiSelectMode?Array.from(root.querySelectorAll('.selected-block')):[block],x:t.clientX,y:t.clientY,started:Date.now(),active:false};}}, {passive:true});
                            root.addEventListener('touchmove',function(ev){if(!touchDrag||!ev.touches||ev.touches.length!==1)return;const t=ev.touches[0],dx=t.clientX-touchDrag.x,dy=t.clientY-touchDrag.y;if(!touchDrag.active){if(Date.now()-touchDrag.started<260||Math.abs(dx)+Math.abs(dy)<10)return;touchDrag.active=true;root.style.userSelect='none';}ev.preventDefault();const hit=document.elementFromPoint(t.clientX,t.clientY);let target=null;if(touchDrag.kind==='group'){const cell=hit&&hit.closest?hit.closest('td,th'):null;if(cell&&cell.parentElement===touchDrag.row&&cell!==touchDrag.source)target=cell;}else{target=topLevelAt(hit);if((touchDrag.sources||[touchDrag.source]).includes(target))target=null;}if(target!== (touchDrop&&touchDrop.el)){clearTouchDrop();if(target){touchDrop={el:target,outline:target.style.outline,shadow:target.style.boxShadow};target.style.outline='2px dashed #159765';target.style.boxShadow='0 0 0 2px rgba(21,151,101,.12)';}}},{passive:false});
                            function finishTouchDrag(){if(!touchDrag)return;const drag=touchDrag;const target=touchDrop&&touchDrop.el;clearTouchDrop();root.style.userSelect='';if(drag.active&&target){if(drag.kind==='group'&&target.parentElement===drag.row){const rect=target.getBoundingClientRect();drag.row.insertBefore(drag.source,touchDrag.lastX<rect.left+rect.width/2?target:target.nextSibling);commitHistory();NativeEditor.changed(root.innerHTML);NativeEditor.imageSelected(activeImage?activeImage.outerHTML:'');}else if((drag.kind==='block'||drag.kind==='blocks')&&target.parentElement===root){const rect=target.getBoundingClientRect(),anchor=touchDrag.lastY<rect.top+rect.height/2?target:target.nextSibling,sources=drag.kind==='blocks'?drag.sources:[drag.source];sources.forEach(node=>root.insertBefore(node,anchor));commitHistory();NativeEditor.changed(root.innerHTML);NativeEditor.blockSelected(sources.map(node=>cleanBlockHtml(node)).join(''));}}touchDrag=null;}"""
    new = """                            root.addEventListener('touchstart',function(ev){
                              if(!ev.touches||ev.touches.length!==1)return;
                              const t=ev.touches[0],img=ev.target&&ev.target.closest?ev.target.closest('img'):null;
                              const cell=img?img.closest('td,th'):null,table=cell?cell.closest('table'):null,block=topLevelAt(ev.target);
                              if(img&&activeImage===img&&cell&&table&&table.querySelectorAll('img').length>1){
                                touchDrag={kind:'image-grid',source:cell,table:table,x:t.clientX,y:t.clientY,started:Date.now(),active:false};
                              }else if(img&&activeImage===img&&block&&block.parentElement===root){
                                touchDrag={kind:'image-row',source:block,x:t.clientX,y:t.clientY,started:Date.now(),active:false};
                              }else if(block&&block.classList.contains('selected-block')){
                                touchDrag={kind:multiSelectMode?'blocks':'block',source:block,sources:multiSelectMode?Array.from(root.querySelectorAll('.selected-block')):[block],x:t.clientX,y:t.clientY,started:Date.now(),active:false};
                              }
                            },{passive:true});
                            root.addEventListener('touchmove',function(ev){
                              if(!touchDrag||!ev.touches||ev.touches.length!==1)return;
                              const t=ev.touches[0],dx=t.clientX-touchDrag.x,dy=t.clientY-touchDrag.y;
                              if(!touchDrag.active){if(Date.now()-touchDrag.started<180||Math.abs(dx)+Math.abs(dy)<8)return;touchDrag.active=true;root.style.userSelect='none';}
                              ev.preventDefault();
                              const hit=document.elementFromPoint(t.clientX,t.clientY);let target=null;
                              if(touchDrag.kind==='image-grid'){
                                const cell=hit&&hit.closest?hit.closest('td,th'):null;
                                if(cell&&cell!==touchDrag.source&&cell.closest('table')===touchDrag.table)target=cell;
                              }else if(touchDrag.kind==='image-row'){
                                target=topLevelAt(hit);
                                if(target===touchDrag.source||!target||target.parentElement!==root)target=null;
                              }else{
                                target=topLevelAt(hit);
                                if((touchDrag.sources||[touchDrag.source]).includes(target))target=null;
                              }
                              if(target!==(touchDrop&&touchDrop.el)){
                                clearTouchDrop();
                                if(target){touchDrop={el:target,outline:target.style.outline,shadow:target.style.boxShadow};target.style.outline='2px dashed #159765';target.style.boxShadow='0 0 0 2px rgba(21,151,101,.12)';}
                              }
                            },{passive:false});
                            function finishTouchDrag(){
                              if(!touchDrag)return;
                              const drag=touchDrag,target=touchDrop&&touchDrop.el;
                              clearTouchDrop();root.style.userSelect='';
                              if(drag.active&&target){
                                if(drag.kind==='image-grid'&&target.closest('table')===drag.table){
                                  const sourceHtml=drag.source.innerHTML,targetHtml=target.innerHTML;
                                  drag.source.innerHTML=targetHtml;target.innerHTML=sourceHtml;
                                  activeImage=target.querySelector('img');
                                  root.querySelectorAll('.selected-image').forEach(x=>x.classList.remove('selected-image'));
                                  if(activeImage){activeImage.classList.add('selected-image');NativeEditor.imageSelected(activeImage.outerHTML);}
                                  commitHistory();NativeEditor.changed(root.innerHTML);
                                }else if(drag.kind==='image-row'&&target.parentElement===root){
                                  const rect=target.getBoundingClientRect(),before=touchDrag.lastY<rect.top+rect.height/2;
                                  root.insertBefore(drag.source,before?target:target.nextSibling);
                                  commitHistory();NativeEditor.changed(root.innerHTML);
                                  if(activeImage)NativeEditor.imageSelected(activeImage.outerHTML);
                                }else if((drag.kind==='block'||drag.kind==='blocks')&&target.parentElement===root){
                                  const rect=target.getBoundingClientRect(),anchor=touchDrag.lastY<rect.top+rect.height/2?target:target.nextSibling;
                                  const sources=drag.kind==='blocks'?drag.sources:[drag.source];
                                  sources.forEach(node=>root.insertBefore(node,anchor));
                                  commitHistory();NativeEditor.changed(root.innerHTML);
                                  NativeEditor.blockSelected(sources.map(node=>cleanBlockHtml(node)).join(''));
                                }
                              }
                              touchDrag=null;
                            }"""
    if old not in s:
        raise SystemExit("Segmented image drag patch: original touch handler anchor not found")
    s = s.replace(old, new, 1)

hint = '                             Text("图片调整", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 7.dp))'
hint_new = hint + '\n                             Text("长按拖动：单列按行移动，多列按格移动；松手自动吸附", color = Color(0xFF929892), fontSize = 10.sp, modifier = Modifier.padding(top = 2.dp, bottom = 4.dp))'
if "长按拖动：单列按行移动，多列按格移动" not in s:
    if s.count(hint) != 1:
        raise SystemExit("Segmented image drag patch: image panel hint anchor mismatch")
    s = s.replace(hint, hint_new, 1)

checks = {
    "grid-cell drag": "kind:'image-grid'" in s and "cell.closest('table')===touchDrag.table" in s,
    "single-column row drag": "kind:'image-row'" in s and "root.insertBefore(drag.source,before?target:target.nextSibling)" in s,
    "visible interaction hint": "长按拖动：单列按行移动，多列按格移动" in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Segmented image drag patch validation failed: " + ", ".join(failed))

EDITOR.write_text(s, encoding="utf-8")
print("Segmented image movement installed: standalone images snap between rows; multi-column image groups snap between table cells.")
