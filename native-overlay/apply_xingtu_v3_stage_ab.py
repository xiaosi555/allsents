#!/usr/bin/env python3
"""Apply 醒图 3.0 Stage A (article/session context) and Stage B (8-category dock)."""
from pathlib import Path
import re

ROOT = Path(".")
JAVA = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
V3 = JAVA / "ui/v3/ArticleEditorScreenV3.kt"
MAIN = JAVA / "MainActivity.kt"

def fail(message):
    raise SystemExit("醒图 3.0 Stage A/B: " + message)

def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)

def matching_brace(source, opening):
    depth = 0
    quote = None
    escaped = False
    for index in range(opening, len(source)):
        ch = source[index]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    fail("unable to locate balanced Kotlin block")
    
if not V3.is_file() or not MAIN.is_file():
    fail("generated V3 editor or MainActivity is missing")

s = V3.read_text(encoding="utf-8")

# Stage A1: allow an explicit article ID to be passed through the route.
s = replace_once(
    s,
    "fun ArticleEditorScreenV3(vm: AppViewModel, onBack: () -> Unit) {",
    "fun ArticleEditorScreenV3(vm: AppViewModel, onBack: () -> Unit, initialArticleId: String? = null) {",
    "V3 composable article context parameter"
)

# Stage A2: restore the last V3 document when entering the generic 3.0 entry;
# explicit route IDs take precedence. The session preference is V3-only.
s = replace_once(
    s,
    '''    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    var articleId by remember { mutableStateOf(vm.newId()) }
    var title by remember { mutableStateOf("未命名文章") }
    var html by remember { mutableStateOf("<p><br></p>") }''',
    '''    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val v3SessionPrefs = remember(context) { context.getSharedPreferences("xingtu_v3_editor_session", Context.MODE_PRIVATE) }
    val initialArticle = remember(initialArticleId, vm.data.articles) {
        val requested = initialArticleId?.takeIf { id -> id.isNotBlank() && vm.data.articles.any { it.id == id } }
        val last = v3SessionPrefs.getString("active_article_id", null)
            ?.takeIf { id -> vm.data.articles.any { it.id == id } }
        (requested ?: last)?.let { id -> vm.data.articles.firstOrNull { it.id == id } }
    }
    var articleId by remember { mutableStateOf(initialArticle?.id ?: vm.newId()) }
    var title by remember { mutableStateOf(initialArticle?.title ?: "未命名文章") }
    var html by remember { mutableStateOf(initialArticle?.html ?: "<p><br></p>") }''',
    "V3 isolated article session initialization"
)

# Seed all article metadata from the selected document instead of blanking it on entry.
for old, new, label in [
    ('var saved by remember { mutableStateOf(false) }', 'var saved by remember { mutableStateOf(initialArticle != null) }', "initial saved state"),
    ('var subtitle by remember { mutableStateOf("") }', 'var subtitle by remember { mutableStateOf(initialArticle?.subtitle ?: "") }', "initial subtitle"),
    ('var summary by remember { mutableStateOf("") }', 'var summary by remember { mutableStateOf(initialArticle?.summary ?: "") }', "initial summary"),
    ('var author by remember { mutableStateOf("") }', 'var author by remember { mutableStateOf(initialArticle?.author ?: "") }', "initial author"),
    ('var category by remember { mutableStateOf("") }', 'var category by remember { mutableStateOf(initialArticle?.category ?: "") }', "initial category"),
    ('var tagsText by remember { mutableStateOf("") }', 'var tagsText by remember { mutableStateOf(initialArticle?.tags?.joinToString(", ") ?: "") }', "initial tags"),
    ('var articleStatus by remember { mutableStateOf("draft") }', 'var articleStatus by remember { mutableStateOf(initialArticle?.status ?: "draft") }', "initial status"),
    ('var coverAssetId by remember { mutableStateOf("") }', 'var coverAssetId by remember { mutableStateOf(initialArticle?.coverAssetId ?: "") }', "initial cover")
]:
    s = replace_once(s, old, new, label)

# Every article switch updates only the V3 session pointer; document data remains shared.
s = replace_once(
    s,
    '''    fun newArticle() {
        saveDocument()
        articleId = vm.newId()''',
    '''    fun newArticle() {
        saveDocument()
        articleId = vm.newId()
        v3SessionPrefs.edit().putString("active_article_id", articleId).apply()''',
    "new article session pointer"
)
s = replace_once(
    s,
    '''    fun openArticle(article: ArticleDocument) {
        articleId = article.id''',
    '''    fun openArticle(article: ArticleDocument) {
        articleId = article.id
        v3SessionPrefs.edit().putString("active_article_id", article.id).apply()''',
    "open article session pointer"
)

