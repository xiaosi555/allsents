#!/usr/bin/env python3
"""Add row/column snapped image dragging to the Xingtu image editor."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
if not EDITOR.is_file():
    raise SystemExit("Article editor source missing: " + str(EDITOR))
s = EDITOR.read_text(encoding="utf-8")

def find_js_block(source, marker):
    start = source.find(marker)
    if start < 0:
        raise SystemExit("Segmented image patch: missing JS marker: " + marker)
    brace = source.find("{", start + len(marker))
    if brace < 0:
        raise SystemExit("Segmented image patch: missing JS body")
    depth = 0
    quote = None
    escaped = False
    for i in range(brace, len(source)):
        ch = source[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise SystemExit("Segmented image patch: unclosed JS block: " + marker)

def replace_js_block(source, marker, replacement):
    start, end = find_js_block(source, marker)
    return source[:start] + replacement + source[end:]

if "kind:'image-grid'" not in s:
    new_start = """root.addEventListener('touchstart',function(ev){
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
},{passive:true});"""
    new_move = """root.addEventListener('touchmove',function(ev){
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
},{passive:false});"""
    new_finish = """function finishTouchDrag(){
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
    s = replace_js_block(s, "root.addEventListener('touchstart',function(ev)", new_start)
    s = replace_js_block(s, "root.addEventListener('touchmove',function(ev)", new_move)
    s = replace_js_block(s, "function finishTouchDrag()", new_finish)
    # Restore event-listener options removed with the function-body replacement.
    for marker, suffix in [
        ("root.addEventListener('touchstart',function(ev)", ",{passive:true});"),
        ("root.addEventListener('touchmove',function(ev)", ",{passive:false});"),
    ]:
        _, end = find_js_block(s, marker)
        if not s[end:].lstrip().startswith(suffix):
            s = s[:end] + suffix + s[end:]

# Match the two-finger transform gesture used by the independent Xingtu 2.0 canvas.
pinch_anchor = "let touchDrag=null,touchDrop=null;"
pinch_code = """let imagePinch=null;
root.addEventListener('touchstart',function(ev){
  if(!ev.touches||ev.touches.length!==2)return;
  const img=ev.target&&ev.target.closest?ev.target.closest('img'):null;
  if(!img||activeImage!==img)return;
  const a=ev.touches[0],b=ev.touches[1],rect=img.getBoundingClientRect();
  imagePinch={img:img,distance:Math.hypot(b.clientX-a.clientX,b.clientY-a.clientY),width:rect.width,
    angle:Math.atan2(b.clientY-a.clientY,b.clientX-a.clientX)*180/Math.PI,
    rotation:parseFloat(img.dataset.rotation||'0'),maxWidth:img.parentElement.clientWidth||rect.width};
},{passive:true});
root.addEventListener('touchmove',function(ev){
  if(!imagePinch||!ev.touches||ev.touches.length!==2)return;
  const g=imagePinch,a=ev.touches[0],b=ev.touches[1];
  const distance=Math.hypot(b.clientX-a.clientX,b.clientY-a.clientY);
  const angle=Math.atan2(b.clientY-a.clientY,b.clientX-a.clientX)*180/Math.PI;
  const width=Math.max(48,Math.min(g.maxWidth,g.width*distance/Math.max(1,g.distance)));
  const rotation=g.rotation+angle-g.angle;
  g.img.style.width=width+'px';g.img.style.maxWidth='100%';g.img.style.height='auto';
  g.img.style.transformOrigin='center center';g.img.dataset.rotation=String(rotation);
  g.img.style.transform='rotate('+rotation+'deg)';
  ev.preventDefault();if(typeof notifyCanvasPreview==='function')notifyCanvasPreview();
},{passive:false});
function finishImagePinch(){
  if(!imagePinch)return;
  commitHistory();NativeEditor.changed(root.innerHTML);
  if(activeImage)NativeEditor.imageSelected(activeImage.outerHTML);
  imagePinch=null;
}
root.addEventListener('touchend',function(ev){if(imagePinch&&(!ev.touches||ev.touches.length<2))finishImagePinch();},{passive:true});
root.addEventListener('touchcancel',finishImagePinch,{passive:true});
"""
if "let imagePinch=null;" not in s:
    if s.count(pinch_anchor)!=1:
        raise SystemExit("Pinch transform patch: touch state anchor mismatch")
    s=s.replace(pinch_anchor,pinch_anchor+"\n"+pinch_code,1)
hint = 'Text("图片调整", color = Color.Gray, fontSize = 10.sp'
if "长按拖动：单列按行移动，多列按格移动" not in s and hint in s:
    pos = s.find(hint)
    line_start = s.rfind("\n", 0, pos) + 1
    line_end = s.find("\n", pos)
    line = s[line_start:line_end]
    indent = line[:len(line)-len(line.lstrip())]
    s = s[:line_end] + "\n" + indent + 'Text("长按拖动按行/列吸附；双指缩放旋转；松手自动保存", color = Color(0xFF929892), fontSize = 10.sp, modifier = Modifier.padding(top = 2.dp, bottom = 4.dp))' + s[line_end:]

checks = {
    "grid-cell drag": "kind:'image-grid'" in s and "cell.closest('table')===touchDrag.table" in s,
    "single-column row drag": "kind:'image-row'" in s and "root.insertBefore(drag.source,before?target:target.nextSibling)" in s,
    "two-finger image transform": "let imagePinch=null;" in s and "g.img.style.transform='rotate('" in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Segmented image patch validation failed: " + ", ".join(failed))

EDITOR.write_text(s, encoding="utf-8")
print("Segmented image movement installed: single-column images snap by row; multi-column image groups snap by row and column.")
