#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
import traceback

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
UI = JAVA / "ui"
DATA = JAVA / "data"

def fail(message):
    (ROOT / "article_editor_patch_error.txt").write_text(message + "\n" + traceback.format_exc(), encoding="utf-8")
    raise SystemExit(message)

try:
    shutil.copy2(ROOT / "native-overlay/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt", UI / "ArticleEditorScreen.kt")
except Exception as error:
    fail("Unable to copy ArticleEditorScreen.kt: " + repr(error))

def replace_once(path, old, new, label):
    s = path.read_text(encoding="utf-8")
    if new in s:
        return
    if old not in s:
        fail("Article editor patch anchor missing: " + label)
    path.write_text(s.replace(old, new, 1), encoding="utf-8")

# Data model: reusable style blocks and editable article documents.
p = DATA / "Models.kt"
replace_once(p,
'''data class EmojiItem(val id: String = "", val name: String = "", val content: String = "")''',
'''data class EmojiItem(val id: String = "", val name: String = "", val content: String = "")

data class StyleModule(
    val id: String = "",
    val name: String = "",
    val category: String = "",
    val html: String = "",
    val updatedAt: String = "",
    val isFavorite: Boolean = false,
    val type: String = "component",
    val thumbnail: String = "",
    val tags: List<String> = emptyList()
)

data class ArticleDocument(
    val id: String = "",
    val title: String = "",
    val html: String = "",
    val createdAt: String = "",
    val updatedAt: String = "",
    val subtitle: String = "",
    val summary: String = "",
    val author: String = "",
    val coverAssetId: String = "",
    val category: String = "",
    val tags: List<String> = emptyList(),
    val status: String = "draft",
    val wordCount: Int = 0,
    val isFavorite: Boolean = false
)

data class MediaAsset(
    val id: String = "",
    val fileName: String = "",
    val mimeType: String = "",
    val relativePath: String = "",
    val sizeBytes: Long = 0L,
    val createdAt: String = ""
)

data class ArticleRevision(
    val id: String = "",
    val articleId: String = "",
    val title: String = "",
    val html: String = "",
    val createdAt: String = "",
    val note: String = "",
    val subtitle: String = "",
    val summary: String = "",
    val author: String = "",
    val coverAssetId: String = "",
    val category: String = "",
    val tags: List<String> = emptyList(),
    val status: String = "draft",
    val isFavorite: Boolean = false
)''', "style and article data classes")
replace_once(p,
'''    val emoji: List<EmojiItem> = emptyList(),
    val files: Files = Files(),''',
'''    val emoji: List<EmojiItem> = emptyList(),
    val styles: List<StyleModule> = emptyList(),
    val articles: List<ArticleDocument> = emptyList(),
    val styleSeedApplied: Boolean = false,
    val mediaAssets: List<MediaAsset> = emptyList(),
    val articleRevisions: List<ArticleRevision> = emptyList(),
    val files: Files = Files(),''', "AppData editor fields")

