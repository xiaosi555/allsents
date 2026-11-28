package com.shiwanju.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private data class AppIconItem(val key:String,val title:String,val category:String,val vector:ImageVector)
private val appIconItems = listOf(
 AppIconItem("home","主页","导航",Icons.Outlined.Home), AppIconItem("layout","排版","导航",Icons.Outlined.ViewQuilt),
 AppIconItem("xiumi","秀米排版","导航",Icons.Outlined.Article), AppIconItem("xingtu","醒图","导航",Icons.Outlined.PhotoCamera),
 AppIconItem("xingtu2","醒图 2.0","导航",Icons.Outlined.Edit), AppIconItem("profile","我的","导航",Icons.Outlined.AccountCircle),
 AppIconItem("icon-library","图标库","导航",Icons.Outlined.GridView), AppIconItem("search","搜索","通用",Icons.Outlined.Search),
 AppIconItem("settings","设置","通用",Icons.Outlined.Settings), AppIconItem("more","更多","通用",Icons.Outlined.MoreHoriz),
 AppIconItem("back","返回","通用",Icons.Outlined.ArrowBack), AppIconItem("close","关闭","通用",Icons.Outlined.Close),
 AppIconItem("confirm","确认","通用",Icons.Outlined.Check), AppIconItem("add","添加","通用",Icons.Outlined.Add),
 AppIconItem("save","保存","通用",Icons.Outlined.Save), AppIconItem("undo","撤销","通用",Icons.Outlined.Undo),
 AppIconItem("redo","重做","通用",Icons.Outlined.Redo), AppIconItem("image","图片","素材",Icons.Outlined.Image),
 AppIconItem("gallery","相册","素材",Icons.Outlined.PhotoLibrary), AppIconItem("camera","相机","素材",Icons.Outlined.CameraAlt),
 AppIconItem("folder","文件夹","素材",Icons.Outlined.Folder), AppIconItem("history","历史","素材",Icons.Outlined.History),
 AppIconItem("text","文字","编辑",Icons.Outlined.TextFields), AppIconItem("font","字体","编辑",Icons.Outlined.FormatSize),
 AppIconItem("brush","画笔","编辑",Icons.Outlined.Brush), AppIconItem("crop","裁剪","编辑",Icons.Outlined.Crop),
 AppIconItem("rotate","旋转","编辑",Icons.Outlined.RotateRight), AppIconItem("layers","图层","编辑",Icons.Outlined.Layers),
 AppIconItem("widgets","组件","编辑",Icons.Outlined.Widgets), AppIconItem("align","对齐","编辑",Icons.Outlined.FormatAlignCenter),
 AppIconItem("palette","调色","编辑",Icons.Outlined.Palette), AppIconItem("filter","滤镜","编辑",Icons.Outlined.AutoFixHigh),
 AppIconItem("opacity","透明度","编辑",Icons.Outlined.Opacity), AppIconItem("border","边框","编辑",Icons.Outlined.BorderAll),
 AppIconItem("lock","锁定","编辑",Icons.Outlined.Lock), AppIconItem("visible","显示","编辑",Icons.Outlined.Visibility),
 AppIconItem("delete","删除","编辑",Icons.Outlined.Delete), AppIconItem("copy","复制","编辑",Icons.Outlined.ContentCopy),
 AppIconItem("upload","导入","文件",Icons.Outlined.Upload), AppIconItem("download","导出","文件",Icons.Outlined.Download),
 AppIconItem("favorite","收藏","通用",Icons.Outlined.Favorite)
)

/** The single vector source used by every application screen and icon-library preview. */
fun AppIconVector(key:String):ImageVector = appIconItems.firstOrNull{it.key==key}?.vector ?: Icons.Outlined.Circle

@Composable fun AppIcon(key:String,modifier:Modifier=Modifier,tint:Color=LocalContentColor.current) {
 val item=appIconItems.firstOrNull{it.key==key}
 ShiWanJuLineIcon(item?.title?:key,tint,modifier)
}
private data class HomePageItem(val title:String,val subtitle:String,val route:String,val icon:String,val colors:List<Color>)

