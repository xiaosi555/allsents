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
    val updatedAt: String = ""
)

data class ArticleDocument(
    val id: String = "",
    val title: String = "",
    val html: String = "",
    val createdAt: String = "",
    val updatedAt: String = ""
)''', "style and article data classes")
replace_once(p,
'''    val emoji: List<EmojiItem> = emptyList(),
    val files: Files = Files(),''',
'''    val emoji: List<EmojiItem> = emptyList(),
    val styles: List<StyleModule> = emptyList(),
    val articles: List<ArticleDocument> = emptyList(),
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
                .map { it.copy(name = it.name ?: "", category = it.category ?: "", html = it.html ?: "", updatedAt = it.updatedAt ?: "") },
            articles = fill(raw.articles, "article", { it.id }, { x, i -> x.copy(id = i) })
                .map { it.copy(title = it.title ?: "", html = it.html ?: "", createdAt = it.createdAt ?: "", updatedAt = it.updatedAt ?: "") },
            files = Files(''', "Store normalization")
if "styles = fill(raw.styles" not in p.read_text(encoding="utf-8"):
    fail("Style/article fields are not normalized")

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
    fun reorderStyle(from: Int, to: Int) = updateData { d ->
        val list = d.styles.toMutableList()
        if (from in list.indices && to in list.indices && from != to) { val item = list.removeAt(from); list.add(to, item) }
        d.copy(styles = list)
    }
    fun saveArticle(x: ArticleDocument) = updateData { d ->
        val list = d.articles
        val i = list.indexOfFirst { it.id == x.id }
        d.copy(articles = if (i >= 0) list.toMutableList().also { it[i] = x } else list + x)
    }

    fun saveEmoji(x: EmojiItem) = updateData { d ->''', "AppViewModel style/article actions")

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
    val list = vm.data.styles
    TopActions {
        ThemeChip(if (grid) "列表" else "宫格", false, dark = false) { grid = !grid }
        Spacer(Modifier.width(8.dp))
        ThemeChip(if (sorting) "完成" else "排序", sorting, dark = false) { sorting = !sorting }
        if (!sorting) { Spacer(Modifier.width(8.dp)); ThemeChip("+ 新建样式", true, dark = false) { edit = StyleModule(id = vm.newId(), category = "自定义分类"); isNew = true } }
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

# Add a compact icon-only entry beside Edit in the layout toolbar.
p = UI / "LayoutScreen.kt"
s = p.read_text(encoding="utf-8")
if 'contentDescription = "文章编辑器"' not in s:
    s = s.replace('import androidx.compose.material.icons.outlined.Refresh',
                  'import androidx.compose.material.icons.outlined.Refresh\nimport androidx.compose.material.icons.outlined.Article', 1)
    old = '''        ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing) { vm.toggleEditing() }'''
    new = '''        ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing) { vm.toggleEditing() }
        IconButton(onClick = { vm.screen = "article_editor" }, modifier = Modifier.size(38.dp)) {
            Icon(Icons.Outlined.Article, contentDescription = "文章编辑器", tint = AppColors.TextMain, modifier = Modifier.size(21.dp))
        }'''
    if old not in s:
        fail("Layout top bar edit button anchor missing")
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# Route the new page from the activity; preserve existing screen routes.
p = JAVA / "MainActivity.kt"
s = p.read_text(encoding="utf-8")
if 'ArticleEditorScreen(vm)' not in s:
    s = s.replace('import com.shiwanju.app.ui.LayoutScreen',
                  'import com.shiwanju.app.ui.LayoutScreen\nimport com.shiwanju.app.ui.ArticleEditorScreen', 1)
    old = '''                      if (vm.screen == "layout") LayoutScreen(vm) else MyScreen(vm)'''
    new = '''                      when (vm.screen) {
                          "article_editor" -> ArticleEditorScreen(vm) { vm.screen = "layout" }
                          "layout" -> LayoutScreen(vm)
                          else -> MyScreen(vm)
                      }'''
    if old not in s:
        fail("MainActivity screen routing anchor missing")
    s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# Compile-time contract checks.
checks = [
    (DATA / "Models.kt", "val styles: List<StyleModule>"),
    (DATA / "Models.kt", "val articles: List<ArticleDocument>"),
    (DATA / "Store.kt", "styles = fill(raw.styles"),
    (UI / "AppViewModel.kt", "fun saveArticle("),
    (UI / "MyScreens.kt", "private fun StylesPage("),
    (UI / "LayoutScreen.kt", 'contentDescription = "文章编辑器"'),
    (JAVA / "MainActivity.kt", "ArticleEditorScreen(vm)")
]
for path, token in checks:
    if token not in path.read_text(encoding="utf-8"):
        fail("Article editor wiring check failed: " + str(path) + " :: " + token)
print("Article editor data, style manager, editor route and layout entry wired.")
