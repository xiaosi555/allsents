#!/usr/bin/env python3
from pathlib import Path
P=Path(__file__).resolve().parents[1]/"source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
s=P.read_text(encoding="utf-8")
def rep(a,b):
 global s
 if b in s:return
 if s.count(a)!=1: raise SystemExit("anchor mismatch: "+a[:60])
 s=s.replace(a,b,1)
rep('    TEXT("文字"), TEXT2("文字2"), TITLE("标题"), IMAGE("图片"), LAYOUT("布局"),','    TEXT("文字"), TEXT2("文字2"), TITLE("标题"), IMAGE("图片"), IMAGE_CROP("裁剪"), IMAGE_COLOR("调色"), LAYOUT("布局"),')
rep('    var text2MainTab by remember { mutableStateOf("字体") }','    var text2MainTab by remember { mutableStateOf("字体") }\n    var imageCropMainTab by remember { mutableStateOf("比例") }\n    var imageColorMainTab by remember { mutableStateOf("光效") }')
rep('''                                    "image-copy" -> runJs("copySelectedImageObject()")
                                    "image-copy-style" -> runJs("copySelectedImageStyle()")
                                    "image-paste" -> runJs("pasteImageClipboard()")
                                    else -> activeObjectDialog = action''','''                                    "image-copy" -> runJs("copySelectedImageObject()")
                                    "image-copy-style" -> runJs("copySelectedImageStyle()")
                                    "image-paste" -> runJs("pasteImageClipboard()")
                                    "crop" -> { activePanel = EditorPanel.IMAGE_CROP; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }
                                    "color" -> { activePanel = EditorPanel.IMAGE_COLOR; showToolPopup = true; showCanvasPopup = false; toolPanelHeightDp = 200f }
                                    else -> activeObjectDialog = action''')
rep('''                        } else if (showTemplateSubnav) {''','''                        } else if (activePanel == EditorPanel.IMAGE_CROP || activePanel == EditorPanel.IMAGE_COLOR) {
                            val tabs = if (activePanel == EditorPanel.IMAGE_CROP) listOf("比例", "尺寸", "旋转", "翻转", "校正", "辅助线") else listOf("光效", "色彩", "HSL", "曲线", "细节")
                            Row(Modifier.weight(1f).horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
                                tabs.forEach { tab ->
                                    val chosen = if (activePanel == EditorPanel.IMAGE_CROP) imageCropMainTab == tab else imageColorMainTab == tab
                                    Column(Modifier.clickable { if (activePanel == EditorPanel.IMAGE_CROP) imageCropMainTab = tab else imageColorMainTab = tab }.padding(horizontal = 7.dp, vertical = 5.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                        Text(tab, color = if (chosen) Color.White else Color(0xFF888888), fontSize = 14.sp, fontWeight = if (chosen) FontWeight.Bold else FontWeight.Normal)
                                        Box(Modifier.padding(top = 2.dp).width(20.dp).height(2.dp).clip(RoundedCornerShape(4.dp)).background(if (chosen) AppColors.Theme else Color.Transparent))
                                    }
                                }
                            }
                        } else if (showTemplateSubnav) {''')
rep('''                    EditorPanel.TEXT2 -> {
                        Text2EditorPanel(''','''                    EditorPanel.IMAGE_CROP -> ImageCropColorPanel("crop", imageCropMainTab, { runJs(it) })
                    EditorPanel.IMAGE_COLOR -> ImageCropColorPanel("color", imageColorMainTab, { runJs(it) })
                    EditorPanel.TEXT2 -> {
                        Text2EditorPanel(''')