# Keep old JSON backups compatible and preserve new fields on import/export.
p = DATA / "Store.kt"
replace_once(p,
'''            emoji = fill(raw.emoji, "emoji", { it.id }, { x, i -> x.copy(id = i) })
                .map { it.copy(name = it.name ?: "", content = it.content ?: "") },
            files = Files(''',
'''            emoji = fill(raw.emoji, "emoji", { it.id }, { x, i -> x.copy(id = i) })
                .map { it.copy(name = it.name ?: "", content = it.content ?: "") },
            styles = fill(raw.styles, "style", { it.id }, { x, i -> x.copy(id = i) })
                .map { it.copy(name = it.name ?: "", category = it.category ?: "", html = it.html ?: "", updatedAt = it.updatedAt ?: "", type = it.type ?: "component", thumbnail = it.thumbnail ?: "", tags = it.tags ?: emptyList()) },
            articles = fill(raw.articles, "article", { it.id }, { x, i -> x.copy(id = i) })
                .map { it.copy(title = it.title ?: "", html = it.html ?: "", createdAt = it.createdAt ?: "", updatedAt = it.updatedAt ?: "", subtitle = it.subtitle ?: "", summary = it.summary ?: "", author = it.author ?: "", coverAssetId = it.coverAssetId ?: "", category = it.category ?: "", tags = it.tags ?: emptyList(), status = it.status ?: "draft", isFavorite = it.isFavorite) },
            styleSeedApplied = raw.styleSeedApplied,
            mediaAssets = fill<MediaAsset>(raw.mediaAssets, "media", { asset: MediaAsset -> asset.id }, { asset: MediaAsset, i -> asset.copy(id = i) })
                .map { asset: MediaAsset -> asset.copy(fileName = asset.fileName ?: "", mimeType = asset.mimeType ?: "", relativePath = asset.relativePath ?: "", createdAt = asset.createdAt ?: "") },
            articleRevisions = fill<ArticleRevision>(raw.articleRevisions, "revision", { revision: ArticleRevision -> revision.id }, { revision: ArticleRevision, i -> revision.copy(id = i) })
                .map { revision: ArticleRevision -> revision.copy(articleId = revision.articleId ?: "", title = revision.title ?: "", html = revision.html ?: "", createdAt = revision.createdAt ?: "", note = revision.note ?: "", subtitle = revision.subtitle ?: "", summary = revision.summary ?: "", author = revision.author ?: "", coverAssetId = revision.coverAssetId ?: "", category = revision.category ?: "", tags = revision.tags ?: emptyList(), status = revision.status ?: "draft", isFavorite = revision.isFavorite) },
            files = Files(''', "Store normalization")
if "styles = fill(raw.styles" not in p.read_text(encoding="utf-8"):
    fail("Style/article fields are not normalized")
replace_once(p,
'''        if (raw == null || data != loaded) saveData(data)
        return data''',
'''        val defaultStyle = StyleModule(
            id = "style_default_green_title",
            name = "清新绿标题",
            category = "标题组件",
            html = """<section style="margin:22px 0;padding:16px 18px;background:#f0faf4;border-left:4px solid #16a36a;border-radius:4px;"><p style="margin:0;color:#168653;font-size:20px;font-weight:700;line-height:1.5;">在这里输入标题</p><p style="margin:7px 0 0;color:#789487;font-size:12px;letter-spacing:1px;">A SIMPLE SECTION TITLE</p></section><p><br></p>""",
            updatedAt = "seed"
        )
        val migrated = if (!data.styleSeedApplied) {
            val styles = if (data.styles.any { it.id == defaultStyle.id }) data.styles else data.styles + defaultStyle
            data.copy(styles = styles, styleSeedApplied = true)
        } else data
        if (raw == null || migrated != loaded || migrated != data) saveData(migrated)
        return migrated''', "one-time default style migration")

# Recover from an interrupted save before falling back to seed data. A valid backup
# takes precedence whenever the primary file is absent or cannot be parsed.
replace_once(p,
'''    fun loadData(): AppData {
        val raw: AppData? = runCatching {
            if (dataFile.exists()) gson.fromJson(dataFile.readText(Charsets.UTF_8), AppData::class.java) else null
        }.getOrNull()''',
'''    fun loadData(): AppData {
        val backupFile = File(ctx.filesDir, "app_data.json.bak")
        val primaryRaw: AppData? = runCatching {
            if (dataFile.exists()) gson.fromJson(dataFile.readText(Charsets.UTF_8), AppData::class.java) else null
        }.getOrNull()
        val backupRaw: AppData? = if (primaryRaw == null && backupFile.exists()) {
            runCatching { gson.fromJson(backupFile.readText(Charsets.UTF_8), AppData::class.java) }.getOrNull()
        } else null
        if (primaryRaw == null && backupRaw != null) {
            runCatching { backupFile.copyTo(dataFile, overwrite = true) }
        }
        val raw: AppData? = primaryRaw ?: backupRaw''', "primary/backup data recovery")

