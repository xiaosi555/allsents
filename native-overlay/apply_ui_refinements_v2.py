#!/usr/bin/env python3
from pathlib import Path
root = Path(".")
base = root / "source/ShiWanJu-Android/app/src/main"
java = base / "java/com/shiwanju/app"

def edit(rel, transform):
    p = java / rel
    s = p.read_text(encoding="utf-8")
    updated = transform(s)
    p.write_text(updated, encoding="utf-8")

def must_replace(s, old, new, label):
    if old not in s:
        raise SystemExit("Required UI patch anchor missing: " + label)
    return s.replace(old, new, 1)

def theme_settings(s):
    return must_replace(s,
        'Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp)).background(AppColors.MyCard).padding(16.dp), verticalArrangement = Arrangement.spacedBy(15.dp)) {',
        'Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(15.dp)) {',
        "theme color outer rectangle")
edit("ui/ThemeSettings.kt", theme_settings)

def icon_settings(s):
    s = s.replace('        Text("图标风格", color = AppColors.MyText, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)\n', '')
    s = s.replace('        Text("选择后会切换手机桌面图标；原版图形轮廓保持一致。", color = Color(0xFF8A8A8A), fontSize = 12.sp)\n', '')
    return s
edit("ui/IconSettings.kt", icon_settings)

def my_screens(s):
    s = s.replace('.shadow(1.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp))',
                  '.clip(RoundedCornerShape(12.dp))')
    s = s.replace('import androidx.compose.ui.draw.shadow\n', '')
    s = must_replace(s,
        '    val tabs = listOf("emoji" to "emoji", "history" to "往期", "gif" to "动图", "image" to "配图")',
        '''    val tabs = listOf("emoji" to "emoji", "history" to "往期", "gif" to "动图", "image" to "配图")
    val visibleHistory = vm.data.history.filterNot { it.id == "1791721426948" || it.id == "1791721454725" }''',
        "visible text-only history presets")
    s = s.replace('"history" -> vm.data.history.forEach { h ->', '"history" -> visibleHistory.forEach { h ->')
    s = s.replace('''                    ListRow(h.name.ifEmpty { "未命名往期" }, "\${count} 条内容 · \${if (h.images.isNotBlank() || h.image.isNotBlank()) "图片版" else "文字版"}") { editKey = h.id }''',
                  '''                    ListRow(h.name.ifEmpty { "未命名往期" }, "\${count} 条内容 · 文字版") { editKey = h.id }''')
    s = s.replace('"history" -> vm.data.history.isEmpty()', '"history" -> visibleHistory.isEmpty()')
    s = must_replace(s,
        '''            var links by remember(key) { mutableStateOf(cur.links.ifEmpty { cur.link }) }
            var images by remember(key) { mutableStateOf(cur.images.ifEmpty { cur.image }) }
            var template by remember(key) { mutableStateOf(cur.content) }
            EditDialog("详情与编辑", close, {
                val ts = titles.trim(); val ls = links.trim(); val ims = images.trim()
                val ft = TextUtil.splitSingleLines(ts).firstOrNull().orEmpty()
                val fl = TextUtil.splitSingleLines(ls).firstOrNull().orEmpty()
                val fi = TextUtil.splitSingleLines(ims).firstOrNull().orEmpty()
                val html = template.ifBlank { PreviewEngine.historyTemplateHtml(ims.isNotBlank()) }
                vm.saveHistory(cur.copy(name = name.trim().ifEmpty { ft.ifEmpty { "未命名配置" } }, title = ft, link = fl, image = fi, titles = ts, links = ls, images = ims, content = html)); close()
            }, if (isNew) null else ({ confirm = true })) {
                Text("配置基本信息", color = AppColors.Theme, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                Field("配置名称", name, { name = it }, hint = "例如：文字版 / 图片版")
                Text("往期内容", color = AppColors.Theme, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                Field("标题（每行一条）", titles, { titles = it }, 3, "标题与链接、图片按行对应")
                Field("链接（每行一个）", links, { links = it }, 3, "每行填写一个文章链接")
                Field("图片地址（每行一个）", images, { images = it }, 3, "留空则使用文字版往期")
                Text("高级模板", color = AppColors.Theme, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                val previewTitles = TextUtil.splitSingleLines(titles)
                val previewLinks = TextUtil.splitSingleLines(links)
                val previewImages = TextUtil.splitSingleLines(images)
                val previewItem = cur.copy(
                    title = previewTitles.firstOrNull().orEmpty(),
                    link = previewLinks.firstOrNull().orEmpty(),
                    image = previewImages.firstOrNull().orEmpty(),
                    titles = titles, links = links, images = images,
                    content = template.ifBlank { PreviewEngine.historyTemplateHtml(previewImages.any { it.isNotBlank() }) }
                )
                val historyHtml = remember(cur.id, titles, links, images, template) {
                    PreviewEngine.composeHistoryHtml(previewItem)
                }
                Field("HTML 模板（可选）", template, { template = it }, 4, "留空时自动使用默认模板")
                Text("往期样式预览", color = AppColors.MyText, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                RawHtmlPreview(historyHtml, Modifier.fillMaxWidth().aspectRatio(3f / 4f).clip(RoundedCornerShape(12.dp)))
            }''',
        '''            var links by remember(key) { mutableStateOf(cur.links.ifEmpty { cur.link }) }
            EditDialog("详情与编辑", close, {
                val ts = titles.trim(); val ls = links.trim()
                val ft = TextUtil.splitSingleLines(ts).firstOrNull().orEmpty()
                val fl = TextUtil.splitSingleLines(ls).firstOrNull().orEmpty()
                val html = cur.content.ifBlank { PreviewEngine.historyTemplateHtml(false) }
                // Preserve legacy image fields exactly; this editor only changes text titles and links.
                vm.saveHistory(cur.copy(name = name.trim().ifEmpty { ft.ifEmpty { "未命名配置" } }, title = ft, link = fl, titles = ts, links = ls, content = html)); close()
            }, if (isNew) null else ({ confirm = true })) {
                Text("配置基本信息", color = AppColors.Theme, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                Field("配置名称", name, { name = it }, hint = "例如：文字版")
                Text("往期内容", color = AppColors.Theme, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                Field("标题（每行一条）", titles, { titles = it }, 3, "标题与链接按行对应")
                Field("链接（每行一个）", links, { links = it }, 3, "每行填写一个文章链接")
            }''',
        "text-only history editor")
    return s
