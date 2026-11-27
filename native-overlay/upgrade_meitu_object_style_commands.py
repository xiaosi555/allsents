#!/usr/bin/env python3
"""Improve existing image appearance commands with editable, live Meitu-style controls."""
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
s = P.read_text(encoding="utf-8")

def once(old, new, label):
    global s
    if new in s:
        return
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected one anchor, got {n}")
    s = s.replace(old, new, 1)

once(
    '    var imageRadius by remember { mutableFloatStateOf(0f) }',
    '''    var imageRadius by remember { mutableFloatStateOf(0f) }
    var imageRadiusLinked by remember { mutableStateOf(true) }
    var imageRadiusTL by remember { mutableFloatStateOf(0f) }
    var imageRadiusTR by remember { mutableFloatStateOf(0f) }
    var imageRadiusBR by remember { mutableFloatStateOf(0f) }
    var imageRadiusBL by remember { mutableFloatStateOf(0f) }
    var imageBorderWidth by remember { mutableFloatStateOf(1f) }
    var imageBorderStyle by remember { mutableStateOf("solid") }
    var imageBorderColor by remember { mutableStateOf("#DDE3EA") }
    var imageShadowX by remember { mutableFloatStateOf(0f) }
    var imageShadowY by remember { mutableFloatStateOf(4f) }
    var imageShadowBlur by remember { mutableFloatStateOf(12f) }
    var imageShadowSpread by remember { mutableFloatStateOf(0f) }
    var imageShadowOpacity by remember { mutableFloatStateOf(24f) }
    var imageShadowColor by remember { mutableStateOf("#000000") }''',
    "image appearance states"
)

once(
    "function setSelectedImageBorder(v){if(!activeImage)return;activeImage.style.border=v;commitHistory();NativeEditor.changed(root.innerHTML);}",
    """function setSelectedImageBorder(v){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.border=v;commitSelectedImageStyle();}
                            function previewSelectedImageBorder(w,style,color){if(!activeImage||activeImage.dataset.editorLocked==='1')return;w=Math.max(0,Math.min(12,Number(w)||0));activeImage.style.border=w===0?'none':w+'px '+(style||'solid')+' '+(color||'#DDE3EA');}
                            function previewSelectedImageRadius(tl,tr,br,bl){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.borderRadius=[tl,tr,br,bl].map(v=>Math.max(0,Math.min(120,Number(v)||0))+'px').join(' ');}
                            function previewSelectedImageShadow(x,y,blur,spread,color,opacity){if(!activeImage||activeImage.dataset.editorLocked==='1')return;const h=(color||'#000000').replace('#',''),r=parseInt(h.slice(0,2),16)||0,g=parseInt(h.slice(2,4),16)||0,b=parseInt(h.slice(4,6),16)||0,a=Math.max(0,Math.min(100,Number(opacity)||0))/100;activeImage.style.boxShadow=a===0?'none':(Number(x)||0)+'px '+(Number(y)||0)+'px '+Math.max(0,Number(blur)||0)+'px '+(Number(spread)||0)+'px rgba('+r+','+g+','+b+','+a+')';}""",
    "image appearance preview helpers"
)

once(
    "function alignSelectedImage(v){if(!activeImage)return;activeImage.style.display='block';activeImage.style.marginLeft=v==='left'?'0':'auto';activeImage.style.marginRight=v==='right'?'0':'auto';if(v==='center'){activeImage.style.marginLeft='auto';activeImage.style.marginRight='auto';}commitHistory();NativeEditor.changed(root.innerHTML);}",
    """function alignSelectedImage(v){if(!activeImage||activeImage.dataset.editorLocked==='1')return;if(v==='top'||v==='middle'||v==='bottom'){activeImage.style.display='inline-block';activeImage.style.verticalAlign=v==='middle'?'middle':v;}else if(v==='fit'){activeImage.style.display='block';activeImage.style.width='100%';activeImage.style.height='auto';activeImage.style.marginLeft='0';activeImage.style.marginRight='0';}else if(v==='reset'){activeImage.style.display='';activeImage.style.marginLeft='';activeImage.style.marginRight='';activeImage.style.verticalAlign='';}else{activeImage.style.display='block';activeImage.style.marginLeft=v==='left'?'0':'auto';activeImage.style.marginRight=v==='right'?'0':'auto';if(v==='center'){activeImage.style.marginLeft='auto';activeImage.style.marginRight='auto';}}commitSelectedImageStyle();}""",
    "image alignment"
)

