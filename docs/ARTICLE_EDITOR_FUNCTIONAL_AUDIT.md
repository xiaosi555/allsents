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

4. **文字选区悬浮工具坐标可能过期**：原滚动监听只在图片或模块选中时重新上报位置，普通文字选区滚动后可能仍使用旧坐标。本轮已将画布滚动和窗口尺寸变化都接入选区位置刷新，需在真机上验证软键盘、滚动和选区跨屏时悬浮工具跟随正确。

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


## 10. 逐项回归记录（2026-11-25）

> 状态定义：**静态通过**=源码路径和关键调用已确认；**待运行**=需要 Android 运行环境/真机验证；**待修复**=已发现逻辑缺口，不能以静态通过关闭。

| 回归项 | 静态检查点 | 当前结论 | 运行验收步骤 |
|---|---|---|---|
| 新建文章 | `newArticle()` 生成 UUID、重置元信息和正文；`saveDocument()` 写入 `ArticleDocument` | 静态通过；保存失败反馈路径已修正，待新构建验证 | 新建空白文章→输入标题/正文→保存→返回列表→重启后检查仍存在 |
| 编辑文章 | `saveDocument()` 读取 WebView 实际 HTML，比较正文和元信息后调用 `vm.saveArticle` | 静态通过；保存失败时应保持 dirty 状态，待新构建验证 | 修改正文、摘要、作者、分类、标签、封面和状态，逐项保存并重启核对 |
| 复制文章 | 复制时生成新 ID、标题追加“（副本）”，调用 `saveArticle`；HTML 和素材 ID 目前沿用原文 | 静态通过；共享素材引用策略需运行确认 | 复制含图片文章，分别修改副本与原文，确认互不覆盖且图片都能显示 |
| 删除文章 | `deleteArticle` 同时删除文章和该文章的版本快照；素材文件不在此处物理删除 | 静态通过；孤立素材清理策略待确认 | 删除含图片且有版本的文章，确认文章/版本消失，其他文章共享图片不受影响 |
| 恢复版本 | `restoreArticleRevision(revision): Boolean` 在恢复前将当前文章写入“恢复前自动快照”，再原子恢复正文和文章元信息；恢复结果受 `updateData` 持久化结果控制 | 静态通过；已补强 5 分钟合并窗口下的恢复前快照保护，待最新 APK 运行验收 | 连续编辑后 5 分钟内恢复旧版本，确认恢复前状态仍可找回；同时核对正文、封面、分类、标签、图片资源 |
| 图片引用 | 图片以 MediaAsset ID 映射到 `editor.local/assets/{id}`；删除保护覆盖当前正文/封面、历史版本正文/封面、样式 HTML/缩略图 | 静态通过；资源文件存在性、共享引用和恢复流程待运行 | 导入图片→插入正文→设封面→保存版本→尝试删除素材→恢复版本→导出/导入后检查图片 |
| HTML 导入/导出 | HTML 导入走清理流程；导出时从 WebView 取当前 HTML 并包装标题/元信息 | 静态通过；异常文件、中文、图片 URL 待运行 | 导入含脚本/事件属性/外链图片的 HTML，检查净化结果；导出后用浏览器打开 |
| Markdown 导入/导出 | 独立 Markdown importer/exporter，导出包含标题、副标题和元信息 | 静态通过；转换边界待运行 | 测试标题、列表、引用、表格、链接、图片和特殊字符往返 |
| 文章包导入/导出 | 包含文章元信息、HTML 和 Base64 图片；导入时重映射素材 ID，失败时清理已写入资源 | 静态通过；回滚及大文件边界待运行 | 导出带多张图片的文章包→新文章导入→核对资源映射；损坏包/超限包导入应无残留 |
| 文字选区悬浮工具栏 | TEXT_BLOCK/TEXT_RANGE/CARET 由 Bridge 回传；滚动和 resize 时刷新坐标 | 逻辑入口静态通过；坐标单位已修正，等待新构建和真机验证 | 选中跨行文字、折叠光标、软键盘弹出、上下滚动，确认工具栏贴近选区且不被键盘遮挡 |
| 图片选区悬浮工具栏 | 图片选择状态显示尺寸、裁切、外观、替换、说明、删除操作 | 静态通过；触屏选中和裁切交互待运行 | 选图、滚动、缩放、裁切、替换、删除，检查坐标和操作对象 |
| 组件/表格选区悬浮工具栏 | COMPONENT/TABLE/LAYOUT/MULTI_BLOCK 分派模块/表格/组合操作 | 静态通过；不同 DOM 结构和多选状态待运行 | 选中引用卡片、分割线、标题组件、表格、组合模块，检查工具栏类型及操作命中对象 |
| 底部工具栏常驻 | `!previewMode` 时画布下方独立渲染工具面板；选择工具栏作为画布覆盖层 | 静态通过；软键盘/小屏布局待运行 | 普通编辑、选中文本/图片/组件、多选、切换面板、滚动画布时检查底栏不消失、不遮挡输入 |

