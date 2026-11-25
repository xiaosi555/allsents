package com.shiwanju.app.ui
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shiwanju.app.data.ArticleDocument
import com.shiwanju.app.data.MediaAsset
import com.shiwanju.app.data.StyleModule
import org.json.JSONArray
import org.json.JSONObject

private enum class XiumiDock(val label:String,val icon:String) {
 THEME("主题","◉"), TITLE("标题","T"), TEXT("文字","文"), IMAGE("图片","▧"), LAYOUT("布局","▦"),
 CARD("卡片","▤"), SVG("SVG","◇"), COMPONENT("组件","⊞"), TEMPLATE("模板","▣"), FAVORITE("收藏","♡")
}
private data class XiumiMaterial(val name:String,val detail:String,val value:String)
private data class XiumiBlock(
 val id:String,val type:String,val content:String,
 val fontSize:Float=16f,val lineSpace:Float=1.8f,val bold:Boolean=false,val align:String="左对齐",
 val color:Long=0xFF333333,val padding:Float=8f,val border:Float=0f,val radius:Float=0f
)
private fun classifyXiumiBlock(value:String):String = when {
 value.trimStart().startsWith("<img") || value.startsWith("![") || value.startsWith("［图片") -> "图片"
 value.contains("卡片") || value.startsWith("▧") || value.startsWith("▢") -> "卡片"
 value.contains("［点击展开］") || value.contains("［卡片") -> "SVG"
 value.contains("关注公众号") || value.contains("文 /") -> "组件"
 value.startsWith("【") || value.startsWith("#") || value.startsWith("01 ") -> "标题"
 else -> "正文"
}
private fun readXiumiBlocks(context:android.content.Context,articleId:String,body:String,newId:()->String):List<XiumiBlock> {
 val raw=context.getSharedPreferences("xiumi_editor",android.content.Context.MODE_PRIVATE).getString("blocks_$articleId",null)
 if(!raw.isNullOrBlank()) runCatching {
  val array=JSONArray(raw)
  return (0 until array.length()).mapNotNull { i -> array.optJSONObject(i)?.let { o ->
   XiumiBlock(o.optString("id",newId()),o.optString("type","正文"),o.optString("content"),
    o.optDouble("fontSize",16.0).toFloat(),o.optDouble("lineSpace",1.8).toFloat(),o.optBoolean("bold"),
    o.optString("align","左对齐"),o.optLong("color",0xFF333333),o.optDouble("padding",8.0).toFloat(),
    o.optDouble("border",0.0).toFloat(),o.optDouble("radius",0.0).toFloat())
  } }
 }.onFailure { android.util.Log.w("XiumiEditor","读取组件数据失败",it) }
 return body.split("\n\n").filter { it.isNotBlank() }.map { XiumiBlock(newId(),classifyXiumiBlock(it),it) }
}
private fun writeXiumiBlocks(context:android.content.Context,articleId:String,blocks:List<XiumiBlock>) {
 val array=JSONArray()
 blocks.forEach { b -> array.put(JSONObject().put("id",b.id).put("type",b.type).put("content",b.content)
  .put("fontSize",b.fontSize.toDouble()).put("lineSpace",b.lineSpace.toDouble()).put("bold",b.bold)
  .put("align",b.align).put("color",b.color).put("padding",b.padding.toDouble())
  .put("border",b.border.toDouble()).put("radius",b.radius.toDouble())) }
 context.getSharedPreferences("xiumi_editor",android.content.Context.MODE_PRIVATE).edit().putString("blocks_$articleId",array.toString()).apply()
}


