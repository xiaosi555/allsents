#!/usr/bin/env python3
from pathlib import Path

root = Path('.')
base = root / 'source/ShiWanJu-Android/app/src/main'
java = base / 'java/com/shiwanju/app'

def read(rel):
    p = java / rel
    return p, p.read_text(encoding='utf-8')

def write(p, s):
    p.write_text(s, encoding='utf-8')

def replace_once(s, old, new, label):
    if old not in s:
        raise SystemExit('UI refinement anchor missing: ' + label)
    return s.replace(old, new, 1)

# Global light/dark palette and explicit override precedence.
p, s = read('ui/Theme.kt')
s = replace_once(s,
'''    private var darkAppearance by mutableStateOf(false)
    fun setAppearanceMode(mode: String, systemDark: Boolean) {
        darkAppearance = when (mode) {
            "dark" -> true
            "light" -> false
            else -> systemDark
        }
    }''',
'''    private var darkAppearance by mutableStateOf(false)
    private var appearanceModeState by mutableStateOf("system")
    val AppearanceMode: String get() = appearanceModeState
    val IsDark: Boolean get() = darkAppearance
    fun setAppearanceMode(mode: String, systemDark: Boolean) {
        appearanceModeState = if (mode in listOf("system", "light", "dark")) mode else "system"
        darkAppearance = when (appearanceModeState) {
            "dark" -> true
            "light" -> false
            else -> systemDark
        }
    }''', 'appearance mode state')
start = s.index('    // 排版页（深色）')
end = s.index('\n}\n\n@Composable\nfun ShiWanJuTheme', start)
palette = '''    // 全局外观调色板：排版、我的、公众号、表单和弹窗共用语义色。
    val Bg: Color get() = if (darkAppearance) Color(0xFF111315) else Color(0xFFF7F8F9)
    val Panel: Color get() = if (darkAppearance) Color(0xFF1C2023) else Color(0xFFFFFFFF)
    val Field: Color get() = if (darkAppearance) Color(0xFF252A2E) else Color(0xFFF1F3F5)
    val Line: Color get() = if (darkAppearance) Color(0xFF353B40) else Color(0xFFE2E6E9)
    val TextMain: Color get() = if (darkAppearance) Color(0xFFF1F3F4) else Color(0xFF17191B)
    val TextDim: Color get() = if (darkAppearance) Color(0xFFA8B0B6) else Color(0xFF737B82)
    val MyBg: Color get() = Bg
    val MyCard: Color get() = Panel
    val MyText: Color get() = TextMain
    val MyDim: Color get() = TextDim
    val MySubText: Color get() = TextDim
    val MyHint: Color get() = if (darkAppearance) Color(0xFF929AA1) else Color(0xFF92999F)
    val MyLine: Color get() = Line'''
s = s[:start] + palette + s[end:]
s = replace_once(s,
'''fun ShiWanJuTheme(dark: Boolean, content: @Composable () -> Unit) {
    val scheme = if (dark) darkColorScheme(''',
'''fun ShiWanJuTheme(dark: Boolean, content: @Composable () -> Unit) {
    val useDark = if (AppColors.AppearanceMode == "system") dark else AppColors.IsDark
    val scheme = if (useDark) darkColorScheme(''', 'Material3 theme mode precedence')
write(p, s)

# Common chips use the adaptive card surface rather than a hard-coded white fill.
p, s = read('ui/Components.kt')
s = s.replace('else Color.White', 'else AppColors.MyCard')
write(p, s)

# Shared back-arrow style and right-aligned hints in the three-item home group.
p, s = read('ui/MyScreens.kt')
if 'import androidx.compose.material.icons.Icons' not in s:
    s = s.replace('package com.shiwanju.app.ui\n', 'package com.shiwanju.app.ui\nimport androidx.compose.material.icons.Icons\nimport androidx.compose.material.icons.outlined.ArrowBack\n', 1)
