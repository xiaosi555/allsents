#!/usr/bin/env python3
"""Stage C: normalize redesigned Xingtu secondary panel chrome without changing theme surfaces or actions."""
from pathlib import Path

ROOT = Path(".")
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorRedesignedScreen.kt"
ERROR = ROOT / "xingtu_stage_c_patch_error.txt"

def fail(message: str):
    ERROR.write_text(message + "\n", encoding="utf-8")
    raise SystemExit(message)

if not EDITOR.is_file():
    fail("Redesigned editor source missing; Stage C must run after the clone step")

s = EDITOR.read_text(encoding="utf-8")

def replace_once(old: str, new: str, label: str):
    global s
    count = s.count(old)
    if count != 1:
        fail(f"Stage C anchor mismatch [{label}]: expected 1, found {count}")
    s = s.replace(old, new, 1)

# The left action is always close/back; the right action is confirm/finish.
# Both preserve the original live-preview behavior and close only this panel.
confirm_left = 'IconButton(onClick = { if (activePanel == EditorPanel.TEXT2) runJs("setText2SelectionPreview(false);"); showToolPopup = false }) { Icon(Icons.Outlined.Check, contentDescription = "确定", tint = AppColors.Theme) }'
close_right = 'IconButton(onClick = { if (activePanel == EditorPanel.TEXT2) runJs("setText2SelectionPreview(false);"); showToolPopup = false }) { Icon(Icons.Outlined.Close, contentDescription = "关闭功能窗口", tint = Color.White) }'
replace_once(confirm_left, 'IconButton(onClick = { if (activePanel == EditorPanel.TEXT2) runJs("setText2SelectionPreview(false);"); showToolPopup = false }) { Icon(Icons.Outlined.Close, contentDescription = "关闭功能面板", tint = Color.White) }', "left close action")
replace_once(close_right, 'IconButton(onClick = { if (activePanel == EditorPanel.TEXT2) runJs("setText2SelectionPreview(false);"); showToolPopup = false }) { Icon(Icons.Outlined.Check, contentDescription = "完成并关闭", tint = AppColors.Theme) }', "right confirm action")

# Keep the established dark work-surface (#181818) and accent color. Add only
# a subtle separator to distinguish panel navigation from its working content.
anchor = '                    CompositionLocalProvider(LocalEditorToolDark provides true) {'
anchor_count = s.count(anchor)
if anchor_count < 1:
    fail("Stage C anchor mismatch [panel header separator]: expected at least 1, found 0")
separator = '                    Box(Modifier.fillMaxWidth().height(1.dp).background(Color(0xFF303030)))\\n'
s = s.replace(anchor, separator + anchor)
print(f"Stage C panel separators inserted: {anchor_count}")

# The old dock filtered every template sub-panel from the primary navigation,
# which also hid direct access to Image/Layout/Card/Component/SVG tools. Keep
# TITLE as a template-only category and TEXT2 as the text-properties workspace,
# but expose the functional panels as direct primary entries as well.
replace_once(
    'EditorPanel.values().filterNot { it in templateSubPanels || it == EditorPanel.TEXT2 }.forEach { panel ->',
    'EditorPanel.values().filterNot { it == EditorPanel.TEXT2 || it == EditorPanel.TITLE }.forEach { panel ->',
    "complete primary panel navigation"
)

# Normalize panel content inset. This does not alter the canvas, page background,
# article styles, theme palette, or any feature content.
old_padding = '.padding(horizontal = 13.dp, vertical = 4.dp)'
new_padding = '.padding(horizontal = 14.dp, vertical = 8.dp)'
if s.count(old_padding) != 1:
    fail(f"Stage C panel padding anchor mismatch: expected 1, found {s.count(old_padding)}")
s = s.replace(old_padding, new_padding, 1)

# Split the dense text tool cloud into named, independently spaced groups.
# Every existing EditorTool and callback is retained verbatim.
replace_once(
    '                        FlowRow(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {\n                            listOf("14" to "小", "16" to "标准", "18" to "大", "22" to "特大", "26" to "标题").forEach',
    '                        Text("字号与文字效果", color = Color(0xFFB0B0B0), fontSize = 11.sp, fontWeight = FontWeight.Medium, modifier = Modifier.padding(start = 2.dp, top = 7.dp, bottom = 2.dp))\n                        FlowRow(Modifier.fillMaxWidth().padding(top = 2.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {\n                            listOf("14" to "小", "16" to "标准", "18" to "大", "22" to "特大", "26" to "标题").forEach',
    "text panel typography group"
)

replace_once(
    '                            EditorTool("格式刷·应用") { runJs("restoreSelection();pasteTextFormat();saveSelection();") }\n                            EditorTool("无序列表")',
    '                            EditorTool("格式刷·应用") { runJs("restoreSelection();pasteTextFormat();saveSelection();") }\n                        }\n                        Text("段落结构", color = Color(0xFFB0B0B0), fontSize = 11.sp, fontWeight = FontWeight.Medium, modifier = Modifier.padding(start = 2.dp, top = 7.dp, bottom = 2.dp))\n                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {\n                            EditorTool("无序列表")',
    "text panel paragraph group"
)