# Keep the V3 last-open pointer current without touching the classic editor.
s = replace_once(
    s,
    '''    LaunchedEffect(title, html, articleId, pendingSave, webReady) {
        if (!webReady || showArticleList) return@LaunchedEffect''',
    '''    LaunchedEffect(articleId) {
        if (articleId.isNotBlank()) v3SessionPrefs.edit().putString("active_article_id", articleId).apply()
    }

    LaunchedEffect(title, html, articleId, pendingSave, webReady) {
        if (!webReady || showArticleList) return@LaunchedEffect''',
    "V3 session persistence effect"
)

# Stage B: retain the legacy panel enum and all panel bodies; introduce a separate
# 8-item primary category enum that routes to the existing implementations.
enum_marker = "private enum class EditorPanel(val label: String) {"
if s.count(enum_marker) != 1:
    fail("legacy EditorPanel enum declaration is missing or ambiguous")
enum_start = s.index(enum_marker)
enum_open = s.index("{", enum_start)
enum_end = matching_brace(s, enum_open)
legacy_enum = s[enum_start:enum_end]
for old_label, new_label in [
    ('TEXT2("文字2")', 'TEXT2("文字高级")'),
    ('LAYOUT("布局")', 'LAYOUT("分栏")'),
    ('STYLE("图文收藏")', 'STYLE("样式")'),
    ('TEMPLATE("图文模板")', 'TEMPLATE("模板库")')
]:
    legacy_enum = legacy_enum.replace(old_label, new_label, 1)
category_enum = """

private enum class EditorCategory(val label: String) {
    TEXT("文字"), IMAGE("图片"), COMPONENT("组件"), LAYOUT("排版"),
    LAYER("图层"), STYLE("样式"), TEMPLATE("模板"), DOCUMENT("文档")
}"""
s = s[:enum_start] + legacy_enum + category_enum + s[enum_end:]

s = replace_once(
    s,
    '''    var showTemplateSubnav by remember { mutableStateOf(false) }
    var showInsertLauncherMenu''',
    '''    var showTemplateSubnav by remember { mutableStateOf(false) }
    var showTextSubnav by remember { mutableStateOf(false) }
    var showComponentSubnav by remember { mutableStateOf(false) }
    var showLayoutSubnav by remember { mutableStateOf(false) }
    var showInsertLauncherMenu''',
    "category subnavigation state"
)

# Replace only the persistent primary dock. The secondary panel content and every
# old EditorPanel implementation remain intact and are still reachable.
marker = "// Persistent primary navigation: keep it in the editor's main Box, not only inside the tool Dialog."
if s.count(marker) != 1:
    fail("persistent primary navigation anchor is not unique")
start = s.index(marker)
if_start = s.find("            if (!previewMode) {", start)
if if_start < 0:
    fail("primary navigation if-block not found")