# Make business-data writes fail visibly and avoid truncating the previous JSON on interrupted writes.
p = DATA / "Store.kt"
replace_once(p,
'''    fun saveData(d: AppData) {
        runCatching { dataFile.writeText(gson.toJson(d), Charsets.UTF_8) }
    }''',
'''    fun saveData(d: AppData): Boolean {
        val temp = File(ctx.filesDir, "app_data.json.tmp")
        val backup = File(ctx.filesDir, "app_data.json.bak")
        return try {
            java.io.FileOutputStream(temp).use { output ->
                output.write(gson.toJson(d).toByteArray(Charsets.UTF_8))
                output.fd.sync()
            }
            if (backup.exists()) backup.delete()
            val hadOriginal = dataFile.exists()
            if (hadOriginal && !dataFile.renameTo(backup)) throw java.io.IOException("无法备份原数据文件")
            if (!temp.renameTo(dataFile)) {
                if (hadOriginal && backup.exists()) backup.renameTo(dataFile)
                throw java.io.IOException("无法提交新数据文件")
            }
            if (backup.exists()) backup.delete()
            true
        } catch (error: Exception) {
            temp.delete()
            if (!dataFile.exists() && backup.exists()) backup.renameTo(dataFile)
            android.util.Log.e("ShiWanJuStore", "保存数据失败", error)
            false
        }
    }''', "atomic data persistence")

p = UI / "AppViewModel.kt"
replace_once(p,
'''    fun updateData(block: (AppData) -> AppData) {
        data = block(data)
        store.saveData(data)
        validateSelections()
        if (!ui.mediaInit) applyDefaultMediaOnce()
        rebuild()
    }''',
'''    fun updateData(block: (AppData) -> AppData): Boolean {
        val updated = block(data)
        if (!store.saveData(updated)) {
            toast("数据保存失败，原有数据未被覆盖，请检查设备存储空间后重试")
            return false
        }
        data = updated
        validateSelections()
        if (!ui.mediaInit) applyDefaultMediaOnce()
        rebuild()
        return true
    }''', "transactional data updates")

