#!/usr/bin/env python3
from pathlib import Path
import uuid
root = Path(__file__).resolve().parents[1]
java = root / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"

def patch(rel, pairs):
    p = java / rel
    s = p.read_text(encoding="utf-8")
    for item in pairs:
        if len(item) == 2:
            old, new = item
            label = old[:80].replace(chr(10), ' ')
        else:
            old, new, label = item
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"{rel}: {label}: expected one anchor, found {n}")
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")

patch("data/Models.kt", [
("""data class StyleModule(
    val id: String = "",
    val name: String = "",
    val category: String = "",
    val html: String = "",
    val updatedAt: String = "",
    val isFavorite: Boolean = false,
    val type: String = "component",
    val thumbnail: String = "",
    val tags: List<String> = emptyList()
)""",
"""data class StyleCategory(val id: String = "", val name: String = "", val sortOrder: Int = 0, val createdAt: String = "")

data class StyleModule(
    val id: String = "",
    val name: String = "",
    val category: String = "",
    val html: String = "",
    val updatedAt: String = "",
    val isFavorite: Boolean = false,
    val type: String = "component",
    val thumbnail: String = "",
    val tags: List<String> = emptyList(),
    val categoryId: String = "",
    val origin: String = "user"
)""", "StyleModule categoryId/origin"),
("""    val styles: List<StyleModule> = emptyList(),
    val articles: List<ArticleDocument> = emptyList(),""",
"""    val styles: List<StyleModule> = emptyList(),
    val styleCategories: List<StyleCategory> = emptyList(),
    val articles: List<ArticleDocument> = emptyList(),""", "AppData styleCategories")
])

patch("data/Store.kt", [
("import java.io.File", "import java.io.File\nimport java.util.UUID", "UUID import"),
("""        val defaultStyle = StyleModule(
            id = "style_default_green_title",
            name = "清新绿标题",
            category = "标题组件",""",
"""        val defaultCategory = data.styleCategories.firstOrNull { it.name == "标题组件" }
            ?: StyleCategory(id = "stylecat_builtin_titles", name = "标题组件", sortOrder = data.styleCategories.size)
        val defaultStyle = StyleModule(
            id = "style_default_green_title",
            name = "清新绿标题",
            category = defaultCategory.name,
            categoryId = defaultCategory.id,
            origin = "official",""", "built-in official style"),
('''        val migrated = if (!data.styleSeedApplied) {
            val styles = if (data.styles.any { it.id == defaultStyle.id }) data.styles else data.styles + defaultStyle
            data.copy(styles = styles, styleSeedApplied = true)
        } else data''',
'''        val builtInCategories = listOf(
            defaultCategory,
            StyleCategory("stylecat_builtin_quotes", "引用组件", 1, "seed"),
            StyleCategory("stylecat_builtin_dividers", "分隔组件", 2, "seed"),
            StyleCategory("stylecat_builtin_full", "整篇模板", 3, "seed")
        )
        val builtInStyles = listOf(
            defaultStyle,
            StyleModule(
                id = "style_official_quote_warm", name = "暖色引言卡", category = "引用组件",
                html = """<section style="margin:18px 0;padding:18px 20px;background:#fff8ef;border-radius:8px;border-left:4px solid #d69a55;"><p style="margin:0;color:#8a6238;font-size:15px;line-height:1.9;">在这里放入值得停留的句子。</p><p style="margin:10px 0 0;color:#b28c65;font-size:11px;text-align:right;">—— 引言 / 出处</p></section>""",
                updatedAt = "seed", type = "component", tags = listOf("引用", "暖色", "金句"),
                categoryId = "stylecat_builtin_quotes", origin = "official"
            ),
            StyleModule(
                id = "style_official_divider_dots", name = "轻点分隔线", category = "分隔组件",
                html = """<div style="margin:26px auto;text-align:center;color:#b7c7bc;font-size:13px;letter-spacing:8px;">· · ·</div>""",
                updatedAt = "seed", type = "component", tags = listOf("分隔", "极简"),
                categoryId = "stylecat_builtin_dividers", origin = "official"
            ),
            StyleModule(
                id = "style_official_full_minimal", name = "清爽图文长文", category = "整篇模板",
                html = """<article style="margin:0 auto;max-width:100%;color:#333;font-family:Arial,'Microsoft YaHei',sans-serif;line-height:1.9;"><header style="padding:26px 0 20px;border-bottom:1px solid #e8eee9;"><p style="margin:0 0 10px;color:#4a9b72;font-size:12px;letter-spacing:2px;">NOTES · ARTICLE</p><h1 style="margin:0;color:#25372d;font-size:26px;line-height:1.45;font-weight:700;">在这里填写文章标题</h1><p style="margin:10px 0 0;color:#89948d;font-size:13px;">副标题或一句简短说明</p></header><section style="padding:22px 0;"><p style="margin:0 0 18px;color:#68766e;font-size:15px;">在这里填写文章导语，简要介绍文章主题。</p><h2 style="margin:26px 0 12px;color:#31845b;font-size:19px;">一、章节标题</h2><p style="margin:0 0 16px;font-size:15px;">在这里填写正文内容。可继续使用编辑器添加段落、图片、引用和其他组件。</p><blockquote style="margin:22px 0;padding:12px 16px;background:#f4f8f5;border-left:3px solid #70ad88;color:#607568;">在这里填写重点句子或引用内容。</blockquote><h2 style="margin:26px 0 12px;color:#31845b;font-size:19px;">二、继续展开</h2><p style="margin:0 0 16px;font-size:15px;">在这里继续填写正文内容。</p><p style="margin:28px 0 0;padding-top:14px;border-top:1px solid #e8eee9;color:#9aa39d;font-size:12px;text-align:center;">— END —</p></section></article>""",
                updatedAt = "seed", type = "full", tags = listOf("极简", "图文", "长文"),
                categoryId = "stylecat_builtin_full", origin = "official"
            )
        )
        val styles = data.styles + builtInStyles.filterNot { builtin -> data.styles.any { it.id == builtin.id } }
        val categories = data.styleCategories + builtInCategories.filterNot { builtin -> data.styleCategories.any { it.id == builtin.id } }
        val migrated = data.copy(styles = styles, styleCategories = categories, styleSeedApplied = true)''', "merge official template catalog on every migration")
])