edit("ui/MyScreens.kt", my_screens)

def layout_screen(s):
    if 'import androidx.compose.foundation.Image\n' not in s:
        s = s.replace('import androidx.compose.foundation.BorderStroke\n',
                      'import androidx.compose.foundation.BorderStroke\nimport androidx.compose.foundation.Image\n')
    if 'import androidx.compose.ui.res.painterResource\n' not in s:
        s = s.replace('import androidx.compose.ui.platform.LocalDensity\n',
                      'import androidx.compose.ui.platform.LocalDensity\nimport androidx.compose.ui.res.painterResource\n')
    if 'import com.shiwanju.app.R\n' not in s:
        s = s.replace('import com.shiwanju.app.data.LayoutItem\n',
                      'import com.shiwanju.app.R\nimport com.shiwanju.app.data.LayoutItem\n')
    s = must_replace(s,
        '''private fun TopBar(vm: AppViewModel) {
    val ctx = LocalContext.current
    Row(Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 14.dp), verticalAlignment = Alignment.CenterVertically) {
        Text("拾万句", color = Color.White, fontSize = 17.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.width(10.dp))
        Text("\${vm.charCount}字", color = AppColors.TextDim, fontSize = 12.sp)
        Spacer(Modifier.weight(1f))
        ThemeChip("复制", false) { copyRenderedPreview(ctx, vm) }
        Spacer(Modifier.width(8.dp))
        ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing) { vm.toggleEditing() }
    }
}''',
        '''private fun TopBar(vm: AppViewModel) {
    Row(Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 14.dp), verticalAlignment = Alignment.CenterVertically) {
        Image(
            painter = painterResource(R.drawable.app_logo),
            contentDescription = "拾万句",
            contentScale = ContentScale.Fit,
            modifier = Modifier.size(width = 28.dp, height = 27.dp)
        )
        Spacer(Modifier.weight(1f))
        Text("\${vm.charCount}字", color = AppColors.TextDim, fontSize = 12.sp)
        Spacer(Modifier.width(10.dp))
        ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing) { vm.toggleEditing() }
    }
}''',
        "layout toolbar logo and character count")
    old = '''    var showFolderName by remember { mutableStateOf(true) }
    LaunchedEffect(listState) {
        snapshotFlow { listState.isScrollInProgress to listState.lastScrolledForward }.collect { (scrolling, forward) ->
            if (scrolling) showFolderName = !forward
        }
    }'''
    new = '''    var showFolderName by remember { mutableStateOf(true) }
    val density = androidx.compose.ui.platform.LocalDensity.current
    LaunchedEffect(listState) {
        val stepPx = with(density) { 72.dp.toPx() }
        val thresholdPx = with(density) { 52.dp.toPx() }
        var previousPosition = 0f
        var direction = 0
        var accumulated = 0f
        var initialized = false
        snapshotFlow { listState.firstVisibleItemIndex to listState.firstVisibleItemScrollOffset }.collect { (index, offset) ->
            val position = index * stepPx + offset
            if (!initialized) {
                previousPosition = position
                initialized = true
            } else {
                val delta = position - previousPosition
                previousPosition = position
                if (kotlin.math.abs(delta) > 0.5f) {
                    val nextDirection = if (delta > 0f) 1 else -1
                    if (nextDirection != direction) {
                        direction = nextDirection
                        accumulated = 0f
                    }
                    accumulated += kotlin.math.abs(delta)
                    if (accumulated >= thresholdPx) {
                        // Finger/content moves right (backward): show source; moves left: hide source.
                        showFolderName = direction > 0
                        accumulated = 0f
                    }
                }
            }
        }
    }'''
    s = must_replace(s, old, new, "image folder name scroll threshold")
    return s
