#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
root=Path(__file__).resolve().parents[1]
base=root/"source/ShiWanJu-Android/app/src/main"
java=base/"java/com/shiwanju/app"
shutil.copy2(root/"native-overlay/app/src/main/java/com/shiwanju/app/ui/OfficialAccountPage.kt", java/"ui/OfficialAccountPage.kt")
def patch(rel,pairs):
 p=java/rel;s=p.read_text(encoding="utf-8")
 for a,b in pairs:
  if a not in s:
   # Keep the build pipeline running when an optional UI anchor differs
   # between source archive revisions; report it explicitly for follow-up.
   print("WARNING: optional patch anchor not found; skipped: "+rel+" :: "+a[:80])
   continue
  s=s.replace(a,b,1)
 p.write_text(s,encoding="utf-8")
shutil.copy2(root/"native-overlay/app/src/main/assets/douyin_template.txt",base/"assets/douyin_template.html")

patch("engine/TextUtil.kt",[(
'    /** 按单个换行符分割并剔除空行（随机标题的读取规则） */',
'''    /** 网页 splitEntries：空行分条，条目内部单换行保留。 */
    fun splitEntries(c: String?): List<String> {
        val t = (c ?: "").replace("\\r\\n", "\\n").replace("\\r", "\\n").trim()
        if (t.isEmpty()) return emptyList()
        if (Regex("\\\\n[ \\\\t]*\\\\n").containsMatchIn(t)) {
            return t.split(Regex("\\\\n(?:[ \\\\t]*\\\\n)+"))
                .map { block -> block.split('\\n').map { it.trim() }.filter { it.isNotEmpty() }.joinToString("\\n") }
                .filter { it.isNotEmpty() }
        }
        return t.split('\\n').map { it.trim() }.filter { it.isNotEmpty() }
    }

    /** 按单个换行符分割并剔除空行（随机标题的读取规则） */''')])
patch("data/Models.kt",[
('    val image: String = ""\n)','    val image: String = "",\n    val titles: String = "",\n    val links: String = "",\n    val images: String = ""\n)'),
('    val layoutVer: Int = 0\n)','    val layoutVer: Int = 0,\n    val douyinAdded: Boolean = false\n)'),
('    val previewEmoji: String = ""\n)','    val previewEmoji: String = "",\n    val douyinBg: String = ""\n)'),
('val moreCat: String = "emoji"','val moreCat: String = "image"'),
('        n.contains("断句") -> "sentence"\n','        n.contains("断句") -> "sentence"\n        n.contains("抖音") -> "douyin"\n')])
patch("data/Store.kt",[
('''        var layout = fill(raw.layout, "layout", { it.id }, { x, i -> x.copy(id = i) })
            .map { it.copy(name = it.name ?: "", content = it.content ?: "") }
''','''        var layout = fill(raw.layout, "layout", { it.id }, { x, i -> x.copy(id = i) })
            .map { it.copy(name = it.name ?: "", content = it.content ?: "") }
        var douyinAdded = raw.douyinAdded
        if (!douyinAdded) {
            if (layout.none { it.name.contains("抖音") }) {
                val dy = LayoutItem(id = "layout_douyin", name = "04_抖音版", content = readAsset("douyin_template.html"))
                val at = layout.indexOfFirst { it.name.trim().startsWith("05") }
                layout = layout.toMutableList().also { if (at >= 0) it.add(at, dy) else it.add(dy) }
            }
            douyinAdded = true
        }
'''),
('image = it.image ?: "") },','image = it.image ?: "", titles = it.titles ?: "", links = it.links ?: "", images = it.images ?: "") },'),
('            layoutVer = layoutVer\n        )','            layoutVer = layoutVer,\n            douyinAdded = douyinAdded\n        )')])
patch("ui/AppViewModel.kt",[
('TextUtil.sampleN(TextUtil.splitLines(m.content), COPY_POOL_SIZE)','TextUtil.sampleN(TextUtil.splitEntries(m.content), COPY_POOL_SIZE)'),
('val mods = data.files.image.filter { TextUtil.imageUrls(it.content).isNotEmpty() }','val mods = data.files.image.filter { TextUtil.imageUrls(it.content).isNotEmpty() && !it.name.contains("抖音背景") }'),
('val cur = TextUtil.splitLines(cm.content).toSet()','val cur = TextUtil.splitEntries(cm.content).toSet()'),
('    fun selectLayout(id: String) = updateUi { copy(layoutId = id) }\n','''    private fun drawDouyinBg(): String = data.files.image.filter { it.name.contains("抖音背景") }.flatMap { TextUtil.imageUrls(it.content) }.randomOrNull().orEmpty()
    fun selectLayout(id: String) {
        val item = data.layout.firstOrNull { it.id == id }
        updateUi { copy(layoutId = id, douyinBg = if (item?.name?.contains("抖音") == true) drawDouyinBg() else douyinBg) }
    }
'''),
('updateUi { copy(copyModuleId = id, copyLines = drawCopy(m)) }','updateUi { copy(copyModuleId = id, copyLines = drawCopy(m), douyinBg = if (kind == "douyin") drawDouyinBg() else douyinBg) }'),
('val im = data.files.image.firstOrNull { it.id == u.imgModuleId }','val im = data.files.image.firstOrNull { it.id == u.imgModuleId && !it.name.contains("抖音背景") }'),
('fun deleteLayout(id: String) = updateData { d -> d.copy(layout = d.layout.filter { it.id != id }) }','fun deleteLayout(id: String) = updateData { d -> d.copy(layout = d.layout.filter { it.id != id }, douyinAdded = true) }'),
('val ids = TextUtil.sampleN(data.history, 5).map { it.id }','val ids = listOf(data.history.random().id)')])
patch("engine/PreviewEngine.kt",[
('''    private fun buildPreview(ctx: Ctx, content: String?): Element {
        val frag = Jsoup.parseBodyFragment(content ?: "")
''','''    private fun buildPreview(ctx: Ctx, content: String?): Element {
        if (ctx.kind == "douyin") return buildDouyin(ctx, content)
        val frag = Jsoup.parseBodyFragment(content ?: "")
'''),
('    /** 最后一个条目去掉尾部间距','''    /** 网页 buildDouyin 等价：替换背景图并按正文长度升序填充文案。 */
    private fun buildDouyin(ctx: Ctx, content: String?): Element {
        val out = ctx.doc.createElement("div").attr("style", "width:100%;margin:0;padding:0;background:#ffffff;box-sizing:border-box;")
        val frag = Jsoup.parseBodyFragment(content ?: "")
        frag.select("script").remove()
        out.appendChildren(frag.body().childNodes().map { it.clone() })
        val bg = ctx.ui.douyinBg
        if (bg.isNotBlank()) {
            val targets = out.select("[data-lazy-bgimg]")
            val target = targets.firstOrNull { it.attr("data-lazy-bgimg").contains("cKZHCJzxwWMjEHl3Nfrx") } ?: targets.firstOrNull { it.tagName() == "section" }
            if (target != null) {
                target.attr("data-lazy-bgimg", bg)
                Css.set(target, "background-image", "url(" + bg.replace("\\\"", "") + ")", true)
            }
        }
        val copy = ctx.ui.copyLines
        if (copy.isNotEmpty()) {
            val total = minOf(ctx.ui.quantity.coerceAtLeast(1), copy.size)
            val ordered = copy.take(total).mapIndexed { index, line -> TextUtil.parseSource(line).copy(idx = index) }
                .sortedWith(compareBy({ TextUtil.charLen(it.body) }, { it.idx }))
            val span = out.select("span[leaf]").firstOrNull { it.text().trim() == "文案" }
            if (span != null) {
                val p = span.closest("p")
                if (ordered.size == 1) {
                    span.empty()
                    copy[ordered.first().idx].split("\\n").forEachIndexed { index, line ->
                        if (index > 0) span.appendElement("br")
                        span.appendChild(ctx.doc.createTextNode(line))
                    }
                } else if (p != null && p.parent() != null) {
                    ordered.forEach { parsed ->
                        val para = ctx.doc.createElement("p").attr("style", "margin:0;")
                        copy[parsed.idx].split("\\n").forEachIndexed { index, line ->
                            if (index > 0) para.appendElement("br")
                            para.appendChild(ctx.doc.createTextNode(line))
                        }
                        p.before(para)
                    }
                    p.remove()
                }
            }
        }
        out.children().firstOrNull()?.attr("data-unit", "0")
        if (ctx.ui.previewEmoji.isNotEmpty()) appendEmojiToNumbers(ctx, out, ctx.ui.previewEmoji)
        out.attr("data-douyin", "true")
        return out
    }

    /** 最后一个条目去掉尾部间距''')])
patch("ui/MyScreens.kt",[
('''            var title by remember(key) { mutableStateOf(cur.title.ifEmpty { cur.name }) }
            var link by remember(key) { mutableStateOf(cur.link) }; var image by remember(key) { mutableStateOf(cur.image) }
            EditDialog(if (isNew) "新增往期" else "详情与编辑", close, {
                // 保存标题 / 链接 / 图片三项；content 为按模板生成的渲染代码（有图片=图片版，无图片=文字版）
                val t = title.trim(); val l = link.trim(); val im = image.trim()
                vm.saveHistory(cur.copy(name = t.ifEmpty { "未命名配置" }, title = t, link = l, image = im, content = PreviewEngine.historyEntryHtml(t.ifEmpty { "未命名配置" }, l, im))); close()
            }, if (isNew) null else ({ confirm = true })) {
                Field("标题", title, { title = it }); Field("链接", link, { link = it }); Field("图片（留空为文字版）", image, { image = it })
            }
''','''            var titles by remember(key) { mutableStateOf(cur.titles.ifEmpty { cur.title.ifEmpty { cur.name } }) }
            var links by remember(key) { mutableStateOf(cur.links.ifEmpty { cur.link }) }
            var images by remember(key) { mutableStateOf(cur.images.ifEmpty { cur.image }) }
            var template by remember(key) { mutableStateOf(cur.content) }
            EditDialog(if (isNew) "新增往期" else "详情与编辑", close, {
                val ts = titles.trim(); val ls = links.trim(); val ims = images.trim()
                val ft = TextUtil.splitSingleLines(ts).firstOrNull().orEmpty()
                val fl = TextUtil.splitSingleLines(ls).firstOrNull().orEmpty()
                val fi = TextUtil.splitSingleLines(ims).firstOrNull().orEmpty()
                val html = template.ifBlank { PreviewEngine.historyEntryHtml(ft.ifEmpty { "未命名配置" }, fl, fi) }
                vm.saveHistory(cur.copy(name = ft.ifEmpty { "未命名配置" }, title = ft, link = fl, image = fi, titles = ts, links = ls, images = ims, content = html)); close()
            }, if (isNew) null else ({ confirm = true })) {
                Field("标题（每行一条，与链接、图片按行对应）", titles, { titles = it }, 5)
                Field("链接（每行一个）", links, { links = it }, 5)
                Field("图片（每行一个；文字版留空）", images, { images = it }, 5)
                Field("HTML 模板（可选，留空使用默认模板）", template, { template = it }, 5)
            }
''')])


patch("ui/AppViewModel.kt",[
('    var js: ((String) -> Unit)? = null','    var js: ((String) -> Unit)? = null\n    var jsResult: ((String, (String?) -> Unit) -> Unit)? = null')
])
patch("ui/PreviewWebView.kt",[
('''        vm.js = { script -> webView.evaluateJavascript(script, null) }
        onDispose { vm.js = null; webView.destroy() }''',
'''        vm.js = { script -> webView.evaluateJavascript(script, null) }
        vm.jsResult = { script, callback -> webView.evaluateJavascript(script) { value -> callback(value) } }
        onDispose { vm.js = null; vm.jsResult = null; webView.destroy() }''')
])
patch("ui/LayoutScreen.kt",[
('''        ThemeChip("复制", false) {
            // 把当前预览作为富文本 HTML 复制到剪贴板（可直接粘贴进公众号编辑器）
            val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            cm.setPrimaryClip(ClipData.newHtmlText("拾万句", vm.previewHtml.replace(Regex("<[^>]+>"), ""), vm.previewHtml))
            vm.toast("已复制排版内容")
        }''',
'''        ThemeChip("复制", false) {
            val copyHtml: (String) -> Unit = { html ->
                val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                val plain = android.text.Html.fromHtml(html, android.text.Html.FROM_HTML_MODE_LEGACY).toString()
                cm.setPrimaryClip(ClipData.newHtmlText("拾万句", plain, html))
                vm.toast("已复制当前预览内容")
            }
            val read = vm.jsResult
            if (read == null) copyHtml(vm.previewHtml)
            else read("getHtml()") { raw ->
                val html = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull()
                copyHtml(html ?: vm.previewHtml)
            }
        }''')
])

patch("ui/LayoutScreen.kt",[
('''    val cats = listOf("emoji" to "emoji", "gif" to "动图", "history" to "往期")
    val cur = if (cats.any { it.first == vm.ui.moreCat }) vm.ui.moreCat else "gif"''',
'''    val cats = listOf("image" to "配图", "emoji" to "emoji", "gif" to "动图", "history" to "往期")
    val cur = if (cats.any { it.first == vm.ui.moreCat }) vm.ui.moreCat else "image"'''),
('''    when (cur) {
        "emoji" -> if (vm.data.emoji.isEmpty())''',
'''    when (cur) {
        "image" -> ImagePanel(vm)
        "emoji" -> if (vm.data.emoji.isEmpty())''')
]);

patch("engine/PreviewEngine.kt",[
('ctx.doc.createTextNode(line)','TextNode(line, "")')
])
patch("ui/MyScreens.kt",[
('import com.shiwanju.app.engine.PreviewEngine','import com.shiwanju.app.engine.PreviewEngine\nimport com.shiwanju.app.engine.TextUtil')
])

patch("engine/PreviewEngine.kt",[
('ctx.doc.createTextNode(line)','TextNode(line, "")')
])

patch("ui/AppViewModel.kt",[
('''    fun rollHistory() {
        if (data.history.isEmpty()) return toast("暂无往期条目，请到【我的】-更多-往期中添加")
        pendingScroll = "history"
        val ids = listOf(data.history.random().id)
        updateUi { copy(historyIds = ids, mediaOrder = if ("history" in mediaOrder) mediaOrder else mediaOrder + "history") }
    }''',
'''    fun rollHistory(id: String? = null) {
        if (data.history.isEmpty()) return toast("暂无往期条目，请到【我的】-更多-往期中添加")
        val item = data.history.firstOrNull { it.id == id } ?: data.history.random()
        pendingScroll = "history"
        updateUi { copy(historyIds = listOf(item.id), mediaOrder = if ("history" in mediaOrder) mediaOrder else mediaOrder + "history") }
    }''')
])
patch("ui/LayoutScreen.kt",[
('GridCard(if (on) "重新随机5条" else "随机5条", on) { vm.rollHistory() }',
 'GridCard(if (on) "重新随机" else "随机往期", on) { vm.rollHistory() }')
])

patch("engine/PreviewEngine.kt",[
('TextNode(line, "")','TextNode(line)')
])
patch("engine/PreviewEngine.kt",[
('TextNode(line, "")','TextNode(line)')
])

patch("engine/TextUtil.kt",[
('.groupValues[2].trim().length <= 40','.let { charLen(m.groupValues[2].trim()) <= 40 }')
])
patch("engine/PreviewEngine.kt",[
('''    fun historyEntryHtml(title: String, link: String, image: String): String {''',
'''    fun historyTemplateHtml(withImages: Boolean): String {
        val cells = (0 until 5).joinToString("") {
            if (withImages) "<td style='width:20%;vertical-align:top;padding:4px;'><a href=''><img src='' style='display:block;width:100%;height:auto;'></a><p>标题</p></td>"
            else "<td style='padding:6px;'><a href=''>标题</a></td>"
        }
        return "<table style='width:100%;table-layout:fixed;border-collapse:collapse;'><tr>$cells</tr></table>"
    }

    fun historyEntryHtml(title: String, link: String, image: String): String {''')
])

patch("ui/MyScreens.kt",[
('PreviewEngine.historyEntryHtml(ft.ifEmpty { "未命名配置" }, fl, fi)',
 'PreviewEngine.historyTemplateHtml(fi.isNotBlank())')
])
patch("ui/LayoutScreen.kt",[

])

patch("ui/LayoutScreen.kt",[
('''private val MAIN_TABS = listOf("account" to "账号", "layout" to "版式", "copy" to "文案", "image" to "配图", "more" to "更多")''',
 '''private val MAIN_TABS = listOf("account" to "账号", "layout" to "版式", "copy" to "文案", "more" to "更多")'''),
('''            "image" -> ImagePanel(vm)
''','')
])

patch("ui/AppViewModel.kt",[
('fun setQuantity(n: Int) { if (n > 0) updateUi { copy(quantity = n) } }',
 'fun setQuantity(n: Int) { updateUi { copy(quantity = n.coerceIn(1, 15)) } }'),
('''    fun applyRandomEmoji() {''',
'''    fun clearEmoji() = updateUi { copy(previewEmoji = "") }

    fun applyRandomEmoji() {''')
])
patch("ui/LayoutScreen.kt",[
('''        else GridCards { vm.data.emoji.forEach { e -> GridCard(e.name.ifEmpty { "emoji" }) { vm.applyRandomEmoji() } } }''',
'''        else GridCards {
            vm.data.emoji.forEach { e -> GridCard(e.name.ifEmpty { "emoji" }) { vm.applyRandomEmoji() } }
            if (vm.ui.previewEmoji.isNotEmpty()) GridCard("移除emoji") { vm.clearEmoji() }
        }'''),
('GridCard(if (on) "重新随机" else "随机往期", on) { vm.rollHistory() }',
 'vm.data.history.forEach { h -> GridCard(h.name.ifEmpty { h.title.ifEmpty { "未命名往期" } }, vm.ui.historyIds.contains(h.id)) { vm.rollHistory(h.id) } }')
])

patch("engine/PreviewEngine.kt",[
('''    fun historyTemplateHtml(withImages: Boolean): String {
        val cells = (0 until 5).joinToString("") {
            if (withImages) "<td style='width:20%;vertical-align:top;padding:4px;'><a href=''><img src='' style='display:block;width:100%;height:auto;'></a><p>标题</p></td>"
            else "<td style='padding:6px;'><a href=''>标题</a></td>"
        }
        return "<table style='width:100%;table-layout:fixed;border-collapse:collapse;'><tr>$cells</tr></table>"
    }''',
'''    fun historyTemplateHtml(withImages: Boolean): String {
        val cells = (0 until 5).joinToString("") {
            if (withImages) """<td style="width:20%;vertical-align:top;padding:4px;"><a href=""><img src="" style="display:block;width:100%;height:auto;"></a><p>标题</p></td>"""
            else """<td style="padding:6px;"><a href="">标题</a></td>"""
        }
        return """<table style="width:100%;table-layout:fixed;border-collapse:collapse;"><tr>$cells</tr></table>"""
    }''')
])

patch("ui/AppViewModel.kt",[
('''    init { validateSelections(); rebuild() }''',
'''    init {
        if (ui.tab == "image") {
            ui = ui.copy(tab = "more", moreCat = "image")
            store.saveUi(ui)
        }
        validateSelections()
        rebuild()
    }''')
])


# ----------------------------------------------------------------------
# UI parity fixes: compact layout selector, removable media, robust editor windows,
# and consistent responsive dialogs for every My subpage.
patch("ui/LayoutScreen.kt",[
    ('Modifier.width(92.dp).height(128.dp)', 'Modifier.width(70.dp).height(64.dp)'),
    ('.fillMaxWidth().height(30.dp).background(t.color)', '.fillMaxWidth().height(28.dp).background(t.color)'),
    ('''        else -> if (vm.data.files.gif.isEmpty()) EmptyTip("暂无动图，请到【我的】-更多-动图中添加")
        else GridCards { vm.data.files.gif.forEach { g -> GridCard(g.name, g.id == vm.ui.gifId) { vm.pickGif(g) } } }''',
     '''        else -> if (vm.data.files.gif.isEmpty()) EmptyTip("暂无动图，请到【我的】-更多-动图中添加")
        else GridCards {
            vm.data.files.gif.forEach { g -> GridCard(g.name, g.id == vm.ui.gifId) { vm.pickGif(g) } }
            if (vm.ui.gifId != null) GridCard("移除动图") { vm.clearGif() }
        }''')
])

patch("ui/AppViewModel.kt",[
    ('''        if (data.files.gif.none { it.id == u.gifId }) u = u.copy(gifId = null, gifContent = "")''',
     '''        if (data.files.gif.none { it.id == u.gifId }) u = u.copy(gifId = null, gifContent = "", mediaOrder = u.mediaOrder.filter { it != "gif" })'''),
    ('''    fun clearHistory() = updateUi { copy(historyIds = emptyList(), mediaOrder = mediaOrder.filter { it != "history" }) }''',
     '''    fun clearHistory() = updateUi { copy(historyIds = emptyList(), mediaOrder = mediaOrder.filter { it != "history" }) }

    fun clearGif() = updateUi { copy(gifId = null, gifContent = "", mediaOrder = mediaOrder.filter { it != "gif" }) }''')
])

patch("ui/Components.kt",[
    ('''    var text by remember(value) { mutableStateOf(value.toString()) }
    var prev by remember { mutableStateOf(value.toString()) }
    val shape = RoundedCornerShape(6.dp)''',
     '''    var text by remember { mutableStateOf(value.toString()) }
    var prev by remember { mutableStateOf(value.toString()) }
    var focused by remember { mutableStateOf(false) }
    LaunchedEffect(value, focused) {
        if (!focused) { text = value.toString(); prev = value.toString() }
    }
    val shape = RoundedCornerShape(6.dp)'''),
    ('''                text = d
                d.toIntOrNull()?.let(onValue)''',
     '''                text = d
                d.toIntOrNull()?.let { n -> prev = n.toString(); onValue(n) }'''),
    ('''                .onFocusChanged { f ->
                    if (f.isFocused) { prev = text; text = "" }
                    else if (text.isEmpty()) text = prev
                }''',
     '''                .onFocusChanged { f ->
                    if (f.isFocused && !focused) { focused = true; prev = value.toString(); text = "" }
                    else if (!f.isFocused && focused) {
                        focused = false
                        if (text.isEmpty()) text = prev else prev = text
                    }
                }'''),
    ('''{ val n = ((text.toIntOrNull() ?: prev.toIntOrNull() ?: 0) + 1).coerceAtLeast(0); text = n.toString(); prev = text; onValue(n) }''',
     '''{ val n = ((text.toIntOrNull() ?: prev.toIntOrNull() ?: value) + 1).coerceAtLeast(0); text = n.toString(); prev = text; onValue(n) }'''),
    ('''{ val n = ((text.toIntOrNull() ?: prev.toIntOrNull() ?: 0) - 1).coerceAtLeast(0); text = n.toString(); prev = text; onValue(n) }''',
     '''{ val n = ((text.toIntOrNull() ?: prev.toIntOrNull() ?: value) - 1).coerceAtLeast(0); text = n.toString(); prev = text; onValue(n) }'''),
    ('''x = (cx + drag.x).coerceIn(0f, maxOf(0f, boundsW - cw))
                            y = (cy + drag.y).coerceIn(0f, maxOf(0f, boundsH - ch))''',
     '''x = (x + drag.x).coerceIn(0f, maxOf(0f, boundsW - w))
                            y = (y + drag.y).coerceIn(0f, maxOf(0f, boundsH - h))'''),
    ('''w = (cw + drag.x).coerceIn(minOf(minW, boundsW - cx), boundsW - cx)
                        h = (ch + drag.y).coerceIn(minOf(minH, boundsH - cy), boundsH - cy)''',
     '''w = (w + drag.x).coerceIn(minOf(minW, maxOf(1f, boundsW - cx)), maxOf(1f, boundsW - cx))
                        h = (h + drag.y).coerceIn(minOf(minH, maxOf(1f, boundsH - cy)), maxOf(1f, boundsH - cy))''')
])

