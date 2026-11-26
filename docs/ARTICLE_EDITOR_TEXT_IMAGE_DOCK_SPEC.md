# 文章编辑器文字与图片底部工具栏专项设计

> 日期：2026-11-27  
> 适用页面：独立文章编辑器 `ArticleEditorScreen`  
> 主分支：`main`  
> 原则：保持现有暗色工具面板、底部导航和浮动工具窗的视觉体系；文字、图片和组件命令必须按选中对象类型路由，不跨类型误操作。

## 1. 现有工程与技术文件

| 文件 | 职责 |
|---|---|
| `native-overlay/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt` | Compose 面板、WebView 画布、选择回调、图片素材选择、文字/图片工具面板 |
| `native-overlay/apply_editor_bottom_nav_v2.py` | 对象类型底部导航、文字四个二级栏目、图片/组件导航入口 |
| `native-overlay/apply_editor_functional_v3.py` | 类型化剪贴板、文字/图片/组件操作、组件自由拖动、图片调整面板 |
| `native-overlay/apply_editor_functional_v4.py` | 文字输入法显式唤起、隐藏旧“文字2”一级入口、图片调整值同步、图片对象粘贴后重新选中 |
| `.github/workflows/android.yml` | APK 注入与打包 |
| `.github/workflows/android-compile-check.yml` | Kotlin 编译检查 |
| `docs/ARTICLE_EDITOR_INTERACTION_TECHNICAL_PLAN.md` | 编辑器交互技术方案 |
| `docs/ARTICLE_EDITOR_FUNCTIONAL_AUDIT.md` | 功能审计和回归记录 |

构建顺序必须保持：文章编辑器基础补丁 → Stage B/C2 → 底部导航 v2 → 功能 v3 → 功能 v4 → 最终状态栏处理 → Kotlin 编译/ APK 打包。v4 依赖 v2/v3 已注入的状态和函数，不能提前执行。

## 2. 文字底部导航

文字对象被选中时，底部导航按以下顺序显示：

1. **编辑**：恢复当前段落的编辑光标，打开输入法。
2. **字体**：打开同一文字二级面板并默认定位“字体”栏目。
3. **样式**：打开同一面板并定位“样式”栏目。
4. **排版**：打开同一面板并定位“排版”栏目。
5. **透明度**：打开同一面板并定位“透明度”栏目。
6. **存为模板**：将当前整段文字 HTML 作为收藏模板保存，归入“图文收藏”。
7. **顺序**：打开组件浮动工具，使用自由拖动/方向移动改变当前文字段落位置。
8. **对齐**：定位到“排版”栏目，水平对齐操作作用于当前整段段落，而不是只改局部字符。
9. **创建副本**：在当前段落之后插入副本；原下一段内容自然顺延。
10. **复制**：复制当前文字段落对象。
11. **复制样式**：复制当前段落的行内块级样式。
12. **粘贴**：按剪贴板类型粘贴文字对象或文字样式。
13. **多选**：进入/退出多选。
14. **锁定**：固定当前对象；锁定对象通过组件工具解锁后再编辑。

“字体/样式/排版/透明度”是同一个二级面板的四个栏目。旧的“文字2”不再作为一级导航项单独显示；文字工具栏中的入口设置目标栏目后打开面板。点击栏目时切换目标内容，不创建重复面板。

## 3. 图片底部导航

图片对象被选中时，底部导航按以下顺序显示：

1. **替换**：调用系统图片选择器替换当前图片源。
2. **裁剪**：进入现有比例裁切、位置微调和像素裁切工具。
3. **调色**：亮度、对比度、饱和度滑块实时预览，松手后提交历史。
4. **透明度**：透明度滑块实时预览，松手后提交历史。
5. **边框**：细边框、强调边框、无边框。
6. **圆角**：圆角滑块实时预览，松手后提交历史。
7. **阴影**：轻/中/强/无阴影预设。
8. **翻转**：水平翻转、垂直翻转。
9. **对齐**：图片左对齐、居中、右对齐。
10. **复制**：复制图片对象。
11. **复制样式**：复制宽度、裁剪适配、位置、边框、圆角、阴影、透明度、滤镜和变换。
12. **粘贴**：若剪贴板是图片对象则插入图片副本；若是图片样式则应用样式，不允许把文字对象粘贴进图片对象。
13. **设为背景图**：将当前图片设为所在容器背景。

图片滑块必须在图片选中时从该图片的计算样式同步初始值，不能始终使用固定默认值，否则再次打开面板会错误覆盖原调整。

## 4. 对象类型与剪贴板约束

- 文字导航只允许文字段落和文字样式。
- 图片导航只允许图片对象和图片样式。
- 组件工具可处理当前选中的文字、图片或组件。
- 剪贴板区分 `OBJECT`、`TEXT_STYLE`、`IMAGE_STYLE`。
- 图片对象粘贴后应立即成为新的当前选中图片，继续编辑时命中新副本。
- 锁定对象的修改、删除、移动和样式操作必须被拒绝；组件工具只允许执行解锁操作。

## 5. 技术依据

- WebView 画布使用 DOM Selection/Range 保留真实文字选区；整段文字操作需要在无字符选区时回退到活动段落。参考 [MDN Selection API](https://developer.mozilla.org/en-US/docs/Web/API/Selection_API)。
- 对象复制和样式复制使用不同剪贴板类型；系统剪贴板可支持多种 MIME 表示，但本编辑器内部仍需类型校验。参考 [MDN Clipboard API](https://developer.mozilla.org/en-US/docs/Web/API/Clipboard_API)。
- 图片调色采用 CSS `filter` 的 brightness/contrast/saturate；图片透明度使用 opacity，裁剪显示由 object-fit/object-position 控制。参考 [MDN filter](https://developer.mozilla.org/en-US/docs/Web/CSS/filter)、[object-fit](https://developer.mozilla.org/en-US/docs/Web/CSS/object-fit)、[object-position](https://developer.mozilla.org/en-US/docs/Web/CSS/object-position)。
- “编辑”需要真实唤起 Android 输入法：WebView 获得焦点后请求 `InputMethodManager.showSoftInput`，不能只调用 DOM `focus()` 就假定键盘一定出现。参考 [Android 输入法可见性指南](https://developer.android.com/develop/ui/views/touch-and-input/keyboard-input/visibility)。

## 6. 本轮代码整改与验证

- [x] 新增 v4 构建注入脚本，并加入 APK 与 Kotlin 编译两个工作流。
- [x] 文字“编辑”增加 Android 输入法显式请求。
- [x] 隐藏旧“文字2”一级入口，保留四个栏目作为二级导航。
- [x] 图片选中时读取亮度、对比度、饱和度、透明度、圆角并同步 Compose 滑块。
- [x] 图片对象粘贴后移除旧选择标记/对象 ID，并将新图片设为活动选中对象。
- [ ] 等待最新主分支 Kotlin 编译检查。
- [ ] 等待最新主分支 APK 构建及产物确认。
- [ ] 真机逐项验证软键盘、文字样式/整段对齐、模板收藏回显、图片裁剪/调色/透明度/边框/圆角/阴影/翻转/对齐、两种剪贴板、锁定/解锁。
- [ ] 真机确认自由拖动跨段落、跨列时不破坏表格和嵌套布局。

> 构建通过仅证明注入源码可编译和 APK 可打包；没有真机实测前，不将触控、IME、剪贴板或图像显示标记为运行验收通过。