s = replace_once(s,
'''            TextButton(onClick = { if (route == "home") { vm.screen = "layout" } else route = "home" }) {
                Text("‹ " + if (route == "home") "排版" else "我的", color = AppColors.MyText, fontSize = 16.sp)
            }''',
'''            IconButton(onClick = { if (route == "home") { vm.screen = "layout" } else route = "home" }) {
                Icon(Icons.Outlined.ArrowBack, contentDescription = "返回", tint = Color(0xFFB8B8B8), modifier = Modifier.size(20.dp))
            }''', 'My page header back button')
s = replace_once(s,
'''    Row(
        Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, color = AppColors.MyText, fontSize = 15.sp, fontWeight = FontWeight.Medium)
            Text(summary, color = Color(0xFF9CA3AF), fontSize = 12.sp, modifier = Modifier.padding(top = 4.dp))
        }
        Text("›", color = Color(0xFFB8B8B8), fontSize = 22.sp)
    }''',
'''    Row(
        Modifier.fillMaxWidth().clickable(onClick = onClick).padding(vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(title, color = AppColors.MyText, fontSize = 15.sp, fontWeight = FontWeight.Medium)
        Spacer(Modifier.weight(1f))
        Text(summary, color = AppColors.MyDim, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        Text("›", color = Color(0xFFB8B8B8), fontSize = 22.sp, modifier = Modifier.padding(start = 7.dp))
    }''', 'HomeGroupRow right-aligned summary')
s = s.replace('TextButton(onClick = onDismiss, contentPadding = PaddingValues(0.dp)) { Text("‹ 返回", color = AppColors.MyText, fontSize = 15.sp) }',
'''IconButton(onClick = onDismiss) { Icon(Icons.Outlined.ArrowBack, contentDescription = "返回", tint = Color(0xFFB8B8B8), modifier = Modifier.size(20.dp)) }''')
s = s.replace('TextButton(onClick = onCancel, contentPadding = PaddingValues(0.dp)) { Text("‹ 返回", color = AppColors.MyText, fontSize = 15.sp) }',
'''IconButton(onClick = onCancel) { Icon(Icons.Outlined.ArrowBack, contentDescription = "返回", tint = Color(0xFFB8B8B8), modifier = Modifier.size(20.dp)) }''')
write(p, s)

# Explicit ordered image selection. null preserves the original first-N default.
p, s = read('data/Models.kt')
s = replace_once(s,
'''    val imgPool: List<String> = emptyList(),       // 随机读取的配图池（最多 20 张）
    val moreCat:''',
'''    val imgPool: List<String> = emptyList(),       // 随机读取的配图池（最多 20 张）
    val selectedImgPool: List<String>? = null,     // 手动选择顺序；null 表示默认前 N 张
    val moreCat:''', 'UiState selected image list')
write(p, s)

p, s = read('ui/AppViewModel.kt')
s = replace_once(s,
'''        u = u.copy(imgModuleId = imgId, imgPool = pool)''',
'''        u = u.copy(imgModuleId = imgId, imgPool = pool, selectedImgPool = u.selectedImgPool?.filter { it in pool })''',
'validate selected images')
s = replace_once(s,
'''    fun rerollImages() { val (id, p) = drawImagePool(ui.imgModuleId); updateUi { copy(imgModuleId = id, imgPool = p) } }''',
'''    fun rerollImages() { val (id, p) = drawImagePool(ui.imgModuleId); updateUi { copy(imgModuleId = id, imgPool = p, selectedImgPool = null) } }

    /** 图片选择顺序就是最终排版顺序；再次点击已选图片即可取消。 */
    fun toggleImageSelection(url: String) {
        if (url !in ui.imgPool) return
        val selected = (ui.selectedImgPool ?: ui.imgPool.take(ui.quantity)).toMutableList()
        if (url in selected) selected.remove(url) else selected.add(url)
        updateUi { copy(selectedImgPool = selected) }
    }''', 'image selection view model')
write(p, s)