once(
    "radius:Math.max(0,parseFloat(css.borderTopLeftRadius)||0)",
    """radius:Math.max(0,parseFloat(css.borderTopLeftRadius)||0),
                                 radiusTL:Math.max(0,parseFloat(css.borderTopLeftRadius)||0),
                                 radiusTR:Math.max(0,parseFloat(css.borderTopRightRadius)||0),
                                 radiusBR:Math.max(0,parseFloat(css.borderBottomRightRadius)||0),
                                 radiusBL:Math.max(0,parseFloat(css.borderBottomLeftRadius)||0),
                                 borderWidth:Math.max(0,parseFloat(css.borderTopWidth)||0),
                                 borderStyle:css.borderTopStyle||'solid',
                                 borderColor:(()=>{const m=(css.borderTopColor||'').match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);return m?'#'+[m[1],m[2],m[3]].map(v=>Number(v).toString(16).padStart(2,'0')).join('').toUpperCase():'#DDE3EA';})(),
                                 shadow:(()=>{const m=(css.boxShadow||'').match(/(-?[\\d.]+)px\\s+(-?[\\d.]+)px\\s+([\\d.]+)px(?:\\s+(-?[\\d.]+)px)?\\s+rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+),?\\s*([\\d.]*)\\)/);return m?{x:Number(m[1]),y:Number(m[2]),blur:Number(m[3]),spread:Number(m[4]||0),color:'#'+[m[5],m[6],m[7]].map(v=>Number(v).toString(16).padStart(2,'0')).join('').toUpperCase(),opacity:Math.round(Number(m[8]||1)*100)}:{x:0,y:4,blur:12,spread:0,color:'#000000',opacity:24};})()""",
    "image appearance reader"
)

once(
    'imageRadius = controls.optDouble("radius", 0.0).toFloat().coerceIn(0f, 40f)',
    '''imageRadius = controls.optDouble("radius", 0.0).toFloat().coerceIn(0f, 120f)
                                             imageRadiusTL = controls.optDouble("radiusTL", 0.0).toFloat().coerceIn(0f, 120f)
                                             imageRadiusTR = controls.optDouble("radiusTR", 0.0).toFloat().coerceIn(0f, 120f)
                                             imageRadiusBR = controls.optDouble("radiusBR", 0.0).toFloat().coerceIn(0f, 120f)
                                             imageRadiusBL = controls.optDouble("radiusBL", 0.0).toFloat().coerceIn(0f, 120f)
                                             imageRadiusLinked = imageRadiusTL == imageRadiusTR && imageRadiusTR == imageRadiusBR && imageRadiusBR == imageRadiusBL
                                             imageBorderWidth = controls.optDouble("borderWidth", 0.0).toFloat().coerceIn(0f, 12f)
                                             imageBorderStyle = controls.optString("borderStyle", "solid").takeIf { it in listOf("solid", "dashed", "dotted") } ?: "solid"
                                             imageBorderColor = controls.optString("borderColor", "#DDE3EA")
                                             controls.optJSONObject("shadow")?.let { sh ->
                                                 imageShadowX = sh.optDouble("x", 0.0).toFloat().coerceIn(-30f, 30f)
                                                 imageShadowY = sh.optDouble("y", 4.0).toFloat().coerceIn(-30f, 30f)
                                                 imageShadowBlur = sh.optDouble("blur", 12.0).toFloat().coerceIn(0f, 60f)
                                                 imageShadowSpread = sh.optDouble("spread", 0.0).toFloat().coerceIn(-20f, 30f)
                                                 imageShadowColor = sh.optString("color", "#000000")
                                                 imageShadowOpacity = sh.optDouble("opacity", 24.0).toFloat().coerceIn(0f, 100f)
                                             }''',
    "image appearance state readback"
)

