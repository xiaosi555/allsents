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

## 5. 当前构建阻塞

最近一次已检查的 CI 构建在 `ArticleEditorScreen.kt` 中因 `LocalDensity` 未解析及 `toDp` 调用无法解析而失败。错误位于阶段 C2 悬浮工具定位的 dp 坐标换算附近。优先核查是否缺少 `androidx.compose.ui.platform.LocalDensity` 导入，并在修复后重新构建；不能在构建通过前进入 APK 交付验收。

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

## 8. 后续阶段执行门槛

- 阶段 B：选择状态、Range 保持、对象 ID、命令路由及撤销重做先通过专项测试。
- 阶段 C：底栏常驻、对象悬浮窗按类型出现、坐标与键盘避让、模板/收藏功能联动。
- 阶段 D：逐入口功能回归、文章数据回归、旧文章兼容、屏幕尺寸/键盘/滚动测试。
- 阶段 E：只有 D 通过后才做 UI 精修；保留现有排版页的布局体系与视觉风格。
- APK：CI 编译成功、产物存在、可安装并完成真机关键路径验证后，才能标记完成。