store = java / "data/Store.kt"
s = store.read_text(encoding="utf-8")
a = """        val files = raw.files ?: Files()
        var layout = fill(raw.layout, "layout", { it.id }, { x, i -> x.copy(id = i) })"""
b = """        val files = raw.files ?: Files()
        val styleBase = fill(raw.styles, "style", { it.id }, { x, i -> x.copy(id = i) })
            .map { it.copy(name = it.name ?: "", category = it.category ?: "", html = it.html ?: "", updatedAt = it.updatedAt ?: "", type = it.type ?: "component", thumbnail = it.thumbnail ?: "", tags = it.tags ?: emptyList(), categoryId = it.categoryId ?: "", origin = if (it.id == "style_default_green_title" || it.origin == "official") "official" else "user") }
        val styleCategories = fill(raw.styleCategories, "stylecat", { it.id }, { x, i -> x.copy(id = i) })
            .map { it.copy(name = (it.name ?: "").trim().ifBlank { "未分类" }, createdAt = it.createdAt ?: "") }
            .distinctBy { it.name.lowercase(java.util.Locale.ROOT) }.toMutableList()
        styleBase.forEach { style ->
            val name = style.category.trim().ifBlank { "未分类" }
            if (styleCategories.none { (style.categoryId.isNotBlank() && it.id == style.categoryId) || it.name.equals(name, true) }) {
                val stableId = UUID.nameUUIDFromBytes(("shiwanju-style-category:" + name.lowercase(java.util.Locale.ROOT)).toByteArray(Charsets.UTF_8)).toString()
                styleCategories.add(StyleCategory(id = stableId, name = name, sortOrder = styleCategories.size))
            }
        }
        val normalizedStyles = styleBase.map { style ->
            val name = style.category.trim().ifBlank { "未分类" }
            val cat = styleCategories.firstOrNull { style.categoryId.isNotBlank() && it.id == style.categoryId }
                ?: styleCategories.firstOrNull { it.name.equals(name, true) }
            style.copy(category = cat?.name ?: name, categoryId = cat?.id.orEmpty())
        }
        var layout = fill(raw.layout, "layout", { it.id }, { x, i -> x.copy(id = i) })"""
if s.count(a) != 1: raise SystemExit("Store.kt: category normalization anchor mismatch")
s = s.replace(a, b, 1)
a = """            styles = fill(raw.styles, "style", { it.id }, { x, i -> x.copy(id = i) })
                .map { it.copy(name = it.name ?: "", category = it.category ?: "", html = it.html ?: "", updatedAt = it.updatedAt ?: "", type = it.type ?: "component", thumbnail = it.thumbnail ?: "", tags = it.tags ?: emptyList()) },
            articles = fill(raw.articles, "article", { it.id }, { x, i -> x.copy(id = i) })"""
b = """            styles = normalizedStyles,
            styleCategories = styleCategories,
            articles = fill(raw.articles, "article", { it.id }, { x, i -> x.copy(id = i) })"""
