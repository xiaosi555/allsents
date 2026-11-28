#!/usr/bin/env python3
"""Repair local image picker launch and insertion feedback."""
from pathlib import Path
p = Path(__file__).resolve().parents[1] / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
s = p.read_text(encoding="utf-8")
s = s.replace("val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments())",
              "val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents())")
s = s.replace("val imageGroupPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments())",
              "val imageGroupPicker = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents())")
pairs = [
('EditorTool("本地图片/相册") { imagePicker.launch(arrayOf("image/*")) }',
'''EditorTool("本地图片/相册") {
                                runCatching { imagePicker.launch("image/*") }
                                    .onFailure { vm.toast("无法打开图片选择器，请检查系统相册") }
                            }'''),
('EditorTool("双图组") { pendingImageGroupCount = 2; imageGroupPicker.launch(arrayOf("image/*")) }',
'''EditorTool("双图组") {
                                pendingImageGroupCount = 2
                                runCatching { imageGroupPicker.launch("image/*") }
                                    .onFailure { vm.toast("无法打开图片选择器，请检查系统相册") }
                            }'''),
('EditorTool("三图组") { pendingImageGroupCount = 3; imageGroupPicker.launch(arrayOf("image/*")) }',
'''EditorTool("三图组") {
                                pendingImageGroupCount = 3
                                runCatching { imageGroupPicker.launch("image/*") }
                                    .onFailure { vm.toast("无法打开图片选择器，请检查系统相册") }
                            }'''),
('EditorTool("双图并排") { pendingImageGroupCount = 2; imageGroupPicker.launch(arrayOf("image/*")) }',
'''EditorTool("双图并排") {
                                pendingImageGroupCount = 2
                                runCatching { imageGroupPicker.launch("image/*") }
                                    .onFailure { vm.toast("无法打开图片选择器，请检查系统相册") }
                            }''')
]
for old,new in pairs:
    if old in s: s=s.replace(old,new,1)
    else: print("Already migrated or anchor absent:",old[:35])
old = '''val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents()) { uris ->
        uris.forEach { uri ->'''
new = '''val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents()) { uris ->
        if (uris.isEmpty()) vm.toast("未选择图片")
        uris.forEach { uri ->'''
s=s.replace(old,new,1)
checks = [
"ActivityResultContracts.GetMultipleContents()) { uris ->" in s,
"val imageGroupPicker = rememberLauncherForActivityResult(ActivityResultContracts.GetMultipleContents())" in s,
'imagePicker.launch("image/*")' in s,
'imageGroupPicker.launch("image/*")' in s
]
if not all(checks): raise SystemExit("Image picker migration validation failed")
p.write_text(s,encoding="utf-8")
print("Image picker migrated to GetMultipleContents with visible launch-error feedback.")