# Shared business actions.
p = UI / "AppViewModel.kt"
replace_once(p,
'''    fun saveEmoji(x: EmojiItem) = updateData { d ->''',
'''    fun saveStyle(x: StyleModule) = updateData { d ->
        val list = d.styles
        val i = list.indexOfFirst { it.id == x.id }
        d.copy(styles = if (i >= 0) list.toMutableList().also { it[i] = x } else list + x)
    }
    fun deleteStyle(id: String) = updateData { d -> d.copy(styles = d.styles.filterNot { it.id == id }) }
    fun renameStyleCategory(from: String, to: String) = updateData { d ->
        if (from.isBlank() || to.isBlank()) d else d.copy(styles = d.styles.map { if (it.category == from) it.copy(category = to) else it })
    }
    fun reorderStyle(from: Int, to: Int) = updateData { d ->
        val list = d.styles.toMutableList()
        if (from in list.indices && to in list.indices && from != to) { val item = list.removeAt(from); list.add(to, item) }
        d.copy(styles = list)
    }
    fun saveArticle(x: ArticleDocument) = updateData { d ->
        val list = d.articles
        val i = list.indexOfFirst { it.id == x.id }
        val previous = list.getOrNull(i)
        val changed = previous != null && (
            previous.html != x.html || previous.title != x.title || previous.subtitle != x.subtitle ||
            previous.summary != x.summary || previous.author != x.author || previous.coverAssetId != x.coverAssetId ||
            previous.category != x.category || previous.tags != x.tags || previous.status != x.status || previous.isFavorite != x.isFavorite
        )
        val nowMillis = System.currentTimeMillis()
        val now = nowMillis.toString()
        // Coalesce rapid autosaves: keep the earliest pre-edit state and create at most one snapshot per five-minute window.
        val lastRevisionAt = d.articleRevisions.asSequence()
            .filter { it.articleId == x.id }
            .mapNotNull { it.createdAt.toLongOrNull() }
            .maxOrNull()
        val shouldCreateRevision = changed && (lastRevisionAt == null || nowMillis - lastRevisionAt >= 5 * 60 * 1000L)
        val revisions = if (shouldCreateRevision) {
            val articleHistory = (d.articleRevisions.filter { it.articleId == x.id } + ArticleRevision(
                id = newId(), articleId = previous!!.id, title = previous.title, html = previous.html,
                createdAt = now, note = "自动保存快照", subtitle = previous.subtitle, summary = previous.summary,
                author = previous.author, coverAssetId = previous.coverAssetId, category = previous.category,
                tags = previous.tags, status = previous.status, isFavorite = previous.isFavorite
            )).takeLast(30)
            d.articleRevisions.filterNot { it.articleId == x.id } + articleHistory
        } else d.articleRevisions
        d.copy(
            articles = if (i >= 0) list.toMutableList().also { it[i] = x } else list + x,
            articleRevisions = revisions
        )
    }
    fun deleteArticle(id: String) = updateData { d ->
        d.copy(articles = d.articles.filterNot { it.id == id }, articleRevisions = d.articleRevisions.filterNot { it.articleId == id })
    }
    fun restoreArticleRevision(revision: ArticleRevision): Boolean = updateData { d ->
        val current = d.articles.firstOrNull { it.id == revision.articleId } ?: return@updateData d
        val sameAsRevision = current.title == revision.title && current.html == revision.html &&
            current.subtitle == revision.subtitle && current.summary == revision.summary &&
            current.author == revision.author && current.coverAssetId == revision.coverAssetId &&
            current.category == revision.category && current.tags == revision.tags &&
            current.status == revision.status && current.isFavorite == revision.isFavorite
        val now = System.currentTimeMillis().toString()
        val history = if (sameAsRevision) d.articleRevisions else {
            val snapshot = ArticleRevision(
                id = newId(), articleId = current.id, title = current.title, html = current.html,
                createdAt = now, note = "恢复前自动快照", subtitle = current.subtitle, summary = current.summary,
                author = current.author, coverAssetId = current.coverAssetId, category = current.category,
                tags = current.tags, status = current.status, isFavorite = current.isFavorite
            )
            val retained = (d.articleRevisions.filter { it.articleId == current.id } + snapshot).takeLast(30)
            d.articleRevisions.filterNot { it.articleId == current.id } + retained
        }
        val restored = current.copy(
            title = revision.title, html = revision.html, subtitle = revision.subtitle, summary = revision.summary,
            author = revision.author, coverAssetId = revision.coverAssetId, category = revision.category,
            tags = revision.tags, status = revision.status, isFavorite = revision.isFavorite, updatedAt = now
        )
        d.copy(
            articles = d.articles.map { if (it.id == current.id) restored else it },
            articleRevisions = history
        )
    }
    fun saveMediaAsset(asset: MediaAsset) = updateData { d ->
        val i = d.mediaAssets.indexOfFirst { it.id == asset.id }
        d.copy(mediaAssets = if (i >= 0) d.mediaAssets.toMutableList().also { it[i] = asset } else d.mediaAssets + asset)
    }
    fun deleteMediaAsset(id: String) = updateData { d ->
        // Keep assets referenced by live articles, article revisions (restore depends on them),
        // style HTML, and style thumbnails. A revision must remain restorable after editing.
        val usedByArticles = d.articles.any { it.html.contains(id) || it.coverAssetId == id }
        val usedByRevisions = d.articleRevisions.any { it.html.contains(id) || it.coverAssetId == id }
        val usedByStyles = d.styles.any { it.html.contains(id) || it.thumbnail == id }
        if (usedByArticles || usedByRevisions || usedByStyles) d
        else d.copy(mediaAssets = d.mediaAssets.filterNot { it.id == id })
    }

    fun saveEmoji(x: EmojiItem) = updateData { d ->''', "AppViewModel style/article actions")

# Generate collision-resistant IDs for rapid consecutive article/media creation.
replace_once(UI / "AppViewModel.kt",
'''    fun newId(): String = System.currentTimeMillis().toString()''',
'''    fun newId(): String = java.util.UUID.randomUUID().toString()''',
"collision-resistant editor IDs")