### 10.1 本轮新增代码修正

1. **选区坐标单位**：Stage C2 曾将 WebView 的 CSS px 再通过 Density 转成 dp。当前编辑器 viewport 使用 `device-width`，CSS px 对应 Compose dp；二次除以 density 会导致高密度屏幕坐标偏移。已将选区 y/height 改为直接按 dp 使用，仅 IME inset 继续由物理 px 转 dp。
2. **保存失败状态**：`updateData` 现在返回 Boolean；写盘失败时不提交内存态更新并反馈错误，`saveDocument` 仅在持久化成功后清除 dirty 状态或执行完成回调。
3. **恢复版本保护**：恢复旧版本前自动保存当前文章快照，避免 5 分钟自动快照合并窗口导致恢复前内容无法找回；版本列表仍限制为每篇文章最近 30 条。
4. **异步保存竞态**：异步保存回调不再将旧文章 HTML 写回当前编辑器，也不会在用户切换文章后错误标记新文章为已保存。
5. 上述修正均已进入 main 的最新构建流水线；本轮 Kotlin Compile Check 已通过，APK Build 仍在执行。

### 10.2 当前静态验收结论

- 文章增删改查的主要调用链已定位；文章复制生成新 ID，删除同时清除版本快照。
- 文章版本最多保留 30 条；自动快照有 5 分钟合并窗口，已在显式恢复版本前单独保存“恢复前自动快照”，但需真机验证恢复前后内容均可再次找回。
- 图片资源采用独立 MediaAsset 记录；文章复制沿用资源 ID，因此资源必须按共享引用管理，不能随文章删除直接物理清理。
- HTML、Markdown、文章包三条导入导出链路均存在；仅静态确认入口和数据处理代码，不代表导出文件已在外部应用验证。
- 底部工具栏在非预览状态常驻；悬浮工具栏按文字、图片、组件/表格/布局等选区状态分派。选区坐标已修正为 CSS px 到 Compose dp 的直接映射；坐标跟随、键盘避让及底栏常驻仍必须通过真机验证。


### 10.3 最新构建与最终源码核对（2026-11-25）

- Kotlin Compile Check：工作流 run `45614254038`，结论 **success**。
- APK Build：工作流 run `45614253917`，结论 **success**；`Build debug APK`、`Upload APK`、`Package patched native source`、`Upload patched native source` 均成功。
- 已下载并检查本轮两个产物：APK 压缩包内包含 `app-debug.apk`（19,312,914 bytes）；原生源码包内含本次构建后的完整 Android 工程源码。
- 对最终注入源码复核：`Store.loadData` 有备份恢复分支；`Store.saveData` 有临时文件、同步写入和备份替换；`AppViewModel.updateData` 返回持久化 Boolean；`restoreArticleRevision` 在恢复前创建“恢复前自动快照”；`saveDocument` 仅在写盘成功时清除 dirty 状态，并对异步回调检查文章 ID；选区 y/height 使用 dp 直接映射；底部工具栏仍在 `!previewMode` 下渲染。
- APK SHA-256：`f3440d248c90affdbebb227ab0ad84f2c02df1cd267261311f07fdefb26dbfd4`。
- **结论：静态检查与本轮构建通过；真机操作验收尚未执行。** 本记录不将真机项目标记为通过。


## 11. 秀米式独立编辑页面入口与功能缺口审计（2026-11-25）

### 11.1 页面入口修正

