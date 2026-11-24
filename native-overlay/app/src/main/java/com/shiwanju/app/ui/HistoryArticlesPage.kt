package com.shiwanju.app.ui

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.MoreHoriz
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
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
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val HistoryGreen = Color(0xFF01CC7A)
private data class HistoryArticle(val id: String, val title: String, val link: String, val date: String, val cover: String, val digest: String = "")
private data class HistoryResult(val articles: List<HistoryArticle>, val nextOffset: String, val ended: Boolean, val accountName: String = "")

private object OfficialHistoryApi {
    private fun postJson(endpoint: String, payload: JSONObject): JSONObject {
        val c = (URL(endpoint).openConnection() as HttpURLConnection)
        c.requestMethod = "POST"; c.connectTimeout = 18000; c.readTimeout = 30000
        c.doOutput = true
        c.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        c.setRequestProperty("Accept", "application/json")
        c.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
        val code = c.responseCode
        val body = (if (code in 200..299) c.inputStream else c.errorStream)?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
        c.disconnect()
        if (code !in 200..299) throw IllegalStateException("接口 HTTP $code：${body.take(160)}")
        return JSONObject(body)
    }

    private fun postForm(endpoint: String, fields: Map<String, String>): JSONObject {
        val body = fields.entries.joinToString("&") { URLEncoder.encode(it.key, "UTF-8") + "=" + URLEncoder.encode(it.value, "UTF-8") }
        val c = (URL(endpoint).openConnection() as HttpURLConnection)
        c.requestMethod = "POST"; c.connectTimeout = 18000; c.readTimeout = 30000
        c.doOutput = true
        c.setRequestProperty("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
        c.setRequestProperty("Accept", "application/json")
        c.outputStream.use { it.write(body.toByteArray(Charsets.UTF_8)) }
        val code = c.responseCode
        val response = (if (code in 200..299) c.inputStream else c.errorStream)?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
        c.disconnect()
        if (code !in 200..299) throw IllegalStateException("JustOneAPI HTTP $code：${response.take(160)}")
        return JSONObject(response)
    }

    fun dajiala(key: String, verify: String, account: String, sourceUrl: String, offset: String): HistoryResult {
        val req = JSONObject().put("key", key).put("verifycode", verify).put("offset", offset)
            .put("ghid", if (account.startsWith("gh_")) account else "")
            .put("nickname", if (account.startsWith("gh_")) "" else account)
            .put("url", sourceUrl)
        val json = postJson("https://www.dajiala.com/fbmain/monitor/v3/post_history", req)
        val code = json.optInt("code", -999)
        if (code != 0) throw IllegalStateException("极致了 API 错误 $code：${json.optString("msg", json.optString("error_msg", "请检查 Key、附加码和账号信息"))}")
        val data = json.optJSONArray("data") ?: JSONArray()
        val result = (0 until data.length()).mapNotNull { i ->
            val p = data.optJSONObject(i) ?: return@mapNotNull null
            val link = p.optString("url")
            if (link.isBlank()) return@mapNotNull null
            HistoryArticle(
                p.optString("sn", link), p.optString("title", "未命名文章"), link,
                p.optString("post_time_str").ifBlank { p.optLong("post_time").takeIf { it > 0 }?.let { formatEpoch(it) } ?: "" },
                p.optString("pic_cdn_url_235_1").ifBlank { p.optString("cover_url") }.ifBlank { p.optString("pic_cdn_url_16_9") },
                p.optString("digest")
            )
        }
        val next = json.optString("offset")
        val ended = json.optInt("is_end", 0) == 1 || next.isBlank()
        return HistoryResult(result, next, ended, json.optString("nickname"))
    }

    fun justOne(token: String, sourceUrl: String, ghid: String, offset: String): HistoryResult {
        val params = linkedMapOf("token" to token, "offset" to offset)
        if (sourceUrl.isNotBlank()) params["url"] = sourceUrl else params["ghid"] = ghid
        val json = postForm("https://api.justoneapi.com/api/weixin/get-account-history-articles/v2", params)
        if (json.optInt("code", -999) != 0) throw IllegalStateException("JustOneAPI 错误码：${json.opt("code")}")
        val data = json.optJSONObject("data") ?: JSONObject()
        val messages = data.optJSONObject("MsgList")?.optJSONArray("Msg") ?: JSONArray()
        val out = mutableListOf<HistoryArticle>()
        for (i in 0 until messages.length()) {
            val detail = messages.optJSONObject(i)?.optJSONObject("AppMsg")?.optJSONArray("DetailInfo") ?: continue
            for (j in 0 until detail.length()) {
                val item = detail.optJSONObject(j) ?: continue
                val link = item.optString("ContentUrl")
                if (link.isBlank()) continue
                out.add(HistoryArticle(
                    link, item.optString("Title", "未命名文章"), link,
                    item.optString("CreateTime").ifBlank { item.optString("CreateTimeStr") },
                    item.optString("Cover").ifBlank { item.optString("CoverUrl") },
                    item.optString("Digest")
                ))
            }
        }
        val paging = data.optJSONObject("PagingInfo") ?: JSONObject()
        val next = paging.optString("Offset")
        val ended = paging.opt("IsEnd")?.toString() in listOf("1", "true")
        return HistoryResult(out, next, ended)
    }
}

private fun formatEpoch(seconds: Long): String = runCatching {
    SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault()).format(Date(seconds * 1000))
}.getOrDefault("")