if s.count(a) != 1: raise SystemExit("Store.kt: styles assignment anchor mismatch")
s = s.replace(a, b, 1)
store.write_text(s, encoding="utf-8")

patch("ui/AppViewModel.kt", [
("""    fun saveStyle(x: StyleModule) = updateData { d ->
        val list = d.styles
        val i = list.indexOfFirst { it.id == x.id }
        d.copy(styles = if (i >= 0) list.toMutableList().also { it[i] = x } else list + x)
    }
    fun deleteStyle(id: String) = updateData { d -> d.copy(styles = d.styles.filterNot { it.id == id }) }
    fun renameStyleCategory(from: String, to: String) = updateData { d ->
        if (from.isBlank() || to.isBlank()) d else d.copy(styles = d.styles.map { if (it.category == from) it.copy(category = to) else it })
    }
    fun reorderStyle(from: Int, to: Int) = updateData { d ->""",
"""    fun createStyleCategory(name: String): String {
        val clean = name.trim()
        if (clean.isBlank()) return ""
        val old = data.styleCategories.firstOrNull { it.name.equals(clean, true) }
        if (old != null) return old.id
        val id = newId()
        updateData { d -> d.copy(styleCategories = d.styleCategories + StyleCategory(id, clean, (d.styleCategories.maxOfOrNull { it.sortOrder } ?: -1) + 1, System.currentTimeMillis().toString())) }
        return id
    }
    fun saveStyle(x: StyleModule) = updateData { d ->
        val name = x.category.trim().ifBlank { "未分类" }
        val cat = d.styleCategories.firstOrNull { it.name.equals(name, true) }
            ?: d.styleCategories.firstOrNull { x.categoryId.isNotBlank() && it.id == x.categoryId }
            ?: StyleCategory(newId(), name, (d.styleCategories.maxOfOrNull { it.sortOrder } ?: -1) + 1, System.currentTimeMillis().toString())
        val categories = if (d.styleCategories.any { it.id == cat.id }) d.styleCategories else d.styleCategories + cat
        val i = d.styles.indexOfFirst { it.id == x.id }
        val old = d.styles.getOrNull(i)
        val saved = x.copy(category = cat.name, categoryId = cat.id, origin = old?.origin ?: if (x.id == "style_default_green_title") "official" else "user")
        d.copy(styleCategories = categories, styles = if (i >= 0) d.styles.toMutableList().also { it[i] = saved } else d.styles + saved)
    }
    fun deleteStyle(id: String) = updateData { d -> d.copy(styles = d.styles.filterNot { it.id == id }) }
    fun renameStyleCategory(from: String, to: String) = updateData { d ->
        val sourceName = from.trim(); val targetName = to.trim()
        if (sourceName.isBlank() || targetName.isBlank()) d else {
            val source = d.styleCategories.firstOrNull { it.name.equals(sourceName, true) }
            val target = d.styleCategories.firstOrNull { it.name.equals(targetName, true) && it.id != source?.id }
            val destination = target ?: source?.copy(name = targetName) ?: StyleCategory(newId(), targetName, d.styleCategories.size)
            val categories = d.styleCategories.filterNot { source != null && target != null && it.id == source.id }
                .map { if (source != null && target == null && it.id == source.id) destination else it }
                .let { list -> if (source == null && list.none { it.id == destination.id }) list + destination else list }
            d.copy(styleCategories = categories, styles = d.styles.map { style ->
                if ((source != null && style.categoryId == source.id) || (source == null && style.category.equals(sourceName, true)))
                    style.copy(category = destination.name, categoryId = destination.id) else style
            })
        }
    }
    fun reorderStyleCategory(from: Int, to: Int) = updateData { d ->
        val list = d.styleCategories.sortedBy { it.sortOrder }.toMutableList()
        if (from in list.indices && to in list.indices && from != to) { val item = list.removeAt(from); list.add(to, item) }
        d.copy(styleCategories = list.mapIndexed { index, item -> item.copy(sortOrder = index) })
    }
    fun reorderStyle(from: Int, to: Int) = updateData { d ->""", "style category CRUD")
])

