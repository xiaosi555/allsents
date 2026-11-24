#!/usr/bin/env python3
from pathlib import Path
import re

base = Path("source/ShiWanJu-Android/app/src/main")
java = base / "java/com/shiwanju/app"

def file(rel):
    p = java / rel
    return p, p.read_text(encoding="utf-8")

def save(p, s):
    p.write_text(s, encoding="utf-8")

# Theme swatches should sit directly on the settings page, not inside a card.
p, s = file("ui/ThemeSettings.kt")
s, n = re.subn(
    r'Column\(Modifier\.fillMaxWidth\(\)\.clip\(RoundedCornerShape\(18\.dp\)\)\.background\(AppColors\.MyCard\)\.padding\(16\.dp\), verticalArrangement = Arrangement\.spacedBy\(15\.dp\)\) \{',
    'Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(15.dp)) {',
    s, count=1
)
if n != 1: print("WARNING: theme swatch wrapper anchor not found")
save(p, s)

# Remove only the two explanatory labels; retain selectable icon artwork and names.
p, s = file("ui/IconSettings.kt")
s = "\n".join(line for line in s.split("\n") if 'Text("图标风格"' not in line and 'Text("选择后会切换手机桌面图标' not in line)
save(p, s)

# The My page uses the same flat, borderless card treatment as the 文章/版式/更多 group.
p, s = file("ui/MyScreens.kt")
s = s.replace('.shadow(1.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp))', '.clip(RoundedCornerShape(12.dp))')
s = s.replace('import androidx.compose.ui.draw.shadow\n', '')
s = s.replace('vm.data.history.forEach { h ->', 'vm.data.history.filterNot { it.id == "1791721426948" || it.id == "1791721454725" }.forEach { h ->')
s = re.sub(r'(?m)^(\s*)ListRow\(h\.name\.ifEmpty.*\n', r'\1ListRow(h.name.ifEmpty { h.title.ifEmpty { "未命名往期" } }, count.toString() + " 条内容 · 文字版") { editKey = h.id }\n', s)
s = s.replace('Field("图片地址（每行一个）", images, { images = it }, 3, "留空则使用文字版往期")', '')
save(p, s)

# Layout toolbar: white logo at left, count in the former copy-button position, no top copy button.
p, s = file("ui/LayoutScreen.kt")
if "import androidx.compose.foundation.Image\n" not in s:
    s = s.replace("import androidx.compose.foundation.BorderStroke\n", "import androidx.compose.foundation.BorderStroke\nimport androidx.compose.foundation.Image\n")
if "import androidx.compose.ui.res.painterResource\n" not in s:
    s = s.replace("import androidx.compose.ui.platform.LocalDensity\n", "import androidx.compose.ui.platform.LocalDensity\nimport androidx.compose.ui.res.painterResource\n")
if "import com.shiwanju.app.R\n" not in s:
    s = s.replace("import com.shiwanju.app.data.LayoutItem\n", "import com.shiwanju.app.R\nimport com.shiwanju.app.data.LayoutItem\n")
toolbar = '''@Composable
private fun TopBar(vm: AppViewModel) {
    Row(Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 14.dp), verticalAlignment = Alignment.CenterVertically) {
        Image(
            painter = painterResource(R.drawable.app_logo),
            contentDescription = "拾万句",
            contentScale = ContentScale.Fit,
            modifier = Modifier.size(width = 28.dp, height = 27.dp)
        )
        Spacer(Modifier.weight(1f))
        Text(vm.charCount.toString() + "字", color = AppColors.TextDim, fontSize = 12.sp)
        Spacer(Modifier.width(10.dp))
        ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing) { vm.toggleEditing() }
    }
}'''
s, n = re.subn(r'@Composable\nprivate fun TopBar\(vm: AppViewModel\) \{.*?\n\}', lambda m: toolbar, s, count=1, flags=re.S)
if n != 1: print("WARNING: layout toolbar anchor not found")

# Require 52dp of accumulated horizontal travel before changing the source label.
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
                        showFolderName = direction > 0
                        accumulated = 0f
                    }
                }
            }
        }
    }'''
if old in s:
    s = s.replace(old, new, 1)
else:
    print("WARNING: image folder scroll anchor not found")

# Hide only the two bundled non-text presets. Imported/custom history entries remain in the data model.
s = s.replace('vm.data.history.forEach { h -> GridCard', 'vm.data.history.filterNot { it.id == "1791721426948" || it.id == "1791721454725" }.forEach { h ->')
save(p, s)

# Prevent a previous install's saved selection from resurrecting the hidden image/pinned presets.
p, s = file("ui/AppViewModel.kt")
s = s.replace(
    'val hids = u.historyIds.filter { id -> data.history.any { it.id == id } }',
    'val hids = u.historyIds.filter { id -> id != "1791721426948" && id != "1791721454725" && data.history.any { it.id == id } }'
)
s = s.replace(
    'if (data.history.isEmpty()) return toast("暂无往期条目，请到【我的】-更多-往期中添加")',
    'if (data.history.none { it.id != "1791721426948" && it.id != "1791721454725" }) return toast("暂无文字版往期条目，请到【我的】-更多-往期中添加")'
)
s = s.replace('''val item = data.history.firstOrNull { it.id == id }
            ?: data.history.firstOrNull { it.id == selectedId }
            ?: data.history.first()''',
'''val available = data.history.filterNot { it.id == "1791721426948" || it.id == "1791721454725" }
        val item = available.firstOrNull { it.id == id }
            ?: available.firstOrNull { it.id == selectedId }
            ?: available.first()''')
save(p, s)

print("UI refinement v2 completed")
