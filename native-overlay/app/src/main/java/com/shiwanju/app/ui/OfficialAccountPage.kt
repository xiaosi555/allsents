package com.shiwanju.app.ui

import android.content.Intent
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.rounded.Star
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.jsoup.Jsoup
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private const val FIRST_ARTICLE = "https://mp.weixin.qq.com/s/eGh-S6J1YY48vsKNenReFg"
private const val OFFICIAL_AVATAR = "https://mmbiz.qpic.cn/sz_mmbiz_png/rpicN7OehSy7qNDoI9pnJMUbM2c9d38f0TpRibQ2icA6nOePn4buH2buUId7xfRLVGibkFtib7oIib7LCBcyXqHjOOMQ/640?wx_fmt=png&from=appmsg"
private val FeedGreen = Color(0xFF07C160)
private data class OfficialArticle(val url: String, val title: String = "", val summary: String = "", val cover: String = "", val images: List<String> = emptyList(), val publishedAt: String = "")
private class OfficialArticleStore(context: android.content.Context) {
    private val file = File(context.filesDir, "official_articles.json")
    private val gson = Gson()
    fun load(): List<OfficialArticle> = runCatching {
        if (!file.exists()) emptyList() else gson.fromJson<List<OfficialArticle>>(file.readText(Charsets.UTF_8), object : TypeToken<List<OfficialArticle>>() {}.type) ?: emptyList()
    }.getOrDefault(emptyList())
    fun save(items: List<OfficialArticle>) { runCatching { file.writeText(gson.toJson(items), Charsets.UTF_8) } }
}
private object OfficialArticleImporter {
    fun fetch(url: String): OfficialArticle {
        require(url.startsWith("https://mp.weixin.qq.com/s/")) { "无效的微信文章链接" }
        val doc = Jsoup.connect(url).userAgent("Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36 MicroMessenger").timeout(18000).get()
        fun meta(selector: String): String = doc.selectFirst(selector)?.attr("content")?.trim().orEmpty()
        val title = meta("meta[property=og:title]").ifBlank { doc.selectFirst("#activity-name")?.text()?.trim().orEmpty() }
        val summary = meta("meta[property=og:description]").ifBlank { meta("meta[name=description]") }
        // The feed card must use the article cover, not the first images inside the article body.
        val cover = doc.selectFirst("#js_cover")?.let { it.attr("data-src").ifBlank { it.attr("src") } }
            ?.takeIf { it.startsWith("http") }
            ?: meta("meta[property=og:image]").ifBlank { meta("meta[name=twitter:image]") }
        val images = listOf(cover).filter { it.isNotBlank() }
        val date = doc.selectFirst("#publish_time")?.text()?.trim().orEmpty()
        return OfficialArticle(url, title, summary, cover, images, date)
    }
}