edit("ui/LayoutScreen.kt", layout_screen)

def history_selector(s):
    s = must_replace(s,
        '''        "history" -> if (vm.data.history.isEmpty()) EmptyTip("暂无往期，请到【我的】-更多-往期中添加")
        else {
            val on = vm.ui.historyIds.isNotEmpty()
            GridCards {
                vm.data.history.forEach { h -> GridCard(h.name.ifEmpty { h.title.ifEmpty { "未命名往期" } }, vm.ui.historyIds.contains(h.id)) { vm.rollHistory(h.id) } }''',
        '''        "history" -> {
            val availableHistory = vm.data.history.filterNot { it.id == "1791721426948" || it.id == "1791721454725" }
            if (availableHistory.isEmpty()) EmptyTip("暂无文字版往期，请到【我的】-更多-往期中添加")
            else {
            val on = vm.ui.historyIds.isNotEmpty()
            GridCards {
                availableHistory.forEach { h -> GridCard(h.name.ifEmpty { h.title.ifEmpty { "未命名往期" } }, vm.ui.historyIds.contains(h.id)) { vm.rollHistory(h.id) } }''',
        "layout text-only history picker")
    s = must_replace(s,
        '''                Text("共 \${vm.data.history.size} 条", color = AppColors.TextDim, fontSize = 12.sp, modifier = Modifier.padding(top = 10.dp))
            }
        }
        else ->''',
        '''                Text("共 \${availableHistory.size} 条", color = AppColors.TextDim, fontSize = 12.sp, modifier = Modifier.padding(top = 10.dp))
            }
            }
        }
        else ->''',
        "layout history picker block closure")
    return s
edit("ui/LayoutScreen.kt", history_selector)

def app_view_model(s):
    s = must_replace(s,
        'val hids = u.historyIds.filter { id -> data.history.any { it.id == id } }',
        'val hids = u.historyIds.filter { id -> id != "1791721426948" && id != "1791721454725" && data.history.any { it.id == id } }',
        "validate history selection")
    s = must_replace(s,
        '''        if (data.history.isEmpty()) return toast("暂无往期条目，请到【我的】-更多-往期中添加")
        val selectedId = ui.historyIds.firstOrNull()
        val item = data.history.firstOrNull { it.id == id }
            ?: data.history.firstOrNull { it.id == selectedId }
            ?: data.history.first()''',
        '''        val available = data.history.filterNot { it.id == "1791721426948" || it.id == "1791721454725" }
        if (available.isEmpty()) return toast("暂无文字版往期条目，请到【我的】-更多-往期中添加")
        val selectedId = ui.historyIds.firstOrNull()
        val item = available.firstOrNull { it.id == id }
            ?: available.firstOrNull { it.id == selectedId }
            ?: available.first()''',
        "roll only visible text history")
    return s
edit("ui/AppViewModel.kt", app_view_model)

print("UI refinement v2 passed: unboxed theme swatches, icon copy removed, flat My cards, text-only history presets, thresholded folder label, white logo toolbar.")