@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun XiumiArticleLayoutScreen(vm: AppViewModel, onBack: () -> Unit) {
 val context = LocalContext.current
 val compact = LocalConfiguration.current.screenWidthDp < 600
 val initial=remember { vm.data.articles.maxByOrNull { it.updatedAt } }
 var currentArticle by remember { mutableStateOf(initial) }
 var id by remember { mutableStateOf(initial?.id ?: vm.newId()) }
 var title by remember { mutableStateOf(initial?.title.orEmpty()) }
 var subtitle by remember { mutableStateOf(initial?.subtitle.orEmpty()) }
 var author by remember { mutableStateOf(initial?.author?.ifBlank { "拾万句" } ?: "拾万句") }
 var body by remember { mutableStateOf(initial?.html.orEmpty()) }
 var blocks by remember { mutableStateOf(readXiumiBlocks(context,initial?.id ?: "new",initial?.html.orEmpty(),vm::newId)) }
 var selectedBlockId by remember { mutableStateOf("") }
 var dock by remember { mutableStateOf(XiumiDock.TITLE) }
 var selected by remember { mutableStateOf("正文") }
 var search by remember { mutableStateOf("") }
 var preview by remember { mutableStateOf(false) }
 var properties by remember { mutableStateOf(!compact) }
 var zoom by remember { mutableFloatStateOf(1f) }
 var showArticlePicker by remember { mutableStateOf(false) }
 var showImageInsert by remember { mutableStateOf(false) }
 var showLayers by remember { mutableStateOf(false) }
 var selectedSnippet by remember { mutableStateOf("") }
 var showBlockEditor by remember { mutableStateOf(false) }
 var blockDraft by remember { mutableStateOf("") }
 var selectedType by remember { mutableStateOf("正文") }
 var showMaterialPreview by remember { mutableStateOf<XiumiMaterial?>(null) }
 var favoriteMaterials by remember { mutableStateOf(setOf<String>()) }
 var importedMaterials by remember { mutableStateOf(listOf<XiumiMaterial>()) }
 var foreground by remember { mutableStateOf(Color(0xFF333333)) }
 var canvasBackground by remember { mutableStateOf(Color.White) }
 var contentPadding by remember { mutableFloatStateOf(28f) }
 var borderWidth by remember { mutableFloatStateOf(1f) }
 var cornerRadius by remember { mutableFloatStateOf(3f) }
 val clipboard = LocalClipboardManager.current
 val importLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
  if(uri!=null) runCatching { context.contentResolver.openInputStream(uri)?.bufferedReader()?.use { it.readText() } }.getOrNull()?.let { imported ->
   val name=uri.lastPathSegment?.substringAfterLast('/')?.substringBeforeLast('.')?.ifBlank { "导入素材" } ?: "导入素材"
   importedMaterials=importedMaterials+XiumiMaterial(name,"导入文件 · ${imported.length} 字",imported)
  }
 }
 val exportLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/plain")) { uri ->
  if(uri!=null) runCatching { context.contentResolver.openOutputStream(uri)?.bufferedWriter()?.use { it.write("# ${title}\n\n${subtitle}\n\n${body}") } }
 }
 var imageUrl by remember { mutableStateOf("") }
 var imageAlt by remember { mutableStateOf("") }
 var dirty by remember { mutableStateOf(false) }
 var accent by remember { mutableStateOf(Color(0xFF16A36A)) }
 var fontSize by remember { mutableFloatStateOf(16f) }
 var lineSpace by remember { mutableFloatStateOf(1.8f) }
 var bold by remember { mutableStateOf(false) }
 var align by remember { mutableStateOf("左对齐") }
 var undo by remember { mutableStateOf(listOf("")) }
 var redo by remember { mutableStateOf(emptyList<String>()) }
 fun save() {
  val now=System.currentTimeMillis().toString()
  val saved = ArticleDocument(id=id,title=title.ifBlank { "未命名文章" },html=body,createdAt=currentArticle?.createdAt ?: now,
   updatedAt=now,subtitle=subtitle,summary=currentArticle?.summary.orEmpty(),author=author,coverAssetId=currentArticle?.coverAssetId.orEmpty(),
   category=currentArticle?.category.orEmpty(),tags=currentArticle?.tags ?: emptyList(),status="draft",wordCount=(title+subtitle+body).length,
   isFavorite=currentArticle?.isFavorite ?: false)
  vm.saveArticle(saved)
  writeXiumiBlocks(context,id,blocks)
  currentArticle = saved
  dirty=false
 }
 fun changeBody(value:String) {
  if(value==body) return
  val old=blocks.toMutableList()
  val next=value.split("\n\n").filter { it.isNotBlank() }.map { chunk ->
   val match=old.firstOrNull { it.content==chunk }
   if(match!=null) { old.remove(match); match } else XiumiBlock(vm.newId(),classifyXiumiBlock(chunk),chunk)
  }
  undo=(undo+body).takeLast(50); redo=emptyList()
  blocks=next; body=value; selectedSnippet=next.firstOrNull { it.id==selectedBlockId }?.content.orEmpty()
  dirty=true
 }
 fun syncBlocks(next:List<XiumiBlock>) {
  undo=(undo+body).takeLast(50); redo=emptyList()
  blocks=next; body=next.joinToString("\n\n") { it.content }
  selectedSnippet=next.firstOrNull { it.id==selectedBlockId }?.content.orEmpty()
  dirty=true
 }
 fun insert(value:String) {
  val block=XiumiBlock(vm.newId(),classifyXiumiBlock(value),value)
  syncBlocks(blocks+block); selectedBlockId=block.id; selected="内容组件"; selectedSnippet=value
 }
 fun editSelected(transform:(String)->String) {
  val index=blocks.indexOfFirst { it.id==selectedBlockId }; if(index<0) return
  val next=blocks.toMutableList(); val content=transform(next[index].content)
  next[index]=next[index].copy(content=content,type=classifyXiumiBlock(content)); syncBlocks(next); selectedSnippet=content
 }
 fun moveSelected(delta:Int) {
  val index=blocks.indexOfFirst { it.id==selectedBlockId }; val target=index+delta
  if(index<0 || target !in blocks.indices) return
  val next=blocks.toMutableList(); val item=next.removeAt(index); next.add(target,item); syncBlocks(next)
 }
 fun updateSelectedBlock(transform:(XiumiBlock)->XiumiBlock) {
  val index=blocks.indexOfFirst { it.id==selectedBlockId }; if(index<0) return
  val next=blocks.toMutableList(); next[index]=transform(next[index]); blocks=next; dirty=true
 }
 BackHandler { if(dirty) save(); onBack() }
 val materials=remember(dock,vm.data.styles,importedMaterials,favoriteMaterials) {
  when(dock) {
   XiumiDock.TITLE -> listOf(XiumiMaterial("大标题","醒目章节标题","【大标题】"),XiumiMaterial("编号标题","序号标题","01  【章节标题】"),XiumiMaterial("色块标题","带底色标题","▰  【标题文字】"))
   XiumiDock.TEXT -> listOf(XiumiMaterial("正文段落","标准文字段落","在这里输入正文内容。"),XiumiMaterial("引用","引用与出处","“在这里输入引用内容。”\n—— 来源"),XiumiMaterial("分割线","段落分隔","━━━━━━━━━━━━"),XiumiMaterial("注释","小字说明","注：补充说明。"))
   XiumiDock.IMAGE -> listOf(XiumiMaterial("单图","图片占位","［图片：点击替换］"),XiumiMaterial("双图","左右双图","［图片 1］　　　［图片 2］"),XiumiMaterial("图文混排","图文组合","［图片］\n图片说明文字。"))
   XiumiDock.LAYOUT -> listOf(XiumiMaterial("双栏布局","两列内容","［左栏内容］　　　［右栏内容］"),XiumiMaterial("三栏布局","三列内容","［一］　［二］　［三］"),XiumiMaterial("图文卡片","图文组合卡片","［图片］\n【卡片标题】\n卡片正文"),XiumiMaterial("留白","段落留白","\n\n"))
   XiumiDock.CARD -> listOf(XiumiMaterial("灰底卡片","浅灰内容块","▧ 【卡片标题】\n卡片正文内容"),XiumiMaterial("边框卡片","描边内容块","▢ 【卡片标题】\n卡片正文内容"),XiumiMaterial("强调卡片","重点提示","✦ 重点提示：输入内容。"))
   XiumiDock.SVG -> listOf(XiumiMaterial("展开阅读","点击展开内容","［点击展开］\n展开后的详细内容"),XiumiMaterial("横向滑动","横向卡片组","［卡片 1］　［卡片 2］　［卡片 3］"),XiumiMaterial("步骤组件","步骤序列","01  第一步\n02  第二步\n03  第三步"))
   XiumiDock.COMPONENT -> listOf(XiumiMaterial("关注引导","公众号关注提示","关注公众号｜拾万句"),XiumiMaterial("作者信息","作者署名","文 / 拾万句"),XiumiMaterial("二维码","二维码占位","［二维码图片］"))
   XiumiDock.TEMPLATE -> listOf(XiumiMaterial("简约文章","标题、正文、引用","【文章标题】\n\n导语内容\n\n正文内容\n\n“引用内容”"),XiumiMaterial("清新图文","图片与正文","【图文标题】\n［封面图片］\n\n正文内容"),XiumiMaterial("知识卡片","知识点卡片","01｜知识点标题\n知识点解释")) + importedMaterials + importedMaterials
   XiumiDock.THEME -> listOf(XiumiMaterial("薄荷绿","清新绿色","mint"),XiumiMaterial("暖阳橙","温暖橙色","orange"),XiumiMaterial("海盐蓝","清爽蓝色","blue"))
   XiumiDock.FAVORITE -> (vm.data.styles.map { XiumiMaterial(it.name,it.category,it.html) } + importedMaterials).filter { it.name in favoriteMaterials }
  }
 }
 Column(Modifier.fillMaxSize().background(Color(0xFFF2F3F4))) {
  Row(Modifier.fillMaxWidth().height(54.dp).background(Color.White).padding(horizontal=8.dp),verticalAlignment=Alignment.CenterVertically) {
   IconButton(onClick={if(dirty) save();onBack()}) { Icon(Icons.Outlined.ArrowBack,contentDescription="返回") }
   Column(Modifier.weight(1f)) { Text("秀米式图文排版",fontSize=16.sp,fontWeight=FontWeight.SemiBold); Text(if(dirty) "未保存" else "编辑器",fontSize=10.sp,color=Color.Gray) }
   TextButton(onClick={showArticlePicker=true}) { Text("文章") }
   TextButton(onClick={
    currentArticle=null; id=vm.newId(); title=""; subtitle=""; author="拾万句"; body=""
    undo=listOf(""); redo=emptyList(); dirty=true; preview=false
   }) { Text("新建") }
   TextButton(onClick={preview=!preview}) { Text(if(preview) "编辑" else "预览") }
   TextButton(onClick={exportLauncher.launch("${title.ifBlank { "文章" }}.txt")}) { Text("导出") }
   TextButton(onClick={ { save() } }) { Text("保存",color=accent,fontWeight=FontWeight.Bold) }
   TextButton(onClick={properties=!properties}) { Text("属性") }
  }
  Row(Modifier.weight(1f).fillMaxWidth()) {
   Column(Modifier.width(if(compact) 48.dp else 64.dp).fillMaxHeight().background(Color(0xFFFAFAFA)).verticalScroll(rememberScrollState()).padding(horizontal=4.dp, vertical=8.dp),horizontalAlignment=Alignment.CenterHorizontally) {
    XiumiDock.entries.forEach { item ->
     val active=dock==item
     Column(Modifier.fillMaxWidth().padding(horizontal=4.dp,vertical=2.dp).clip(RoundedCornerShape(8.dp)).background(if(active) accent.copy(alpha=.12f) else Color.Transparent)
      .clickable { dock=item;search="" }.padding(vertical=8.dp),horizontalAlignment=Alignment.CenterHorizontally) {
      Text(item.icon,fontSize=19.sp,color=if(active) accent else Color.DarkGray); Text(item.label,fontSize=10.sp,color=if(active) accent else Color.DarkGray)
     }
    }
   }
   Column(Modifier.width(if(compact) 116.dp else 224.dp).fillMaxHeight().background(Color.White).padding(horizontal=if(compact) 7.dp else 12.dp, vertical=12.dp)) {
    Row(verticalAlignment=Alignment.CenterVertically) { Text("素材中心",fontSize=14.sp,fontWeight=FontWeight.Bold,color=Color(0xFF292D31),modifier=Modifier.weight(1f)); Text("导入＋",fontSize=10.sp,color=accent,modifier=Modifier.clickable { importLauncher.launch(arrayOf("text/plain","text/markdown","text/html")) }) }
    Text(dock.label,fontSize=10.sp,color=accent,modifier=Modifier.padding(top=3.dp,bottom=8.dp))
    OutlinedTextField(search,{search=it},Modifier.fillMaxWidth().heightIn(min=42.dp),singleLine=true,placeholder={Text("搜索",fontSize=11.sp)},textStyle=LocalTextStyle.current.copy(fontSize=11.sp),shape=RoundedCornerShape(7.dp))
    Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(top=8.dp)) {
     materials.filter { search.isBlank() || it.name.contains(search) || it.detail.contains(search) }.forEach { material ->
      Column(Modifier.fillMaxWidth().padding(bottom=7.dp).clip(RoundedCornerShape(8.dp)).background(Color(0xFFF5F6F6)).clickable {
       if(dock==XiumiDock.THEME) accent=when(material.value) { "orange"->Color(0xFFE58B45); "blue"->Color(0xFF4D91C7); else->Color(0xFF16A36A) } else showMaterialPreview=material
      }.padding(9.dp)) {
       Row(verticalAlignment=Alignment.CenterVertically) { Text(material.name,fontSize=12.sp,fontWeight=FontWeight.SemiBold,modifier=Modifier.weight(1f)); Text(if(material.name in favoriteMaterials) "♥" else "♡",fontSize=15.sp,color=accent,modifier=Modifier.clickable { favoriteMaterials=if(material.name in favoriteMaterials) favoriteMaterials-material.name else favoriteMaterials+material.name }) }
       Text(material.detail,fontSize=10.sp,color=Color.Gray)
       if(dock!=XiumiDock.THEME) Text("＋ 添加",fontSize=10.sp,color=accent,modifier=Modifier.padding(top=4.dp))
      }
     }
     if(materials.isEmpty()) Text("暂无收藏素材",fontSize=11.sp,color=Color.Gray)
    }
   }
   Column(Modifier.weight(1f).fillMaxHeight().background(Color(0xFFEDEFF1)).verticalScroll(rememberScrollState()).padding(horizontal=if(compact) 6.dp else 18.dp, vertical=10.dp),horizontalAlignment=Alignment.CenterHorizontally) {
    Row(Modifier.fillMaxWidth().height(42.dp).background(Color.White, RoundedCornerShape(8.dp)).padding(horizontal=12.dp),verticalAlignment=Alignment.CenterVertically) {
     Text("正文画布",fontSize=12.sp,fontWeight=FontWeight.SemiBold,color=Color(0xFF42464A))
     Spacer(Modifier.weight(1f))
     Text("−",fontSize=18.sp,color=Color.Gray,modifier=Modifier.clickable { zoom=(zoom-.1f).coerceAtLeast(.6f) }.padding(horizontal=5.dp))
     Text("${(zoom*100).toInt()}%",fontSize=10.sp,color=Color.Gray)
     Text("＋",fontSize=18.sp,color=Color.Gray,modifier=Modifier.clickable { zoom=(zoom+.1f).coerceAtMost(1.4f) }.padding(horizontal=5.dp))
     Text("适宽",fontSize=10.sp,color=accent,modifier=Modifier.clickable { zoom=1f }.padding(start=6.dp))
    }
    if(selectedBlockId.isNotBlank() && !preview) Row(
     Modifier.fillMaxWidth().padding(top=7.dp).clip(RoundedCornerShape(8.dp)).background(Color.White).padding(horizontal=8.dp,vertical=6.dp),
     verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(8.dp)
    ) {
     Text("已选 · $selected",fontSize=10.sp,color=accent,modifier=Modifier.weight(1f),maxLines=1)
     listOf("上移","下移","复制","删除").forEach { action ->
      Text(action,fontSize=10.sp,color=if(action=="删除") Color(0xFFCC5555) else Color.DarkGray,
       modifier=Modifier.clickable {
        when(action) {
         "上移" -> moveSelected(-1)
         "下移" -> moveSelected(1)
         "复制" -> insert(selectedSnippet)
         "删除" -> { editSelected { "" }; selectedSnippet=""; selected="正文" }
        }
       }.padding(horizontal=4.dp,vertical=3.dp))
     }
    }
    Column(Modifier.fillMaxWidth(if(compact) .98f else .88f).widthIn(max=(760f*zoom).dp).padding(vertical=8.dp).background(canvasBackground, RoundedCornerShape(cornerRadius.dp)).border(borderWidth.dp,Color(0xFFE1E3E5),RoundedCornerShape(cornerRadius.dp)).padding(contentPadding.dp)) {
     if(!preview) {
      Text("文章信息",fontSize=10.sp,color=Color.LightGray)
      OutlinedTextField(title,{title=it;dirty=true},Modifier.fillMaxWidth(),placeholder={Text("请输入文章标题")},textStyle=LocalTextStyle.current.copy(fontSize=21.sp,fontWeight=FontWeight.Bold))
      OutlinedTextField(subtitle,{subtitle=it;dirty=true},Modifier.fillMaxWidth(),placeholder={Text("摘要 / 导语（可选）")},textStyle=LocalTextStyle.current.copy(fontSize=13.sp),minLines=2)
      Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
       Text("文 /",fontSize=11.sp,color=Color.Gray); Spacer(Modifier.width(6.dp))
       BasicTextField(author,{author=it;dirty=true},Modifier.weight(1f),textStyle=LocalTextStyle.current.copy(fontSize=12.sp,color=Color.DarkGray))
       Text("封面 ＋",fontSize=11.sp,color=accent,modifier=Modifier.clickable { dock=XiumiDock.IMAGE })
      }
      Divider(Modifier.padding(vertical=12.dp))
      Row(Modifier.fillMaxWidth().padding(bottom=8.dp),horizontalArrangement=Arrangement.spacedBy(5.dp),verticalAlignment=Alignment.CenterVertically) {
       Text("正文内容",fontSize=10.sp,color=Color.LightGray,modifier=Modifier.weight(1f))
       listOf("B","居中","引用","分割线","图片").forEach { tool ->
        Text(tool,fontSize=10.sp,fontWeight=if(tool=="B") FontWeight.Bold else FontWeight.Normal,
         color=accent,modifier=Modifier.clip(RoundedCornerShape(5.dp)).background(accent.copy(alpha=.08f)).clickable {
          when(tool) {
           "B" -> bold=!bold
           "居中" -> align=if(align=="居中") "左对齐" else "居中"
           "引用" -> insert("“在这里输入引用内容。”\n—— 来源")
           "分割线" -> insert("━━━━━━━━━━━━━━━━")
           "图片" -> showImageInsert=true
          }
         }.padding(horizontal=7.dp,vertical=5.dp))
       }
      }
      OutlinedTextField(body,{changeBody(it)},Modifier.fillMaxWidth().defaultMinSize(minHeight=300.dp),placeholder={Text("从左侧选择素材添加内容，也可直接输入正文。")},
       textStyle=LocalTextStyle.current.copy(fontSize=fontSize.sp,lineHeight=(fontSize*lineSpace).sp,color=foreground,fontWeight=if(bold) FontWeight.Bold else FontWeight.Normal,
        textAlign=when(align) { "居中"->TextAlign.Center; "右对齐"->TextAlign.End; else->TextAlign.Start }),minLines=14)
     } else {
      Text(title.ifBlank { "未命名文章" },fontSize=23.sp,fontWeight=FontWeight.Bold,color=Color(0xFF222222))
      if(subtitle.isNotBlank()) Text(subtitle,fontSize=13.sp,color=Color.Gray,modifier=Modifier.padding(top=8.dp))
      Text("文 / $author",fontSize=11.sp,color=Color.Gray,modifier=Modifier.padding(vertical=12.dp))
      Text(body.ifBlank { "正文预览将在这里显示。" },fontSize=fontSize.sp,lineHeight=(fontSize*lineSpace).sp,color=foreground)
     }
     Spacer(Modifier.height(32.dp))
    }
   }
   if(properties && !compact) Column(Modifier.width(if(LocalConfiguration.current.screenWidthDp < 900) 184.dp else 224.dp).fillMaxHeight().background(Color.White).verticalScroll(rememberScrollState()).padding(horizontal=14.dp, vertical=14.dp)) {
    Text("属性面板",fontSize=14.sp,fontWeight=FontWeight.Bold,color=Color(0xFF292D31)); Text("当前对象 · $selected",fontSize=10.sp,color=Color.Gray,modifier=Modifier.padding(vertical=10.dp)); Divider()
    Text("字号 ${fontSize.toInt()} px",fontSize=11.sp,modifier=Modifier.padding(top=10.dp)); Slider(fontSize,{fontSize=it},valueRange=12f..32f)
    Text("行间距 ${"%.1f".format(lineSpace)}",fontSize=11.sp); Slider(lineSpace,{lineSpace=it},valueRange=1.2f..2.6f)
    FilterChip(bold,{bold=!bold},{Text("粗体",fontSize=10.sp)})
    Text("对齐方式",fontSize=11.sp,modifier=Modifier.padding(top=10.dp))
    listOf("左对齐","居中","右对齐").forEach { option -> Text(option,fontSize=11.sp,color=if(align==option) accent else Color.Gray,modifier=Modifier.fillMaxWidth().clickable { align=option }.padding(vertical=6.dp)) }
    Text("文字颜色",fontSize=11.sp,modifier=Modifier.padding(top=10.dp,bottom=6.dp))
    Row(horizontalArrangement=Arrangement.spacedBy(5.dp)) { listOf(Color(0xFF222222),Color(0xFF666666),Color(0xFF16A36A),Color(0xFFE58B45),Color(0xFF4D91C7),Color(0xFFBD6B91)).forEach { c -> Box(Modifier.size(21.dp).clip(RoundedCornerShape(50)).background(c).clickable { foreground=c }) } }
    Text("画布背景",fontSize=11.sp,modifier=Modifier.padding(top=10.dp,bottom=6.dp))
    Row(horizontalArrangement=Arrangement.spacedBy(5.dp)) { listOf(Color.White,Color(0xFFFFFBF2),Color(0xFFF4F7F6),Color(0xFFF3F3F3)).forEach { c -> Box(Modifier.size(21.dp).clip(RoundedCornerShape(5.dp)).background(c).border(1.dp,Color.LightGray,RoundedCornerShape(5.dp)).clickable { canvasBackground=c }) } }
    Text("内边距 ${contentPadding.toInt()} dp",fontSize=11.sp,modifier=Modifier.padding(top=8.dp)); Slider(contentPadding,{contentPadding=it},valueRange=12f..40f)
    Text("边框 ${borderWidth.toInt()} dp",fontSize=11.sp); Slider(borderWidth,{borderWidth=it},valueRange=0f..3f)
    Text("圆角 ${cornerRadius.toInt()} dp",fontSize=11.sp); Slider(cornerRadius,{cornerRadius=it},valueRange=0f..18f)
   }
  }
  if(showArticlePicker) AlertDialog(
   onDismissRequest={showArticlePicker=false},
   title={Text("选择文章")},
   text={
    Column(Modifier.heightIn(max=420.dp).verticalScroll(rememberScrollState())) {
     vm.data.articles.sortedByDescending { it.updatedAt }.forEach { article ->
      Column(Modifier.fillMaxWidth().clickable {
       currentArticle=article; id=article.id; title=article.title; subtitle=article.subtitle; author=article.author
       body=article.html; dirty=false; undo=listOf(""); redo=emptyList(); selectedSnippet=""; selected="正文"; showArticlePicker=false; preview=false
      }.padding(vertical=10.dp)) {
       Text(article.title.ifBlank { "未命名文章" },fontSize=13.sp,fontWeight=FontWeight.SemiBold)
       Text(article.updatedAt,fontSize=10.sp,color=Color.Gray)
      }
      Divider()
     }
     if(vm.data.articles.isEmpty()) Text("暂无已保存文章",fontSize=12.sp,color=Color.Gray)
    }
   },
   confirmButton={TextButton(onClick={showArticlePicker=false}) { Text("关闭") }}
  )
  if(showLayers) AlertDialog(
   onDismissRequest={showLayers=false},
   title={Text("图层 / 内容结构")},
   text={
    Column(Modifier.heightIn(max=420.dp).verticalScroll(rememberScrollState())) {
     if(blocks.isEmpty()) Text("画布中还没有内容组件",fontSize=12.sp,color=Color.Gray)
     blocks.forEachIndexed { index, block ->
      Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(7.dp)).background(if(block.id==selectedBlockId) accent.copy(alpha=.10f) else Color.Transparent)
       .clickable { selectedBlockId=block.id; selectedSnippet=block.content; selectedType=block.type; selected=block.type; fontSize=block.fontSize; lineSpace=block.lineSpace; bold=block.bold; align=block.align; foreground=Color(block.color); contentPadding=block.padding; borderWidth=block.border; cornerRadius=block.radius; showLayers=false; blockDraft=block.content; showBlockEditor=true }.padding(9.dp),
       verticalAlignment=Alignment.CenterVertically) {
       Text("\${index+1}",fontSize=10.sp,color=Color.Gray,modifier=Modifier.width(22.dp))
       Text(block.content.replace("\n"," / "),fontSize=11.sp,maxLines=2,modifier=Modifier.weight(1f))
       if(block.id==selectedBlockId) Text("选中",fontSize=10.sp,color=accent)
      }
      Divider()
     }
    }
   },
   confirmButton={TextButton(onClick={showLayers=false}) { Text("完成") }}
  )
  if(showMaterialPreview!=null) AlertDialog(
   onDismissRequest={showMaterialPreview=null}, title={Text("素材预览 · ${showMaterialPreview?.name.orEmpty()}")},
   text={Text(showMaterialPreview?.value.orEmpty(),fontSize=13.sp,color=Color(0xFF333333))},
   confirmButton={TextButton(onClick={showMaterialPreview?.let { if(dock==XiumiDock.TEMPLATE) changeBody(it.value) else insert(it.value); selectedSnippet=if(dock==XiumiDock.TEMPLATE) "" else it.value };showMaterialPreview=null}) { Text(if(dock==XiumiDock.TEMPLATE) "套用模板" else "添加到文章") }},
   dismissButton={TextButton(onClick={showMaterialPreview=null}) { Text("关闭") }}
  )
  if(showBlockEditor) AlertDialog(
   onDismissRequest={showBlockEditor=false}, title={Text("独立编辑 · $selectedType")},
   text={OutlinedTextField(blockDraft,{blockDraft=it},Modifier.fillMaxWidth(),minLines=5)},
   confirmButton={TextButton(onClick={
    if(selectedBlockId.isNotBlank()) editSelected { blockDraft }
    showBlockEditor=false
   }) { Text("应用修改") }},
   dismissButton={TextButton(onClick={showBlockEditor=false}) { Text("取消") }}
  )
  if(showImageInsert) AlertDialog(
   onDismissRequest={showImageInsert=false},
   title={Text("插入图片引用")},
   text={
    Column(verticalArrangement=Arrangement.spacedBy(8.dp)) {
     OutlinedTextField(imageUrl,{imageUrl=it},label={Text("图片 URL")},singleLine=true,placeholder={Text("https://...")})
     OutlinedTextField(imageAlt,{imageAlt=it},label={Text("图片说明")},singleLine=true)
     Text("插入 Markdown 图片引用；本入口暂不替代本地图片导入与素材管理。",fontSize=11.sp,color=Color.Gray)
    }
   },
   confirmButton={TextButton(onClick={
    if(imageUrl.startsWith("https://") || imageUrl.startsWith("http://")) {
     insert("![${imageAlt.ifBlank { "图片" }}]($imageUrl)"); imageUrl=""; imageAlt=""; showImageInsert=false
    }
   }) { Text("插入") }},
   dismissButton={TextButton(onClick={showImageInsert=false}) { Text("取消") }}
  )
  if(properties && compact) ModalBottomSheet(onDismissRequest={properties=false}) {
   Column(Modifier.fillMaxWidth().padding(horizontal=18.dp, vertical=10.dp)) {
    Text("属性设置 · $selected",fontSize=16.sp,fontWeight=FontWeight.Bold)
    Text("字号 ${fontSize.toInt()} px",fontSize=12.sp,modifier=Modifier.padding(top=10.dp)); Slider(fontSize,{fontSize=it},valueRange=12f..32f)
    Text("行间距 ${"%.1f".format(lineSpace)}",fontSize=12.sp); Slider(lineSpace,{lineSpace=it},valueRange=1.2f..2.6f)
    FilterChip(bold,{bold=!bold},{Text("粗体")})
    Text("内边距 ${contentPadding.toInt()} dp",fontSize=12.sp); Slider(contentPadding,{contentPadding=it},valueRange=12f..40f)
    Text("边框 ${borderWidth.toInt()} dp",fontSize=12.sp); Slider(borderWidth,{borderWidth=it},valueRange=0f..3f)
    Text("圆角 ${cornerRadius.toInt()} dp",fontSize=12.sp); Slider(cornerRadius,{cornerRadius=it},valueRange=0f..18f)
    Row(horizontalArrangement=Arrangement.spacedBy(16.dp)) { listOf("左对齐","居中","右对齐").forEach { option -> Text(option,color=if(align==option) accent else Color.Gray,modifier=Modifier.clickable { align=option }.padding(vertical=8.dp)) } }
    Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) { listOf(Color(0xFF16A36A),Color(0xFFE58B45),Color(0xFF4D91C7),Color(0xFFBD6B91)).forEach { c -> Box(Modifier.size(26.dp).clip(RoundedCornerShape(50)).background(c).clickable { accent=c }) } }
   }
  }
  Row(Modifier.fillMaxWidth().height(54.dp).background(Color.White).padding(horizontal=8.dp),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceEvenly) {
   Text("撤销",fontSize=11.sp,color=if(undo.size>1) accent else Color.LightGray,modifier=Modifier.clickable { if(undo.size>1) {redo=redo+body;body=undo.last();undo=undo.dropLast(1);dirty=true;selectedSnippet=""} })
   Text("重做",fontSize=11.sp,color=if(redo.isNotEmpty()) accent else Color.LightGray,modifier=Modifier.clickable { if(redo.isNotEmpty()) {undo=undo+body;body=redo.last();redo=redo.dropLast(1);dirty=true;selectedSnippet=""} })
   Text("复制",fontSize=11.sp,color=if(selectedSnippet.isNotBlank()) accent else Color.LightGray,modifier=Modifier.clickable { if(selectedBlockId.isNotBlank()) clipboard.setText(AnnotatedString(blocks.firstOrNull { it.id==selectedBlockId }?.content.orEmpty())) })
   Text("粘贴",fontSize=11.sp,color=accent,modifier=Modifier.clickable { clipboard.getText()?.text?.takeIf { it.isNotBlank() }?.let { insert(it) } })
   listOf("文字","图片","布局","组件","图层").forEach { label -> Text(label,fontSize=11.sp,color=if(selected==label) accent else Color.DarkGray,modifier=Modifier.clickable {
    selected=label
    if(label=="图层") showLayers=true
    else dock=when(label) { "文字"->XiumiDock.TEXT;"图片"->XiumiDock.IMAGE;"布局"->XiumiDock.LAYOUT;else->XiumiDock.COMPONENT }
   }.padding(6.dp)) }
  }
 }
}