old_radius = '''                        "radius" -> {
                            Text("圆角 §{imageRadius.toInt()}px", color = Color.LightGray, fontSize = 12.sp)
                            Slider(value = imageRadius, onValueChange = { imageRadius = it; runJs("previewSelectedImageRadius('§{it}px')") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..40f)
                            TextButton(onClick = { imageRadius = 0f; runJs("previewSelectedImageRadius('0px');commitSelectedImageStyle()") }) { Text("直角", color = AppColors.Theme) }
                        }'''.replace("§", "$")
new_radius = '''                        "radius" -> {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                Text("圆角半径", color = Color.LightGray, fontSize = 12.sp)
                                TextButton(onClick = { imageRadiusLinked = !imageRadiusLinked }) { Text(if (imageRadiusLinked) "四角统一" else "四角独立", color = AppColors.Theme, fontSize = 11.sp) }
                            }
                            if (imageRadiusLinked) {
                                Text("统一圆角 " + imageRadius.toInt() + " px", color = Color.LightGray, fontSize = 11.sp)
                                Slider(value = imageRadius, onValueChange = { imageRadius = it; imageRadiusTL = it; imageRadiusTR = it; imageRadiusBR = it; imageRadiusBL = it; runJs("previewSelectedImageRadius(" + it + "," + it + "," + it + "," + it + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..120f)
                            } else {
                                Text("左上 " + imageRadiusTL.toInt() + " px", color = Color.LightGray, fontSize = 11.sp)
                                Slider(value = imageRadiusTL, onValueChange = { imageRadiusTL = it; runJs("previewSelectedImageRadius(" + it + "," + imageRadiusTR + "," + imageRadiusBR + "," + imageRadiusBL + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..120f)
                                Text("右上 " + imageRadiusTR.toInt() + " px", color = Color.LightGray, fontSize = 11.sp)
                                Slider(value = imageRadiusTR, onValueChange = { imageRadiusTR = it; runJs("previewSelectedImageRadius(" + imageRadiusTL + "," + it + "," + imageRadiusBR + "," + imageRadiusBL + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..120f)
                                Text("右下 " + imageRadiusBR.toInt() + " px", color = Color.LightGray, fontSize = 11.sp)
                                Slider(value = imageRadiusBR, onValueChange = { imageRadiusBR = it; runJs("previewSelectedImageRadius(" + imageRadiusTL + "," + imageRadiusTR + "," + it + "," + imageRadiusBL + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..120f)
                                Text("左下 " + imageRadiusBL.toInt() + " px", color = Color.LightGray, fontSize = 11.sp)
                                Slider(value = imageRadiusBL, onValueChange = { imageRadiusBL = it; runJs("previewSelectedImageRadius(" + imageRadiusTL + "," + imageRadiusTR + "," + imageRadiusBR + "," + it + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..120f)
                            }
                            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                listOf(0f, 4f, 8f, 16f, 24f, 40f).forEach { v -> TextButton(onClick = { imageRadius = v; imageRadiusTL = v; imageRadiusTR = v; imageRadiusBR = v; imageRadiusBL = v; imageRadiusLinked = true; runJs("previewSelectedImageRadius(" + v + "," + v + "," + v + "," + v + ");commitSelectedImageStyle()") }, contentPadding = PaddingValues(horizontal = 5.dp, vertical = 0.dp)) { Text(v.toInt().toString(), color = Color.White, fontSize = 10.sp) } }
                            }
                        }'''
once(old_radius, new_radius, "four-corner radius controls")

old_border = '''                        "border" -> listOf("无边框" to "0", "细边框" to "1px solid #dfe5e1", "主题色边框" to "2px solid #159765").forEach { (label, value) ->
                            TextButton(onClick = { runJs("setSelectedImageBorder('$value')"); activeObjectDialog = "" }) { Text(label, color = Color.White) }
                        }'''