p, s = read('engine/PreviewEngine.kt')
s = replace_once(s, '        val pool = ui.imgPool\n', '        val pool = ui.selectedImgPool ?: ui.imgPool\n', 'preview selected image pool')
s = replace_once(s,
'''            fillUnit(ctx, clones, i, if (hasCopy) ordered[i] else null, if (pool.isNotEmpty()) pool[i % pool.size] else null, extras, ui.previewEmoji)''',
'''            val imageForItem = if (ui.selectedImgPool != null) pool.getOrNull(i) else if (pool.isNotEmpty()) pool[i % pool.size] else null
            fillUnit(ctx, clones, i, if (hasCopy) ordered[i] else null, imageForItem, extras, ui.previewEmoji)''',
'render selected images in click order')
write(p, s)

# Image picker: icon-only reroll, scroll-direction folder label, tap to select/deselect and numbered order.
p, s = read('ui/LayoutScreen.kt')
if 'import androidx.compose.material.icons.Icons' not in s:
    s = s.replace('import androidx.compose.material3.Text\n', 'import androidx.compose.material.icons.Icons\nimport androidx.compose.material.icons.outlined.Refresh\nimport androidx.compose.material3.Icon\nimport androidx.compose.material3.IconButton\nimport androidx.compose.material3.Text\n', 1)
if 'import androidx.compose.foundation.lazy.rememberLazyListState' not in s:
    s = s.replace('import androidx.compose.foundation.lazy.LazyRow\n', 'import androidx.compose.foundation.lazy.LazyRow\nimport androidx.compose.foundation.lazy.rememberLazyListState\n', 1)
if 'import androidx.compose.runtime.snapshotFlow' not in s:
    s = s.replace('import androidx.compose.runtime.*\n', 'import androidx.compose.runtime.*\nimport androidx.compose.runtime.snapshotFlow\n', 1)
start = s.index('@Composable\nprivate fun ImagePanel(vm: AppViewModel) {')
end = s.index('\n@Composable\nprivate fun MorePanel', start)
image_panel = '''@Composable
private fun ImagePanel(vm: AppViewModel) {
    val pool = vm.ui.imgPool
    if (pool.isEmpty()) return EmptyTip("暂无配图，请到【我的】-更多-配图中添加")
    val module = vm.data.files.image.firstOrNull { it.id == vm.ui.imgModuleId }
    val defaultSelected = pool.take(minOf(vm.ui.quantity, pool.size))
    val selected = vm.ui.selectedImgPool ?: defaultSelected
    val listState = rememberLazyListState()
    var showFolderName by remember { mutableStateOf(true) }
    LaunchedEffect(listState) {
        snapshotFlow { listState.isScrollInProgress to listState.lastScrolledForward }.collect { (scrolling, forward) ->
            if (scrolling) showFolderName = !forward
        }
    }
    Row(
        Modifier.fillMaxSize().padding(horizontal = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        IconButton(onClick = { vm.rerollImages() }, modifier = Modifier.size(38.dp)) {
            Icon(Icons.Outlined.Refresh, contentDescription = "重新选择", tint = AppColors.TextDim, modifier = Modifier.size(22.dp))
        }
        if (showFolderName) {
            Text(module?.name.orEmpty(), color = AppColors.TextDim, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
        LazyRow(state = listState, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.weight(1f)) {
            items(pool.size) { index ->
                val url = pool[index]
                val selectedIndex = selected.indexOf(url)
                Box(
                    Modifier.size(64.dp).clip(RoundedCornerShape(8.dp))
                        .border(2.dp, if (selectedIndex >= 0) AppColors.Theme else Color.Transparent, RoundedCornerShape(8.dp))
                        .clickable { vm.toggleImageSelection(url) }
                ) {
                    AsyncImage(model = url, contentDescription = "配图",
                        modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(6.dp)), contentScale = ContentScale.Crop)
                    if (selectedIndex >= 0) {
                        Box(Modifier.align(Alignment.BottomEnd).padding(3.dp).size(19.dp)
                            .clip(CircleShape).background(AppColors.Theme), contentAlignment = Alignment.Center) {
                            Text((selectedIndex + 1).toString(), color = AppColors.OnTheme, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }
}'''
s = s[:start] + image_panel + s[end:]
s = s.replace('vm.ui.copyLines, vm.ui.imgPool)', 'vm.ui.copyLines, vm.ui.imgPool, vm.ui.selectedImgPool)')
s = s.replace('imgModuleId = imageModule?.id, imgPool = images, historyIds = emptyList()', 'imgModuleId = imageModule?.id, imgPool = images, selectedImgPool = null, historyIds = emptyList()')
write(p, s)

