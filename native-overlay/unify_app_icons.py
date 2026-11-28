#!/usr/bin/env python3
"""Route every Compose Material icon through the searchable in-app icon registry."""
from pathlib import Path
import re

ROOT = Path("source/ShiWanJu-Android/app/src/main/java")
if not ROOT.exists():
    raise SystemExit(f"Android Kotlin source tree not found: {ROOT}")

registry = ROOT / "com/shiwanju/app/ui/HomeAndIconLibrary.kt"
if not registry.is_file():
    raise SystemExit("Central icon registry is missing.")

files = list(ROOT.rglob("*.kt"))
pattern = re.compile(r"Icons\.(Outlined|Filled|Rounded|TwoTone|Sharp|Default)\.([A-Za-z0-9_]+)")
found = {}
for path in files:
    if path == registry:
        continue
    source = path.read_text(encoding="utf-8")
    for style, name in pattern.findall(source):
        found.setdefault(name, (style, name))

labels = {
    "ArrowBack":"返回", "ArrowForward":"前进", "Close":"关闭", "Check":"确认",
    "Add":"添加", "Remove":"移除", "Delete":"删除", "Edit":"编辑", "Save":"保存",
    "Search":"搜索", "Settings":"设置", "Home":"主页", "MoreHoriz":"更多",
    "MoreVert":"更多操作", "Undo":"撤销", "Redo":"重做", "Refresh":"刷新",
    "Image":"图片", "Photo":"照片", "PhotoLibrary":"相册", "CameraAlt":"相机",
    "Folder":"文件夹", "History":"历史记录", "TextFields":"文字", "FormatSize":"字号",
    "FormatAlignCenter":"居中对齐", "FormatAlignLeft":"左对齐", "FormatAlignRight":"右对齐",
    "Brush":"画笔", "Crop":"裁剪", "RotateRight":"旋转", "Layers":"图层",
    "Widgets":"组件", "Palette":"调色板", "AutoFixHigh":"智能优化",
    "Opacity":"透明度", "BorderAll":"边框", "Lock":"锁定", "LockOpen":"解锁",
    "Visibility":"显示", "VisibilityOff":"隐藏", "ContentCopy":"复制",
    "ContentPaste":"粘贴", "Share":"分享", "Download":"下载", "Upload":"上传",
    "Favorite":"收藏", "Star":"星标", "AccountCircle":"账户", "Person":"用户",
    "Notifications":"通知", "Help":"帮助", "Info":"信息", "Warning":"警告",
    "Error":"错误", "CheckCircle":"成功", "ExpandMore":"展开", "ExpandLess":"收起",
    "KeyboardArrowDown":"向下", "KeyboardArrowUp":"向上", "Tune":"调整",
    "FilterList":"筛选", "Sort":"排序", "GridView":"网格", "ViewList":"列表",
    "ViewQuilt":"排版", "Article":"文章", "PhotoCamera":"图片编辑", "CloudUpload":"云上传",
    "Download":"导出", "FileUpload":"导入", "FileDownload":"导出", "CalendarMonth":"日历",
    "Schedule":"时间", "Link":"链接", "OpenInNew":"打开", "Fullscreen":"全屏",
    "FullscreenExit":"退出全屏", "ZoomIn":"放大", "ZoomOut":"缩小", "CenterFocusStrong":"定位",
    "AlignHorizontalCenter":"水平居中", "AlignVerticalCenter":"垂直居中",
    "Flip":"翻转", "FlipCameraAndroid":"翻转", "RotateLeft":"向左旋转",
    "FormatColorFill":"填充", "FormatColorText":"文字颜色", "TextFormat":"文字样式",
    "FormatBold":"粗体", "FormatItalic":"斜体", "FormatUnderlined":"下划线",
    "FormatLineSpacing":"行距", "SpaceBar":"间距", "AspectRatio":"比例",
    "LayersClear":"清空图层", "PlaylistAdd":"添加项目", "Menu":"菜单",
    "ArrowUpward":"上移", "ArrowDownward":"下移", "DragHandle":"拖动",
    "Done":"完成", "DoneAll":"全部完成", "Cancel":"取消", "Clear":"清除",
    "CloseFullscreen":"关闭全屏", "More":"更多", "Circle":"圆形"
}

registry_source = registry.read_text(encoding="utf-8")
styles = {style for style, _ in found.values()}
style_imports = []
for style, package in [("Filled","filled"),("Default","filled"),("Rounded","rounded"),("TwoTone","twotone"),("Sharp","sharp")]:
    if style in styles:
        line = f"import androidx.compose.material.icons.{package}.*"
        if line not in registry_source:
            style_imports.append(line)
for line in style_imports:
    registry_source = registry_source.replace("import androidx.compose.material.icons.Icons\n", "import androidx.compose.material.icons.Icons\n" + line + "\n", 1)
existing = set(re.findall(r'AppIconItem\("([^"]+)"', registry_source))
additions = []
for name, (style, _) in sorted(found.items()):
    key = re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()
    if key in existing:
        continue
    additions.append(f' AppIconItem("{key}","{labels.get(name, name)}","扩展",Icons.{style}.{name}),')
if additions:
    anchor = ")\n\n@Composable fun AppIconVector"
    if anchor not in registry_source:
        raise SystemExit("Cannot locate icon registry insertion point.")
    registry_source = registry_source.replace(anchor, "\n" + "\n".join(additions) + anchor, 1)
    registry.write_text(registry_source, encoding="utf-8")

replaced = 0
for path in files:
    if path == registry:
        continue
    source = path.read_text(encoding="utf-8")
    if not pattern.search(source):
        continue
    package = re.search(r"(?m)^package ([\w.]+)", source)
    package_name = package.group(1) if package else ""
    def convert(match):
        nonlocal_dummy = None
        name = match.group(2)
        key = re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower()
        return f'AppIconVector("{key}")'
    updated = pattern.sub(convert, source)
    if package_name != "com.shiwanju.app.ui" and "import com.shiwanju.app.ui.AppIconVector" not in updated:
        updated = re.sub(r"(?m)^package [^\n]+\n", lambda m: m.group(0) + "\nimport com.shiwanju.app.ui.AppIconVector\n", updated, count=1)
    path.write_text(updated, encoding="utf-8")
    replaced += 1

print(f"Central icon registry expanded with {len(additions)} icons; routed Material icon usage through AppIconVector in {replaced} Kotlin files.")