new_border = '''                        "border" -> {
                            Text("边框粗细 " + imageBorderWidth.toInt() + " px", color = Color.LightGray, fontSize = 11.sp)
                            Slider(value = imageBorderWidth, onValueChange = { imageBorderWidth = it; runJs("previewSelectedImageBorder(" + it + "," + JSONObject.quote(imageBorderStyle) + "," + JSONObject.quote(imageBorderColor) + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..12f)
                            Text("线型", color = Color.LightGray, fontSize = 11.sp)
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                listOf("solid" to "实线", "dashed" to "虚线", "dotted" to "点线").forEach { (v, label) -> TextButton(onClick = { imageBorderStyle = v; runJs("previewSelectedImageBorder(" + imageBorderWidth + "," + JSONObject.quote(v) + "," + JSONObject.quote(imageBorderColor) + ");commitSelectedImageStyle()") }) { Text(label, color = if (imageBorderStyle == v) AppColors.Theme else Color.White, fontSize = 11.sp) } }
                            }
                            Text("边框颜色", color = Color.LightGray, fontSize = 11.sp)
                            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                                listOf("#FFFFFF", "#DDE3EA", "#222222", "#159765", "#3978B7", "#D69A35", "#C84B4B").forEach { color ->
                                    Box(Modifier.size(28.dp).clip(CircleShape).background(Color(android.graphics.Color.parseColor(color))).border(if (imageBorderColor == color) 2.dp else 1.dp, Color.White, CircleShape).clickable { imageBorderColor = color; runJs("previewSelectedImageBorder(" + imageBorderWidth + "," + JSONObject.quote(imageBorderStyle) + "," + JSONObject.quote(color) + ");commitSelectedImageStyle()") })
                                }
                            }
                            TextButton(onClick = { imageBorderWidth = 0f; runJs("previewSelectedImageBorder(0,'solid','#000000');commitSelectedImageStyle()") }) { Text("移除边框", color = AppColors.Theme) }
                        }'''
once(old_border, new_border, "custom image border controls")

old_shadow = '''                        "shadow" -> listOf("无阴影" to "none", "轻阴影" to "0 2px 6px rgba(0,0,0,.14)", "中阴影" to "0 4px 14px rgba(0,0,0,.22)", "强阴影" to "0 8px 24px rgba(0,0,0,.28)").forEach { (label, value) ->
                            TextButton(onClick = { runJs("setSelectedImageShadow(§{JSONObject.quote(value)})"); activeObjectDialog = "" }) { Text(label, color = Color.White) }
                        }'''.replace("§", "$")