/** User-overridable semantic icon mapping. Overrides persist across app launches. */
internal object AppIconRegistry {
    val overrides = mutableStateMapOf<String, String>()
    fun resolve(context: android.content.Context, key: String): String =
        overrides[key] ?: context.getSharedPreferences("shiwanju_icon_overrides", 0).getString(key, key) ?: key
    fun replace(context: android.content.Context, key: String, replacement: String) {
        overrides[key] = replacement
        context.getSharedPreferences("shiwanju_icon_overrides", 0).edit().putString(key, replacement).apply()
    }
    fun reset(context: android.content.Context, key: String) {
        overrides.remove(key)
        context.getSharedPreferences("shiwanju_icon_overrides", 0).edit().remove(key).apply()
    }
}


@Composable fun ShiWanJuHomeScreen(onOpenPage:(String)->Unit) {
 val pages=listOf(
  HomePageItem("排版制作","文案 · 配图 · 版式","layout","排版",listOf(Color(0xFF17231E),Color(0xFF344B3D))),
  HomePageItem("秀米排版","文章编辑与组件排版","xiumi_article_layout","秀米",listOf(Color(0xFF6B8F73),Color(0xFFB4CFA9))),
  HomePageItem("醒图","图片与文字编辑","xingtu_article_editor","醒图",listOf(Color(0xFF1F2024),Color(0xFF55565C))),
  HomePageItem("醒图 2.0","独立画布编辑器","xingtu_editor_v2","醒图 2.0",listOf(Color(0xFFB7EA42),Color(0xFF6D9C31))),
  HomePageItem("我的","账号 · 素材 · 设置","my","我的",listOf(Color(0xFF687B91),Color(0xFFA9B9C8))),
  HomePageItem("图标库","统一图标 · 分类 · 搜索","icon_library","图标库",listOf(Color(0xFF8E7BB4),Color(0xFFC4B8DD)))
 )
 Column(Modifier.fillMaxSize().background(Color(0xFFF8F9F6)).verticalScroll(rememberScrollState())) {
  Box(Modifier.fillMaxWidth().height(224.dp).background(Brush.verticalGradient(listOf(Color(0xFF9AB7C4),Color(0xFFE9B8A8),Color(0xFFF8F9F6))))) {
   Column(Modifier.align(Alignment.BottomStart).padding(start=22.dp,bottom=24.dp)) {
    Text("拾万句",fontSize=34.sp,fontWeight=FontWeight.Bold,color=Color(0xFF26332B))
    Text("创作工具 · 一站式工作空间",fontSize=13.sp,color=Color(0xFF526158))
   }
   Surface(Modifier.align(Alignment.TopEnd).padding(top=22.dp,end=18.dp).size(42.dp).clickable{onOpenPage("icon_library")},shape=RoundedCornerShape(50),color=Color.White.copy(alpha=.72f)) {
    Box(contentAlignment=Alignment.Center){ShiWanJuLineIcon("搜索",Color(0xFF26332B),Modifier.size(22.dp))}
   }
  }
  Column(Modifier.padding(horizontal=18.dp).offset(y=(-8).dp)) {
   Text("开始创作",fontSize=21.sp,fontWeight=FontWeight.Bold,color=Color(0xFF171A18))
   Text("选择一个页面进入",fontSize=12.sp,color=Color(0xFF858B86),modifier=Modifier.padding(top=3.dp,bottom=14.dp))
   pages.chunked(2).forEach { row ->
    Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.spacedBy(12.dp)) {
     row.forEach { page ->
      Column(Modifier.weight(1f).padding(bottom=14.dp).clip(RoundedCornerShape(15.dp)).background(Color.White).clickable{onOpenPage(page.route)}) {
       Box(Modifier.fillMaxWidth().height(116.dp).background(Brush.linearGradient(page.colors))) {
        ShiWanJuLineIcon(page.icon,Color.White.copy(alpha=.94f),Modifier.align(Alignment.Center).size(48.dp))
        Text("打开页面  ›",fontSize=10.sp,color=Color.White.copy(alpha=.82f),modifier=Modifier.align(Alignment.BottomEnd).padding(9.dp))
       }
       Column(Modifier.padding(horizontal=12.dp,vertical=11.dp)) {
        Text(page.title,fontSize=16.sp,fontWeight=FontWeight.SemiBold,color=Color(0xFF202521),maxLines=1,overflow=TextOverflow.Ellipsis)
        Text(page.subtitle,fontSize=11.sp,color=Color(0xFF929992),modifier=Modifier.padding(top=4.dp),maxLines=1,overflow=TextOverflow.Ellipsis)
       }
      }
     }
    }
   }
   Text("全部页面 · 仅显示已接入功能",fontSize=11.sp,color=Color(0xFF9A9F9A),modifier=Modifier.align(Alignment.CenterHorizontally).padding(top=2.dp,bottom=22.dp))
  }
 }