# Add the style manager route to My and a home-page entry.
p = UI / "MyScreens.kt"
s = p.read_text(encoding="utf-8")
s = s.replace('"texts" -> "文案"; "layouts" -> "版式";', '"texts" -> "文案"; "styles" -> "样式"; "layouts" -> "版式";', 1)
s = s.replace('''                "texts" -> TextsPage(vm)
                "layouts" -> LayoutsPage(vm)''',
'''                "texts" -> TextsPage(vm)
                "styles" -> StylesPage(vm)
                "layouts" -> LayoutsPage(vm)''', 1)
if 'HomeGroupRow("样式"' not in s:
    s = s.replace('''        HomeGroupRow("文章", "共 ${d.files.text.size} 个文案模块") { go("texts") }
        Spacer(Modifier.height(8.dp))
        HomeGroupRow("版式"''',
'''        HomeGroupRow("文章", "共 ${d.files.text.size} 个文案模块") { go("texts") }
        Spacer(Modifier.height(8.dp))
        HomeGroupRow("样式", "共 ${d.styles.size} 个样式模块") { go("styles") }
        Spacer(Modifier.height(8.dp))
        HomeGroupRow("版式"''', 1)

    anchor = "// ---------------------------------------------------------------------- 版式"
    if anchor not in s:
        fail("MyScreens layout section anchor missing")
    styles_code = '''
// ---------------------------------------------------------------------- 样式：与文案模块同样的列表 / 宫格 / 排序 / 新增编辑删除；分类由用户自定义。

@Composable
private fun StylesPage(vm: AppViewModel) = Page {
    var edit by remember { mutableStateOf<StyleModule?>(null) }
    var isNew by remember { mutableStateOf(false) }
    var grid by remember { mutableStateOf(false) }
    var sorting by remember { mutableStateOf(false) }
    var showCategoryManager by remember { mutableStateOf(false) }
    var categoryFrom by remember { mutableStateOf("") }
    var categoryTo by remember { mutableStateOf("") }
    var searchStyle by remember { mutableStateOf("") }
    val list = vm.data.styles.filter { searchStyle.isBlank() || it.name.contains(searchStyle, true) || it.category.contains(searchStyle, true) }
    val categories = vm.data.styles.map { it.category }.filter { it.isNotBlank() }.distinct()
    TopActions {
        ThemeChip(if (grid) "列表" else "宫格", false, dark = false) { grid = !grid }
        Spacer(Modifier.width(8.dp))
        ThemeChip("分类管理", false, dark = false) { categoryFrom = categories.firstOrNull().orEmpty(); categoryTo = ""; showCategoryManager = true }
        Spacer(Modifier.width(8.dp))
        ThemeChip(if (sorting) "完成" else "排序", sorting, dark = false) { sorting = !sorting }
        if (!sorting) { Spacer(Modifier.width(8.dp)); ThemeChip("+ 新建样式", true, dark = false) { edit = StyleModule(id = vm.newId(), category = "自定义分类"); isNew = true } }
    }
    OutlinedTextField(searchStyle, { searchStyle = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, placeholder = { Text("搜索样式名称或分类") })
    if (showCategoryManager) {
        AlertDialog(
            onDismissRequest = { showCategoryManager = false },
            title = { Text("样式分类管理") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("分类由样式模块关联。将旧分类名称改为新名称，即可批量迁移该分类下的所有样式。", color = AppColors.MyDim, fontSize = 12.sp)
                    OutlinedTextField(categoryFrom, { categoryFrom = it }, label = { Text("原分类名称") }, singleLine = true)
                    OutlinedTextField(categoryTo, { categoryTo = it }, label = { Text("新分类名称") }, singleLine = true)
                    Text("现有分类：${categories.joinToString("、").ifBlank { "暂无" }}", color = AppColors.MyDim, fontSize = 11.sp)
                }
            },
            confirmButton = {
                Row {
                    TextButton(onClick = {
                        if (categoryFrom.isBlank() || categoryTo.isBlank()) vm.toast("请填写原分类和新分类")
                        else { vm.renameStyleCategory(categoryFrom.trim(), categoryTo.trim()); showCategoryManager = false; vm.toast("分类及关联样式已迁移") }
                    }) { Text("迁移/重命名") }
                    TextButton(onClick = {
                        if (categoryFrom.isBlank()) vm.toast("请先填写要删除的分类")
                        else if (categoryFrom.trim() == "未分类") vm.toast("默认分类「未分类」不能删除")
                        else { vm.renameStyleCategory(categoryFrom.trim(), "未分类"); showCategoryManager = false; vm.toast("分类已删除，关联样式已迁移到未分类") }
                    }) { Text("删除并迁移") }
                }
            },
            dismissButton = { TextButton(onClick = { showCategoryManager = false }) { Text("取消") } }
        )
    }
    Text("分类名称由你自己填写；编辑器会将这些分类显示为可插入的样式功能项。", color = AppColors.MyDim, fontSize = 12.sp)
    if (list.isEmpty()) Empty("暂无样式模块，请点击右上角新建")
    if (sorting) {
        list.forEachIndexed { index, item ->
            Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(AppColors.MyCard).padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(item.name, color = AppColors.MyText, fontSize = 14.sp, fontWeight = FontWeight.Medium)
                    Text("【${item.category}】" + summarize(item.html, 34), color = AppColors.MyDim, fontSize = 11.sp, maxLines = 1)
                }
                TextButton(enabled = index > 0, onClick = { vm.reorderStyle(index, index - 1) }) { Text("↑") }
                TextButton(enabled = index < list.lastIndex, onClick = { vm.reorderStyle(index, index + 1) }) { Text("↓") }
            }
        }
    } else if (grid) {
        list.chunked(3).forEach { row ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                row.forEach { item ->
                    Column(Modifier.weight(1f).heightIn(min = 76.dp).clip(RoundedCornerShape(11.dp)).background(AppColors.MyCard)
                        .clickable { edit = item; isNew = false }.padding(10.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        Text(item.name, color = AppColors.MyText, fontSize = 12.sp, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        Text(item.category, color = AppColors.MyDim, fontSize = 10.sp, maxLines = 1, modifier = Modifier.padding(top = 5.dp))
                    }
                }
                repeat(3 - row.size) { Spacer(Modifier.weight(1f)) }
            }
        }
    } else list.forEach { item ->
        ListRow(item.name, "【${item.category}】" + summarize(item.html, 48)) { edit = item; isNew = false }
    }

    edit?.let { item ->
        var name by remember(item.id) { mutableStateOf(item.name) }
        var category by remember(item.id) { mutableStateOf(item.category) }
        var html by remember(item.id) { mutableStateOf(item.html) }
        var confirm by remember { mutableStateOf(false) }
        EditDialog(if (isNew) "新增样式" else "样式详情与编辑", { edit = null }, {
            vm.saveStyle(item.copy(name = name.ifBlank { "未命名样式" }, category = category.trim().ifBlank { "未分类" }, html = html,
                updatedAt = System.currentTimeMillis().toString()))
            edit = null
        }, if (isNew) null else ({ confirm = true })) {
            Field("样式名称", name, { name = it })
            Field("自定义分类名称", category, { category = it }, hint = "例如：标题组件、图文卡片、引导关注")
            Field("样式 HTML 片段", html, { html = it }, 8, "编辑器中点击该样式时，会将这段 HTML 插入光标位置")
            Text("建议使用内联 CSS，避免公众号编辑器清理样式后出现错位。", color = AppColors.MyDim, fontSize = 11.sp)
        }
        if (confirm) ConfirmDelete("样式模块", { vm.deleteStyle(item.id); confirm = false; edit = null }, { confirm = false })
    }
}

'''
    s = s.replace(anchor, styles_code + anchor, 1)
