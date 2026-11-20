#!/usr/bin/env python3
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
base=root/"source/ShiWanJu-Android/app/src/main"
java=base/"java/com/shiwanju/app"
def patch(rel,pairs):
 p=java/rel;s=p.read_text(encoding="utf-8")
 for a,b in pairs:
  if a not in s: raise SystemExit("Patch anchor missing: "+rel+" :: "+a[:80])
  s=s.replace(a,b,1)
 p.write_text(s,encoding="utf-8")
shutil.copy2(root/"native-overlay/app/src/main/assets/douyin_template.html",base/"assets/douyin_template.html")
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
    dismissButton = { TextButton(onClick = onCancel) { Text("取消", color = AppColors.MyDim) } }
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
