package com.shiwanju.app.ui

import android.os.Handler
import android.os.Looper
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.platform.LocalContext
import java.io.File
import java.util.Locale
import com.shiwanju.app.data.ArticleDocument
import com.shiwanju.app.data.MediaAsset
import com.shiwanju.app.data.StyleModule
import org.json.JSONObject
import kotlinx.coroutines.delay

private class ArticleEditorBridge(private val onChange: (String) -> Unit, private val onBlock: (String) -> Unit) {
    private val main = Handler(Looper.getMainLooper())
    @JavascriptInterface fun changed(value: String) { main.post { onChange(value) } }
    @JavascriptInterface fun blockSelected(value: String) { main.post { onBlock(value) } }
}

private enum class EditorPanel(val label: String) {
    TEXT("文字"), IMAGE("图片"), COMPONENT("组件"), STYLE("样式"), TEMPLATE("模板")
}

@Composable
fun ArticleEditorScreen(vm: AppViewModel, onBack: () -> Unit) {
    val context = LocalContext.current
    var articleId by remember { mutableStateOf(vm.newId()) }
    var title by remember { mutableStateOf("未命名文章") }
    var html by remember { mutableStateOf("<p><br></p>") }
    var editor by remember { mutableStateOf<WebView?>(null) }
    var webReady by remember { mutableStateOf(false) }
    var activePanel by remember { mutableStateOf(EditorPanel.TEXT) }
    var activeCategory by remember { mutableStateOf("") }
    var showArticleList by remember { mutableStateOf(false) }
    var showLink by remember { mutableStateOf(false) }
    var showImage by remember { mutableStateOf(false) }
    var dialogValue by remember { mutableStateOf("") }
    var saved by remember { mutableStateOf(false) }
    var previewMode by remember { mutableStateOf(false) }
    var pendingSave by remember { mutableIntStateOf(0) }
    var searchText by remember { mutableStateOf("") }
    var showDeleteConfirm by remember { mutableStateOf<ArticleDocument?>(null) }
    var showRevisionList by remember { mutableStateOf(false) }
    var showArticleInfo by remember { mutableStateOf(false) }
    var fullTemplateConfirm by remember { mutableStateOf<StyleModule?>(null) }
    var showCompatibilityReport by remember { mutableStateOf(false) }
    var compatibilityWarnings by remember { mutableStateOf(emptyList<String>()) }
    var subtitle by remember { mutableStateOf("") }
    var summary by remember { mutableStateOf("") }
    var author by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("") }
    var tagsText by remember { mutableStateOf("") }
    var articleStatus by remember { mutableStateOf("draft") }
    var coverAssetId by remember { mutableStateOf("") }
    var pendingExportHtml by remember { mutableStateOf("") }
    var pendingExportMarkdown by remember { mutableStateOf("") }
    var selectedBlockHtml by remember { mutableStateOf("") }
    val categories = vm.data.styles.map { it.category.trim() }.filter { it.isNotEmpty() }.distinct()
    val categoryStyles = vm.data.styles.filter { it.category == activeCategory }
    val filteredArticles = vm.data.articles.filter { searchText.isBlank() || it.title.contains(searchText, true) || it.summary.contains(searchText, true) || it.tags.any { tag -> tag.contains(searchText, true) } }.sortedByDescending { it.updatedAt }
    val currentArticle = vm.data.articles.firstOrNull { it.id == articleId }
    val pageBg = Color(0xFFF5F6F5)
    val ink = Color(0xFF252A27)
    val accent = Color(0xFF159765)

    fun runJs(script: String) {
        editor?.evaluateJavascript(script, null)
        saved = false
        pendingSave++
    }
    fun command(name: String, value: String? = null) {
        val arg = value?.let { JSONObject.quote(it) } ?: "null"
        runJs("restoreSelection();document.execCommand('$name',false,$arg);saveSelection();document.getElementById('editor').focus();")
    }
    fun insert(fragment: String) {
        runJs("restoreSelection();insertHtml(${JSONObject.quote(fragment)});saveSelection();document.getElementById('editor').focus();")
    }
    fun saveDocument(showToast: Boolean = false) {
        val savingId = articleId
        val savingTitle = title.ifBlank { "未命名文章" }
        val savingSubtitle = subtitle
        val savingSummary = summary
        val savingAuthor = author
        val savingCategory = category
        val savingTags = tagsText.split(",").map { it.trim() }.filter { it.isNotEmpty() }
        val savingStatus = articleStatus
        val savingCoverAssetId = coverAssetId
        val view = editor
        if (view == null || !webReady) {
            val now = System.currentTimeMillis().toString()
            val old = vm.data.articles.firstOrNull { it.id == savingId }
            vm.saveArticle(ArticleDocument(savingId, savingTitle, html, old?.createdAt ?: now, now,
                savingSubtitle, savingSummary, savingAuthor, savingCoverAssetId, savingCategory, savingTags,
                savingStatus, html.replace(Regex("<[^>]*>"), "").length))
            saved = true
            if (showToast) vm.toast("文章已保存")
            return
        }
        view.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
            val current = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
            html = current
            val now = System.currentTimeMillis().toString()
            val old = vm.data.articles.firstOrNull { it.id == savingId }
            vm.saveArticle(ArticleDocument(savingId, savingTitle, current, old?.createdAt ?: now, now,
                savingSubtitle, savingSummary, savingAuthor, old?.coverAssetId ?: "", savingCategory, savingTags,
                old?.status ?: "draft", current.replace(Regex("<[^>]*>"), "").length))
            saved = true
            if (showToast) vm.toast("文章已保存")
        }
    }
    fun newArticle() {
        saveDocument()
        articleId = vm.newId()
        title = "未命名文章"
        subtitle = ""; summary = ""; author = ""; category = ""; tagsText = ""; articleStatus = "draft"; coverAssetId = ""
        html = "<p><br></p>"
        previewMode = false
        showArticleList = false
        if (webReady) editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(html)});setEditable(true);", null)
        saved = false
    }
    fun openArticle(article: ArticleDocument) {
        articleId = article.id
        title = article.title
        html = article.html
        subtitle = article.subtitle
        summary = article.summary
        author = article.author
        category = article.category
        tagsText = article.tags.joinToString(", ")
        articleStatus = article.status
        coverAssetId = article.coverAssetId
        showArticleList = false
        previewMode = false
        if (webReady) editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(article.html)});setEditable(true);", null)
        saved = true
    }

    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->
        uris.forEach { uri ->
            runCatching {
                val mime = context.contentResolver.getType(uri) ?: "image/jpeg"
                val ext = when (mime.lowercase(Locale.ROOT)) { "image/png" -> "png"; "image/webp" -> "webp"; "image/gif" -> "gif"; "image/heic" -> "heic"; else -> "jpg" }
                val id = vm.newId() + (0..999).random().toString()
                val dir = File(context.filesDir, "article_media").apply { mkdirs() }
                val target = File(dir, "$id.$ext")
                context.contentResolver.openInputStream(uri)?.use { input -> target.outputStream().use { output -> input.copyTo(output) } }
                    ?: error("无法读取图片")
                val relative = "article_media/${target.name}"
                vm.saveMediaAsset(MediaAsset(id, target.name, mime, relative, target.length(), System.currentTimeMillis().toString()))
                insert("<p><img src='https://editor.local/assets/$id' alt='${target.name}' style='max-width:100%;height:auto;display:block;margin:14px auto'></p>")
            }.onFailure { vm.toast("图片导入失败：${it.message ?: "未知错误"}") }
        }
    }
    val htmlImporter = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) runCatching {
            val raw = context.contentResolver.openInputStream(uri)?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: error("文件为空")
            val safe = sanitizeArticleHtml(raw)
            if (showArticleList) {
                articleId = vm.newId()
                title = "导入文章"
                subtitle = ""; summary = ""; author = ""; category = ""; tagsText = ""
                showArticleList = false
            }
            html = safe
            editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(safe)});", null)
            pendingSave++
            vm.toast("HTML 已导入")
        }.onFailure { vm.toast("HTML 导入失败：${it.message ?: "无法读取文件"}") }
    }
    val markdownExporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/markdown")) { uri ->
        if (uri != null) runCatching {
            context.contentResolver.openOutputStream(uri)?.bufferedWriter(Charsets.UTF_8)?.use { it.write(pendingExportMarkdown) }
                ?: error("无法写入文件")
            vm.toast("Markdown 已导出")
        }.onFailure { vm.toast("Markdown 导出失败：${it.message ?: "无法写入文件"}") }
    }
    val htmlExporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/html")) { uri ->
        if (uri != null) runCatching {
            context.contentResolver.openOutputStream(uri)?.bufferedWriter(Charsets.UTF_8)?.use { it.write(pendingExportHtml) }
                ?: error("无法写入文件")
            vm.toast("HTML 已导出")
        }.onFailure { vm.toast("HTML 导出失败：${it.message ?: "无法写入文件"}") }
    }
    fun copyPlainText() {
        editor?.evaluateJavascript("document.getElementById('editor').innerText") { raw ->
            val plain = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull()
                ?: html.replace(Regex("<[^>]*>"), "")
            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            clipboard.setPrimaryClip(ClipData.newPlainText(title, plain))
            vm.toast("已复制纯文本")
        }
    }
    fun copyRichHtml() {
        val view = editor
        if (view == null || !webReady) {
            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            clipboard.setPrimaryClip(ClipData.newPlainText(title, html.replace(Regex("<[^>]*>"), "")))
            vm.toast("已复制纯文本")
            return
        }
        view.evaluateJavascript("(function(){var h=document.getElementById('editor').innerHTML;var d=document.createElement('div');d.innerHTML=h;return JSON.stringify({html:h,text:d.innerText||d.textContent||''});})()") { raw ->
            runCatching {
                val jsonText = org.json.JSONTokener(raw ?: "null").nextValue() as String
                val payload = JSONObject(jsonText)
                val rich = payload.optString("html")
                val plain = payload.optString("text")
                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newHtmlText(title, plain, rich))
                vm.toast("已复制富文本，可粘贴到支持 HTML 的编辑器")
            }.onFailure {
                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newPlainText(title, html.replace(Regex("<[^>]*>"), "")))
                vm.toast("富文本复制失败，已回退为纯文本")
            }
        }
    }

    LaunchedEffect(title, html, articleId, pendingSave, webReady) {
        if (!webReady || showArticleList) return@LaunchedEffect
        saved = false
        delay(1100)
        saveDocument()
    }
    BackHandler {
        if (showArticleList) showArticleList = false else { saveDocument(); onBack() }
    }

    Column(Modifier.fillMaxSize().background(pageBg).systemBarsPadding()) {
        Row(
            Modifier.fillMaxWidth().height(56.dp).background(Color.White).padding(horizontal = 7.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = { saveDocument(); onBack() }) { Icon(Icons.Outlined.ArrowBack, "返回", tint = Color(0xFF777777)) }
            Column(Modifier.weight(1f).padding(start = 4.dp)) {
                BasicTextField(
                    value = title, onValueChange = { title = it; saved = false; pendingSave++ },
                    modifier = Modifier.fillMaxWidth(), singleLine = true,
                    textStyle = androidx.compose.ui.text.TextStyle(color = ink, fontSize = 15.sp, fontWeight = FontWeight.SemiBold),
                    decorationBox = { inner -> Box { if (title.isEmpty()) Text("文章标题", color = Color.LightGray); inner() } }
                )
                Text(if (saved) "已自动保存" else "正在编辑 · 自动保存", color = Color(0xFF9A9F9B), fontSize = 10.sp)
            }
            TextButton(onClick = { saveDocument(true) }) { Text("保存", color = accent) }
            TextButton(onClick = { saveDocument(); showArticleList = true }) { Text("文章", color = ink) }
        }

        if (showArticleList) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("我的文章", fontSize = 20.sp, fontWeight = FontWeight.SemiBold, color = ink, modifier = Modifier.weight(1f))
                TextButton(onClick = { htmlImporter.launch(arrayOf("text/html", "application/xhtml+xml", "text/plain")) }) { Text("导入", color = ink) }
                TextButton(onClick = { newArticle() }) { Text("+ 新建文章", color = accent) }
            }
            OutlinedTextField(searchText, { searchText = it }, modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp), singleLine = true, placeholder = { Text("搜索文章标题、摘要或标签") })
            if (vm.data.articles.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("还没有保存的文章，点击「新建文章」开始创作", color = Color.Gray, fontSize = 13.sp)
                }
            } else {
                androidx.compose.foundation.lazy.LazyColumn(
                    Modifier.fillMaxSize().padding(horizontal = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(filteredArticles.size, key = { filteredArticles[it].id }) { index ->
                        val item = filteredArticles.getOrNull(index)
                        if (item != null) {
                            Row(
                                Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Color.White)
                                    .clickable { openArticle(item) }.padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(Modifier.weight(1f)) {
                                    Text(item.title.ifBlank { "未命名文章" }, color = ink, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    Text("最近编辑：${item.updatedAt.take(10)} · ${item.html.replace(Regex("<[^>]*>"), "").length} 字", color = Color.Gray, fontSize = 11.sp, modifier = Modifier.padding(top = 5.dp))
                                }
                                Column(horizontalAlignment = Alignment.End) {
                                    TextButton(onClick = {
                                        val now = System.currentTimeMillis().toString()
                                        val copy = item.copy(id = vm.newId(), title = item.title + "（副本）", createdAt = now, updatedAt = now)
                                        vm.saveArticle(copy)
                                    }) { Text("复制", color = accent) }
                                    TextButton(onClick = { showDeleteConfirm = item }) { Text("删除", color = Color(0xFFCC5555)) }
                                }
                            }
                        }
                    }
                }
            }
        } else {
            Row(
                Modifier.fillMaxWidth().background(Color.White).horizontalScroll(rememberScrollState())
                    .padding(horizontal = 9.dp, vertical = 7.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                EditorTool("撤销") { runJs("restoreSelection();document.execCommand('undo');saveSelection();") }
                EditorTool("重做") { runJs("restoreSelection();document.execCommand('redo');saveSelection();") }
                EditorTool("预览", previewMode) {
                    previewMode = !previewMode
                    editor?.evaluateJavascript("setEditable(${!previewMode});", null)
                }
                EditorTool("全选") { runJs("document.getElementById('editor').focus();document.execCommand('selectAll');saveSelection();") }
                EditorTool("复制富文本") { copyRichHtml() }
                EditorTool("复制纯文本") { copyPlainText() }
                EditorTool("兼容检查") {
                    editor?.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
                        val current = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
                        compatibilityWarnings = articleCompatibilityWarnings(current)
                        showCompatibilityReport = true
                    }
                }
                EditorTool("导入HTML") { htmlImporter.launch(arrayOf("text/html", "application/xhtml+xml", "text/plain")) }
                EditorTool("导出HTML") {
                    editor?.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
                        pendingExportHtml = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
                        htmlExporter.launch("${title.ifBlank { "文章" }}.html")
                    }
                }
                EditorTool("导出Markdown") {
                    editor?.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
                        val current = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
                        pendingExportMarkdown = articleHtmlToMarkdown(current)
                        markdownExporter.launch("${title.ifBlank { "文章" }}.md")
                    }
                }
                EditorTool("版本记录") { saveDocument(); showRevisionList = true }
                EditorTool("文章信息") { showArticleInfo = true }
                EditorTool("保存整篇模板") {
                    editor?.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
                        val fullHtml = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
                        if (fullHtml.isBlank()) vm.toast("文章内容为空，无法保存模板")
                        else {
                            vm.saveStyle(StyleModule(vm.newId(), title.ifBlank { "未命名整篇模板" }, "整篇模板", fullHtml, System.currentTimeMillis().toString()))
                            vm.toast("已保存到模板中心")
                        }
                    }
                }
                EditorTool("插入链接") { dialogValue = ""; showLink = true }
                EditorTool("模块上移", selectedBlockHtml.isNotBlank()) { runJs("moveSelectedBlock(-1)") }
                EditorTool("模块下移", selectedBlockHtml.isNotBlank()) { runJs("moveSelectedBlock(1)") }
                EditorTool("复制模块", selectedBlockHtml.isNotBlank()) { runJs("duplicateSelectedBlock()") }
                EditorTool("删除模块", selectedBlockHtml.isNotBlank()) { runJs("deleteSelectedBlock()"); selectedBlockHtml = "" }
                EditorTool("保存为样式", selectedBlockHtml.isNotBlank()) {
                    vm.saveStyle(StyleModule(vm.newId(), "我的模块", "自定义组件", selectedBlockHtml, System.currentTimeMillis().toString()))
                    vm.toast("已保存到「我的 - 样式」")
                }
            }

            AndroidView(
                factory = { ctx ->
                    WebView(ctx).apply {
                        settings.javaScriptEnabled = true
                        settings.domStorageEnabled = false
                        settings.allowFileAccess = false
                        settings.allowContentAccess = false
                        settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
                        settings.javaScriptCanOpenWindowsAutomatically = false
                        isVerticalScrollBarEnabled = true
                        setBackgroundColor(android.graphics.Color.WHITE)
                        addJavascriptInterface(ArticleEditorBridge(
                            { value -> html = value; saved = false; pendingSave++ },
                            { value -> selectedBlockHtml = value }
                        ), "NativeEditor")
                        webViewClient = object : WebViewClient() {
                            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean = true
                            override fun shouldInterceptRequest(view: WebView?, request: WebResourceRequest?): WebResourceResponse? {
                                val url = request?.url ?: return null
                                if (url.host != "editor.local" || !url.path.orEmpty().startsWith("/assets/")) return null
                                val id = url.lastPathSegment ?: return null
                                val asset = vm.data.mediaAssets.firstOrNull { it.id == id } ?: return null
                                val mediaRoot = File(context.filesDir, "article_media").canonicalFile
                                val file = File(context.filesDir, asset.relativePath).canonicalFile
                                if (!file.path.startsWith(mediaRoot.path + File.separator) || !file.isFile) return null
                                return runCatching { WebResourceResponse(asset.mimeType.ifBlank { "application/octet-stream" }, null, file.inputStream()) }.getOrNull()
                            }
                            override fun onPageFinished(view: WebView?, url: String?) {
                                webReady = true
                                view?.evaluateJavascript("setEditorHtml(${JSONObject.quote(html)});", null)
                            }
                        }
                        val page = """
                            <!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
                            <style>
                            *{box-sizing:border-box}html,body{margin:0;padding:0;background:#fff;color:#333;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}
                            #editor{min-height:100vh;padding:24px 18px 100px;outline:none;font-size:16px;line-height:1.9;overflow-wrap:anywhere}
                            #editor:empty:before{content:"从这里开始写文章…";color:#b8bdb9}
                            #editor h1{font-size:26px;line-height:1.4;margin:24px 0 16px}#editor h2{font-size:21px;line-height:1.5;margin:22px 0 14px}
                            #editor h3{font-size:18px;line-height:1.5;margin:18px 0 12px}#editor p{margin:0 0 14px}
                            #editor blockquote{margin:18px 0;padding:10px 14px;border-left:3px solid #159765;background:#f4f8f5;color:#66716a}
                            #editor img{max-width:100%;height:auto;display:block;margin:12px auto}
                            #editor table{width:100%;border-collapse:collapse;table-layout:fixed}#editor td,#editor th{border:1px solid #dfe4e0;padding:8px;min-width:24px;vertical-align:top}
                            #editor a{color:#16865a;text-decoration:underline}#editor hr{border:0;border-top:1px solid #e1e5e2;margin:22px 0}
                            #editor .selected-block{outline:1px dashed #159765;outline-offset:3px}
                            </style></head><body><div id="editor" contenteditable="true" spellcheck="true"></div>
                            <script>
                            const root=document.getElementById('editor');let savedRange=null;let timer=null;
                            function setEditorHtml(v){root.innerHTML=v||'<p><br></p>';saveSelection();}
                            function setEditable(v){root.contentEditable=!!v;if(!v){root.querySelectorAll('.selected-block').forEach(e=>e.classList.remove('selected-block'));}}
                            function selectedBlock(){return root.querySelector('.selected-block');}
                            function duplicateSelectedBlock(){const e=selectedBlock();if(!e)return;const c=e.cloneNode(true);c.classList.remove('selected-block');e.insertAdjacentElement('afterend',c);c.classList.add('selected-block');NativeEditor.blockSelected(c.outerHTML);NativeEditor.changed(root.innerHTML);}
                            function deleteSelectedBlock(){const e=selectedBlock();if(!e)return;e.remove();NativeEditor.blockSelected('');NativeEditor.changed(root.innerHTML);}
                            function moveSelectedBlock(dir){const e=selectedBlock();if(!e)return;if(dir<0&&e.previousElementSibling)e.parentNode.insertBefore(e,e.previousElementSibling);else if(dir>0&&e.nextElementSibling)e.parentNode.insertBefore(e.nextElementSibling,e);NativeEditor.changed(root.innerHTML);}
                            function selectedTable(){const e=selectedBlock();return e?(e.tagName==='TABLE'?e:e.querySelector('table')):null;}
                            function addTableRow(){const t=selectedTable();if(!t||!t.rows.length)return;const r=t.rows[t.rows.length-1];const n=r.cloneNode(true);Array.from(n.cells).forEach(c=>c.innerHTML='<br>');r.parentNode.insertBefore(n,r.nextSibling);NativeEditor.changed(root.innerHTML);}
                            function removeTableRow(){const t=selectedTable();if(!t||t.rows.length<=1)return;t.deleteRow(t.rows.length-1);NativeEditor.changed(root.innerHTML);}
                            function addTableColumn(){const t=selectedTable();if(!t)return;Array.from(t.rows).forEach(r=>{const c=r.insertCell(-1);c.innerHTML='<br>';c.style.border='1px solid #ddd';c.style.padding='8px';});NativeEditor.changed(root.innerHTML);}
                            function removeTableColumn(){const t=selectedTable();if(!t)return;Array.from(t.rows).forEach(r=>{if(r.cells.length>1)r.deleteCell(r.cells.length-1);});NativeEditor.changed(root.innerHTML);}
                            root.addEventListener('click',function(ev){let e=ev.target;while(e&&e!==root&&e.parentElement!==root)e=e.parentElement;if(e&&e!==root){root.querySelectorAll('.selected-block').forEach(x=>x.classList.remove('selected-block'));e.classList.add('selected-block');NativeEditor.blockSelected(e.outerHTML);}});
                            function saveSelection(){const s=window.getSelection();if(s&&s.rangeCount){savedRange=s.getRangeAt(0).cloneRange();}}
                            function restoreSelection(){root.focus();const s=window.getSelection();if(savedRange&&s){s.removeAllRanges();s.addRange(savedRange);}}
                            function insertHtml(v){restoreSelection();const s=window.getSelection();if(!s||!s.rangeCount){root.insertAdjacentHTML('beforeend',v);return;}
                              const r=s.getRangeAt(0);r.deleteContents();const t=document.createElement('div');t.innerHTML=v;const f=document.createDocumentFragment();while(t.firstChild)f.appendChild(t.firstChild);const last=f.lastChild;r.insertNode(f);if(last){r.setStartAfter(last);r.collapse(true);s.removeAllRanges();s.addRange(r);}saveSelection();}
                            root.addEventListener('keyup',saveSelection);root.addEventListener('mouseup',saveSelection);root.addEventListener('touchend',saveSelection);
                            root.addEventListener('input',()=>{saveSelection();clearTimeout(timer);timer=setTimeout(()=>NativeEditor.changed(root.innerHTML),300);});
                            document.addEventListener('selectionchange',()=>{if(document.activeElement===root)saveSelection();});
                            </script></body></html>
                        """.trimIndent()
                        loadDataWithBaseURL("https://editor.local/", page, "text/html", "UTF-8", null)
                        editor = this
                        tag = "article-editor"
                    }
                },
                modifier = Modifier.weight(1f).fillMaxWidth(),
                update = { editor = it }
            )

            Row(
                Modifier.fillMaxWidth().background(Color.White).padding(horizontal = 7.dp, vertical = 5.dp),
                horizontalArrangement = Arrangement.SpaceAround,
                verticalAlignment = Alignment.CenterVertically
            ) {
                EditorPanel.values().forEach { panel ->
                    EditorTool(panel.label, activePanel == panel) { activePanel = panel }
                }
            }
            Column(
                Modifier.fillMaxWidth().background(Color(0xFFFCFDFC)).navigationBarsPadding()
                    .heightIn(min = 92.dp, max = 176.dp).padding(horizontal = 9.dp, vertical = 8.dp)
            ) {
                when (activePanel) {
                    EditorPanel.TEXT -> {
                        Text("文字与段落", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("加粗 B") { command("bold") }; EditorTool("斜体 I") { command("italic") }; EditorTool("下划线 U") { command("underline") }; EditorTool("删除线") { command("strikeThrough") }
                            EditorTool("上标") { command("superscript") }; EditorTool("下标") { command("subscript") }; EditorTool("清除格式") { command("removeFormat") }
                        }
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("正文") { command("formatBlock", "p") }; EditorTool("H1") { command("formatBlock", "h1") }; EditorTool("H2") { command("formatBlock", "h2") }; EditorTool("H3") { command("formatBlock", "h3") }; EditorTool("引用") { command("formatBlock", "blockquote") }
                            EditorTool("左对齐") { command("justifyLeft") }; EditorTool("居中") { command("justifyCenter") }; EditorTool("右对齐") { command("justifyRight") }
                        }
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            listOf("14" to "小", "16" to "标准", "18" to "大", "22" to "特大").forEach { (size, label) -> EditorTool("字号$label") { runJs("restoreSelection();document.execCommand('fontSize',false,'$size');saveSelection();") } }
                            EditorTool("文字色") { runJs("restoreSelection();document.execCommand('foreColor',false,'#159765');saveSelection();") }
                            EditorTool("高亮") { runJs("restoreSelection();document.execCommand('hiliteColor',false,'#FFF1B8');saveSelection();") }
                            EditorTool("无序列表") { command("insertUnorderedList") }; EditorTool("编号列表") { command("insertOrderedList") }
                            EditorTool("缩进") { command("indent") }; EditorTool("减缩进") { command("outdent") }
                            EditorTool("代码段") { command("formatBlock", "pre") }
                            EditorTool("日期") { insert("<span>${java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.getDefault()).format(java.util.Date())}</span>") }
                            EditorTool("分隔线") { insert("<hr style='border:0;border-top:1px solid #ddd;margin:22px 0'><p><br></p>") }
                            EditorTool("Emoji") { insert("✨") }
                            EditorTool("特殊符号") { insert("「」『』· — … ★ ✓ → ※") }
                        }
                    }
                    EditorPanel.IMAGE -> {
                        Text("图片素材", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("本地图片/相册") { imagePicker.launch(arrayOf("image/*")) }
                            EditorTool("插入网络图片") { dialogValue = ""; showImage = true }
                            EditorTool("双图并排") { insert("<table style='width:100%;table-layout:fixed;border-collapse:collapse'><tr><td style='width:50%;padding:3px'><img src='https://placehold.co/600x600?text=Image+1' style='width:100%'></td><td style='width:50%;padding:3px'><img src='https://placehold.co/600x600?text=Image+2' style='width:100%'></td></tr></table>") }
                            EditorTool("图片说明") { insert("<p style='text-align:center;color:#999;font-size:12px;margin-top:6px'>在此输入图片说明</p>") }
                            EditorTool("图片居中") { command("justifyCenter") }
                        }
                        if (vm.data.mediaAssets.isNotEmpty()) {
                            Text("本地图片库 · ${vm.data.mediaAssets.size} 张", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 7.dp))
                            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                vm.data.mediaAssets.forEach { asset ->
                                    EditorTool(asset.fileName.take(12)) {
                                        insert("<p><img src='https://editor.local/assets/${asset.id}' alt='${asset.fileName}' style='max-width:100%;height:auto;display:block;margin:14px auto'></p>")
                                    }
                                    EditorTool("删") {
                                        val used = html.contains(asset.id) || vm.data.articles.any { it.id != articleId && it.html.contains(asset.id) }
                                        if (used) vm.toast("该图片仍被文章引用，不能删除")
                                        else {
                                            File(context.filesDir, asset.relativePath).delete()
                                            vm.deleteMediaAsset(asset.id)
                                            vm.toast("图片已从素材库删除")
                                        }
                                    }
                                }
                            }
                        }
                        Text("本地图片已复制到应用私有目录；网络图片仍依赖原图链接可访问。", color = Color(0xFF929892), fontSize = 10.sp, modifier = Modifier.padding(top = 5.dp))
                    }
                    EditorPanel.COMPONENT -> {
                        Text("公众号排版组件 · 插入后可继续编辑", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("编号标题") { insert("<section style='margin:22px 0 14px;padding:10px 14px;border-left:4px solid #159765;background:#f2f8f4'><p style='margin:0;font-size:19px;font-weight:700;color:#235b43'>01 / 在这里输入标题</p></section>") }
                            EditorTool("引用卡片") { insert("<blockquote style='margin:18px 0;padding:14px 16px;background:#f4f7f5;border-left:3px solid #159765'><p style='margin:0'>在这里输入引用内容</p></blockquote>") }
                            EditorTool("提示卡片") { insert("<section style='margin:18px 0;padding:14px;background:#f1f8f4;border-radius:8px'><p style='margin:0 0 6px;color:#168653;font-weight:700'>温馨提示</p><p style='margin:0'>在这里输入提示内容</p></section>") }
                            EditorTool("分割线") { insert("<hr style='border:0;border-top:1px solid #dfe6e1;margin:24px 0'><p><br></p>") }
                            EditorTool("留白") { insert("<p style='height:24px;margin:0'><br></p>") }
                            EditorTool("数字列表") { insert("<ol><li>第一步</li><li>第二步</li><li>第三步</li></ol>") }
                            EditorTool("色块标题") { insert("<h2 style='margin:22px 0 14px;padding:9px 13px;background:#edf6f0;border-left:4px solid #159765;color:#235b43;font-size:19px'>在这里输入标题</h2>") }
                            EditorTool("边线标题") { insert("<h2 style='margin:22px 0 14px;padding-bottom:9px;border-bottom:1px solid #159765;color:#333;font-size:20px'>在这里输入标题</h2>") }
                            EditorTool("重点段落") { insert("<p style='margin:16px 0;padding:12px 14px;background:#fff8e9;color:#805d24;border-radius:5px;line-height:1.9'>在这里输入需要强调的内容</p>") }
                            EditorTool("首字下沉") { insert("<p style='line-height:2'><span style='float:left;font-size:42px;line-height:1;color:#159765;padding:4px 7px 0 0'>拾</span>在这里继续输入正文内容。</p>") }
                            EditorTool("时间轴") { insert("<section style='border-left:2px solid #b8d8c6;margin:18px 0;padding-left:16px'><p style='margin:0 0 5px;color:#159765;font-weight:700'>01 · 时间节点</p><p style='margin:0 0 16px'>在这里输入事件内容</p><p style='margin:0 0 5px;color:#159765;font-weight:700'>02 · 时间节点</p><p style='margin:0'>在这里输入事件内容</p></section>") }
                            EditorTool("表格") { insert("<table style='width:100%;border-collapse:collapse'><tr><th style='border:1px solid #ddd;padding:8px'>项目</th><th style='border:1px solid #ddd;padding:8px'>内容</th></tr><tr><td style='border:1px solid #ddd;padding:8px'>项目一</td><td style='border:1px solid #ddd;padding:8px'>填写内容</td></tr></table><p><br></p>") }
                            EditorTool("代码块") { insert("<pre style='padding:12px;background:#f4f5f4;white-space:pre-wrap;font-family:monospace;font-size:13px'>在此输入代码或等宽文本</pre>") }
                            EditorTool("关注引导") { insert("<section style='margin:24px 0;padding:18px 14px;text-align:center;background:#f3f8f4;border:1px solid #dcebe1'><p style='margin:0 0 6px;font-weight:700;color:#28724e'>感谢阅读</p><p style='margin:0;font-size:13px;color:#77857c'>关注「拾万句」，查看更多内容</p></section>") }
                            EditorTool("作者简介") { insert("<section style='margin:22px 0;padding:14px;background:#f6f7f6'><p style='margin:0 0 5px;font-weight:700'>关于作者</p><p style='margin:0;font-size:13px;color:#777'>在这里填写作者简介</p></section>") }
                            EditorTool("表格加行", selectedBlockHtml.contains("<table", true)) { runJs("addTableRow()") }
                            EditorTool("表格删行", selectedBlockHtml.contains("<table", true)) { runJs("removeTableRow()") }
                            EditorTool("表格加列", selectedBlockHtml.contains("<table", true)) { runJs("addTableColumn()") }
                            EditorTool("表格删列", selectedBlockHtml.contains("<table", true)) { runJs("removeTableColumn()") }
                        }
                    }
                    EditorPanel.STYLE -> {
                        Text("我的样式 · 选择分类后插入已保存模块", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        if (categories.isEmpty()) Text("暂无样式分类，请在「我的 - 样式」中创建", color = Color.Gray, fontSize = 11.sp)
                        else {
                            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                categories.forEach { category -> EditorTool(category, activeCategory == category) { activeCategory = category } }
                            }
                            Row(Modifier.horizontalScroll(rememberScrollState()).padding(top = 7.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                categoryStyles.forEach { style -> EditorTool(style.name) { insert(style.html) } }
                            }
                        }
                    }
                    EditorPanel.TEMPLATE -> {
                        Text("快速模板 · 插入到当前光标位置", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("简约文章开头") { insert("<h1 style='font-size:25px;line-height:1.5;margin:18px 0'>在这里输入文章标题</h1><p style='color:#999;font-size:12px;margin-bottom:24px'>作者 · 拾万句</p><p>从这里开始写正文……</p>") }
                            EditorTool("杂志风标题") { insert("<section style='margin:24px 0;padding:18px 12px;border-top:2px solid #222;border-bottom:1px solid #aaa'><p style='font-size:24px;font-weight:700;letter-spacing:2px;margin:0'>SECTION TITLE</p><p style='font-size:11px;color:#999;letter-spacing:2px;margin:5px 0 0'>VOL. 01 / EDITORIAL</p></section>") }
                            EditorTool("文艺引用") { insert("<blockquote style='margin:24px 0;padding:18px;background:#f7f4ef;border:0;color:#685f54;font-size:17px;line-height:1.9'><p>“在这里写下一段值得被记住的话。”</p><p style='text-align:right;font-size:12px;color:#aaa'>—— 摘录</p></blockquote>") }
                            EditorTool("清单文章") { insert("<h2 style='font-size:22px;margin:24px 0 14px'>本期清单</h2><ol style='padding-left:22px;line-height:2'><li>第一项内容</li><li>第二项内容</li><li>第三项内容</li></ol>") }
                            EditorTool("结尾段落") { insert("<section style='margin:28px 0 12px;padding-top:16px;border-top:1px solid #e4e8e5'><p style='margin:0;color:#666;line-height:1.9'>愿你在平凡的日子里，也能找到值得珍藏的片刻。</p></section>") }
                            vm.data.styles.filter { it.category == "整篇模板" }.forEach { template ->
                                EditorTool("模板·${template.name}") { fullTemplateConfirm = template }
                            }
                        }
                    }
                }
            }
        }
    }

    if (showImage) EditorInputDialog("插入图片", "输入 https:// 开头的图片地址", dialogValue, { dialogValue = it }, {
        val url = dialogValue.trim()
        if (url.startsWith("https://") || url.startsWith("http://")) insert("<img src='${url.replace("'", "%27")}' alt='图片' style='max-width:100%;height:auto;display:block;margin:14px auto'>")
        else vm.toast("请输入有效的 http/https 图片地址")
        showImage = false
    }) { showImage = false }
    if (showLink) EditorInputDialog("插入链接", "输入 https:// 开头的网址", dialogValue, { dialogValue = it }, {
        val url = dialogValue.trim()
        if (url.startsWith("https://") || url.startsWith("http://")) insert("<a href='${url.replace("'", "%27")}' target='_blank'>链接文字</a>")
        else vm.toast("请输入有效的 http/https 网址")
        showLink = false
    }) { showLink = false }
    if (showDeleteConfirm != null) {
        val target = showDeleteConfirm!!
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = null },
            title = { Text("删除文章？") },
            text = { Text("将删除「${target.title}」及其版本快照。此操作不可撤销。") },
            confirmButton = { TextButton(onClick = { vm.deleteArticle(target.id); showDeleteConfirm = null; if (target.id == articleId) { articleId = vm.newId(); title = "未命名文章"; html = "<p><br></p>"; subtitle = ""; summary = ""; author = ""; category = ""; tagsText = "" } }) { Text("删除", color = Color(0xFFCC5555)) } },
            dismissButton = { TextButton(onClick = { showDeleteConfirm = null }) { Text("取消") } }
        )
    }
    if (showRevisionList) {
        val revisions = vm.data.articleRevisions.filter { it.articleId == articleId }.sortedByDescending { it.createdAt }
        AlertDialog(
            onDismissRequest = { showRevisionList = false },
            title = { Text("历史版本（最近 30 个）") },
            text = {
                Column(Modifier.fillMaxWidth().heightIn(max = 420.dp).verticalScroll(rememberScrollState())) {
                    if (revisions.isEmpty()) Text("暂无历史快照。文章内容发生变化并自动保存后会生成快照。", color = Color.Gray, fontSize = 12.sp)
                    revisions.forEach { revision ->
                        Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(revision.title.ifBlank { "未命名文章" }, fontSize = 13.sp, color = ink)
                                Text("${revision.createdAt} · ${revision.html.replace(Regex("<[^>]*>"), "").length} 字", fontSize = 10.sp, color = Color.Gray)
                            }
                            TextButton(onClick = {
                                vm.restoreArticleRevision(revision)
                                title = revision.title; html = revision.html
                                editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(revision.html)});", null)
                                showRevisionList = false
                                vm.toast("已恢复历史版本")
                            }) { Text("恢复", color = accent) }
                        }
                        HorizontalDivider(color = Color(0xFFE9ECE9))
                    }
                }
            },
            confirmButton = { TextButton(onClick = { showRevisionList = false }) { Text("关闭") } }
        )
    }
    if (fullTemplateConfirm != null) {
        val template = fullTemplateConfirm!!
        AlertDialog(
            onDismissRequest = { fullTemplateConfirm = null },
            title = { Text("应用整篇模板？") },
            text = { Text("将用「${template.name}」替换当前文章正文。建议先保存当前文章。") },
            confirmButton = { TextButton(onClick = {
                html = template.html
                editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(template.html)});", null)
                pendingSave++
                fullTemplateConfirm = null
                vm.toast("整篇模板已应用")
            }) { Text("替换正文", color = Color(0xFFCC5555)) } },
            dismissButton = { TextButton(onClick = { fullTemplateConfirm = null }) { Text("取消") } }
        )
    }
    if (showCompatibilityReport) {
        AlertDialog(
            onDismissRequest = { showCompatibilityReport = false },
            title = { Text("公众号兼容性检查") },
            text = {
                Column(Modifier.fillMaxWidth().heightIn(max = 420.dp).verticalScroll(rememberScrollState())) {
                    if (compatibilityWarnings.isEmpty()) Text("未发现常见风险项。实际发布效果仍以微信公众号编辑器的粘贴与预览为准。", color = Color(0xFF168653), fontSize = 13.sp)
                    compatibilityWarnings.forEachIndexed { index, warning ->
                        Text("${index + 1}. ${warning}", color = ink, fontSize = 12.sp, modifier = Modifier.padding(vertical = 4.dp))
                    }
                    Text("检查仅基于 HTML 结构做静态提示，不代表平台审核或发布保证。", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 8.dp))
                }
            },
            confirmButton = { TextButton(onClick = { showCompatibilityReport = false }) { Text("知道了") } }
        )
    }
    if (showArticleInfo) {
        AlertDialog(
            onDismissRequest = { showArticleInfo = false },
            title = { Text("文章信息") },
            text = {
                Column(Modifier.fillMaxWidth().heightIn(max = 480.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(subtitle, { subtitle = it }, label = { Text("副标题") }, singleLine = true)
                    OutlinedTextField(author, { author = it }, label = { Text("作者") }, singleLine = true)
                    OutlinedTextField(category, { category = it }, label = { Text("分类") }, singleLine = true)
                    OutlinedTextField(tagsText, { tagsText = it }, label = { Text("标签（逗号分隔）") }, singleLine = true)
                    OutlinedTextField(summary, { summary = it }, label = { Text("文章摘要") }, minLines = 3)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("文章状态", color = ink, fontSize = 12.sp, modifier = Modifier.weight(1f))
                        TextButton(onClick = { articleStatus = if (articleStatus == "draft") "complete" else "draft" }) { Text(if (articleStatus == "draft") "草稿" else "已完成", color = accent) }
                    }
                    Text("封面图片", color = ink, fontSize = 12.sp)
                    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        EditorTool("不设置", coverAssetId.isBlank()) { coverAssetId = "" }
                        vm.data.mediaAssets.forEach { asset -> EditorTool(asset.fileName.take(10), coverAssetId == asset.id) { coverAssetId = asset.id } }
                    }
                    Text("文章信息与封面资源 ID 会随文章保存；封面图片暂作为文章素材关联，不自动上传公众号。", color = Color.Gray, fontSize = 11.sp)
                }
            },
            confirmButton = { TextButton(onClick = { showArticleInfo = false; pendingSave++ }) { Text("完成", color = accent) } },
            dismissButton = { TextButton(onClick = { showArticleInfo = false }) { Text("取消") } }
        )
    }
}