rep('private val templateSubPanels = setOf(EditorPanel.TITLE, EditorPanel.CARD, EditorPanel.IMAGE, EditorPanel.LAYOUT, EditorPanel.SVG, EditorPanel.COMPONENT)','private val templateSubPanels = setOf(EditorPanel.TITLE, EditorPanel.CARD, EditorPanel.IMAGE, EditorPanel.IMAGE_CROP, EditorPanel.IMAGE_COLOR, EditorPanel.LAYOUT, EditorPanel.SVG, EditorPanel.COMPONENT)')
anchor="function previewSelectedImageFilters(b,c,s){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.filter='brightness('+b+'%) contrast('+c+'%) saturate('+s+'%)';}"
addition=anchor+"""
                            function previewSelectedImageAdvanced(b,c,s,temp,tint,hue,gray,sepia,blur,rotation){
                              if(!activeImage||activeImage.dataset.editorLocked==='1')return;
                              const f=['brightness('+b+'%)','contrast('+c+'%)','saturate('+s+'%)','hue-rotate('+((Number(hue)||0)+(Number(tint)||0)*.12)+'deg)'];
                              if(Number(gray)>0)f.push('grayscale('+Math.max(0,Math.min(100,gray))+'%)');
                              if(Number(sepia)>0||Number(temp)!==0)f.push('sepia('+Math.max(0,Math.min(100,Number(sepia)+Math.abs(Number(temp))*.22))+'%)');
                              if(Number(blur)>0)f.push('blur('+Math.max(0,Math.min(12,blur))+'px)');
                              activeImage.style.filter=f.join(' ');
                              activeImage.style.transform='rotate('+(Number(activeImage.dataset.rotation||0)+Number(rotation||0))+'deg)';
                            }
                            function previewSelectedImageTransform(deg){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.transform='rotate('+(Number(activeImage.dataset.rotation||0)+Number(deg||0))+'deg)';}
                            function cropSelectedImageCustom(w,h){if(!activeImage||activeImage.dataset.editorLocked==='1')return;w=Math.max(1,Number(w)||1);h=Math.max(1,Number(h)||1);const box=activeImage.parentElement.clientWidth||320;activeImage.style.width='100%';activeImage.style.height=Math.max(1,Math.round(box*h/w))+'px';activeImage.style.maxWidth='100%';activeImage.style.objectFit='cover';activeImage.style.objectPosition='50% 50%';commitHistory();NativeEditor.imageSelected(activeImage.outerHTML);NativeEditor.changed(root.innerHTML);}
                            function previewSelectedImagePosition(x,y){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.objectPosition=Math.max(0,Math.min(100,x))+'% '+Math.max(0,Math.min(100,y))+'%';}
                            function resetSelectedImageColor(){if(!activeImage||activeImage.dataset.editorLocked==='1')return;activeImage.style.filter='';commitHistory();NativeEditor.changed(root.innerHTML);}
"""
rep(anchor,addition)
panel=r'''
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun ImageCropColorPanel(kind: String, tab: String, onJs: (String) -> Unit) {
 var a by remember { mutableFloatStateOf(100f) }; var b by remember { mutableFloatStateOf(100f) }; var c by remember { mutableFloatStateOf(100f) }
 var angle by remember { mutableFloatStateOf(0f) }; var x by remember { mutableFloatStateOf(50f) }; var y by remember { mutableFloatStateOf(50f) }
 var width by remember { mutableStateOf("4") }; var height by remember { mutableStateOf("3") }
 val ink=Color(0xFFE7E7E7)
 Column(Modifier.fillMaxWidth().fillMaxHeight().verticalScroll(rememberScrollState()).padding(5.dp),verticalArrangement=Arrangement.spacedBy(6.dp)) {
  if(kind=="crop") when(tab) {
   "比例" -> {
    FlowRow(horizontalArrangement=Arrangement.spacedBy(5.dp)){listOf("原始","1:1","3:4","4:3","9:16","16:9","2:3","3:2").forEach{r->OutlinedButton(onClick={if(r=="原始")onJs("resetSelectedImageCrop()") else {val p=r.split(":");onJs("cropSelectedImageCustom("+p[0]+","+p[1]+")")}}){Text(r,color=ink)}}}
    ImageAdjustRow("水平取景",x,0f,100f,"%"){x=it;onJs("previewSelectedImagePosition("+it+","+y+")")}
    ImageAdjustRow("垂直取景",y,0f,100f,"%"){y=it;onJs("previewSelectedImagePosition("+x+","+it+")")}
   }
   "尺寸" -> Row(verticalAlignment=Alignment.CenterVertically){OutlinedTextField(width,{width=it.filter(Char::isDigit)},Modifier.weight(1f),label={Text("宽比例")});Text(":");OutlinedTextField(height,{height=it.filter(Char::isDigit)},Modifier.weight(1f),label={Text("高比例")});Button(onClick={val w=width.toIntOrNull()?:4;val h=height.toIntOrNull()?:3;if(w>0&&h>0)onJs("cropSelectedImageCustom("+w+","+h+")")}){Text("应用")}}
   "旋转" -> {ImageAdjustRow("旋转角度",angle,-180f,180f,"°"){angle=it;onJs("previewSelectedImageTransform("+it+")")};TextButton(onClick={onJs("rotateSelectedImage()")}){Text("旋转90°")};TextButton(onClick={angle=0f;onJs("previewSelectedImageTransform(0);commitSelectedImageStyle()")}){Text("复位")}}
   "翻转" -> Row{Button(onClick={onJs("flipSelectedImage('horizontal')")}){Text("水平翻转")};Button(onClick={onJs("flipSelectedImage('vertical')")}){Text("垂直翻转")}}
   "校正" -> ImageAdjustRow("倾斜校正",angle,-15f,15f,"°"){angle=it;onJs("previewSelectedImageTransform("+it+")")}
   "辅助线" -> Text("使用水平、垂直取景滑块调整主体位置；辅助线仅作参考。")
  } else when(tab) {
   "光效" -> {ImageAdjustRow("亮度",a,0f,200f,"%"){a=it;onJs("previewSelectedImageFilters("+it+","+b+","+c+")")};ImageAdjustRow("对比度",b,0f,200f,"%"){b=it;onJs("previewSelectedImageFilters("+a+","+it+","+c+")")}}
   "色彩" -> {ImageAdjustRow("饱和度",c,0f,200f,"%"){c=it;onJs("previewSelectedImageFilters("+a+","+b+","+it+")")};ImageAdjustRow("色温/色调",angle,-100f,100f,""){angle=it;onJs("previewSelectedImageAdvanced("+a+","+b+","+c+","+it+",0,0,0,0,0,0)")}}
   "HSL" -> {Text("基础 CSS 渲染目前支持全局色彩调整；逐色相像素蒙版尚未接入，不伪装为精准 HSL。");ImageAdjustRow("色相",angle,-180f,180f,"°"){angle=it;onJs("previewSelectedImageAdvanced("+a+","+b+","+c+",0,0,"+it+",0,0,0,0)")};ImageAdjustRow("饱和度",c,0f,200f,"%"){c=it};ImageAdjustRow("明度",a,0f,200f,"%"){a=it}}
   "曲线" -> FlowRow{listOf("原始","提亮","压暗","高对比","柔和").forEach{v->TextButton(onClick={when(v){"提亮"->a=115f;"压暗"->a=85f;"高对比"->b=130f;"柔和"->{a=108f;b=88f};else->{a=100f;b=100f}};onJs("previewSelectedImageFilters("+a+","+b+","+c+")")}){Text(v)}}}
   "细节" -> {ImageAdjustRow("清晰度/对比度",b,0f,200f,"%"){b=it;onJs("previewSelectedImageFilters("+a+","+it+","+c+")")};Text("降噪、锐化和颗粒像素处理引擎尚未接入。")}
  }
  if(kind=="color")Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.End){TextButton(onClick={a=100f;b=100f;c=100f;onJs("resetSelectedImageColor()")}){Text("重置")};Button(onClick={onJs("commitSelectedImageStyle()")}){Text("应用")}}
 }
}
@Composable
private fun ImageAdjustRow(label:String,value:Float,min:Float,max:Float,suffix:String,onChange:(Float)->Unit){
 Column{Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically){Text(label,color=Color(0xFFE7E7E7),fontSize=11.sp,modifier=Modifier.weight(1f));Text(value.toInt().toString()+suffix,color=Color(0xFFAAAAAA),fontSize=10.sp)};Slider(value=value.coerceIn(min,max),onValueChange=onChange,valueRange=min..max,modifier=Modifier.height(22.dp))}
}
'''
rep('@Composable\nprivate fun EditorTool(label: String, selected: Boolean = false, onClick: () -> Unit) {',panel+'@Composable\nprivate fun EditorTool(label: String, selected: Boolean = false, onClick: () -> Unit) {')
if 'IMAGE_CROP("裁剪")' not in s or 'ImageCropColorPanel("color"' not in s: raise SystemExit("validation failed")
P.write_text(s,encoding="utf-8")
print("Crop/color panels patched")