@OptIn(ExperimentalMaterial3Api::class)
@Composable fun AppIconLibraryScreen(onBack:()->Unit) {
 var query by remember{mutableStateOf("")}
 var category by remember{mutableStateOf("全部")}
 var selectedKey by remember{mutableStateOf<String?>(null)}
 var replacementQuery by remember{mutableStateOf("")}
 val context = LocalContext.current
 val categories=listOf("全部","导航","通用","素材","编辑","文件","扩展")
 val shown=appIconItems.filter{(category=="全部"||it.category==category)&&(query.isBlank()||it.title.contains(query,true)||it.key.contains(query,true))}
 Column(Modifier.fillMaxSize().background(Color(0xFFF8F9F6)).statusBarsPadding()) {
  Row(Modifier.fillMaxWidth().height(54.dp).padding(horizontal=14.dp),verticalAlignment=Alignment.CenterVertically) {
   IconButton(onClick=onBack){ShiWanJuLineIcon("返回",Color(0xFF303A33),Modifier.size(22.dp))}
   Text("图标库",fontSize=19.sp,fontWeight=FontWeight.SemiBold,modifier=Modifier.weight(1f))
   Text("${shown.size} 个",fontSize=12.sp,color=Color(0xFF888E88))
  }
  OutlinedTextField(query,{query=it},modifier=Modifier.fillMaxWidth().padding(horizontal=16.dp),singleLine=true,placeholder={Text("搜索图标名称或标识")},leadingIcon={ShiWanJuLineIcon("搜索",Color(0xFF303A33),Modifier.size(20.dp))})
  Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal=14.dp,vertical=10.dp),horizontalArrangement=Arrangement.spacedBy(7.dp)) {
   categories.forEach{item->FilterChip(selected=category==item,onClick={category=item},label={Text(item)})}
  }
  LazyVerticalGrid(columns=GridCells.Adaptive(minSize=92.dp),modifier=Modifier.fillMaxSize().padding(horizontal=12.dp),contentPadding=PaddingValues(bottom=20.dp),verticalArrangement=Arrangement.spacedBy(8.dp),horizontalArrangement=Arrangement.spacedBy(8.dp)) {
   items(shown,key={it.key}){item->
    Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Color.White).clickable { selectedKey=item.key; replacementQuery="" }.padding(vertical=14.dp,horizontal=5.dp),horizontalAlignment=Alignment.CenterHorizontally) {
     AppIcon(item.key,Modifier.size(27.dp),Color(0xFF303A33))
     Text(item.title,fontSize=12.sp,color=Color(0xFF353B36),modifier=Modifier.padding(top=8.dp))
     Text(item.key,fontSize=9.sp,color=Color(0xFF9A9F9A),maxLines=1)
    }
   }
  }
 }
 if (selectedKey != null) {
  val target = appIconItems.firstOrNull { it.key == selectedKey }
  val candidates = appIconItems.filter { replacementQuery.isBlank() || it.title.contains(replacementQuery,true) || it.key.contains(replacementQuery,true) }
  AlertDialog(
   onDismissRequest = { selectedKey=null },
   title = { Text("替换图标 · " + (target?.title ?: selectedKey!!)) },
   text = {
    Column(Modifier.fillMaxWidth()) {
     OutlinedTextField(replacementQuery,{replacementQuery=it},modifier=Modifier.fillMaxWidth(),singleLine=true,placeholder={Text("搜索要替换成的图标")})
     Column(Modifier.heightIn(max=340.dp).verticalScroll(rememberScrollState())) {
      candidates.forEach { candidate ->
       TextButton(onClick={ AppIconRegistry.replace(context,selectedKey!!,candidate.key); selectedKey=null },modifier=Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth(),verticalAlignment=Alignment.CenterVertically) {
         AppIcon(candidate.key,Modifier.size(22.dp),Color(0xFF303A33))
         Text(candidate.title,modifier=Modifier.padding(start=12.dp),color=Color(0xFF303A33))
         Spacer(Modifier.weight(1f))
         Text(candidate.key,fontSize=9.sp,color=Color(0xFF9A9F9A))
        }
       }
      }
     }
    }
   },
   confirmButton = { TextButton(onClick={ AppIconRegistry.reset(context,selectedKey!!); selectedKey=null }) { Text("恢复默认") } },
   dismissButton = { TextButton(onClick={selectedKey=null}) { Text("取消") } }
  )
 }

}