# Official page backgrounds, labels, dropdown and add-article dialog adapt to the selected theme.
p, s = read('ui/OfficialAccountPage.kt')
s = s.replace('background(Color(0xFFF0F0F0))', 'background(AppColors.MyBg)')
s = s.replace('.background(Color.White)', '.background(AppColors.MyCard)')
for old, new in [
    ('color = Color(0xFF191919)', 'color = AppColors.MyText'),
    ('color = Color(0xFF171717)', 'color = AppColors.MyText'),
    ('color = Color(0xFF292929)', 'color = AppColors.MyText'),
    ('color = Color(0xFF202020)', 'color = AppColors.MyText'),
    ('color = Color.Gray', 'color = AppColors.MyDim'),
    ('color = Color.LightGray', 'color = AppColors.MyDim'),
]:
    s = s.replace(old, new)
s = s.replace('DropdownMenu(expanded = menu, onDismissRequest = { menu = false })',
              'DropdownMenu(expanded = menu, onDismissRequest = { menu = false }, containerColor = AppColors.MyCard)')
s = replace_once(s,
'''    if (adding) AlertDialog(
        onDismissRequest = { adding = false },''',
'''    if (adding) AlertDialog(
        onDismissRequest = { adding = false },
        containerColor = AppColors.MyCard,
        titleContentColor = AppColors.MyText,
        textContentColor = AppColors.MyText,''', 'official add dialog palette')
s = s.replace('title = { Text("添加公众号文章") }', 'title = { Text("添加公众号文章", color = AppColors.MyText) }')
s = s.replace('placeholder = { Text("粘贴微信文章链接") }',
'''placeholder = { Text("粘贴微信文章链接", color = AppColors.MyDim) },
            colors = OutlinedTextFieldDefaults.colors(focusedTextColor = AppColors.MyText, unfocusedTextColor = AppColors.MyText, focusedContainerColor = AppColors.MyCard, unfocusedContainerColor = AppColors.MyCard, focusedBorderColor = AppColors.Theme, unfocusedBorderColor = AppColors.MyLine, cursorColor = AppColors.Theme)''')
s = s.replace('Text("导入后缓存标题、封面、摘要和发布时间，正文在微信原文中打开。", color = Color.Gray, fontSize = 12.sp)',
              'Text("导入后缓存标题、封面、摘要和发布时间，正文在微信原文中打开。", color = AppColors.MyDim, fontSize = 12.sp)')
s = s.replace('Text("导入", color = FeedGreen)', 'Text("导入", color = AppColors.Theme)')
s = s.replace('Text("取消")', 'Text("取消", color = AppColors.MyDim)')
write(p, s)

# History page back button matches the official-account outline icon.
p, s = read('ui/HistoryArticlesPage.kt')
s = s.replace('import androidx.compose.material.icons.filled.ArrowBack', 'import androidx.compose.material.icons.outlined.ArrowBack')
s = s.replace('Icons.Default.ArrowBack, "返回", tint = Color(0xFFAAAAAA)',
              'Icons.Outlined.ArrowBack, "返回", tint = Color(0xFFB8B8B8), modifier = Modifier.size(19.dp)')
write(p, s)

print('UI refinements passed: global dark palette, right-aligned hints, shared back icon, official dialogs, ordered image selection and directional folder label.')