new_shadow = '''                        "shadow" -> {
                            Text("水平偏移 " + imageShadowX.toInt() + " px", color = Color.LightGray, fontSize = 11.sp)
                            Slider(value = imageShadowX, onValueChange = { imageShadowX = it; runJs("previewSelectedImageShadow(" + it + "," + imageShadowY + "," + imageShadowBlur + "," + imageShadowSpread + "," + JSONObject.quote(imageShadowColor) + "," + imageShadowOpacity + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = -30f..30f)
                            Text("垂直偏移 " + imageShadowY.toInt() + " px", color = Color.LightGray, fontSize = 11.sp)
                            Slider(value = imageShadowY, onValueChange = { imageShadowY = it; runJs("previewSelectedImageShadow(" + imageShadowX + "," + it + "," + imageShadowBlur + "," + imageShadowSpread + "," + JSONObject.quote(imageShadowColor) + "," + imageShadowOpacity + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = -30f..30f)
                            Text("模糊 " + imageShadowBlur.toInt() + " px", color = Color.LightGray, fontSize = 11.sp)
                            Slider(value = imageShadowBlur, onValueChange = { imageShadowBlur = it; runJs("previewSelectedImageShadow(" + imageShadowX + "," + imageShadowY + "," + it + "," + imageShadowSpread + "," + JSONObject.quote(imageShadowColor) + "," + imageShadowOpacity + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..60f)
                            Text("扩散 " + imageShadowSpread.toInt() + " px", color = Color.LightGray, fontSize = 11.sp)
                            Slider(value = imageShadowSpread, onValueChange = { imageShadowSpread = it; runJs("previewSelectedImageShadow(" + imageShadowX + "," + imageShadowY + "," + imageShadowBlur + "," + it + "," + JSONObject.quote(imageShadowColor) + "," + imageShadowOpacity + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = -20f..30f)
                            Text("不透明度 " + imageShadowOpacity.toInt() + "%", color = Color.LightGray, fontSize = 11.sp)
                            Slider(value = imageShadowOpacity, onValueChange = { imageShadowOpacity = it; runJs("previewSelectedImageShadow(" + imageShadowX + "," + imageShadowY + "," + imageShadowBlur + "," + imageShadowSpread + "," + JSONObject.quote(imageShadowColor) + "," + it + ")") }, onValueChangeFinished = { runJs("commitSelectedImageStyle()") }, valueRange = 0f..100f)
                            Text("阴影颜色", color = Color.LightGray, fontSize = 11.sp)
                            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                                listOf("#000000", "#333333", "#666666", "#159765", "#3978B7", "#C84B4B", "#FFFFFF").forEach { color ->
                                    Box(Modifier.size(28.dp).clip(CircleShape).background(Color(android.graphics.Color.parseColor(color))).border(if (imageShadowColor == color) 2.dp else 1.dp, Color.White, CircleShape).clickable { imageShadowColor = color; runJs("previewSelectedImageShadow(" + imageShadowX + "," + imageShadowY + "," + imageShadowBlur + "," + imageShadowSpread + "," + JSONObject.quote(color) + "," + imageShadowOpacity + ");commitSelectedImageStyle()") })
                                }
                            }
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                listOf("无" to 0f, "轻" to 12f, "中" to 24f, "强" to 40f).forEach { (label, alpha) -> TextButton(onClick = { imageShadowX = 0f; imageShadowY = 4f; imageShadowBlur = 12f; imageShadowSpread = 0f; imageShadowColor = "#000000"; imageShadowOpacity = alpha; runJs("previewSelectedImageShadow(0,4,12,0,'#000000'," + alpha + ");commitSelectedImageStyle()") }) { Text(label, color = Color.White, fontSize = 11.sp) } }
                            }
                        }'''
once(old_shadow, new_shadow, "custom image shadow controls")

old_align = '''                        "image-align" -> listOf("左对齐" to "left", "居中" to "center", "右对齐" to "right").forEach { (label, value) ->
                            TextButton(onClick = { runJs("alignSelectedImage('$value')"); activeObjectDialog = "" }) { Text(label, color = Color.White) }
                        }'''
new_align = '''                        "image-align" -> {
                            Text("水平对齐", color = Color.LightGray, fontSize = 11.sp)
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) { listOf("left" to "左对齐", "center" to "水平居中", "right" to "右对齐").forEach { (v, label) -> TextButton(onClick = { runJs("alignSelectedImage('$v')") }) { Text(label, color = Color.White, fontSize = 11.sp) } } }
                            Text("垂直对齐", color = Color.LightGray, fontSize = 11.sp)
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) { listOf("top" to "顶部", "middle" to "居中", "bottom" to "底部").forEach { (v, label) -> TextButton(onClick = { runJs("alignSelectedImage('$v')") }) { Text(label, color = Color.White, fontSize = 11.sp) } } }
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                                TextButton(onClick = { runJs("alignSelectedImage('fit')") }) { Text("适应宽度", color = AppColors.Theme) }
                                TextButton(onClick = { runJs("alignSelectedImage('reset')") }) { Text("重置对齐", color = Color.White) }
                            }
                        }'''
once(old_align, new_align, "image alignment controls")

