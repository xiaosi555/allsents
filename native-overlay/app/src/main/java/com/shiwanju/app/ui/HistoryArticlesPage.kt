package com.shiwanju.app.ui

import android.content.Intent
import android.net.Uri
import android.widget.Toast
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
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
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private const val HISTORY_AVATAR = "https://mmbiz.qpic.cn/sz_mmbiz_png/rpicN7OehSy7qNDoI9pnJMUbM2c9d38f0TpRibQ2icA6nOePn4buH2buUId7xfRLVGibkFtib7oIib7LCBcyXqHjOOMQ/640?wx_fmt=png&from=appmsg"
private val HistoryGreen = Color(0xFF07C160)

private data class SpiderProfile(
    val id: String,
    val title: String,
    val msgBiz: String,
    val headimg: String = "",
    val totalPosts: Int = 0,
    val newestAt: String = ""
)

private data class SpiderArticle(
    val id: String,
    val title: String,
    val link: String,
    val publishAt: String = "",
    val readNum: Int = 0,
    val likeNum: Int = 0,
    val likeNum2: Int = 0,
    val cover: String = "",
    val digest: String = ""
)

private data class SpiderPage(
    val items: List<SpiderArticle>,
    val page: Int,
    val totalPages: Int,
    val total: Int
)

private object WechatSpiderApi {
    private fun request(base: String, path: String): JSONObject {
        val endpoint = URL(base.trimEnd('/') + path)
        val connection = endpoint.openConnection() as HttpURLConnection
        connection.requestMethod = "GET"
        connection.connectTimeout = 12000
        connection.readTimeout = 18000
        connection.setRequestProperty("Accept", "application/json")
        connection.setRequestProperty("User-Agent", "ShiWanJu-Android/1.0")
        try {
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val body = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (code !in 200..299) throw IllegalStateException("采集服务返回 HTTP $code：${body.take(180)}")
            return JSONObject(body)
        } finally {
            connection.disconnect()
        }
    }

    fun profiles(base: String): List<SpiderProfile> {
        val json = request(base, "/api/profiles?page=1&perPage=100")
        val data = json.optJSONArray("data") ?: return emptyList()
        return (0 until data.length()).mapNotNull { i ->
            val p = data.optJSONObject(i) ?: return@mapNotNull null
            SpiderProfile(
                id = p.optString("id"),
                title = p.optString("title", "未命名公众号"),
                msgBiz = p.optString("msgBiz"),
                headimg = p.optString("headimg"),
                totalPosts = p.optInt("postsAllCount"),
                newestAt = p.optString("newestPostTime")
            )
        }.filter { it.msgBiz.isNotBlank() }
    }

    fun posts(base: String, biz: String, page: Int): SpiderPage {
        val encodedBiz = URLEncoder.encode(biz, "UTF-8")
        val json = request(base, "/api/posts?msgBiz=$encodedBiz&sortWay=-publishAt&page=$page&perPage=20")
        val metadata = json.optJSONObject("metadata") ?: JSONObject()
        val data = json.optJSONArray("data")
        val items = if (data == null) emptyList() else (0 until data.length()).mapNotNull { i ->
            val p = data.optJSONObject(i) ?: return@mapNotNull null
            val id = p.optString("id")
            // Upstream list results omit cover and digest; the detail endpoint includes both.
            val detail = if (id.isBlank()) null else runCatching {
                request(base, "/api/posts/" + URLEncoder.encode(id, "UTF-8")).optJSONObject("data")
            }.getOrNull()
            SpiderArticle(
                id = id,
                title = p.optString("title", "未命名文章"),
                link = p.optString("link"),
                publishAt = p.optString("publishAt"),
                readNum = p.optInt("readNum"),
                likeNum = p.optInt("likeNum"),
                likeNum2 = p.optInt("likeNum2"),
                cover = detail?.optString("cover").orEmpty(),
                digest = detail?.optString("digest").orEmpty()
            )
        }
        return SpiderPage(items, metadata.optInt("currentPage", page), metadata.optInt("totalPages"), metadata.optInt("count"))
    }
}

