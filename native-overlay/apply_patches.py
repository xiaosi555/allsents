#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
base = root / "source" / "ShiWanJu-Android" / "app" / "src" / "main" / "java" / "com" / "shiwanju" / "app"
def edit(path, replacements):
    p = base / path
    s = p.read_text(encoding="utf-8")
    for old, new in replacements:
        if old not in s:
            raise SystemExit(f"Patch anchor missing in {path}: {old[:90]!r}")
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")

edit("ui/AppViewModel.kt", [
    ('var previewHtml by mutableStateOf(""); private set',
     'var previewHtml by mutableStateOf(""); private set\n    var manualInput by mutableStateOf("")'),
    ('var screen by mutableStateOf("layout")          // layout / my',
     'var screen by mutableStateOf("home")            // home / layout / my'),
    ('    /** 选中文案名称；再次点击同一名称 = 重新随机读取 */',
     '''    fun setManualInput(value: String) { manualInput = value }

    /** 将顶部手动输入的多行内容作为当前预览文案池；“正文——出处”由预览引擎统一识别。 */
    fun applyManualText() {
        val lines = TextUtil.splitSingleLines(manualInput)
        if (lines.isEmpty()) {
            if (ui.copyLines.isEmpty()) {
                val module = data.files.text.firstOrNull { it.id == ui.copyModuleId }
                    ?: data.files.text.firstOrNull { it.category == ui.textCat }
                if (module != null) updateUi { copy(copyModuleId = module.id, copyLines = drawCopy(module)) }
                else toast("请输入文案，或先选择一个文案模块")
            }
            return
        }
        updateUi { copy(copyModuleId = null, copyLines = lines.take(COPY_POOL_SIZE)) }
        toast("已将输入内容应用到预览")
    }

    /** 对当前文案模块重新随机抽取一组内容。 */
    fun rerollCopy() {
        val module = data.files.text.firstOrNull { it.id == ui.copyModuleId }
            ?: data.files.text.firstOrNull { it.category == ui.textCat }
        if (module == null) return toast("当前分类暂无文案模块")
        updateUi { copy(copyModuleId = module.id, copyLines = drawCopy(module)) }
    }

    /** 选中文案名称；再次点击同一名称 = 重新随机读取 */''')
])

edit("ui/MyScreens.kt", [
    ('BackHandler { if (route == "home") vm.screen = "layout" else route = "home" }',
     'BackHandler { if (route == "home") vm.screen = "home" else route = "home" }'),
    ('onClick = { if (route == "home") vm.screen = "layout" else route = "home" }',
     'onClick = { if (route == "home") vm.screen = "home" else route = "home" }')
])

edit("ui/LayoutScreen.kt", [
    ('        ThemeChip("复制", false) {',
     '        ThemeChip("首页", false) { vm.screen = "home" }\n        Spacer(Modifier.width(8.dp))\n        ThemeChip("复制", false) {')
])