patch("ui/MyScreens.kt", [
("""    val categories = vm.data.styles.map { it.category }.filter { it.isNotBlank() }.distinct()""",
"""    val categories = vm.data.styleCategories.sortedBy { it.sortOrder }.map { it.name }""", "persistent category list"),
("""                        if (categoryFrom.isBlank() || categoryTo.isBlank()) vm.toast("请填写原分类和新分类")
                        else { vm.renameStyleCategory(categoryFrom.trim(), categoryTo.trim()); showCategoryManager = false; vm.toast("分类及关联样式已迁移") }""",
"""                        if (categoryTo.isBlank()) vm.toast("请填写分类名称")
                        else if (categoryFrom.isBlank()) { vm.createStyleCategory(categoryTo.trim()); showCategoryManager = false; vm.toast("分类已创建") }
                        else { vm.renameStyleCategory(categoryFrom.trim(), categoryTo.trim()); showCategoryManager = false; vm.toast("分类及关联样式已迁移") }""", "create category action"),
("""                    OutlinedTextField(categoryTo, { categoryTo = it }, label = { Text("新分类名称") }, singleLine = true)
                    Text("现有分类：""",
"""                    OutlinedTextField(categoryTo, { categoryTo = it }, label = { Text("新分类名称") }, singleLine = true)
                    categories.forEachIndexed { index, name ->
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            TextButton(onClick = { categoryFrom = name }, modifier = Modifier.weight(1f)) { Text(name, color = if (categoryFrom == name) AppColors.Theme else AppColors.MyText) }
                            TextButton(enabled = index > 0, onClick = { vm.reorderStyleCategory(index, index - 1) }) { Text("↑") }
                            TextButton(enabled = index < categories.lastIndex, onClick = { vm.reorderStyleCategory(index, index + 1) }) { Text("↓") }
                        }
                    }
                    Text("现有分类：""", "category selection and ordering")
])

patch("ui/ArticleEditorScreen.kt", [
("""    var templateSearchText by remember { mutableStateOf("") }
    var templateLibraryTab by remember { mutableStateOf("full") }""",
"""    var templateSearchText by remember { mutableStateOf("") }
    var templateLibraryOrigin by remember { mutableStateOf("mine") }
    var templateLibraryTab by remember { mutableStateOf("full") }""", "template origin state"),
("""    val categories = vm.data.styles.map { it.category.trim() }.filter { it.isNotEmpty() }.distinct()
    val categoryStyles = vm.data.styles.filter { it.category == activeCategory }""",
"""    val categories = vm.data.styleCategories.sortedBy { it.sortOrder }.map { it.name }
    val selectedStyleCategory = vm.data.styleCategories.firstOrNull { it.name == activeCategory }
    val categoryStyles = vm.data.styles.filter { if (selectedStyleCategory != null) it.categoryId == selectedStyleCategory.id else it.category == activeCategory }""", "editor category IDs"),
("""    val templateLibraryItems = vm.data.styles.filter { style ->
        when (templateLibraryTab) {""",
"""    val templateLibraryItems = vm.data.styles.filter { style ->
        style.origin == templateLibraryOrigin && when (templateLibraryTab) {""", "official/user filtering"),
("""                    Text("我的模板库", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 8.dp, bottom = 5.dp))
                    FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        EditorTool("官方模板", templateLibraryOrigin == "official") { templateLibraryOrigin = "official"; templateLibraryTab = "component"; templateTagFilter = "" }
                        EditorTool("我的模板", templateLibraryOrigin == "mine") { templateLibraryOrigin = "mine"; templateLibraryTab = "full"; templateTagFilter = "" }
                    }
                    FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        EditorTool("整篇模板", templateLibraryTab == "full")""", "official/user tabs"),
("""                                    .put("thumbnail", style.thumbnail).put("tags", org.json.JSONArray(style.tags)))""",
"""                                    .put("thumbnail", style.thumbnail).put("tags", org.json.JSONArray(style.tags)).put("origin", style.origin))""", "template package origin export"),
("""                        isFavorite = row.optBoolean("isFavorite", false), type = type, thumbnail = idMap[row.optString("thumbnail")] ?: row.optString("thumbnail").take(200), tags = safeTags""",
"""                        isFavorite = row.optBoolean("isFavorite", false), type = type, thumbnail = idMap[row.optString("thumbnail")] ?: row.optString("thumbnail").take(200), tags = safeTags, origin = "user" """, "imported templates stay user-owned"),
("""                            FlowRow(Modifier.fillMaxWidth().padding(top = 7.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                categoryStyles.forEach { style -> EditorTool(style.name) { insert(style.html) } }
                            }""",
"""                            FlowRow(Modifier.fillMaxWidth().padding(top = 7.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                categoryStyles.forEach { style -> EditorTool(style.name) { insert(style.html) } }
                            }
                            if (categoryStyles.isEmpty()) Text("该分类暂时没有组件，可在「我的 - 样式」中添加", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 5.dp))""", "empty category state")
])

print("Style category IDs, legacy migration, official/user separation and category ordering applied.")