@Composable
@OptIn(ExperimentalFoundationApi::class)
fun HistoryArticlesPage(onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val prefs = remember { context.getSharedPreferences("wechat_spider_settings", 0) }
    var server by remember { mutableStateOf(prefs.getString("server", "") ?: "") }
    var biz by remember { mutableStateOf(prefs.getString("biz", "") ?: "") }
    var profiles by remember { mutableStateOf<List<SpiderProfile>>(emptyList()) }
    var selectedProfile by remember { mutableStateOf<SpiderProfile?>(null) }
    var articles by remember { mutableStateOf<List<SpiderArticle>>(emptyList()) }
    var page by remember { mutableIntStateOf(1) }
    var totalPages by remember { mutableIntStateOf(0) }
    var total by remember { mutableIntStateOf(0) }
    var busy by remember { mutableStateOf(false) }
    var notice by remember { mutableStateOf("先配置 wechat_spider 服务地址，再读取已采集的公众号文章。") }
    var settingsOpen by remember { mutableStateOf(server.isBlank()) }
    var profilePickerOpen by remember { mutableStateOf(false) }
    var searching by remember { mutableStateOf(false) }
    var searchText by remember { mutableStateOf("") }

    suspend fun loadPosts(pageNumber: Int) {
        if (server.isBlank() || biz.isBlank()) {
            notice = "请先在设置中填写采集服务地址和公众号 msgBiz。"
            return
        }
        busy = true
        try {
            val result = withContext(Dispatchers.IO) { WechatSpiderApi.posts(server, biz, pageNumber) }
            articles = result.items
            page = result.page
            totalPages = result.totalPages
            total = result.total
            notice = if (result.items.isEmpty()) "服务连接正常，但当前公众号还没有采集到文章。请在微信中打开历史页并向下滚动触发采集。" else "已从 wechat_spider 读取第 " + result.page + " 页数据。"
        } catch (e: Exception) {
            notice = "读取失败：" + (e.message ?: "请检查服务地址、msgBiz 和网络")
        } finally {
            busy = false
        }
    }

    BackHandler { onBack() }

    fun persist() {
        prefs.edit().putString("server", server.trim().trimEnd('/')).putString("biz", biz.trim()).apply()
    }

    fun loadProfiles() {
        if (server.isBlank()) { settingsOpen = true; return }
        scope.launch {
            busy = true
            notice = "正在连接采集服务…"
            try {
                val result = withContext(Dispatchers.IO) { WechatSpiderApi.profiles(server) }
                profiles = result
                notice = if (result.isEmpty()) "服务已连接，但尚无公众号记录。请先在微信中打开公众号历史页并通过代理采集。" else "已连接，识别到 ${result.size} 个公众号。"
                if (biz.isBlank() && result.size == 1) {
                    biz = result.first().msgBiz
                    selectedProfile = result.first()
                    persist()
                }
                if (biz.isNotBlank()) loadPosts(1)
            } catch (e: Exception) {
                notice = "连接失败：${e.message ?: "请检查服务地址和网络"}"
            } finally { busy = false }
        }
    }

    fun openHistoryInWechat() {
        val targetBiz = biz.trim()
        if (targetBiz.isBlank()) {
            notice = "请先选择公众号或填写 msgBiz。"
            profilePickerOpen = profiles.isNotEmpty()
            return
        }
        val url = "https://mp.weixin.qq.com/mp/profile_ext?action=home&__biz=${targetBiz}&scene=124#wechat_redirect"
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).setPackage("com.tencent.mm")
        runCatching { context.startActivity(intent) }.onFailure {
            runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
                .onFailure { Toast.makeText(context, "无法打开微信", Toast.LENGTH_SHORT).show() }
        }
        notice = "已打开公众号历史页。请确认手机微信使用采集服务所在电脑的代理（8101），并已安装其 HTTPS 证书。"
    }

    // Local function is intentionally declared before callbacks that use it.
    fun refreshCurrent() {
        if (server.isBlank() || biz.isBlank()) { settingsOpen = true; return }
        scope.launch { loadPosts(1) }
    }

    // Keep requests on IO; the upstream spider itself captures pages through AnyProxy.
    fun selectProfile(profile: SpiderProfile) {
        selectedProfile = profile
        biz = profile.msgBiz
        persist()
        profilePickerOpen = false
        scope.launch { loadPosts(1) }
    }

    Column(Modifier.fillMaxSize().background(Color(0xFFF6F6F6)).statusBarsPadding()) {
        Row(
            Modifier.fillMaxWidth().height(52.dp).background(Color.White).padding(horizontal = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "返回", tint = Color(0xFFAAAAAA)) }
            Text("历史文章", Modifier.weight(1f), color = Color(0xFF222222), fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
            IconButton(onClick = { searching = !searching; searchText = "" }) { Icon(Icons.Default.Search, "搜索", tint = Color(0xFFAAAAAA)) }
            IconButton(onClick = { settingsOpen = true }) { Icon(Icons.Default.Settings, "设置", tint = Color(0xFFAAAAAA)) }
        }
        if (searching) {
            OutlinedTextField(searchText, { searchText = it }, Modifier.fillMaxWidth().background(Color.White).padding(horizontal = 12.dp, vertical = 6.dp), singleLine = true, placeholder = { Text("搜索已采集文章标题") })
        }
        LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 28.dp)) {
            item("profile") {
                Row(Modifier.fillMaxWidth().background(Color.White).padding(horizontal = 20.dp, vertical = 18.dp), verticalAlignment = Alignment.CenterVertically) {
                    AsyncImage(model = selectedProfile?.headimg?.takeIf { it.isNotBlank() } ?: HISTORY_AVATAR, contentDescription = "公众号头像", modifier = Modifier.size(76.dp).clip(CircleShape))
                    Column(Modifier.weight(1f).padding(start = 16.dp)) {
                        Text(selectedProfile?.title ?: "历史文章采集", color = Color(0xFF191919), fontSize = 21.sp, fontWeight = FontWeight.SemiBold)
                        Text(if (biz.isBlank()) "尚未选择公众号" else "已绑定公众号 · ${biz.take(12)}", color = Color.Gray, fontSize = 13.sp)
                    }
                    TextButton(onClick = { profilePickerOpen = true; if (profiles.isEmpty()) loadProfiles() }) { Text("选择", color = HistoryGreen) }
                }
            }
            item("description") {
                Column(Modifier.fillMaxWidth().background(Color.White).padding(horizontal = 20.dp, vertical = 4.dp)) {
                    Text("通过 wechat_spider 采集并展示公众号历史文章", color = Color(0xFF333333), fontSize = 15.sp)
                    Spacer(Modifier.height(12.dp))
                }
            }
            stickyHeader("profile-collapsed") {
                Row(Modifier.fillMaxWidth().height(60.dp).background(Color.White).padding(horizontal = 20.dp), verticalAlignment = Alignment.CenterVertically) {
                    AsyncImage(
                        model = selectedProfile?.headimg?.takeIf { it.isNotBlank() } ?: HISTORY_AVATAR,
                        contentDescription = "公众号头像",
                        modifier = Modifier.size(40.dp).clip(CircleShape),
                        contentScale = ContentScale.Crop
                    )
                    Text(
                        selectedProfile?.title ?: "拾万句",
                        Modifier.padding(start = 30.dp),
                        color = Color(0xFF171717),
                        fontSize = 17.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }
            stickyHeader("sticky") {
                Row(Modifier.fillMaxWidth().height(54.dp).background(Color.White).padding(horizontal = 18.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("全部文章", color = Color(0xFF777777), fontSize = 14.sp)
                    Spacer(Modifier.weight(1f))
                    Text(if (busy) "同步中…" else if (total > 0) "共 $total 篇" else "等待采集", color = Color.LightGray, fontSize = 12.sp)
                    IconButton(onClick = { refreshCurrent() }, enabled = !busy) { Icon(Icons.Default.Refresh, "刷新", tint = Color(0xFFAAAAAA)) }
                }
            }
            item("capture-help") {
                Column(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp)) {
                    Text("采集入口", color = Color(0xFF888888), fontSize = 12.sp)
                    Row(Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Button(onClick = { openHistoryInWechat() }, colors = ButtonDefaults.buttonColors(containerColor = HistoryGreen), modifier = Modifier.weight(1f)) { Text("在微信中打开历史页") }
                        OutlinedButton(onClick = { loadProfiles() }, modifier = Modifier.weight(1f)) { Text("连接并读取") }
                    }
                    if (notice.isNotBlank()) Text(notice, Modifier.padding(top = 8.dp), color = Color(0xFF8A8A8A), fontSize = 12.sp, lineHeight = 18.sp)
                }
            }
            val shown = articles.filter { !searching || searchText.isBlank() || it.title.contains(searchText, true) }
            if (shown.isEmpty()) {
                item("empty") {
                    Box(Modifier.fillMaxWidth().height(170.dp), contentAlignment = Alignment.Center) {
                        Text(if (busy) "正在读取采集结果…" else "暂无历史文章记录", color = Color.Gray, fontSize = 14.sp)
                    }
                }
            } else {
                items(shown, key = { it.id.ifBlank { it.link } }) { article ->
                    Column(
                        Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp)
                            .background(Color.White, MaterialTheme.shapes.medium)
                            .clickable { openArticle(context, article.link) }
                            .padding(horizontal = 16.dp, vertical = 14.dp)
                    ) {
                        Text(formatSpiderDate(article.publishAt), color = Color.LightGray, fontSize = 12.sp)
                        if (article.cover.isNotBlank()) {
                            AsyncImage(model = article.cover, contentDescription = "文章封面", modifier = Modifier.fillMaxWidth().height(180.dp), contentScale = ContentScale.Crop)
                        } else {
                            Box(Modifier.fillMaxWidth().height(150.dp).background(Color(0xFFE8F3E8)), contentAlignment = Alignment.Center) { Text("封面暂不可用", color = Color(0xFF8AAB98), fontSize = 13.sp) }
                        }
                        Text(article.title.ifBlank { "未命名文章" }, Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 14.dp), color = Color(0xFF202020), fontSize = 18.sp, lineHeight = 25.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        if (article.digest.isNotBlank()) Text(article.digest, Modifier.fillMaxWidth().padding(horizontal = 16.dp).padding(bottom = 10.dp), color = Color.Gray, fontSize = 13.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(18.dp)) {
                            Text("阅读 ${article.readNum}", color = Color(0xFFAAAAAA), fontSize = 11.sp)
                            Text("点赞 ${article.likeNum}", color = Color(0xFFAAAAAA), fontSize = 11.sp)
                            Text("在看 ${article.likeNum2}", color = Color(0xFFAAAAAA), fontSize = 11.sp)
                        }
                    }
                }
            }
            if (totalPages > 1) {
                item("pagination") {
                    Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center) {
                        TextButton(onClick = { if (page > 1) scope.launch { loadPosts(page - 1) } }, enabled = page > 1 && !busy) { Text("上一页") }
                        Text("$page / $totalPages", color = Color.Gray, fontSize = 13.sp)
                        TextButton(onClick = { if (page < totalPages) scope.launch { loadPosts(page + 1) } }, enabled = page < totalPages && !busy) { Text("下一页") }
                    }
                }
            }
        }
    }

    if (settingsOpen) {
        AlertDialog(
            onDismissRequest = { settingsOpen = false },
            title = { Text("采集服务设置") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(server, { server = it }, Modifier.fillMaxWidth(), label = { Text("服务地址") }, placeholder = { Text("http://电脑局域网IP:8104") }, singleLine = true)
                    OutlinedTextField(biz, { biz = it }, Modifier.fillMaxWidth(), label = { Text("公众号 msgBiz") }, placeholder = { Text("可从已采集公众号列表中选择") }, singleLine = true)
                    Text("服务地址填写运行 wechat_spider 的电脑地址。手机和电脑需在同一网络；微信代理端口默认 8101。", color = Color.Gray, fontSize = 12.sp, lineHeight = 17.sp)
                }
            },
            confirmButton = {
                TextButton(onClick = { persist(); settingsOpen = false; loadProfiles() }) { Text("保存并连接", color = HistoryGreen) }
            },
            dismissButton = { TextButton(onClick = { settingsOpen = false }) { Text("取消") } }
        )
    }

    if (profilePickerOpen) {
        AlertDialog(
            onDismissRequest = { profilePickerOpen = false },
            title = { Text("选择已采集公众号") },
            text = {
                Column(Modifier.heightIn(max = 360.dp)) {
                    if (profiles.isEmpty()) Text("暂未获取到公众号记录。请先使用微信打开该公众号的历史文章页面，让代理捕获资料。", color = Color.Gray)
                    else profiles.forEach { profile ->
                        TextButton(onClick = { selectProfile(profile) }, modifier = Modifier.fillMaxWidth()) {
                            Column(Modifier.fillMaxWidth()) {
                                Text(profile.title, color = Color(0xFF222222))
                                Text("文章 ${profile.totalPosts} 篇 · ${profile.msgBiz}", color = Color.Gray, fontSize = 11.sp)
                            }
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { profilePickerOpen = false }) { Text("关闭") } }
        )
    }
}

private fun openArticle(context: android.content.Context, link: String) {
    if (link.isBlank()) return
    val uri = Uri.parse(link)
    val opened = runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, uri).setPackage("com.tencent.mm")) }.isSuccess
    if (!opened) runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, uri)) }
}

private fun formatSpiderDate(value: String): String {
    if (value.isBlank() || value == "null") return "发布时间未知"
    return runCatching {
        val normalized = value.substringBefore('.').replace("T", " ")
        normalized.take(16)
    }.getOrDefault(value)
}
