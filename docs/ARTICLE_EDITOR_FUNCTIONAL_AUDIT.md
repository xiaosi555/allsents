# 文章编辑器阶段 A 功能审计记录（第一版）

> 仓库：xiaosi555/allsents  
> 分支：main  
> 审计对象：native-overlay 中的 ArticleEditorScreen.kt，以及构建时注入脚本  
> 记录原则：静态代码盘点不等于运行验收；未从完整 Android 工程核实的数据模型、持久化及旧数据迁移细节均明确标记为待核查。

## 1. 当前工程结构与构建方式

- 编辑器 UI 源文件：`native-overlay/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt`。
- 构建时由 `native-overlay/apply_article_editor.py` 将编辑器文件复制到解压后的 Android 工程，并对 Models、Store、AppViewModel、MyScreens 等文件执行补丁。
- 阶段 B 和 C2 分别由 `apply_article_editor_stage_b.py`、`apply_article_editor_stage_c2.py` 注入。
- 因此，仓库中的 overlay 源文件、补丁脚本和最终构建工程是三个不同层次。仅检查 overlay 文件不能代表最终 APK 中的合成代码；验收必须以 CI 实际执行后的工程和构建产物为准。

## 2. 当前功能入口盘点

以下数量是对编辑器源码中静态 `EditorTool("...")` 标签的盘点，不代表实际可执行功能数；动态列表、弹窗和二级操作可能未计入。

| 分类 | 静态入口数 | 主要功能 |
|---|---:|---|
| 文字 | 51 | 字体、字形、字号、颜色、高亮、对齐、标题、引用、列表、缩进、段落间距、格式刷、查找替换、特殊符号等 |
| 图片 | 35 | 本地导入、网络图片、组图、宽度、裁切、旋转、圆角、边框、替换、说明文字、替代文本、组内移动、删除等 |
| 组件 | 21 | 编号标题、引用卡片、提示卡片、分割线、留白、数字列表、色块标题、边线标题、重点段落、首字下沉、时间轴、表格、代码块、关注引导、作者/媒体卡片及表格行列操作 |
| 样式 | 1 | 动态样式入口；实际样式条目由数据驱动，不能按 1 项理解为只有一种样式 |
| 图层 | 8 | 保存组合样式、模块移动、模块样式、复制/删除模块、保存为样式、插入链接等 |
| 文档 | 9 | 保存、文章信息、文章列表、版本记录、兼容检查、HTML/Markdown/文章包导入及导出等 |
| 图文模板 | 11 | 文章开头、标题、引用、清单、结尾、模板包导入导出、整篇模板、局部/组合组件及分类等 |

## 3. 关键处理函数与功能映射

### 3.1 编辑历史与内容同步

- `commitHistory`：提交编辑历史快照。
- `restoreHistoryCaret`：恢复历史记录中的光标。
- `undoEditor` / `redoEditor`：撤销、重做。
- `setEditorHtml`：写入编辑器 HTML。
- `setEditable`：切换编辑状态。
- `setPreviewInfo`：更新预览信息。
- `saveSelection` / `restoreSelection`：保存和恢复浏览器 Selection/Range。
- `insertHtml`：在编辑位置插入 HTML。

### 3.2 文字

- `applyInlineStyle`：对真实文字选区应用行内样式。
- `setSelectionFontSize`：设置选区字号。
- `selectedParagraph`、`styleSelectedParagraph`：识别并设置当前段落。
- `styleSelectionOrParagraph`：在有效选区与当前段落之间分派样式操作。
- `copyTextFormat` / `pasteTextFormat`：格式刷。
- `replaceAllText`：查找替换。
- `selectedTextElement`：定位当前文字元素。
- 部分基础字形命令仍通过 `document.execCommand` 实现，需重点验证跨节点选区、空选区、嵌套样式和撤销/重做。

### 3.3 图片

- `replaceSelectedImage`、`deleteSelectedImage`：替换、删除图片。
- `setSelectedImageWidth`、`setSelectedImageObjectPosition`：宽度和显示位置。
- `rotateSelectedImage`：旋转。
- `cropSelectedImage`、`resetSelectedImageCrop`：裁切与重置。
- `setSelectedImageRadius`、`setSelectedImageBorder`：圆角、边框。
- `setSelectedImageAlt`：替代文本。
- `moveSelectedImageInGroup`：组图内移动。
- 自定义像素裁切另有 Android Bitmap 文件处理流程；必须验证原素材保留、生成新资源、文章引用更新及撤销行为。

