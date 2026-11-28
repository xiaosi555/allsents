#!/usr/bin/env python3
"""Restore live Text2 canvas preview and replace font-glyph placeholders with vector icons."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "editor_live_preview_icons_patch_error.txt"
if not EDITOR.is_file():
    raise SystemExit(f"Article editor source missing: {EDITOR}")
s = EDITOR.read_text(encoding="utf-8")

def once(old: str, new: str, label: str):
    global s
    if new in s:
        return
    count = s.count(old)
    if count != 1:
        ERROR.write_text(f"{label}: expected 1 anchor, found {count}\\n", encoding="utf-8")
        raise SystemExit(f"Live preview/icon patch anchor mismatch [{label}]: {count}")
    s = s.replace(old, new, 1)
    print("Live preview/icon patch:", label)

# Text2 can be opened after a single-tap object selection. That selection deliberately
# clears the browser Range to avoid opening the keyboard. Resolve the selected object
# explicitly instead of relying only on a restored Range or a selected-block class.
import re
text2_target_pattern = re.compile(
    r"(?m)^([ \t]*)if\(!target\|\|!root\.contains\(target\)\)target=root\.querySelector\('\.text2-selection-preview'\);\n"
    r"[ \t]*if\(!target\|\|!root\.contains\(target\)\)target=root\.querySelector\('\.selected-block'\);\n"
    r"[ \t]*if\(!target\|\|!root\.contains\(target\)\)target=typeof selectedParagraph==='function'\?selectedParagraph\(\):null;"
)
text2_target_matches = list(text2_target_pattern.finditer(s))
if len(text2_target_matches) != 2:
    raise SystemExit(f"Text2 target fallback expected 2 anchors, found {len(text2_target_matches)}")
def replace_text2_target(match):
    indent = match.group(1)
    return (
        indent + "if(!target||!root.contains(target))target=root.querySelector('.text2-selection-preview');\n" +
        indent + "if(!target||!root.contains(target))target=(activeTextBlock&&root.contains(activeTextBlock))?activeTextBlock:root.querySelector('.selected-text-block');\n" +
        indent + "if(!target||!root.contains(target))target=root.querySelector('.selected-block');\n" +
        indent + "if(!target||!root.contains(target))target=typeof selectedParagraph==='function'?selectedParagraph():null;"
    )
s = text2_target_pattern.sub(replace_text2_target, s)
print("Updated both Text2 style and command target fallbacks.")

# The first-tap selection must be previewable even when no live Range remains.
once(
"""if(!r||r.collapsed||!root.contains(r.commonAncestorContainer)){if(activeTextBlock&&root.contains(activeTextBlock)){root.querySelectorAll('.text2-selection-preview').forEach(el=>el.classList.remove('text2-selection-preview'));activeTextBlock.classList.add('text2-selection-preview');savedRange=null;if(s)s.removeAllRanges();notifyCanvasPreview();return true;}return !!root.querySelector('.text2-selection-preview');}""",
"""if(!r||r.collapsed||!root.contains(r.commonAncestorContainer)){const block=(activeTextBlock&&root.contains(activeTextBlock))?activeTextBlock:root.querySelector('.selected-text-block');if(block){root.querySelectorAll('.text2-selection-preview').forEach(el=>el.classList.remove('text2-selection-preview'));block.classList.add('text2-selection-preview');savedRange=null;if(s)s.removeAllRanges();notifyCanvasPreview();return true;}return !!root.querySelector('.text2-selection-preview');}""",
"Text2 preview on tap-selected paragraph"
)

icon_composable = r'''
@Composable
fun ShiWanJuLineIcon(label: String, tint: Color, modifier: Modifier = Modifier) {
    Canvas(modifier = modifier.size(24.dp)) {
        val w = size.width
        val h = size.height
        val sw = (w + h) / 48f * 1.5f
        val c = tint
        val cx = w / 2f
        val cy = h / 2f
        fun line(x1: Float, y1: Float, x2: Float, y2: Float) {
            drawLine(c, Offset(x1, y1), Offset(x2, y2), strokeWidth = sw, cap = androidx.compose.ui.graphics.StrokeCap.Round)
        }
        fun outlineRect(x: Float, y: Float, rw: Float, rh: Float, radius: Float = sw) {
            drawRoundRect(c, Offset(x, y), Size(rw, rh), androidx.compose.ui.geometry.CornerRadius(radius, radius), style = Stroke(sw))
        }
        fun circle(x: Float, y: Float, radius: Float, filled: Boolean = false) {
            drawCircle(c, radius, Offset(x, y), style = Stroke(sw))
        }
        fun poly(points: List<Offset>, close: Boolean = false) {
            val p = androidx.compose.ui.graphics.Path()
            points.forEachIndexed { index, point -> if (index == 0) p.moveTo(point.x, point.y) else p.lineTo(point.x, point.y) }
            if (close) p.close()
            drawPath(p, c, style = Stroke(sw, cap = androidx.compose.ui.graphics.StrokeCap.Round, join = androidx.compose.ui.graphics.StrokeJoin.Round))
        }
        val k = label.lowercase()
        when {
            k.contains("撤销") || k.contains("undo") -> { poly(listOf(Offset(w*.42f,h*.24f),Offset(w*.18f,h*.24f),Offset(w*.18f,h*.48f))); poly(listOf(Offset(w*.18f,h*.48f),Offset(w*.38f,h*.29f),Offset(w*.55f,h*.25f),Offset(w*.75f,h*.34f),Offset(w*.82f,h*.52f),Offset(w*.76f,h*.72f))) }
            k.contains("重做") || k.contains("redo") -> { poly(listOf(Offset(w*.58f,h*.24f),Offset(w*.82f,h*.24f),Offset(w*.82f,h*.48f))); poly(listOf(Offset(w*.82f,h*.48f),Offset(w*.62f,h*.29f),Offset(w*.45f,h*.25f),Offset(w*.25f,h*.34f),Offset(w*.18f,h*.52f),Offset(w*.24f,h*.72f))) }
            k.contains("透明度") || k.contains("opacity") -> { circle(cx,cy,w*.34f); drawArc(c, -90f, 180f, false, Offset(cx-w*.34f,cy-w*.34f), Size(w*.68f,w*.68f), style = Stroke(sw)); line(cx,cy-w*.34f,cx,cy+w*.34f) }
            k.contains("裁剪") || k.contains("裁切") || k.contains("crop") -> { line(w*.12f,h*.36f,w*.12f,h*.12f); line(w*.12f,h*.12f,w*.36f,h*.12f); line(w*.64f,h*.12f,w*.88f,h*.12f); line(w*.88f,h*.12f,w*.88f,h*.36f); line(w*.12f,h*.64f,w*.12f,h*.88f); line(w*.12f,h*.88f,w*.36f,h*.88f); line(w*.64f,h*.88f,w*.88f,h*.88f); line(w*.88f,h*.64f,w*.88f,h*.88f) }
            k.contains("图片") || k.contains("加图") || k.contains("相册") || k.contains("封面") || k.contains("image") -> { outlineRect(w*.12f,h*.16f,w*.76f,h*.68f,sw*1.4f); circle(w*.68f,h*.35f,w*.07f,true); poly(listOf(Offset(w*.18f,h*.72f),Offset(w*.40f,h*.49f),Offset(w*.54f,h*.62f),Offset(w*.64f,h*.52f),Offset(w*.82f,h*.73f))) }
            k.contains("加粗") || k.contains("粗体") || k.contains("bold") -> { line(w*.18f,h*.25f,w*.82f,h*.25f); line(cx,h*.25f,cx,h*.78f); line(w*.34f,h*.78f,w*.66f,h*.78f); line(w*.30f,h*.45f,w*.70f,h*.45f); line(w*.24f,h*.54f,w*.76f,h*.54f) }
            k.contains("斜体") || k.contains("italic") -> { poly(listOf(Offset(w*.58f,h*.18f),Offset(w*.42f,h*.82f))); line(w*.32f,h*.18f,w*.78f,h*.18f); line(w*.22f,h*.82f,w*.68f,h*.82f) }
            k.contains("下划线") || k.contains("underline") -> { line(w*.18f,h*.22f,w*.82f,h*.22f); line(cx,h*.22f,cx,h*.66f); line(w*.18f,h*.82f,w*.82f,h*.82f) }
            k.contains("删除线") || k.contains("strike") -> { line(w*.18f,h*.22f,w*.82f,h*.22f); line(cx,h*.22f,cx,h*.78f); line(w*.18f,h*.50f,w*.82f,h*.50f) }
            k.contains("文字") || k.contains("加字") || k.contains("字体") || k.contains("字号") || k.contains("标题") || k.contains("font") -> { line(w*.18f,h*.25f,w*.82f,h*.25f); line(cx,h*.25f,cx,h*.78f); line(w*.34f,h*.78f,w*.66f,h*.78f); line(w*.35f,h*.45f,w*.65f,h*.45f) }
            k.contains("颜色") || k.contains("调色") || k.contains("高亮") || k.contains("color") -> { poly(listOf(Offset(w*.50f,h*.13f),Offset(w*.78f,h*.29f),Offset(w*.85f,h*.56f),Offset(w*.67f,h*.82f),Offset(w*.34f,h*.86f),Offset(w*.14f,h*.63f),Offset(w*.18f,h*.36f),Offset(w*.50f,h*.13f)),true); circle(w*.35f,h*.43f,w*.045f,true); circle(w*.55f,h*.34f,w*.045f,true); circle(w*.69f,h*.51f,w*.045f,true) }
            k.contains("对齐") || k.contains("居中") || k.contains("align") -> { line(w*.18f,h*.23f,w*.82f,h*.23f); line(w*.18f,h*.42f,w*.68f,h*.42f); line(w*.32f,h*.61f,w*.82f,h*.61f); line(w*.18f,h*.80f,w*.68f,h*.80f) }
            k.contains("边框") || k.contains("border") -> outlineRect(w*.16f,h*.16f,w*.68f,h*.68f,sw*.5f)
            k.contains("圆角") || k.contains("radius") -> outlineRect(w*.14f,h*.14f,w*.72f,h*.72f,w*.22f)
            k.contains("阴影") || k.contains("shadow") -> { outlineRect(w*.12f,h*.12f,w*.68f,h*.68f,w*.12f); outlineRect(w*.23f,h*.23f,w*.68f,h*.68f,w*.12f) }
            k.contains("翻转") || k.contains("flip") -> { line(cx,h*.14f,cx,h*.86f); poly(listOf(Offset(w*.38f,h*.28f),Offset(w*.18f,h*.50f),Offset(w*.38f,h*.72f))); poly(listOf(Offset(w*.62f,h*.28f),Offset(w*.82f,h*.50f),Offset(w*.62f,h*.72f))) }
            k.contains("替换") || k.contains("replace") -> { poly(listOf(Offset(w*.15f,h*.35f),Offset(w*.82f,h*.35f),Offset(w*.66f,h*.20f))); poly(listOf(Offset(w*.85f,h*.65f),Offset(w*.18f,h*.65f),Offset(w*.34f,h*.80f))) }
            k.contains("复制样式") || k.contains("copy-style") || k.contains("格式刷") -> { line(w*.25f,h*.76f,w*.72f,h*.29f); outlineRect(w*.53f,h*.12f,w*.25f,h*.25f,w*.04f); line(w*.18f,h*.83f,w*.34f,h*.67f) }
            k.contains("复制") || k.contains("副本") || k.contains("duplicate") || k.contains("copy") -> { outlineRect(w*.28f,h*.12f,w*.55f,h*.62f); outlineRect(w*.14f,h*.28f,w*.55f,h*.62f) }
            k.contains("粘贴") || k.contains("paste") -> { outlineRect(w*.20f,h*.20f,w*.60f,h*.68f); outlineRect(w*.36f,h*.11f,w*.28f,h*.20f,w*.05f); line(w*.32f,h*.48f,w*.68f,h*.48f); line(w*.32f,h*.64f,w*.62f,h*.64f) }
            k.contains("多选") || k.contains("multi") -> { for (row in 0..1) for (col in 0..1) outlineRect(w*(.16f+col*.36f),h*(.16f+row*.36f),w*.22f,h*.22f,sw*.6f) }
            k.contains("锁定") || k.contains("lock") -> { outlineRect(w*.18f,h*.42f,w*.64f,h*.44f,w*.07f); val p=androidx.compose.ui.graphics.Path().apply{moveTo(w*.30f,h*.43f);lineTo(w*.30f,h*.30f);quadraticTo(w*.30f,h*.10f,w*.50f,h*.10f);quadraticTo(w*.70f,h*.10f,w*.70f,h*.30f);lineTo(w*.70f,h*.43f)};drawPath(p,c,style=Stroke(sw)) }
            k.contains("收藏") || k.contains("喜欢") || k.contains("模板") || k.contains("save-template") -> { val pts=(0..10).map{idx->val a=(-90+idx*36)*Math.PI/180.0;val r=if(idx%2==0)w*.36f else w*.16f;Offset(cx+Math.cos(a).toFloat()*r,cy+Math.sin(a).toFloat()*r)};poly(pts,true) }
            k.contains("顺序") || k.contains("order") -> { line(cx,h*.18f,cx,h*.82f); poly(listOf(Offset(w*.32f,h*.34f),Offset(cx,h*.18f),Offset(w*.68f,h*.34f))); poly(listOf(Offset(w*.32f,h*.66f),Offset(cx,h*.82f),Offset(w*.68f,h*.66f))) }
            k.contains("插入") || k.contains("添加") || k.contains("新建") || k.contains("加图") || k.contains("加字") -> { line(cx,h*.18f,cx,h*.82f); line(w*.18f,cy,w*.82f,cy) }
            k.contains("放大") || k.contains("zoom-in") -> { circle(cx,cy,w*.30f); line(cx-w*.16f,cy,cx+w*.16f,cy); line(cx,cy-w*.16f,cx,cy+w*.16f); line(w*.70f,h*.70f,w*.88f,h*.88f) }
            k.contains("缩小") || k.contains("zoom-out") -> { circle(cx,cy,w*.30f); line(cx-w*.16f,cy,cx+w*.16f,cy); line(w*.70f,h*.70f,w*.88f,h*.88f) }
            k.contains("拖动") || k.contains("移动") || k.contains("move") -> { line(cx,h*.12f,cx,h*.88f); line(w*.12f,cy,w*.88f,cy); poly(listOf(Offset(w*.38f,h*.28f),Offset(cx,h*.12f),Offset(w*.62f,h*.28f))); poly(listOf(Offset(w*.38f,h*.72f),Offset(cx,h*.88f),Offset(w*.62f,h*.72f))); poly(listOf(Offset(w*.28f,h*.38f),Offset(w*.12f,cy),Offset(w*.28f,h*.62f))); poly(listOf(Offset(w*.72f,h*.38f),Offset(w*.88f,cy),Offset(w*.72f,h*.62f))) }
            k.contains("上移") || k.contains("move-up") -> { line(cx,h*.82f,cx,h*.20f); poly(listOf(Offset(w*.28f,h*.42f),Offset(cx,h*.20f),Offset(w*.72f,h*.42f))) }
            k.contains("下移") || k.contains("move-down") -> { line(cx,h*.18f,cx,h*.80f); poly(listOf(Offset(w*.28f,h*.58f),Offset(cx,h*.80f),Offset(w*.72f,h*.58f))) }
            k.contains("说明") || k.contains("信息") || k.contains("info") -> { circle(cx,cy,w*.37f); circle(cx,h*.31f,sw*.75f,true); line(cx,h*.45f,cx,h*.72f) }
            k.contains("尺寸") || k.contains("size") -> { outlineRect(w*.16f,h*.16f,w*.68f,h*.68f,sw*.6f); line(w*.16f,h*.08f,w*.16f,h*.25f); line(w*.08f,h*.16f,w*.25f,h*.16f); line(w*.75f,h*.84f,w*.92f,h*.84f); line(w*.84f,h*.75f,w*.84f,h*.92f) }
            k.contains("样式") || k.contains("外观") || k.contains("style") -> { circle(cx,cy,w*.30f); circle(w*.50f,h*.18f,sw*.8f,true); circle(w*.78f,h*.50f,sw*.8f,true); circle(w*.50f,h*.82f,sw*.8f,true); circle(w*.22f,h*.50f,sw*.8f,true) }
            k.contains("搜索") || k.contains("查找") || k.contains("search") -> { circle(w*.43f,h*.42f,w*.25f); line(w*.61f,h*.61f,w*.84f,h*.84f) }
            k.contains("表格") || k.contains("table") -> { outlineRect(w*.12f,h*.16f,w*.76f,h*.68f,sw*.5f); line(w*.12f,h*.39f,w*.88f,h*.39f); line(w*.12f,h*.62f,w*.88f,h*.62f); line(w*.38f,h*.16f,w*.38f,h*.84f); line(w*.64f,h*.16f,w*.64f,h*.84f) }
            k.contains("列表") || k.contains("编号") || k.contains("list") -> { for(i in 0..2){circle(w*.22f,h*(.28f+i*.23f),sw*.8f,true);line(w*.38f,h*(.28f+i*.23f),w*.82f,h*(.28f+i*.23f))} }
            k.contains("引用") || k.contains("quote") -> { line(w*.20f,h*.30f,w*.42f,h*.30f); line(w*.20f,h*.30f,w*.20f,h*.54f); line(w*.20f,h*.54f,w*.38f,h*.54f); line(w*.56f,h*.30f,w*.78f,h*.30f); line(w*.56f,h*.30f,w*.56f,h*.54f); line(w*.56f,h*.54f,w*.74f,h*.54f) }
            k.contains("分割") || k.contains("分栏") || k.contains("布局") || k.contains("layout") -> { line(w*.16f,h*.20f,w*.84f,h*.20f); line(w*.16f,h*.80f,w*.84f,h*.80f); line(cx,h*.20f,cx,h*.80f); line(w*.16f,h*.50f,w*.84f,h*.50f) }
            k.contains("图层") || k.contains("层级") || k.contains("layer") -> { poly(listOf(Offset(cx,h*.14f),Offset(w*.86f,h*.36f),Offset(cx,h*.58f),Offset(w*.14f,h*.36f),Offset(cx,h*.14f))); poly(listOf(Offset(w*.14f,h*.54f),Offset(cx,h*.76f),Offset(w*.86f,h*.54f))); poly(listOf(Offset(w*.14f,h*.70f),Offset(cx,h*.90f),Offset(w*.86f,h*.70f))) }
            k.contains("导入") || k.contains("import") -> { line(cx,h*.16f,cx,h*.65f); poly(listOf(Offset(w*.30f,h*.48f),Offset(cx,h*.66f),Offset(w*.70f,h*.48f))); line(w*.18f,h*.82f,w*.82f,h*.82f) }
            k.contains("导出") || k.contains("export") -> { line(cx,h*.66f,cx,h*.16f); poly(listOf(Offset(w*.30f,h*.34f),Offset(cx,h*.14f),Offset(w*.70f,h*.34f))); line(w*.18f,h*.82f,w*.82f,h*.82f) }
            k.contains("设置") || k.contains("属性") || k.contains("settings") -> { circle(cx,cy,w*.30f); circle(cx,cy,w*.10f); for(i in 0..7){val a=i*Math.PI/4;line(cx+Math.cos(a).toFloat()*w*.34f,cy+Math.sin(a).toFloat()*w*.34f,cx+Math.cos(a).toFloat()*w*.43f,cy+Math.sin(a).toFloat()*w*.43f)} }
            k.contains("完成") || k.contains("确定") || k.contains("check") -> { poly(listOf(Offset(w*.16f,h*.52f),Offset(w*.40f,h*.75f),Offset(w*.84f,h*.24f))) }
            k.contains("预览") || k.contains("阅读") || k.contains("eye") -> { val p=androidx.compose.ui.graphics.Path().apply{moveTo(w*.10f,cy);quadraticTo(cx,h*.12f,w*.90f,cy);quadraticTo(cx,h*.88f,w*.10f,cy)};drawPath(p,c,style=Stroke(sw));circle(cx,cy,w*.13f) }
            k.contains("卡片") || k.contains("组件") || k.contains("card") || k.contains("component") -> { outlineRect(w*.13f,h*.16f,w*.74f,h*.68f,w*.08f); line(w*.13f,h*.36f,w*.87f,h*.36f); line(w*.25f,h*.55f,w*.72f,h*.55f); line(w*.25f,h*.69f,w*.60f,h*.69f) }
            k.contains("旋转") || k.contains("rotate") -> { val p=androidx.compose.ui.graphics.Path().apply{moveTo(w*.78f,h*.36f);quadraticTo(w*.82f,h*.12f,w*.54f,h*.13f);quadraticTo(w*.20f,h*.12f,w*.18f,h*.48f);quadraticTo(w*.18f,h*.82f,w*.55f,h*.84f);quadraticTo(w*.82f,h*.84f,w*.84f,h*.60f)};drawPath(p,c,style=Stroke(sw));poly(listOf(Offset(w*.65f,h*.20f),Offset(w*.80f,h*.36f),Offset(w*.61f,h*.43f))) }
            k.contains("删除") || k.contains("delete") -> { outlineRect(w*.22f,h*.30f,w*.56f,h*.56f,w*.04f); line(w*.16f,h*.25f,w*.84f,h*.25f); line(w*.38f,h*.16f,w*.62f,h*.16f); line(w*.40f,h*.42f,w*.40f,h*.72f); line(w*.60f,h*.42f,w*.60f,h*.72f) }
            k.contains("链接") || k.contains("link") -> { val p=androidx.compose.ui.graphics.Path().apply{moveTo(w*.43f,h*.64f);lineTo(w*.31f,h*.76f);quadraticTo(w*.12f,h*.80f,w*.12f,h*.62f);quadraticTo(w*.12f,h*.48f,w*.25f,h*.36f);lineTo(w*.38f,h*.24f);quadraticTo(w*.55f,h*.12f,w*.68f,h*.28f);lineTo(w*.72f,h*.32f);moveTo(w*.57f,h*.36f);lineTo(w*.69f,h*.24f);quadraticTo(w*.88f,h*.20f,w*.88f,h*.38f);quadraticTo(w*.88f,h*.52f,w*.75f,h*.64f);lineTo(w*.62f,h*.76f);quadraticTo(w*.45f,h*.88f,w*.32f,h*.72f)};drawPath(p,c,style=Stroke(sw)) }
            k.contains("编辑") || k.contains("edit") -> { line(w*.25f,h*.76f,w*.72f,h*.29f); poly(listOf(Offset(w*.64f,h*.22f),Offset(w*.78f,h*.36f),Offset(w*.72f,h*.29f))); line(w*.20f,h*.82f,w*.36f,h*.78f) }
            k.contains("关闭") || k.contains("close") -> { line(w*.22f,h*.22f,w*.78f,h*.78f); line(w*.78f,h*.22f,w*.22f,h*.78f) }
            k.contains("对比度") || k.contains("contrast") -> { circle(cx,cy,w*.34f); line(cx,h*.16f,cx,h*.84f); line(w*.16f,cy,w*.84f,cy); poly(listOf(Offset(w*.28f,h*.28f),Offset(w*.72f,h*.72f))); poly(listOf(Offset(w*.72f,h*.28f),Offset(w*.28f,h*.72f))) }
            k.contains("更多") || k.contains("more") -> { for(i in 0..2) circle(w*(.25f+i*.25f),cy,sw*.9f,true) }
            k.contains("随机") || k.contains("shuffle") -> { poly(listOf(Offset(w*.16f,h*.28f),Offset(w*.35f,h*.28f),Offset(w*.66f,h*.72f),Offset(w*.84f,h*.72f))); poly(listOf(Offset(w*.16f,h*.72f),Offset(w*.35f,h*.72f),Offset(w*.66f,h*.28f),Offset(w*.84f,h*.28f))); poly(listOf(Offset(w*.70f,h*.58f),Offset(w*.84f,h*.72f),Offset(w*.70f,h*.86f))); poly(listOf(Offset(w*.70f,h*.14f),Offset(w*.84f,h*.28f),Offset(w*.70f,h*.42f))) }
            k.contains("切换") || k.contains("swap") -> { poly(listOf(Offset(w*.16f,h*.32f),Offset(w*.82f,h*.32f),Offset(w*.68f,h*.18f))); poly(listOf(Offset(w*.84f,h*.68f),Offset(w*.18f,h*.68f),Offset(w*.32f,h*.82f))) }
            k.contains("刷新") || k.contains("refresh") -> { val p=androidx.compose.ui.graphics.Path().apply{moveTo(w*.78f,h*.38f);quadraticTo(w*.66f,h*.12f,w*.42f,h*.18f);quadraticTo(w*.12f,h*.24f,w*.16f,h*.56f);quadraticTo(w*.20f,h*.84f,w*.50f,h*.84f);quadraticTo(w*.72f,h*.84f,w*.82f,h*.64f)};drawPath(p,c,style=Stroke(sw));poly(listOf(Offset(w*.65f,h*.18f),Offset(w*.80f,h*.18f),Offset(w*.80f,h*.34f))) }
            k.contains("新增") || k.contains("添加") || k.contains("add") -> { line(cx,h*.16f,cx,h*.84f); line(w*.16f,cy,w*.84f,cy) }
            k.contains("悬浮窗") || k.contains("浮窗") || k.contains("overlay") -> { outlineRect(w*.12f,h*.18f,w*.76f,h*.64f,w*.05f); outlineRect(w*.48f,h*.42f,w*.40f,h*.34f,w*.04f) }
            k.contains("缩放") || k.contains("resize") -> { poly(listOf(Offset(w*.18f,h*.40f),Offset(w*.18f,h*.18f),Offset(w*.40f,h*.18f))); poly(listOf(Offset(w*.60f,h*.82f),Offset(w*.82f,h*.82f),Offset(w*.82f,h*.60f))); line(w*.22f,h*.38f,w*.78f,h*.78f) }
            k.contains("边距") || k.contains("margin") -> { outlineRect(w*.12f,h*.12f,w*.76f,h*.76f,sw*.6f); outlineRect(w*.30f,h*.30f,w*.40f,h*.40f,sw*.6f) }
            k.contains("空行") || k.contains("间距") || k.contains("spacing") -> { line(cx,h*.14f,cx,h*.86f); poly(listOf(Offset(w*.34f,h*.30f),Offset(cx,h*.14f),Offset(w*.66f,h*.30f))); poly(listOf(Offset(w*.34f,h*.70f),Offset(cx,h*.86f),Offset(w*.66f,h*.70f))); line(w*.18f,h*.50f,w*.82f,h*.50f) }
            k.contains("公众号") || k.contains("账号") || k.contains("account") -> { outlineRect(w*.14f,h*.12f,w*.72f,h*.76f,w*.08f); circle(cx,h*.39f,w*.13f); val p=androidx.compose.ui.graphics.Path().apply{moveTo(w*.28f,h*.76f);quadraticTo(w*.28f,h*.58f,cx,h*.58f);quadraticTo(w*.72f,h*.58f,w*.72f,h*.76f)};drawPath(p,c,style=Stroke(sw)) }
            k.contains("emoji") || k.contains("表情") -> { circle(cx,cy,w*.36f); circle(w*.38f,h*.42f,sw*.8f,true); circle(w*.62f,h*.42f,sw*.8f,true); val p=androidx.compose.ui.graphics.Path().apply{moveTo(w*.34f,h*.60f);quadraticTo(cx,h*.78f,w*.66f,h*.60f)};drawPath(p,c,style=Stroke(sw)) }
            k.contains("动图") || k.contains("gif") || k.contains("视频") -> { outlineRect(w*.12f,h*.20f,w*.76f,h*.60f,w*.08f); poly(listOf(Offset(w*.43f,h*.34f),Offset(w*.66f,cy),Offset(w*.43f,h*.66f)),true) }
            k.contains("往期") || k.contains("历史") || k.contains("history") -> { circle(cx,cy,w*.34f); line(cx,cy,cx,h*.28f); line(cx,cy,w*.68f,h*.60f); poly(listOf(Offset(w*.18f,h*.34f),Offset(w*.18f,h*.16f),Offset(w*.36f,h*.16f))) }
            k.contains("朋友圈") || k.contains("moments") -> { circle(cx,cy,w*.32f); circle(cx,cy,w*.12f); circle(cx,h*.12f,sw*.6f); circle(cx,h*.88f,sw*.6f) }
            k.contains("抖音") || k.contains("音乐") || k.contains("douyin") -> { val p=androidx.compose.ui.graphics.Path().apply{moveTo(w*.58f,h*.16f);lineTo(w*.58f,h*.64f);quadraticTo(w*.58f,h*.84f,w*.38f,h*.84f);quadraticTo(w*.20f,h*.84f,w*.20f,h*.68f);quadraticTo(w*.20f,h*.52f,w*.42f,h*.50f);lineTo(w*.58f,h*.50f);lineTo(w*.58f,h*.16f);lineTo(w*.78f,h*.32f)};drawPath(p,c,style=Stroke(sw)) }
            k.contains("json") -> { val p=androidx.compose.ui.graphics.Path().apply{moveTo(w*.40f,h*.18f);quadraticTo(w*.24f,h*.18f,w*.24f,h*.34f);lineTo(w*.24f,h*.44f);quadraticTo(w*.24f,h*.50f,w*.14f,h*.50f);quadraticTo(w*.24f,h*.50f,w*.24f,h*.58f);lineTo(w*.24f,h*.68f);quadraticTo(w*.24f,h*.82f,w*.40f,h*.82f);moveTo(w*.60f,h*.18f);quadraticTo(w*.76f,h*.18f,w*.76f,h*.34f);lineTo(w*.76f,h*.44f);quadraticTo(w*.76f,h*.50f,w*.86f,h*.50f);quadraticTo(w*.76f,h*.50f,w*.76f,h*.58f);lineTo(w*.76f,h*.68f);quadraticTo(w*.76f,h*.82f,w*.60f,h*.82f)};drawPath(p,c,style=Stroke(sw)) }
            k.contains("本地保存") || k.contains("手机") || k.contains("local") -> { outlineRect(w*.28f,h*.10f,w*.44f,h*.80f,w*.08f); line(w*.40f,h*.20f,w*.60f,h*.20f); line(w*.44f,h*.78f,w*.56f,h*.78f) }
            k.contains("成功") || k.contains("success") -> { circle(cx,cy,w*.38f); poly(listOf(Offset(w*.28f,h*.52f),Offset(w*.44f,h*.68f),Offset(w*.74f,h*.34f))) }
            k.contains("警告") || k.contains("warning") -> { poly(listOf(Offset(cx,h*.12f),Offset(w*.88f,h*.84f),Offset(w*.12f,h*.84f)),true); line(cx,h*.36f,cx,h*.60f); circle(cx,h*.70f,sw*.7f,true) }
            k.contains("提示") || k.contains("信息") || k.contains("info") -> { circle(cx,cy,w*.38f); circle(cx,h*.31f,sw*.7f,true); line(cx,h*.46f,cx,h*.72f) }
            else -> { outlineRect(w*.18f,h*.12f,w*.64f,h*.76f,w*.06f); line(w*.31f,h*.35f,w*.69f,h*.35f); line(w*.31f,h*.52f,w*.69f,h*.52f); line(w*.31f,h*.69f,w*.58f,h*.69f) }
        }
    }
}

'''
once(
"@Composable\nprivate fun EditorTool(label: String, selected: Boolean = false, onClick: () -> Unit) {",
icon_composable + "@Composable\nprivate fun EditorTool(label: String, selected: Boolean = false, onClick: () -> Unit) {",
"vector icon renderer"
)
once(
"""        Text(editorToolGlyph(label), color = if (selected) AppColors.Theme else if (dark) Color(0xFFDDDDDD) else AppColors.TextMain,
            fontSize = 19.sp, fontWeight = FontWeight.Medium, lineHeight = 21.sp)""",
"""        ShiWanJuLineIcon(label, if (selected) AppColors.Theme else if (dark) Color(0xFFDDDDDD) else AppColors.TextMain, Modifier.size(22.dp))""",
"replace glyph icons in secondary panels"
)
once(
"""        Text(glyph, color = AppColors.TextMain, fontSize = 19.sp, lineHeight = 21.sp, fontWeight = FontWeight.Medium)""",
"""        ShiWanJuLineIcon(label, AppColors.TextMain, Modifier.size(21.dp))""",
"replace glyph icons in text/image selection dock"
)
once(
"""Text(editorToolGlyph(item), color = Color(0xFFDDDDDD), fontSize = 18.sp, lineHeight = 20.sp)""",
"""ShiWanJuLineIcon(item, Color(0xFFDDDDDD), Modifier.size(20.dp))""",
"replace glyph icons in persistent primary dock"
)

# Replace remaining toolbar glyphs with the same semantic line renderer.
glyph_replacements = {
    'Text("⠿", color = AppColors.TextDim, fontSize = 15.sp, modifier = Modifier.padding(end = 6.dp))':
        'ShiWanJuLineIcon("拖动", AppColors.TextDim, Modifier.padding(end = 6.dp).size(20.dp))',
    'Text("▣ 尺寸 ▾", color = accent, fontSize = 11.sp)':
        'Row(verticalAlignment = Alignment.CenterVertically) { ShiWanJuLineIcon("尺寸", accent, Modifier.size(15.dp)); Text("尺寸 ▾", color = accent, fontSize = 11.sp) }',
    'Text("▧ 裁切 ▾", color = ink, fontSize = 11.sp)':
        'Row(verticalAlignment = Alignment.CenterVertically) { ShiWanJuLineIcon("裁剪", ink, Modifier.size(15.dp)); Text("裁切 ▾", color = ink, fontSize = 11.sp) }',
    'Text("↻ 旋转", color = ink, fontSize = 11.sp)':
        'Row(verticalAlignment = Alignment.CenterVertically) { ShiWanJuLineIcon("旋转", ink, Modifier.size(15.dp)); Text("旋转", color = ink, fontSize = 11.sp) }',
    'Text("◒ 外观 ▾", color = ink, fontSize = 11.sp)':
        'Row(verticalAlignment = Alignment.CenterVertically) { ShiWanJuLineIcon("样式", ink, Modifier.size(15.dp)); Text("外观 ▾", color = ink, fontSize = 11.sp) }',
    'Text("▧ 替换", color = ink, fontSize = 11.sp)':
        'Row(verticalAlignment = Alignment.CenterVertically) { ShiWanJuLineIcon("替换图片", ink, Modifier.size(15.dp)); Text("替换", color = ink, fontSize = 11.sp) }',
    'Text("ⓘ 说明", color = ink, fontSize = 11.sp)':
        'Row(verticalAlignment = Alignment.CenterVertically) { ShiWanJuLineIcon("说明", ink, Modifier.size(15.dp)); Text("说明", color = ink, fontSize = 11.sp) }',
    'Text("⌫ 删除", color = Color(0xFFCC5555), fontSize = 11.sp)':
        'Row(verticalAlignment = Alignment.CenterVertically) { ShiWanJuLineIcon("删除", Color(0xFFCC5555), Modifier.size(15.dp)); Text("删除", color = Color(0xFFCC5555), fontSize = 11.sp) }',
    'Text("更多 ⋯", color = accent, fontSize = 11.sp)':
        'Row(verticalAlignment = Alignment.CenterVertically) { ShiWanJuLineIcon("更多", accent, Modifier.size(15.dp)); Text("更多", color = accent, fontSize = 11.sp) }',
    'Text("Aᴀ 字号 ▾", color = accent, fontSize = 11.sp)':
        'Row(verticalAlignment = Alignment.CenterVertically) { ShiWanJuLineIcon("字号", accent, Modifier.size(15.dp)); Text("字号 ▾", color = accent, fontSize = 11.sp) }',
    'Text("≡", color = ink, fontSize = 15.sp)':
        'ShiWanJuLineIcon("左对齐", ink, Modifier.size(20.dp))',
    'Text("☷", color = ink, fontSize = 15.sp)':
        'ShiWanJuLineIcon("居中对齐", ink, Modifier.size(20.dp))',
    'Text("☷•", color = ink, fontSize = 12.sp)':
        'ShiWanJuLineIcon("列表", ink, Modifier.size(18.dp))',
    'Text("⌕", color = ink, fontSize = 15.sp)':
        'ShiWanJuLineIcon("搜索", ink, Modifier.size(20.dp))',
    'Text("↑", color = ink, fontSize = 12.sp)':
        'ShiWanJuLineIcon("上移", ink, Modifier.size(16.dp))',
    'Text("↓", color = ink, fontSize = 12.sp)':
        'ShiWanJuLineIcon("下移", ink, Modifier.size(16.dp))',
    'Text("B", color = ink, fontWeight = FontWeight.Bold, fontSize = 14.sp)':
        'ShiWanJuLineIcon("加粗", ink, Modifier.size(18.dp))',
    'Text("I", color = ink, fontSize = 14.sp)':
        'ShiWanJuLineIcon("斜体", ink, Modifier.size(18.dp))',
    'Text("U", color = ink, fontSize = 14.sp)':
        'ShiWanJuLineIcon("下划线", ink, Modifier.size(18.dp))',
    'Text("S", color = ink, fontSize = 14.sp)':
        'ShiWanJuLineIcon("删除线", ink, Modifier.size(18.dp))',
    'Text("−", color = Color.White)':
        'ShiWanJuLineIcon("缩小", Color.White, Modifier.size(16.dp))',
    'Text("+ 新建文章", color = accent)':
        'Row(verticalAlignment = Alignment.CenterVertically) { ShiWanJuLineIcon("新增", accent, Modifier.size(16.dp)); Text("新建文章", color = accent) }',

    'Text("⠿", color = AppColors.Theme, fontSize = 17.sp)':
        'ShiWanJuLineIcon("拖动", AppColors.Theme, Modifier.size(20.dp))',
}
for old, new in glyph_replacements.items():
    s = s.replace(old, new)


# Discrete image positioning: free transform remains unchanged; layout drag snaps to
# the next row/column slot, like moving between cells in a grid.
def replace_pattern(pattern, replacement, label):
    global s
    updated, count = re.subn(pattern, replacement, s, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"Image grid patch anchor mismatch [{label}]: {count}")
    s = updated
    print("Image grid patch:", label)

replace_pattern(
    r"function moveSelectedImageInGroup\(dir\)\{.*?NativeEditor\.changed\(root\.innerHTML\);\}",
    """function moveSelectedImageInGrid(dx,dy){if(!activeImage)return;const cell=activeImage.closest('td,th'),table=activeImage.closest('table');if(cell&&table){const rows=Array.from(table.rows),ri=rows.indexOf(cell.parentElement),ci=Array.from(cell.parentElement.cells).indexOf(cell),tr=rows[ri+dy],target=tr&&tr.cells[ci+dx];if(!target||target===cell)return;const html=cell.innerHTML;cell.innerHTML=target.innerHTML;target.innerHTML=html;activeImage=target.querySelector('img');if(activeImage){root.querySelectorAll('.selected-image').forEach(x=>x.classList.remove('selected-image'));activeImage.classList.add('selected-image');NativeEditor.imageSelected(activeImage.outerHTML);}commitHistory();NativeEditor.changed(root.innerHTML);return;}if(dy!==0){const block=topLevelAt(activeImage),siblings=Array.from(root.children),i=siblings.indexOf(block),target=siblings[i+dy];if(block&&target){if(dy<0)root.insertBefore(block,target);else root.insertBefore(target,block);commitHistory();NativeEditor.changed(root.innerHTML);}}}
                             function moveSelectedImageInGroup(dir){moveSelectedImageInGrid(dir,0);}""",
    "grid movement function"
)
replace_pattern(
    r"root\.addEventListener\('touchstart'.*?(?=root\.addEventListener\('touchend')",
    """root.addEventListener('touchstart',function(ev){if(!ev.touches||ev.touches.length!==1)return;const t=ev.touches[0],img=ev.target&&ev.target.closest?ev.target.closest('img'):null,cell=img?img.closest('td,th'):null,table=img?img.closest('table'):null,block=topLevelAt(ev.target);if(img){activeImage=img;touchDrag=cell&&table?{kind:'image-grid',source:cell,table:table,x:t.clientX,y:t.clientY,started:Date.now(),active:false}:{kind:'image-block',source:block,x:t.clientX,y:t.clientY,started:Date.now(),active:false};}else if(block&&block.classList.contains('selected-block')){touchDrag={kind:multiSelectMode?'blocks':'block',source:block,sources:multiSelectMode?Array.from(root.querySelectorAll('.selected-block')):[block],x:t.clientX,y:t.clientY,started:Date.now(),active:false};}}, {passive:true});
                             root.addEventListener('touchmove',function(ev){if(!touchDrag||!ev.touches||ev.touches.length!==1)return;const t=ev.touches[0],dx=t.clientX-touchDrag.x,dy=t.clientY-touchDrag.y;if(!touchDrag.active){if(Date.now()-touchDrag.started<180||Math.abs(dx)+Math.abs(dy)<8)return;touchDrag.active=true;root.style.userSelect='none';}ev.preventDefault();const hit=document.elementFromPoint(t.clientX,t.clientY);let target=null;if(touchDrag.kind==='image-grid'){const cell=hit&&hit.closest?hit.closest('td,th'):null;if(cell&&cell.closest('table')===touchDrag.table&&cell!==touchDrag.source)target=cell;}else if(touchDrag.kind==='image-block'){target=topLevelAt(hit);if(!target||target===touchDrag.source||!touchDrag.source||target.parentElement!==root)target=null;}else{target=topLevelAt(hit);if((touchDrag.sources||[touchDrag.source]).includes(target))target=null;}if(target!==(touchDrop&&touchDrop.el)){clearTouchDrop();if(target){touchDrop={el:target,outline:target.style.outline,shadow:target.style.boxShadow};target.style.outline='2px dashed #159765';target.style.boxShadow='0 0 0 2px rgba(21,151,101,.12)';}}},{passive:false});
                             function finishTouchDrag(){if(!touchDrag)return;const drag=touchDrag,target=touchDrop&&touchDrop.el;clearTouchDrop();root.style.userSelect='';if(drag.active&&target){if(drag.kind==='image-grid'&&target.closest('table')===drag.table){const a=drag.source.innerHTML,b=target.innerHTML;drag.source.innerHTML=b;target.innerHTML=a;activeImage=target.querySelector('img');if(activeImage){root.querySelectorAll('.selected-image').forEach(x=>x.classList.remove('selected-image'));activeImage.classList.add('selected-image');NativeEditor.imageSelected(activeImage.outerHTML);}commitHistory();NativeEditor.changed(root.innerHTML);}else if(drag.kind==='image-block'&&target.parentElement===root){const rect=target.getBoundingClientRect(),before=drag.lastY<rect.top+rect.height/2;root.insertBefore(drag.source,before?target:target.nextSibling);commitHistory();NativeEditor.changed(root.innerHTML);activeImage=drag.source.querySelector('img');if(activeImage){root.querySelectorAll('.selected-image').forEach(x=>x.classList.remove('selected-image'));activeImage.classList.add('selected-image');NativeEditor.imageSelected(activeImage.outerHTML);}}else if((drag.kind==='block'||drag.kind==='blocks')&&target.parentElement===root){const rect=target.getBoundingClientRect(),anchor=drag.lastY<rect.top+rect.height/2?target:target.nextSibling,sources=drag.kind==='blocks'?drag.sources:[drag.source];sources.forEach(node=>root.insertBefore(node,anchor));commitHistory();NativeEditor.changed(root.innerHTML);NativeEditor.blockSelected(sources.map(node=>cleanBlockHtml(node)).join(''));}}touchDrag=null;}
                             """,
    "touch image grid and vertical block dragging"
)
replace_pattern(
    r'EditorTool\("组内左移"\).*?\n\s*EditorTool\("组内右移"\).*?(?=\n)',
    """EditorTool("组内左移") { runJs("moveSelectedImageInGrid(-1,0)") }
                             EditorTool("组内右移") { runJs("moveSelectedImageInGrid(1,0)") }
                             EditorTool("组内上移") { runJs("moveSelectedImageInGrid(0,-1)") }
                             EditorTool("组内下移") { runJs("moveSelectedImageInGrid(0,1)") }""",
    "four-direction image movement controls"
)

# Validate that every icon-bearing dock now uses the vector renderer and that the
# live Text2 path updates both persisted HTML state and the visible WebView canvas.
checks = {
    "Text2 applies style to active selected text": "activeTextBlock:root.querySelector('.selected-text-block')" in s[s.index("function applyText2Style"):s.index("function applyText2Command")],
    "Text2 updates HTML immediately": "NativeEditor.changed(root.innerHTML);" in s[s.index("function applyText2Style"):s.index("function applyText2Command")],
    "Text2 notifies live canvas": "notifyCanvasPreview();" in s[s.index("function applyText2Style"):s.index("function applyText2Command")],
    "Compose vector icon renderer installed": "fun ShiWanJuLineIcon(" in s and "Canvas(modifier = modifier.size(24.dp))" in s,
    "secondary panel glyphs replaced": "Text(editorToolGlyph(label)" not in s,
    "selection dock glyphs replaced": "Text(glyph, color = AppColors.TextMain" not in s,
    "primary dock glyphs replaced": "Text(editorToolGlyph(item)" not in s,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    ERROR.write_text("Live preview/icon validation failed: " + ", ".join(failed) + "\\n", encoding="utf-8")
    raise SystemExit("Live preview/icon validation failed: " + ", ".join(failed))

EDITOR.write_text(s, encoding="utf-8")
print("Live preview repaired: Text2 resolves the active text block after Compose focus changes and notifies the live canvas. Editor tools now use drawn vector icons instead of font glyph placeholders.")