@Composable
private fun EditorTool(label: String, selected: Boolean = false, onClick: () -> Unit) {
    Box(
        Modifier.clip(RoundedCornerShape(7.dp))
            .background(if (selected) Color(0xFFE6F5EC) else Color(0xFFF1F3F1))
            .clickable(onClick = onClick).padding(horizontal = 10.dp, vertical = 8.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(label, color = if (selected) Color(0xFF087B4A) else Color(0xFF515852), fontSize = 11.sp,
            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal, maxLines = 1)
    }
}

@Composable
private fun EditorInputDialog(title: String, hint: String, value: String, onChange: (String) -> Unit, onConfirm: () -> Unit, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = { OutlinedTextField(value, onChange, modifier = Modifier.fillMaxWidth(), placeholder = { Text(hint) }, singleLine = true) },
        confirmButton = { TextButton(onClick = onConfirm) { Text("确定") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } }
    )
}

private fun sanitizeArticleHtml(source: String): String {
    val doc = org.jsoup.Jsoup.parseBodyFragment(source)
    doc.select("script,iframe,object,embed,form").remove()
    doc.getAllElements().forEach { element ->
        val attrs = element.attributes().asList().map { it.key }
        attrs.filter { it.startsWith("on", true) }.forEach { element.removeAttr(it) }
        listOf("href", "src", "xlink:href").forEach { key ->
            val value = element.attr(key).trim().lowercase(Locale.ROOT)
            if (value.startsWith("javascript:") || value.startsWith("data:text/html")) element.removeAttr(key)
        }
    }
    return doc.body().html()
}