### 3.4 组件、表格与模块

- `selectedBlock`、`cleanBlockHtml`：识别和清理当前模块 HTML。
- `replaceSelectedBlockWithHtml`：替换模块结构。
- `duplicateSelectedBlock`、`deleteSelectedBlock`、`moveSelectedBlock`：复制、删除、移动。
- `applySelectedBlockStyle`：模块样式。
- `selectedTable`、`addTableRow`、`removeTableRow`、`addTableColumn`、`removeTableColumn`：表格操作。
- `updateMultiDragHandle`、`setMultiSelectMode`、`clearDragTarget`、`topLevelAt`、`clearTouchDrop`、`finishTouchDrag`：多选和拖动相关操作。

## 4. 对象选择与面板现状

当前编辑器通过 Android WebView 承载 contenteditable 画布，Compose 负责原生页面与工具面板。现有 Bridge 已有内容变化、模块选中、图片选中、文字选中回调。

阶段 B 补丁计划/实现的扩展包括：
- `EditorSelectionKind`：NONE、TEXT_BLOCK、TEXT_RANGE、CARET、IMAGE、COMPONENT、TABLE、LAYOUT、MULTI_BLOCK、PREVIEW。
- `EditorSelectionState`：对象 ID、折叠状态、坐标、尺寸、多选 ID。
- WebView 通过 `selectionChanged` 回传结构化选择状态。
- 为 DOM 模块分配稳定 ID；复制模块时重新生成 ID。
- 保存/恢复真实 Range 时校验其仍属于编辑根节点。
- 底部工具栏常驻，不再因文字或图片被选中而整体隐藏。

注意：阶段 B 补丁目前由构建脚本注入，需检查脚本应用后的最终源文件，不能仅凭补丁文件存在判定运行行为正确。

## 5. 构建状态与已确认问题

- 2026-11-25 提交 `cbf04729b8d4a4ddbee6edb487385b9bab238e0a` 为 `LocalDensity` 补入 Compose 导入后，Kotlin Compile Check（run 45604569581）通过。
- 同一提交的 Android APK Build（run 45604569593）通过全部步骤，APK 已上传；产物为 `app-debug.apk`，APK 文件大小约 19.3 MB。
- 这仅证明当时提交的补丁注入和编译/打包成功，不代表真机交互验收通过。
- 后续已在 `apply_article_editor.py` 加入素材引用保护、UUID ID 和原子数据保存补丁；这些新增补丁尚待最新工作流验证。

## 6. 数据与持久化审计边界

`apply_article_editor.py` 中包含对以下数据结构/业务方法的注入：
- `StyleModule`：可复用样式/模板模块。
- `ArticleDocument`：文章正文、标题、摘要、作者、封面、分类、标签、状态、字数和收藏状态。
- `MediaAsset`：本地素材 ID、文件名、MIME、相对路径、大小、创建时间。
- `ArticleRevision`：文章版本快照及文章元信息。
- `AppData`：styles、articles、mediaAssets、articleRevisions 等集合。
- Store 负责旧 JSON 归一化、缺失字段默认值和默认样式的一次性迁移。
- AppViewModel 注入保存/删除样式、保存/删除文章、恢复版本、保存/删除素材等操作。

仍需在完整 Android 工程构建上下文中逐项核查：
1. Models/Store 的实际数据类序列化方式、字段默认值和旧 JSON 兼容性。
2. 图片资源删除保护是否覆盖正文、封面、模板缩略图及组合样式引用。
3. 文章版本快照是否满足“最近 30 个版本”的既定规则，快速自动保存合并逻辑是否可能丢失重要版本。
4. HTML 清理、Markdown 转换、文章包导入导出对资源 ID 和外链的处理。
5. 文章复制、删除、恢复、封面替换及素材清理的关联数据完整性。

## 7. 阶段 A 尚未关闭的项目