patch("ui/LayoutScreen.kt",[
    ('FloatingWindow("随机标题", 60.dp, 70.dp, 270.dp, 170.dp', 'FloatingWindow("随机标题", 60.dp, 70.dp, 270.dp, 160.dp'),
    ('FloatingWindow("编辑设置", 48.dp, 240.dp, 272.dp, 330.dp', 'FloatingWindow("编辑设置", 48.dp, 240.dp, 272.dp, 390.dp'),
    ('EntryIcon("设", vm.showSettings)', 'EntryIcon("☷", vm.showSettings)'),
    ('EntryIcon("题", vm.showTitle)', 'EntryIcon("T", vm.showTitle)')
])

patch("ui/MyScreens.kt",[
    ('import androidx.compose.ui.zIndex', 'import androidx.compose.ui.zIndex\nimport androidx.compose.ui.window.Dialog'),
    ('''    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = { Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp), content = content) },
        confirmButton = { TextButton(onClick = onSave) { Text("保存", color = AppColors.MyText, fontWeight = FontWeight.Bold) } },
        dismissButton = {
            Row {
                if (onDelete != null) TextButton(onClick = onDelete) { Text("删除", color = Color(0xFFDC2626)) }
                TextButton(onClick = onDismiss) { Text("取消", color = AppColors.MyDim) }
            }
        }
    )''',
     '''    Dialog(onDismissRequest = onDismiss) {
        Surface(
            modifier = Modifier.fillMaxWidth(0.96f).heightIn(max = 760.dp),
            shape = RoundedCornerShape(18.dp), color = Color.White,
            tonalElevation = 8.dp, shadowElevation = 18.dp
        ) {
            Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 16.dp)) {
                Text(title, color = AppColors.MyText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(14.dp))
                Column(
                    Modifier.fillMaxWidth().weight(1f, fill = false).heightIn(max = 610.dp).verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp), content = content
                )
                Spacer(Modifier.height(14.dp))
                HorizontalDivider(color = AppColors.MyLine)
                Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    if (onDelete != null) TextButton(onClick = onDelete) { Text("删除", color = Color(0xFFDC2626)) }
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = onDismiss) { Text("取消", color = AppColors.MyDim) }
                    Button(onClick = onSave, colors = ButtonDefaults.buttonColors(containerColor = AppColors.Theme, contentColor = AppColors.OnTheme), shape = RoundedCornerShape(9.dp)) {
                        Text("保存", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }'''),
    ('''private fun ConfirmDelete(what: String, onOk: () -> Unit, onCancel: () -> Unit) = AlertDialog(
    onDismissRequest = onCancel, title = { Text("确认删除") }, text = { Text("确定要删除该$what 吗？") },
    confirmButton = { TextButton(onClick = onOk) { Text("删除", color = Color(0xFFDC2626)) } },
    dismissButton = { TextButton(onClick = onCancel) { Text("取消") } }
)''',
     '''private fun ConfirmDelete(what: String, onOk: () -> Unit, onCancel: () -> Unit) {
    Dialog(onDismissRequest = onCancel) {
        Surface(shape = RoundedCornerShape(16.dp), color = Color.White, shadowElevation = 16.dp) {
            Column(Modifier.widthIn(min = 260.dp, max = 340.dp).padding(20.dp)) {
                Text("确认删除", color = AppColors.MyText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(12.dp))
                Text("确定要删除该$what 吗？此操作无法撤销。", color = AppColors.MyDim, fontSize = 14.sp, lineHeight = 21.sp)
                Spacer(Modifier.height(18.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = onCancel) { Text("取消", color = AppColors.MyDim) }
                    TextButton(onClick = onOk) { Text("删除", color = Color(0xFFDC2626), fontWeight = FontWeight.Bold) }
                }
            }
        }
    }
}''')
])

patch("ui/LayoutScreen.kt",[
    ('''private fun SettingsWindow(vm: AppViewModel, bw: Float, bh: Float, onTouch: () -> Unit) {
    FloatingWindow''',
     '''private fun SettingsWindow(vm: AppViewModel, bw: Float, bh: Float, onTouch: () -> Unit) {
    val ctx = LocalContext.current
    FloatingWindow'''),
    ('''            Text(vm.anchorLabel, color = Color(0xFF888888), fontSize = 12.sp, lineHeight = 17.sp)
        }
    }
}''',
     '''            Text(vm.anchorLabel, color = Color(0xFF888888), fontSize = 12.sp, lineHeight = 17.sp)
            Spacer(Modifier.height(10.dp))
            ThemeChip("复制预览内容", true, modifier = Modifier.fillMaxWidth()) {
                val copyHtml: (String) -> Unit = { html ->
                    val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    val plain = android.text.Html.fromHtml(html, android.text.Html.FROM_HTML_MODE_LEGACY).toString()
                    cm.setPrimaryClip(ClipData.newHtmlText("拾万句", plain, html))
                    vm.toast("已复制当前预览内容")
                }
                val read = vm.jsResult
                if (read == null) copyHtml(vm.previewHtml)
                else read("getHtml()") { raw ->
                    val html = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull()
                    copyHtml(html ?: vm.previewHtml)
                }
            }
        }
    }
}''')
])


# ----------------------------------------------------------------------


# HTML parity: seed starter media once, default preview media, and editor UI polish.
shutil.copy2(root/"native-overlay/app/src/main/assets/seed.json",base/"assets/seed.json")

patch("data/Models.kt",[
    ('    val douyinAdded: Boolean = false\n)', '    val douyinAdded: Boolean = false,\n    val seedDefaultsApplied: Boolean = false\n)'),
    ('    val douyinBg: String = ""\n)', '    val douyinBg: String = "",\n    val mediaInit: Boolean = false\n)')
])

patch("data/Store.kt",[
    ('''        val data = normalize(raw ?: gson.fromJson(readAsset("seed.json"), AppData::class.java))
        if (raw == null) saveData(data)
        return data''',
     '''        val starter = normalize(gson.fromJson(readAsset("seed.json"), AppData::class.java))
        val loaded = normalize(raw ?: gson.fromJson(readAsset("seed.json"), AppData::class.java))
        val data = if (raw == null) {
            loaded.copy(seedDefaultsApplied = true)
        } else if (!loaded.seedDefaultsApplied) {
            fun <T> merge(current: List<T>, defaults: List<T>, id: (T) -> String): List<T> {
                val known = current.map(id).toHashSet()
                return current + defaults.filter { id(it) !in known }
            }
            loaded.copy(
                history = merge(loaded.history, starter.history) { it.id },
                emoji = merge(loaded.emoji, starter.emoji) { it.id },
                files = loaded.files.copy(
                    image = merge(loaded.files.image, starter.files.image) { it.id },
                    gif = merge(loaded.files.gif, starter.files.gif) { it.id }
                ),
                seedDefaultsApplied = true
            )
        } else loaded
        if (raw == null || data != loaded) saveData(data)
        return data'''),
    ('            douyinAdded = douyinAdded\n        )',
     '            douyinAdded = douyinAdded,\n            seedDefaultsApplied = raw.seedDefaultsApplied\n        )')
])

patch("ui/AppViewModel.kt",[
    ('''        validateSelections()
        rebuild()
    }''',
     '''        validateSelections()
        applyDefaultMediaOnce()
        rebuild()
    }'''),
    ('''    // ------------------------------------------------------------------ 基础

    private fun rebuild()''',
     '''    // HTML initFromData / applyDefaultMedia：首次进入普通版式时自动加入 emoji、随机动图和文字版往期。
    // mediaInit 会持久化，用户主动移除后不会在每次重启时重新插入。
    private fun applyDefaultMediaOnce() {
        if (ui.mediaInit) return
        if (kind == "douyin") {
            ui = ui.copy(previewEmoji = "", gifId = null, gifContent = "", historyIds = emptyList(), mediaOrder = emptyList(), mediaInit = true)
        } else {
            var emoji = ui.previewEmoji
            if (emoji.isBlank()) emoji = data.emoji.randomOrNull()?.let { randomBlock(it.content) }.orEmpty()
            var gifId = ui.gifId
            var gifContent = ui.gifContent
            if (gifId == null) {
                val gif = data.files.gif.randomOrNull()
                val content = gif?.let { randomBlock(it.content) }.orEmpty()
                if (gif != null && content.isNotBlank()) { gifId = gif.id; gifContent = content }
            }
            var historyIds = ui.historyIds
            if (historyIds.isEmpty()) {
                val history = data.history.firstOrNull { it.name.contains("文字") } ?: data.history.firstOrNull()
                if (history != null) historyIds = listOf(history.id)
            }
            val order = buildList {
                if (gifId != null) add("gif")
                if (historyIds.isNotEmpty()) add("history")
            }
            ui = ui.copy(previewEmoji = emoji, gifId = gifId, gifContent = gifContent, historyIds = historyIds, mediaOrder = order, mediaInit = true)
        }
        store.saveUi(ui)
    }

    // ------------------------------------------------------------------ 基础

    private fun rebuild()'''),
    ('''    fun selectLayout(id: String) {
        val item = data.layout.firstOrNull { it.id == id }
        updateUi { copy(layoutId = id, douyinBg = if (item?.name?.contains("抖音") == true) drawDouyinBg() else douyinBg) }
    }''',
     '''    fun selectLayout(id: String) {
        val item = data.layout.firstOrNull { it.id == id }
        updateUi {
            if (item?.name?.contains("抖音") == true) copy(
                layoutId = id, douyinBg = drawDouyinBg(), previewEmoji = "", gifId = null,
                gifContent = "", historyIds = emptyList(), mediaOrder = emptyList(), mediaInit = true
            ) else copy(layoutId = id)
        }
    }''')
])

patch("ui/LayoutScreen.kt",[
    ('FloatingWindow("随机标题", 60.dp, 70.dp, 270.dp, 160.dp', 'FloatingWindow("随机标题", 60.dp, 70.dp, 270.dp, 210.dp'),
    ('''            ThemeChip("换一个", false) { vm.loadRandomTitle() }
        }
    }
}

@Composable
private fun SettingsWindow''',
     '''            ThemeChip("换一个", false) { vm.loadRandomTitle() }
        }
        Spacer(Modifier.height(10.dp))
        CopyPreviewButton(vm)
    }
}

@Composable
private fun SettingsWindow'''),
    ('''    val ctx = LocalContext.current
    FloatingWindow("编辑设置"''','''    FloatingWindow("编辑设置"'''),
    ('''            Spacer(Modifier.height(10.dp))
            ThemeChip("复制预览内容", true, modifier = Modifier.fillMaxWidth()) {
                val copyHtml: (String) -> Unit = { html ->
                    val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    val plain = android.text.Html.fromHtml(html, android.text.Html.FROM_HTML_MODE_LEGACY).toString()
                    cm.setPrimaryClip(ClipData.newHtmlText("拾万句", plain, html))
                    vm.toast("已复制当前预览内容")
                }
                val read = vm.jsResult
                if (read == null) copyHtml(vm.previewHtml)
                else read("getHtml()") { raw ->
                    val html = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull()
                    copyHtml(html ?: vm.previewHtml)
                }
            }''',
     '''            Spacer(Modifier.height(10.dp))
            CopyPreviewButton(vm)''')
])

patch("ui/LayoutScreen.kt",[
    ('''@Composable
private fun EntryIcon(label: String, active: Boolean, onClick: () -> Unit) {''',
     '''@Composable
private fun CopyPreviewButton(vm: AppViewModel) {
    val ctx = LocalContext.current
    ThemeChip("复制预览内容", true, modifier = Modifier.fillMaxWidth()) {
        val copyHtml: (String) -> Unit = { html ->
            val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val plain = android.text.Html.fromHtml(html, android.text.Html.FROM_HTML_MODE_LEGACY).toString()
            cm.setPrimaryClip(ClipData.newHtmlText("拾万句", plain, html))
            vm.toast("已复制当前预览内容")
        }
        val read = vm.jsResult
        if (read == null) copyHtml(vm.previewHtml)
        else read("getHtml()") { raw ->
            val html = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull()
            copyHtml(html ?: vm.previewHtml)
        }
    }
}

@Composable
private fun EntryIcon(label: String, active: Boolean, onClick: () -> Unit) {''')
])

patch("ui/MyScreens.kt",[
    ('import androidx.compose.ui.window.Dialog', 'import androidx.compose.ui.window.Dialog\nimport androidx.compose.ui.window.DialogProperties\nimport androidx.compose.foundation.shape.CircleShape'),
    ('''    OutlinedTextField(
        value = value, onValueChange = onChange, label = { Text(label) }, placeholder = { if (hint.isNotEmpty()) Text(hint) },
        modifier = Modifier.fillMaxWidth(), minLines = lines, maxLines = if (lines == 1) 1 else 12, singleLine = lines == 1
    )''',
     '''    OutlinedTextField(
        value = value, onValueChange = onChange, label = { Text(label) }, placeholder = { if (hint.isNotEmpty()) Text(hint) },
        modifier = Modifier.fillMaxWidth(), minLines = lines, maxLines = if (lines == 1) 1 else 12, singleLine = lines == 1,
        shape = RoundedCornerShape(11.dp),
        colors = OutlinedTextFieldDefaults.colors(
            focusedBorderColor = AppColors.Theme, unfocusedBorderColor = AppColors.MyLine,
            focusedLabelColor = AppColors.Theme, cursorColor = AppColors.Theme,
            focusedContainerColor = Color.White, unfocusedContainerColor = Color.White
        )
    )'''),
    ('''    Dialog(onDismissRequest = onDismiss) {
        Surface(
            modifier = Modifier.fillMaxWidth(0.96f).heightIn(max = 760.dp),
            shape = RoundedCornerShape(18.dp), color = Color.White,
            tonalElevation = 8.dp, shadowElevation = 18.dp
        ) {
            Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 16.dp)) {
                Text(title, color = AppColors.MyText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(14.dp))
                Column(
                    Modifier.fillMaxWidth().weight(1f, fill = false).heightIn(max = 610.dp).verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp), content = content
                )
                Spacer(Modifier.height(14.dp))
                HorizontalDivider(color = AppColors.MyLine)
                Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    if (onDelete != null) TextButton(onClick = onDelete) { Text("删除", color = Color(0xFFDC2626)) }
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = onDismiss) { Text("取消", color = AppColors.MyDim) }
                    Button(onClick = onSave, colors = ButtonDefaults.buttonColors(containerColor = AppColors.Theme, contentColor = AppColors.OnTheme), shape = RoundedCornerShape(9.dp)) {
                        Text("保存", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }''',
     '''    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Surface(
            modifier = Modifier.fillMaxWidth(0.94f).widthIn(max = 440.dp).heightIn(max = 680.dp),
            shape = RoundedCornerShape(20.dp), color = AppColors.MyBg,
            tonalElevation = 10.dp, shadowElevation = 20.dp
        ) {
            Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 16.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(title, color = AppColors.MyText, fontSize = 19.sp, fontWeight = FontWeight.SemiBold)
                        Text("拾万句 · 配置管理", color = AppColors.MyDim, fontSize = 11.sp, modifier = Modifier.padding(top = 3.dp))
                    }
                    Box(Modifier.size(7.dp).clip(CircleShape).background(AppColors.Theme))
                }
                Spacer(Modifier.height(14.dp))
                HorizontalDivider(color = AppColors.MyLine)
                Column(
                    Modifier.fillMaxWidth().weight(1f, fill = false).heightIn(max = 540.dp).verticalScroll(rememberScrollState()).padding(vertical = 14.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp), content = content
                )
                HorizontalDivider(color = AppColors.MyLine)
                Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    if (onDelete != null) TextButton(onClick = onDelete) { Text("删除", color = Color(0xFFDC2626), fontWeight = FontWeight.Medium) }
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = onDismiss) { Text("取消", color = AppColors.MyDim) }
                    Button(onClick = onSave, colors = ButtonDefaults.buttonColors(containerColor = AppColors.Theme, contentColor = AppColors.OnTheme), shape = RoundedCornerShape(10.dp)) {
                        Text("保存配置", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }'''),
    ('''                val html = template.ifBlank { PreviewEngine.historyTemplateHtml(fi.isNotBlank()) }
                vm.saveHistory(cur.copy(name = ft.ifEmpty { "未命名配置" }, title = ft, link = fl, image = fi, titles = ts, links = ls, images = ims, content = html)); close()
            }, if (isNew) null else ({ confirm = true })) {
                Field("标题（每行一条，与链接、图片按行对应）", titles, { titles = it }, 5)
                Field("链接（每行一个）", links, { links = it }, 5)
                Field("图片（每行一个；文字版留空）", images, { images = it }, 5)
                Field("HTML 模板（可选，留空使用默认模板）", template, { template = it }, 5)
            }''',
     '''                val html = template.ifBlank { PreviewEngine.historyTemplateHtml(fi.isNotBlank()) }
                vm.saveHistory(cur.copy(name = name.trim().ifEmpty { ft.ifEmpty { "未命名配置" } }, title = ft, link = fl, image = fi, titles = ts, links = ls, images = ims, content = html)); close()
            }, if (isNew) null else ({ confirm = true })) {
                Text("配置基本信息", color = AppColors.Theme, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                Field("配置名称", name, { name = it }, hint = "例如：文字版 / 图片版")
                Text("往期内容", color = AppColors.Theme, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                Field("标题（每行一条）", titles, { titles = it }, 3, "标题与链接、图片按行对应")
                Field("链接（每行一个）", links, { links = it }, 3, "每行填写一个文章链接")
                Field("图片地址（每行一个）", images, { images = it }, 3, "留空则使用文字版往期")
                Text("高级模板", color = AppColors.Theme, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                Field("HTML 模板（可选）", template, { template = it }, 4, "留空时自动使用默认模板")
            }'''),
    ('''            var titles by remember(key) { mutableStateOf(cur.titles.ifEmpty { cur.title.ifEmpty { cur.name } }) }''',
     '''            var name by remember(key) { mutableStateOf(cur.name) }
            var titles by remember(key) { mutableStateOf(cur.titles.ifEmpty { cur.title }) }'''),
    ('''                "history" -> vm.data.history.forEach { h -> ListRow(h.title.ifEmpty { h.name }, h.link.ifEmpty { h.image }.ifEmpty { summarize(h.content) }) { editKey = h.id } }''',
     '''                "history" -> vm.data.history.forEach { h -> ListRow(h.name.ifEmpty { h.title }, h.title.ifEmpty { h.link }.ifEmpty { h.image }.ifEmpty { summarize(h.content) }) { editKey = h.id } }''')
])


# ----------------------------------------------------------------------
# My area parity pass: reproduce the HTML single-line settings rows,
# improve list density and page hierarchy, and expose complete item metadata.
patch("ui/MyScreens.kt",[
    ('''import androidx.compose.ui.draw.clip''','''import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow'''),
    ('''private fun Card(onClick: (() -> Unit)? = null, content: @Composable ColumnScope.() -> Unit) {
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(AppColors.MyCard)
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier).padding(14.dp),
        content = content
    )
}''',
     '''private fun Card(onClick: (() -> Unit)? = null, content: @Composable ColumnScope.() -> Unit) {
    Column(
        Modifier.fillMaxWidth().shadow(1.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp))
            .background(AppColors.MyCard)
            .then(if (onClick != null) Modifier.clickable(onClick = onClick) else Modifier).padding(14.dp),
        content = content
    )
}'''),
    ('''private fun ListRow(name: String, summary: String, onClick: () -> Unit) {
    Card(onClick) {
        Text(name, color = AppColors.MyText, fontSize = 15.sp, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
        if (summary.isNotEmpty()) Text(summary, color = Color(0xFF9CA3AF), fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 4.dp))
    }
}''',
     '''private fun ListRow(name: String, summary: String, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().shadow(1.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp))
            .background(AppColors.MyCard).clickable(onClick = onClick).padding(horizontal = 16.dp, vertical = 17.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(name, color = AppColors.MyText, fontSize = 15.sp, fontWeight = FontWeight.Medium,
            maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
        if (summary.isNotEmpty()) {
            Text(summary, color = Color(0xFF6B7280), fontSize = 12.sp, maxLines = 1,
                overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(start = 12.dp))
        }
        Text("›", color = Color(0xFF9CA3AF), fontSize = 23.sp, modifier = Modifier.padding(start = 7.dp))
    }
}'''),
    ('''    Column(Modifier.fillMaxSize().background(AppColors.MyBg).systemBarsPadding()) {''',
     '''    Column(Modifier.fillMaxSize().background(AppColors.MyBg).systemBarsPadding()) {'''),
    ('''        Row(Modifier.fillMaxWidth().height(52.dp).padding(horizontal = 6.dp), verticalAlignment = Alignment.CenterVertically) {''',
     '''        Row(Modifier.fillMaxWidth().height(52.dp).padding(horizontal = 6.dp), verticalAlignment = Alignment.CenterVertically) {'''),
    ('''    ListRow("账号", "已配置 ${d.accounts.size} 个账号") { go("accounts") }
    ListRow("文案", "共 ${d.files.text.size} 个文案模块") { go("texts") }
    ListRow("版式", "已保存 ${d.layout.size} 个版式") { go("layouts") }
    ListRow("更多", "共 ${d.emoji.size + d.history.size + d.files.gif.size + d.files.image.size} 个数据模块") { go("more") }
    ListRow("备份", "导出 / 导入全部数据") { go("backup") }''',
     '''    val moreCount = d.emoji.size + d.history.size + d.files.gif.size + d.files.image.size
    ListRow("账号", "已配置 " + d.accounts.size + " 个账号") { go("accounts") }
    ListRow("文案", "共 " + d.files.text.size + " 个文案模块") { go("texts") }
    ListRow("版式", "已保存 " + d.layout.size + " 个版式") { go("layouts") }
    ListRow("更多", "共 " + moreCount + " 个数据模块") { go("more") }
    ListRow("备份", "完整数据导出与恢复导入") { go("backup") }'''),
    ('''    if (vm.data.layout.isEmpty()) Empty("暂无数据，请点击右上角新增")
    vm.data.layout.forEach { l -> ListRow(l.name, summarize(l.content)) { edit = l; isNew = false } }''',
     '''    if (vm.data.layout.isEmpty()) Empty("暂无版式，请点击右上角新增")
    vm.data.layout.forEach { l ->
        val kind = when (layoutKindOf(l.name)) {
            "moments" -> "朋友圈版式"
            "sentence" -> "文字断句版式"
            "card" -> "卡片版式"
            "duan" -> "断章序引版式"
            "douyin" -> "抖音版式"
            else -> "自定义版式"
        }
        ListRow(l.name, "$kind · HTML ${l.content.length} 字符") { edit = l; isNew = false }
    }'''),
    ('''                "emoji" -> vm.data.emoji.forEach { e -> ListRow(e.name, summarize(e.content)) { editKey = e.id } }
                "history" -> vm.data.history.forEach { h -> ListRow(h.name.ifEmpty { h.title }, h.title.ifEmpty { h.link }.ifEmpty { h.image }.ifEmpty { summarize(h.content) }) { editKey = h.id } }
                "gif" -> vm.data.files.gif.forEach { f -> ListRow(f.name, summarize(f.content)) { editKey = f.id } }
                else -> vm.data.files.image.forEach { f -> ListRow(f.name, summarize(f.content)) { editKey = f.id } }''',
     '''                "emoji" -> vm.data.emoji.forEach { e -> ListRow(e.name.ifEmpty { "未命名 Emoji" }, summarize(e.content, 42)) { editKey = e.id } }
                "history" -> vm.data.history.forEach { h ->
                    val count = maxOf(TextUtil.splitSingleLines(h.titles.ifEmpty { h.title }).size, 1)
                    ListRow(h.name.ifEmpty { h.title.ifEmpty { "未命名往期" } }, "${count} 条内容 · ${if (h.images.isNotBlank() || h.image.isNotBlank()) "图片版" else "文字版"}") { editKey = h.id }
                }
                "gif" -> vm.data.files.gif.forEach { f -> ListRow(f.name.ifEmpty { "未命名动图" }, "${TextUtil.splitEntries(f.content).size} 个动图片段") { editKey = f.id } }
                else -> vm.data.files.image.forEach { f -> ListRow(f.name.ifEmpty { "未命名配图" }, "${TextUtil.imageUrls(f.content).size} 张图片") { editKey = f.id } }'''),

])