p.write_text(s, encoding="utf-8")

# Add a palette entry immediately to the RIGHT of Edit in the layout toolbar.
p = UI / "LayoutScreen.kt"
s = p.read_text(encoding="utf-8")
if 'contentDescription = "秀米式文章排版"' not in s:
    s = s.replace('import androidx.compose.material.icons.outlined.Refresh',
                  'import androidx.compose.material.icons.outlined.Refresh\\nimport androidx.compose.material.icons.outlined.Palette', 1)
    old = '''        ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing) { vm.toggleEditing() }'''
    new = '''        ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing) { vm.toggleEditing() }
        IconButton(onClick = { vm.screen = "article_editor" }, modifier = Modifier.size(38.dp)) {
            Icon(Icons.Outlined.Palette, contentDescription = "秀米式文章排版", tint = AppColors.TextMain, modifier = Modifier.size(21.dp))
        }'''
    if old not in s:
        fail("Layout top bar edit button anchor missing")
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# Route the new page from the activity. Do not infer routing from imports or comments.
p = JAVA / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
if "import com.shiwanju.app.ui.XiumiArticleLayoutScreen" not in s:
    s = s.replace("import com.shiwanju.app.ui.LayoutScreen",
                  "import com.shiwanju.app.ui.LayoutScreen\nimport com.shiwanju.app.ui.XiumiArticleLayoutScreen", 1)

