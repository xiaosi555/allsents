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
     '''    ListRow("账号", "多账号管理、配置信息 · ${d.accounts.size}") { go("accounts") }
    ListRow("文案", "文案模块管理、排序 · ${d.files.text.size}") { go("texts") }
    ListRow("版式", "布局、排版预览、代码渲染 · ${d.layout.size}") { go("layouts") }
    ListRow("更多", "emoji、往期、动图、配图") { go("more") }
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
                AsyncImage(t.bg, null, Modifier.fillMaxWidth().weight(1f), contentScale = ContentScale.Crop)
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