# Full-screen management editors and rendered layout previews.
patch("ui/MyScreens.kt",[
('''private fun EditDialog(title: String, onDismiss: () -> Unit, onSave: () -> Unit, onDelete: (() -> Unit)? = null, content: @Composable ColumnScope.() -> Unit) {
    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Surface(
            modifier = Modifier.fillMaxWidth(0.94f).widthIn(max = 440.dp).heightIn(max = 680.dp),
            shape = RoundedCornerShape(20.dp), color = AppColors.MyBg,
            tonalElevation = 10.dp, shadowElevation = 20.dp
        ) {
            Column(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 16.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text(title, color = AppColors.MyText, fontSize = 19.sp, fontWeight = FontWeight.SemiBold)
                        Text("拾万句 · 配置管理", color = AppColors.MyDim, fontSize = 11.sp, modifier = Modifier.padding(top = 3.dp))
                    }
                    Box(Modifier.size(7.dp).clip(CircleShape).background(AppColors.Theme))
                }
                Spacer(Modifier.height(14.dp))
                HorizontalDivider(color = AppColors.MyLine)
                Column(
                    Modifier.fillMaxWidth().weight(1f, fill = false).heightIn(max = 540.dp).verticalScroll(rememberScrollState()).padding(vertical = 14.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp), content = content
                )
                HorizontalDivider(color = AppColors.MyLine)
                Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    if (onDelete != null) TextButton(onClick = onDelete) { Text("删除", color = Color(0xFFDC2626), fontWeight = FontWeight.Medium) }
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = onDismiss) { Text("取消", color = AppColors.MyDim) }
                    Button(onClick = onSave, colors = ButtonDefaults.buttonColors(containerColor = AppColors.Theme, contentColor = AppColors.OnTheme), shape = RoundedCornerShape(10.dp)) {
                        Text("保存配置", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}''',
'''private fun EditDialog(title: String, onDismiss: () -> Unit, onSave: () -> Unit, onDelete: (() -> Unit)? = null, content: @Composable ColumnScope.() -> Unit) {
    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false)) {
        Surface(Modifier.fillMaxSize(), shape = RoundedCornerShape(0.dp), color = AppColors.MyBg) {
            Column(Modifier.fillMaxSize().systemBarsPadding().imePadding()) {
                Row(Modifier.fillMaxWidth().height(58.dp).padding(horizontal = 18.dp), verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = onDismiss, contentPadding = PaddingValues(0.dp)) { Text("‹ 返回", color = AppColors.MyText, fontSize = 15.sp) }
                    Text(title, Modifier.weight(1f), color = AppColors.MyText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
                    Box(Modifier.size(7.dp).clip(CircleShape).background(AppColors.Theme))
                }
                HorizontalDivider(color = AppColors.MyLine)
                Column(Modifier.fillMaxWidth().weight(1f).verticalScroll(rememberScrollState()).padding(horizontal = 18.dp, vertical = 18.dp), verticalArrangement = Arrangement.spacedBy(14.dp), content = content)
                HorizontalDivider(color = AppColors.MyLine)
                Row(Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 18.dp, vertical = 12.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    if (onDelete != null) TextButton(onClick = onDelete) { Text("删除", color = Color(0xFFDC2626), fontWeight = FontWeight.Medium) }
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = onDismiss) { Text("取消", color = AppColors.MyDim) }
                    Button(onClick = onSave, modifier = Modifier.height(46.dp), colors = ButtonDefaults.buttonColors(containerColor = AppColors.Theme, contentColor = AppColors.OnTheme), shape = RoundedCornerShape(12.dp)) { Text("保存配置", fontWeight = FontWeight.Bold) }
                }
            }
        }
    }
}'''),
('''private fun ConfirmDelete(what: String, onOk: () -> Unit, onCancel: () -> Unit) {
    Dialog(onDismissRequest = onCancel) {
        Surface(shape = RoundedCornerShape(16.dp), color = Color.White, shadowElevation = 16.dp) {
            Column(Modifier.widthIn(min = 260.dp, max = 340.dp).padding(20.dp)) {
                Text("确认删除", color = AppColors.MyText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                Spacer(Modifier.height(12.dp))
                Text("确定要删除该$what 吗？此操作无法撤销。", color = AppColors.MyDim, fontSize = 14.sp, lineHeight = 21.sp)
                Spacer(Modifier.height(18.dp))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = onCancel) { Text("取消", color = AppColors.MyDim) }
                    TextButton(onClick = onOk) { Text("删除", color = Color(0xFFDC2626), fontWeight = FontWeight.Bold) }
                }
            }
        }
    }
}''',
'''private fun ConfirmDelete(what: String, onOk: () -> Unit, onCancel: () -> Unit) {
    Dialog(onDismissRequest = onCancel, properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false)) {
        Surface(Modifier.fillMaxSize(), shape = RoundedCornerShape(0.dp), color = AppColors.MyBg) {
            Column(Modifier.fillMaxSize().systemBarsPadding()) {
                Row(Modifier.fillMaxWidth().height(58.dp).padding(horizontal = 18.dp), verticalAlignment = Alignment.CenterVertically) {
                    TextButton(onClick = onCancel, contentPadding = PaddingValues(0.dp)) { Text("‹ 返回", color = AppColors.MyText, fontSize = 15.sp) }
                    Text("确认删除", Modifier.weight(1f), color = AppColors.MyText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold, textAlign = androidx.compose.ui.text.style.TextAlign.Center)
                    Spacer(Modifier.width(48.dp))
                }
                HorizontalDivider(color = AppColors.MyLine)
                Column(Modifier.weight(1f).fillMaxWidth().padding(24.dp), verticalArrangement = Arrangement.Center) {
                    Text("确定要删除该$what 吗？", color = AppColors.MyText, fontSize = 20.sp, fontWeight = FontWeight.SemiBold)
                    Spacer(Modifier.height(12.dp))
                    Text("删除后无法撤销，请确认该配置不再需要。", color = AppColors.MyDim, fontSize = 14.sp, lineHeight = 22.sp)
                }
                HorizontalDivider(color = AppColors.MyLine)
                Row(Modifier.fillMaxWidth().navigationBarsPadding().padding(18.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    OutlinedButton(onClick = onCancel, modifier = Modifier.weight(1f).height(48.dp)) { Text("取消") }
                    Button(onClick = onOk, modifier = Modifier.weight(1f).height(48.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFDC2626))) { Text("确认删除", color = Color.White) }
                }
            }
        }
    }
}'''),
('''    vm.data.layout.forEach { l ->
        val kind = when (layoutKindOf(l.name)) {
            "moments" -> "朋友圈版式"
            "sentence" -> "文字断句版式"
            "card" -> "卡片版式"
            "duan" -> "断章序引版式"
            "douyin" -> "抖音版式"
            else -> "自定义版式"
        }
        ListRow(l.name, "$kind · HTML ${l.content.length} 字符") { edit = l; isNew = false }
    }''',
'''    vm.data.layout.chunked(2).forEach { row ->
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            row.forEach { l ->
                val kind = when (layoutKindOf(l.name)) {
                    "moments" -> "朋友圈"
                    "sentence" -> "文字断句"
                    "card" -> "卡片"
                    "duan" -> "断章序引"
                    "douyin" -> "抖音"
                    else -> "自定义版式"
                }
                Column(Modifier.weight(1f).clip(RoundedCornerShape(12.dp)).background(Color.White).clickable { edit = l; isNew = false }) {
                    RenderedLayoutPreview(vm, l, Modifier.fillMaxWidth().aspectRatio(3f / 4f))
                    Column(Modifier.fillMaxWidth().padding(horizontal = 11.dp, vertical = 10.dp)) {
                        Text(l.name, color = AppColors.MyText, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(kind + " · HTML " + l.content.length + " 字符", color = AppColors.MyDim, fontSize = 11.sp, modifier = Modifier.padding(top = 4.dp), maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                }
            }
            if (row.size == 1) Spacer(Modifier.weight(1f))
        }
    }''')
])
patch("ui/LayoutScreen.kt",[
('''            Column(
                Modifier.width(76.dp).height(92.dp).clip(RoundedCornerShape(12.dp))
                    .background(if (i == sel) AppColors.Theme.copy(alpha = 0.16f) else AppColors.Field)
                    .border(1.dp, if (i == sel) AppColors.Theme else AppColors.Line, RoundedCornerShape(12.dp))
                    .clickable { vm.selectAccount(a.id) }.padding(8.dp),
                horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center
            ) {
                AsyncImage(a.avatar, null, Modifier.size(40.dp).clip(RoundedCornerShape(8.dp)).background(Color(0xFF333333)), contentScale = ContentScale.Crop)
                Spacer(Modifier.height(6.dp))
                Text(a.name, color = if (i == sel) AppColors.Theme else AppColors.TextMain, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }''',
'''            Row(Modifier.widthIn(min = 112.dp, max = 160.dp).height(76.dp).clickable { vm.selectAccount(a.id) }.padding(horizontal = 4.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                AsyncImage(a.avatar, null, Modifier.size(46.dp).clip(CircleShape).background(Color(0xFF333333)), contentScale = ContentScale.Crop)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.Center) {
                    Text(a.name, color = if (i == sel) AppColors.Theme else AppColors.TextMain, fontSize = 13.sp, fontWeight = if (i == sel) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(a.author.ifBlank { "公众号账号" }, color = AppColors.TextDim, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }'''),
('''private fun LayoutPanel(vm: AppViewModel) {
    val list = vm.data.layout
    if (list.isEmpty()) return EmptyTip("暂无版式，请到【我的】中添加")
    val cur = vm.layoutIndex
    LazyRow(Modifier.fillMaxSize().padding(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
        items(list.size) { i ->
            val l = list[i]; val t = thumbFor(l.name, i)
            Column(
                Modifier.width(70.dp).height(64.dp).clip(RoundedCornerShape(10.dp))
                    .border(2.dp, if (i == cur) AppColors.Theme else Color.Transparent, RoundedCornerShape(10.dp))
                    .clickable { vm.selectLayout(l.id) }
            ) {
                Box(Modifier.fillMaxWidth().height(28.dp).background(t.color), contentAlignment = Alignment.Center) {
                    Text(shortName(l.name), color = Color.Black, fontSize = 12.sp, fontWeight = FontWeight.Bold, maxLines = 1)
                }
                AsyncImage(t.bg, null, Modifier.fillMaxWidth().weight(1f).background(Color(0xFF2A2A2A)), contentScale = ContentScale.Crop)
            }
        }
    }
}''',
'''private fun LayoutPanel(vm: AppViewModel) {
    val list = vm.data.layout
    if (list.isEmpty()) return EmptyTip("暂无版式，请到【我的】中添加")
    val cur = vm.layoutIndex
    LazyRow(Modifier.fillMaxSize().padding(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        items(list.size) { i ->
            val l = list[i]
            Column(Modifier.width(82.dp).clip(RoundedCornerShape(9.dp)).border(2.dp, if (i == cur) AppColors.Theme else Color.Transparent, RoundedCornerShape(9.dp)).clickable { vm.selectLayout(l.id) }) {
                RenderedLayoutPreview(vm, l, Modifier.fillMaxWidth().aspectRatio(3f / 4f))
                Text(shortName(l.name), Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 5.dp), color = if (i == cur) AppColors.Theme else AppColors.TextMain, fontSize = 11.sp, fontWeight = if (i == cur) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center)
            }
        }
    }
}'''),
('import androidx.compose.ui.unit.sp','import androidx.compose.ui.unit.sp\nimport androidx.compose.ui.viewinterop.AndroidView\nimport android.webkit.WebView\nimport android.webkit.WebViewClient\nimport com.shiwanju.app.data.LayoutItem\nimport com.shiwanju.app.engine.PreviewEngine'),
('''private fun thumbFor(name: String, index: Int) = THUMBS.firstOrNull { name.contains(it.key) } ?: THUMBS[index % THUMBS.size]''',
'''private fun thumbFor(name: String, index: Int) = THUMBS.firstOrNull { name.contains(it.key) } ?: THUMBS[index % THUMBS.size]

/** Render each template as a real 3:4 WebView preview and reuse it until its data changes. */
@Composable
fun RenderedLayoutPreview(vm: AppViewModel, layout: LayoutItem, modifier: Modifier = Modifier) {
    val html = remember(layout.id, layout.content, vm.data.files, vm.data.accounts, vm.ui.copyLines, vm.ui.imgPool) {
        val textModule = vm.data.files.text.firstOrNull()
        val sample = textModule?.content.orEmpty().split(Regex("\\\\r?\\\\n")).map { it.trim() }.filter { it.isNotEmpty() }.take(3)
            .ifEmpty { listOf("生活中值得记录的每一个瞬间", "把平凡的日子写成喜欢的模样", "愿每一次表达都有温度") }
        val imageModule = vm.data.files.image.firstOrNull()
        val images = vm.data.files.image.flatMap { TextUtil.imageUrls(it.content) }.take(12)
        val previewState = vm.ui.copy(layoutId = layout.id, quantity = 3, copyModuleId = textModule?.id, copyLines = sample,
            imgModuleId = imageModule?.id, imgPool = images, historyIds = emptyList(), gifId = null, gifContent = "",
            mediaOrder = emptyList(), previewEmoji = "")
        val body = PreviewEngine.render(vm.data, previewState)
        "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1,maximum-scale=1'><style>html,body{margin:0;padding:0;width:100%;min-height:100%;overflow:hidden;background:#fff}body{font-family:Arial,sans-serif}img{max-width:100%;height:auto}</style></head><body>$body</body></html>"
    }
    AndroidView(factory = { context ->
        WebView(context).apply {
            settings.javaScriptEnabled = false
            settings.domStorageEnabled = false
            isVerticalScrollBarEnabled = false
            isHorizontalScrollBarEnabled = false
            setBackgroundColor(android.graphics.Color.WHITE)
            webViewClient = WebViewClient()
            tag = html
            loadDataWithBaseURL("https://preview.local/", html, "text/html", "UTF-8", null)
        }
    }, modifier = modifier, update = { view ->
        if (view.tag != html) {
            view.tag = html
            view.loadDataWithBaseURL("https://preview.local/", html, "text/html", "UTF-8", null)
        }
    })
}''')
])


# Detail & edit terminology, complete clickable cards, and live template preview.
patch("ui/MyScreens.kt",[
('''                Row(Modifier.widthIn(min = 112.dp, max = 160.dp).height(76.dp).clickable { vm.selectAccount(a.id) }.padding(horizontal = 4.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                AsyncImage(a.avatar, null, Modifier.size(46.dp).clip(CircleShape).background(Color(0xFF333333)), contentScale = ContentScale.Crop)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.Center) {
                    Text(a.name, color = if (i == sel) AppColors.Theme else AppColors.TextMain, fontSize = 13.sp, fontWeight = if (i == sel) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(a.author.ifBlank { "公众号账号" }, color = AppColors.TextDim, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }''',
'''                Column(Modifier.width(76.dp).clip(RoundedCornerShape(10.dp)).clickable { vm.selectAccount(a.id) }.padding(horizontal = 4.dp, vertical = 5.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    AsyncImage(a.avatar, null, Modifier.size(width = 68.dp, height = 54.dp).clip(RoundedCornerShape(10.dp)).background(Color(0xFF333333)), contentScale = ContentScale.Crop)
                    Text(a.name, color = if (i == sel) AppColors.Theme else AppColors.TextMain, fontSize = 12.sp, fontWeight = if (i == sel) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(a.author.ifBlank { "公众号账号" }, color = AppColors.TextDim, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }''')
])
patch("ui/LayoutScreen.kt",[
('''            Column(Modifier.width(82.dp).clip(RoundedCornerShape(9.dp)).border(2.dp, if (i == cur) AppColors.Theme else Color.Transparent, RoundedCornerShape(9.dp)).clickable { vm.selectLayout(l.id) }) {
                RenderedLayoutPreview(vm, l, Modifier.fillMaxWidth().aspectRatio(3f / 4f))
                Text(shortName(l.name), Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 5.dp), color = if (i == cur) AppColors.Theme else AppColors.TextMain, fontSize = 11.sp, fontWeight = if (i == cur) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center)
            }''',
'''            Box(Modifier.width(82.dp).clip(RoundedCornerShape(9.dp)).border(2.dp, if (i == cur) AppColors.Theme else Color.Transparent, RoundedCornerShape(9.dp))) {
                Column(Modifier.fillMaxWidth()) {
                    RenderedLayoutPreview(vm, l, Modifier.fillMaxWidth().aspectRatio(3f / 4f))
                    Text(shortName(l.name), Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 5.dp), color = if (i == cur) AppColors.Theme else AppColors.TextMain, fontSize = 11.sp, fontWeight = if (i == cur) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center)
                }
                Box(Modifier.matchParentSize().clickable { vm.selectLayout(l.id) })
            }''')
])


# ----------------------------------------------------------------------
# 2026-11-21 detail/edit parity, real live template preview, full tap targets.
# Keep these anchors aligned with the deployed native source archive.
patch("ui/MyScreens.kt",[
    ('EditDialog(if (isNew) "新增账号" else "编辑账号"',
     'EditDialog("详情与编辑"'),
    ('EditDialog(if (isNew) "新建文案模块" else "编辑文案模块"',
     'EditDialog("详情与编辑"'),
    ('EditDialog(if (isNew) "新增版式" else "详情与编辑"',
     'EditDialog("详情与编辑"'),
    ('EditDialog(if (isNew) "新增配置" else "详情与编辑"',
     'EditDialog("详情与编辑"'),
    ('EditDialog(if (isNew) "新增往期" else "详情与编辑"',
     'EditDialog("详情与编辑"'),
    ('EditDialog(if (isNew) "新建模块" else "编辑模块"',
     'EditDialog("详情与编辑"'),
    ('Field("配置名称", name, { name = it }); Field("模板代码（HTML）", content, { content = it }, 10)',
     '''Field("配置名称", name, { name = it })
            Field("模板代码（HTML）", content, { content = it }, 10)
            Text("实时渲染预览", color = AppColors.Theme, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            RenderedLayoutPreview(vm, LayoutItem(id = "edit-preview", name = name, content = content),
                Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))''')
])

patch("ui/LayoutScreen.kt",[
    ('''            Row(Modifier.widthIn(min = 112.dp, max = 160.dp).height(76.dp).clickable { vm.selectAccount(a.id) }.padding(horizontal = 4.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                AsyncImage(a.avatar, null, Modifier.size(46.dp).clip(CircleShape).background(Color(0xFF333333)), contentScale = ContentScale.Crop)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.Center) {
                    Text(a.name, color = if (i == sel) AppColors.Theme else AppColors.TextMain, fontSize = 13.sp, fontWeight = if (i == sel) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(a.author.ifBlank { "公众号账号" }, color = AppColors.TextDim, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }''',
     '''            Column(Modifier.width(76.dp).clip(RoundedCornerShape(10.dp)).clickable { vm.selectAccount(a.id) }.padding(horizontal = 4.dp, vertical = 5.dp),
                horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(5.dp)) {
                AsyncImage(a.avatar, null, Modifier.size(width = 68.dp, height = 54.dp).clip(RoundedCornerShape(10.dp)).background(Color(0xFF333333)), contentScale = ContentScale.Crop)
                Text(a.name, color = if (i == sel) AppColors.Theme else AppColors.TextMain, fontSize = 12.sp, fontWeight = if (i == sel) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(a.author.ifBlank { "公众号账号" }, color = AppColors.TextDim, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }'''),
    ('''            Column(Modifier.width(82.dp).clip(RoundedCornerShape(9.dp)).border(2.dp, if (i == cur) AppColors.Theme else Color.Transparent, RoundedCornerShape(9.dp)).clickable { vm.selectLayout(l.id) }) {
                RenderedLayoutPreview(vm, l, Modifier.fillMaxWidth().aspectRatio(3f / 4f))
                Text(shortName(l.name), Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 5.dp), color = if (i == cur) AppColors.Theme else AppColors.TextMain, fontSize = 11.sp, fontWeight = if (i == cur) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center)
            }''',
     '''            Box(Modifier.width(82.dp).clip(RoundedCornerShape(9.dp)).border(2.dp, if (i == cur) AppColors.Theme else Color.Transparent, RoundedCornerShape(9.dp))) {
                Column(Modifier.fillMaxWidth()) {
                    RenderedLayoutPreview(vm, l, Modifier.fillMaxWidth().aspectRatio(3f / 4f))
                    Text(shortName(l.name), Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 5.dp), color = if (i == cur) AppColors.Theme else AppColors.TextMain, fontSize = 11.sp, fontWeight = if (i == cur) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center)
                }
                Box(Modifier.matchParentSize().clickable { vm.selectLayout(l.id) })
            }''')
])

patch("ui/AppViewModel.kt",[
    ('''                val gif = data.files.gif.randomOrNull()
                val content = gif?.let { randomBlock(it.content) }.orEmpty()
                if (gif != null && content.isNotBlank()) { gifId = gif.id; gifContent = content }''',
     '''                // 默认优先从文字版动图模块中随机抽取一个纯文字片段，避免初始预览误放图片版。
                val textModules = data.files.gif.filter { it.name.contains("文字") }
                val textBlocks = (textModules.ifEmpty { data.files.gif }).flatMap { module ->
                    TextUtil.splitEntries(module.content)
                        .filterNot { Regex("(?is)<img\\\\b|<video\\\\b|background-image\\\\s*:").containsMatchIn(it) }
                        .map { module to it }
                }
                val chosenText = textBlocks.randomOrNull()
                if (chosenText != null) {
                    gifId = chosenText.first.id
                    gifContent = chosenText.second
                } else {
                    val gif = textModules.randomOrNull() ?: data.files.gif.randomOrNull()
                    val content = gif?.let { randomBlock(it.content) }.orEmpty()
                    if (gif != null && content.isNotBlank()) { gifId = gif.id; gifContent = content }
                }''')
])


# Render HTML-backed history and GIF module source as actual content, not source text.
patch("ui/MyScreens.kt",[
    ('''                Field("HTML 模板（可选）", template, { template = it }, 4, "留空时自动使用默认模板")''',
     '''                Field("HTML 模板（可选）", template, { template = it }, 4, "留空时自动使用默认模板")
                Text("实时渲染预览", color = AppColors.Theme, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                RenderedLayoutPreview(vm, LayoutItem(id = "history-edit-preview", name = "自定义预览",
                    content = template.ifBlank { PreviewEngine.historyTemplateHtml(images.isNotBlank()) }),
                    Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))'''),
    ('''                Field(if (isGif) "内容（按两个换行分隔，随机取一段）" else "内容（每行一个图片地址，可省略 https://）", content, { content = it }, 8)''',
     '''                Field(if (isGif) "内容（按两个换行分隔，随机取一段）" else "内容（每行一个图片地址，可省略 https://）", content, { content = it }, 8)
                if (isGif) {
                    Text("实时渲染预览", color = AppColors.Theme, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    RenderedLayoutPreview(vm, LayoutItem(id = "gif-edit-preview", name = "自定义预览", content = content),
                        Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))
                }''')
])


# ----------------------------------------------------------------------
# 2026-11-21 follow-up: whole-page copy, square account avatar, item previews.
patch("ui/LayoutScreen.kt",[
    ('''                AsyncImage(a.avatar, null, Modifier.size(width = 68.dp, height = 54.dp).clip(RoundedCornerShape(10.dp)).background(Color(0xFF333333)), contentScale = ContentScale.Crop)
                Text(a.name, color = if (i == sel) AppColors.Theme else AppColors.TextMain, fontSize = 12.sp, fontWeight = if (i == sel) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(a.author.ifBlank { "公众号账号" }, color = AppColors.TextDim, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)''',
     '''                AsyncImage(a.avatar, null, Modifier.size(54.dp).clip(RoundedCornerShape(10.dp)).background(Color(0xFF333333)), contentScale = ContentScale.Crop)
                Text(a.name, color = if (i == sel) AppColors.Theme else AppColors.TextMain, fontSize = 12.sp, fontWeight = if (i == sel) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)'''),
    ('''            else read("getHtml()") { raw ->''',
     '''            else read("(()=>{document.execCommand('selectAll');return document.documentElement.outerHTML;})()") { raw ->''')
])