route = '''when (vm.screen) {
                          "article_editor" -> XiumiArticleLayoutScreen(vm) { vm.screen = "layout" }
                          "layout" -> LayoutScreen(vm)
                          else -> MyScreen(vm)
                      }'''
if '"article_editor" -> XiumiArticleLayoutScreen(vm)' not in s:
    pattern = re.compile(r'if\s*\(vm\.screen\s*==\s*"layout"\)\s*LayoutScreen\(vm\)\s*else\s*MyScreen\(vm\)')
    match = pattern.search(s)
    if match:
        s = s[:match.start()] + route + s[match.end():]
    else:
        # Also support a previous when-expression that omitted the editor branch.
        pattern = re.compile(r'when\s*\(vm\.screen\)\s*\{[^}]*"layout"\s*->\s*LayoutScreen\(vm\)[^}]*else\s*->\s*MyScreen\(vm\)[^}]*\}', re.S)
        match = pattern.search(s)
        if match:
            s = s[:match.start()] + route + s[match.end():]
        else:
            fail("Cannot locate MainActivity screen dispatcher; refusing to ship a dead editor button.")
p.write_text(s, encoding="utf-8")

# Compile-time contract checks.
checks = [
    (DATA / "Models.kt", "val styles: List<StyleModule>"),
    (DATA / "Models.kt", "val articles: List<ArticleDocument>"),
    (DATA / "Models.kt", "val styleSeedApplied: Boolean"),
    (DATA / "Models.kt", "val mediaAssets: List<MediaAsset>"),
    (DATA / "Models.kt", "val articleRevisions: List<ArticleRevision>"),
    (DATA / "Models.kt", "val isFavorite: Boolean = false"),
    (DATA / "Store.kt", "styles = fill(raw.styles"),
    (DATA / "Store.kt", "mediaAssets = fill<MediaAsset>"),
    (DATA / "Store.kt", "articleRevisions = fill<ArticleRevision>"),
    (DATA / "Store.kt", "styleSeedApplied = raw.styleSeedApplied"),
    (DATA / "Store.kt", "fun saveData(d: AppData): Boolean"),
    (DATA / "Store.kt", "output.fd.sync()"),
    (DATA / "Store.kt", "val backupRaw: AppData?"),
    (DATA / "Store.kt", "backupFile.copyTo(dataFile, overwrite = true)"),
    (UI / "AppViewModel.kt", "if (!store.saveData(updated))"),
    (UI / "AppViewModel.kt", "fun updateData(block: (AppData) -> AppData): Boolean"),
    (UI / "AppViewModel.kt", "note = \"恢复前自动快照\""),
    (UI / "AppViewModel.kt", "fun restoreArticleRevision(revision: ArticleRevision): Boolean"),
    (UI / "AppViewModel.kt", "return true"),
    (UI / "AppViewModel.kt", "fun saveArticle("),
    (UI / "AppViewModel.kt", "fun deleteArticle("),
    (UI / "AppViewModel.kt", "fun saveMediaAsset("),
    (UI / "AppViewModel.kt", "previous.coverAssetId != x.coverAssetId"),
    (UI / "AppViewModel.kt", "previous.isFavorite != x.isFavorite"),
    (UI / "AppViewModel.kt", "d.articleRevisions.any { it.html.contains(id) || it.coverAssetId == id }"),
    (UI / "AppViewModel.kt", "d.styles.any { it.html.contains(id) || it.thumbnail == id }"),
    (UI / "AppViewModel.kt", "java.util.UUID.randomUUID().toString()"),
    (UI / "AppViewModel.kt", "revision.subtitle"),
    (UI / "MyScreens.kt", "private fun StylesPage("),
    (UI / "LayoutScreen.kt", 'contentDescription = "文章编辑器"'),
    (UI / "ArticleEditorScreen.kt", "rememberLauncherForActivityResult"),
    (UI / "ArticleEditorScreen.kt", "copyRichHtml"),
    (UI / "ArticleEditorScreen.kt", "articleJsonImporter"),
    (UI / "ArticleEditorScreen.kt", "showHtmlImportPreview"),
    (UI / "ArticleEditorScreen.kt", "markdownImporter"),
    (UI / "ArticleEditorScreen.kt", "markdownToArticleHtml"),
    (UI / "ArticleEditorScreen.kt", "imageGroupPicker"),
    (UI / "ArticleEditorScreen.kt", "articleHtmlToMarkdown"),
    (UI / "ArticleEditorScreen.kt", "articleCompatibilityWarnings"),
    (UI / "ArticleEditorScreen.kt", "function duplicateSelectedBlock"),
    (UI / "ArticleEditorScreen.kt", "function replaceSelectedBlockWithHtml"),
    (UI / "ArticleEditorScreen.kt", "function setMultiSelectMode"),
    (UI / "ArticleEditorScreen.kt", "function undoEditor"),
    (UI / "ArticleEditorScreen.kt", "function cropSelectedImage"),
    (UI / "ArticleEditorScreen.kt", "function setSelectedImageObjectPosition"),
    (UI / "ArticleEditorScreen.kt", "fun cropSelectedImagePixels"),
    (UI / "ArticleEditorScreen.kt", "private fun cropArticleImageFile"),
    (UI / "ArticleEditorScreen.kt", "function replaceSelectedImage"),
    (UI / "ArticleEditorScreen.kt", "function deleteSelectedImage"),
    (UI / "ArticleEditorScreen.kt", "function moveSelectedImageInGroup"),
    (UI / "ArticleEditorScreen.kt", "root.addEventListener('paste'"),
    (UI / "ArticleEditorScreen.kt", "function setSelectionFontSize"),
    (UI / "ArticleEditorScreen.kt", "copyTextFormat"),
    (UI / "ArticleEditorScreen.kt", "previewAsset"),
    (UI / "ArticleEditorScreen.kt", "mediaSearchText"),
    (UI / "ArticleEditorScreen.kt", "articleFilter == \"收藏\""),
    (UI / "ArticleEditorScreen.kt", "savingIsFavorite"),
    (UI / "ArticleEditorScreen.kt", "formatArticleTimestamp"),
    (UI / "ArticleEditorScreen.kt", "revisionPreview"),
    (UI / "ArticleEditorScreen.kt", "import com.shiwanju.app.data.ArticleRevision"),
    (UI / "ArticleEditorScreen.kt", "filteredTemplates"),
    (UI / "ArticleEditorScreen.kt", "templatePreview"),
    (UI / "ArticleEditorScreen.kt", "stylePackageImporter"),
    (UI / "ArticleEditorScreen.kt", "shiwanju.styles.v1"),
    (UI / "ArticleEditorScreen.kt", "multiSelectMode"),
    (UI / "ArticleEditorScreen.kt", "fullTemplateConfirm"),
    (UI / "ArticleEditorScreen.kt", "fun XiumiArticleLayoutScreen(vm: AppViewModel, onBack: () -> Unit)"),
    (JAVA / "MainActivity.kt", '"article_editor" -> XiumiArticleLayoutScreen(vm)')
]
for path, token in checks:
    if token not in path.read_text(encoding="utf-8"):
        fail("Article editor wiring check failed: " + str(path) + " :: " + token)
print("Article editor data, style manager, editor route and layout entry wired.")