open_brace = s.find("{", if_start)
end = matching_brace(s, open_brace)
new_dock = '''            // 醒图 3.0 primary navigation: exactly eight semantic categories.
            if (!previewMode && !showToolPopup) {
                Row(
                    Modifier.fillMaxWidth().height(50.dp).background(Color(0xFF181818)),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceAround
                ) {
                    EditorCategory.values().forEach { category ->
                        val selected = when (category) {
                            EditorCategory.TEXT -> activePanel == EditorPanel.TEXT || activePanel == EditorPanel.TEXT2
                            EditorCategory.IMAGE -> activePanel == EditorPanel.IMAGE
                            EditorCategory.COMPONENT -> activePanel in setOf(EditorPanel.TITLE, EditorPanel.CARD, EditorPanel.COMPONENT, EditorPanel.SVG)
                            EditorCategory.LAYOUT -> activePanel == EditorPanel.LAYOUT || activePanel == EditorPanel.CANVAS
                            EditorCategory.LAYER -> activePanel == EditorPanel.LAYER
                            EditorCategory.STYLE -> activePanel == EditorPanel.STYLE
                            EditorCategory.TEMPLATE -> activePanel == EditorPanel.TEMPLATE
                            EditorCategory.DOCUMENT -> activePanel == EditorPanel.DOCUMENT
                        }
                        TextButton(
                            onClick = {
                                showTextSubnav = category == EditorCategory.TEXT
                                showComponentSubnav = category == EditorCategory.COMPONENT
                                showLayoutSubnav = category == EditorCategory.LAYOUT
                                showTemplateSubnav = category == EditorCategory.TEMPLATE
                                showCanvasPopup = false
                                floatingMenu = ""
                                when (category) {
                                    EditorCategory.TEXT -> {
                                        activePanel = EditorPanel.TEXT
                                        runJs("setText2SelectionPreview(false);")
                                    }
                                    EditorCategory.IMAGE -> activePanel = EditorPanel.IMAGE
                                    EditorCategory.COMPONENT -> activePanel = EditorPanel.COMPONENT
                                    EditorCategory.LAYOUT -> activePanel = EditorPanel.LAYOUT
                                    EditorCategory.LAYER -> { activePanel = EditorPanel.LAYER; refreshLayerItems() }
                                    EditorCategory.STYLE -> activePanel = EditorPanel.STYLE
                                    EditorCategory.TEMPLATE -> { templateSubPanel = EditorPanel.TEMPLATE; activePanel = EditorPanel.TEMPLATE }
                                    EditorCategory.DOCUMENT -> activePanel = EditorPanel.DOCUMENT
                                }
                                showToolPopup = true
                                toolPanelHeightDp = if (category == EditorCategory.TEXT) 330f else 200f
                            },
                            contentPadding = PaddingValues(horizontal = 5.dp, vertical = 3.dp)
                        ) {
                            Text(
                                category.label,
                                color = if (selected) AppColors.Theme else Color(0xFFAAAAAA),
                                fontSize = 12.sp,
                                fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
                                maxLines = 1
                            )
                        }
                    }
                }
            }'''
s = s[:if_start] + new_dock + s[end:]

# Add category-specific tabs to the existing secondary panel header. The original
# template type tabs are retained, with an explicit route to the template library.
s = replace_once(
    s,
    '''                        if (activePanel == EditorPanel.TEXT2) {
                            Row(Modifier.weight(1f), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
                                listOf("字体", "样式", "排版").forEach { tab ->
                                    Column(Modifier.weight(1f).clickable { text2MainTab = tab }.padding(vertical = 5.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                        Text(tab, color = if (text2MainTab == tab) Color.White else Color(0xFF888888), fontSize = 15.sp, fontWeight = if (text2MainTab == tab) FontWeight.Bold else FontWeight.Normal)
                                        Box(Modifier.padding(top = 2.dp).width(20.dp).height(2.dp).clip(RoundedCornerShape(4.dp)).background(if (text2MainTab == tab) AppColors.Theme else Color.Transparent))
                                    }
                                }
                            }
                        } else if (showTemplateSubnav) {''',
    '''                        if (showTextSubnav || activePanel == EditorPanel.TEXT2) {
                            Row(Modifier.weight(1f), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
                                listOf(EditorPanel.TEXT to "基础", EditorPanel.TEXT2 to "高级").forEach { tab ->
                                    Column(Modifier.weight(1f).clickable {
                                        activePanel = tab.first
                                        if (tab.first == EditorPanel.TEXT2) runJs("setText2SelectionPreview(true);")
                                        else runJs("setText2SelectionPreview(false);")
                                    }.padding(vertical = 5.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                        Text(tab.second, color = if (activePanel == tab.first) Color.White else Color(0xFF888888), fontSize = 15.sp, fontWeight = if (activePanel == tab.first) FontWeight.Bold else FontWeight.Normal)
                                        Box(Modifier.padding(top = 2.dp).width(20.dp).height(2.dp).clip(RoundedCornerShape(4.dp)).background(if (activePanel == tab.first) AppColors.Theme else Color.Transparent))
                                    }
                                }
                            }
                        } else if (showComponentSubnav) {
                            Row(Modifier.weight(1f).horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
                                listOf(EditorPanel.TITLE, EditorPanel.CARD, EditorPanel.COMPONENT, EditorPanel.SVG).forEach { tab ->
                                    Column(Modifier.clickable { activePanel = tab }.padding(horizontal = 8.dp, vertical = 5.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                        Text(tab.label, color = if (activePanel == tab) Color.White else Color(0xFF888888), fontSize = 14.sp, fontWeight = if (activePanel == tab) FontWeight.Bold else FontWeight.Normal)
                                        Box(Modifier.padding(top = 2.dp).width(20.dp).height(2.dp).clip(RoundedCornerShape(4.dp)).background(if (activePanel == tab) AppColors.Theme else Color.Transparent))
                                    }
                                }
                            }
                        } else if (showLayoutSubnav) {
                            Row(Modifier.weight(1f), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
                                listOf(EditorPanel.LAYOUT to "分栏", EditorPanel.CANVAS to "画布").forEach { tab ->
                                    Column(Modifier.weight(1f).clickable { activePanel = tab.first }.padding(vertical = 5.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                        Text(tab.second, color = if (activePanel == tab.first) Color.White else Color(0xFF888888), fontSize = 14.sp, fontWeight = if (activePanel == tab.first) FontWeight.Bold else FontWeight.Normal)
                                        Box(Modifier.padding(top = 2.dp).width(20.dp).height(2.dp).clip(RoundedCornerShape(4.dp)).background(if (activePanel == tab.first) AppColors.Theme else Color.Transparent))
                                    }
                                }
                            }
                        } else if (showTemplateSubnav) {''',
    "8-category secondary tab routing"
)