@Composable
fun HistoryArticlesPage(onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val prefs = remember { context.getSharedPreferences("official_history_api", Context.MODE_PRIVATE) }
    var provider by remember { mutableStateOf(prefs.getString("provider", "dajiala") ?: "dajiala") }
    var key by remember { mutableStateOf(prefs.getString("key", "") ?: "") }
    var verify by remember { mutableStateOf(prefs.getString("verify", "") ?: "") }
    var token by remember { mutableStateOf(prefs.getString("token", "") ?: "") }
    var account by remember { mutableStateOf(prefs.getString("account", "") ?: "") }
    var sourceUrl by remember { mutableStateOf(prefs.getString("source_url", "") ?: "") }
    var offset by remember { mutableStateOf("") }
    var articles by remember { mutableStateOf<List<HistoryArticle>>(emptyList()) }
    var ended by remember { mutableStateOf(false) }
    var accountName by remember { mutableStateOf("拾万句") }
    var busy by remember { mutableStateOf(false) }
    var notice by remember { mutableStateOf("配置 API 凭证后即可获取公众号历史文章。") }
    var settingsOpen by remember { mutableStateOf(key.isBlank() && token.isBlank()) }
    var menuOpen by remember { mutableStateOf(false) }
    var searching by remember { mutableStateOf(false) }
    var search by remember { mutableStateOf("") }

    BackHandler { onBack() }

    fun saveSettings() {
        prefs.edit().putString("provider", provider).putString("key", key.trim())
            .putString("verify", verify.trim()).putString("token", token.trim())
            .putString("account", account.trim()).putString("source_url", sourceUrl.trim()).apply()
    }

    fun fetch(reset: Boolean) {
        if (busy) return
        if (provider == "dajiala" && (key.isBlank() || (account.isBlank() && sourceUrl.isBlank()))) {
            settingsOpen = true; notice = "请填写极致了 API Key，以及公众号原始 ID、名称或文章链接。"; return
        }
        if (provider == "justone" && (token.isBlank() || (sourceUrl.isBlank() && account.isBlank()))) {
            settingsOpen = true; notice = "请填写 JustOneAPI Token，以及公众号 ghid 或文章链接。"; return
        }
        if (reset) { offset = ""; articles = emptyList(); ended = false }
        busy = true
        scope.launch {
            try {
                val cursor = if (reset) "" else offset
                val result = withContext(Dispatchers.IO) {
                    if (provider == "dajiala") OfficialHistoryApi.dajiala(key.trim(), verify.trim(), account.trim(), sourceUrl.trim(), cursor)
                    else OfficialHistoryApi.justOne(token.trim(), sourceUrl.trim(), account.trim(), cursor)
                }
                val merged = (if (reset) emptyList() else articles) + result.articles
                articles = merged.distinctBy { it.link }
                offset = result.nextOffset
                ended = result.ended
                if (result.accountName.isNotBlank()) accountName = result.accountName
                notice = if (result.articles.isEmpty()) "接口连接成功，但本页没有返回文章。" else "本次获取 ${result.articles.size} 篇，累计 ${articles.size} 篇。${if (ended) " 已到列表末尾。" else ""}"
            } catch (e: Exception) {
                notice = "获取失败：${e.message ?: "请检查网络和 API 凭证"}"
            } finally { busy = false }
        }
    }

    Column(Modifier.fillMaxSize().background(Color(0xFFF6F6F6)).statusBarsPadding()) {
        Row(Modifier.fillMaxWidth().height(54.dp).background(Color.White).padding(horizontal = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.Default.ArrowBack, "返回", tint = Color(0xFFAAAAAA)) }
            Text("历史文章", Modifier.weight(1f), color = Color(0xFF222222), fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
            IconButton(onClick = { searching = !searching; search = "" }) { Icon(Icons.Default.Search, "搜索", tint = Color(0xFFAAAAAA)) }
            Box {
                IconButton(onClick = { menuOpen = true }) { Icon(Icons.Default.MoreHoriz, "更多", tint = Color(0xFFAAAAAA)) }
                DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                    DropdownMenuItem(text = { Text("API 设置") }, onClick = { menuOpen = false; settingsOpen = true })
                    DropdownMenuItem(text = { Text("重新获取") }, onClick = { menuOpen = false; fetch(true) })
                }
            }
        }
        if (searching) OutlinedTextField(search, { search = it }, Modifier.fillMaxWidth().background(Color.White).padding(horizontal = 12.dp, vertical = 6.dp), singleLine = true, placeholder = { Text("搜索文章标题") })
        LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(bottom = 30.dp)) {
            item("account") {
                Column(Modifier.fillMaxWidth().background(Color.White).padding(20.dp)) {
                    Text(accountName, color = Color(0xFF202020), fontSize = 21.sp, fontWeight = FontWeight.SemiBold)
                    Text(if (provider == "dajiala") "极致了 API · 历史文章实时接口" else "JustOneAPI · 历史文章 V2", color = Color.Gray, fontSize = 12.sp, modifier = Modifier.padding(top = 5.dp))
                }
            }
            item("tools") {
                Column(Modifier.fillMaxWidth().padding(16.dp)) {
                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Button(onClick = { fetch(true) }, enabled = !busy, colors = ButtonDefaults.buttonColors(containerColor = HistoryGreen), modifier = Modifier.weight(1f)) {
                            Icon(Icons.Default.Refresh, null); Spacer(Modifier.width(6.dp)); Text(if (busy) "获取中…" else "获取历史文章")
                        }
                        OutlinedButton(onClick = { fetch(false) }, enabled = !busy && !ended && offset.isNotBlank(), modifier = Modifier.weight(1f)) { Text("继续获取") }
                    }
                    Text(notice, color = Color.Gray, fontSize = 12.sp, lineHeight = 18.sp, modifier = Modifier.padding(top = 9.dp))
                }
            }
            val shown = articles.filter { search.isBlank() || it.title.contains(search, true) }
            items(shown, key = { it.id }) { article ->
                Column(
                    Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp)
                        .clip(RoundedCornerShape(12.dp)).background(Color.White)
                        .clickable { openHistoryArticle(context, article.link) }
                        .padding(14.dp)
                ) {
                    Text(article.date.ifBlank { "发布时间未知" }, color = Color.LightGray, fontSize = 12.sp)
                    if (article.cover.isNotBlank()) AsyncImage(article.cover, null, Modifier.fillMaxWidth().height(170.dp).padding(top = 8.dp), contentScale = ContentScale.Crop)
                    Text(article.title, Modifier.padding(top = 12.dp), color = Color(0xFF222222), fontSize = 16.sp, fontWeight = FontWeight.Medium, maxLines = 2, overflow = TextOverflow.Ellipsis)
                    if (article.digest.isNotBlank()) Text(article.digest, Modifier.padding(top = 6.dp), color = Color.Gray, fontSize = 12.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                }
            }
            if (articles.isNotEmpty()) item("more") {
                TextButton(onClick = { fetch(false) }, enabled = !busy && !ended && offset.isNotBlank(), modifier = Modifier.fillMaxWidth()) {
                    Text(if (ended) "已获取到末尾" else if (busy) "正在获取…" else "加载更多历史文章")
                }
            }
        }
    }

    if (settingsOpen) {
        AlertDialog(
            onDismissRequest = { settingsOpen = false },
            title = { Text("历史文章 API 设置") },
            text = {
                Column(Modifier.heightIn(max = 520.dp).widthIn(max = 480.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Text("数据来源", fontWeight = FontWeight.SemiBold)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        FilterChip(selected = provider == "dajiala", onClick = { provider = "dajiala" }, label = { Text("极致了 API") })
                        FilterChip(selected = provider == "justone", onClick = { provider = "justone" }, label = { Text("JustOneAPI") })
                    }
                    OutlinedTextField(account, { account = it }, Modifier.fillMaxWidth(), label = { Text(if (provider == "dajiala") "公众号名称或 ghid" else "公众号 ghid（可留空）"), placeholder = { Text("例如 gh_...") }, singleLine = true)
                    OutlinedTextField(sourceUrl, { sourceUrl = it }, Modifier.fillMaxWidth(), label = { Text("公众号文章链接（推荐）"), placeholder = { Text("https://mp.weixin.qq.com/s/...") }, singleLine = true)
                    if (provider == "dajiala") {
                        OutlinedTextField(key, { key = it }, Modifier.fillMaxWidth(), label = { Text("API Key") }, singleLine = true)
                        OutlinedTextField(verify, { verify = it }, Modifier.fillMaxWidth(), label = { Text("附加码 verifycode（没有可留空）") }, singleLine = true)
                    } else {
                        OutlinedTextField(token, { token = it }, Modifier.fillMaxWidth(), label = { Text("JustOneAPI Token") }, singleLine = true)
                    }
                    Text("凭证仅保存在本机应用偏好设置中，不写入代码仓库。接口调用可能产生费用，获取范围受服务商权限和微信文章可见状态影响。", color = Color.Gray, fontSize = 11.sp, lineHeight = 16.sp)
                }
            },
            confirmButton = { TextButton(onClick = { saveSettings(); settingsOpen = false; fetch(true) }) { Text("保存并获取", color = HistoryGreen) } },
            dismissButton = { TextButton(onClick = { settingsOpen = false }) { Text("取消") } }
        )
    }
}

private fun openHistoryArticle(context: Context, link: String) {
    if (link.isBlank()) return
    val uri = Uri.parse(link)
    val opened = runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, uri).setPackage("com.tencent.mm")) }.isSuccess
    if (!opened) runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, uri)) }
}