- [ ] 在完整 Android 工程中核实 Models、Store、AppViewModel 的真实实现与所有调用点。
- [ ] 为 7 个功能分类建立“入口 → 处理函数 → 数据影响 → 验收方式”逐项映射，尤其补齐动态样式/模板条目。
- [ ] 核对文章、版本、素材、模板收藏的持久化及迁移。
- [ ] 核对导入/导出/HTML 清理/旧文章兼容链路。
- [ ] 对所有入口进行静态死链检查：按钮是否只切换状态、是否有无效命令、是否有未接入处理函数。
- [ ] 形成 A 阶段最终审计清单并关闭未确认项。


## 9. 本轮进一步审计发现（2026-11-25）

已解包成功构建产生的 `ShiWanJu-native-source`，检查的是补丁实际注入后的 Android 源码，而不是仅凭 overlay 源文件推断。

### 9.1 数据模型和持久化确认

- `AppData` 已包含 `styles`、`styleCategories`、`articles`、`mediaAssets`、`articleRevisions`。
- `ArticleDocument` 保存标题、HTML、创建/更新时间、副标题、摘要、作者、封面素材 ID、分类、标签、草稿/完成状态、字数和收藏状态。
- `ArticleRevision` 保存正文和上述文章元信息；`AppViewModel.saveArticle` 对每篇文章最多保留 30 条自动快照，并以 5 分钟为自动快照合并窗口。
- `Store` 将业务数据保存在 `filesDir/app_data.json`，界面状态及偏好放在 SharedPreferences。
- 备份 JSON 解析要求包含 `accounts` 数组和 `files` 对象；文章、模板和素材数据作为 `AppData` 字段随 JSON 一起序列化。
- 旧字段缺失时使用模型默认值，并通过 `normalize` 补齐缺失/重复 ID、文案分类和样式分类；新增文章相关字段的兼容性仍需使用真实旧备份进行导入回归。

### 9.2 已发现并已提交修复的风险

1. **素材引用保护不完整**：旧 `deleteMediaAsset` 只检查当前文章正文/封面和样式 HTML，未检查文章版本快照，也未检查样式缩略图。恢复旧版本时可能因素材元数据已移除而无法加载图片。本轮已修改构建注入脚本，增加版本快照和样式缩略图引用保护。
2. **ID 生成碰撞风险**：旧 `newId()` 使用毫秒时间戳；同一毫秒创建多条文章/素材可能得到相同 ID。本轮已改为 UUID。
3. **数据保存失败被静默吞掉**：旧 `Store.saveData` 用 `runCatching` 忽略写入异常，`updateData` 又先更新内存再保存，可能造成界面提示正常但磁盘没有持久化。本轮已在注入脚本加入临时文件 + 同目录备份替换、文件同步及失败反馈；写盘失败时不提交内存态更新。

以上三个修复已提交到 main，但必须等最新 CI 构建成功，并检查注入后的源文件确实包含补丁后，才可关闭对应静态检查项。

### 9.3 仍需回归的持久化边界

- 删除素材后检查当前文章、版本快照、封面、样式 HTML 和样式缩略图引用均能保护资源。
- 删除文章后确认对应版本一并删除；确认不影响其他文章引用的共享素材。
- 恢复版本后确认正文、元信息、图片和封面均恢复。
- 模板包导入中途失败时，确认已写入文件和元数据都能回滚；成功时检查所有图片 ID 重映射。
- 文章包导入确认图片文件、MediaAsset、HTML URL 映射一致；取消预览不应写入数据。
- 旧版 JSON 导入后再导出，确认旧字段保留、新字段有合理默认值，且重复导入不重复生成内置样式/分类。
- 对存储空间不足、只读目录、临时文件替换失败进行失败路径验证。

### 9.4 最新工作流

- 最新提交 `182f2b267f7ef231785fe18a92d65f0b1ca77780` 已触发新的 Kotlin 编译检查和 APK 构建。
- 新工作流尚未完成；不得沿用上一次成功构建结果来宣称最新补丁已编译。

## 8. 后续阶段执行门槛

- 阶段 B：选择状态、Range 保持、对象 ID、命令路由及撤销重做先通过专项测试。
- 阶段 C：底栏常驻、对象悬浮窗按类型出现、坐标与键盘避让、模板/收藏功能联动。
- 阶段 D：逐入口功能回归、文章数据回归、旧文章兼容、屏幕尺寸/键盘/滚动测试。
- 阶段 E：只有 D 通过后才做 UI 精修；保留现有排版页的布局体系与视觉风格。
- APK：CI 编译成功、产物存在、可安装并完成真机关键路径验证后，才能标记完成。