# Extend the existing module-style dialog rather than adding a duplicate command.
once(
    '    var blockAlign by remember { mutableStateOf("left") }',
    '    var blockAlign by remember { mutableStateOf("left") }\n    var blockObjectAlign by remember { mutableStateOf("center") }',
    "module object alignment state"
)
once(
    '                    OutlinedTextField(blockBorderWidth, { blockBorderWidth = it.filter { c -> c.isDigit() }.take(1) }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("边框宽度（0–8 px）") })',
    '''                    OutlinedTextField(blockBorderWidth, { blockBorderWidth = it.filter { c -> c.isDigit() }.take(1) }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("边框宽度（0–8 px）") })
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(3.dp)) { listOf("0", "1", "2", "3", "4", "8").forEach { v -> TextButton(onClick = { blockBorderWidth = v }) { Text(v + "px", color = if (blockBorderWidth == v) accent else ink, fontSize = 10.sp) } } }''',
    "module border width presets"
)
once(
    '                    OutlinedTextField(blockBorderStyle, { blockBorderStyle = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("边框样式（solid / dashed / dotted）") })',
    '''                    OutlinedTextField(blockBorderStyle, { blockBorderStyle = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("边框样式（solid / dashed / dotted）") })
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(4.dp)) { listOf("solid" to "实线", "dashed" to "虚线", "dotted" to "点线").forEach { (v, label) -> TextButton(onClick = { blockBorderStyle = v }) { Text(label, color = if (blockBorderStyle == v) accent else ink, fontSize = 11.sp) } } }''',
    "module border style presets"
)
once(
    '                    OutlinedTextField(blockRadius, { blockRadius = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("圆角（例如 8px）") })',
    '''                    OutlinedTextField(blockRadius, { blockRadius = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("圆角（1–4 个值，可分别控制四角）") })
                    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(3.dp)) { listOf("0px", "4px", "8px", "12px", "20px", "32px", "50%").forEach { v -> TextButton(onClick = { blockRadius = v }) { Text(v, color = if (blockRadius == v) accent else ink, fontSize = 10.sp) } } }''',
    "module radius presets"
)
once(
    '                    OutlinedTextField(blockShadow, { blockShadow = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("阴影（none / 0 2px 8px #0002）") })',
    '''                    OutlinedTextField(blockShadow, { blockShadow = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("阴影（X / Y / 模糊 / 扩散 / 颜色）") })
                    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(3.dp)) { listOf("none" to "无", "0px 2px 6px #00000024" to "轻", "0px 4px 14px 0px #00000030" to "中", "0px 8px 24px 0px #0000003D" to "强", "0px 0px 0px 2px #00000020" to "描边").forEach { (v, label) -> TextButton(onClick = { blockShadow = v }) { Text(label, color = if (blockShadow == v) accent else ink, fontSize = 10.sp) } } }''',
    "module shadow presets"
)
once(
    '                    OutlinedTextField(blockAlign, { blockAlign = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("内容对齐（left / center / right / justify）") })',
    '''                    Text("内容对齐", color = ink, fontSize = 12.sp)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(3.dp)) { listOf("left" to "左", "center" to "中", "right" to "右", "justify" to "两端").forEach { (v, label) -> TextButton(onClick = { blockAlign = v }) { Text(label, color = if (blockAlign == v) accent else ink, fontSize = 11.sp) } } }
                    Text("模块位置", color = ink, fontSize = 12.sp)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(3.dp)) { listOf("left" to "靠左", "center" to "居中", "right" to "靠右").forEach { (v, label) -> TextButton(onClick = { blockObjectAlign = v }) { Text(label, color = if (blockObjectAlign == v) accent else ink, fontSize = 11.sp) } } }''',
    "module alignment controls"
)
once(
    'val shadowValue = Regex("""^(?:none|0(?:px)?\\s+\\d{1,3}px\\s+\\d{1,3}px\\s+#[0-9a-fA-F]{3,8})$""")',
    'val shadowValue = Regex("""^(?:none|[-+]?\\d{1,3}px\\s+[-+]?\\d{1,3}px\\s+\\d{1,3}px(?:\\s+[-+]?\\d{1,3}px)?\\s+#[0-9a-fA-F]{6,8})$""")',
    "module shadow validator"
)
old_apply = 'runJs("applySelectedBlockStyle(§{JSONObject.quote(blockPadding)},§{JSONObject.quote(blockMargin)},§{JSONObject.quote(blockWidth)},§{JSONObject.quote(blockBackground)},§{JSONObject.quote(blockBorder)},§{JSONObject.quote(blockBorderWidth)},§{JSONObject.quote(blockBorderStyle)},§{JSONObject.quote(blockRadius)},§{JSONObject.quote(blockShadow)},§{JSONObject.quote(blockAlign)},§{JSONObject.quote(blockOpacity)})")'.replace("§", "$")
new_apply = 'runJs("applySelectedBlockStyle(§{JSONObject.quote(blockPadding)},§{JSONObject.quote(blockMargin)},§{JSONObject.quote(blockWidth)},§{JSONObject.quote(blockBackground)},§{JSONObject.quote(blockBorder)},§{JSONObject.quote(blockBorderWidth)},§{JSONObject.quote(blockBorderStyle)},§{JSONObject.quote(blockRadius)},§{JSONObject.quote(blockShadow)},§{JSONObject.quote(blockAlign)},§{JSONObject.quote(blockOpacity)},§{JSONObject.quote(blockObjectAlign)})")'.replace("§", "$")
once(old_apply, new_apply, "module alignment command binding")
once(
    "function applySelectedBlockStyle(padding,margin,width,bg,border,borderWidth,borderStyle,radius,shadow,align,opacity){const e=selectedBlock();if(!e)return;e.style.boxSizing='border-box';e.style.padding=padding;e.style.margin=margin+' auto';e.style.width=width;e.style.maxWidth='100%';e.style.background='none';e.style.background=bg;e.style.border=borderWidth+'px '+borderStyle+' '+border;e.style.borderRadius=radius;e.style.boxShadow=shadow;e.style.textAlign=align;e.style.opacity=String(Math.max(0,Math.min(100,Number(opacity))))/100;commitHistory();NativeEditor.blockSelected(cleanBlockHtml(e));NativeEditor.changed(root.innerHTML);}",
    "function applySelectedBlockStyle(padding,margin,width,bg,border,borderWidth,borderStyle,radius,shadow,align,opacity,objectAlign){const e=selectedBlock();if(!e||e.dataset.editorLocked==='1')return;e.style.boxSizing='border-box';e.style.padding=padding;e.style.marginTop=margin;e.style.marginBottom=margin;e.style.marginLeft=objectAlign==='left'?'0':'auto';e.style.marginRight=objectAlign==='right'?'0':'auto';e.style.width=width;e.style.maxWidth='100%';e.style.background='none';e.style.background=bg;e.style.border=borderWidth+'px '+borderStyle+' '+border;e.style.borderRadius=radius;e.style.boxShadow=shadow;e.style.textAlign=align;e.style.opacity=String(Math.max(0,Math.min(100,Number(opacity))))/100;commitHistory();NativeEditor.blockSelected(cleanBlockHtml(e));NativeEditor.changed(root.innerHTML);}",
    "module object alignment implementation"
)

checks = [
    ("image border controls", "previewSelectedImageBorder(w,style,color)" in s and '"border" -> {' in s),
    ("four corner radius controls", "imageRadiusBL" in s and "previewSelectedImageRadius(tl,tr,br,bl)" in s),
    ("shadow controls", "previewSelectedImageShadow(x,y,blur,spread,color,opacity)" in s),
    ("horizontal and vertical alignment", "垂直对齐" in s and "alignSelectedImage(v)" in s),
    ("module border/radius/shadow presets", "blockBorderWidth" in s and "blockRadius" in s and "blockShadow" in s),
    ("module object alignment", "blockObjectAlign" in s),
]
failed = [name for name, ok in checks if not ok]
if failed:
    raise SystemExit("Appearance command verification failed: " + ", ".join(failed))

P.write_text(s, encoding="utf-8")
print("Existing image border/radius/shadow/alignment commands upgraded with live parameter controls.")
