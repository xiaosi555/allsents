package com.shiwanju.app.ui

import android.os.Handler
import android.os.Looper
import android.webkit.JavascriptInterface
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.shiwanju.app.data.ArticleDocument
import org.json.JSONObject

private class ArticleEditorBridge(private val onChange: (String) -> Unit) {
    private val main = Handler(Looper.getMainLooper())
    @JavascriptInterface fun changed(value: String) { main.post { onChange(value) } }
}

@Composable
fun ArticleEditorScreen(vm: AppViewModel, onBack: () -> Unit) {
    var title by remember { mutableStateOf("未命名文章") }
    val articleId = remember { vm.newId() }
    var html by remember { mutableStateOf("<p><br></p>") }
    var editor by remember { mutableStateOf<WebView?>(null) }
    var activeCategory by remember { mutableStateOf("") }
    var showLink by remember { mutableStateOf(false) }
    var showImage by remember { mutableStateOf(false) }
    var showTable by remember { mutableStateOf(false) }
    var dialogValue by remember { mutableStateOf("") }
    var saved by remember { mutableStateOf(false) }
    var previewMode by remember { mutableStateOf(false) }
    val categories = vm.data.styles.map { it.category.trim() }.filter { it.isNotEmpty() }.distinct()
    val categoryStyles = vm.data.styles.filter { it.category == activeCategory }
    BackHandler { onBack() }

    fun command(name: String, value: String? = null) {
        val v = value?.let { JSONObject.quote(it) } ?: "null"
        editor?.evaluateJavascript("document.execCommand('$name',false,$v);document.getElementById('editor').focus();", null)
        saved = false
    }
    fun insert(fragment: String) {
        editor?.evaluateJavascript("document.execCommand('insertHTML',false,${JSONObject.quote(fragment)});document.getElementById('editor').focus();", null)
        saved = false
    }
    fun saveDocument() {
        editor?.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
            val current = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
            html = current
            val now = System.currentTimeMillis().toString()
            val old = vm.data.articles.firstOrNull { it.id == articleId }
            vm.saveArticle(ArticleDocument(articleId, title.ifBlank { "未命名文章" }, current, old?.createdAt ?: now, now))
            saved = true
            vm.toast("文章已保存")
        }
    }

    Column(Modifier.fillMaxSize().background(Color(0xFFF5F5F5)).systemBarsPadding()) {
        Row(Modifier.fillMaxWidth().height(54.dp).background(Color.White).padding(horizontal = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) { Icon(Icons.Outlined.ArrowBack, "返回", tint = Color(0xFF999999)) }
            BasicTextField(value = title, onValueChange = { title = it; saved = false },
                modifier = Modifier.weight(1f).padding(horizontal = 8.dp), singleLine = true,
                textStyle = androidx.compose.ui.text.TextStyle(color = Color(0xFF222222), fontSize = 16.sp, fontWeight = FontWeight.Medium),
                decorationBox = { inner -> Box { if (title.isEmpty()) Text("文章标题", color = Color.LightGray); inner() } })
            Text(if (saved) "已保存" else "未保存", color = Color(0xFF999999), fontSize = 11.sp)
            TextButton(onClick = { saveDocument() }) { Text("保存") }
        }
        Row(Modifier.fillMaxWidth().background(Color.White).horizontalScroll(rememberScrollState()).padding(horizontal = 8.dp, vertical = 7.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            EditorTool("撤销") { command("undo") }; EditorTool("重做") { command("redo") }
            EditorTool("B") { command("bold") }; EditorTool("I") { command("italic") }; EditorTool("U") { command("underline") }; EditorTool("S") { command("strikeThrough") }
            EditorTool("正文") { command("formatBlock", "p") }; EditorTool("H1") { command("formatBlock", "h1") }; EditorTool("H2") { command("formatBlock", "h2") }
            EditorTool("引用") { command("formatBlock", "blockquote") }
            EditorTool("左对齐") { command("justifyLeft") }; EditorTool("居中") { command("justifyCenter") }; EditorTool("右对齐") { command("justifyRight") }
        }
        Row(Modifier.fillMaxWidth().background(Color.White).horizontalScroll(rememberScrollState()).padding(start = 8.dp, end = 8.dp, bottom = 8.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            EditorTool("字号") { command("fontSize", "4") }; EditorTool("文字色") { command("foreColor", "#333333") }; EditorTool("高亮") { command("hiliteColor", "#FFF2A8") }
            EditorTool("无序列表") { command("insertUnorderedList") }; EditorTool("编号列表") { command("insertOrderedList") }
            EditorTool("减少缩进") { command("outdent") }; EditorTool("增加缩进") { command("indent") }
            EditorTool("分割线") { insert("<hr style='border:0;border-top:1px solid #ddd;margin:22px 0;'>") }
            EditorTool("链接") { dialogValue = ""; showLink = true }; EditorTool("图片") { dialogValue = ""; showImage = true }
            EditorTool("表格") { showTable = true }
            EditorTool(if (previewMode) "编辑" else "预览") {
                previewMode = !previewMode
                editor?.evaluateJavascript("document.getElementById('editor').contentEditable='${!previewMode}'", null)
            }
        }
        AndroidView(factory = { ctx ->
            WebView(ctx).apply {
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = false
                settings.allowFileAccess = false
                settings.allowContentAccess = false
                settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
                isVerticalScrollBarEnabled = true
                setBackgroundColor(android.graphics.Color.WHITE)
                addJavascriptInterface(ArticleEditorBridge { html = it; saved = false }, "NativeEditor")
                webViewClient = WebViewClient()
                val page = """
                    <!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
                    <style>*{box-sizing:border-box}html,body{margin:0;padding:0;background:#fff;color:#333;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}
                    #editor{min-height:100%;padding:20px 18px 80px;outline:none;font-size:16px;line-height:1.9;overflow-wrap:anywhere}
                    #editor:empty:before{content:"从这里开始写文章…";color:#bbb}
                    #editor h1{font-size:26px;line-height:1.4;margin:24px 0 16px}#editor h2{font-size:21px;line-height:1.5;margin:22px 0 14px}
                    #editor p{margin:0 0 14px}#editor blockquote{margin:18px 0;padding:8px 14px;border-left:3px solid #07c160;background:#f7f7f7;color:#666}
                    #editor img{max-width:100%;height:auto;display:block;margin:12px auto}#editor table{width:100%;border-collapse:collapse}#editor td{border:1px solid #ddd;padding:8px;min-width:30px}</style></head>
                    <body><div id="editor" contenteditable="true" spellcheck="true"></div><script>
                    const root=document.getElementById('editor');root.innerHTML=${JSONObject.quote(html)};
                    let timer;root.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>NativeEditor.changed(root.innerHTML),250)});
                    </script></body></html>
                """.trimIndent()
                loadDataWithBaseURL("https://editor.local/", page, "text/html", "UTF-8", null)
                editor = this
                tag = "article-editor"
            }
        }, modifier = Modifier.weight(1f).fillMaxWidth(), update = { editor = it })

        if (categories.isNotEmpty()) {
            Column(Modifier.fillMaxWidth().background(Color(0xFFF8F8F8)).padding(vertical = 7.dp)) {
                Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 10.dp), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    categories.forEach { cat -> EditorTool(cat, activeCategory == cat) { activeCategory = cat } }
                }
                if (categoryStyles.isNotEmpty()) Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 10.dp, vertical = 7.dp), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    categoryStyles.forEach { style -> EditorTool(style.name) { insert(style.html) } }
                } else Text("该分类暂无样式模块，可在「我的 - 样式」中添加", color = Color.Gray, fontSize = 11.sp, modifier = Modifier.padding(horizontal = 12.dp, vertical = 5.dp))
            }
        } else Text("还没有自定义样式分类，可到「我的 - 样式」中创建", color = Color.Gray, fontSize = 11.sp, modifier = Modifier.fillMaxWidth().background(Color(0xFFF8F8F8)).padding(10.dp))
    }

    if (showLink) EditorInputDialog("插入链接", "输入完整网址", dialogValue, { dialogValue = it }, {
        if (dialogValue.startsWith("https://") || dialogValue.startsWith("http://")) insert("<a href='${dialogValue.replace("'", "%27")}' target='_blank'>链接文字</a>")
        showLink = false
    }) { showLink = false }
    if (showImage) EditorInputDialog("插入图片", "输入图片 URL", dialogValue, { dialogValue = it }, {
        if (dialogValue.startsWith("https://") || dialogValue.startsWith("http://")) insert("<img src='${dialogValue.replace("'", "%27")}' alt='图片' style='max-width:100%;height:auto;'>")
        showImage = false
    }) { showImage = false }
    if (showTable) AlertDialog(onDismissRequest = { showTable = false }, title = { Text("插入表格") }, text = { Text("插入 2 行 × 2 列的可编辑表格") },
        confirmButton = { TextButton(onClick = { insert("<table><tbody><tr><td>内容</td><td>内容</td></tr><tr><td>内容</td><td>内容</td></tr></tbody></table><p><br></p>"); showTable = false }) { Text("插入") } },
        dismissButton = { TextButton(onClick = { showTable = false }) { Text("取消") } })
}

@Composable
private fun EditorTool(label: String, selected: Boolean = false, onClick: () -> Unit) {
    Box(Modifier.clip(RoundedCornerShape(7.dp)).background(if (selected) Color(0xFFE3F6EC) else Color(0xFFF1F1F1)).clickable(onClick = onClick).padding(horizontal = 10.dp, vertical = 8.dp), contentAlignment = Alignment.Center) {
        Text(label, color = if (selected) Color(0xFF078B4B) else Color(0xFF555555), fontSize = 12.sp, fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal)
    }
}
@Composable
private fun EditorInputDialog(title: String, hint: String, value: String, onChange: (String) -> Unit, onConfirm: () -> Unit, onDismiss: () -> Unit) {
    AlertDialog(onDismissRequest = onDismiss, title = { Text(title) }, text = { OutlinedTextField(value, onChange, modifier = Modifier.fillMaxWidth(), placeholder = { Text(hint) }, singleLine = true) },
        confirmButton = { TextButton(onClick = onConfirm) { Text("确定") } }, dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } })
}