replace_once(
    '                            EditorTool("任务清单") { insert("<ul style=\'list-style:none;padding-left:0\'><li>□ 第一项任务</li><li>□ 第二项任务</li><li>□ 第三项任务</li></ul>") }\n                            EditorTool("日期")',
    '                            EditorTool("任务清单") { insert("<ul style=\'list-style:none;padding-left:0\'><li>□ 第一项任务</li><li>□ 第二项任务</li><li>□ 第三项任务</li></ul>") }\n                        }\n                        Text("辅助插入", color = Color(0xFFB0B0B0), fontSize = 11.sp, fontWeight = FontWeight.Medium, modifier = Modifier.padding(start = 2.dp, top = 7.dp, bottom = 2.dp))\n                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {\n                            EditorTool("日期")',
    "text panel insert utilities group"
)

replace_once(
    '                            EditorTool("特殊符号") { insert("「」『』· — … ★ ✓ → ※") }\n                            EditorTool("行距1.6")',
    '                            EditorTool("特殊符号") { insert("「」『』· — … ★ ✓ → ※") }\n                        }\n                        Text("段落间距", color = Color(0xFFB0B0B0), fontSize = 11.sp, fontWeight = FontWeight.Medium, modifier = Modifier.padding(start = 2.dp, top = 7.dp, bottom = 2.dp))\n                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {\n                            EditorTool("行距1.6")',
    "text panel spacing group"
)

replace_once(
    '                            EditorTool("查找替换") { showFindReplace = true }\n                            EditorTool("宋体")',
    '                            EditorTool("查找替换") { showFindReplace = true }\n                        }\n                        Text("常用字体", color = Color(0xFFB0B0B0), fontSize = 11.sp, fontWeight = FontWeight.Medium, modifier = Modifier.padding(start = 2.dp, top = 7.dp, bottom = 2.dp))\n                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {\n                            EditorTool("宋体")',
    "text panel font group"
)

# Standardize the spacing between wrapped action tiles. Only FlowRows that do
# not already define vertical spacing are changed; all tool callbacks stay intact.
old_flow = 'horizontalArrangement = Arrangement.spacedBy(6.dp)) {'
new_flow = 'horizontalArrangement = Arrangement.spacedBy(6.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {'
flow_lines = s.splitlines()
for index, line in enumerate(flow_lines):
    if "FlowRow(" in line and old_flow in line:
        flow_lines[index] = line.replace(old_flow, new_flow)
s = "\n".join(flow_lines) + "\n"

# Normalize the small section captions in the secondary panel while preserving
# their text and location. Dynamic labels and explanatory copy are untouched.
old_color = 'color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp)'
new_color = 'color = Color(0xFFB0B0B0), fontSize = 11.sp, fontWeight = FontWeight.Medium, modifier = Modifier.padding(start = 2.dp, bottom = 7.dp)'
count = s.count(old_color)
if count < 4:
    fail(f"Expected multiple secondary-panel section captions, found {count}")
s = s.replace(old_color, new_color)

# Explicitly preserve the independent scroll container created by the existing
# bottom-sheet patch. TEXT2 keeps its own internal scroll container.
required = {
    "left close icon": 'contentDescription = "关闭功能面板"' in s,
    "right confirm icon": 'contentDescription = "完成并关闭"' in s,
    "subtle panel separator": 'background(Color(0xFF303030))' in s,
    "existing panel surface preserved": '.background(Color(0xFF181818))' in s,
    "panel content inset": '.padding(horizontal = 14.dp, vertical = 8.dp)' in s,
    "independent panel scroll": '.verticalScroll(toolPanelScrollState)' in s,
    "TEXT2 own scroll": 'verticalScroll(rememberScrollState())' in s[s.index('private fun Text2EditorPanel'):s.index('@OptIn(ExperimentalLayoutApi::class)', s.index('private fun Text2EditorPanel') + 1)],
    "200dp minimum and 400dp maximum": 'toolPanelHeightDp.coerceIn(200f, 400f)' in s,
    "all feature cases retained": all(f'EditorPanel.{name} ->' in s for name in ["TEXT","IMAGE","TEXT2","TITLE","LAYOUT","CARD","COMPONENT","SVG","STYLE","LAYER","CANVAS","DOCUMENT","TEMPLATE"]),
    "direct primary entries exposed": 'EditorPanel.values().filterNot { it == EditorPanel.TEXT2 || it == EditorPanel.TITLE }' in s,
    "text tools grouped": all(f'Text("{label}"' in s for label in ["字号与文字效果","段落结构","辅助插入","段落间距","常用字体"]),
}
failed = [name for name, ok in required.items() if not ok]
if failed:
    fail("Stage C post-patch validation failed: " + ", ".join(failed))

EDITOR.write_text(s, encoding="utf-8")
print(f"Stage C panel chrome normalized; {count} section captions updated; feature callbacks and existing theme surface preserved.")