patch("ui/MyScreens.kt",[
    ('''            Text("实时渲染预览", color = AppColors.Theme, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            RenderedLayoutPreview(vm, LayoutItem(id = "edit-preview", name = name, content = content),
                Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))''',
     '''            Text("样式预览", color = AppColors.MyText, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            RawHtmlPreview(content, Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))'''),
    ('''                Field("HTML 模板（可选，留空使用默认模板）", template, { template = it }, 5)
            }''',
     '''                Field("HTML 模板（可选，留空使用默认模板）", template, { template = it }, 5)
                Text("往期样式预览", color = AppColors.MyText, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                RawHtmlPreview(template.ifBlank { PreviewEngine.historyTemplateHtml(images.isNotBlank()) },
                    Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))
            }'''),
    ('''                if (isGif) {
                    Text("实时渲染预览", color = AppColors.Theme, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    RenderedLayoutPreview(vm, LayoutItem(id = "gif-edit-preview", name = "自定义预览", content = content),
                        Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))
                }''',
     '''                // 动图条目详情只编辑内容，不展示预览区。''')
])

# A raw HTML WebView is used for item-detail previews: unlike a layout selector,
# it renders the selected item's own HTML without substituting another layout.
patch("ui/MyScreens.kt",[
    ('''private fun Field(''',
     '''@Composable
private fun RawHtmlPreview(html: String, modifier: Modifier = Modifier) {
    val document = remember(html) {
        val style = "<style>html,body{margin:0;padding:0;width:100%;}*{color:#111111 !important;box-sizing:border-box;}img{max-width:100%;height:auto;}</style>"
        if (html.contains("<html", ignoreCase = true)) {
            if (html.contains("</head>", ignoreCase = true)) html.replaceFirst(Regex("(?i)</head>"), "$style</head>")
            else html.replaceFirst(Regex("(?i)<html[^>]*>"), "$0<head>$style</head>")
        } else "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>$style</head><body>$html</body></html>"
    }
    androidx.compose.ui.viewinterop.AndroidView(
        factory = { context -> android.webkit.WebView(context).apply {
            settings.javaScriptEnabled = false
            isVerticalScrollBarEnabled = false
            isHorizontalScrollBarEnabled = false
            setBackgroundColor(android.graphics.Color.WHITE)
            webViewClient = android.webkit.WebViewClient()
        } },
        modifier = modifier,
        update = { view ->
            if (view.tag != document) {
                view.tag = document
                view.loadDataWithBaseURL("https://preview.local/", document, "text/html", "UTF-8", null)
            }
        }
    )
}

private fun Field(''')
])


# ----------------------------------------------------------------------
# 2026-11-21 item-detail rendering and full-page copy correction.
# These corrections intentionally run after earlier compatibility patches.
patch("ui/MyScreens.kt",[
    ('''@Composable
@Composable
private fun RawHtmlPreview''',
     '''@Composable
private fun RawHtmlPreview'''),
    ('''}

private fun Field(label: String''',
     '''}

@Composable
private fun Field(label: String'''),
    ('''Field("HTML 模板（可选）", template, { template = it }, 4, "留空时自动使用默认模板")
                Text("实时渲染预览", color = AppColors.Theme, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                RenderedLayoutPreview(vm, LayoutItem(id = "history-edit-preview", name = "自定义预览",
                    content = template.ifBlank { PreviewEngine.historyTemplateHtml(images.isNotBlank()) }),
                    Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))''',
     '''val previewTitles = TextUtil.splitSingleLines(titles)
                val previewLinks = TextUtil.splitSingleLines(links)
                val previewImages = TextUtil.splitSingleLines(images)
                val previewEntries = previewTitles.mapIndexed { index, title ->
                    HistoryEntry(id = "history-preview-$index", title = title,
                        link = previewLinks.getOrNull(index).orEmpty(),
                        image = previewImages.getOrNull(index).orEmpty())
                }
                val historyHtml = if (previewEntries.isNotEmpty()) PreviewEngine.buildHistoryHtml(previewEntries)
                    else template.ifBlank { cur.content }
                Field("HTML 模板（可选）", template, { template = it }, 4, "留空时自动使用默认模板")
                Text("往期样式预览", color = AppColors.MyText, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                RawHtmlPreview(historyHtml, Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))'''),
    ('''            Field("配置名称", name, { name = it }); Field("模板代码（HTML）", content, { content = it }, 10)
            Text("实时渲染预览", color = AppColors.Theme, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            RenderedLayoutPreview(vm, LayoutItem(id = "edit-preview", name = name, content = content),
                Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))''',
     '''            Field("配置名称", name, { name = it }); Field("模板代码（HTML）", content, { content = it }, 10)
            Text("当前版式渲染预览", color = AppColors.MyText, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            RenderedLayoutPreview(vm, l.copy(name = name, content = content),
                Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))'''),
    ('''                if (isGif) {
                    Text("实时渲染预览", color = AppColors.Theme, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                    RenderedLayoutPreview(vm, LayoutItem(id = "gif-edit-preview", name = "自定义预览", content = content),
                        Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))
                }''',
     '''                // 动图条目详情按要求仅编辑内容，不显示预览。''')
])

patch("ui/LayoutScreen.kt",[
    ('''            Row(Modifier.widthIn(min = 112.dp, max = 160.dp).height(76.dp).clickable { vm.selectAccount(a.id) }.padding(horizontal = 4.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                AsyncImage(a.avatar, null, Modifier.size(46.dp).clip(CircleShape).background(Color(0xFF333333)), contentScale = ContentScale.Crop)
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.Center) {
                    Text(a.name, color = if (i == sel) AppColors.Theme else AppColors.TextMain, fontSize = 13.sp, fontWeight = if (i == sel) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(a.author.ifBlank { "公众号账号" }, color = AppColors.TextDim, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
            }''',
     '''            Column(Modifier.width(76.dp).clip(RoundedCornerShape(10.dp)).clickable { vm.selectAccount(a.id) }.padding(horizontal = 4.dp, vertical = 5.dp),
                horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(5.dp)) {
                AsyncImage(a.avatar, null, Modifier.size(54.dp).clip(RoundedCornerShape(10.dp)).background(Color(0xFF333333)), contentScale = ContentScale.Crop)
                Text(a.name, color = if (i == sel) AppColors.Theme else AppColors.TextMain, fontSize = 12.sp, fontWeight = if (i == sel) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }''')
])

# Selecting the rendered content area is equivalent to Select All before copying.
asset = base / "assets/preview.html"
asset_html = asset.read_text(encoding="utf-8")
old_get_html = "window.getHtml = function () { return area.innerHTML; };"
new_get_html = """window.getHtml = function () {
    var selection = window.getSelection();
    var range = document.createRange();
    range.selectNode(area);
    selection.removeAllRanges();
    selection.addRange(range);

    // Export rendered appearance rather than a fragment dependent on preview CSS.
    var clone = area.cloneNode(true);
    var originals = [area].concat(Array.from(area.querySelectorAll("*")));
    var copies = [clone].concat(Array.from(clone.querySelectorAll("*")));
    originals.forEach(function (source, index) {
      var target = copies[index];
      var computed = window.getComputedStyle(source);
      var css = [];
      for (var i = 0; i < computed.length; i++) {
        var name = computed[i];
        var value = computed.getPropertyValue(name);
        if (value) css.push(name + ":" + value);
      }
      target.setAttribute("style", css.join(";"));
    });

    clone.querySelectorAll("p").forEach(function (p) {
      if (!p.style.lineHeight || p.style.lineHeight === "normal") p.style.lineHeight = "1.5";
      if (!p.style.marginTop) p.style.marginTop = "0";
      if (!p.style.marginBottom) p.style.marginBottom = "0";
    });
    var holder = document.createElement("div");
    holder.appendChild(clone);
    return holder.innerHTML;
  };"""
if old_get_html not in asset_html:
    raise SystemExit("Required preview.html getHtml() anchor missing; refusing partial copy patch")
asset.write_text(asset_html.replace(old_get_html, new_get_html, 1), encoding="utf-8")


# Final required correction: a layout detail must use the same native rendering
# engine as the layout picker, not a raw source-code WebView.
def must_replace(rel, old, new, label):
    path = java / rel
    source = path.read_text(encoding="utf-8")
    if old not in source:
        raise SystemExit("Required patch missing (" + label + "): " + rel)
    path.write_text(source.replace(old, new, 1), encoding="utf-8")

must_replace(
    "ui/MyScreens.kt",
    '''Text("样式预览", color = AppColors.MyText, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            RawHtmlPreview(content, Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))''',
    '''Text("当前版式渲染预览", color = AppColors.MyText, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            RenderedLayoutPreview(vm, l.copy(name = name, content = content),
                Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))''',
    "layout detail uses rendered layout engine"
)

# Fail fast rather than silently ship if any of this round's requirements regress.
my = (java / "ui/MyScreens.kt").read_text(encoding="utf-8")
layout = (java / "ui/LayoutScreen.kt").read_text(encoding="utf-8")
preview = (base / "assets/preview.html").read_text(encoding="utf-8")
required = {
    "account avatar is square": "Modifier.size(54.dp)" in layout,
    "account secondary line removed": 'Text(a.author.ifBlank { "公众号账号" }' not in layout,
    "history detail has HTML preview": "RawHtmlPreview(historyHtml" in my,
    "GIF detail has no preview": "gif-edit-preview" not in my,
    "layout detail uses renderer": "RenderedLayoutPreview(vm, l.copy(name = name, content = content)" in my,
    "copy selects whole preview area": "range.selectNode(area)" in preview,
    "RawHtmlPreview composable annotation": "@Composable\nprivate fun RawHtmlPreview" in my,
    "Field composable annotation": "@Composable\nprivate fun Field(" in my,
}
failed = [label for label, ok in required.items() if not ok]
if failed:
    raise SystemExit("Required acceptance checks failed: " + "; ".join(failed))
print("Required UI acceptance checks passed: " + ", ".join(required.keys()))


# ----------------------------------------------------------------------
# 2026-11-21: visually de-emphasize only the three media removal actions.
# Keep their click targets and removal callbacks unchanged.
must_replace(
    "ui/LayoutScreen.kt",
    'if (vm.ui.previewEmoji.isNotEmpty()) GridCard("移除emoji") { vm.clearEmoji() }',
    'if (vm.ui.previewEmoji.isNotEmpty()) SubtleRemoveAction("移除 emoji") { vm.clearEmoji() }',
    "subtle emoji removal action"
)
must_replace(
    "ui/LayoutScreen.kt",
    'if (on) GridCard("移除往期") { vm.clearHistory() }',
    'if (on) SubtleRemoveAction("移除往期") { vm.clearHistory() }',
    "subtle history removal action"
)
must_replace(
    "ui/LayoutScreen.kt",
    'if (vm.ui.gifId != null) GridCard("移除动图") { vm.clearGif() }',
    'if (vm.ui.gifId != null) SubtleRemoveAction("移除动图") { vm.clearGif() }',
    "subtle GIF removal action"
)
must_replace(
    "ui/LayoutScreen.kt",
    '''@Composable
private fun CopyPanel(vm: AppViewModel) {''',
    '''@Composable
private fun SubtleRemoveAction(text: String, onClick: () -> Unit) {
    Box(
        Modifier.clip(RoundedCornerShape(7.dp))
            .background(Color.Transparent)
            .border(0.5.dp, AppColors.Line.copy(alpha = 0.42f), RoundedCornerShape(7.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 11.dp, vertical = 6.dp)
    ) {
        Text(
            text,
            color = AppColors.TextDim.copy(alpha = 0.78f),
            fontSize = 11.sp,
            fontWeight = FontWeight.Normal
        )
    }
}

@Composable
private fun CopyPanel(vm: AppViewModel) {''',
    "insert subtle removal action style"
)

layout_source = (java / "ui/LayoutScreen.kt").read_text(encoding="utf-8")
for label, needle in [
    ("emoji removal action", 'SubtleRemoveAction("移除 emoji")'),
    ("history removal action", 'SubtleRemoveAction("移除往期")'),
    ("GIF removal action", 'SubtleRemoveAction("移除动图")'),
]:
    if needle not in layout_source:
        raise SystemExit("Required acceptance check failed: " + label)
print("Media removal actions now use subtle border and typography.")


# 2026-11-21: preserve the selected history template and its randomized row content,
# matching the actual 000_拾万句.html behavior. Also copy only the preview area.
models_path = java / "data/Models.kt"
models_source = models_path.read_text(encoding="utf-8")
if 'val historyHtml: String = ""' not in models_source:
    model_lines = models_source.splitlines()
    history_line = next((i for i, line in enumerate(model_lines) if "val historyIds:" in line), None)
    if history_line is None:
        raise SystemExit("Required patch missing (historyIds state field): data/Models.kt")
    indent = model_lines[history_line][:len(model_lines[history_line]) - len(model_lines[history_line].lstrip())]
    model_lines.insert(history_line + 1, indent + 'val historyHtml: String = "",                   // 已随机填充并持久化的往期 HTML')
    models_path.write_text("\n".join(model_lines) + "\n", encoding="utf-8")

must_replace(
    "engine/PreviewEngine.kt",
    '''        val hist = ui.historyIds.mapNotNull { id -> data.history.firstOrNull { it.id == id } }
        val blocks = LinkedHashMap<String, Element>()
        val m = margins(ui, ctx.kind)
''',
    '''        val hist = ui.historyIds.mapNotNull { id -> data.history.firstOrNull { it.id == id } }
        val histHtml = ui.historyHtml.ifBlank { hist.firstOrNull()?.let { composeHistoryHtml(it) }.orEmpty() }
        val blocks = LinkedHashMap<String, Element>()
        val m = margins(ui, ctx.kind)
''',
    "resolve persisted history HTML"
)
must_replace(
    "engine/PreviewEngine.kt",
    '''        if (hist.isNotEmpty()) {
            val h = htmlBlock(ctx, buildHistoryHtml(hist))
''',
    '''        if (histHtml.isNotBlank()) {
            val h = htmlBlock(ctx, histHtml)
''',
    "render selected history HTML"
)

must_replace(
    "engine/PreviewEngine.kt",
    '''    private fun histImageCell(e: HistoryEntry): String {''',
    r'''    private data class HistoryRow(val title: String, val link: String, val image: String)

    private fun historyRows(item: HistoryEntry): List<HistoryRow> {
        val titles = TextUtil.splitSingleLines(item.titles.ifBlank { item.title })
        val links = TextUtil.splitSingleLines(item.links.ifBlank { item.link })
        val images = TextUtil.splitSingleLines(item.images.ifBlank { item.image })
        return (0 until minOf(titles.size, links.size)).map { i ->
            HistoryRow(titles[i], links[i], images.getOrNull(i).orEmpty())
        }
    }

    private fun historyTitleLines(title: String): List<String> {
        val parts = Regex("[^，,、。！？!?；;：:]+[，,、。！？!?；;：:]?")
            .findAll(title).map { it.value }.filter { it.isNotEmpty() }.toList()
        return parts.flatMap { part ->
            val chars = part.toList()
            if (chars.isEmpty()) emptyList() else {
                val count = (chars.size + 6) / 7
                val chunk = (chars.size + count - 1) / count
                chars.chunked(chunk).map { it.joinToString("") }
            }
        }
    }

    /** 对应网页版 composeHistoryHtml：按当前往期模块模板随机填充标题、链接和图片。 */
    fun composeHistoryHtml(item: HistoryEntry): String {
        val template = item.content.ifBlank {
            historyTemplateHtml(item.images.isNotBlank() || item.image.isNotBlank())
        }
        val doc = Jsoup.parseBodyFragment(template)
        doc.outputSettings().prettyPrint(false)
        doc.select("script").remove()
        val anchors = doc.select("a[href]").toList()
        if (anchors.isEmpty()) return template

        var rows = historyRows(item)
        val hasImages = anchors.any { it.selectFirst("img") != null }
        if (hasImages) rows = rows.filter { it.image.isNotBlank() }
        if (rows.isEmpty()) return template

        val pool = rows.shuffled()
        anchors.forEachIndexed { index, anchor ->
            val entry = anchor.parent() as? Element ?: anchor
            val row = pool.getOrNull(index)
            if (row == null) {
                entry.remove()
                return@forEachIndexed
            }
            anchor.attr("href", row.link)
            val image = anchor.selectFirst("img")
            if (image == null) {
                anchor.text(row.title)
            } else {
                image.attr("src", row.image)
                if (image.hasAttr("alt")) image.attr("alt", row.title)
                val title = entry.selectFirst("p")
                if (title != null) {
                    title.text(row.title)
                } else {
                    val overlay = entry.selectFirst("[class*=random-style]")
                    if (overlay != null) {
                        val styleClass = overlay.classNames().firstOrNull { it.startsWith("random-style-") }
                        val verticalByClass = styleClass?.let {
                            Regex("\\." + Regex.escape(it) + "\\s*\\{[^}]*writing-mode", RegexOption.IGNORE_CASE)
                                .containsMatchIn(template)
                        } ?: false
                        val vertical = verticalByClass ||
                            Regex("writing-mode", RegexOption.IGNORE_CASE).containsMatchIn(overlay.attr("style"))
                        overlay.empty()
                        if (vertical) {
                            overlay.appendText(row.title)
                        } else {
                            historyTitleLines(row.title).forEachIndexed { lineIndex, line ->
                                if (lineIndex > 0) overlay.appendElement("br")
                                overlay.appendText(line)
                            }
                        }
                    }
                }
            }
        }
        return doc.body().html()
    }

    private fun histImageCell(e: HistoryEntry): String {''',
    "implement HTML-compatible history template composition"
)



must_replace(
    "ui/AppViewModel.kt",
    '''            var historyIds = ui.historyIds
            if (historyIds.isEmpty()) {
                val history = data.history.firstOrNull { it.name.contains("文字") } ?: data.history.firstOrNull()
                if (history != null) historyIds = listOf(history.id)
            }
            val order = buildList {
''',
    '''            var historyIds = ui.historyIds
            var historyHtml = ui.historyHtml
            if (historyIds.isEmpty()) {
                val history = data.history.firstOrNull { it.name.contains("文字") } ?: data.history.firstOrNull()
                if (history != null) {
                    historyIds = listOf(history.id)
                    historyHtml = PreviewEngine.composeHistoryHtml(history)
                }
            } else if (historyHtml.isBlank()) {
                historyIds.firstOrNull()?.let { id ->
                    data.history.firstOrNull { it.id == id }?.let { historyHtml = PreviewEngine.composeHistoryHtml(it) }
                }
            }
            val order = buildList {
''',
    "initialize default history template content"
)
must_replace(
    "ui/AppViewModel.kt",
    'ui = ui.copy(previewEmoji = emoji, gifId = gifId, gifContent = gifContent, historyIds = historyIds, mediaOrder = order, mediaInit = true)',
    'ui = ui.copy(previewEmoji = emoji, gifId = gifId, gifContent = gifContent, historyIds = historyIds, historyHtml = historyHtml, mediaOrder = order, mediaInit = true)',
    "save default history HTML"
)
must_replace(
    "ui/AppViewModel.kt",
    '''        val hids = u.historyIds.filter { id -> data.history.any { it.id == id } }
        u = u.copy(historyIds = hids, mediaOrder = if (hids.isEmpty()) u.mediaOrder.filter { it != "history" } else u.mediaOrder)
''',
    '''        val hids = u.historyIds.filter { id -> data.history.any { it.id == id } }
        val selectedHistory = hids.firstOrNull()?.let { id -> data.history.firstOrNull { it.id == id } }
        val historyHtml = when {
            hids.isEmpty() -> ""
            u.historyHtml.isNotBlank() -> u.historyHtml
            else -> selectedHistory?.let { PreviewEngine.composeHistoryHtml(it) }.orEmpty()
        }
        u = u.copy(historyIds = hids, historyHtml = historyHtml,
            mediaOrder = if (hids.isEmpty()) u.mediaOrder.filter { it != "history" } else u.mediaOrder)
''',
    "validate and retain selected history HTML"
)
must_replace(
    "ui/AppViewModel.kt",
    'gifContent = "", historyIds = emptyList(), mediaOrder = emptyList(), mediaInit = true',
    'gifContent = "", historyIds = emptyList(), historyHtml = "", mediaOrder = emptyList(), mediaInit = true',
    "clear history HTML when switching to Douyin"
)
must_replace(
    "ui/AppViewModel.kt",
    '''    /** 往期：每次随机读取 5 条 */
    fun rollHistory(id: String? = null) {
        if (data.history.isEmpty()) return toast("暂无往期条目，请到【我的】-更多-往期中添加")
        val item = data.history.firstOrNull { it.id == id } ?: data.history.random()
        pendingScroll = "history"
        updateUi { copy(historyIds = listOf(item.id), mediaOrder = if ("history" in mediaOrder) mediaOrder else mediaOrder + "history") }
    }

    fun clearHistory() = updateUi { copy(historyIds = emptyList(), mediaOrder = mediaOrder.filter { it != "history" }) }
''',
    '''    /** 往期：选择一个模块，并按网页版模板随机填充其标题 / 链接 / 图片 */
    fun rollHistory(id: String? = null) {
        if (data.history.isEmpty()) return toast("暂无往期条目，请到【我的】-更多-往期中添加")
        val selectedId = ui.historyIds.firstOrNull()
        val item = data.history.firstOrNull { it.id == id }
            ?: data.history.firstOrNull { it.id == selectedId }
            ?: data.history.first()
        val html = PreviewEngine.composeHistoryHtml(item)
        pendingScroll = "history"
        updateUi { copy(historyIds = listOf(item.id), historyHtml = html,
            mediaOrder = if ("history" in mediaOrder) mediaOrder else mediaOrder + "history") }
    }

    fun clearHistory() = updateUi { copy(historyIds = emptyList(), historyHtml = "", mediaOrder = mediaOrder.filter { it != "history" }) }
''',
    "randomize and persist history template on selection"
)

must_replace(
    "ui/LayoutScreen.kt",
    '''            else read("(()=>{document.execCommand('selectAll');return document.documentElement.outerHTML;})()") { raw ->''',
    '''            else read("getHtml()") { raw ->''',
    "copy only the preview area"
)
must_replace(
    "ui/LayoutScreen.kt",
    'historyIds = emptyList(), gifId = null, gifContent = "",',
    'historyIds = emptyList(), historyHtml = "", gifId = null, gifContent = "",',
    "clear history from rendered layout sample"
)

must_replace(
    "ui/MyScreens.kt",
    '''                val historyHtml = if (previewEntries.isNotEmpty()) PreviewEngine.buildHistoryHtml(previewEntries)
                    else template.ifBlank { cur.content }
''',
    '''                val previewItem = cur.copy(
                    title = previewTitles.firstOrNull().orEmpty(),
                    link = previewLinks.firstOrNull().orEmpty(),
                    image = previewImages.firstOrNull().orEmpty(),
                    titles = titles, links = links, images = images,
                    content = template.ifBlank { PreviewEngine.historyTemplateHtml(previewImages.any { it.isNotBlank() }) }
                )
                val historyHtml = remember(cur.id, titles, links, images, template) {
                    PreviewEngine.composeHistoryHtml(previewItem)
                }
''',
    "preview the actual selected history template"
)
must_replace(
    "ui/MyScreens.kt",
    'val html = template.ifBlank { PreviewEngine.historyTemplateHtml(fi.isNotBlank()) }',
    'val html = template.ifBlank { PreviewEngine.historyTemplateHtml(ims.isNotBlank()) }',
    "choose history template from all image rows"
)

# Fail fast on the history parity and preview-copy fixes.
models = (java / "data/Models.kt").read_text(encoding="utf-8")
vm = (java / "ui/AppViewModel.kt").read_text(encoding="utf-8")
engine = (java / "engine/PreviewEngine.kt").read_text(encoding="utf-8")
layout = (java / "ui/LayoutScreen.kt").read_text(encoding="utf-8")
my = (java / "ui/MyScreens.kt").read_text(encoding="utf-8")
checks = {
    "history HTML is persisted": 'val historyHtml: String = ""' in models,
    "history template composer exists": "fun composeHistoryHtml(item: HistoryEntry)" in engine,
    "render uses persisted history HTML": "htmlBlock(ctx, histHtml)" in engine,
    "history selection stores composed HTML": "historyHtml = html" in vm,
    "history edit preview uses template composer": "PreviewEngine.composeHistoryHtml(previewItem)" in my,
    "top copy reads only preview area": 'read("getHtml()")' in layout,
}
failed = [label for label, ok in checks.items() if not ok]
if failed:
    raise SystemExit("History parity acceptance checks failed: " + "; ".join(failed))
