#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt'
s=P.read_text(encoding='utf-8')
def rep(a,b,label):
 global s
 if s.count(a)!=1: raise SystemExit(f'{label}: expected one anchor, got {s.count(a)}')
 s=s.replace(a,b,1)

rep('''    fun runJs(script: String) {
        editor?.evaluateJavascript(script) { editor?.postInvalidateOnAnimation() }
        saved = false
        pendingSave++
    }''','''    fun runJs(script: String) {
        editor?.evaluateJavascript(script) { editor?.postInvalidateOnAnimation() }
        if (!script.contains("previewSelectedImage")) {
            saved = false
            pendingSave++
        }
    }''','transient preview')
rep('''                            function syncSelectedImageLive(){
                              try{if(typeof NativeEditor!=='undefined'&&NativeEditor.changed)NativeEditor.changed(root.innerHTML);}catch(e){}
                              try{if(typeof notifyCanvasPreview==='function')notifyCanvasPreview();}catch(e){}
                            }''','''                            function syncSelectedImageLive(){
                              try{if(typeof notifyCanvasPreview==='function')notifyCanvasPreview();}catch(e){}
                            }''','preview only sync')

old="function commitSelectedImageStyle(){if(!activeImage||activeImage.dataset.editorLocked==='1')return;commitHistory();NativeEditor.changed(root.innerHTML);}"
new="function commitSelectedImageStyle(){const el=selectedImageTarget();if(!el)return;try{if(typeof commitHistory==='function')commitHistory();}catch(e){}try{if(typeof NativeEditor!=='undefined'&&typeof NativeEditor.changed==='function')NativeEditor.changed(root.innerHTML);}catch(e){}syncSelectedImageLive();}"
i=s.rfind(old)
if i<0: raise SystemExit('final image commit anchor missing')
s=s[:i]+new+s[i+len(old):]

full='''
                            let imageColorCommitTimer=null;
                            function scheduleImageColorCommit(){if(imageColorCommitTimer)clearTimeout(imageColorCommitTimer);imageColorCommitTimer=setTimeout(()=>{imageColorCommitTimer=null;commitSelectedImageStyle();},360);}
                            function previewSelectedImageFull(b,c,sat,ev,hi,sh,temp,tint,vib,hue,gray,sepia,blur){
                              const el=selectedImageTarget();if(!el)return;const n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
                              const bright=Math.max(0,Math.min(300,n(b,100)*Math.pow(2,n(ev))*(1+n(sh)/650+n(hi)/1400)));
                              const cont=Math.max(0,Math.min(300,n(c,100)*(1-n(hi)/550)));
                              const satv=Math.max(0,Math.min(300,n(sat,100)*(1+n(vib)/150)));
                              el.dataset.colorBrightness=String(n(b,100));el.dataset.colorContrast=String(n(c,100));el.dataset.colorSaturation=String(n(sat,100));
                              el.dataset.colorExposure=String(n(ev));el.dataset.colorHighlights=String(n(hi));el.dataset.colorShadows=String(n(sh));el.dataset.colorTemperature=String(n(temp));el.dataset.colorTint=String(n(tint));el.dataset.colorVibrance=String(n(vib));el.dataset.colorHue=String(n(hue));el.dataset.colorGrayscale=String(n(gray));el.dataset.colorSepia=String(n(sepia));el.dataset.colorBlur=String(n(blur));
                              el.style.filter='brightness('+bright+'%) contrast('+cont+'%) saturate('+satv+'%) hue-rotate('+(n(hue)+n(tint)*.12)+'deg) sepia('+Math.max(0,Math.min(100,n(sepia)+Math.abs(n(temp))*.22))+'%) grayscale('+Math.max(0,Math.min(100,n(gray)))+'%) blur('+Math.max(0,Math.min(8,n(blur)))+'px)';
                              syncSelectedImageLive();scheduleImageColorCommit();
                            }
'''
s=s.replace(new,new+full,1)

rep('''private fun ImageCropColorPanel(kind: String, tab: String, onJs: (String) -> Unit) {''','''private fun ImageCropColorPanel(kind: String, tab: String, onJs: (String) -> Unit, onPixelCrop: (Float) -> Unit = {}, onCustomCrop: () -> Unit = {}) {''','crop panel callback')
rep('''                    EditorPanel.IMAGE_CROP -> ImageCropColorPanel("crop", imageCropMainTab, { runJs(it) })''','''                    EditorPanel.IMAGE_CROP -> ImageCropColorPanel("crop", imageCropMainTab, { runJs(it) }, { cropSelectedImagePixels(it) }, { openCustomImageCrop() })''','crop panel call')
rep('''    FlowRow(horizontalArrangement=Arrangement.spacedBy(5.dp)){listOf("原始","1:1","3:4","4:3","9:16","16:9","2:3","3:2").forEach{r->OutlinedButton(onClick={if(r=="原始")onJs("resetSelectedImageCrop()") else {val p=r.split(":");onJs("cropSelectedImageCustom("+p[0]+","+p[1]+")")}}){Text(r,color=ink)}}}''','''    FlowRow(horizontalArrangement=Arrangement.spacedBy(5.dp)){listOf("原始","1:1","3:4","4:3","9:16","16:9","2:3","3:2").forEach{r->OutlinedButton(onClick={if(r=="原始")onJs("resetSelectedImageCrop();commitSelectedImageStyle()") else {val p=r.split(":");onJs("cropSelectedImageCustom("+p[0]+","+p[1]+");commitSelectedImageStyle()")}}){Text(r,color=ink)}}}
    Text("像素裁剪（生成新图片，不覆盖原图）",color=ink,fontSize=12.sp)
    FlowRow(horizontalArrangement=Arrangement.spacedBy(4.dp)){listOf("1:1" to 1f,"4:3" to (4f/3f),"3:4" to (3f/4f),"16:9" to (16f/9f),"9:16" to (9f/16f)).forEach{(label,ratio)->TextButton(onClick={onPixelCrop(ratio)}){Text(label,color=AppColors.Theme)}};TextButton(onClick=onCustomCrop){Text("自定义像素裁剪",color=AppColors.Theme)}}''','pixel crop buttons')

