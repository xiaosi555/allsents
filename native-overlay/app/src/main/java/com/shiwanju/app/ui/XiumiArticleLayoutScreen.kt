package com.shiwanju.app.ui
import androidx.activity.compose.BackHandler
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shiwanju.app.data.ArticleDocument

private enum class XiumiDock(val label:String,val icon:String) {
 THEME("主题","◉"), TITLE("标题","T"), TEXT("文字","文"), IMAGE("图片","▧"), LAYOUT("布局","▦"),
 CARD("卡片","▤"), SVG("SVG","◇"), COMPONENT("组件","⊞"), TEMPLATE("模板","▣"), FAVORITE("收藏","♡")
}
private data class XiumiMaterial(val name:String,val detail:String,val value:String)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun XiumiArticleLayoutScreen(vm:AppViewModel,onBack:()->Unit) {
 val initial=remember { vm.data.articles.maxByOrNull { it.updatedAt } }
 var id by remember { mutableStateOf(initial?.id ?: vm.newId()) }
 var title by remember { mutableStateOf(initial?.title.orEmpty()) }
 var subtitle by remember { mutableStateOf(initial?.subtitle.orEmpty()) }
 var author by remember { mutableStateOf(initial?.author?.ifBlank { "拾万句" } ?: "拾万句") }
 var body by remember { mutableStateOf(initial?.html.orEmpty()) }
 var dock by remember { mutableStateOf(XiumiDock.TITLE) }
 var selected by remember { mutableStateOf("正文") }
 var search by remember { mutableStateOf("") }
 var preview by remember { mutableStateOf(false) }
 var properties by remember { mutableStateOf(true) }
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
  vm.saveArticle(ArticleDocument(id=id,title=title.ifBlank { "未命名文章" },html=body,createdAt=initial?.createdAt ?: now,
   updatedAt=now,subtitle=subtitle,summary=initial?.summary.orEmpty(),author=author,coverAssetId=initial?.coverAssetId.orEmpty(),
   category=initial?.category.orEmpty(),tags=initial?.tags ?: emptyList(),status="draft",wordCount=(title+subtitle+body).length,
   isFavorite=initial?.isFavorite ?: false))
  dirty=false
 }
 fun changeBody(value:String) { if(value!=body) { undo=(undo+body).takeLast(50); redo=emptyList(); body=value; dirty=true } }
 fun insert(value:String) { changeBody(if(body.isBlank()) value else body.trimEnd()+"\\n\\n"+value) }
 BackHandler { if(dirty) save(); onBack() }
 val materials=remember(dock,vm.data.styles) {
  when(dock) {
   XiumiDock.TITLE -> listOf(XiumiMaterial("大标题","醒目章节标题","【大标题】"),XiumiMaterial("编号标题","序号标题","01  【章节标题】"),XiumiMaterial("色块标题","带底色标题","▰  【标题文字】"))
   XiumiDock.TEXT -> listOf(XiumiMaterial("正文段落","标准文字段落","在这里输入正文内容。"),XiumiMaterial("引用","引用与出处","“在这里输入引用内容。”\\n—— 来源"),XiumiMaterial("分割线","段落分隔","━━━━━━━━━━━━"),XiumiMaterial("注释","小字说明","注：补充说明。"))
   XiumiDock.IMAGE -> listOf(XiumiMaterial("单图","图片占位","［图片：点击替换］"),XiumiMaterial("双图","左右双图","［图片 1］　　　［图片 2］"),XiumiMaterial("图文混排","图文组合","［图片］\\n图片说明文字。"))
   XiumiDock.LAYOUT -> listOf(XiumiMaterial("双栏布局","两列内容","［左栏内容］　　　［右栏内容］"),XiumiMaterial("三栏布局","三列内容","［一］　［二］　［三］"),XiumiMaterial("图文卡片","图文组合卡片","［图片］\\n【卡片标题】\\n卡片正文"),XiumiMaterial("留白","段落留白","\\n\\n"))
   XiumiDock.CARD -> listOf(XiumiMaterial("灰底卡片","浅灰内容块","▧ 【卡片标题】\\n卡片正文内容"),XiumiMaterial("边框卡片","描边内容块","▢ 【卡片标题】\\n卡片正文内容"),XiumiMaterial("强调卡片","重点提示","✦ 重点提示：输入内容。"))
   XiumiDock.SVG -> listOf(XiumiMaterial("展开阅读","点击展开内容","［点击展开］\\n展开后的详细内容"),XiumiMaterial("横向滑动","横向卡片组","［卡片 1］　［卡片 2］　［卡片 3］"),XiumiMaterial("步骤组件","步骤序列","01  第一步\\n02  第二步\\n03  第三步"))
   XiumiDock.COMPONENT -> listOf(XiumiMaterial("关注引导","公众号关注提示","关注公众号｜拾万句"),XiumiMaterial("作者信息","作者署名","文 / 拾万句"),XiumiMaterial("二维码","二维码占位","［二维码图片］"))
   XiumiDock.TEMPLATE -> listOf(XiumiMaterial("简约文章","标题、正文、引用","【文章标题】\\n\\n导语内容\\n\\n正文内容\\n\\n“引用内容”"),XiumiMaterial("清新图文","图片与正文","【图文标题】\\n［封面图片］\\n\\n正文内容"),XiumiMaterial("知识卡片","知识点卡片","01｜知识点标题\\n知识点解释"))
   XiumiDock.THEME -> listOf(XiumiMaterial("薄荷绿","清新绿色","mint"),XiumiMaterial("暖阳橙","温暖橙色","orange"),XiumiMaterial("海盐蓝","清爽蓝色","blue"))
   XiumiDock.FAVORITE -> vm.data.styles.map { XiumiMaterial(it.name,it.category,it.html) }
  }
 }
 Column(Modifier.fillMaxSize().background(Color(0xFFF2F3F4))) {
  Row(Modifier.fillMaxWidth().height(54.dp).background(Color.White).padding(horizontal=8.dp),verticalAlignment=Alignment.CenterVertically) {
   IconButton(onClick={if(dirty) save();onBack()}) { Icon(Icons.Outlined.ArrowBack,contentDescription="返回") }
   Column(Modifier.weight(1f)) { Text("秀米式图文排版",fontSize=16.sp,fontWeight=FontWeight.SemiBold); Text(if(dirty) "未保存" else "编辑器",fontSize=10.sp,color=Color.Gray) }
   TextButton(onClick={preview=!preview}) { Text(if(preview) "编辑" else "预览") }
   TextButton(onClick={save}) { Text("保存",color=accent,fontWeight=FontWeight.Bold) }
   TextButton(onClick={properties=!properties}) { Text("属性") }
  }
  Row(Modifier.weight(1f).fillMaxWidth()) {
   Column(Modifier.width(60.dp).fillMaxHeight().background(Color(0xFFFAFAFA)).verticalScroll(rememberScrollState()),horizontalAlignment=Alignment.CenterHorizontally) {
    XiumiDock.entries.forEach { item ->
     val active=dock==item
     Column(Modifier.fillMaxWidth().padding(horizontal=4.dp,vertical=2.dp).clip(RoundedCornerShape(8.dp)).background(if(active) accent.copy(alpha=.12f) else Color.Transparent)
      .clickable { dock=item;search="" }.padding(vertical=8.dp),horizontalAlignment=Alignment.CenterHorizontally) {
      Text(item.icon,fontSize=19.sp,color=if(active) accent else Color.DarkGray); Text(item.label,fontSize=10.sp,color=if(active) accent else Color.DarkGray)
     }
    }
   }
   Column(Modifier.width(168.dp).fillMaxHeight().background(Color.White).padding(9.dp)) {
    Text(dock.label,fontSize=15.sp,fontWeight=FontWeight.Bold)
    OutlinedTextField(search,{search=it},Modifier.fillMaxWidth(),singleLine=true,placeholder={Text("搜索素材",fontSize=11.sp)},textStyle=LocalTextStyle.current.copy(fontSize=12.sp))
    Column(Modifier.weight(1f).verticalScroll(rememberScrollState()).padding(top=8.dp)) {
     materials.filter { search.isBlank() || it.name.contains(search) || it.detail.contains(search) }.forEach { material ->
      Column(Modifier.fillMaxWidth().padding(bottom=7.dp).clip(RoundedCornerShape(8.dp)).background(Color(0xFFF5F6F6)).clickable {
       if(dock==XiumiDock.THEME) accent=when(material.value) { "orange"->Color(0xFFE58B45); "blue"->Color(0xFF4D91C7); else->Color(0xFF16A36A) } else insert(material.value)
      }.padding(9.dp)) {
       Text(material.name,fontSize=12.sp,fontWeight=FontWeight.SemiBold); Text(material.detail,fontSize=10.sp,color=Color.Gray)
       if(dock!=XiumiDock.THEME) Text("＋ 添加",fontSize=10.sp,color=accent,modifier=Modifier.padding(top=4.dp))
      }
     }
     if(materials.isEmpty()) Text("暂无收藏素材",fontSize=11.sp,color=Color.Gray)
    }
   }
   Column(Modifier.weight(1f).fillMaxHeight().verticalScroll(rememberScrollState()),horizontalAlignment=Alignment.CenterHorizontally) {
    Row(Modifier.fillMaxWidth().height(38.dp).background(Color(0xFFF8F8F8)).padding(horizontal=8.dp),verticalAlignment=Alignment.CenterVertically) {
     Text("画布",fontSize=11.sp,color=Color.Gray); Spacer(Modifier.weight(1f)); Text("100%",fontSize=10.sp,color=Color.Gray)
    }
    Column(Modifier.fillMaxWidth(.96f).padding(vertical=10.dp).background(Color.White).border(1.dp,Color(0xFFE6E6E6)).padding(14.dp)) {
     if(!preview) {
      Text("文章信息",fontSize=10.sp,color=Color.LightGray)
      OutlinedTextField(title,{title=it;dirty=true},Modifier.fillMaxWidth(),placeholder={Text("请输入文章标题")},textStyle=LocalTextStyle.current.copy(fontSize=21.sp,fontWeight=FontWeight.Bold))
      OutlinedTextField(subtitle,{subtitle=it;dirty=true},Modifier.fillMaxWidth(),placeholder={Text("摘要 / 导语（可选）")},textStyle=LocalTextStyle.current.copy(fontSize=13.sp),minLines=2)
      Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
       Text("文 /",fontSize=11.sp,color=Color.Gray); Spacer(Modifier.width(6.dp))
       BasicTextField(author,{author=it;dirty=true},Modifier.weight(1f),textStyle=LocalTextStyle.current.copy(fontSize=12.sp,color=Color.DarkGray))
       Text("封面 ＋",fontSize=11.sp,color=accent,modifier=Modifier.clickable { dock=XiumiDock.IMAGE })
      }
      HorizontalDivider(Modifier.padding(vertical=12.dp)); Text("正文内容",fontSize=10.sp,color=Color.LightGray)
      OutlinedTextField(body,{changeBody(it)},Modifier.fillMaxWidth().defaultMinSize(minHeight=300.dp),placeholder={Text("从左侧选择标题、文字、图片、布局或组件添加到文章，也可直接输入。")},
       textStyle=LocalTextStyle.current.copy(fontSize=fontSize.sp,lineHeight=(fontSize*lineSpace).sp,fontWeight=if(bold) FontWeight.Bold else FontWeight.Normal,
        textAlign=when(align) { "居中"->TextAlign.Center; "右对齐"->TextAlign.End; else->TextAlign.Start }),minLines=14)
     } else {
      Text(title.ifBlank { "未命名文章" },fontSize=23.sp,fontWeight=FontWeight.Bold,color=Color(0xFF222222))
      if(subtitle.isNotBlank()) Text(subtitle,fontSize=13.sp,color=Color.Gray,modifier=Modifier.padding(top=8.dp))
      Text("文 / $author",fontSize=11.sp,color=Color.Gray,modifier=Modifier.padding(vertical=12.dp))
      Text(body.ifBlank { "正文预览将在这里显示。" },fontSize=fontSize.sp,lineHeight=(fontSize*lineSpace).sp,color=Color(0xFF333333))
     }
     Spacer(Modifier.height(32.dp))
    }
   }
   if(properties) Column(Modifier.width(148.dp).fillMaxHeight().background(Color.White).verticalScroll(rememberScrollState()).padding(9.dp)) {
    Text("属性设置",fontSize=14.sp,fontWeight=FontWeight.Bold); Text("选中：$selected",fontSize=10.sp,color=Color.Gray,modifier=Modifier.padding(vertical=8.dp)); HorizontalDivider()
    Text("字号 \${fontSize.toInt()} px",fontSize=11.sp,modifier=Modifier.padding(top=10.dp)); Slider(fontSize,{fontSize=it},valueRange=12f..32f)
    Text("行间距 \${"%.1f".format(lineSpace)}",fontSize=11.sp); Slider(lineSpace,{lineSpace=it},valueRange=1.2f..2.6f)
    FilterChip(bold,{bold=!bold},{Text("粗体",fontSize=10.sp)})
    Text("对齐方式",fontSize=11.sp,modifier=Modifier.padding(top=10.dp))
    listOf("左对齐","居中","右对齐").forEach { option -> Text(option,fontSize=11.sp,color=if(align==option) accent else Color.Gray,modifier=Modifier.fillMaxWidth().clickable { align=option }.padding(vertical=6.dp)) }
    Text("主题色",fontSize=11.sp,modifier=Modifier.padding(top=10.dp,bottom=6.dp))
    Row(horizontalArrangement=Arrangement.spacedBy(5.dp)) { listOf(Color(0xFF16A36A),Color(0xFFE58B45),Color(0xFF4D91C7),Color(0xFFBD6B91)).forEach { c -> Box(Modifier.size(21.dp).clip(RoundedCornerShape(50)).background(c).clickable { accent=c }) } }
   }
  }
  Row(Modifier.fillMaxWidth().height(52.dp).background(Color.White),verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.SpaceEvenly) {
   Text("↶",fontSize=23.sp,color=if(undo.size>1) accent else Color.LightGray,modifier=Modifier.clickable { if(undo.isNotEmpty()) {redo=redo+body;body=undo.last();undo=undo.dropLast(1);dirty=true} })
   Text("↷",fontSize=23.sp,color=if(redo.isNotEmpty()) accent else Color.LightGray,modifier=Modifier.clickable { if(redo.isNotEmpty()) {undo=undo+body;body=redo.last();redo=redo.dropLast(1);dirty=true} })
   listOf("文字","图片","布局","组件","图层").forEach { label -> Text(label,fontSize=11.sp,color=if(selected==label) accent else Color.DarkGray,modifier=Modifier.clickable { selected=label;dock=when(label) { "文字"->XiumiDock.TEXT;"图片"->XiumiDock.IMAGE;"布局"->XiumiDock.LAYOUT;else->XiumiDock.COMPONENT } }.padding(6.dp)) }
  }
 }
}