s = replace_once(
    s,
    '''                                listOf(EditorPanel.TITLE, EditorPanel.CARD, EditorPanel.IMAGE, EditorPanel.LAYOUT, EditorPanel.SVG, EditorPanel.COMPONENT).forEach { sub ->
                                    Column(Modifier.clickable { templateSubPanel = sub; activePanel = sub }.padding(horizontal = 7.dp, vertical = 5.dp),''',
    '''                                listOf(EditorPanel.TEMPLATE, EditorPanel.TITLE, EditorPanel.CARD, EditorPanel.IMAGE, EditorPanel.LAYOUT, EditorPanel.SVG, EditorPanel.COMPONENT).forEach { sub ->
                                    Column(Modifier.clickable { templateSubPanel = sub; activePanel = sub }.padding(horizontal = 7.dp, vertical = 5.dp),''',
    "template library tab"
)

# Ensure the old primary enum loop cannot silently reappear.
if "EditorPanel.values().filterNot" in s:
    fail("legacy primary navigation loop remains after Stage B")
if s.count("EditorCategory.values().forEach") != 1:
    fail("expected exactly one eight-category primary navigation")
for token in [
    "initialArticleId: String? = null",
    "xingtu_v3_editor_session",
    "EditorCategory.TEXT(\"文字\")",
    "EditorCategory.IMAGE(\"图片\")",
    "EditorCategory.COMPONENT(\"组件\")",
    "EditorCategory.LAYOUT(\"排版\")",
    "EditorCategory.LAYER(\"图层\")",
    "EditorCategory.STYLE(\"样式\")",
    "EditorCategory.TEMPLATE(\"模板\")",
    "EditorCategory.DOCUMENT(\"文档\")",
    "EditorPanel.TEXT2",
    "EditorPanel.TITLE",
    "EditorPanel.CARD",
    "EditorPanel.SVG",
    "EditorPanel.CANVAS",
    "EditorPanel.DOCUMENT",
]:
    if token not in s:
        fail("post-patch verification missing: " + token)

V3.write_text(s, encoding="utf-8")

# Route may carry an explicit document ID as:
# vm.screen = "xingtu_article_editor_v3:<article-id>"
main = MAIN.read_text(encoding="utf-8")
exact_route = '"xingtu_article_editor_v3" -> ArticleEditorScreenV3(vm) { vm.screen = "layout" }'
dynamic_route = '''vm.screen.startsWith("xingtu_article_editor_v3:") -> ArticleEditorScreenV3(
                            vm,
                            { vm.screen = "layout" },
                            vm.screen.substringAfter("xingtu_article_editor_v3:").takeIf { it.isNotBlank() }
                        )
                        '''
if dynamic_route.strip() not in main:
    main = replace_once(main, exact_route, dynamic_route + exact_route, "explicit article-ID route")
MAIN.write_text(main, encoding="utf-8")

check = MAIN.read_text(encoding="utf-8")
if 'vm.screen.startsWith("xingtu_article_editor_v3:")' not in check:
    fail("explicit article ID route verification failed")
if '"xingtu_article_editor_v3" -> ArticleEditorScreenV3(vm)' not in check:
    fail("generic 3.0 route verification failed")
print("Verified: Stage A V3 article/session context and Stage B eight-category navigation applied; legacy editor panel implementations retained.")