rep(''' var a by remember { mutableFloatStateOf(100f) }; var b by remember { mutableFloatStateOf(100f) }; var c by remember { mutableFloatStateOf(100f) }
 var angle by remember { mutableFloatStateOf(0f) }; var x by remember { mutableFloatStateOf(50f) }; var y by remember { mutableFloatStateOf(50f) }''',''' var a by remember { mutableFloatStateOf(100f) }; var b by remember { mutableFloatStateOf(100f) }; var c by remember { mutableFloatStateOf(100f) }
 var angle by remember { mutableFloatStateOf(0f) }; var x by remember { mutableFloatStateOf(50f) }; var y by remember { mutableFloatStateOf(50f) }
 var exposure by remember { mutableFloatStateOf(0f) }; var highlights by remember { mutableFloatStateOf(0f) }; var shadows by remember { mutableFloatStateOf(0f) }
 var tint by remember { mutableFloatStateOf(0f) }; var vibrance by remember { mutableFloatStateOf(0f) }; var hue by remember { mutableFloatStateOf(0f) }
 var gray by remember { mutableFloatStateOf(0f) }; var sepia by remember { mutableFloatStateOf(0f) }; var blur by remember { mutableFloatStateOf(0f) }
 fun previewFull() = onJs("previewSelectedImageFull("+a+","+b+","+c+","+exposure+","+highlights+","+shadows+","+angle+","+tint+","+vibrance+","+hue+","+gray+","+sepia+","+blur+")")''','color panel state')
rep('''   "光效" -> {ImageAdjustRow("亮度",a,0f,200f,"%"){a=it;onJs("previewSelectedImageFilters("+it+","+b+","+c+")")};ImageAdjustRow("对比度",b,0f,200f,"%"){b=it;onJs("previewSelectedImageFilters("+a+","+it+","+c+")")}}''','''   "光效" -> {ImageAdjustRow("亮度",a,0f,200f,"%"){a=it;previewFull()};ImageAdjustRow("曝光",exposure,-3f,3f,"EV"){exposure=it;previewFull()};ImageAdjustRow("对比度",b,0f,200f,"%"){b=it;previewFull()};ImageAdjustRow("高光",highlights,-100f,100f,""){highlights=it;previewFull()};ImageAdjustRow("阴影",shadows,-100f,100f,""){shadows=it;previewFull()}}''','light controls')
rep('''   "色彩" -> {ImageAdjustRow("饱和度",c,0f,200f,"%"){c=it;onJs("previewSelectedImageFilters("+a+","+b+","+it+")")};ImageAdjustRow("色温/色调",angle,-100f,100f,""){angle=it;onJs("previewSelectedImageAdvanced("+a+","+b+","+c+","+it+",0,0,0,0,0,0)")}}''','''   "色彩" -> {ImageAdjustRow("色温",angle,-100f,100f,""){angle=it;previewFull()};ImageAdjustRow("色调",tint,-100f,100f,""){tint=it;previewFull()};ImageAdjustRow("自然饱和度",vibrance,-100f,100f,""){vibrance=it;previewFull()};ImageAdjustRow("饱和度",c,0f,200f,"%"){c=it;previewFull()};ImageAdjustRow("色相",hue,-180f,180f,"°"){hue=it;previewFull()};ImageAdjustRow("褪色/棕褐",sepia,0f,100f,"%"){sepia=it;previewFull()};ImageAdjustRow("黑白",gray,0f,100f,"%"){gray=it;previewFull()}}''','color controls')
rep('''   "HSL" -> {Text("基础 CSS 渲染目前支持全局色彩调整；逐色相像素蒙版尚未接入，不伪装为精准 HSL。");ImageAdjustRow("色相",angle,-180f,180f,"°"){angle=it;onJs("previewSelectedImageAdvanced("+a+","+b+","+c+",0,0,"+it+",0,0,0,0)")};ImageAdjustRow("饱和度",c,0f,200f,"%"){c=it};ImageAdjustRow("明度",a,0f,200f,"%"){a=it}}''','''   "HSL" -> {Text("当前为全局 HSL；八色独立蒙版需后续像素级处理。",color=Color(0xFFAAAAAA),fontSize=10.sp);ImageAdjustRow("色相",hue,-180f,180f,"°"){hue=it;previewFull()};ImageAdjustRow("饱和度",c,0f,200f,"%"){c=it;previewFull()};ImageAdjustRow("明度",a,0f,200f,"%"){a=it;previewFull()}}''','HSL controls')

s=s.replace('80_000_000L','48_000_000L').replace('> 20_000_000L) sample *= 2','> 12_000_000L) sample *= 2')
if 'previewSelectedImageFull' not in s or 'onPixelCrop' not in s:
    raise SystemExit('image crop/color validation failed')
P.write_text(s,encoding='utf-8')
print('Image crop/color controls upgraded.')