- 排版页顶部栏的文章编辑器图标必须紧邻「编辑」按钮左侧；不得放在「编辑」按钮右侧。
- 点击图标设置 `vm.screen = "article_editor"`，MainActivity 必须分派到 `XiumiArticleEditorScreen`。
- 编辑器返回操作必须回到 `layout`，不能回到「我的」或直接退出 APP。
- `ensure_article_editor_route.py` 已增加构建期强校验：图标存在、点击事件存在、图标在 Edit 按钮左侧、MainActivity 路由和返回路由存在、独立页面入口函数存在。
- 2026-11-25 已发现图标 modifier 使用了未导入的 `semantics` 扩展，造成 Kotlin 编译失败；已移除该 modifier，保留 Icon 自身的 contentDescription，等待最新工作流验证。

### 11.2 本轮新增编辑功能

- 分类面板由原有分类扩展为 12 类：文字、标题、图片、布局、卡片、组件、SVG、图层、图文收藏、图文模板、文档、画布。
- 新增「标题」和「卡片」专属面板，分别提供多种标题样式、引用/提示/重点/信息/作者/关注/时间轴/清单/图片说明卡片。
- 新增「画布」面板：内容宽度、画布背景、正文默认字号、行距、左右留白和重置操作。
- 模块属性由原来的内边距、背景、边框、圆角扩展为：宽度、内边距、上下间距、背景、边框、圆角、阴影、内容对齐、透明度；属性对话框支持滚动。
- 布局、SVG 面板当前仍以可插入预设结构为主；不得将预设数量等同于完整的自由布局/SVG 编辑器。

### 11.3 仍缺少或需要深化的功能项

| 优先级 | 缺口 | 当前状态 | 后续实现要求 |
|---|---|---|---|
| P0 | 入口点击及返回真机验收 | 构建期静态校验已增强 | 真机从排版页点击图标进入，编辑后返回排版页；连续进入/返回多次 |
| P0 | 编辑器首屏和画布可用性 | 独立页面及 WebView 画布已存在 | 验证首次进入、空白文章、键盘弹出、横竖屏和系统返回 |
| P1 | 真正的图层树 | 目前以选中模块、多选、上移/下移、复制/删除为主 | 显示所有顶层模块、名称/类型、选中定位、拖动排序、隐藏/显示、锁定/解锁 |
| P1 | 自由布局编辑器 | 当前提供双栏、三栏、图文混排等预设 | 支持列数、比例、间距、对齐、嵌套布局、拖拽调整宽度和实时预览 |
| P1 | 完整组件属性面板 | 本轮已增加宽度、间距、阴影、对齐、透明度 | 增加边框四边独立控制、背景渐变、背景图、圆角四角独立值、组件定位与层级 |
| P1 | 素材中心 | 图片素材库位于图片分类内；模板库独立 | 增加统一素材入口、图片/视频/音频分类、搜索、筛选、收藏、最近使用和资源引用检查 |
| P1 | SVG 深度编辑 | 当前有 SVG/HTML 交互预设 | 支持 SVG 文件导入、源码/预览切换、元素属性、点击事件、动画参数、序列帧和兼容性检查 |
| P2 | 组件拖拽与吸附 | 已有模块拖动和多选拖动基础 | 增加拖拽插入、边缘吸附、占位提示、拖动中自动滚动及撤销回退 |
| P2 | 右侧属性面板形态 | 目前主要通过弹窗和底部面板设置 | 手机端用可展开底部属性面板，平板/横屏再采用右侧属性栏；保持选中对象不丢失 |
| P2 | 快捷键与操作历史 | 有撤销/重做及历史栈 | 增加键盘快捷键、操作历史列表、批量撤销/重做、复制粘贴及跨文章剪贴板 |
| P2 | 微信发布兼容性 | 已有兼容检查和富文本复制 | 对 SVG、视频、音频、表格、外链图片和 CSS 属性生成逐项兼容报告，并在复制前给出修复建议 |

### 11.4 当前验收边界

- 构建期脚本检查只能证明代码入口与路由结构存在，不能证明设备上的点击区域、页面切换和返回手势没有问题。
- 当前画布属性修改、图层、布局、SVG、模板功能均需在真实 Android 设备上进行触摸操作回归。
- 最新代码修改必须以最新 commit 对应的 Kotlin Compile Check 和 APK Build 结果为准；此前成功构建的 APK 不代表后续提交已通过。