private fun articleCompatibilityWarnings(html: String): List<String> {
    val warnings = mutableListOf<String>()
    if (Regex("""(?is)<img[^>]+src=["']https?://""").containsMatchIn(html)) warnings += "包含外链图片：复制到公众号后可能需要重新上传或替换为公众号素材。"
    if (Regex("""(?is)<table\b""").containsMatchIn(html)) warnings += "包含表格：请检查手机端是否出现横向溢出或列宽挤压。"
    if (Regex("""(?is)@font-face|https?://[^\s"']+\.(?:woff2?|ttf|otf)""").containsMatchIn(html)) warnings += "可能依赖外部字体文件，公众号环境不一定能加载。"
    if (Regex("""(?is)<(?:iframe|video|audio|object|embed)\b""").containsMatchIn(html)) warnings += "包含音视频或嵌入式媒体标签，公众号正文不一定支持直接承载，建议改用平台素材或链接卡片。"
    if (Regex("""(?is)<p[^>]*>\s*(?:<br\s*/?>)?\s*</p>""").findAll(html).count() > 5) warnings += "空段落较多，可能造成阅读间距过大。"
    if (Regex("""(?is)style=["'][^"']*(?:position\s*:\s*fixed|display\s*:\s*flex|grid)""").containsMatchIn(html)) warnings += "包含复杂布局 CSS，公众号可能清理或改变其显示效果。"
    if (Regex("""(?is)href=["'](?:javascript:|#)""").containsMatchIn(html)) warnings += "存在脚本链接或空锚点，请检查链接是否有效。"
    return warnings
}
private fun articleHtmlToMarkdown(html: String): String {
    var value = html
    value = value.replace(Regex("(?is)<h1[^>]*>(.*?)</h1>")) { "
# ${it.groupValues[1].replace(Regex("<[^>]*>"), "").trim()}

" }
    value = value.replace(Regex("(?is)<h2[^>]*>(.*?)</h2>")) { "
## ${it.groupValues[1].replace(Regex("<[^>]*>"), "").trim()}

" }
    value = value.replace(Regex("(?is)<h([34])[^>]*>(.*?)</h[34]>")) { "
### ${it.groupValues[2].replace(Regex("<[^>]*>"), "").trim()}

" }
    value = value.replace(Regex("(?is)<blockquote[^>]*>(.*?)</blockquote>")) { "
> ${it.groupValues[1].replace(Regex("<[^>]*>"), "").trim()}

" }
    value = value.replace(Regex("(?is)<li[^>]*>(.*?)</li>")) { "- ${it.groupValues[1].replace(Regex("<[^>]*>"), "").trim()}
" }
    value = value.replace(Regex("(?is)<(strong|b)[^>]*>(.*?)</\\1>")) { "**${it.groupValues[2].replace(Regex("<[^>]*>"), "")}**" }
    value = value.replace(Regex("(?is)<(em|i)[^>]*>(.*?)</\\1>")) { "*${it.groupValues[2].replace(Regex("<[^>]*>"), "")}*" }
    value = value.replace(Regex("(?is)<br\\s*/?>"), "
")
    value = value.replace(Regex("(?is)</p>|</div>|</section>|</tr>"), "

")
    value = value.replace(Regex("(?is)<hr[^>]*>"), "
---
")
    value = value.replace(Regex("(?is)<[^>]+>"), "")
    value = org.jsoup.parser.Parser.unescapeEntities(value, false)
    return value.replace(Regex("\\n{3,}"), "

").trim()
}

