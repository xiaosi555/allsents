#!/usr/bin/env python3
"""Migrate Xiumi and Xingtu 2.0 controls to the shared semantic line-icon renderer."""
from pathlib import Path

ROOT = Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui")
EDITOR = ROOT / "ArticleEditorScreen.kt"
XIUMI = ROOT / "XiumiArticleLayoutScreen.kt"
XINGTU2 = ROOT / "XingtuEditorV2Screen.kt"
for p in (EDITOR, XIUMI, XINGTU2):
    if not p.is_file():
        raise SystemExit(f"Required screen missing: {p}")
e = EDITOR.read_text(encoding="utf-8")
if "fun ShiWanJuLineIcon(" not in e or "val sw = (w + h) / 48f * 1.5f" not in e:
    raise SystemExit("Shared 24dp / 1.5px line icon renderer is not installed.")
if 'k.contains("加字")' not in e or 'k.contains("加图")' not in e:
    raise SystemExit("加字 / 加图 semantic icon mappings are missing.")

x = XIUMI.read_text(encoding="utf-8")
old_enum = '''private enum class XiumiDock(val label:String,val icon:String) {
 THEME("主题","◉"), TITLE("标题","T"), TEXT("文字","文"), IMAGE("图片","▧"), LAYOUT("布局","▦"),
 CARD("卡片","▤"), SVG("SVG","◇"), COMPONENT("组件","⊞"), TEMPLATE("模板","▣"), FAVORITE("收藏","♡")
}'''
new_enum = '''private enum class XiumiDock(val label:String,val icon:String) {
 THEME("主题","palette"), TITLE("标题","title"), TEXT("文字","font"), IMAGE("图片","image"), LAYOUT("布局","layout"),
 CARD("卡片","card"), SVG("SVG","component"), COMPONENT("组件","widgets"), TEMPLATE("模板","template"), FAVORITE("收藏","favorite")
}'''
if old_enum in x:
    x = x.replace(old_enum, new_enum, 1)
x = x.replace('Text(item.icon,fontSize=19.sp,color=if(active) accent else Color.DarkGray)', 'ShiWanJuLineIcon(item.label,if(active) accent else Color.DarkGray,Modifier.size(22.dp))')
x = x.replace('Icon(Icons.Outlined.ArrowBack,contentDescription="返回")', 'ShiWanJuLineIcon("返回",Color(0xFF292D31),Modifier.size(22.dp))')
x = x.replace('Text("图片＋",fontSize=10.sp,color=accent,modifier=Modifier.clickable { imageImportLauncher.launch(arrayOf("image/*")) })', 'Row(Modifier.clickable { imageImportLauncher.launch(arrayOf("image/*")) },verticalAlignment=Alignment.CenterVertically) { ShiWanJuLineIcon("加图",accent,Modifier.size(15.dp)); Text("图片",fontSize=10.sp,color=accent) }')
x = x.replace('Text("导入＋",fontSize=10.sp,color=accent,modifier=Modifier.clickable { importLauncher.launch(arrayOf("text/plain","text/markdown","text/html","application/json")) })', 'Row(Modifier.clickable { importLauncher.launch(arrayOf("text/plain","text/markdown","text/html","application/json")) },verticalAlignment=Alignment.CenterVertically) { ShiWanJuLineIcon("导入",accent,Modifier.size(15.dp)); Text("导入",fontSize=10.sp,color=accent) }')
if "Text(item.icon" in x or "Icon(Icons.Outlined.ArrowBack" in x or "Text(\"图片＋\"" in x or "Text(\"导入＋\"" in x:
    raise SystemExit("Xiumi contains an unconverted glyph-based icon control.")
if "ShiWanJuLineIcon(item.label" not in x or "ShiWanJuLineIcon(\"加图\"" not in x:
    raise SystemExit("Xiumi dock or add-image action is not using semantic line icons.")
XIUMI.write_text(x, encoding="utf-8")

v = XINGTU2.read_text(encoding="utf-8")
v = v.replace('Text("⠿", color = panelColors.onSurfaceVariant, fontSize = 17.sp,', 'ShiWanJuLineIcon("拖动", panelColors.onSurfaceVariant, Modifier.size(20.dp)); Text(" ", color = panelColors.onSurfaceVariant, fontSize = 1.sp,')
if 'Text("⠿"' in v or 'ShiWanJuLineIcon("拖动"' not in v:
    raise SystemExit("Xingtu 2.0 layer drag handle is not using the shared line icon.")
XINGTU2.write_text(v, encoding="utf-8")
print("Linear icon migration verified: shared renderer, Xiumi dock/actions, Xingtu 2.0 layer drag.")