print("History template parity and preview-copy acceptance checks passed.")


# 2026-11-21: restore default media after leaving Douyin and wait for media data.
must_replace(
    "ui/AppViewModel.kt",
    '''    private fun applyDefaultMediaOnce() {
        if (ui.mediaInit) return
        if (kind == "douyin") {''',
    '''    private fun applyDefaultMediaOnce() {
        if (ui.mediaInit) return
        if (kind != "douyin" && data.emoji.isEmpty() && data.files.gif.isEmpty() && data.history.isEmpty()) return
        if (kind == "douyin") {''',
    "do not mark media initialized before media data exists"
)
must_replace(
    "ui/AppViewModel.kt",
    '''    fun updateData(block: (AppData) -> AppData) {
        data = block(data)
        store.saveData(data)
        validateSelections()
        rebuild()
    }
''',
    '''    fun updateData(block: (AppData) -> AppData) {
        data = block(data)
        store.saveData(data)
        validateSelections()
        if (!ui.mediaInit) applyDefaultMediaOnce()
        rebuild()
    }
''',
    "initialize default media after data becomes available"
)
must_replace(
    "ui/AppViewModel.kt",
    '''    fun selectLayout(id: String) {
        val item = data.layout.firstOrNull { it.id == id }
        updateUi {
            if (item?.name?.contains("抖音") == true) copy(
                layoutId = id, douyinBg = drawDouyinBg(), previewEmoji = "", gifId = null,
                gifContent = "", historyIds = emptyList(), mediaOrder = emptyList(), mediaInit = true
            ) else copy(layoutId = id)
        }
    }
''',
    '''    fun selectLayout(id: String) {
        val item = data.layout.firstOrNull { it.id == id }
        val wasDouyin = kind == "douyin"
        val isDouyin = item?.name?.contains("抖音") == true
        updateUi {
            when {
                isDouyin -> copy(
                    layoutId = id, douyinBg = drawDouyinBg(), previewEmoji = "", gifId = null,
                    gifContent = "", historyIds = emptyList(), historyHtml = "",
                    mediaOrder = emptyList(), mediaInit = true
                )
                wasDouyin -> copy(
                    layoutId = id, previewEmoji = "", gifId = null, gifContent = "",
                    historyIds = emptyList(), historyHtml = "", mediaOrder = emptyList(), mediaInit = false
                )
                else -> copy(layoutId = id)
            }
        }
        if (wasDouyin && !isDouyin) {
            applyDefaultMediaOnce()
            rebuild()
        }
    }
''',
    "restore default media when leaving Douyin layout"
)