@Composable
fun OfficialAccountPage(onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val store = remember { OfficialArticleStore(context.applicationContext) }
    var articles by remember { mutableStateOf(store.load()) }
    var busy by remember { mutableStateOf(false) }
    var query by remember { mutableStateOf("") }
    var searching by remember { mutableStateOf(false) }
    var adding by remember { mutableStateOf(false) }
    var input by remember { mutableStateOf("") }
    var notice by remember { mutableStateOf("") }
    var syncedAt by remember { mutableStateOf("") }

    fun save(items: List<OfficialArticle>) { articles = items.distinctBy { it.url }; store.save(articles) }
    suspend fun importUrl(raw: String) {
        val url = raw.trim()
        if (!url.startsWith("https://mp.weixin.qq.com/s/")) { notice = "请粘贴有效的微信公众号文章链接"; return }
        busy = true
        notice = ""
        try {
            val item = withContext(Dispatchers.IO) { OfficialArticleImporter.fetch(url) }
            save(listOf(item) + articles.filterNot { it.url == url })
            syncedAt = SimpleDateFormat("MM-dd HH:mm", Locale.getDefault()).format(Date())
        } catch (_: Exception) {
            if (articles.none { it.url == url }) save(listOf(OfficialArticle(url, "微信文章（信息待获取）")) + articles)
            notice = "暂时无法读取文章详情，链接已保存，仍可点击卡片在微信中打开。"
        } finally { busy = false }
    }
    suspend fun refresh() {
        if (busy) return
        if (articles.isEmpty()) { importUrl(FIRST_ARTICLE); return }
        busy = true
        val updated = withContext(Dispatchers.IO) { articles.map { old -> runCatching { OfficialArticleImporter.fetch(old.url) }.getOrDefault(old) } }
        save(updated)
        syncedAt = SimpleDateFormat("MM-dd HH:mm", Locale.getDefault()).format(Date())
        busy = false
        if (updated.all { it.title.isBlank() }) notice = "文章链接已保留，但微信暂时未返回文章详情。"
    }
    LaunchedEffect(Unit) { if (articles.isEmpty()) importUrl(FIRST_ARTICLE) }
    BackHandler { onBack() }
    val listState = rememberLazyListState()
    // 只有完整资料区滚出可视区域后才显示紧凑吸顶栏；回到资料区即隐藏。
    // 通过 AnimatedVisibility 进行淡入和轻微上滑，避免页面初始状态提前显示。
    val showCompactProfile by remember {
        derivedStateOf { listState.firstVisibleItemIndex > 0 }
    }

    Column(Modifier.fillMaxSize().background(Color(0xFFF0F0F0)).statusBarsPadding()) {
        Row(Modifier.fillMaxWidth().height(54.dp).background(Color.White).padding(horizontal = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "返回", tint = Color(0xFFB8B8B8), modifier = Modifier.size(20.dp)) }
            Text("公众号", Modifier.weight(1f), fontSize = 19.sp, color = Color(0xFF191919), textAlign = androidx.compose.ui.text.style.TextAlign.Center)
            IconButton(onClick = { searching = !searching; query = "" }) { Icon(Icons.Default.Search, "搜索", tint = Color(0xFFB8B8B8), modifier = Modifier.size(20.dp)) }
            Box {
                var menu by remember { mutableStateOf(false) }
                IconButton(onClick = { menu = true }) { Icon(Icons.Default.MoreHoriz, "更多", tint = Color(0xFFB8B8B8), modifier = Modifier.size(21.dp)) }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    DropdownMenuItem(text = { Text("添加文章链接") }, onClick = { menu = false; adding = true })
                    DropdownMenuItem(text = { Text("刷新文章列表") }, onClick = { menu = false; scope.launch { refresh() } })
                }
            }
        }
        if (searching) OutlinedTextField(query, { query = it }, Modifier.fillMaxWidth().background(Color.White).padding(12.dp), singleLine = true, placeholder = { Text("搜索文章标题") })
        val shown = articles.filter { !searching || query.isBlank() || it.title.contains(query, true) }
        Box(Modifier.fillMaxSize()) {
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(0.dp)
            ) {
                item(key = "profile") {
                    Column(Modifier.fillMaxWidth().background(Color.White)) {
                        Row(Modifier.fillMaxWidth().padding(start = 20.dp, end = 20.dp, top = 18.dp, bottom = 20.dp), verticalAlignment = Alignment.CenterVertically) {
                            AsyncImage(
                                model = OFFICIAL_AVATAR,
                                contentDescription = "拾万句公众号头像",
                                modifier = Modifier.size(76.dp).clip(CircleShape),
                                contentScale = ContentScale.Crop
                            )
                            Column(Modifier.weight(1f).padding(start = 14.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text("拾万句", color = Color(0xFF171717), fontSize = 22.sp, fontWeight = FontWeight.SemiBold)
                                    Icon(Icons.Rounded.Star, contentDescription = "公众号标识", tint = Color(0xFFFFB800), modifier = Modifier.padding(start = 3.dp).size(19.dp))
                                    Text(" ›", color = Color.LightGray, fontSize = 25.sp)
                                }
                                Text("上海", color = Color.Gray, fontSize = 15.sp)
                            }
                        }
                        Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 4.dp)) {
                            Text("一句两句拾万句", color = Color(0xFF292929), fontSize = 16.sp)
                            Spacer(Modifier.height(12.dp))
                        }
                    }
                }
            item(key = "article-section-title") {
                Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("全部文章", color = Color.Gray, fontSize = 14.sp)
                    Spacer(Modifier.weight(1f))
                    Text(
                        if (busy) "正在同步…" else if (syncedAt.isNotBlank()) "更新于 " + syncedAt else "本地缓存 " + articles.size + " 篇",
                        color = Color.LightGray,
                        fontSize = 12.sp
                    )
                }
            }
            if (notice.isNotBlank()) {
                item(key = "notice") {
                    Text(notice, Modifier.padding(horizontal = 16.dp, vertical = 4.dp), color = Color(0xFF9A6A28), fontSize = 12.sp)
                }
            }
            if (shown.isEmpty()) {
                item(key = "empty") {
                    Box(Modifier.fillMaxWidth().height(220.dp), contentAlignment = Alignment.Center) {
                        Text("暂无文章，点击右上角添加文章链接", color = Color.Gray)
                    }
                }
            } else {
                items(shown, key = { it.url }) { article ->
                    Column(
                        Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                            .fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(Color.White).clickable {
                                val opened = runCatching {
                                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(article.url)).setPackage("com.tencent.mm"))
                                }.isSuccess
                                if (!opened) runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(article.url))) }
                            }
                    ) {
                        Text(article.publishedAt.ifBlank { "文章" }, Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 13.dp), color = Color.LightGray, fontSize = 14.sp)
                        val coverUrl = article.cover
                        if (coverUrl.isBlank()) {
                            Box(Modifier.fillMaxWidth().height(180.dp).background(Color(0xFFE8F3E8)), contentAlignment = Alignment.Center) {
                                Text("封面暂不可用", color = Color(0xFF8AAB98), fontSize = 14.sp)
                            }
                        } else {
                            AsyncImage(model = coverUrl, contentDescription = "文章封面", modifier = Modifier.fillMaxWidth().height(180.dp), contentScale = ContentScale.Crop)
                        }
                        Text(article.title.ifBlank { "微信文章（信息待获取）" }, Modifier.fillMaxWidth().padding(start = 16.dp, end = 16.dp, top = 16.dp, bottom = 18.dp), color = Color(0xFF202020), fontSize = 18.sp, lineHeight = 25.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    }
                }
            }
            }
            AnimatedVisibility(
                visible = showCompactProfile,
                modifier = Modifier.align(Alignment.TopCenter),
                enter = fadeIn(animationSpec = tween(durationMillis = 240, easing = FastOutSlowInEasing)) +
                    slideInVertically(
                        animationSpec = tween(durationMillis = 280, easing = FastOutSlowInEasing),
                        initialOffsetY = { -it / 3 }
                    ),
                exit = fadeOut(animationSpec = tween(durationMillis = 180, easing = FastOutSlowInEasing)) +
                    slideOutVertically(
                        animationSpec = tween(durationMillis = 220, easing = FastOutSlowInEasing),
                        targetOffsetY = { -it / 3 }
                    )
            ) {
                Row(
                    Modifier.fillMaxWidth().height(60.dp).background(Color.White).padding(horizontal = 20.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    AsyncImage(
                        model = OFFICIAL_AVATAR,
                        contentDescription = "拾万句公众号头像",
                        modifier = Modifier.size(40.dp).clip(CircleShape),
                        contentScale = ContentScale.Crop
                    )
                    Text(
                        "拾万句",
                        Modifier.padding(start = 30.dp),
                        color = Color(0xFF171717),
                        fontSize = 17.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Icon(Icons.Rounded.Star, contentDescription = "公众号标识", tint = Color(0xFFFFB800), modifier = Modifier.padding(start = 3.dp).size(16.dp))
                }
            }
        }
    }
    if (adding) AlertDialog(
        onDismissRequest = { adding = false },
        title = { Text("添加公众号文章") },
        text = { Column { OutlinedTextField(input, { input = it }, Modifier.fillMaxWidth(), placeholder = { Text("粘贴微信文章链接") }, minLines = 2); Text("导入后缓存标题、封面、摘要和发布时间，正文在微信原文中打开。", color = Color.Gray, fontSize = 12.sp) } },
        confirmButton = { TextButton(onClick = { val url = input.trim(); input = ""; adding = false; scope.launch { importUrl(url) } }) { Text("导入", color = FeedGreen) } },
        dismissButton = { TextButton(onClick = { adding = false }) { Text("取消") } }
    )
}