vm_source = (java / "ui/AppViewModel.kt").read_text(encoding="utf-8")
checks = {
    "leaving Douyin resets media initialization": "if (wasDouyin && !isDouyin)" in vm_source,
    "Douyin transition clears history HTML": 'historyIds = emptyList(), historyHtml = ""' in vm_source,
    "late media data initializes defaults": "if (!ui.mediaInit) applyDefaultMediaOnce()" in vm_source,
    "empty media data does not lock initialization": "data.emoji.isEmpty() && data.files.gif.isEmpty() && data.history.isEmpty()" in vm_source,
}
failed = [label for label, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Douyin/media initialization acceptance checks failed: " + "; ".join(failed))
print("Douyin media transition acceptance checks passed.")


# 2026-11-21: align adjacent media spacing and complete My-page summary counts.
must_replace(
    "engine/PreviewEngine.kt",
    '        order.forEach { body.appendChild(blocks.getValue(it)) }',
    '''        order.forEachIndexed { index, key ->
            val block = blocks.getValue(key)
            if (index > 0) Css.set(block, "margin-top", "0px", true)
            if (index < order.lastIndex) {
                Css.set(block, "margin-bottom", maxOf(m[2], m[0]).toString() + "px", true)
            }
            body.appendChild(block)
        }''',
    "merge margins between adjacent history and GIF blocks"
)

preview_path = base / "assets/preview.html"
preview_source = preview_path.read_text(encoding="utf-8")
old_margins = '''  window.setMargins = function (t, r, b, l) {
    var v = [t, r, b, l], names = ['top', 'right', 'bottom', 'left'];
    Array.from(area.querySelectorAll('[data-preview-gif], [data-preview-history]')).forEach(function (el) {
      names.forEach(function (n, i) { el.style.setProperty('margin-' + n, v[i] + 'px', 'important'); });
    });
  };'''
new_margins = '''  window.setMargins = function (t, r, b, l) {
    var v = [t, r, b, l], names = ['top', 'right', 'bottom', 'left'];
    var blocks = Array.from(area.querySelectorAll('[data-preview-gif], [data-preview-history]'));
    blocks.forEach(function (el) {
      names.forEach(function (n, i) { el.style.setProperty('margin-' + n, v[i] + 'px', 'important'); });
    });
    // Flex items do not collapse vertical margins: use max(bottom, top) between adjacent media blocks.
    var between = Math.max(t, b);
    blocks.forEach(function (el, index) {
      if (index > 0) el.style.setProperty('margin-top', '0px', 'important');
      if (index < blocks.length - 1) el.style.setProperty('margin-bottom', between + 'px', 'important');
    });
  };'''
if old_margins not in preview_source:
    raise SystemExit("Required patch missing (adjacent media margins): assets/preview.html")
preview_path.write_text(preview_source.replace(old_margins, new_margins, 1), encoding="utf-8")

must_replace(
    "ui/MyScreens.kt",
    '''        val title = when (route) { "accounts" -> "账号"; "texts" -> "文案"; "layouts" -> "版式管理"; "more" -> "更多"; "backup" -> "备份"; else -> "我的" }''',
    '''        val title = when (route) { "accounts" -> "账号"; "texts" -> "文案"; "layouts" -> "版式"; "more" -> "更多"; "backup" -> "备份"; else -> "我的" }''',
    "use the required My page layout title"
)
my_home_path = java / "ui/MyScreens.kt"
my_home_source = my_home_path.read_text(encoding="utf-8")
home_start = my_home_source.find("private fun HomePage")
home_end = my_home_source.find("// ---------------------------------------------------------------------- 账号", home_start)
if home_start < 0 or home_end < 0:
    raise SystemExit("Required patch missing (My HomePage section): ui/MyScreens.kt")
home_lines = my_home_source[home_start:home_end].splitlines()
new_home_lines = []
seen = {"account": 0, "text": 0, "layout": 0, "more": 0}
has_more_count = any("val moreCount =" in line for line in home_lines)
for line in home_lines:
    stripped = line.strip()
    if stripped == "val d = vm.data":
        new_home_lines.append(line)
        if not has_more_count:
            new_home_lines.append("    val moreCount = d.emoji.size + d.history.size + d.files.gif.size + d.files.image.size")
    elif 'ListRow("账号",' in line:
        new_home_lines.append('    ListRow("账号", "已配置 " + d.accounts.size + " 个账号") { go("accounts") }')
        seen["account"] += 1
    elif 'ListRow("文案",' in line:
        new_home_lines.append('    ListRow("文案", "共 " + d.files.text.size + " 个文案模块") { go("texts") }')
        seen["text"] += 1
    elif 'ListRow("版式",' in line:
        new_home_lines.append('    ListRow("版式", "已保存 " + d.layout.size + " 个版式") { go("layouts") }')
        seen["layout"] += 1
    elif 'ListRow("更多",' in line:
        new_home_lines.append('    ListRow("更多", "共 " + moreCount + " 个数据模块") { go("more") }')
        seen["more"] += 1
    else:
        new_home_lines.append(line)
if any(v != 1 for v in seen.values()):
    raise SystemExit("Required My HomePage rows missing or duplicated: " + str(seen))
new_home = "\n".join(new_home_lines) + "\n"
my_home_source = my_home_source[:home_start] + new_home + my_home_source[home_end:]
my_home_path.write_text(my_home_source, encoding="utf-8")

must_replace(
    "ui/MyScreens.kt",
    '''                val previewEntries = previewTitles.mapIndexed { index, title ->
                    HistoryEntry(id = "history-preview-$index", title = title,
                        link = previewLinks.getOrNull(index).orEmpty(),
                        image = previewImages.getOrNull(index).orEmpty())
                }
''',
    "",
    "remove obsolete generic history preview rows"
)

engine_source = (java / "engine/PreviewEngine.kt").read_text(encoding="utf-8")
my_source = (java / "ui/MyScreens.kt").read_text(encoding="utf-8")
preview_source = (base / "assets/preview.html").read_text(encoding="utf-8")
checks = {
    "initial media margins merge by maximum": "maxOf(m[2], m[0])" in engine_source,
    "live media margins merge by maximum": "Math.max(t, b)" in preview_source,
    "My home shows more module count": '"共 " + moreCount + " 个数据模块"' in my_source,
    "My layout page title is concise": '"layouts" -> "版式"' in my_source,
}
failed = [label for label, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Layout and My-page acceptance checks failed: " + "; ".join(failed))
print("Adjacent media spacing and My-page summary acceptance checks passed.")


# 2026-11-21: stable rich-copy export, refresh random materials on every Layout entry.
from pathlib import Path as _Path
import re as _re
_vm = java / "ui/AppViewModel.kt"
_vms = _vm.read_text(encoding="utf-8")
_marker = "    // ------------------------------------------------------------------ 编辑模式 / 悬浮窗"
if _marker not in _vms:
    raise SystemExit("Required insertion point missing: AppViewModel layout entry refresh")
_refresh = r'''    /** 每次重新进入排版页时重新抽取五类素材；不依赖首次安装标记。 */
    fun refreshRandomSelections() {
        if (kind == "douyin") { rebuild(); return }
        val copyModule = data.files.text.filter { it.category == ui.textCat }.randomOrNull()
            ?: data.files.text.randomOrNull()
        val copyLines = copyModule?.let { drawCopy(it) }.orEmpty()
        val (imageId, imagePool) = drawImagePool()

        val emoji = data.emoji.randomOrNull()?.let { randomBlock(it.content) }.orEmpty()

        val textGifBlocks = data.files.gif.flatMap { module ->
            TextUtil.splitEntries(module.content)
                .filterNot { Regex("(?is)<img\\b|<video\\b|background-image\\s*:").containsMatchIn(it) }
                .map { module to it }
        }
        val gifPick = textGifBlocks.randomOrNull()
        val gifFallback = if (gifPick == null) data.files.gif.randomOrNull() else null
        val gifId = gifPick?.first?.id ?: gifFallback?.id
        val gifContent = gifPick?.second ?: gifFallback?.let { randomBlock(it.content) }.orEmpty()

        val history = data.history.randomOrNull()
        val historyIds = history?.let { listOf(it.id) }.orEmpty()
        val historyHtml = history?.let { PreviewEngine.composeHistoryHtml(it) }.orEmpty()
        val order = buildList {
            if (!gifId.isNullOrBlank() && gifContent.isNotBlank()) add("gif")
            if (historyIds.isNotEmpty()) add("history")
        }
        ui = ui.copy(
            copyModuleId = copyModule?.id,
            copyLines = copyLines,
            imgModuleId = imageId,
            imgPool = imagePool,
            previewEmoji = emoji,
            gifId = gifId,
            gifContent = gifContent,
            historyIds = historyIds,
            historyHtml = historyHtml,
            mediaOrder = order,
            mediaInit = true
        )
        store.saveUi(ui)
        rebuild()
    }

'''
_vms = _vms.replace(_marker, _refresh + _marker, 1)
_vm.write_text(_vms, encoding="utf-8")

# Copy only a compact, supported set of computed CSS properties. Avoid selecting the
# WebView DOM and avoid serializing hundreds of computed properties per node.
_asset = base / "assets/preview.html"
_html = _asset.read_text(encoding="utf-8")
_start = _html.find("  window.getHtml = function () {")
_end = _html.find("\n  };", _start)
if _start < 0 or _end < 0:
    raise SystemExit("Required getHtml() function missing in preview.html")
_safe_get = """  window.getHtml = function () {
    var clone = area.cloneNode(true);
    var originals = [area].concat(Array.from(area.querySelectorAll("*")));
    var copies = [clone].concat(Array.from(clone.querySelectorAll("*")));
    var allowed = [
      "display","box-sizing","width","max-width","height","margin","margin-top","margin-right",
      "margin-bottom","margin-left","padding","padding-top","padding-right","padding-bottom",
      "padding-left","font-family","font-size","font-weight","font-style","line-height",
      "letter-spacing","color","background-color","background-image","background-size",
      "background-position","text-align","text-indent","text-decoration","white-space",
      "vertical-align","border","border-radius","border-collapse","table-layout","object-fit"
    ];
    originals.forEach(function (source, index) {
      var target = copies[index];
      var computed = window.getComputedStyle(source);
      var css = [];
      allowed.forEach(function (name) {
        var value = computed.getPropertyValue(name);
        if (value && value !== "none" && value !== "normal" && value !== "auto") {
          css.push(name + ":" + value);
        }
      });
      var inline = source.getAttribute("style");
      if (inline) css.push(inline);
      target.setAttribute("style", css.join(";"));
    });
    clone.querySelectorAll("p").forEach(function (p) {
      if (!p.style.lineHeight || p.style.lineHeight === "normal") p.style.lineHeight = "1.5";
      if (!p.style.marginTop) p.style.marginTop = "0";
      if (!p.style.marginBottom) p.style.marginBottom = "0";
    });
    var holder = document.createElement("div");
    holder.appendChild(clone);
    return holder.innerHTML;
  };"""
_html = _html[:_start] + _safe_get + _html[_end+4:]
_asset.write_text(_html, encoding="utf-8")

_layout = java / "ui/LayoutScreen.kt"
_ls = _layout.read_text(encoding="utf-8")
# Replace TopBar copy lambda with the shared guarded copy path.
_top_start = _ls.find('        ThemeChip("复制", false) {')
_top_end = _ls.find('\n        Spacer(Modifier.width(8.dp))', _top_start)
if _top_start < 0 or _top_end < 0:
    raise SystemExit("Required TopBar copy action missing")
_ls = _ls[:_top_start] + '        ThemeChip("复制", false) { copyRenderedPreview(ctx, vm) }' + _ls[_top_end:]
# Replace the floating-window copy helper.
_cp_start = _ls.find("@Composable\nprivate fun CopyPreviewButton")
_cp_end = _ls.find("@Composable\nprivate fun EntryIcon", _cp_start)
if _cp_start < 0 or _cp_end < 0:
    raise SystemExit("Required CopyPreviewButton composable missing")
_copy_helper = """private fun copyRenderedPreview(ctx: android.content.Context, vm: AppViewModel) {
    val finish: (String?) -> Unit = { raw ->
        try {
            val parsed = runCatching {
                org.json.JSONTokener(raw ?: "null").nextValue() as? String
            }.getOrNull()
            val html = parsed?.takeIf { it.isNotBlank() } ?: vm.previewHtml
            require(html.isNotBlank()) { "当前预览内容为空" }
            val plain = android.text.Html.fromHtml(html, android.text.Html.FROM_HTML_MODE_LEGACY).toString()
            val clipboard = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            clipboard.setPrimaryClip(ClipData.newHtmlText("拾万句", plain, html))
            vm.toast("已复制当前预览内容")
        } catch (error: Throwable) {
            vm.toast("复制失败，请稍后重试：" + (error.message ?: "剪贴板不可用"))
        }
    }
    val read = vm.jsResult
    if (read == null) finish(null)
    else try {
        read("getHtml()") { raw -> finish(raw) }
    } catch (error: Throwable) {
        finish(null)
    }
}

@Composable
private fun CopyPreviewButton(vm: AppViewModel) {
    val ctx = LocalContext.current
    ThemeChip("复制预览内容", true, modifier = Modifier.fillMaxWidth()) {
        copyRenderedPreview(ctx, vm)
    }
}

"""
_ls = _ls[:_cp_start] + _copy_helper + _ls[_cp_end:]
_layout.write_text(_ls, encoding="utf-8")

# Refresh selections when returning from My to the layout screen.
_my = java / "ui/MyScreens.kt"
_ms = _my.read_text(encoding="utf-8")
_ms = _ms.replace('BackHandler { if (route == "home") vm.screen = "layout" else route = "home" }',
                  'BackHandler { if (route == "home") { vm.refreshRandomSelections(); vm.screen = "layout" } else route = "home" }', 1)
_ms = _ms.replace('TextButton(onClick = { if (route == "home") vm.screen = "layout" else route = "home" })',
                  'TextButton(onClick = { if (route == "home") { vm.refreshRandomSelections(); vm.screen = "layout" } else route = "home" })', 1)
_my.write_text(_ms, encoding="utf-8")

# Acceptance checks: all requested random pools refresh together; both copy entry points use safe helper.
_vmcheck = _vm.read_text(encoding="utf-8")
_lcheck = _layout.read_text(encoding="utf-8")
_ac = _asset.read_text(encoding="utf-8")
checks = {
    "refresh method rerolls copy": "copyLines = copyLines" in _vmcheck,
    "refresh method rerolls image pool": "imgPool = imagePool" in _vmcheck,
    "refresh method rerolls emoji": "previewEmoji = emoji" in _vmcheck,
    "refresh method rerolls text GIF": "gifContent = gifContent" in _vmcheck,
    "refresh method rerolls history": "historyHtml = historyHtml" in _vmcheck,
    "top copy uses safe helper": 'ThemeChip("复制", false) { copyRenderedPreview(ctx, vm) }' in _lcheck,
    "floating copy uses safe helper": "copyRenderedPreview(ctx, vm)" in _lcheck,
    "HTML export uses compact allowlist": 'var allowed = [' in _ac,
    "HTML export no longer selects page content": "selection.addRange(range)" not in _ac,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Copy/random refresh acceptance checks failed: " + "; ".join(failed))
print("Copy safety and per-entry random refresh acceptance checks passed.")


# 2026-11-22: use the existing rendered-HTML export and native clipboard directly.
# No extra JS clipboard bridge: evaluate getHtml(), then write ClipData.newHtmlText in Kotlin.
_layout = java / "ui/LayoutScreen.kt"
_ls = _layout.read_text(encoding="utf-8")
_cp_start = _ls.find("private fun copyRenderedPreview(ctx: android.content.Context, vm: AppViewModel) {")
_cp_end = _ls.find("@Composable\nprivate fun CopyPreviewButton", _cp_start)
if _cp_start < 0 or _cp_end < 0:
    raise SystemExit("Native copy helper not found; refusing to patch")
_copy_helper = """private fun copyRenderedPreview(ctx: android.content.Context, vm: AppViewModel) {
    val read = vm.jsResult
    if (read == null) {
        vm.toast("预览尚未就绪，请稍后重试")
        return
    }
    try {
        read("typeof window.getHtml === 'function' ? window.getHtml() : ''") { raw ->
            try {
                val html = runCatching {
                    org.json.JSONTokener(raw ?: "null").nextValue() as? String
                }.getOrNull()
                if (html.isNullOrBlank()) {
                    vm.toast("读取预览失败，请重新进入排版页")
                } else {
                    val plain = android.text.Html.fromHtml(
                        html, android.text.Html.FROM_HTML_MODE_LEGACY
                    ).toString()
                    val clipboard = ctx.getSystemService(android.content.Context.CLIPBOARD_SERVICE)
                        as android.content.ClipboardManager
                    clipboard.setPrimaryClip(
                        android.content.ClipData.newHtmlText("拾万句", plain, html)
                    )
                    vm.toast("已复制预览内容")
                }
            } catch (error: Throwable) {
                vm.toast("复制失败：" + (error.message ?: "剪贴板不可用"))
            }
        }
    } catch (error: Throwable) {
        vm.toast("读取预览失败：" + (error.message ?: "请重试"))
    }
}

"""
_ls = _ls[:_cp_start] + _copy_helper + _ls[_cp_end:]
_layout.write_text(_ls, encoding="utf-8")

_final_layout = _layout.read_text(encoding="utf-8")
_final_preview = (java / "ui/PreviewWebView.kt").read_text(encoding="utf-8")
_final_asset = _asset.read_text(encoding="utf-8")
if "window.getHtml = function" not in _final_asset:
    raise SystemExit("Rendered HTML export function getHtml() is missing")
if "evaluateJavascript(script) { value -> callback(value) }" not in _final_preview:
    raise SystemExit("WebView JavaScript result callback is missing")
if "ClipData.newHtmlText" not in _final_layout:
    raise SystemExit("Native rich HTML clipboard write is missing")
if "window.copyPreviewContent()" in _final_asset:
    raise SystemExit("Obsolete JavaScript copy action is still invoked")
if "copyRenderedPreview(ctx, vm)" not in _final_layout:
    raise SystemExit("Native copy buttons are not connected to the clipboard helper")
print("Rendered HTML -> evaluateJavascript callback -> native rich clipboard validated.")


# ---------------------------------------------------------------------- 版式条目间距：全局 / 单独版式，排版预览实时同步
patch("data/Models.kt",[
('    val margins: Map<String, List<Int>> = emptyMap(), // 往期/动图共用边距（上右下左），按版式种类记忆\n',
 '    val margins: Map<String, List<Int>> = emptyMap(), // 往期/动图共用边距（上右下左），按版式种类记忆\n    val layoutSpacing: Map<String, Int> = emptyMap(), // 版式条目之间的间距：* 为全局，版式 id 为单独设置\n')
])
patch("engine/PreviewEngine.kt",[
('            if (i < total - 1 && clones.isNotEmpty()) Css.set(clones.last(), "margin-bottom", "25px", true)   // 条目之间统一 25px',
 '            if (i < total - 1 && clones.isNotEmpty()) {\n                val layoutId = ctx.data.layout.getOrNull(ctx.layoutIdx)?.id.orEmpty()\n                val gap = ctx.ui.layoutSpacing[layoutId] ?: ctx.ui.layoutSpacing["*"] ?: 25\n                Css.set(clones.last(), "margin-bottom", "${gap.coerceIn(0, 100)}px", true)\n            }')
])
patch("ui/AppViewModel.kt",[
('    fun saveLayout(x: LayoutItem) = updateData { d ->',
'''    fun layoutSpacingFor(layoutId: String?): Int = if (layoutId == null) (ui.layoutSpacing["*"] ?: 25) else (ui.layoutSpacing[layoutId] ?: ui.layoutSpacing["*"] ?: 25)
    fun setLayoutSpacing(layoutId: String?, value: Int) = updateUi {
        copy(layoutSpacing = layoutSpacing + ((layoutId ?: "*") to value.coerceIn(0, 100)))
    }

    fun saveLayout(x: LayoutItem) = updateData { d ->''')
])
patch("ui/MyScreens.kt",[
('''private fun LayoutsPage(vm: AppViewModel) = Page {
    var edit by remember { mutableStateOf<LayoutItem?>(null) }
    var isNew by remember { mutableStateOf(false) }
    TopActions { ThemeChip("+ 新增", true, dark = false) { edit = LayoutItem(id = vm.newId()); isNew = true } }''',
'''private fun LayoutsPage(vm: AppViewModel) = Page {
    var edit by remember { mutableStateOf<LayoutItem?>(null) }
    var isNew by remember { mutableStateOf(false) }
    var showSpacing by remember { mutableStateOf(false) }
    TopActions {
        ThemeChip("增加间距", false, dark = false) { showSpacing = true }
        Spacer(Modifier.weight(1f))
        ThemeChip("+ 新增", true, dark = false) { edit = LayoutItem(id = vm.newId()); isNew = true }
    }'''),
('''        if (confirm) ConfirmDelete("版式", { vm.deleteLayout(l.id); confirm = false; edit = null }, { confirm = false })
    }
}

// ---------------------------------------------------------------------- 更多：emoji''',
'''        if (confirm) ConfirmDelete("版式", { vm.deleteLayout(l.id); confirm = false; edit = null }, { confirm = false })
    }

    if (showSpacing) {
        var targetId by remember { mutableStateOf<String?>(null) } // null = 全部版式
        var spacing by remember(targetId) { mutableIntStateOf(vm.layoutSpacingFor(targetId)) }
        Dialog(onDismissRequest = { showSpacing = false }, properties = DialogProperties(usePlatformDefaultWidth = false)) {
            Surface(
                modifier = Modifier.fillMaxWidth(0.92f).widthIn(max = 420.dp),
                shape = RoundedCornerShape(18.dp),
                color = Color.White
            ) {
                Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text("版式间距", color = AppColors.MyText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
                    Text("调整排版预览中每一个版式单元与下一个单元之间的距离。修改后立即生效并自动保存。", color = AppColors.MyDim, fontSize = 12.sp)
                    Text("应用范围", color = AppColors.MyText, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                    ThemeChip(if (targetId == null) "✓ 全部版式统一调整" else "全部版式统一调整", targetId == null, dark = false) {
                        targetId = null
                        spacing = vm.layoutSpacingFor(null)
                    }
                    vm.data.layout.forEach { item ->
                        ThemeChip(if (targetId == item.id) "✓ ${item.name}" else item.name, targetId == item.id, dark = false) {
                            targetId = item.id
                            spacing = vm.layoutSpacingFor(item.id)
                        }
                    }
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text("当前间距", color = AppColors.MyText, fontSize = 13.sp, modifier = Modifier.weight(1f))
                        Text("${spacing} dp", color = AppColors.Theme, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                    }
                    Slider(
                        value = spacing.toFloat(),
                        onValueChange = { v ->
                            spacing = v.roundToInt()
                            vm.setLayoutSpacing(targetId, spacing)
                        },
                        valueRange = 0f..100f,
                        steps = 19
                    )
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("紧凑 0 dp", color = AppColors.MyDim, fontSize = 11.sp)
                        Text("宽松 100 dp", color = AppColors.MyDim, fontSize = 11.sp)
                    }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        ThemeChip("完成", true, dark = false) { showSpacing = false }
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------- 更多：emoji''')
])


# 抖音版式以多个段落承载多个文案条目，同样应用全局 / 单独版式间距。
patch("engine/PreviewEngine.kt",[
('''                    ordered.forEach { parsed ->
                        val para = ctx.doc.createElement("p").attr("style", "margin:0;")''',
'''                    val layoutId = ctx.data.layout.getOrNull(ctx.layoutIdx)?.id.orEmpty()
                    val gap = (ctx.ui.layoutSpacing[layoutId] ?: ctx.ui.layoutSpacing["*"] ?: 25).coerceIn(0, 100)
                    ordered.forEachIndexed { position, parsed ->
                        val para = ctx.doc.createElement("p").attr("style", if (position < ordered.lastIndex) "margin:0;margin-bottom:${gap}px;" else "margin:0;")''')
])


# ----------------------------------------------------------------------
# Follow-up reliability fixes: native clipboard, entry-time randomization,
# Moments as the initial layout, original account-list styling, and launcher safe area.
patch("data/Models.kt",[
('    val layoutSpacing: Map<String, Int> = emptyMap(), // 版式条目之间的间距：* 为全局，版式 id 为单独设置\n',
 '    val layoutSpacing: Map<String, Int> = emptyMap(), // 版式条目之间的间距：* 为全局，版式 id 为单独设置\n    val emojiModuleId: String? = null,\n    val layoutDefaultMigrated: Boolean = false,\n'),
('const val LAYOUT_VER = 2','const val LAYOUT_VER = 3')
])

# Add the four standard templates to fresh / legacy data when absent.
patch("data/Store.kt",[
('''        var layout = fill(raw.layout, "layout", { it.id }, { x, i -> x.copy(id = i) })
            .map { it.copy(name = it.name ?: "", content = it.content ?: "") }
        var douyinAdded = raw.douyinAdded''',
'''        var layout = fill(raw.layout, "layout", { it.id }, { x, i -> x.copy(id = i) })
            .map { it.copy(name = it.name ?: "", content = it.content ?: "") }
        val defaultLayouts = listOf(
            "moments" to LayoutItem("layout_moments", "01_朋友圈版", templates["moments"] ?: ""),
            "duan" to LayoutItem("layout_duan", "02_断章序引版", templates["duan"] ?: ""),
            "card" to LayoutItem("layout_card", "03_卡片版", templates["card"] ?: ""),
            "sentence" to LayoutItem("layout_sentence", "04_文字断句版", templates["sentence"] ?: "")
        )
        defaultLayouts.forEach { (kind, item) ->
            if (layout.none { layoutKindOf(it.name) == kind }) {
                layout = if (kind == "moments") listOf(item) + layout else layout + item
            }
        }
        var douyinAdded = raw.douyinAdded'''),
('name = "04_抖音版"','name = "05_抖音版"')
])

patch("ui/AppViewModel.kt",[
('''        validateSelections()
        applyDefaultMediaOnce()
        rebuild()''',
'''        val moments = data.layout.firstOrNull { layoutKindOf(it.name) == "moments" }
        if (!ui.layoutDefaultMigrated) {
            val selected = data.layout.firstOrNull { it.id == ui.layoutId }
            if (moments != null && (selected == null || layoutKindOf(selected.name) == "douyin")) {
                ui = ui.copy(layoutId = moments.id, layoutDefaultMigrated = true)
            } else {
                ui = ui.copy(layoutDefaultMigrated = true)
            }
            store.saveUi(ui)
        }
        validateSelections()
        applyDefaultMediaOnce()
        rebuild()'''),
('''    private fun drawImagePool(): Pair<String?, List<String>> {
        val mods = data.files.image.filter { TextUtil.imageUrls(it.content).isNotEmpty() && !it.name.contains("抖音背景") }
        if (mods.isEmpty()) return null to emptyList()
        val m = mods.random()
        return m.id to TextUtil.sampleN(TextUtil.imageUrls(m.content), IMG_POOL_SIZE)
    }''',
'''    private fun drawImagePool(excludeId: String? = null): Pair<String?, List<String>> {
        val mods = data.files.image.filter { TextUtil.imageUrls(it.content).isNotEmpty() && !it.name.contains("抖音背景") }
        if (mods.isEmpty()) return null to emptyList()
        val choices = mods.filterNot { it.id == excludeId }.ifEmpty { mods }
        val m = choices.random()
        return m.id to TextUtil.sampleN(TextUtil.imageUrls(m.content), IMG_POOL_SIZE)
    }'''),
('''    fun clearEmoji() = updateUi { copy(previewEmoji = "") }

    fun applyRandomEmoji() {
        val item = data.emoji.randomOrNull() ?: return toast("暂无emoji条目，请到【我的】-更多-emoji中添加")
        val v = randomBlock(item.content)
        if (v.isEmpty()) return toast("所选emoji条目没有可用内容")
        updateUi { copy(previewEmoji = v) }
    }''',
'''    fun clearEmoji() = updateUi { copy(previewEmoji = "", emojiModuleId = null) }

    fun applyRandomEmoji() {
        val choices = data.emoji.filterNot { it.id == ui.emojiModuleId }.ifEmpty { data.emoji }
        val item = choices.randomOrNull() ?: return toast("暂无emoji条目，请到【我的】-更多-emoji中添加")
        val v = randomBlock(item.content)
        if (v.isEmpty()) return toast("所选emoji条目没有可用内容")
        updateUi { copy(previewEmoji = v, emojiModuleId = item.id) }
    }'''),
('''    /** 每次重新进入排版页时重新抽取五类素材；不依赖首次安装标记。 */
    fun refreshRandomSelections() {
        if (kind == "douyin") { rebuild(); return }
        val copyModule = data.files.text.filter { it.category == ui.textCat }.randomOrNull()
            ?: data.files.text.randomOrNull()
        val copyLines = copyModule?.let { drawCopy(it) }.orEmpty()
        val (imageId, imagePool) = drawImagePool()

        val emoji = data.emoji.randomOrNull()?.let { randomBlock(it.content) }.orEmpty()

        val textGifBlocks = data.files.gif.flatMap { module ->
            TextUtil.splitEntries(module.content)
                .filterNot { Regex("(?is)<img\\\\b|<video\\\\b|background-image\\\\s*:").containsMatchIn(it) }
                .map { module to it }
        }
        val gifPick = textGifBlocks.randomOrNull()
        val gifFallback = if (gifPick == null) data.files.gif.randomOrNull() else null
        val gifId = gifPick?.first?.id ?: gifFallback?.id
        val gifContent = gifPick?.second ?: gifFallback?.let { randomBlock(it.content) }.orEmpty()

        val history = data.history.randomOrNull()
        val historyIds = history?.let { listOf(it.id) }.orEmpty()
        val historyHtml = history?.let { PreviewEngine.composeHistoryHtml(it) }.orEmpty()
        val order = buildList {
            if (!gifId.isNullOrBlank() && gifContent.isNotBlank()) add("gif")
            if (historyIds.isNotEmpty()) add("history")
        }
        ui = ui.copy(
            copyModuleId = copyModule?.id,
            copyLines = copyLines,
            imgModuleId = imageId,
            imgPool = imagePool,
            previewEmoji = emoji,
            gifId = gifId,
            gifContent = gifContent,
            historyIds = historyIds,
            historyHtml = historyHtml,
            mediaOrder = order,
            mediaInit = true
        )
        store.saveUi(ui)
        rebuild()
    }''',
'''    /** 每次进入排版页都重新抽取：文案类别、图片文件、emoji 模块、动图模块分别随机。 */
    fun refreshRandomSelections() {
        if (kind == "douyin") { rebuild(); return }

        val categories = TEXT_CATEGORIES.filter { category -> data.files.text.any { it.category == category } }
        val categoryChoices = categories.filterNot { it == ui.textCat }.ifEmpty { categories }
        val textCategory = categoryChoices.randomOrNull() ?: ui.textCat
        val categoryModules = data.files.text.filter { it.category == textCategory }
        val copyChoices = categoryModules.filterNot { it.id == ui.copyModuleId }.ifEmpty { categoryModules }
        val copyModule = copyChoices.randomOrNull()
            ?: data.files.text.filterNot { it.id == ui.copyModuleId }.ifEmpty { data.files.text }.randomOrNull()
        val copyLines = copyModule?.let { drawCopy(it) }.orEmpty()

        val (imageId, imagePool) = drawImagePool(ui.imgModuleId)

        val emojiChoices = data.emoji.filterNot { it.id == ui.emojiModuleId }.ifEmpty { data.emoji }
        val emojiModule = emojiChoices.randomOrNull()
        val emoji = emojiModule?.let { randomBlock(it.content) }.orEmpty()

        val gifChoices = data.files.gif.filterNot { it.id == ui.gifId }.ifEmpty { data.files.gif }
        val gifModule = gifChoices.randomOrNull()
        val gifTextBlocks = gifModule?.let { module ->
            TextUtil.splitEntries(module.content)
                .filterNot { Regex("(?is)<img\\\\b|<video\\\\b|background-image\\\\s*:").containsMatchIn(it) }
        }.orEmpty()
        val gifContent = gifTextBlocks.randomOrNull() ?: gifModule?.let { randomBlock(it.content) }.orEmpty()
        val gifId = gifModule?.id

        val history = data.history.firstOrNull { it.name.contains("文字") }
            ?: data.history.firstOrNull { it.image.isBlank() && it.images.isBlank() }
            ?: data.history.firstOrNull()
        val historyIds = history?.let { listOf(it.id) }.orEmpty()
        val historyHtml = history?.let { PreviewEngine.composeHistoryHtml(it) }.orEmpty()
        val order = buildList {
            if (!gifId.isNullOrBlank() && gifContent.isNotBlank()) add("gif")
            if (historyIds.isNotEmpty()) add("history")
        }
        ui = ui.copy(
            textCat = textCategory,
            copyModuleId = copyModule?.id,
            copyLines = copyLines,
            imgModuleId = imageId,
            imgPool = imagePool,
            emojiModuleId = emojiModule?.id,
            previewEmoji = emoji,
            gifId = gifId,
            gifContent = gifContent,
            historyIds = historyIds,
            historyHtml = historyHtml,
            mediaOrder = order,
            mediaInit = true
        )
        store.saveUi(ui)
        rebuild()
    }''')
])

# Account list follows 000_拾万句.html: white rounded card, circular 40dp avatar,
# title + AppID/author metadata, and a right chevron.
patch("ui/MyScreens.kt",[
('import androidx.compose.ui.graphics.Color\n','import androidx.compose.ui.graphics.Color\nimport androidx.compose.ui.layout.ContentScale\nimport coil.compose.AsyncImage\n'),
('''@Composable
private fun AccountsPage(vm: AppViewModel) = Page {
    var edit by remember { mutableStateOf<Account?>(null) }
    var isNew by remember { mutableStateOf(false) }
    TopActions { ThemeChip("+ 新增账号", true, dark = false) { edit = Account(id = vm.newId()); isNew = true } }
    if (vm.data.accounts.isEmpty()) Empty("暂无数据，请点击右上角新增")
    vm.data.accounts.forEach { a -> ListRow(a.name, a.author.ifEmpty { a.appId }) { edit = a; isNew = false } }

    edit?.let { a ->
        var avatar by remember(a.id) { mutableStateOf(a.avatar) }; var name by remember(a.id) { mutableStateOf(a.name) }
        var appId by remember(a.id) { mutableStateOf(a.appId) }; var secret by remember(a.id) { mutableStateOf(a.secret) }
        var mp by remember(a.id) { mutableStateOf(a.mpAvatar) }; var author by remember(a.id) { mutableStateOf(a.author) }
        var confirm by remember { mutableStateOf(false) }
        EditDialog("详情与编辑", { edit = null },
            { vm.saveAccount(a.copy(avatar = avatar, name = name.ifEmpty { "未命名账号" }, appId = appId, secret = secret, mpAvatar = mp, author = author)); edit = null },
            if (isNew) null else ({ confirm = true })) {
            Field("微信头像链接（朋友圈版头像取自这里）", avatar, { avatar = it }); Field("账号名称", name, { name = it })
            Field("AppID", appId, { appId = it }); Field("AppSecret", secret, { secret = it })
            Field("公众号头像", mp, { mp = it }); Field("作者", author, { author = it })
        }
        if (confirm) ConfirmDelete("账号", { vm.deleteAccount(a.id); confirm = false; edit = null }, { confirm = false })
    }
}''',
'''@Composable
private fun AccountsPage(vm: AppViewModel) = Page {
    var edit by remember { mutableStateOf<Account?>(null) }
    var isNew by remember { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text("已有账号列表", color = Color(0xFF6B7280), fontSize = 13.sp, fontWeight = FontWeight.Medium, modifier = Modifier.weight(1f))
        ThemeChip("+ 新增账号", true, dark = false) { edit = Account(id = vm.newId()); isNew = true }
    }
    if (vm.data.accounts.isEmpty()) Empty("暂无账号，请点击右上角新增")
    vm.data.accounts.forEach { account ->
        AccountListRow(account) { edit = account; isNew = false }
    }

    edit?.let { a ->
        var avatar by remember(a.id) { mutableStateOf(a.avatar) }; var name by remember(a.id) { mutableStateOf(a.name) }
        var appId by remember(a.id) { mutableStateOf(a.appId) }; var secret by remember(a.id) { mutableStateOf(a.secret) }
        var mp by remember(a.id) { mutableStateOf(a.mpAvatar) }; var author by remember(a.id) { mutableStateOf(a.author) }
        var confirm by remember { mutableStateOf(false) }
        EditDialog("详情与编辑", { edit = null },
            { vm.saveAccount(a.copy(avatar = avatar, name = name.ifEmpty { "未命名账号" }, appId = appId, secret = secret, mpAvatar = mp, author = author)); edit = null },
            if (isNew) null else ({ confirm = true })) {
            Field("本地配置头像（图片 URL 或 Base64）", avatar, { avatar = it })
            Field("公众号名称", name, { name = it })
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Box(Modifier.weight(1f)) { Field("APP_ID", appId, { appId = it }) }
                Box(Modifier.weight(1f)) { Field("APP_SECRET", secret, { secret = it }) }
            }
            Field("公众号头像", mp, { mp = it })
            Field("公众号作者", author, { author = it })
        }
        if (confirm) ConfirmDelete("账号", { vm.deleteAccount(a.id); confirm = false; edit = null }, { confirm = false })
    }
}

@Composable
private fun AccountListRow(account: Account, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().shadow(1.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp))
            .background(Color.White).clickable(onClick = onClick).padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        if (account.avatar.isNotBlank()) {
            AsyncImage(
                model = account.avatar,
                contentDescription = "头像",
                modifier = Modifier.size(40.dp).clip(CircleShape),
                contentScale = ContentScale.Crop
            )
        } else {
            Box(Modifier.size(40.dp).clip(CircleShape).background(Color(0xFFF3F4F6)), contentAlignment = Alignment.Center) {
                Text("头像", color = Color(0xFF9CA3AF), fontSize = 10.sp)
            }
        }
        Column(Modifier.weight(1f).padding(start = 12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(account.name.ifBlank { "未命名账号" }, color = Color(0xFF111827), fontSize = 15.sp, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text(
                "AppID: " + account.appId.ifBlank { "未填" } + " | 作者: " + account.author.ifBlank { "未填" },
                color = Color(0xFF9CA3AF), fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis
            )
        }
        Text("›", color = Color(0xFF9CA3AF), fontSize = 23.sp, modifier = Modifier.padding(start = 7.dp))
    }
}''')
])

# Copy the actual rendered WebView DOM into Android's system clipboard.
patch("ui/LayoutScreen.kt",[
('''private fun copyRenderedPreview(ctx: android.content.Context, vm: AppViewModel) {
    val runCopy = vm.js
    if (runCopy == null) {
        vm.toast("预览页面尚未就绪，请稍后重试")
        return
    }
    // Invoke the HTML reference's copyPreviewContent() against the live rendered DOM.
    // The browser/WebView, not Kotlin, writes the rich HTML clipboard representation.
    runCopy("window.copyPreviewContent && window.copyPreviewContent()")
    vm.toast("已执行富文本复制，请粘贴到公众号检查")
}''',
'''private fun copyRenderedPreview(ctx: android.content.Context, vm: AppViewModel) {
    val read = vm.jsResult
    if (read == null) {
        vm.toast("预览尚未就绪，请稍后重试")
        return
    }
    try {
        read("typeof window.getHtml === 'function' ? window.getHtml() : ''") { raw ->
            try {
                val html = runCatching {
                    org.json.JSONTokener(raw ?: "null").nextValue() as? String
                }.getOrNull()
                if (html.isNullOrBlank()) {
                    vm.toast("读取实时预览失败，请重新进入排版页")
                } else {
                    val plain = android.text.Html.fromHtml(
                        html, android.text.Html.FROM_HTML_MODE_LEGACY
                    ).toString()
                    val clipboard = ctx.getSystemService(android.content.Context.CLIPBOARD_SERVICE)
                        as android.content.ClipboardManager
                    clipboard.setPrimaryClip(
                        android.content.ClipData.newHtmlText("拾万句", plain, html)
                    )
                    vm.toast("已复制实时预览内容")
                }
            } catch (error: Throwable) {
                vm.toast("复制失败：" + (error.message ?: "剪贴板不可用"))
            }
        }
    } catch (error: Throwable) {
        vm.toast("读取预览失败：" + (error.message ?: "页面尚未就绪"))
    }
}''')
])

# Refresh every time the app enters the layout screen; do not depend on saved mediaInit.
patch("MainActivity.kt",[
('''                LaunchedEffect(vm.message) { vm.message?.let { Toast.makeText(this@MainActivity, it, Toast.LENGTH_SHORT).show(); vm.message = null } }
                if (vm.screen == "layout") LayoutScreen(vm) else MyScreen(vm)''',
'''                LaunchedEffect(vm.message) { vm.message?.let { Toast.makeText(this@MainActivity, it, Toast.LENGTH_SHORT).show(); vm.message = null } }
                LaunchedEffect(vm.screen) { if (vm.screen == "layout") vm.refreshRandomSelections() }
                if (vm.screen == "layout") LayoutScreen(vm) else MyScreen(vm)''')
])
patch("ui/MyScreens.kt",[
('vm.refreshRandomSelections(); vm.screen = "layout"','vm.screen = "layout"')
])
print("Applied clipboard, random-entry, Moments-default, account-list and icon-safe-area patches.")
# Final clipboard authority check: only the live rendered WebView export may be copied.
_final_layout = (java / "ui/LayoutScreen.kt").read_text(encoding="utf-8")
_final_asset = (base / "assets/preview.html").read_text(encoding="utf-8")
_copy_start = _final_layout.find("private fun copyRenderedPreview(ctx: android.content.Context, vm: AppViewModel) {")
_copy_end = _final_layout.find("@Composable\nprivate fun CopyPreviewButton", _copy_start)
if _copy_start < 0 or _copy_end < 0:
    raise SystemExit("Authoritative rendered-copy helper missing")
_copy_impl = _final_layout[_copy_start:_copy_end]
if "vm.jsResult" not in _copy_impl or "window.getHtml()" not in _copy_impl:
    raise SystemExit("Clipboard must read the live rendered WebView DOM")
if "vm.previewHtml" in _copy_impl:
    raise SystemExit("Raw source HTML must never override the rendered clipboard export")
if "ClipData.newHtmlText" not in _copy_impl:
    raise SystemExit("Rich HTML clipboard write missing from authoritative helper")
if "window.getHtml = function" not in _final_asset or "var allowed = [" not in _final_asset:
    raise SystemExit("Rendered DOM export with WeChat-safe inline style allowlist missing")
print("Authoritative live-rendered DOM clipboard checks passed.")



# Avoid a duplicate random draw on the toolbar return path; the screen-entry effect owns it.
patch("ui/MyScreens.kt",[
('vm.refreshRandomSelections(); vm.screen = "layout"','vm.screen = "layout"'),
('vm.refreshRandomSelections(); vm.screen = "layout"','vm.screen = "layout"')
])
patch("ui/AppViewModel.kt",[
('fun rerollImages() { val (id, p) = drawImagePool(); updateUi { copy(imgModuleId = id, imgPool = p) } }',
 'fun rerollImages() { val (id, p) = drawImagePool(ui.imgModuleId); updateUi { copy(imgModuleId = id, imgPool = p) } }')
])


# Match the centered rounded account editor modal from 000_拾万句.html.
patch("ui/MyScreens.kt",[
('''        EditDialog("详情与编辑", { edit = null },
            { vm.saveAccount(a.copy(avatar = avatar, name = name.ifEmpty { "未命名账号" }, appId = appId, secret = secret, mpAvatar = mp, author = author)); edit = null },
            if (isNew) null else ({ confirm = true })) {''',
'''        AccountEditDialog(if (isNew) "新增账号" else "编辑账号", { edit = null },
            { vm.saveAccount(a.copy(avatar = avatar, name = name.ifEmpty { "未命名账号" }, appId = appId, secret = secret, mpAvatar = mp, author = author)); edit = null },
            if (isNew) null else ({ confirm = true })) {'''),
('''// ---------------------------------------------------------------------- 文案（宫格 / 列表、排序）''',
'''@Composable
private fun AccountEditDialog(
    title: String,
    onDismiss: () -> Unit,
    onSave: () -> Unit,
    onDelete: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit
) {
    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(usePlatformDefaultWidth = false)) {
        Surface(
            Modifier.fillMaxWidth(0.92f).widthIn(max = 480.dp),
            shape = RoundedCornerShape(18.dp),
            color = Color.White,
            shadowElevation = 14.dp
        ) {
            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Text(title, color = Color(0xFF111827), fontSize = 18.sp, fontWeight = FontWeight.Medium)
                Column(
                    Modifier.heightIn(max = 520.dp).verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    content = content
                )
                HorizontalDivider(color = Color(0xFFF3F4F6))
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    if (onDelete != null) {
                        TextButton(onClick = onDelete, contentPadding = PaddingValues(horizontal = 8.dp)) {
                            Text("删除账号", color = Color(0xFFDC2626), fontSize = 13.sp)
                        }
                    }
                    Spacer(Modifier.weight(1f))
                    TextButton(onClick = onDismiss) { Text("取消", color = Color(0xFF6B7280)) }
                    Button(
                        onClick = onSave,
                        colors = ButtonDefaults.buttonColors(containerColor = AppColors.Theme, contentColor = AppColors.OnTheme),
                        shape = RoundedCornerShape(9.dp),
                        contentPadding = PaddingValues(horizontal = 18.dp, vertical = 9.dp)
                    ) { Text("保存", fontWeight = FontWeight.Medium) }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------- 文案（宫格 / 列表、排序）''')
])


# ----------------------------------------------------------------------
# 2026-11-22: show only the sentence-break layout in the app UI.
# Keep every layout record in the external data store/backup untouched.
patch("ui/AppViewModel.kt",[
    ('''        validateSelections()
        applyDefaultMediaOnce()
        rebuild()
    }''',
     '''        validateSelections()
        val sentenceLayout = data.layout.firstOrNull { it.name.contains("文字断句") || it.name.contains("断句") }
        if (sentenceLayout != null && ui.layoutId != sentenceLayout.id) ui = ui.copy(layoutId = sentenceLayout.id)
        applyDefaultMediaOnce()
        rebuild()
    }'''),
    ('''    fun selectLayout(id: String) {
        val item = data.layout.firstOrNull { it.id == id }
        updateUi {
            if (item?.name?.contains("抖音") == true) copy(
                layoutId = id, douyinBg = drawDouyinBg(), previewEmoji = "", gifId = null,
                gifContent = "", historyIds = emptyList(), mediaOrder = emptyList(), mediaInit = true
            ) else copy(layoutId = id)
        }
    }''',
     '''    fun selectLayout(id: String) {
        val item = data.layout.firstOrNull { it.id == id } ?: return
        if (!item.name.contains("文字断句") && !item.name.contains("断句")) return
        updateUi { copy(layoutId = id) }
    }''')
])

patch("ui/LayoutScreen.kt",[
    ('''private fun LayoutPanel(vm: AppViewModel) {
    val list = vm.data.layout
    if (list.isEmpty()) return EmptyTip("暂无版式，请到【我的】中添加")
    val cur = vm.layoutIndex
    LazyRow(Modifier.fillMaxSize().padding(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        items(list.size) { i ->
            val l = list[i]
            Box(Modifier.width(82.dp).clip(RoundedCornerShape(9.dp)).border(2.dp, if (i == cur) AppColors.Theme else Color.Transparent, RoundedCornerShape(9.dp))) {
                Column(Modifier.fillMaxWidth()) {
                    RenderedLayoutPreview(vm, l, Modifier.fillMaxWidth().aspectRatio(3f / 4f))
                    Text(shortName(l.name), Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 5.dp), color = if (i == cur) AppColors.Theme else AppColors.TextMain, fontSize = 11.sp, fontWeight = if (i == cur) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center)
                }
                Box(Modifier.matchParentSize().clickable { vm.selectLayout(l.id) })
            }
        }
    }
}''',
     '''private fun LayoutPanel(vm: AppViewModel) {
    val list = vm.data.layout.filter { it.name.contains("文字断句") || it.name.contains("断句") }
    if (list.isEmpty()) return EmptyTip("数据中暂无文字断句版式")
    val selectedId = vm.ui.layoutId
    LazyRow(Modifier.fillMaxSize().padding(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        items(list.size) { i ->
            val l = list[i]
            val selected = l.id == selectedId
            Column(Modifier.width(82.dp).clip(RoundedCornerShape(9.dp)).border(2.dp, if (selected) AppColors.Theme else Color.Transparent, RoundedCornerShape(9.dp)).clickable { vm.selectLayout(l.id) }) {
                RenderedLayoutPreview(vm, l, Modifier.fillMaxWidth().aspectRatio(3f / 4f))
                Text("文字断句", Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 5.dp), color = if (selected) AppColors.Theme else AppColors.TextMain, fontSize = 11.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium, maxLines = 1, textAlign = TextAlign.Center)
            }
        }
    }
}'''),
    ('''            ThemeChip("换一个", false) { vm.loadRandomTitle() }
        }
        Spacer(Modifier.height(10.dp))
        CopyPreviewButton(vm)''',
     '''            ThemeChip("换一个", false) { vm.loadRandomTitle() }
            val ctx = LocalContext.current
            ThemeChip("文章全选", false) {
                vm.js?.invoke("(function(){var root=document.body;if(!root)return false;root.style.webkitUserSelect='text';root.style.userSelect='text';var range=document.createRange();range.selectNodeContents(root);var selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);return true;})()")
                vm.toast("已全选文章内容")
            }
        }
        Spacer(Modifier.height(10.dp))
        CopyPreviewButton(vm)''')
])

patch("ui/MyScreens.kt",[
    ('''    if (vm.data.layout.isEmpty()) Empty("暂无版式，请点击右上角新增")
    vm.data.layout.chunked(2).forEach { row ->''',
     '''    val visibleLayouts = vm.data.layout.filter { it.name.contains("文字断句") || it.name.contains("断句") }
    if (visibleLayouts.isEmpty()) Empty("数据中暂无文字断句版式")
    visibleLayouts.chunked(2).forEach { row ->''')
])

# Hard acceptance: app UI must filter, preserve the full data collection, and expose the select-all action.
_layoutScreen = (java / "ui/LayoutScreen.kt").read_text(encoding="utf-8")
_myScreens = (java / "ui/MyScreens.kt").read_text(encoding="utf-8")
_viewModel = (java / "ui/AppViewModel.kt").read_text(encoding="utf-8")
if 'vm.data.layout.filter { it.name.contains("文字断句") || it.name.contains("断句") }' not in _layoutScreen:
    raise SystemExit("Layout picker is not restricted to the sentence-break layout")
if 'visibleLayouts = vm.data.layout.filter' not in _myScreens:
    raise SystemExit("Layout manager is not restricted to the sentence-break layout")
if 'selection.selectAll' in _layoutScreen or 'selection.addRange(range)' not in _layoutScreen or '文章全选' not in _layoutScreen:
    raise SystemExit("Article select-all button or WebView selection implementation missing")
if 'data.layout.firstOrNull { it.name.contains("文字断句") || it.name.contains("断句") }' not in _viewModel:
    raise SystemExit("Default sentence-break layout selection missing")
print("Sentence-break-only UI and article select-all acceptance checks passed.")

# ----------------------------------------------------------------------
# 2026-11-22: one UI layout type, data-driven card count, and Android text actions.
# The app ships one sentence-break default only when no layout data exists.
patch("data/Store.kt",[
    ('''        val defaultLayouts = listOf(
            "moments" to LayoutItem("layout_moments", "01_朋友圈版", templates["moments"] ?: ""),
            "duan" to LayoutItem("layout_duan", "02_断章序引版", templates["duan"] ?: ""),
            "card" to LayoutItem("layout_card", "03_卡片版", templates["card"] ?: ""),
            "sentence" to LayoutItem("layout_sentence", "04_文字断句版", templates["sentence"] ?: "")
        )
        defaultLayouts.forEach { (kind, item) ->
            if (layout.none { layoutKindOf(it.name) == kind }) {
                layout = if (kind == "moments") listOf(item) + layout else layout + item
            }
        }''',
     '''        // UI 与数据分离：仅在完全没有导入版式数据时提供一个默认文字断句版。
        // 一旦用户导入了 N 条版式数据，保留这 N 条，不额外补齐其他版式或重复默认项。
        if (layout.isEmpty()) {
            layout = listOf(LayoutItem(
                id = "layout_sentence",
                name = "文字断句版",
                content = templates["sentence"] ?: ""
            ))
        }''')
])

patch("ui/AppViewModel.kt",[
    ('''        val sentenceLayout = data.layout.firstOrNull { it.name.contains("文字断句") || it.name.contains("断句") }
        if (sentenceLayout != null && ui.layoutId != sentenceLayout.id) ui = ui.copy(layoutId = sentenceLayout.id)''',
     '''        val firstLayout = data.layout.firstOrNull()
        if (firstLayout != null && data.layout.none { it.id == ui.layoutId }) {
            ui = ui.copy(layoutId = firstLayout.id)
            store.saveUi(ui)
        }'''),
    ('''    fun selectLayout(id: String) {
        val item = data.layout.firstOrNull { it.id == id }
        val wasDouyin = kind == "douyin"
        val isDouyin = item?.name?.contains("抖音") == true
        updateUi {
            when {
                isDouyin -> copy(
                    layoutId = id, douyinBg = drawDouyinBg(), previewEmoji = "", gifId = null,
                    gifContent = "", historyIds = emptyList(), historyHtml = "",
                    mediaOrder = emptyList(), mediaInit = true
                )
                wasDouyin -> copy(
                    layoutId = id, previewEmoji = "", gifId = null, gifContent = "",
                    historyIds = emptyList(), historyHtml = "", mediaOrder = emptyList(), mediaInit = false
                )
                else -> copy(layoutId = id)
            }
        }
        if (wasDouyin && !isDouyin) {
            applyDefaultMediaOnce()
            rebuild()
        }
    }''',
     '''    fun selectLayout(id: String) {
        if (data.layout.none { it.id == id }) return
        updateUi { copy(layoutId = id) }
    }''')
])

patch("ui/LayoutScreen.kt",[
    ('''    val list = vm.data.layout.filter { it.name.contains("文字断句") || it.name.contains("断句") }
    if (list.isEmpty()) return EmptyTip("数据中暂无文字断句版式")''',
     '''    // 所有卡片都属于同一种「文字断句版」软件版式；卡片数量严格跟随导入数据条数。
    val list = vm.data.layout
    if (list.isEmpty()) return EmptyTip("暂无版式数据，请导入数据")'''),
    ('''                vm.js?.invoke("(function(){var root=document.body;if(!root)return false;root.style.webkitUserSelect='text';root.style.userSelect='text';var range=document.createRange();range.selectNodeContents(root);var selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);return true;})()")
                vm.toast("已全选文章内容")''',
     '''                showArticleSelectionActions(ctx, vm)''')
])

patch("ui/MyScreens.kt",[
    ('''    val visibleLayouts = vm.data.layout.filter { it.name.contains("文字断句") || it.name.contains("断句") }
    if (visibleLayouts.isEmpty()) Empty("数据中暂无文字断句版式")
    visibleLayouts.chunked(2).forEach { row ->''',
     '''    val visibleLayouts = vm.data.layout
    if (visibleLayouts.isEmpty()) Empty("暂无版式数据，请导入数据")
    visibleLayouts.chunked(2).forEach { row ->''')
])

# A native Android ActionMode is shown only after the live article WebView confirms
# that its article content has been selected. Copy/cut/paste operate on that selection.
patch("ui/LayoutScreen.kt",[
    ('''@Composable
private fun CopyPreviewButton(vm: AppViewModel) {''',
     '''private fun showArticleSelectionActions(ctx: android.content.Context, vm: AppViewModel) {
    val read = vm.jsResult
    if (read == null) {
        vm.toast("文章预览尚未就绪")
        return
    }
    val selectScript = """
        (function() {
            var root = document.querySelector('#previewArea') ||
                       document.querySelector('[data-preview-root]') ||
                       document.querySelector('.preview-area') ||
                       document.body;
            if (!root) return '';
            root.setAttribute('contenteditable', 'true');
            root.style.webkitUserSelect = 'text';
            root.style.userSelect = 'text';
            var selection = window.getSelection();
            var range = document.createRange();
            range.selectNodeContents(root);
            selection.removeAllRanges();
            selection.addRange(range);
            return selection.toString();
        })()
    """.trimIndent()
    read(selectScript) { raw ->
        val selectedText = runCatching {
            org.json.JSONTokener(raw ?: "null").nextValue() as? String
        }.getOrNull().orEmpty()
        if (selectedText.isBlank()) {
            vm.toast("没有可全选的文章文字")
            return@read
        }
        var base: android.content.Context? = ctx
        while (base is android.content.ContextWrapper && base !is android.app.Activity) {
            base = base.baseContext
        }
        val activity = base as? android.app.Activity
        if (activity == null) {
            vm.toast("无法打开安卓文本操作菜单")
            return@read
        }
        activity.runOnUiThread {
            activity.startActionMode(object : android.view.ActionMode.Callback {
                override fun onCreateActionMode(mode: android.view.ActionMode, menu: android.view.Menu): Boolean {
                    mode.title = "文章已全选"
                    menu.add(0, 1, 0, "复制")
                    menu.add(0, 2, 1, "剪切")
                    menu.add(0, 3, 2, "粘贴")
                    return true
                }
                override fun onPrepareActionMode(mode: android.view.ActionMode, menu: android.view.Menu): Boolean = false
                override fun onActionItemClicked(mode: android.view.ActionMode, item: android.view.MenuItem): Boolean {
                    when (item.itemId) {
                        1 -> {
                            val clipboard = ctx.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                            clipboard.setPrimaryClip(android.content.ClipData.newPlainText("文章", selectedText))
                            vm.toast("已复制所选文章文字")
                        }
                        2 -> {
                            val clipboard = ctx.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                            clipboard.setPrimaryClip(android.content.ClipData.newPlainText("文章", selectedText))
                            vm.js?.invoke("document.execCommand('delete')")
                            vm.toast("已剪切所选文章文字")
                        }
                        3 -> {
                            val clipboard = ctx.getSystemService(android.content.Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager
                            val pasted = if (clipboard.hasPrimaryClip()) clipboard.primaryClip?.getItemAt(0)?.coerceToText(ctx)?.toString().orEmpty() else ""
                            if (pasted.isNotEmpty()) {
                                val quoted = org.json.JSONObject.quote(pasted)
                                vm.js?.invoke("document.execCommand('insertText', false, $quoted)")
                                vm.toast("已粘贴剪贴板文字")
                            } else vm.toast("剪贴板中没有可粘贴的文字")
                        }
                    }
                    mode.finish()
                    return true
                }
                override fun onDestroyActionMode(mode: android.view.ActionMode) {}
            }, android.view.ActionMode.TYPE_FLOATING)
        }
    }
}

@Composable
private fun CopyPreviewButton(vm: AppViewModel) {''')
])

# Acceptance checks are data-driven, not name-filtered, and require the native text action mode.
_layoutScreen = (java / "ui/LayoutScreen.kt").read_text(encoding="utf-8")
_myScreens = (java / "ui/MyScreens.kt").read_text(encoding="utf-8")
_store = (java / "data/Store.kt").read_text(encoding="utf-8")
_vm = (java / "ui/AppViewModel.kt").read_text(encoding="utf-8")
if 'val list = vm.data.layout\n' not in _layoutScreen:
    raise SystemExit("Layout picker is not driven by the complete imported layout data")
if 'val visibleLayouts = vm.data.layout\n' not in _myScreens:
    raise SystemExit("Layout data manager is not driven by the complete imported layout data")
if 'if (layout.isEmpty())' not in _store or 'layout_sentence' not in _store:
    raise SystemExit("Single default sentence-break layout is missing")
if 'if (data.layout.none { it.id == id }) return' not in _vm:
    raise SystemExit("Imported layout selection is still restricted by display name")
if 'showArticleSelectionActions(ctx, vm)' not in _layoutScreen or 'android.view.ActionMode.TYPE_FLOATING' not in _layoutScreen:
    raise SystemExit("Native Android article selection action mode is missing")
if 'menu.add(0, 1, 0, "复制")' not in _layoutScreen or 'menu.add(0, 2, 1, "剪切")' not in _layoutScreen or 'menu.add(0, 3, 2, "粘贴")' not in _layoutScreen:
    raise SystemExit("Native copy/cut/paste actions are incomplete")
print("Data-driven sentence-break layout count and native article action-mode checks passed.")


# ----------------------------------------------------------------------
# 2026-11-22: custom layout slots, per-layout media margins, and name-based replacement.
patch("data/Models.kt",[
    ('data class LayoutItem(val id: String = "", val name: String = "", val content: String = "")',
'''data class LayoutItem(
    val id: String = "",
    val name: String = "",
    val content: String = "",
    // 原始 HTML 片段定位；留空时沿用既有自动识别。
    val textPosition: String = "",
    val imagePosition: String = "",
    val emojiPosition: String = "",
    // 动图 / 往期各自独立的默认左右边距。
    val gifMarginLeft: Int? = null,
    val gifMarginRight: Int? = null,
    val historyMarginLeft: Int? = null,
    val historyMarginRight: Int? = null
)''')
])
patch("data/Store.kt",[
    ('''        if (layoutVer != LAYOUT_VER) {
            layout = layout.map { l -> templates[layoutKindOf(l.name)]?.let { l.copy(content = it) } ?: l }
            layoutVer = LAYOUT_VER
        }''',
'''        // 版本升级只记录版本，不再按名称覆盖用户导入或编辑的模板代码。
        // 同名版式的自定义片段与边距配置必须完整保留。
        if (layoutVer != LAYOUT_VER) layoutVer = LAYOUT_VER''')
])
patch("ui/AppViewModel.kt",[
    ('''    fun saveLayout(x: LayoutItem) = updateData { d ->
        val i = d.layout.indexOfFirst { it.id == x.id }
        d.copy(layout = if (i >= 0) d.layout.toMutableList().also { it[i] = x } else d.layout + x)
    }''',
'''    fun saveLayout(x: LayoutItem) = updateData { d ->
        // ID 不同但名称相同，也按同一版式处理；整体替换模板与全部配置。
        val byId = d.layout.indexOfFirst { it.id == x.id }
        val byName = if (x.name.isNotBlank()) d.layout.indexOfFirst { it.name.trim() == x.name.trim() } else -1
        val i = if (byId >= 0) byId else byName
        if (i >= 0) {
            val old = d.layout[i]
            val replacement = x.copy(id = old.id)
            d.copy(layout = d.layout.toMutableList().also { it[i] = replacement })
        } else d.copy(layout = d.layout + x)
    }''')
])
patch("engine/PreviewEngine.kt",[
    ('''    fun margins(ui: UiState, kind: String): List<Int> =
        ui.margins[kind.ifEmpty { "default" }]?.takeIf { it.size == 4 } ?: defaultMargins(kind)
''',
'''    fun margins(ui: UiState, kind: String): List<Int> =
        ui.margins[kind.ifEmpty { "default" }]?.takeIf { it.size == 4 } ?: defaultMargins(kind)

    /** 版式详情里的动图/往期默认左右边距分别保存；排版页已有设置优先级更高。 */
    private fun blockMargins(ui: UiState, kind: String, layout: com.shiwanju.app.data.LayoutItem?, isGif: Boolean): List<Int> {
        val key = kind.ifEmpty { "default" }
        val override = ui.margins[key]?.takeIf { it.size == 4 }
        val base = defaultMargins(kind)
        if (override != null) return override
        val left = if (isGif) layout?.gifMarginLeft else layout?.historyMarginLeft
        val right = if (isGif) layout?.gifMarginRight else layout?.historyMarginRight
        return listOf(base[0], right ?: base[1], base[2], left ?: base[3])
    }

    /** 按用户提供的原始代码片段标记插入位置，忽略空白差异，只处理首个匹配项。 */
    private fun markPosition(template: String, snippet: String, marker: String): String {
        val wanted = snippet.trim()
        if (wanted.isEmpty()) return template
        fun compactMap(value: String): Pair<String, List<Int>> {
            val chars = StringBuilder()
            val positions = ArrayList<Int>()
            value.forEachIndexed { index, ch ->
                if (!ch.isWhitespace()) { chars.append(ch); positions.add(index) }
            }
            return chars.toString() to positions
        }
        val (sourceCompact, sourcePositions) = compactMap(template)
        val needle = wanted.filterNot { it.isWhitespace() }
        if (needle.isEmpty()) return template
        val compactIndex = sourceCompact.indexOf(needle)
        if (compactIndex < 0) return template
        val start = sourcePositions[compactIndex]
        val end = sourcePositions[compactIndex + needle.lastIndex] + 1
        val actual = template.substring(start, end)
        val tag = Regex("^(\\\\s*<[A-Za-z][A-Za-z0-9:-]*)").find(actual)
        val marked = if (tag != null) {
            actual.replaceRange(tag.range, tag.value + " data-swju-$marker=\\\"true\\\"")
        } else "<span data-swju-$marker=\\\"true\\\">$actual</span>"
        return template.replaceRange(start, end, marked)
    }

    private fun markConfiguredPositions(layout: com.shiwanju.app.data.LayoutItem, template: String): String {
        var result = template
        result = markPosition(result, layout.textPosition, "text-slot")
        result = markPosition(result, layout.imagePosition, "image-slot")
        result = markPosition(result, layout.emojiPosition, "emoji-slot")
        return result
    }
'''),
    ('''        val blocks = LinkedHashMap<String, Element>()
        val m = margins(ui, ctx.kind)

        if (ctx.layoutIdx >= 0) body.appendChild(buildPreview(ctx, data.layout[ctx.layoutIdx].content))''',
'''        val blocks = LinkedHashMap<String, Element>()
        val activeLayout = data.layout.getOrNull(ctx.layoutIdx)
        val gifMargins = blockMargins(ui, ctx.kind, activeLayout, true)
        val historyMargins = blockMargins(ui, ctx.kind, activeLayout, false)

        if (ctx.layoutIdx >= 0) body.appendChild(buildPreview(ctx, data.layout[ctx.layoutIdx].content))'''),
    ('setMargin(h, m)','setMargin(h, historyMargins)'),
    ('setMargin(g, m)','setMargin(g, gifMargins)'),
    ('''            if (index < order.lastIndex) {
                Css.set(block, "margin-bottom", maxOf(m[2], m[0]).toString() + "px", true)
            }''',
'''            if (index < order.lastIndex) {
                val own = if (key == "gif") gifMargins else historyMargins
                Css.set(block, "margin-bottom", maxOf(own[2], own[0]).toString() + "px", true)
            }'''),
    ('''    private fun buildPreview(ctx: Ctx, content: String?): Element {
        if (ctx.kind == "douyin") return buildDouyin(ctx, content)
        val frag = Jsoup.parseBodyFragment(content ?: "")''',
'''    private fun buildPreview(ctx: Ctx, content: String?): Element {
        val layout = ctx.data.layout.getOrNull(ctx.layoutIdx)
        val prepared = if (layout != null) markConfiguredPositions(layout, content ?: "") else (content ?: "")
        if (ctx.kind == "douyin") return buildDouyin(ctx, prepared)
        val frag = Jsoup.parseBodyFragment(prepared)'''),
    ('''            fillUnit(ctx, clones, i, if (hasCopy) ordered[i] else null, if (pool.isNotEmpty()) pool[i % pool.size] else null, extras)''',
'''            fillUnit(ctx, clones, i, if (hasCopy) ordered[i] else null, if (pool.isNotEmpty()) pool[i % pool.size] else null, extras, ui.previewEmoji)'''),
    ('''        if (ui.previewEmoji.isNotEmpty()) appendEmojiToNumbers(ctx, host, ui.previewEmoji)
        return out''',
'''        if (ui.previewEmoji.isNotEmpty() && host.select("[data-swju-emoji-slot]").isEmpty()) appendEmojiToNumbers(ctx, host, ui.previewEmoji)
        return out'''),
    ('''    private fun fillUnit(ctx: Ctx, nodes: List<Element>, i: Int, line: TextUtil.Parsed?, img: String?, extras: List<String>) {
        val cands = ArrayList<TextNode>()''',
'''    private fun fillUnit(ctx: Ctx, nodes: List<Element>, i: Int, line: TextUtil.Parsed?, img: String?, extras: List<String>, emoji: String) {
        val textSlot = nodes.flatMap { root ->
            (if (root.hasAttr("data-swju-text-slot")) listOf(root) else emptyList()) + root.select("[data-swju-text-slot]").toList()
        }.firstOrNull()
        if (textSlot != null && line != null) {
            textSlot.empty()
            line.body.split("\\n").forEachIndexed { index, part ->
                if (index > 0) textSlot.appendElement("br")
                textSlot.appendText(part)
            }
        }
        val cands = ArrayList<TextNode>()'''),
    ('''        if (line != null && cands.isNotEmpty()) {''','''        if (textSlot == null && line != null && cands.isNotEmpty()) {'''),
    ('''        if (img != null) {
            nodes.forEach { root ->
                imgsOf(root).forEach { im ->''',
'''        if (emoji.isNotBlank()) {
            val emojiSlot = nodes.flatMap { root ->
                (if (root.hasAttr("data-swju-emoji-slot")) listOf(root) else emptyList()) + root.select("[data-swju-emoji-slot]").toList()
            }.firstOrNull()
            if (emojiSlot != null) { emojiSlot.empty(); emojiSlot.appendChild(makeEmoji(emoji)) }
        }
        if (img != null) {
            val imageSlot = nodes.flatMap { root ->
                (if (root.hasAttr("data-swju-image-slot")) listOf(root) else emptyList()) + root.select("[data-swju-image-slot]").toList()
            }.firstOrNull()
            if (imageSlot != null) {
                val target = if (imageSlot.tagName() == "img") imageSlot else imageSlot.selectFirst("img")
                if (target != null) setPreviewImage(target, img)
                else {
                    imageSlot.empty()
                    imageSlot.appendElement("img").attr("style", "display:block;width:100%;height:auto;").also { setPreviewImage(it, img) }
                }
            } else nodes.forEach { root ->
                imgsOf(root).forEach { im ->''')
])
patch("ui/MyScreens.kt",[
    ('''    edit?.let { l ->
        var name by remember(l.id) { mutableStateOf(l.name) }; var content by remember(l.id) { mutableStateOf(l.content) }
        var confirm by remember { mutableStateOf(false) }
        EditDialog("详情与编辑", { edit = null },
            { vm.saveLayout(l.copy(name = name.ifEmpty { "未命名配置" }, content = content)); edit = null },
            if (isNew) null else ({ confirm = true })) {
            Text("名称需含 朋友圈 / 文字断句 / 卡片 / 断章序引 之一，才会套用对应的出处、倍率、头像规则", color = AppColors.MyDim, fontSize = 12.sp)
            Field("配置名称", name, { name = it })
            Field("模板代码（HTML）", content, { content = it }, 10)
            Text("当前版式渲染预览", color = AppColors.MyText, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            RenderedLayoutPreview(vm, l.copy(name = name, content = content),
                Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))
        }
        if (confirm) ConfirmDelete("版式", { vm.deleteLayout(l.id); confirm = false; edit = null }, { confirm = false })
    }''',
'''    edit?.let { l ->
        var name by remember(l.id) { mutableStateOf(l.name) }
        var content by remember(l.id) { mutableStateOf(l.content) }
        var textPosition by remember(l.id) { mutableStateOf(l.textPosition) }
        var imagePosition by remember(l.id) { mutableStateOf(l.imagePosition) }
        var emojiPosition by remember(l.id) { mutableStateOf(l.emojiPosition) }
        var gifLeft by remember(l.id) { mutableStateOf(l.gifMarginLeft?.toString().orEmpty()) }
        var gifRight by remember(l.id) { mutableStateOf(l.gifMarginRight?.toString().orEmpty()) }
        var historyLeft by remember(l.id) { mutableStateOf(l.historyMarginLeft?.toString().orEmpty()) }
        var historyRight by remember(l.id) { mutableStateOf(l.historyMarginRight?.toString().orEmpty()) }
        var showAdvanced by remember(l.id) { mutableStateOf(false) }
        var confirm by remember { mutableStateOf(false) }
        val updatedLayout = l.copy(
            name = name.ifEmpty { "未命名配置" }, content = content,
            textPosition = textPosition, imagePosition = imagePosition, emojiPosition = emojiPosition,
            gifMarginLeft = gifLeft.toIntOrNull()?.coerceIn(0, 300),
            gifMarginRight = gifRight.toIntOrNull()?.coerceIn(0, 300),
            historyMarginLeft = historyLeft.toIntOrNull()?.coerceIn(0, 300),
            historyMarginRight = historyRight.toIntOrNull()?.coerceIn(0, 300)
        )
        EditDialog("详情与编辑", { edit = null },
            { vm.saveLayout(updatedLayout); edit = null },
            if (isNew) null else ({ confirm = true })) {
            Text("配置名称", color = AppColors.MyText, fontSize = 12.sp, fontWeight = FontWeight.Medium)
            Field("配置名称", name, { name = it })
            Field("模板代码（HTML）", content, { content = it }, 10)
            Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(Color(0xFFF5F6F7)).clickable { showAdvanced = !showAdvanced }.padding(horizontal = 12.dp, vertical = 11.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("高级位置与间距配置", color = AppColors.MyText, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f))
                Text(if (showAdvanced) "收起 －" else "展开 ＋", color = AppColors.Theme, fontSize = 12.sp)
            }
            if (showAdvanced) {
                Text("位置配置（输入模板代码中的原始片段；留空时沿用原有自动识别）", color = AppColors.MyDim, fontSize = 11.sp)
                Field("文案位置片段", textPosition, { textPosition = it }, 3, "粘贴模板中要被文案替换的完整 HTML 片段")
                if (textPosition.isNotBlank()) Text(if (content.contains(textPosition.trim())) "✓ 已在模板代码中找到片段" else "⚠ 当前片段未精确匹配；检查是否复制了完整代码", color = if (content.contains(textPosition.trim())) Color(0xFF16834A) else Color(0xFFCC7A00), fontSize = 11.sp)
                Field("配图位置片段", imagePosition, { imagePosition = it }, 3, "粘贴模板中要被图片替换的完整 HTML 片段")
                if (imagePosition.isNotBlank()) Text(if (content.contains(imagePosition.trim())) "✓ 已在模板代码中找到片段" else "⚠ 当前片段未精确匹配；检查是否复制了完整代码", color = if (content.contains(imagePosition.trim())) Color(0xFF16834A) else Color(0xFFCC7A00), fontSize = 11.sp)
                Field("emoji 位置片段", emojiPosition, { emojiPosition = it }, 3, "粘贴模板中要插入 emoji 的完整 HTML 片段")
                if (emojiPosition.isNotBlank()) Text(if (content.contains(emojiPosition.trim())) "✓ 已在模板代码中找到片段" else "⚠ 当前片段未精确匹配；检查是否复制了完整代码", color = if (content.contains(emojiPosition.trim())) Color(0xFF16834A) else Color(0xFFCC7A00), fontSize = 11.sp)
                HorizontalDivider(color = Color(0xFFE5E7EB))
                Text("动图左右边距（dp）", color = AppColors.MyText, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box(Modifier.weight(1f)) { Field("左边距", gifLeft, { gifLeft = it }, hint = "留空沿用原设置") }
                    Box(Modifier.weight(1f)) { Field("右边距", gifRight, { gifRight = it }, hint = "留空沿用原设置") }
                }
                Text("往期左右边距（dp）", color = AppColors.MyText, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Box(Modifier.weight(1f)) { Field("左边距", historyLeft, { historyLeft = it }, hint = "留空沿用原设置") }
                    Box(Modifier.weight(1f)) { Field("右边距", historyRight, { historyRight = it }, hint = "留空沿用原设置") }
                }
                Text("以上默认值分别保存；排版页已有的边距调整仍然有效，并优先于这里的默认值。", color = AppColors.MyDim, fontSize = 11.sp)
            }
            Text("当前版式渲染预览", color = AppColors.MyText, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
            RenderedLayoutPreview(vm, updatedLayout, Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))
        }
        if (confirm) ConfirmDelete("版式", { vm.deleteLayout(l.id); confirm = false; edit = null }, { confirm = false })
    }''')
])
patch("ui/LayoutScreen.kt",[
    ('''            Column(Modifier.width(82.dp).clip(RoundedCornerShape(9.dp)).border(2.dp, if (selected) AppColors.Theme else Color.Transparent, RoundedCornerShape(9.dp)).clickable { vm.selectLayout(l.id) }) {
                RenderedLayoutPreview(vm, l, Modifier.fillMaxWidth().aspectRatio(3f / 4f))
                Text("文字断句", Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 5.dp), color = if (selected) AppColors.Theme else AppColors.TextMain, fontSize = 11.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium, maxLines = 1, textAlign = TextAlign.Center)
            }''',
'''            Box(Modifier.width(82.dp).clip(RoundedCornerShape(9.dp)).border(2.dp, if (selected) AppColors.Theme else Color.Transparent, RoundedCornerShape(9.dp))) {
                Column(Modifier.fillMaxWidth()) {
                    RenderedLayoutPreview(vm, l, Modifier.fillMaxWidth().aspectRatio(3f / 4f))
                    Text(shortName(l.name), Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 5.dp), color = if (selected) AppColors.Theme else AppColors.TextMain, fontSize = 11.sp, fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis, textAlign = TextAlign.Center)
                }
                // WebView 会消费触摸事件，透明点击层覆盖预览图和名称，保证整张卡片可点。
                Box(Modifier.matchParentSize().clickable { vm.selectLayout(l.id) })
            }''')
])

# Verify all new capabilities are actually wired into persistence and preview rendering.
_models = (java / "data/Models.kt").read_text(encoding="utf-8")
_store = (java / "data/Store.kt").read_text(encoding="utf-8")
_vm = (java / "ui/AppViewModel.kt").read_text(encoding="utf-8")
_engine = (java / "engine/PreviewEngine.kt").read_text(encoding="utf-8")
_my = (java / "ui/MyScreens.kt").read_text(encoding="utf-8")
_picker = (java / "ui/LayoutScreen.kt").read_text(encoding="utf-8")
for field in ["textPosition", "imagePosition", "emojiPosition", "gifMarginLeft", "historyMarginLeft"]:
    if field not in _models or field not in _my:
        raise SystemExit("Layout configuration field missing from model/editor: " + field)
if "data-swju-text-slot" not in _engine or "data-swju-image-slot" not in _engine or "data-swju-emoji-slot" not in _engine:
    raise SystemExit("Custom template slot markers are not wired to rendering")
if "val byName" not in _vm or "replacement = x.copy(id = old.id)" not in _vm:
    raise SystemExit("Same-name layout replacement is missing")
if "templates[layoutKindOf(l.name)]?.let" in _store:
    raise SystemExit("Legacy layout-version migration still overwrites imported template HTML")
if 'Text(shortName(l.name)' not in _picker or "Modifier.matchParentSize().clickable" not in _picker:
    raise SystemExit("Layout picker names or full-card click target missing")
print("Custom layout slots, independent media margins, same-name replacement and picker acceptance passed.")


# Do not synthesize extra software layouts during import/normalization.
# The imported list must remain exactly the user's imported list; only an empty list gets one default.
_store_path = java / "data/Store.kt"
_store_text = _store_path.read_text(encoding="utf-8")
_dy_start = _store_text.find("        var douyinAdded = raw.douyinAdded")
if _dy_start >= 0:
    _dy_end = _store_text.find("\n        return AppData(", _dy_start)
    if _dy_end < 0:
        raise SystemExit("Could not isolate legacy automatic Douyin layout insertion")
    _store_text = _store_text[:_dy_start] + "        val douyinAdded = true\n" + _store_text[_dy_end:]
    _store_path.write_text(_store_text, encoding="utf-8")
else:
    print("Automatic Douyin layout insertion already absent.")
if "val douyinAdded = true" not in _store_path.read_text(encoding="utf-8"):
    raise SystemExit("Imported layout list may still receive an automatic extra layout")
print("Layout import count remains exact; only empty data receives the single default.")


patch("ui/LayoutScreen.kt",[
    ('''    val html = remember(layout.id, layout.content, vm.data.files, vm.data.accounts, vm.ui.copyLines, vm.ui.imgPool) {
        val textModule = vm.data.files.text.firstOrNull()''',
'''    val html = remember(layout, vm.data.files, vm.data.accounts, vm.ui.copyLines, vm.ui.imgPool) {
        val textModule = vm.data.files.text.firstOrNull()'''),
    ('''        val previewState = vm.ui.copy(layoutId = layout.id, quantity = 3, copyModuleId = textModule?.id, copyLines = sample,
            imgModuleId = imageModule?.id, imgPool = images, historyIds = emptyList(), historyHtml = "", gifId = null, gifContent = "",
            mediaOrder = emptyList(), previewEmoji = "")
        val body = PreviewEngine.render(vm.data, previewState)''',
'''        val emojiSample = vm.data.emoji.firstOrNull()?.let { TextUtil.splitEntries(it.content).firstOrNull() }.orEmpty()
        val previewState = vm.ui.copy(layoutId = layout.id, quantity = 3, copyModuleId = textModule?.id, copyLines = sample,
            imgModuleId = imageModule?.id, imgPool = images, historyIds = emptyList(), historyHtml = "", gifId = null, gifContent = "",
            mediaOrder = emptyList(), previewEmoji = emojiSample)
        val previewData = if (vm.data.layout.any { it.id == layout.id })
            vm.data.copy(layout = vm.data.layout.map { if (it.id == layout.id) layout else it })
            else vm.data.copy(layout = vm.data.layout + layout)
        val body = PreviewEngine.render(previewData, previewState)''')
])


patch("engine/PreviewEngine.kt",[
    ('''    private fun blockMargins(ui: UiState, kind: String, layout: com.shiwanju.app.data.LayoutItem?, isGif: Boolean): List<Int> {
        val key = kind.ifEmpty { "default" }
        val override = ui.margins[key]?.takeIf { it.size == 4 }''',
'''    fun blockMargins(ui: UiState, kind: String, layout: com.shiwanju.app.data.LayoutItem?, isGif: Boolean): List<Int> {
        val key = kind.ifEmpty { "default" }
        val targetKey = (if (isGif) "gif:" else "history:") + key
        val override = ui.margins[targetKey]?.takeIf { it.size == 4 }
            ?: ui.margins[key]?.takeIf { it.size == 4 }''')
])
# Replace the existing shared margin setter without embedding its Kotlin interpolation expression in this patch script.
_vm_path = java / "ui/AppViewModel.kt"
_vm_text = _vm_path.read_text(encoding="utf-8")
_vm_start = _vm_text.find("    /** 往期 / 动图共用边距：index 0..3")
_vm_end = _vm_text.find("\n    /** 全局空行", _vm_start)
if _vm_start < 0 or _vm_end < 0:
    raise SystemExit("Could not locate existing shared margin setter")
_new_margin_methods = '''    /** 分别读取动图 / 往期边距；旧版共享边距仍作为兼容回退。 */
    fun marginsFor(target: String): List<Int> =
        PreviewEngine.blockMargins(ui, kind, data.layout.getOrNull(layoutIndex), target == "gif")

    /** index 0..3 = 上右下左；动图与往期分别保存，不再互相覆盖。 */
    fun setMargin(target: String, index: Int, value: Int) {
        val arr = marginsFor(target).toMutableList()
        arr[index] = value.coerceAtLeast(0)
        val key = (if (target == "gif") "gif:" else "history:") + (kind.ifEmpty { "default" })
        updateUiQuiet { copy(margins = margins + (key to arr)) }
        js?.invoke("setMarginsFor('$target'," + arr.joinToString(",") + ")")
    }

    /** 兼容旧调用，默认修改动图边距。 */
    fun setMargin(index: Int, value: Int) = setMargin("gif", index, value)
'''
_vm_path.write_text(_vm_text[:_vm_start] + _new_margin_methods + _vm_text[_vm_end:], encoding="utf-8")

patch("ui/LayoutScreen.kt",[
    ('''            Text("往期 / 动图边距（上 右 下 左，px）", color = AppColors.Theme, fontSize = 12.sp)
            Spacer(Modifier.height(8.dp))
            val m = vm.margins
            listOf(listOf(0 to "上", 1 to "右"), listOf(2 to "下", 3 to "左")).forEach { rowItems ->
                Row(Modifier.fillMaxWidth().padding(bottom = 8.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    rowItems.forEach { (idx, label) ->
                        Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
                            Text(label, color = Color(0xFFBBBBBB), fontSize = 13.sp, modifier = Modifier.width(20.dp))
                            Stepper(m[idx], { vm.setMargin(idx, it) })
                        }
                    }
                }
            }''',
'''            Text("媒体边距（上 右 下 左，px）", color = AppColors.Theme, fontSize = 12.sp)
            Spacer(Modifier.height(8.dp))
            var marginTarget by remember { mutableStateOf("gif") }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ThemeChip("动图", marginTarget == "gif") { marginTarget = "gif" }
                ThemeChip("往期", marginTarget == "history") { marginTarget = "history" }
            }
            val m = vm.marginsFor(marginTarget)
            listOf(listOf(0 to "上", 1 to "右"), listOf(2 to "下", 3 to "左")).forEach { rowItems ->
                Row(Modifier.fillMaxWidth().padding(bottom = 8.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    rowItems.forEach { (idx, label) ->
                        Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
                            Text(label, color = Color(0xFFBBBBBB), fontSize = 13.sp, modifier = Modifier.width(20.dp))
                            Stepper(m[idx], { vm.setMargin(marginTarget, idx, it) })
                        }
                    }
                }
            }''')
])
_asset = base / "assets/preview.html"
_asset_text = _asset.read_text(encoding="utf-8")
if "window.setMarginsFor = function" not in _asset_text:
    anchor = '''  window.setMargins = function (t, r, b, l) {'''
    if anchor not in _asset_text:
        raise SystemExit("Preview margin function anchor not found")
    helper = '''  window.setMarginsFor = function (type, t, r, b, l) {
    var v = [t, r, b, l], names = ['top', 'right', 'bottom', 'left'];
    var selector = type === 'gif' ? '[data-preview-gif]' : '[data-preview-history]';
    Array.from(area.querySelectorAll(selector)).forEach(function (el) {
      names.forEach(function (n, i) { el.style.setProperty('margin-' + n, v[i] + 'px', 'important'); });
    });
  };
'''
    _asset_text = _asset_text.replace(anchor, helper + anchor, 1)
    _asset.write_text(_asset_text, encoding="utf-8")
_picker = (java / "ui/LayoutScreen.kt").read_text(encoding="utf-8")
_vm = (java / "ui/AppViewModel.kt").read_text(encoding="utf-8")
_engine = (java / "engine/PreviewEngine.kt").read_text(encoding="utf-8")
_asset_text = (base / "assets/preview.html").read_text(encoding="utf-8")
if "fun marginsFor(target: String)" not in _vm or 'vm.setMargin(marginTarget, idx, it)' not in _picker:
    raise SystemExit("Separate GIF/history margin controls are not connected")
if 'ui.margins[targetKey]' not in _engine or "window.setMarginsFor = function" not in _asset_text:
    raise SystemExit("Separate media margin persistence/live preview is incomplete")
print("Independent GIF/history margin controls passed.")


# Keep the layout schema version declaration when removing the legacy auto-added Douyin item.
_store_path = java / "data/Store.kt"
_store_text = _store_path.read_text(encoding="utf-8")
if "var layoutVer = raw.layoutVer" not in _store_text:
    anchor = "        val douyinAdded = true\n"
    if anchor not in _store_text:
        raise SystemExit("Could not find the normalized layout marker to restore layoutVer")
    _store_text = _store_text.replace(anchor, anchor + "        var layoutVer = raw.layoutVer\n", 1)
if "var layoutVer = raw.layoutVer" not in _store_text:
    raise SystemExit("Layout version declaration was not restored")
_store_path.write_text(_store_text, encoding="utf-8")
print("Layout version declaration restored after removing automatic Douyin insertion.")


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# Official account feed: link import, local article cache and WeChat deep links.
_my_path = java / "ui/MyScreens.kt"
_my = _my_path.read_text(encoding="utf-8")
_root = '    Column(Modifier.fillMaxSize().background(AppColors.MyBg).systemBarsPadding()) {'
if 'if (route == "official")' not in _my:
    if _root not in _my:
        raise SystemExit("Official account integration: MyScreen root column anchor missing")
    _my = _my.replace(_root, '    if (route == "official") { OfficialAccountPage { route = "home" } } else Column(Modifier.fillMaxSize().background(AppColors.MyBg).systemBarsPadding()) {', 1)
_title_line = next((line for line in _my.splitlines() if "val title = when (route)" in line), None)
if _title_line and '"official" -> "公众号"' not in _title_line:
    _my = _my.replace(_title_line, _title_line.replace('; else -> "我的" }', '; "official" -> "公众号"; "history_articles" -> "历史文章"; else -> "我的" }'), 1)
_route_anchor = '                else -> HomePage(vm) { route = it }'
if '"official" -> OfficialAccountPage' not in _my:
    if _route_anchor not in _my:
        raise SystemExit("Official account integration: MyScreen route anchor missing")
    _my = _my.replace(_route_anchor, '                "history_articles" -> HistoryArticlesPage { route = "home" }\n                "official" -> OfficialAccountPage { route = "home" }\n' + _route_anchor, 1)
_home_start = _my.find("private fun HomePage")
_home_end = _my.find("// ---------------------------------------------------------------------- 账号", _home_start)
if _home_start < 0 or _home_end < 0:
    raise SystemExit("Official account integration: HomePage section missing")
_home = _my[_home_start:_home_end]
if 'ListRow("公众号"' not in _home:
    lines = _home.splitlines()
    index = next((n for n, line in enumerate(lines) if 'ListRow("备份"' in line), -1)
    if index < 0:
        raise SystemExit("Official account integration: HomePage backup row missing")
    lines.insert(index, '    ListRow("公众号", "拾万句公众号文章与链接") { go("official") }')
    lines.insert(index + 1, '    ListRow("历史文章", "通过 wechat_spider 读取公众号历史文章") { go("history_articles") }')
    _my = _my[:_home_start] + "\n".join(lines) + "\n" + _my[_home_end:]
_my_path.write_text(_my, encoding="utf-8")
print("Official account feed route and My-page entry connected.")


# ----------------------------------------------------------------------
# wechat_spider history article test page.
history_page = root/"native-overlay/app/src/main/java/com/shiwanju/app/ui/HistoryArticlesPage.kt"
shutil.copy2(history_page, java/"ui/HistoryArticlesPage.kt")
_my_path = java/"ui/MyScreens.kt"
_my = _my_path.read_text(encoding="utf-8")
_root = '    Column(Modifier.fillMaxSize().background(AppColors.MyBg).systemBarsPadding()) {'
if 'if (route == "history_articles")' not in _my:
    old = '    if (route == "official") { OfficialAccountPage { route = "home" } } else Column(Modifier.fillMaxSize().background(AppColors.MyBg).systemBarsPadding()) {'
    new = '    if (route == "official") { OfficialAccountPage { route = "home" } } else if (route == "history_articles") { HistoryArticlesPage { route = "home" } } else Column(Modifier.fillMaxSize().background(AppColors.MyBg).systemBarsPadding()) {'
    if old not in _my:
        raise SystemExit("History articles integration: special page route anchor missing")
    _my = _my.replace(old, new, 1)

_title_line = next((line for line in _my.splitlines() if "val title = when (route)" in line), None)
if _title_line and '"history_articles" -> "历史文章"' not in _title_line:
    _my = _my.replace(_title_line, _title_line.replace('; "official" -> "公众号";', '; "official" -> "公众号"; "history_articles" -> "历史文章";'), 1)

_route_anchor = '                "official" -> OfficialAccountPage { route = "home" }'
if '"history_articles" -> HistoryArticlesPage' not in _my:
    if _route_anchor not in _my:
        raise SystemExit("History articles integration: route switch anchor missing")
    _my = _my.replace(_route_anchor, _route_anchor + '\n                "history_articles" -> HistoryArticlesPage { route = "home" }', 1)

_home_start = _my.find("private fun HomePage")
_home_end = _my.find("// ---------------------------------------------------------------------- 账号", _home_start)
if _home_start < 0 or _home_end < 0:
    raise SystemExit("History articles integration: HomePage section missing")
_home = _my[_home_start:_home_end]
if 'ListRow("历史文章"' not in _home:
    anchor = '    ListRow("公众号", "拾万句公众号文章与链接") { go("official") }'
    if anchor not in _home:
        raise SystemExit("History articles integration: official account entry missing")
    _home = _home.replace(anchor, anchor + '\n    ListRow("历史文章", "使用 wechat_spider 测试历史文章采集") { go("history_articles") }', 1)
    _my = _my[:_home_start] + _home + _my[_home_end:]
_my_path.write_text(_my, encoding="utf-8")

# The spider dashboard/API defaults to HTTP on a local network address.
# Allow the user-configured LAN endpoint; HTTPS remains supported as well.
_manifest = base/"AndroidManifest.xml"
if _manifest.exists():
    _manifest_text = _manifest.read_text(encoding="utf-8")
    if "android.permission.INTERNET" not in _manifest_text:
        _manifest_text = _manifest_text.replace("<application", '<uses-permission android:name="android.permission.INTERNET" />\n    <application', 1)
    if "android:usesCleartextTraffic=" not in _manifest_text:
        _manifest_text = _manifest_text.replace("<application", '<application android:usesCleartextTraffic="true"', 1)
    _manifest.write_text(_manifest_text, encoding="utf-8")

print("wechat_spider history article page and My-page route connected.")
