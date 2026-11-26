package com.shiwanju.app.ui

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Handler
import android.os.Looper
import android.content.ClipData
import android.content.ClipboardManager
import android.content.ComponentCallbacks2
import android.content.Context
import android.content.res.Configuration
import android.util.Base64
import android.webkit.JavascriptInterface
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.Image
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ArrowBack
import androidx.compose.material.icons.outlined.Undo
import androidx.compose.material.icons.outlined.Redo
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Check
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.window.Popup
import androidx.compose.ui.window.PopupProperties
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import java.io.File
import java.util.Locale
import java.text.SimpleDateFormat
import java.util.Date
import com.shiwanju.app.data.ArticleDocument
import com.shiwanju.app.data.ArticleRevision
import com.shiwanju.app.data.MediaAsset
import com.shiwanju.app.data.StyleModule
import org.json.JSONObject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private fun captureTemplateThumbnail(view: WebView, context: Context, template: StyleModule, vm: AppViewModel) {
    if (template.thumbnail.isNotBlank() || view.width <= 0 || view.height <= 0) return
    runCatching {
        val source = Bitmap.createBitmap(view.width, view.height, Bitmap.Config.ARGB_8888)
        view.draw(android.graphics.Canvas(source))
        val targetWidth = 320
        val targetHeight = (source.height * targetWidth.toFloat() / source.width).toInt().coerceIn(1, 640)
        val scaled = Bitmap.createScaledBitmap(source, targetWidth, targetHeight, true)
        if (scaled !== source) source.recycle()
        val mediaDir = File(context.filesDir, "article_media")
        if (!mediaDir.exists() && !mediaDir.mkdirs()) error("无法创建素材目录")
        val id = vm.newId()
        val file = File(mediaDir, "template_preview_$id.jpg")
        file.outputStream().use { output ->
            if (!scaled.compress(Bitmap.CompressFormat.JPEG, 68, output)) error("缩略图压缩失败")
        }
        if (!scaled.isRecycled) scaled.recycle()
        val asset = MediaAsset(id, "template_preview_$id.jpg", "image/jpeg", "article_media/" + file.name, file.length(), System.currentTimeMillis().toString())
        vm.saveMediaAsset(asset)
        vm.saveStyle(template.copy(thumbnail = id))
    }.onFailure { android.util.Log.w("ArticleEditor", "模板缩略图生成失败", it) }
}

private class ArticleEditorBridge(private val onChange: (String) -> Unit, private val onBlock: (String) -> Unit, private val onImage: (String) -> Unit, private val onText: (Boolean) -> Unit) {
    private val main = Handler(Looper.getMainLooper())
    @JavascriptInterface fun changed(value: String) { main.post { onChange(value) } }
    @JavascriptInterface fun blockSelected(value: String) { main.post { onBlock(value) } }
    @JavascriptInterface fun imageSelected(value: String) { main.post { onImage(value) } }
    @JavascriptInterface fun textSelected(value: String) { main.post { onText(value == "1") } }
}

private enum class EditorPanel(val label: String) {
    TEXT("文字"), TEXT2("文字2"), TITLE("标题"), IMAGE("图片"), LAYOUT("布局"), CARD("卡片"), COMPONENT("组件"), SVG("SVG"), LAYER("图层"), STYLE("图文收藏"), TEMPLATE("图文模板"), DOCUMENT("文档"), CANVAS("画布")
}

private val LocalEditorToolDark = compositionLocalOf { false }
private val templateSubPanels = setOf(EditorPanel.TITLE, EditorPanel.CARD, EditorPanel.IMAGE, EditorPanel.LAYOUT, EditorPanel.SVG, EditorPanel.COMPONENT)

private data class EditorLayerItem(
    val id: String,
    val tag: String,
    val name: String,
    val visible: Boolean,
    val locked: Boolean
)


@Composable
private fun CompactEditorSlider(
    value: Float,
    onValueChange: (Float) -> Unit,
    valueRange: ClosedFloatingPointRange<Float>,
    modifier: Modifier = Modifier
) {
    Slider(
        value = value,
        onValueChange = onValueChange,
        valueRange = valueRange,
        modifier = modifier.height(20.dp),
        colors = SliderDefaults.colors(
            thumbColor = Color.White,
            activeTrackColor = Color(0xFF4A91FF),
            inactiveTrackColor = Color(0xFF4A4A4A),
            activeTickColor = Color.Transparent,
            inactiveTickColor = Color.Transparent
        )
    )
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Text2ColorRow(styleTab: String, selectedColor: String, blur: Float, glowWidth: Float, colors: List<String>, onColor: (String) -> Unit, onClear: () -> Unit, onEyedropper: () -> Unit, onGradient: () -> Unit) {
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(7.dp), verticalAlignment = Alignment.CenterVertically) {
            listOf("禁用", "取色", "渐变").forEachIndexed { index, label ->
                Box(Modifier.size(26.dp).clip(CircleShape).background(Color(0xFF303030)).clickable {
                    when (index) {
                        0 -> onClear()
                        1 -> onEyedropper()
                        else -> {
                            onGradient()
                            
                            
                    }
                    }
                }, contentAlignment = Alignment.Center) {
                    Text(if (index == 0) "／" else if (index == 1) "⌁" else "✦", color = Color.White, fontSize = 16.sp)
                }
            }
            colors.forEach { color ->
                Box(
                    Modifier.size(28.dp).clip(CircleShape)
                        .background(Color(android.graphics.Color.parseColor(color)))
                        .then(if (selectedColor == color) Modifier.border(2.dp, Color.White, CircleShape) else Modifier.border(1.dp, Color(0xFF777777), CircleShape))
                        .clickable {
                            onColor(color)
                        }
                )
            }
        }
    }


@Composable
private fun Text2ParameterRow(label: String, value: Float, min: Float, max: Float, suffix: String, onValue: (Float) -> Unit) {
        Row(Modifier.fillMaxWidth().height(26.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(label, Modifier.width(52.dp), color = Color(0xFFCCCCCC), fontSize = 11.sp, maxLines = 1)
            CompactEditorSlider(value = value, onValueChange = onValue, valueRange = min..max, modifier = Modifier.weight(1f))
            Text(value.toInt().toString() + suffix, Modifier.width(40.dp), color = Color.White, fontSize = 10.sp, textAlign = androidx.compose.ui.text.style.TextAlign.End)
    }
    }

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun Text2EditorPanel(
    onCommand: (String, String?) -> Unit,
    onApplyCss: (String, String) -> Unit,
    onApplyColor: (String, Boolean) -> Unit,
    onEyedropper: () -> Unit
) {
    var mainTab by remember { mutableStateOf("字体") }
    var styleTab by remember { mutableStateOf("文本") }
    var selectedColor by remember { mutableStateOf("#222222") }
    var fontSize by remember { mutableFloatStateOf(18f) }
    var opacity by remember { mutableFloatStateOf(100f) }
    var strokeWidth by remember { mutableFloatStateOf(2f) }
    var blur by remember { mutableFloatStateOf(8f) }
    var distance by remember { mutableFloatStateOf(4f) }
    var angle by remember { mutableFloatStateOf(45f) }
    var glowWidth by remember { mutableFloatStateOf(8f) }
    var radius by remember { mutableFloatStateOf(8f) }
    var lineSpacing by remember { mutableFloatStateOf(1.6f) }
    var letterSpacing by remember { mutableFloatStateOf(0f) }
    var outlineMode by remember { mutableStateOf("单层") }
    var selectedAlignment by remember { mutableIntStateOf(1) }
    val colors = listOf("#FF0000", "#000000", "#888888", "#FFFFFF", "#A64B3C", "#F04438", "#FF7F6B", "#E98BB7")


    Column(Modifier.fillMaxWidth().fillMaxHeight().background(Color(0xFF181818)), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Row(Modifier.fillMaxWidth().height(38.dp), horizontalArrangement = Arrangement.spacedBy(22.dp), verticalAlignment = Alignment.CenterVertically) {
            listOf("字体", "样式", "排版").forEach { tab ->
                Column(Modifier.clickable { mainTab = tab }.padding(vertical = 4.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(tab, color = if (mainTab == tab) Color.White else Color(0xFF888888), fontSize = 14.sp, fontWeight = if (mainTab == tab) FontWeight.Bold else FontWeight.Normal)
                    Box(Modifier.padding(top = 4.dp).width(22.dp).height(3.dp).clip(RoundedCornerShape(4.dp)).background(if (mainTab == tab) Color(0xFF3987F7) else Color.Transparent))
                }
            }
        }
        if (mainTab == "样式") {
            Row(Modifier.fillMaxWidth().height(28.dp).horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(16.dp), verticalAlignment = Alignment.CenterVertically) {
                listOf("文本", "描边", "阴影", "发光", "背景").forEach { tab ->
                    Text(tab, Modifier.clickable { styleTab = tab }.padding(vertical = 4.dp), color = if (styleTab == tab) Color.White else Color(0xFF888888), fontSize = 12.sp, fontWeight = if (styleTab == tab) FontWeight.Bold else FontWeight.Normal)
                }
            }
        }
        Column(Modifier.fillMaxWidth().weight(1f).verticalScroll(rememberScrollState()).padding(bottom = 4.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            if (mainTab == "字体") {
                Text("选择字体", color = Color(0xFFAAAAAA), fontSize = 11.sp)
                val fonts = listOf("系统默认", "微软雅黑", "苹方", "思源黑体", "宋体", "楷体", "仿宋", "黑体", "圆体", "衬线", "无衬线", "等宽")
                FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    fonts.forEach { font ->
                        Box(Modifier.weight(1f).widthIn(min = 76.dp).height(44.dp).clip(RoundedCornerShape(8.dp)).background(Color(0xFF303030))
                            .clickable { onCommand("fontName", when (font) { "宋体" -> "SimSun"; "楷体" -> "KaiTi"; "黑体", "微软雅黑" -> "Microsoft YaHei"; "仿宋" -> "FangSong"; "等宽" -> "monospace"; "衬线" -> "serif"; "无衬线" -> "sans-serif"; else -> "sans-serif" }) },
                            contentAlignment = Alignment.Center) { Text(font, color = Color.White, fontSize = 12.sp) }
                    }
                }
            } else if (mainTab == "样式") {
                if (styleTab == "描边") {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        listOf("单层", "多层").forEach { label ->
                            TextButton(onClick = { outlineMode = label }, contentPadding = PaddingValues(horizontal = 7.dp, vertical = 0.dp)) {
                                Text(label, color = if (outlineMode == label) Color.White else Color(0xFF888888), fontSize = 11.sp)
                            }
                        }
                    }
                }
                Text2ColorRow(styleTab, selectedColor, blur, glowWidth, colors, onColor = { color -> selectedColor = color; when (styleTab) { "描边" -> onApplyCss("-webkit-text-stroke-color", color); "阴影" -> onApplyCss("text-shadow", "1px 1px " + blur + "px " + color); "发光" -> onApplyCss("text-shadow", "0 0 " + glowWidth + "px " + color); "背景" -> onApplyColor(color, true); else -> onApplyColor(color, false) } }, onClear = { onApplyColor("transparent", styleTab == "背景") }, onEyedropper = onEyedropper, onGradient = { onApplyCss("background-image", "linear-gradient(90deg,#F04438,#F5C542,#159765,#3978B7,#8B5CF6)"); onApplyCss("-webkit-background-clip", "text"); onApplyCss("color", "transparent") })
                when (styleTab) {
                    "文本" -> {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            listOf("B" to "粗体", "I" to "斜体", "U" to "下划线", "S" to "删除线").forEachIndexed { index, item ->
                                Column(Modifier.weight(1f).clip(RoundedCornerShape(7.dp)).background(Color(0xFF303030)).clickable {
                                    onCommand(listOf("bold", "italic", "underline", "strikeThrough")[index], null)
                                }.padding(vertical = 6.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                                    Text(item.first, color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                                    Text(item.second, color = Color(0xFFAAAAAA), fontSize = 9.sp)
                                }
                            }
                        }
                        Text2ParameterRow("字号", fontSize, 8f, 72f, "px") { fontSize = it; onApplyCss("font-size", it.toInt().toString() + "px") }
                        Row(Modifier.fillMaxWidth().height(28.dp), verticalAlignment = Alignment.CenterVertically) {
                            Text("字号微调", color = Color(0xFFCCCCCC), fontSize = 11.sp)
                            Spacer(Modifier.weight(1f))
                            TextButton(onClick = { fontSize = (fontSize - 1).coerceAtLeast(8f); onApplyCss("font-size", fontSize.toInt().toString() + "px") }, contentPadding = PaddingValues(horizontal = 5.dp, vertical = 0.dp)) { Text("−", color = Color.White) }
                            Text(fontSize.toInt().toString(), color = Color.White, fontSize = 12.sp)
                            TextButton(onClick = { fontSize = (fontSize + 1).coerceAtMost(72f); onApplyCss("font-size", fontSize.toInt().toString() + "px") }, contentPadding = PaddingValues(horizontal = 5.dp, vertical = 0.dp)) { Text("＋", color = Color.White) }
                        }
                        Text2ParameterRow("透明度", opacity, 0f, 100f, "%") { opacity = it; onApplyCss("opacity", (it / 100f).toString()) }
                    }
                    "描边" -> {
                        Text2ParameterRow("粗细", strokeWidth, 0f, 12f, "px") { strokeWidth = it; onApplyCss("-webkit-text-stroke-width", it.toString() + "px") }
                        Text2ParameterRow("透明度", opacity, 0f, 100f, "%") { opacity = it; onApplyCss("opacity", (it / 100f).toString()) }
                    }
                    "阴影" -> {
                        Text2ParameterRow("模糊", blur, 0f, 30f, "px") { blur = it; onApplyCss("text-shadow", "1px 1px " + it + "px " + selectedColor) }
                        Text2ParameterRow("距离", distance, 0f, 30f, "px") { distance = it; onApplyCss("text-shadow", it.toString() + "px " + it + "px " + blur + "px " + selectedColor) }
                        Text2ParameterRow("角度", angle, 0f, 360f, "°") { angle = it; val rad = Math.toRadians(it.toDouble()); onApplyCss("text-shadow", (kotlin.math.cos(rad) * distance).toString() + "px " + (kotlin.math.sin(rad) * distance) + "px " + blur + "px " + selectedColor) }
                        Text2ParameterRow("透明度", opacity, 0f, 100f, "%") { opacity = it; onApplyCss("opacity", (it / 100f).toString()) }
                    }
                    "发光" -> {
                        Text2ParameterRow("粗细", glowWidth, 0f, 30f, "px") { glowWidth = it; onApplyCss("text-shadow", "0 0 " + it + "px " + selectedColor) }
                        Text2ParameterRow("透明度", opacity, 0f, 100f, "%") { opacity = it; onApplyCss("opacity", (it / 100f).toString()) }
                    }
                    "背景" -> {
                        Text2ParameterRow("透明度", opacity, 0f, 100f, "%") { opacity = it; onApplyCss("background-color", selectedColor) }
                        Text2ParameterRow("圆角", radius, 0f, 40f, "px") { radius = it; onApplyCss("border-radius", it.toString() + "px") }
                    }
                }
            } else {
                val alignItems = listOf("居左", "居中", "居右", "水平对齐", "居顶", "居中", "居底", "垂直对齐")
                FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    alignItems.forEachIndexed { index, label ->
                        Column(Modifier.weight(1f).widthIn(min = 62.dp).clip(RoundedCornerShape(7.dp))
                            .background(if (selectedAlignment == index) Color.Black else Color(0xFF303030))
                            .clickable {
                                selectedAlignment = index
                                when (index) {
                                    0 -> onCommand("justifyLeft", null)
                                    1 -> onCommand("justifyCenter", null)
                                    2 -> onCommand("justifyRight", null)
                                    3 -> onCommand("justifyFull", null)
                                    4 -> onApplyCss("vertical-align", "top")
                                    5 -> onApplyCss("vertical-align", "middle")
                                    6 -> onApplyCss("vertical-align", "bottom")
                                    else -> onApplyCss("vertical-align", "middle")
                                }
                            }.padding(vertical = 7.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                            Text(listOf("☰", "≡", "☷", "↔", "↑", "↕", "↓", "↕")[index], color = Color.White, fontSize = 16.sp)
                            Text(label, color = Color(0xFFDDDDDD), fontSize = 9.sp)
                        }
                    }
                }
                Text2ParameterRow("行间距", lineSpacing, 1f, 3f, "x") { lineSpacing = it; onApplyCss("line-height", it.toString()) }
                Text2ParameterRow("字间距", letterSpacing, -2f, 12f, "px") { letterSpacing = it; onApplyCss("letter-spacing", it.toString() + "px") }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun ArticleEditorScreen(vm: AppViewModel, onBack: () -> Unit) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    var articleId by remember { mutableStateOf(vm.newId()) }
    var title by remember { mutableStateOf("未命名文章") }
    var html by remember { mutableStateOf("<p><br></p>") }
    var editor by remember { mutableStateOf<WebView?>(null) }
    var webReady by remember { mutableStateOf(false) }
    var activePanel by remember { mutableStateOf(EditorPanel.TEXT) }
    var templateSubPanel by remember { mutableStateOf(EditorPanel.TITLE) }
    var showTemplateSubnav by remember { mutableStateOf(false) }
    var showInsertLauncherMenu by remember { mutableStateOf(false) }
    var insertLauncherOffset by remember { mutableStateOf(Offset.Zero) }
    var showToolPopup by remember { mutableStateOf(false) }
    var toolPanelHeightDp by remember { mutableFloatStateOf(100f) }
    val toolPanelDensity = LocalDensity.current
    val animatedToolPanelHeight = toolPanelHeightDp.coerceIn(100f, 400f).dp
    var showCanvasPopup by remember { mutableStateOf(false) }
    var toolPopupOffset by remember { mutableStateOf(Offset.Zero) }
    var activeCategory by remember { mutableStateOf("") }
    var showArticleList by remember { mutableStateOf(false) }
    var showLink by remember { mutableStateOf(false) }
    var linkInsertType by remember { mutableStateOf("link") }
    var showImage by remember { mutableStateOf(false) }
    var dialogValue by remember { mutableStateOf("") }
    var saved by remember { mutableStateOf(false) }
    var previewMode by remember { mutableStateOf(false) }
    var showMoreTools by remember { mutableStateOf(false) }
    var pendingSave by remember { mutableIntStateOf(0) }
    var searchText by remember { mutableStateOf("") }
    var articleFilter by remember { mutableStateOf("全部") }
    var mediaSearchText by remember { mutableStateOf("") }
    var showDeleteConfirm by remember { mutableStateOf<ArticleDocument?>(null) }
    var showRevisionList by remember { mutableStateOf(false) }
    var revisionPreview by remember { mutableStateOf<ArticleRevision?>(null) }
    var showArticleInfo by remember { mutableStateOf(false) }
    var articleInfoSnapshot by remember { mutableStateOf(emptyList<String>()) }
    var fullTemplateConfirm by remember { mutableStateOf<StyleModule?>(null) }
    var showCompatibilityReport by remember { mutableStateOf(false) }
    var showFindReplace by remember { mutableStateOf(false) }
    var showHtmlImportPreview by remember { mutableStateOf(false) }
    var pendingImportedHtml by remember { mutableStateOf("") }
    var showArticlePackagePreview by remember { mutableStateOf(false) }
    var pendingArticlePackageRaw by remember { mutableStateOf("") }
    var findValue by remember { mutableStateOf("") }
    var replaceValue by remember { mutableStateOf("") }
    var compatibilityWarnings by remember { mutableStateOf(emptyList<String>()) }
    var subtitle by remember { mutableStateOf("") }
    var summary by remember { mutableStateOf("") }
    var author by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("") }
    var tagsText by remember { mutableStateOf("") }
    var articleStatus by remember { mutableStateOf("draft") }
    var coverAssetId by remember { mutableStateOf("") }
    var pendingExportHtml by remember { mutableStateOf("") }
    var pendingExportMarkdown by remember { mutableStateOf("") }
    var pendingExportArticleJson by remember { mutableStateOf("") }
    var pendingExportStyleJson by remember { mutableStateOf("") }
    var pendingImageGroupCount by remember { mutableIntStateOf(2) }
    var selectedBlockHtml by remember { mutableStateOf("") }
    var layerItems by remember { mutableStateOf(emptyList<EditorLayerItem>()) }
    var showBlockProperties by remember { mutableStateOf(false) }
    var showLayoutBuilder by remember { mutableStateOf(false) }
    var layoutBuilderColumns by remember { mutableIntStateOf(2) }
    var layoutBuilderGap by remember { mutableStateOf("12") }
    var layoutBuilderRatios by remember { mutableStateOf("1,1") }
    var layoutBuilderBackground by remember { mutableStateOf("#F4F7F5") }
    var layoutBuilderImageAssetId by remember { mutableStateOf("") }

    var blockPadding by remember { mutableStateOf("14px") }
    var blockMargin by remember { mutableStateOf("12px") }
    var blockWidth by remember { mutableStateOf("100%") }
    var blockBackground by remember { mutableStateOf("#F4F7F5") }
    var blockBorder by remember { mutableStateOf("#E2E9E4") }
    var blockBorderWidth by remember { mutableStateOf("1") }
    var blockBorderStyle by remember { mutableStateOf("solid") }
    var blockRadius by remember { mutableStateOf("8px") }
    var blockShadow by remember { mutableStateOf("none") }
    var blockAlign by remember { mutableStateOf("left") }
    var blockOpacity by remember { mutableStateOf("100") }
    var multiSelectMode by remember { mutableStateOf(false) }
    var selectedImageHtml by remember { mutableStateOf("") }
    var selectedTextActive by remember { mutableStateOf(false) }
    var floatingToolbarRequest by remember { mutableStateOf("") }
    var floatingMenu by remember { mutableStateOf("") }
    var floatingToolbarOffset by remember { mutableStateOf(Offset.Zero) }
    var showImageAlt by remember { mutableStateOf(false) }
    var showCustomImageCrop by remember { mutableStateOf(false) }
    var customCropAsset by remember { mutableStateOf<MediaAsset?>(null) }
    var cropLeft by remember { mutableFloatStateOf(0.05f) }
    var cropTop by remember { mutableFloatStateOf(0.05f) }
    var cropWidth by remember { mutableFloatStateOf(0.90f) }
    var cropHeight by remember { mutableFloatStateOf(0.90f) }
    var previewAsset by remember { mutableStateOf<MediaAsset?>(null) }
    var templateSearchText by remember { mutableStateOf("") }
    var templateLibraryTab by remember { mutableStateOf("full") }
    var favoriteTemplatesOnly by remember { mutableStateOf(false) }
    var templateTagFilter by remember { mutableStateOf("") }
    var templateKindFilter by remember { mutableStateOf("") }
    var templateSortByName by remember { mutableStateOf(false) }
    var templatePreview by remember { mutableStateOf<StyleModule?>(null) }
    var editingTemplate by remember { mutableStateOf<StyleModule?>(null) }
    var editingTemplateContent by remember { mutableStateOf<StyleModule?>(null) }
    var templateHtmlDraft by remember { mutableStateOf("") }
    var deletingTemplate by remember { mutableStateOf<StyleModule?>(null) }
    val categories = vm.data.styles.map { it.category.trim() }.filter { it.isNotEmpty() }.distinct()
    val categoryStyles = vm.data.styles.filter { it.category == activeCategory && it.isFavorite }
    val filteredArticles = vm.data.articles.filter { article ->
        (articleFilter == "全部" || (articleFilter == "草稿" && article.status != "complete") || (articleFilter == "已完成" && article.status == "complete") || (articleFilter == "收藏" && article.isFavorite)) &&
            (searchText.isBlank() || article.title.contains(searchText, true) || article.summary.contains(searchText, true) || article.tags.any { tag -> tag.contains(searchText, true) } || article.category.contains(searchText, true))
    }.sortedByDescending { it.updatedAt }
    val filteredMediaAssets = vm.data.mediaAssets.filter { mediaSearchText.isBlank() || it.fileName.contains(mediaSearchText, true) || it.mimeType.contains(mediaSearchText, true) }.sortedByDescending { it.createdAt }
    val templateLibraryItems = vm.data.styles.filter { style ->
        when (templateLibraryTab) {
            "full" -> style.type == "full" || style.category == "整篇模板"
            "combination" -> style.type == "combination"
            else -> style.type != "full" && style.category != "整篇模板" && style.type != "combination"
        }
    }
    val availableTemplateTags = templateLibraryItems.flatMap { it.tags }.map { it.trim() }.filter { it.isNotEmpty() }.distinct().sorted()
    val filteredTemplates = templateLibraryItems.filter { style ->
        val kindMatch = when (templateKindFilter) {
            "标题" -> style.category.contains("标题") || style.name.contains("标题") || style.tags.any { it.contains("标题") }
            "卡片" -> listOf("卡片", "引用", "提示").any { key -> style.category.contains(key) || style.name.contains(key) || style.tags.any { it.contains(key) } }
            "图片" -> listOf("图片", "图集", "相册").any { key -> style.category.contains(key) || style.name.contains(key) || style.tags.any { it.contains(key) } }
            "布局" -> listOf("布局", "整篇", "组合", "分栏").any { key -> style.category.contains(key) || style.name.contains(key) || style.tags.any { it.contains(key) } }
            else -> true
        }
        kindMatch && (!favoriteTemplatesOnly || style.isFavorite) &&
            (templateTagFilter.isBlank() || style.tags.any { tag -> tag.equals(templateTagFilter, true) }) &&
            (templateSearchText.isBlank() || style.name.contains(templateSearchText, true) || style.tags.any { tag -> tag.contains(templateSearchText, true) })
    }
        .let { list -> if (templateSortByName) list.sortedBy { it.name.lowercase(Locale.ROOT) } else list.sortedWith(compareByDescending<StyleModule> { it.isFavorite }.thenByDescending { it.updatedAt }) }
    val currentArticle = vm.data.articles.firstOrNull { it.id == articleId }
    val previewBitmap = remember(previewAsset?.id) {
        previewAsset?.let { asset ->
            runCatching {
                val root = File(context.filesDir, "article_media").canonicalFile
                val file = File(context.filesDir, asset.relativePath).canonicalFile
                if (file.path.startsWith(root.path + File.separator) && file.isFile) decodeArticleAssetPreview(file) else null
            }.getOrNull()
        }
    }

    val customCropPreviewBitmap = remember(customCropAsset?.id) {
        customCropAsset?.let { asset ->
            runCatching {
                val root = File(context.filesDir, "article_media").canonicalFile
                val file = File(context.filesDir, asset.relativePath).canonicalFile
                if (file.path.startsWith(root.path + File.separator) && file.isFile) decodeArticleAssetPreview(file) else null
            }.getOrNull()
        }
    }

    val pageBg = AppColors.Bg
    val ink = AppColors.TextMain
    val accent = AppColors.Theme
    val accentHex = "#%06X".format(Locale.ROOT, 0xFFFFFF and accent.toArgb())

    fun refreshLayerItems() {
        editor?.evaluateJavascript("getLayerList()") { raw ->
            val payload = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull()
            val array = runCatching { org.json.JSONArray(payload ?: "[]") }.getOrNull()
            layerItems = if (array == null) emptyList() else (0 until array.length()).mapNotNull { index ->
                val item = array.optJSONObject(index) ?: return@mapNotNull null
                EditorLayerItem(
                    id = item.optString("id"),
                    tag = item.optString("tag"),
                    name = item.optString("name"),
                    visible = item.optBoolean("visible", true),
                    locked = item.optBoolean("locked", false)
                )
            }
        }
    }
    LaunchedEffect(activePanel, webReady) {
        if (activePanel == EditorPanel.LAYER && webReady) refreshLayerItems()
    }
    fun runJs(script: String) {
        editor?.evaluateJavascript(script, null)
        saved = false
        pendingSave++
    }
    fun command(name: String, value: String? = null) {
        val arg = value?.let { JSONObject.quote(it) } ?: "null"
        runJs("restoreSelection();document.execCommand('$name',false,$arg);saveSelection();document.getElementById('editor').focus();")
    }
    fun insert(fragment: String) {
        runJs("restoreSelection();insertHtml(${JSONObject.quote(fragment)});saveSelection();document.getElementById('editor').focus();")
    }
    fun cropSelectedImagePixels(targetRatio: Float) {
        val match = Regex("""https://editor\.local/assets/([A-Za-z0-9_-]+)""").find(selectedImageHtml)
        val asset = match?.groupValues?.getOrNull(1)?.let { id -> vm.data.mediaAssets.firstOrNull { it.id == id } }
        if (asset == null) {
            vm.toast("像素裁切目前仅支持已导入素材库的本地图片")
            return
        }
        coroutineScope.launch {
            try {
                val mediaRoot = File(context.filesDir, "article_media").canonicalFile
                val source = File(context.filesDir, asset.relativePath).canonicalFile
                if (!source.path.startsWith(mediaRoot.path + File.separator) || !source.isFile) error("原图片文件不存在")
                var newId = vm.newId()
                while (vm.data.mediaAssets.any { it.id == newId }) newId = vm.newId()
                val png = asset.mimeType.equals("image/png", true)
                val ext = if (png) "png" else "jpg"
                val newName = "crop_$newId.$ext"
                val target = File(mediaRoot, newName)
                val position = Regex("""object-position\s*:\s*([\d.]+)%\s+([\d.]+)%""").find(selectedImageHtml)
                val positionX = (position?.groupValues?.getOrNull(1)?.toFloatOrNull() ?: 50f) / 100f
                val positionY = (position?.groupValues?.getOrNull(2)?.toFloatOrNull() ?: 50f) / 100f
                val dimensions = withContext(Dispatchers.IO) { cropArticleImageFile(source, target, targetRatio, png, positionX, positionY) }
                val mime = if (png) "image/png" else "image/jpeg"
                vm.saveMediaAsset(MediaAsset(newId, newName, mime, "article_media/$newName", target.length(), System.currentTimeMillis().toString()))
                runJs("replaceSelectedImage('https://editor.local/assets/$newId',${JSONObject.quote(newName)})")
                vm.toast("已完成像素裁切：${dimensions.first} × ${dimensions.second}")
            } catch (error: Exception) {
                vm.toast("像素裁切失败：${error.message ?: "图片处理错误"}")
            }
        }
    }

    fun openCustomImageCrop() {
        val match = Regex("""https://editor\.local/assets/([A-Za-z0-9_-]+)""").find(selectedImageHtml)
        val asset = match?.groupValues?.getOrNull(1)?.let { id -> vm.data.mediaAssets.firstOrNull { it.id == id } }
        if (asset == null) {
            vm.toast("自定义像素裁切仅支持已导入素材库的本地图片")
            return
        }
        customCropAsset = asset
        cropLeft = 0.05f; cropTop = 0.05f; cropWidth = 0.90f; cropHeight = 0.90f
        showCustomImageCrop = true
    }

    fun applyCustomImageCrop() {
        val asset = customCropAsset ?: return
        coroutineScope.launch {
            try {
                val mediaRoot = File(context.filesDir, "article_media").canonicalFile
                val source = File(context.filesDir, asset.relativePath).canonicalFile
                if (!source.path.startsWith(mediaRoot.path + File.separator) || !source.isFile) error("原图片文件不存在")
                var newId = vm.newId()
                while (vm.data.mediaAssets.any { it.id == newId }) newId = vm.newId()
                val png = asset.mimeType.equals("image/png", true)
                val ext = if (png) "png" else "jpg"
                val newName = "crop_$newId.$ext"
                val target = File(mediaRoot, newName)
                val dimensions = withContext(Dispatchers.IO) {
                    cropArticleImageRectFile(source, target, cropLeft, cropTop, cropWidth, cropHeight, png)
                }
                val mime = if (png) "image/png" else "image/jpeg"
                vm.saveMediaAsset(MediaAsset(newId, newName, mime, "article_media/$newName", target.length(), System.currentTimeMillis().toString()))
                runJs("replaceSelectedImage('https://editor.local/assets/$newId',${JSONObject.quote(newName)})")
                showCustomImageCrop = false
                customCropAsset = null
                vm.toast("自定义裁切完成：${dimensions.first} × ${dimensions.second}")
            } catch (error: Exception) {
                vm.toast("自定义裁切失败：${error.message ?: "图片处理错误"}")
            }
        }
    }

    fun saveDocument(showToast: Boolean = false, onComplete: (() -> Unit)? = null) {
        val savingId = articleId
        val savingTitle = title.ifBlank { "未命名文章" }
        val savingSubtitle = subtitle
        val savingSummary = summary
        val savingAuthor = author
        val savingCategory = category
        val savingTags = tagsText.split(",").map { it.trim() }.filter { it.isNotEmpty() }
        val savingStatus = articleStatus
        val savingCoverAssetId = coverAssetId
        val savingIsFavorite = vm.data.articles.firstOrNull { it.id == articleId }?.isFavorite ?: false
        val view = editor
        if (view == null || !webReady) {
            val old = vm.data.articles.firstOrNull { it.id == savingId }
            val changed = old == null || old.title != savingTitle || old.html != html ||
                old.subtitle != savingSubtitle || old.summary != savingSummary || old.author != savingAuthor ||
                old.coverAssetId != savingCoverAssetId || old.category != savingCategory || old.tags != savingTags ||
                old.status != savingStatus || old.isFavorite != savingIsFavorite
            val persisted = if (changed) {
                val now = System.currentTimeMillis().toString()
                vm.saveArticle(ArticleDocument(savingId, savingTitle, html, old?.createdAt ?: now, now,
                    savingSubtitle, savingSummary, savingAuthor, savingCoverAssetId, savingCategory, savingTags,
                    savingStatus, html.replace(Regex("<[^>]*>"), "").length, savingIsFavorite))
            } else true
            saved = persisted
            if (persisted && showToast) vm.toast("文章已保存")
            if (persisted) onComplete?.invoke()
            return
        }
        view.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
            val current = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
            val old = vm.data.articles.firstOrNull { it.id == savingId }
            val changed = old == null || old.title != savingTitle || old.html != current ||
                old.subtitle != savingSubtitle || old.summary != savingSummary || old.author != savingAuthor ||
                old.coverAssetId != savingCoverAssetId || old.category != savingCategory || old.tags != savingTags ||
                old.status != savingStatus || old.isFavorite != savingIsFavorite
            val persisted = if (changed) {
                val now = System.currentTimeMillis().toString()
                vm.saveArticle(ArticleDocument(savingId, savingTitle, current, old?.createdAt ?: now, now,
                    savingSubtitle, savingSummary, savingAuthor, savingCoverAssetId, savingCategory, savingTags,
                    savingStatus, current.replace(Regex("<[^>]*>"), "").length, savingIsFavorite))
            } else true
            if (articleId == savingId) saved = persisted
            if (persisted && showToast) vm.toast("文章已保存")
            if (persisted) onComplete?.invoke()
        }
    }
    fun newArticle() {
        saveDocument()
        articleId = vm.newId()
        title = "未命名文章"
        subtitle = ""; summary = ""; author = ""; category = ""; tagsText = ""; articleStatus = "draft"; coverAssetId = ""
        html = "<p><br></p>"
        previewMode = false
        showArticleList = false
        if (webReady) editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(html)});setEditable(true);", null)
        saved = false
    }
    fun openArticle(article: ArticleDocument) {
        articleId = article.id
        title = article.title
        html = article.html
        subtitle = article.subtitle
        summary = article.summary
        author = article.author
        category = article.category
        tagsText = article.tags.joinToString(", ")
        articleStatus = article.status
        coverAssetId = article.coverAssetId
        showArticleList = false
        previewMode = false
        if (webReady) editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(article.html)});setEditable(true);", null)
        saved = true
    }

    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->
        uris.forEach { uri ->
            runCatching {
                val mime = context.contentResolver.getType(uri) ?: "image/jpeg"
                val ext = when (mime.lowercase(Locale.ROOT)) { "image/png" -> "png"; "image/webp" -> "webp"; "image/gif" -> "gif"; "image/heic" -> "heic"; else -> "jpg" }
                val id = vm.newId() + (0..999).random().toString()
                val dir = File(context.filesDir, "article_media").apply { mkdirs() }
                val target = File(dir, "$id.$ext")
                context.contentResolver.openInputStream(uri)?.use { input -> target.outputStream().use { output -> input.copyTo(output) } }
                    ?: error("无法读取图片")
                val relative = "article_media/${target.name}"
                vm.saveMediaAsset(MediaAsset(id, target.name, mime, relative, target.length(), System.currentTimeMillis().toString()))
                insert("<p><img src='https://editor.local/assets/$id' alt='${target.name}' style='max-width:100%;height:auto;display:block;margin:14px auto'></p>")
            }.onFailure { vm.toast("图片导入失败：${it.message ?: "未知错误"}") }
        }
    }
    val layoutImagePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) runCatching {
            val mime = context.contentResolver.getType(uri) ?: "image/jpeg"
            if (!mime.startsWith("image/")) error("所选文件不是图片")
            val ext = when (mime.lowercase(Locale.ROOT)) {
                "image/png" -> "png"; "image/webp" -> "webp"; "image/gif" -> "gif"; "image/heic" -> "heic"; else -> "jpg"
            }
            var id = vm.newId()
            while (vm.data.mediaAssets.any { it.id == id }) id = vm.newId()
            val dir = File(context.filesDir, "article_media").apply { mkdirs() }
            val target = File(dir, "$id.$ext")
            context.contentResolver.openInputStream(uri)?.use { input -> target.outputStream().use { output -> input.copyTo(output) } }
                ?: error("图片读取失败")
            val asset = MediaAsset(id, target.name, mime, "article_media/${target.name}", target.length(), System.currentTimeMillis().toString())
            vm.saveMediaAsset(asset)
            layoutBuilderImageAssetId = id
            vm.toast("图片已加入素材库并选为首栏图片")
        }.onFailure { vm.toast("图片导入失败：${it.message ?: "未知错误"}") }
    }
    val imageReplacementPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) runCatching {
            if (selectedImageHtml.isBlank()) error("请先选中要替换的图片")
            val mime = context.contentResolver.getType(uri) ?: "image/jpeg"
            if (!mime.startsWith("image/")) error("所选文件不是图片")
            val ext = when (mime.lowercase(Locale.ROOT)) { "image/png" -> "png"; "image/webp" -> "webp"; "image/gif" -> "gif"; "image/heic" -> "heic"; else -> "jpg" }
            var id = vm.newId()
            while (vm.data.mediaAssets.any { it.id == id }) id = vm.newId()
            val dir = File(context.filesDir, "article_media").apply { mkdirs() }
            val target = File(dir, "$id.$ext")
            context.contentResolver.openInputStream(uri)?.use { input -> target.outputStream().use { output -> input.copyTo(output) } } ?: error("图片读取失败")
            vm.saveMediaAsset(MediaAsset(id, target.name, mime, "article_media/${target.name}", target.length(), System.currentTimeMillis().toString()))
            runJs("replaceSelectedImage('https://editor.local/assets/$id',${JSONObject.quote(target.name)})")
            vm.toast("图片已替换")
        }.onFailure { vm.toast("图片替换失败：${it.message ?: "未知错误"}") }
    }
    val stylePackageExporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        if (uri != null) runCatching {
            context.contentResolver.openOutputStream(uri)?.bufferedWriter(Charsets.UTF_8)?.use { it.write(pendingExportStyleJson) } ?: error("无法写入文件")
            vm.toast("模板包已导出")
        }.onFailure { vm.toast("模板包导出失败：${it.message ?: "无法写入文件"}") }
    }
    val stylePackageImporter = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            val importedMedia = mutableListOf<MediaAsset>()
            runCatching {
                val raw = context.contentResolver.openInputStream(uri)?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: error("文件为空")
                if (raw.length > 52 * 1024 * 1024) error("模板包超过 52 MB")
                val pack = JSONObject(raw)
                if (pack.optString("format") != "shiwanju.styles.v1") error("不是拾万句模板包")
                val rows = pack.optJSONArray("styles") ?: error("模板列表缺失")
                if (rows.length() > 100) error("单个模板包最多导入 100 个样式")
                val idMap = mutableMapOf<String, String>()
                val assets = pack.optJSONArray("assets") ?: org.json.JSONArray()
                if (assets.length() > 40) error("模板包最多包含 40 张图片")
                val mediaDir = File(context.filesDir, "article_media").apply { mkdirs() }
                var totalBytes = 0L
                for (index in 0 until assets.length()) {
                    val row = assets.optJSONObject(index) ?: continue
                    val oldId = row.optString("id")
                    if (oldId.isBlank()) error("模板图片缺少资源 ID")
                    val mime = row.optString("mimeType", "image/jpeg")
                    if (!mime.startsWith("image/")) error("模板包含非图片资源")
                    val encoded = row.optString("base64")
                    if (encoded.length > 16 * 1024 * 1024) error("单张模板图片数据过大")
                    val bytes = Base64.decode(encoded, Base64.DEFAULT)
                    if (bytes.size > 12 * 1024 * 1024) error("单张模板图片超过 12 MB")
                    totalBytes += bytes.size
                    if (totalBytes > 36L * 1024 * 1024) error("模板图片总大小超过 36 MB")
                    var newId = vm.newId()
                    while (vm.data.mediaAssets.any { it.id == newId } || importedMedia.any { it.id == newId }) newId = vm.newId()
                    val rawName = row.optString("fileName", "template_image_$index.jpg").substringAfterLast('/').substringAfterLast('\\')
                    val ext = rawName.substringAfterLast('.', "jpg").replace(Regex("[^A-Za-z0-9]"), "").take(8).ifBlank { "jpg" }
                    val target = File(mediaDir, "$newId.$ext")
                    target.writeBytes(bytes)
                    val asset = MediaAsset(newId, rawName.replace(Regex("[^A-Za-z0-9._-]"), "_").take(100), mime, "article_media/${target.name}", target.length(), System.currentTimeMillis().toString())
                    vm.saveMediaAsset(asset); importedMedia.add(asset); idMap[oldId] = newId
                }
                val importedStyles = mutableListOf<StyleModule>()
                for (index in 0 until rows.length()) {
                    val row = rows.optJSONObject(index) ?: continue
                    var htmlValue = row.optString("html")
                    if (htmlValue.length > 2 * 1024 * 1024) error("第 ${index + 1} 个模板内容过大")
                    idMap.forEach { (oldId, newId) -> htmlValue = htmlValue.replace("/assets/$oldId", "/assets/$newId") }
                    val tags = row.optJSONArray("tags") ?: org.json.JSONArray()
                    val safeTags = (0 until minOf(tags.length(), 30)).mapNotNull { tags.optString(it).take(40).takeIf { tag -> tag.isNotBlank() } }
                    val type = row.optString("type").takeIf { it in listOf("full", "component", "combination") } ?: "component"
                    importedStyles += StyleModule(
                        id = vm.newId(), name = row.optString("name", "导入样式").take(100).ifBlank { "导入样式" },
                        category = row.optString("category", "导入模板").take(80).ifBlank { "导入模板" },
                        html = sanitizeArticleHtml(htmlValue), updatedAt = System.currentTimeMillis().toString(),
                        isFavorite = row.optBoolean("isFavorite", false), type = type, thumbnail = idMap[row.optString("thumbnail")] ?: row.optString("thumbnail").take(200), tags = safeTags
                    )
                }
                if (importedStyles.isEmpty()) error("模板包中没有可导入的样式")
                importedStyles.forEach { vm.saveStyle(it) }
                vm.toast("已导入 ${importedStyles.size} 个样式模板及 ${importedMedia.size} 张图片")
            }.onFailure { error ->
                importedMedia.forEach { asset ->
                    runCatching { File(context.filesDir, asset.relativePath).canonicalFile.let { file ->
                        val root = File(context.filesDir, "article_media").canonicalFile
                        if (file.path.startsWith(root.path + File.separator)) file.delete()
                    } }
                    vm.deleteMediaAsset(asset.id)
                }
                vm.toast("模板包导入失败：${error.message ?: "文件格式错误"}")
            }
        }
    }
        val articleJsonExporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        if (uri != null) runCatching {
            context.contentResolver.openOutputStream(uri)?.bufferedWriter(Charsets.UTF_8)?.use { it.write(pendingExportArticleJson) }
                ?: error("无法写入文件")
            vm.toast("文章包及引用的本地图片已导出")
        }.onFailure { vm.toast("文章包导出失败：${it.message ?: "无法写入文件"}") }
    }
    val articleJsonImporter = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) runCatching {
            val raw = context.contentResolver.openInputStream(uri)?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: error("文件为空")
            if (raw.length > 52 * 1024 * 1024) error("文章包超过 52 MB，暂不支持导入")
            val pack = JSONObject(raw)
            if (pack.optString("format") != "shiwanju.article.v1") error("不是拾万句文章包")
            if (pack.optString("html").length > 12 * 1024 * 1024) error("文章 HTML 内容过大")
            val assets = pack.optJSONArray("assets") ?: org.json.JSONArray()
            if (assets.length() > 40) error("单篇文章最多导入 40 张图片")
            pendingArticlePackageRaw = raw
            showArticlePackagePreview = true
        }.onFailure { vm.toast("文章包读取失败：${it.message ?: "文件格式错误"}") }
    }
        val imageGroupPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris ->
        val chosen = uris.take(pendingImageGroupCount)
        if (chosen.size < pendingImageGroupCount) vm.toast("请选择至少 ${pendingImageGroupCount} 张图片")
        else runCatching {
            val fragments = chosen.mapIndexed { index, uri ->
                val mime = context.contentResolver.getType(uri) ?: "image/jpeg"
                val ext = when (mime.lowercase(Locale.ROOT)) { "image/png" -> "png"; "image/webp" -> "webp"; "image/gif" -> "gif"; else -> "jpg" }
                val id = vm.newId() + index.toString()
                val dir = File(context.filesDir, "article_media").apply { mkdirs() }
                val target = File(dir, "$id.$ext")
                context.contentResolver.openInputStream(uri)?.use { input -> target.outputStream().use { output -> input.copyTo(output) } } ?: error("图片读取失败")
                vm.saveMediaAsset(MediaAsset(id, target.name, mime, "article_media/${target.name}", target.length(), System.currentTimeMillis().toString()))
                "<td style='width:${100.0 / pendingImageGroupCount}%;padding:2px;vertical-align:top'><img src='https://editor.local/assets/$id' alt='图片 ${index + 1}' style='width:100%;height:auto;display:block'></td>"
            }
            val htmlGroup = "<table style='width:100%;table-layout:fixed;border-collapse:collapse'><tr>${fragments.joinToString("")}</tr></table><p><br></p>"
            insert(htmlGroup)
            vm.toast("已插入 ${pendingImageGroupCount} 图组")
        }.onFailure { vm.toast("图组导入失败：${it.message ?: "未知错误"}") }
    }
    val htmlImporter = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) runCatching {
            val raw = context.contentResolver.openInputStream(uri)?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: error("文件为空")
            if (raw.length > 12 * 1024 * 1024) error("HTML 文件超过 12 MB")
            pendingImportedHtml = sanitizeArticleHtml(raw)
            showHtmlImportPreview = true
        }.onFailure { vm.toast("HTML 导入失败：${it.message ?: "无法读取文件"}") }
    }
    val markdownImporter = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) runCatching {
            val raw = context.contentResolver.openInputStream(uri)?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: error("文件为空")
            if (raw.length > 4 * 1024 * 1024) error("Markdown 文件超过 4 MB")
            pendingImportedHtml = sanitizeArticleHtml(markdownToArticleHtml(raw))
            showHtmlImportPreview = true
        }.onFailure { vm.toast("Markdown 导入失败：${it.message ?: "无法读取文件"}") }
    }
        val markdownExporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/markdown")) { uri ->
        if (uri != null) runCatching {
            context.contentResolver.openOutputStream(uri)?.bufferedWriter(Charsets.UTF_8)?.use { it.write(pendingExportMarkdown) }
                ?: error("无法写入文件")
            vm.toast("Markdown 已导出")
        }.onFailure { vm.toast("Markdown 导出失败：${it.message ?: "无法写入文件"}") }
    }
    val htmlExporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("text/html")) { uri ->
        if (uri != null) runCatching {
            context.contentResolver.openOutputStream(uri)?.bufferedWriter(Charsets.UTF_8)?.use { it.write(pendingExportHtml) }
                ?: error("无法写入文件")
            vm.toast("HTML 已导出")
        }.onFailure { vm.toast("HTML 导出失败：${it.message ?: "无法写入文件"}") }
    }
    fun copyPlainText() {
        editor?.evaluateJavascript("document.getElementById('editor').innerText") { raw ->
            val plain = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull()
                ?: html.replace(Regex("<[^>]*>"), "")
            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            clipboard.setPrimaryClip(ClipData.newPlainText(title, plain))
            vm.toast("已复制纯文本")
        }
    }
    fun copyRichHtml() {
        val view = editor
        if (view == null || !webReady) {
            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            clipboard.setPrimaryClip(ClipData.newPlainText(title, html.replace(Regex("<[^>]*>"), "")))
            vm.toast("已复制纯文本")
            return
        }
        view.evaluateJavascript("(function(){var h=document.getElementById('editor').innerHTML;var d=document.createElement('div');d.innerHTML=h;return JSON.stringify({html:h,text:d.innerText||d.textContent||''});})()") { raw ->
            runCatching {
                val jsonText = org.json.JSONTokener(raw ?: "null").nextValue() as String
                val payload = JSONObject(jsonText)
                var rich = payload.optString("html")
                val plain = payload.optString("text")
                val localIds = Regex("""https://editor\.local/assets/([A-Za-z0-9_-]+)""").findAll(rich).map { it.groupValues[1] }.distinct().toList()
                var embeddedBytes = 0L
                localIds.forEach { id ->
                    val asset = vm.data.mediaAssets.firstOrNull { it.id == id } ?: return@forEach
                    val root = File(context.filesDir, "article_media").canonicalFile
                    val file = File(context.filesDir, asset.relativePath).canonicalFile
                    if (file.path.startsWith(root.path + File.separator) && file.isFile) {
                        val bytes = file.readBytes()
                        embeddedBytes += bytes.size
                        if (embeddedBytes > 24L * 1024 * 1024) error("本地图片总量超过 24 MB，请减少图片后再复制")
                        val dataUri = "data:${asset.mimeType.ifBlank { "image/jpeg" }};base64,${Base64.encodeToString(bytes, Base64.NO_WRAP)}"
                        rich = rich.replace("https://editor.local/assets/$id", dataUri)
                    }
                }
                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newHtmlText(title, plain, rich))
                vm.toast(if (localIds.isEmpty()) "已复制富文本，可粘贴到支持 HTML 的编辑器" else "已复制富文本并尝试内嵌本地图片；若公众号不接收内嵌图片，请在公众号重新上传图片")
            }.onFailure {
                val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newPlainText(title, html.replace(Regex("<[^>]*>"), "")))
                vm.toast("富文本复制失败，已回退为纯文本")
            }
        }
    }

    LaunchedEffect(title, html, articleId, pendingSave, webReady) {
        if (!webReady || showArticleList) return@LaunchedEffect
        saved = false
        delay(750)
        saveDocument()
    }

    // Persist the latest WebView HTML when Android hides the app UI (background/recents).
    val saveOnBackground by rememberUpdatedState(newValue = { saveDocument() })
    DisposableEffect(context) {
        val appContext = context.applicationContext
        val callbacks = object : ComponentCallbacks2 {
            override fun onTrimMemory(level: Int) {
                if (level >= ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN) saveOnBackground()
            }
            override fun onLowMemory() = Unit
            override fun onConfigurationChanged(newConfig: Configuration) = Unit
        }
        appContext.registerComponentCallbacks(callbacks)
        onDispose { appContext.unregisterComponentCallbacks(callbacks) }
    }

    BackHandler {
        when {
            showArticleList -> showArticleList = false
            previewMode -> {
                previewMode = false
                editor?.evaluateJavascript("setEditable(true);setPreviewInfo('','','','');", null)
            }
            else -> saveDocument(onComplete = onBack)
        }
    }

    Column(Modifier.fillMaxSize().background(pageBg).systemBarsPadding()) {
        Row(
            Modifier.fillMaxWidth().height(58.dp).background(AppColors.Panel)
                .padding(horizontal = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = { saveDocument(onComplete = onBack) }) {
                Icon(Icons.Outlined.ArrowBack, "返回", tint = ink)
            }
            Column(Modifier.weight(1f).padding(start = 2.dp)) {
                BasicTextField(
                    value = title, onValueChange = { title = it; saved = false; pendingSave++ },
                    modifier = Modifier.fillMaxWidth(), singleLine = true,
                    textStyle = androidx.compose.ui.text.TextStyle(color = ink, fontSize = 15.sp, fontWeight = FontWeight.SemiBold),
                    decorationBox = { inner -> Box { if (title.isEmpty()) Text("文章标题", color = Color(0xFF9AA19C)); inner() } }
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(6.dp).clip(CircleShape).background(if (saved) accent else Color(0xFFE0A23B)))
                    Text("醒图 · " + if (saved) "已保存" else "自动保存中", color = AppColors.TextDim, fontSize = 10.sp, modifier = Modifier.padding(start = 5.dp))
                }
            }
            IconButton(onClick = { runJs("undoEditor()") }, modifier = Modifier.size(36.dp)) { Icon(Icons.Outlined.Undo, contentDescription = "撤销", tint = Color(0xFF59625C), modifier = Modifier.size(20.dp)) }
            IconButton(onClick = { runJs("redoEditor()") }, modifier = Modifier.size(36.dp)) { Icon(Icons.Outlined.Redo, contentDescription = "重做", tint = Color(0xFF59625C), modifier = Modifier.size(20.dp)) }
            TextButton(onClick = {
                previewMode = !previewMode
                editor?.evaluateJavascript("setEditable(${!previewMode});setPreviewInfo(${JSONObject.quote(if (previewMode) title else "")},${JSONObject.quote(if (previewMode) subtitle else "")},${JSONObject.quote(if (previewMode) author else "")},${JSONObject.quote(if (previewMode) summary else "")});", null)
            }, contentPadding = PaddingValues(horizontal = 6.dp, vertical = 4.dp)) {
                Text(if (previewMode) "编辑" else "预览", color = accent, fontSize = 11.sp, fontWeight = FontWeight.SemiBold)
            }
        }
        androidx.compose.foundation.layout.Box(
            Modifier.fillMaxWidth().height(1.dp).background(AppColors.Line)
        )

        if (showArticleList) {
            Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                Text("我的文章", fontSize = 20.sp, fontWeight = FontWeight.SemiBold, color = ink, modifier = Modifier.weight(1f))
                TextButton(onClick = { htmlImporter.launch(arrayOf("text/html", "application/xhtml+xml", "text/plain")) }) { Text("导入", color = ink) }
                TextButton(onClick = { newArticle() }) { Text("+ 新建文章", color = accent) }
            }
            OutlinedTextField(searchText, { searchText = it }, modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp), singleLine = true, placeholder = { Text("搜索文章标题、摘要、分类或标签") })
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 14.dp, vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                listOf("全部", "草稿", "已完成", "收藏").forEach { filter ->
                    EditorTool(filter, articleFilter == filter) { articleFilter = filter }
                }
                Text("${filteredArticles.size} 篇", color = Color.Gray, fontSize = 11.sp, modifier = Modifier.align(Alignment.CenterVertically))
            }
            if (filteredArticles.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(if (vm.data.articles.isEmpty()) "还没有保存的文章，点击「新建文章」开始创作" else "没有符合条件的文章，试试更换筛选条件", color = Color.Gray, fontSize = 13.sp)
                }
            } else {
                androidx.compose.foundation.lazy.LazyColumn(
                    Modifier.fillMaxSize().padding(horizontal = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(filteredArticles.size, key = { filteredArticles[it].id }) { index ->
                        val item = filteredArticles.getOrNull(index)
                        if (item != null) {
                            Row(
                                Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Color.White)
                                    .clickable { openArticle(item) }.padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(Modifier.weight(1f)) {
                                    Text(item.title.ifBlank { "未命名文章" }, color = ink, fontSize = 14.sp, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    Text("${if (item.status == "complete") "已完成" else "草稿"} · ${item.category.ifBlank { "未分类" }} · ${item.html.replace(Regex("<[^>]*>"), "").length} 字 · ${Regex("<img\\b").findAll(item.html).count()} 图 · ${formatArticleTimestamp(item.updatedAt)}", color = Color.Gray, fontSize = 11.sp, modifier = Modifier.padding(top = 5.dp))
                                    if (item.summary.isNotBlank()) Text(item.summary, color = Color(0xFF858B86), fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 3.dp))
                                }
                                Column(horizontalAlignment = Alignment.End) {
                                    TextButton(onClick = {
                                        val now = System.currentTimeMillis().toString()
                                        vm.saveArticle(item.copy(isFavorite = !item.isFavorite, updatedAt = now))
                                    }) { Text(if (item.isFavorite) "★" else "☆", color = accent) }
                                    TextButton(onClick = {
                                        val now = System.currentTimeMillis().toString()
                                        val copy = item.copy(id = vm.newId(), title = item.title + "（副本）", createdAt = now, updatedAt = now, isFavorite = false)
                                        vm.saveArticle(copy)
                                    }) { Text("复制", color = accent) }
                                    TextButton(onClick = { showDeleteConfirm = item }) { Text("删除", color = Color(0xFFCC5555)) }
                                }
                            }
                        }
                    }
                }
            }
        } else {
            if (previewMode) {
                Row(Modifier.fillMaxWidth().background(Color.White).padding(horizontal = 12.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text("阅读预览", color = ink, fontSize = 13.sp, modifier = Modifier.weight(1f))
                    EditorTool("返回编辑") { previewMode = false; editor?.evaluateJavascript("setEditable(true);setPreviewInfo('','','','');", null) }
                }
            } else {
            if (showMoreTools) {
                Dialog(onDismissRequest = { showMoreTools = false }) {
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(20.dp),
                        color = Color(0xFFF9FAF9),
                        shadowElevation = 18.dp
                    ) {
                        Column(
                            Modifier.fillMaxWidth().heightIn(max = 600.dp)
                                .verticalScroll(rememberScrollState()).padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            FlowRow(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(7.dp),
                                verticalArrangement = Arrangement.spacedBy(7.dp)
                            ) {
                EditorTool("立即保存") { saveDocument(true); showMoreTools = false }
                EditorTool("撤销") { runJs("undoEditor()") }
                EditorTool("重做") { runJs("redoEditor()") }
                EditorTool("预览", previewMode) {
                    previewMode = !previewMode
                    editor?.evaluateJavascript("setEditable(${!previewMode});setPreviewInfo(${JSONObject.quote(if (previewMode) title else "")},${JSONObject.quote(if (previewMode) subtitle else "")},${JSONObject.quote(if (previewMode) author else "")},${JSONObject.quote(if (previewMode) summary else "")});", null)
                }
                EditorTool("全选") { runJs("document.getElementById('editor').focus();document.execCommand('selectAll');saveSelection();") }
                EditorTool("复制富文本") { copyRichHtml() }
                EditorTool("复制纯文本") { copyPlainText() }
                Text("格式检查与文件", color = Color(0xFF7B847E), fontSize = 11.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
                EditorTool("兼容检查") {
                    editor?.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
                        val current = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
                        compatibilityWarnings = articleCompatibilityWarnings(current)
                        showCompatibilityReport = true
                    }
                }
                EditorTool("导入HTML") { htmlImporter.launch(arrayOf("text/html", "application/xhtml+xml", "text/plain")) }
                EditorTool("导入Markdown") { markdownImporter.launch(arrayOf("text/markdown", "text/plain")) }
                EditorTool("导出HTML") {
                    if (editor == null || !webReady) vm.toast("编辑器尚未准备好，请稍后重试")
                    else editor?.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
                        runCatching {
                            val current = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
                            val safeTitle = escapeMarkdownText(title.ifBlank { "未命名文章" })
                            val safeSubtitle = subtitle.takeIf { it.isNotBlank() }?.let { "<p class='subtitle'>${escapeMarkdownText(it)}</p>" }.orEmpty()
                            val safeMeta = listOf(author, summary).filter { it.isNotBlank() }.joinToString(" · ") { escapeMarkdownText(it) }
                            pendingExportHtml = "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>$safeTitle</title><style>body{max-width:680px;margin:0 auto;padding:22px 18px;font:16px/1.9 sans-serif;color:#333}img{max-width:100%;height:auto}table{max-width:100%;border-collapse:collapse}h1{font-size:25px;line-height:1.45;margin:0 0 12px}.subtitle{color:#777;font-size:16px}.meta{color:#999;font-size:12px;margin-bottom:20px}</style></head><body><header><h1>$safeTitle</h1>$safeSubtitle<p class=\"meta\">$safeMeta</p></header><main>$current</main></body></html>"
                            htmlExporter.launch("${title.ifBlank { "文章" }}.html")
                        }.onFailure { vm.toast("HTML 导出失败：${it.message ?: "内容处理错误"}") }
                    }
                }
                EditorTool("导出Markdown") {
                    editor?.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
                        val current = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
                        pendingExportMarkdown = buildString {
                            append("# ").append(title.ifBlank { "未命名文章" }).append("\n\n")
                            if (subtitle.isNotBlank()) append(subtitle).append("\n\n")
                            val meta = listOf(author, summary).filter { it.isNotBlank() }.joinToString(" · ")
                            if (meta.isNotBlank()) append(meta).append("\n\n")
                            append(articleHtmlToMarkdown(current))
                        }
                        markdownExporter.launch("${title.ifBlank { "文章" }}.md")
                    }
                }
                Text("文章管理与版本", color = Color(0xFF7B847E), fontSize = 11.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
                EditorTool("文章列表") { saveDocument(onComplete = { showArticleList = true; showMoreTools = false }) }
                EditorTool("版本记录") { saveDocument(); showRevisionList = true }
                EditorTool("文章信息") {
                    articleInfoSnapshot = listOf(subtitle, author, category, tagsText, summary, articleStatus, coverAssetId)
                    showArticleInfo = true
                }
                EditorTool("导入文章包") { articleJsonImporter.launch(arrayOf("application/json", "text/json")) }
                EditorTool("导出文章包") {
                    if (editor == null || !webReady) vm.toast("编辑器尚未准备好，请稍后重试")
                    else editor?.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
                        runCatching {
                        val current = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
                        if (current.length > 12 * 1024 * 1024) error("文章 HTML 超过文章包导出容量限制")
                        val pack = JSONObject()
                            .put("format", "shiwanju.article.v1")
                            .put("title", title).put("subtitle", subtitle).put("summary", summary)
                            .put("author", author).put("category", category).put("tags", org.json.JSONArray(tagsText.split(",").map { it.trim() }.filter { it.isNotEmpty() }))
                            .put("status", articleStatus).put("isFavorite", currentArticle?.isFavorite ?: false).put("coverAssetId", coverAssetId).put("html", current)
                        val assets = org.json.JSONArray()
                        var packageImageBytes = 0L
                        vm.data.mediaAssets.filter { current.contains(it.id) || coverAssetId == it.id }.forEach { asset ->
                            val mediaRoot = File(context.filesDir, "article_media").canonicalFile
                            val file = File(context.filesDir, asset.relativePath).canonicalFile
                            if (file.path.startsWith(mediaRoot.path + File.separator) && file.isFile) {
                                val bytes = file.readBytes()
                                packageImageBytes += bytes.size
                                if (bytes.size > 12 * 1024 * 1024 || packageImageBytes > 36L * 1024 * 1024) error("文章引用图片超过文章包导出容量限制")
                                assets.put(JSONObject().put("id", asset.id).put("fileName", asset.fileName).put("mimeType", asset.mimeType)
                                    .put("base64", Base64.encodeToString(bytes, Base64.NO_WRAP)))
                            }
                        }
                        pack.put("assets", assets)
                        pendingExportArticleJson = pack.toString(2)
                        articleJsonExporter.launch("${title.ifBlank { "文章" }}.shiwanju.json")
                        }.onFailure { vm.toast("文章包导出失败：${it.message ?: "无法读取素材"}") }
                    }
                }
                EditorTool("保存整篇模板") {
                    editor?.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
                        val fullHtml = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
                        if (fullHtml.isBlank()) vm.toast("文章内容为空，无法保存模板")
                        else {
                            vm.saveStyle(StyleModule(vm.newId(), title.ifBlank { "未命名整篇模板" }, "整篇模板", fullHtml, System.currentTimeMillis().toString(), type = "full"))
                            vm.toast("已保存到模板中心")
                        }
                    }
                }
                Text("链接与模块操作", color = Color(0xFF7B847E), fontSize = 11.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
                EditorTool("插入链接") { dialogValue = ""; linkInsertType = "link"; showLink = true }
                EditorTool(if (multiSelectMode) "退出多选" else "多选组合", multiSelectMode) {
                    multiSelectMode = !multiSelectMode
                    runJs("setMultiSelectMode(${multiSelectMode})")
                    selectedBlockHtml = ""
                }
                if (multiSelectMode && selectedBlockHtml.isNotBlank()) {
                    EditorTool("保存组合样式") {
                        vm.saveStyle(StyleModule(vm.newId(), "组合组件", "组合组件", selectedBlockHtml, System.currentTimeMillis().toString(), type = "combination"))
                        vm.toast("已保存组合组件到「我的 - 样式」")
                        multiSelectMode = false
                        runJs("setMultiSelectMode(false)")
                    }
                } else if (selectedBlockHtml.isNotBlank()) {
                    EditorTool("模块上移") { runJs("moveSelectedBlock(-1)") }
                    EditorTool("模块下移") { runJs("moveSelectedBlock(1)") }
                    EditorTool("模块样式") { showBlockProperties = true }
                    EditorTool("复制模块") { runJs("duplicateSelectedBlock()") }
                    EditorTool("删除模块") { runJs("deleteSelectedBlock()"); selectedBlockHtml = "" }
                    EditorTool("保存为样式") {
                        vm.saveStyle(StyleModule(vm.newId(), "我的模块", "自定义组件", selectedBlockHtml, System.currentTimeMillis().toString()))
                        vm.toast("已保存到「我的 - 样式」")
                    }
                }
            }
                        }
                    }
                }
            }
            }

            BoxWithConstraints(Modifier.weight(1f).fillMaxWidth().background(pageBg)) {
            AndroidView(
                factory = { ctx ->
                    WebView(ctx).apply {
                        settings.javaScriptEnabled = true
                        settings.domStorageEnabled = false
                        settings.allowFileAccess = false
                        settings.allowContentAccess = false
                        settings.mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
                        settings.javaScriptCanOpenWindowsAutomatically = false
                        isVerticalScrollBarEnabled = true
                        setBackgroundColor(android.graphics.Color.WHITE)
                        addJavascriptInterface(ArticleEditorBridge(
                            { value -> html = value; saved = false; pendingSave++ },
                            { value -> selectedBlockHtml = value },
                            { value -> selectedImageHtml = value; floatingToolbarRequest = "" },
                            { value -> selectedTextActive = value; floatingToolbarRequest = ""; if (value) floatingMenu = "" }
                        ), "NativeEditor")
                        webViewClient = object : WebViewClient() {
                            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean = true
                            override fun shouldInterceptRequest(view: WebView?, request: WebResourceRequest?): WebResourceResponse? {
                                val url = request?.url ?: return null
                                if (url.host != "editor.local" || !url.path.orEmpty().startsWith("/assets/")) return null
                                val id = url.lastPathSegment ?: return null
                                val asset = vm.data.mediaAssets.firstOrNull { it.id == id } ?: return null
                                val mediaRoot = File(context.filesDir, "article_media").canonicalFile
                                val file = File(context.filesDir, asset.relativePath).canonicalFile
                                if (!file.path.startsWith(mediaRoot.path + File.separator) || !file.isFile) return null
                                return runCatching { WebResourceResponse(asset.mimeType.ifBlank { "application/octet-stream" }, null, file.inputStream()) }.getOrNull()
                            }
                            override fun onPageFinished(view: WebView?, url: String?) {
                                webReady = true
                                view?.evaluateJavascript("setEditorHtml(${JSONObject.quote(html)});setEditable(${!previewMode});setPreviewInfo(${JSONObject.quote(if (previewMode) title else "")},${JSONObject.quote(if (previewMode) subtitle else "")},${JSONObject.quote(if (previewMode) author else "")},${JSONObject.quote(if (previewMode) summary else "")});", null)
                            }
                        }
                        val page = """
                            <!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
                            <style>
                            *{box-sizing:border-box}html,body{margin:0;padding:0;min-height:100%;background:#ECEEEC;color:#333;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}
                            #previewHeader{display:none;padding:26px 18px 0;color:#333}#previewHeader h1{font-size:25px;line-height:1.45;margin:0 0 10px;font-weight:700}#previewHeader .sub{font-size:16px;color:#666;margin:0 0 10px;line-height:1.6}#previewHeader .meta{font-size:12px;color:#999;margin:0 0 14px}
                            #editor{width:calc(100% - 34px);max-width:640px;min-height:calc(100vh - 28px);margin:15px auto 24px;padding:30px 22px 120px;background:#fff;border-radius:5px;box-shadow:0 3px 16px rgba(37,48,41,.08);outline:none;font-size:16px;line-height:1.9;overflow-wrap:anywhere}
                            #editor:empty:before{content:"从这里开始写文章…";color:#b8bdb9}
                            #editor h1{font-size:26px;line-height:1.4;margin:24px 0 16px}#editor h2{font-size:21px;line-height:1.5;margin:22px 0 14px}
                            #editor h3{font-size:18px;line-height:1.5;margin:18px 0 12px}#editor p{margin:0 0 14px}
                            #editor blockquote{margin:18px 0;padding:10px 14px;border-left:3px solid #159765;background:#f4f8f5;color:#66716a}
                            #editor img{max-width:100%;height:auto;display:block;margin:12px auto}
                            #editor table{width:100%;border-collapse:collapse;table-layout:fixed}#editor td,#editor th{border:1px solid #dfe4e0;padding:8px;min-width:24px;vertical-align:top}
                            #editor a{color:#16865a;text-decoration:underline}#editor hr{border:0;border-top:1px solid #e1e5e2;margin:22px 0}
                            #editor .selected-block{outline:1px dashed #159765;outline-offset:3px}
                            #editor .drop-before{position:relative}
                            #editor .drop-before::before{content:"";display:block;height:3px;background:#159765;border-radius:3px;margin:0 0 5px}
                            #editor .drop-after{position:relative}
                            #editor .drop-after::after{content:"";display:block;height:3px;background:#159765;border-radius:3px;margin:5px 0 0}
                            #editor img.selected-image{outline:2px solid #159765;outline-offset:2px}
                            </style></head><body><header id="previewHeader"></header><div id="editor" contenteditable="true" spellcheck="true"></div>
                            <script>
                            const root=document.getElementById('editor');let savedRange=null;let timer=null;let snapshots=['<p><br></p>'];let historyIndex=0;let snapshotChars=snapshots[0].length;let dragSource=null;let dragSources=[];let dragTarget=null;let activeImage=null;
                            function commitHistory(){const value=root.innerHTML;if(snapshots[historyIndex]===value)return;snapshots=snapshots.slice(0,historyIndex+1);snapshotChars=snapshots.reduce((n,item)=>n+item.length,0);snapshots.push(value);snapshotChars+=value.length;while((snapshots.length>40||snapshotChars>8*1024*1024)&&snapshots.length>2){const removed=snapshots.shift();snapshotChars-=removed.length;historyIndex=Math.max(0,historyIndex-1);}historyIndex=snapshots.length-1;}
                            function restoreHistoryCaret(){root.focus();const r=document.createRange();r.selectNodeContents(root);r.collapse(false);const sel=window.getSelection();sel.removeAllRanges();sel.addRange(r);saveSelection();}
                            function undoEditor(){commitHistory();if(historyIndex<=0)return;historyIndex--;root.innerHTML=snapshots[historyIndex];restoreHistoryCaret();NativeEditor.changed(root.innerHTML);}
                            function redoEditor(){if(historyIndex>=snapshots.length-1)return;historyIndex++;root.innerHTML=snapshots[historyIndex];restoreHistoryCaret();NativeEditor.changed(root.innerHTML);}
                            function setEditorHtml(v){root.innerHTML=v||'<p><br></p>';snapshots=[root.innerHTML];historyIndex=0;snapshotChars=snapshots[0].length;activeImage=null;NativeEditor.imageSelected('');NativeEditor.blockSelected('');saveSelection();}
                            function setEditable(v){root.contentEditable=!!v;if(!v){root.querySelectorAll('.selected-block,.selected-image').forEach(e=>e.classList.remove('selected-block','selected-image'));activeImage=null;NativeEditor.blockSelected('');NativeEditor.imageSelected('');}}
                            function setPreviewInfo(t,sub,author,summary){const h=document.getElementById('previewHeader');h.innerHTML='';if(!t&&!sub&&!author&&!summary){h.style.display='none';return;}h.style.display='block';if(t){const e=document.createElement('h1');e.textContent=t;h.appendChild(e);}if(sub){const e=document.createElement('p');e.className='sub';e.textContent=sub;h.appendChild(e);}const meta=[author,summary].filter(Boolean).join(' · ');if(meta){const e=document.createElement('p');e.className='meta';e.textContent=meta;h.appendChild(e);}}
                            function setSelectedImageWidth(v){if(!activeImage)return;activeImage.style.width=v;activeImage.style.maxWidth='100%';activeImage.style.height='auto';commitHistory();NativeEditor.changed(root.innerHTML);}function setSelectedImageObjectPosition(v){if(!activeImage)return;activeImage.style.objectPosition=v;commitHistory();NativeEditor.imageSelected(activeImage.outerHTML);NativeEditor.changed(root.innerHTML);}
                            function rotateSelectedImage(){if(!activeImage)return;const n=(parseInt(activeImage.dataset.rotation||'0')+90)%360;activeImage.dataset.rotation=n;activeImage.style.transform='rotate('+n+'deg)';commitHistory();NativeEditor.changed(root.innerHTML);}
                            function setSelectedImageRadius(v){if(!activeImage)return;activeImage.style.borderRadius=v;commitHistory();NativeEditor.changed(root.innerHTML);}
                            function cropSelectedImage(ratio){if(!activeImage)return;const w=activeImage.parentElement.clientWidth||320;const h=ratio==='1:1'?w:ratio==='4:3'?w*0.75:w*0.5625;activeImage.style.width='100%';activeImage.style.height=Math.round(h)+'px';activeImage.style.objectFit='cover';activeImage.style.objectPosition='center';commitHistory();NativeEditor.changed(root.innerHTML);}
                            function resetSelectedImageCrop(){if(!activeImage)return;activeImage.style.width=activeImage.dataset.originalWidth||'';activeImage.style.height=activeImage.dataset.originalHeight||'auto';activeImage.style.objectFit=activeImage.dataset.originalObjectFit||'';activeImage.style.objectPosition=activeImage.dataset.originalObjectPosition||'';commitHistory();NativeEditor.changed(root.innerHTML);}
                            function setSelectedImageBorder(v){if(!activeImage)return;activeImage.style.border=v;commitHistory();NativeEditor.changed(root.innerHTML);}
                            function setSelectedImageAlt(v){if(!activeImage)return;activeImage.alt=v;commitHistory();NativeEditor.changed(root.innerHTML);}
                            function replaceSelectedImage(src,alt){if(!activeImage)return;activeImage.src=src;if(alt)activeImage.alt=alt;commitHistory();NativeEditor.changed(root.innerHTML);NativeEditor.imageSelected(activeImage.outerHTML);}
                            function deleteSelectedImage(){if(!activeImage)return;const parent=activeImage.parentElement;activeImage.remove();if(parent&&/^(P|DIV)$/.test(parent.tagName)&&!parent.textContent.trim()&&!parent.querySelector('img,table'))parent.remove();activeImage=null;NativeEditor.imageSelected('');commitHistory();NativeEditor.changed(root.innerHTML);}
                            function moveSelectedImageInGroup(dir){if(!activeImage)return;const cell=activeImage.closest('td,th');if(!cell)return;const sibling=dir<0?cell.previousElementSibling:cell.nextElementSibling;if(!sibling)return;if(dir<0)cell.parentNode.insertBefore(cell,sibling);else cell.parentNode.insertBefore(sibling,cell);commitHistory();NativeEditor.changed(root.innerHTML);}
                            function selectedParagraph(){const sel=window.getSelection();let e=sel&&sel.anchorNode?(sel.anchorNode.nodeType===3?sel.anchorNode.parentElement:sel.anchorNode):null;while(e&&e!==root&&!/^(P|H1|H2|H3|H4|BLOCKQUOTE|LI|PRE)$/.test(e.tagName))e=e.parentElement;return e&&e!==root?e:null;}
                            function styleSelectedParagraph(prop,value){restoreSelection();const e=selectedParagraph();if(!e)return;e.style[prop]=value;commitHistory();NativeEditor.changed(root.innerHTML);}
                            function styleSelectionOrParagraph(prop,value){const sel=window.getSelection();if(sel&&!sel.isCollapsed){const styles={};styles[prop]=value;applyInlineStyle(styles);}else styleSelectedParagraph(prop,value);}
                            function replaceAllText(search,replacement){if(!search)return 0;const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let node,count=0;while(node=walker.nextNode()){if(node.nodeValue.includes(search)){const parts=node.nodeValue.split(search);count+=parts.length-1;node.nodeValue=parts.join(replacement);}}if(count){commitHistory();NativeEditor.changed(root.innerHTML);}return count;}
                            let formatClipboard=null;
                            function selectedTextElement(){const sel=window.getSelection();let e=sel&&sel.anchorNode?(sel.anchorNode.nodeType===3?sel.anchorNode.parentElement:sel.anchorNode):null;while(e&&e!==root&&!/^(P|H1|H2|H3|H4|SPAN|STRONG|B|EM|I|U)$/.test(e.tagName))e=e.parentElement;return e&&e!==root?e:null;}
                            function applyInlineStyle(styles){const sel=window.getSelection();if(!sel||!sel.rangeCount||sel.isCollapsed)return false;const r=sel.getRangeAt(0);const span=document.createElement('span');Object.assign(span.style,styles);span.appendChild(r.extractContents());r.insertNode(span);r.setStartAfter(span);r.collapse(true);sel.removeAllRanges();sel.addRange(r);saveSelection();commitHistory();NativeEditor.changed(root.innerHTML);return true;}
                            function setSelectionFontSize(px){applyInlineStyle({fontSize:px+'px'});}
                            function copyTextFormat(){const e=selectedTextElement();if(!e)return false;const c=getComputedStyle(e);formatClipboard={fontFamily:c.fontFamily,fontSize:c.fontSize,fontWeight:c.fontWeight,fontStyle:c.fontStyle,color:c.color,backgroundColor:c.backgroundColor,textDecoration:c.textDecoration};return true;}
                            function pasteTextFormat(){if(!formatClipboard)return false;return applyInlineStyle(formatClipboard);}

                            function getLayerList(){
                              return JSON.stringify(Array.from(root.children).map((e,i)=>{
                                const id=ensureEditorId(e);
                                const text=(e.innerText||e.textContent||'').replace(/\s+/g,' ').trim();
                                return {id:id,tag:e.tagName.toLowerCase(),name:text.slice(0,42),visible:getComputedStyle(e).display!=='none',locked:e.dataset.editorLocked==='1'};
                              }));
                            }
                            function selectLayer(id){
                              const e=Array.from(root.children).find(x=>x.dataset.editorId===id);
                              if(!e)return false;
                              root.querySelectorAll('.selected-block').forEach(x=>x.classList.remove('selected-block'));
                              e.classList.add('selected-block');
                              NativeEditor.blockSelected(cleanBlockHtml(e));
                              if(typeof reportSelection==='function')reportSelection();
                              return true;
                            }
                            function setLayerVisibility(id,visible){
                              const e=Array.from(root.children).find(x=>x.dataset.editorId===id);
                              if(!e)return;
                              e.style.display=visible?'':'none';
                              commitHistory();NativeEditor.changed(root.innerHTML);
                            }
                            function setLayerLocked(id,locked){
                              const e=Array.from(root.children).find(x=>x.dataset.editorId===id);
                              if(!e)return;
                              e.dataset.editorLocked=locked?'1':'0';
                              e.contentEditable=locked?'false':'true';
                              e.draggable=!locked;
                              commitHistory();NativeEditor.changed(root.innerHTML);
                            }
                            function moveLayer(id,dir){
                              const e=Array.from(root.children).find(x=>x.dataset.editorId===id);
                              if(!e)return;
                              if(dir<0&&e.previousElementSibling)e.parentNode.insertBefore(e,e.previousElementSibling);
                              else if(dir>0&&e.nextElementSibling)e.parentNode.insertBefore(e.nextElementSibling,e);
                              commitHistory();NativeEditor.changed(root.innerHTML);
                            }
                            function selectedBlock(){return root.querySelector('.selected-block');}
                            function cleanBlockHtml(e){const c=e.cloneNode(true);c.classList.remove('selected-block');c.draggable=false;return c.outerHTML;}
                            function replaceSelectedBlockWithHtml(v){const e=selectedBlock();if(!e)return;const box=document.createElement('div');box.innerHTML=v;const frag=document.createDocumentFragment();while(box.firstChild)frag.appendChild(box.firstChild);const first=frag.firstElementChild;e.replaceWith(frag);if(first){first.classList.add('selected-block');NativeEditor.blockSelected(cleanBlockHtml(first));}commitHistory();NativeEditor.changed(root.innerHTML);}
                            function duplicateSelectedBlock(){const e=selectedBlock();if(!e)return;const c=e.cloneNode(true);c.classList.remove('selected-block');e.insertAdjacentElement('afterend',c);c.classList.add('selected-block');NativeEditor.blockSelected(c.outerHTML);commitHistory();NativeEditor.changed(root.innerHTML);}
                            function deleteSelectedBlock(){const e=selectedBlock();if(!e)return;e.remove();NativeEditor.blockSelected('');commitHistory();NativeEditor.changed(root.innerHTML);}
                            function moveSelectedBlock(dir){const e=selectedBlock();if(!e)return;if(dir<0&&e.previousElementSibling)e.parentNode.insertBefore(e,e.previousElementSibling);else if(dir>0&&e.nextElementSibling)e.parentNode.insertBefore(e.nextElementSibling,e);commitHistory();NativeEditor.changed(root.innerHTML);}
                            function applySelectedBlockStyle(padding,margin,width,bg,border,borderWidth,borderStyle,radius,shadow,align,opacity){const e=selectedBlock();if(!e)return;e.style.boxSizing='border-box';e.style.padding=padding;e.style.margin=margin+' auto';e.style.width=width;e.style.maxWidth='100%';e.style.background='none';e.style.background=bg;e.style.border=borderWidth+'px '+borderStyle+' '+border;e.style.borderRadius=radius;e.style.boxShadow=shadow;e.style.textAlign=align;e.style.opacity=String(Math.max(0,Math.min(100,Number(opacity))))/100;commitHistory();NativeEditor.blockSelected(cleanBlockHtml(e));NativeEditor.changed(root.innerHTML);}
                            function selectedTable(){const e=selectedBlock();return e?(e.tagName==='TABLE'?e:e.querySelector('table')):null;}
                            function addTableRow(){const t=selectedTable();if(!t||!t.rows.length)return;const r=t.rows[t.rows.length-1];const n=r.cloneNode(true);Array.from(n.cells).forEach(c=>c.innerHTML='<br>');r.parentNode.insertBefore(n,r.nextSibling);commitHistory();NativeEditor.changed(root.innerHTML);}
                            function removeTableRow(){const t=selectedTable();if(!t||t.rows.length<=1)return;t.deleteRow(t.rows.length-1);commitHistory();NativeEditor.changed(root.innerHTML);}
                            function addTableColumn(){const t=selectedTable();if(!t)return;Array.from(t.rows).forEach(r=>{const c=r.insertCell(-1);c.innerHTML='<br>';c.style.border='1px solid #ddd';c.style.padding='8px';});commitHistory();NativeEditor.changed(root.innerHTML);}
                            function removeTableColumn(){const t=selectedTable();if(!t)return;Array.from(t.rows).forEach(r=>{if(r.cells.length>1)r.deleteCell(r.cells.length-1);});commitHistory();NativeEditor.changed(root.innerHTML);}
                            function updateMultiDragHandle(preferred){const selected=Array.from(root.querySelectorAll('.selected-block'));selected.forEach(e=>e.draggable=false);const handle=preferred&&selected.includes(preferred)?preferred:selected[selected.length-1];if(handle)handle.draggable=true;}
                            function setMultiSelectMode(v){multiSelectMode=!!v;root.querySelectorAll('.selected-block').forEach(e=>{e.classList.remove('selected-block');e.draggable=false;});NativeEditor.blockSelected('');}
                            root.addEventListener('click',function(ev){
                              if(ev.target&&ev.target.tagName==='IMG'){root.querySelectorAll('.selected-image').forEach(x=>x.classList.remove('selected-image'));activeImage=ev.target;if(activeImage.dataset.originalWidth===undefined){activeImage.dataset.originalWidth=activeImage.style.width;activeImage.dataset.originalHeight=activeImage.style.height;activeImage.dataset.originalObjectFit=activeImage.style.objectFit;activeImage.dataset.originalObjectPosition=activeImage.style.objectPosition;}activeImage.classList.add('selected-image');NativeEditor.imageSelected(activeImage.outerHTML);NativeEditor.textSelected('0');}
                              else {if(activeImage){activeImage.classList.remove('selected-image');activeImage=null;NativeEditor.imageSelected('');}NativeEditor.textSelected(ev.target!==root?'1':'0');}
                              let e=ev.target;while(e&&e!==root&&e.parentElement!==root)e=e.parentElement;
                              if(e&&e!==root){
                                if(multiSelectMode){e.classList.toggle('selected-block');updateMultiDragHandle(e);NativeEditor.blockSelected(Array.from(root.querySelectorAll('.selected-block')).map(x=>cleanBlockHtml(x)).join(''));}
                                else{root.querySelectorAll('.selected-block').forEach(x=>{x.classList.remove('selected-block');x.draggable=false;});e.classList.add('selected-block');e.draggable=true;NativeEditor.blockSelected(cleanBlockHtml(e));}
                              }
                            });
                            function clearDragTarget(){if(dragTarget){dragTarget.classList.remove('drop-before','drop-after');dragTarget=null;}}
                            root.addEventListener('dragstart',function(ev){let e=ev.target;while(e&&e!==root&&e.parentElement!==root)e=e.parentElement;const selected=Array.from(root.querySelectorAll('.selected-block'));if(!e||e===root||!selected.includes(e)){ev.preventDefault();return;}dragSource=e;dragSources=multiSelectMode?selected:[e];ev.dataTransfer.effectAllowed='move';});
                            root.addEventListener('dragover',function(ev){
                              if(!dragSources.length){clearDragTarget();return;}
                              const target=topLevelAt(ev.target);
                              if(!target||dragSources.includes(target)){clearDragTarget();return;}
                              ev.preventDefault();
                              const rect=target.getBoundingClientRect(),before=ev.clientY<rect.top+rect.height/2;
                              const cls=before?'drop-before':'drop-after';
                              if(dragTarget!==target||!target.classList.contains(cls)){clearDragTarget();target.classList.add(cls);dragTarget=target;}
                            });
                            root.addEventListener('drop',function(ev){
                              if(!dragSources.length){clearDragTarget();return;}
                              ev.preventDefault();
                              const target=topLevelAt(ev.target);
                              if(target&&!dragSources.includes(target)&&target.parentElement===root){
                                const rect=target.getBoundingClientRect(),anchor=ev.clientY<rect.top+rect.height/2?target:target.nextSibling;
                                dragSources.forEach(node=>root.insertBefore(node,anchor));
                                commitHistory();NativeEditor.changed(root.innerHTML);NativeEditor.blockSelected(dragSources.map(node=>cleanBlockHtml(node)).join(''));
                              }
                              clearDragTarget();dragSource=null;dragSources=[];
                            });
                            root.addEventListener('dragend',function(){clearDragTarget();dragSource=null;dragSources=[];});

                            // Touch fallback for phones: long-press a selected block or image-group cell, then drag to a visible drop target.
                            let touchDrag=null,touchDrop=null;
                            function topLevelAt(node){let e=node;while(e&&e!==root&&e.parentElement!==root)e=e.parentElement;return e&&e!==root?e:null;}
                            function clearTouchDrop(){if(!touchDrop)return;touchDrop.el.style.outline=touchDrop.outline||'';touchDrop.el.style.boxShadow=touchDrop.shadow||'';touchDrop=null;}
                            root.addEventListener('touchstart',function(ev){if(!ev.touches||ev.touches.length!==1)return;const t=ev.touches[0],img=ev.target&&ev.target.closest?ev.target.closest('img'):null,cell=img?img.closest('td,th'):null;const block=topLevelAt(ev.target);if(cell&&activeImage&&cell.contains(activeImage)&&cell.parentElement&&cell.parentElement.children.length>1){touchDrag={kind:'group',source:cell,row:cell.parentElement,x:t.clientX,y:t.clientY,started:Date.now(),active:false};}else if(block&&block.classList.contains('selected-block')){touchDrag={kind:multiSelectMode?'blocks':'block',source:block,sources:multiSelectMode?Array.from(root.querySelectorAll('.selected-block')):[block],x:t.clientX,y:t.clientY,started:Date.now(),active:false};}}, {passive:true});
                            root.addEventListener('touchmove',function(ev){if(!touchDrag||!ev.touches||ev.touches.length!==1)return;const t=ev.touches[0],dx=t.clientX-touchDrag.x,dy=t.clientY-touchDrag.y;if(!touchDrag.active){if(Date.now()-touchDrag.started<260||Math.abs(dx)+Math.abs(dy)<10)return;touchDrag.active=true;root.style.userSelect='none';}ev.preventDefault();const hit=document.elementFromPoint(t.clientX,t.clientY);let target=null;if(touchDrag.kind==='group'){const cell=hit&&hit.closest?hit.closest('td,th'):null;if(cell&&cell.parentElement===touchDrag.row&&cell!==touchDrag.source)target=cell;}else{target=topLevelAt(hit);if((touchDrag.sources||[touchDrag.source]).includes(target))target=null;}if(target!== (touchDrop&&touchDrop.el)){clearTouchDrop();if(target){touchDrop={el:target,outline:target.style.outline,shadow:target.style.boxShadow};target.style.outline='2px dashed #159765';target.style.boxShadow='0 0 0 2px rgba(21,151,101,.12)';}}},{passive:false});
                            function finishTouchDrag(){if(!touchDrag)return;const drag=touchDrag;const target=touchDrop&&touchDrop.el;clearTouchDrop();root.style.userSelect='';if(drag.active&&target){if(drag.kind==='group'&&target.parentElement===drag.row){const rect=target.getBoundingClientRect();drag.row.insertBefore(drag.source,touchDrag.lastX<rect.left+rect.width/2?target:target.nextSibling);commitHistory();NativeEditor.changed(root.innerHTML);NativeEditor.imageSelected(activeImage?activeImage.outerHTML:'');}else if((drag.kind==='block'||drag.kind==='blocks')&&target.parentElement===root){const rect=target.getBoundingClientRect(),anchor=touchDrag.lastY<rect.top+rect.height/2?target:target.nextSibling,sources=drag.kind==='blocks'?drag.sources:[drag.source];sources.forEach(node=>root.insertBefore(node,anchor));commitHistory();NativeEditor.changed(root.innerHTML);NativeEditor.blockSelected(sources.map(node=>cleanBlockHtml(node)).join(''));}}touchDrag=null;}
                            root.addEventListener('touchend',function(ev){if(touchDrag&&ev.changedTouches&&ev.changedTouches.length){touchDrag.lastX=ev.changedTouches[0].clientX;touchDrag.lastY=ev.changedTouches[0].clientY;}finishTouchDrag();},{passive:true});
                            root.addEventListener('touchcancel',finishTouchDrag,{passive:true});
                            function saveSelection(){const s=window.getSelection();if(s&&s.rangeCount){savedRange=s.getRangeAt(0).cloneRange();}}
                            function restoreSelection(){root.focus();const s=window.getSelection();if(savedRange&&s){s.removeAllRanges();s.addRange(savedRange);}}
                            function insertHtml(v){restoreSelection();const s=window.getSelection();if(!s||!s.rangeCount){root.insertAdjacentHTML('beforeend',v);commitHistory();NativeEditor.changed(root.innerHTML);return;}
                              const r=s.getRangeAt(0);r.deleteContents();const t=document.createElement('div');t.innerHTML=v;const f=document.createDocumentFragment();while(t.firstChild)f.appendChild(t.firstChild);const last=f.lastChild;r.insertNode(f);if(last){r.setStartAfter(last);r.collapse(true);s.removeAllRanges();s.addRange(r);}saveSelection();commitHistory();NativeEditor.changed(root.innerHTML);}
                            root.addEventListener('paste',function(ev){
                              const data=ev.clipboardData;if(!data)return;const pasted=data.getData('text/html');if(!pasted)return;
                              ev.preventDefault();const box=document.createElement('div');box.innerHTML=pasted;
                              box.querySelectorAll('script,iframe,object,embed,form,meta,link').forEach(e=>e.remove());
                              box.querySelectorAll('*').forEach(e=>{
                                Array.from(e.attributes).forEach(a=>{
                                  const key=a.name.toLowerCase(),value=(a.value||'').trim().toLowerCase();
                                  if(key.startsWith('on')||key==='srcdoc')e.removeAttribute(a.name);
                                  if(['href','src','xlink:href','action','formaction'].includes(key)&&(value.startsWith('javascript:')||value.startsWith('data:text/html')||value.startsWith('vbscript:')||value.startsWith('file:')||value.startsWith('content:')||value.startsWith('blob:')))e.removeAttribute(a.name);
                                });
                              });
                              insertHtml(box.innerHTML);
                            });
                            root.addEventListener('keyup',saveSelection);root.addEventListener('mouseup',saveSelection);root.addEventListener('touchend',saveSelection);
                            root.addEventListener('input',()=>{saveSelection();clearTimeout(timer);timer=setTimeout(()=>{commitHistory();NativeEditor.changed(root.innerHTML);},300);});
                            document.addEventListener('selectionchange',()=>{if(document.activeElement===root)saveSelection();});
                            window.addEventListener('scroll',()=>{saveSelection();reportSelection();},{passive:true});window.addEventListener('resize',()=>{reportSelection();},{passive:true});
                            </script></body></html>
                        """.trimIndent()
                            .replace("#159765", accentHex)
                            .replace("#16865a", accentHex)
                        loadDataWithBaseURL("https://editor.local/", page, "text/html", "UTF-8", null)
                        editor = this
                        tag = "article-editor"
                    }
                },
                modifier = Modifier.fillMaxSize(),
                update = { editor = it }
            )
            if (!previewMode) {
                Column(Modifier.align(Alignment.CenterStart)
                    .offset { IntOffset(insertLauncherOffset.x.toInt(), insertLauncherOffset.y.toInt()) }
                    .padding(start = 6.dp), horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (showInsertLauncherMenu) {
                        Surface(shape = RoundedCornerShape(24.dp), color = Color(0xFF242424), shadowElevation = 10.dp) {
                            Column(Modifier.padding(6.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                                listOf(Triple("文字", "✎", "text"), Triple("图片", "▧", "image")).forEach { (label, glyph, mode) ->
                                    Row(Modifier.clip(CircleShape).clickable {
                                        floatingToolbarRequest = mode
                                        showToolPopup = false; showCanvasPopup = false
                                        showInsertLauncherMenu = false
                                        floatingMenu = ""
                                    }.padding(horizontal = 11.dp, vertical = 8.dp),
                                        verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                        Text(glyph, color = AppColors.Theme, fontSize = 17.sp)
                                        Text(label, color = Color.White, fontSize = 12.sp)
                                    }
                                }
                            }
                        }
                    }
                    Surface(Modifier.size(48.dp).pointerInput(Unit) {
                        detectDragGestures { change, drag ->
                            change.consume()
                            insertLauncherOffset = Offset(insertLauncherOffset.x + drag.x, insertLauncherOffset.y + drag.y)
                        }
                    }.clickable { showInsertLauncherMenu = !showInsertLauncherMenu },
                        shape = CircleShape, color = AppColors.Theme, shadowElevation = 12.dp) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(if (showInsertLauncherMenu) "×" else "＋", color = Color.White, fontSize = 25.sp)
                        }
                    }
                }
            }
            if (!previewMode && (floatingToolbarRequest.isNotBlank() || selectedBlockHtml.isNotBlank() ||
                    selectionState.kind == EditorSelectionKind.TABLE || selectionState.kind == EditorSelectionKind.MULTI_BLOCK ||
                    selectionState.kind == EditorSelectionKind.COMPONENT || selectionState.kind == EditorSelectionKind.LAYOUT)) {
                val toolbarHeight = 88.dp
                val selectedTop = selectionState.y.dp
                val floatingY = if (selectedTop > maxHeight * 0.56f) {
                    (selectedTop - toolbarHeight - 8.dp).coerceAtLeast(8.dp)
                } else {
                    (selectedTop + selectionState.height.dp + 10.dp).coerceAtMost((maxHeight - toolbarHeight).coerceAtLeast(8.dp))
                }
                Surface(
                    Modifier.align(Alignment.TopCenter).offset(y = floatingY).offset { IntOffset(floatingToolbarOffset.x.toInt(), floatingToolbarOffset.y.toInt()) }.fillMaxWidth().padding(horizontal = 12.dp),
                    shape = RoundedCornerShape(18.dp), color = AppColors.Panel, shadowElevation = 14.dp,
                    border = androidx.compose.foundation.BorderStroke(1.dp, AppColors.Line)
                ) {
                    Column(Modifier.fillMaxWidth().padding(horizontal = 10.dp, vertical = 7.dp)) {
                        Row(Modifier.fillMaxWidth().height(34.dp).pointerInput(Unit) {
                            detectDragGestures { change, dragAmount -> change.consume(); floatingToolbarOffset = Offset(floatingToolbarOffset.x + dragAmount.x, floatingToolbarOffset.y + dragAmount.y) }
                        }, verticalAlignment = Alignment.CenterVertically) {
                            Text("⠿", color = AppColors.TextDim, fontSize = 15.sp, modifier = Modifier.padding(end = 6.dp))
                            Text(
                                when {
                                    floatingToolbarRequest == "image" || selectedImageHtml.isNotBlank() -> "图片工具"
                                    floatingToolbarRequest == "text" || selectedTextActive -> "文字工具"
                                    selectionState.kind == EditorSelectionKind.TABLE -> "表格工具"
                                    selectionState.kind == EditorSelectionKind.MULTI_BLOCK -> "组合工具"
                                    else -> "模块工具"
                                },
                                color = ink, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.weight(1f)
                            )
                            TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = {
                                selectedTextActive = false; selectedImageHtml = ""; selectedBlockHtml = ""; floatingMenu = ""
                                selectionState = EditorSelectionState()
                                floatingToolbarRequest = ""
                                runJs("root.querySelectorAll('.selected-image,.selected-block').forEach(e=>e.classList.remove('selected-image','selected-block'));activeImage=null;NativeEditor.imageSelected('');NativeEditor.textSelected('0');NativeEditor.blockSelected('');")
                            }) { Text("完成", color = AppColors.TextDim, fontSize = 11.sp) }
                        }
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(0.dp), verticalAlignment = Alignment.CenterVertically) {
                            if (floatingToolbarRequest == "image" || selectedImageHtml.isNotBlank()) {
                                if (floatingToolbarRequest == "image" && selectedImageHtml.isBlank()) {
                                    Text("请先在正文中选择图片，再使用图片工具", color = AppColors.TextDim, fontSize = 10.sp)
                                }
                                Box {
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { floatingMenu = if (floatingMenu == "image-width") "" else "image-width" }) { Text("▣ 尺寸 ▾", color = accent, fontSize = 11.sp) }
                                    DropdownMenu(expanded = floatingMenu == "image-width", onDismissRequest = { floatingMenu = "" }) {
                                        listOf("100%" to "原宽", "75%" to "四分之三", "50%" to "一半").forEach { (v, label) -> DropdownMenuItem(text = { Text("@LABEL@  @V@".replace("@LABEL@", label).replace("@V@", v)) }, onClick = { runJs("setSelectedImageWidth('@V@')".replace("@V@", v)); floatingMenu = "" }) }
                                    }
                                }
                                Box {
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { floatingMenu = if (floatingMenu == "image-crop") "" else "image-crop" }) { Text("▧ 裁切 ▾", color = ink, fontSize = 11.sp) }
                                    DropdownMenu(expanded = floatingMenu == "image-crop", onDismissRequest = { floatingMenu = "" }) {
                                        listOf("1:1", "4:3", "16:9").forEach { ratio -> DropdownMenuItem(text = { Text("裁切 " + ratio) }, onClick = { runJs("cropSelectedImage('" + ratio + "')"); floatingMenu = "" }) }
                                        DropdownMenuItem(text = { Text("自定义像素裁切") }, onClick = { openCustomImageCrop(); floatingMenu = "" })
                                        DropdownMenuItem(text = { Text("恢复原始比例") }, onClick = { runJs("resetSelectedImageCrop()"); floatingMenu = "" })
                                    }
                                }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("rotateSelectedImage()") }) { Text("↻ 旋转", color = ink, fontSize = 11.sp) }
                                Box {
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { floatingMenu = if (floatingMenu == "image-style") "" else "image-style" }) { Text("◒ 外观 ▾", color = ink, fontSize = 11.sp) }
                                    DropdownMenu(expanded = floatingMenu == "image-style", onDismissRequest = { floatingMenu = "" }) {
                                        DropdownMenuItem(text = { Text("圆角") }, onClick = { runJs("setSelectedImageRadius('10px')"); floatingMenu = "" })
                                        DropdownMenuItem(text = { Text("直角") }, onClick = { runJs("setSelectedImageRadius('0')"); floatingMenu = "" })
                                        DropdownMenuItem(text = { Text("细边框") }, onClick = { runJs("setSelectedImageBorder('1px solid #dfe5e1')"); floatingMenu = "" })
                                        DropdownMenuItem(text = { Text("无边框") }, onClick = { runJs("setSelectedImageBorder('0')"); floatingMenu = "" })
                                    }
                                }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { imageReplacementPicker.launch(arrayOf("image/*")) }) { Text("▧ 替换", color = ink, fontSize = 11.sp) }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { dialogValue = ""; showImageAlt = true }) { Text("ⓘ 说明", color = ink, fontSize = 11.sp) }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("deleteSelectedImage()"); selectedImageHtml = "" }) { Text("⌫ 删除", color = Color(0xFFCC5555), fontSize = 11.sp) }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { selectedImageHtml = ""; activePanel = EditorPanel.IMAGE }) { Text("更多 ⋯", color = accent, fontSize = 11.sp) }
                            } else if (floatingToolbarRequest == "text" || selectedTextActive) {
                                Box {
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { floatingMenu = if (floatingMenu == "text-size") "" else "text-size" }) { Text("Aᴀ 字号 ▾", color = accent, fontSize = 11.sp) }
                                    DropdownMenu(expanded = floatingMenu == "text-size", onDismissRequest = { floatingMenu = "" }) {
                                        listOf("12", "14", "16", "18", "20", "22", "24", "28", "32").forEach { px -> DropdownMenuItem(text = { Text(px + " px") }, onClick = { runJs("styleSelectionOrParagraph('fontSize','" + px + "px')"); floatingMenu = "" }) }
                                    }
                                }
                                Box {
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { floatingMenu = if (floatingMenu == "text-font") "" else "text-font" }) { Text("文 字体 ▾", color = ink, fontSize = 11.sp) }
                                    DropdownMenu(expanded = floatingMenu == "text-font", onDismissRequest = { floatingMenu = "" }) {
                                        listOf("PingFang SC" to "苹方", "Microsoft YaHei" to "微软雅黑", "SimSun" to "宋体", "SimHei" to "黑体", "KaiTi" to "楷体", "serif" to "衬线", "sans-serif" to "无衬线").forEach { (font, label) -> DropdownMenuItem(text = { Text(label) }, onClick = { runJs("styleSelectionOrParagraph('fontFamily'," + JSONObject.quote(font) + ")"); floatingMenu = "" }) }
                                    }
                                }
                                Box {
                                    TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { floatingMenu = if (floatingMenu == "text-color") "" else "text-color" }) { Text("● 颜色 ▾", color = ink, fontSize = 11.sp) }
                                    DropdownMenu(expanded = floatingMenu == "text-color", onDismissRequest = { floatingMenu = "" }) {
                                        listOf("#222222" to "黑色", "#666666" to "灰色", "#159765" to "绿色", "#C84B4B" to "红色", "#3978B7" to "蓝色", "#D69A35" to "橙色", "#8056A8" to "紫色").forEach { (hex, label) -> DropdownMenuItem(text = { Text("● " + label + " " + hex, color = Color(android.graphics.Color.parseColor(hex))) }, onClick = { runJs("styleSelectionOrParagraph('color','" + hex + "')"); floatingMenu = "" }) }
                                    }
                                }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { command("bold") }) { Text("B", color = ink, fontWeight = FontWeight.Bold, fontSize = 14.sp) }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { command("italic") }) { Text("I", color = ink, fontSize = 14.sp) }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { command("underline") }) { Text("U", color = ink, fontSize = 14.sp) }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { command("strikeThrough") }) { Text("S", color = ink, fontSize = 14.sp) }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { command("justifyLeft") }) { Text("≡", color = ink, fontSize = 15.sp) }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { command("justifyCenter") }) { Text("☷", color = ink, fontSize = 15.sp) }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { command("insertUnorderedList") }) { Text("☷•", color = ink, fontSize = 12.sp) }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { showFindReplace = true }) { Text("⌕", color = ink, fontSize = 15.sp) }
                                TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { activePanel = EditorPanel.TEXT; selectedTextActive = false; floatingToolbarRequest = "" }) { Text("更多 ⋯", color = accent, fontSize = 11.sp) }
                            } else {
                                when (selectionState.kind) {
                                    EditorSelectionKind.TABLE -> {
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("addTableRow()") }) { Text("＋ 行", color = accent, fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("removeTableRow()") }) { Text("－ 行", color = ink, fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("addTableColumn()") }) { Text("＋ 列", color = accent, fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("removeTableColumn()") }) { Text("－ 列", color = ink, fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { activePanel = EditorPanel.COMPONENT }) { Text("更多 ⋯", color = accent, fontSize = 11.sp) }
                                    }
                                    EditorSelectionKind.MULTI_BLOCK -> {
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("moveSelectedBlock(-1)") }) { Text("上移", color = ink, fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("moveSelectedBlock(1)") }) { Text("下移", color = ink, fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = {
                                            if (selectedBlockHtml.isNotBlank()) {
                                                vm.saveStyle(StyleModule(vm.newId(), "组合组件", "组合组件", selectedBlockHtml, System.currentTimeMillis().toString(), type = "combination"))
                                                vm.toast("已保存组合组件")
                                            } else vm.toast("请先选择要组合的模块")
                                        }) { Text("保存组合", color = accent, fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { activePanel = EditorPanel.LAYER }) { Text("更多 ⋯", color = accent, fontSize = 11.sp) }
                                    }
                                    else -> {
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("moveSelectedBlock(-1)") }) { Text("上移", color = ink, fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("moveSelectedBlock(1)") }) { Text("下移", color = ink, fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { showBlockProperties = true }) { Text("样式", color = accent, fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("duplicateSelectedBlock()") }) { Text("复制", color = ink, fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { runJs("deleteSelectedBlock()"); selectedBlockHtml = "" }) { Text("删除", color = Color(0xFFCC5555), fontSize = 11.sp) }
                                        TextButton(contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp), onClick = { activePanel = EditorPanel.COMPONENT }) { Text("更多 ⋯", color = accent, fontSize = 11.sp) }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            }



            // Persistent primary navigation: keep it in the editor's main Box, not only inside the tool Dialog.
            if (!previewMode) {
                Row(
                    Modifier.fillMaxWidth().height(50.dp)
                        .background(Color(0xFF181818)),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceAround
                ) {
                    Row(
                        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceAround
                    ) {
                        EditorPanel.values().filterNot { it in templateSubPanels }.forEach { panel ->
                            TextButton(
                                onClick = {
                                    showTemplateSubnav = panel == EditorPanel.TEMPLATE
                                    activePanel = if (panel == EditorPanel.TEMPLATE) templateSubPanel else panel
                                    floatingMenu = ""
                                    if (panel == EditorPanel.CANVAS) {
                                        showToolPopup = false
                                        showCanvasPopup = true
                                        toolPopupOffset = Offset.Zero
                                    } else {
                                        showCanvasPopup = false
                                        toolPanelHeightDp = if (panel == EditorPanel.TEXT2) 330f else 180f
                                        showToolPopup = true
                                    }
                                    if (panel == EditorPanel.LAYER) refreshLayerItems()
                                },
                                contentPadding = PaddingValues(horizontal = 9.dp, vertical = 3.dp)
                            ) {
                                Text(
                                    panel.label,
                                    color = if (activePanel == panel || (panel == EditorPanel.TEMPLATE && showTemplateSubnav)) Color.White else Color(0xFF777777),
                                    fontSize = if (activePanel == panel) 15.sp else 13.sp,
                                    fontWeight = if (activePanel == panel) FontWeight.Bold else FontWeight.Normal,
                                    maxLines = 1
                                )
                            }
                        }
                    }
                }
            }

            if (!previewMode) {
            if (showToolPopup && activePanel != EditorPanel.CANVAS) {
                Popup(
                    alignment = Alignment.BottomCenter,
                    onDismissRequest = { showToolPopup = false },
                    properties = PopupProperties(focusable = false, dismissOnBackPress = false, dismissOnClickOutside = false, clippingEnabled = false)
                ) {
                    Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.BottomCenter) {
                Column(Modifier.fillMaxWidth().height(animatedToolPanelHeight).background(Color(0xFF181818)).navigationBarsPadding()) {
                    Row(Modifier.fillMaxWidth().height(44.dp).padding(horizontal = 5.dp), verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = { showToolPopup = false }) { Icon(Icons.Outlined.Close, contentDescription = "关闭功能窗口", tint = Color.White) }
                        if (showTemplateSubnav) {
                            Row(Modifier.weight(1f).horizontalScroll(rememberScrollState()),
                                horizontalArrangement = Arrangement.spacedBy(4.dp), verticalAlignment = Alignment.CenterVertically) {
                                listOf(EditorPanel.TITLE, EditorPanel.CARD, EditorPanel.IMAGE, EditorPanel.LAYOUT, EditorPanel.SVG, EditorPanel.COMPONENT).forEach { sub ->
                                    Column(Modifier.clickable { templateSubPanel = sub; activePanel = sub }.padding(horizontal = 3.dp, vertical = 4.dp),
                                        horizontalAlignment = Alignment.CenterHorizontally) {
                                        Text(sub.label, color = if (activePanel == sub) Color.White else Color(0xFF888888),
                                            fontSize = 11.sp, fontWeight = if (activePanel == sub) FontWeight.Bold else FontWeight.Normal,
                                            maxLines = 1)
                                        Box(Modifier.padding(top = 2.dp).width(16.dp).height(2.dp).clip(RoundedCornerShape(4.dp))
                                            .background(if (activePanel == sub) AppColors.Theme else Color.Transparent))
                                    }
                                }
                            }
                        } else {
                            Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
                                Text(activePanel.label, color = Color.White, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
                            }
                        }
                        IconButton(onClick = { showToolPopup = false }) { Icon(Icons.Outlined.Check, contentDescription = "确定", tint = AppColors.Theme) }
                    }
                    CompositionLocalProvider(LocalEditorToolDark provides true) {
                        Column((if (activePanel == EditorPanel.TEXT2) Modifier.fillMaxWidth().weight(1f) else Modifier.fillMaxWidth().weight(1f).verticalScroll(rememberScrollState())).padding(horizontal = 13.dp, vertical = 6.dp)) {
remove content secondary navigation                when (activePanel) {
                    EditorPanel.TEXT -> {
                        Text("文字与段落", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("加粗 B") { command("bold") }; EditorTool("斜体 I") { command("italic") }; EditorTool("下划线 U") { command("underline") }; EditorTool("删除线") { command("strikeThrough") }
                            EditorTool("上标") { command("superscript") }; EditorTool("下标") { command("subscript") }; EditorTool("清除格式") { command("removeFormat") }
                        }
                        FlowRow(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("正文") { command("formatBlock", "p") }; EditorTool("H1") { command("formatBlock", "h1") }; EditorTool("H2") { command("formatBlock", "h2") }; EditorTool("H3") { command("formatBlock", "h3") }; EditorTool("引用") { command("formatBlock", "blockquote") }
                            EditorTool("左对齐") { command("justifyLeft") }; EditorTool("居中") { command("justifyCenter") }; EditorTool("右对齐") { command("justifyRight") }
                        }
                        FlowRow(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            listOf("14" to "小", "16" to "标准", "18" to "大", "22" to "特大", "26" to "标题").forEach { (size, label) -> EditorTool("字号$label") { runJs("restoreSelection();setSelectionFontSize('$size');saveSelection();") } }
                            EditorTool("文字绿") { runJs("restoreSelection();document.execCommand('foreColor',false,'#159765');saveSelection();") }
                            EditorTool("文字黑") { runJs("restoreSelection();document.execCommand('foreColor',false,'#333333');saveSelection();") }
                            EditorTool("文字红") { runJs("restoreSelection();document.execCommand('foreColor',false,'#C84B4B');saveSelection();") }
                            EditorTool("文字蓝") { runJs("restoreSelection();document.execCommand('foreColor',false,'#3978B7');saveSelection();") }
                            EditorTool("黄色高亮") { runJs("restoreSelection();document.execCommand('hiliteColor',false,'#FFF1B8');saveSelection();") }
                            EditorTool("绿色高亮") { runJs("restoreSelection();document.execCommand('hiliteColor',false,'#DDF3E5');saveSelection();") }
                            EditorTool("格式刷·复制") { runJs("restoreSelection();copyTextFormat();saveSelection();") }
                            EditorTool("格式刷·应用") { runJs("restoreSelection();pasteTextFormat();saveSelection();") }
                            EditorTool("无序列表") { command("insertUnorderedList") }; EditorTool("编号列表") { command("insertOrderedList") }
                            EditorTool("缩进") { command("indent") }; EditorTool("减缩进") { command("outdent") }
                            EditorTool("代码段") { command("formatBlock", "pre") }
                            EditorTool("H4") { command("formatBlock", "h4") }
                            EditorTool("任务清单") { insert("<ul style='list-style:none;padding-left:0'><li>□ 第一项任务</li><li>□ 第二项任务</li><li>□ 第三项任务</li></ul>") }
                            EditorTool("日期") { insert("<span>${java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.getDefault()).format(java.util.Date())}</span>") }
                            EditorTool("时间") { insert("<span>${java.text.SimpleDateFormat("HH:mm", java.util.Locale.getDefault()).format(java.util.Date())}</span>") }
                            EditorTool("分隔线") { insert("<hr style='border:0;border-top:1px solid #ddd;margin:22px 0'><p><br></p>") }
                            EditorTool("Emoji") { insert("✨") }
                            EditorTool("特殊符号") { insert("「」『』· — … ★ ✓ → ※") }
                            EditorTool("行距1.6") { runJs("styleSelectedParagraph('lineHeight','1.6')") }
                            EditorTool("行距1.8") { runJs("styleSelectedParagraph('lineHeight','1.8')") }
                            EditorTool("行距2.0") { runJs("styleSelectedParagraph('lineHeight','2')") }
                            EditorTool("首行缩进") { runJs("styleSelectedParagraph('textIndent','2em')") }
                            EditorTool("取消缩进") { runJs("styleSelectedParagraph('textIndent','0')") }
                            EditorTool("段前12") { runJs("styleSelectedParagraph('marginTop','12px')") }
                            EditorTool("段前24") { runJs("styleSelectedParagraph('marginTop','24px')") }
                            EditorTool("段后12") { runJs("styleSelectedParagraph('marginBottom','12px')") }
                            EditorTool("段后24") { runJs("styleSelectedParagraph('marginBottom','24px')") }
                            EditorTool("左缩进") { runJs("styleSelectedParagraph('marginLeft','1em')") }
                            EditorTool("右缩进") { runJs("styleSelectedParagraph('marginRight','1em')") }
                            EditorTool("字距1px") { runJs("styleSelectedParagraph('letterSpacing','1px')") }
                            EditorTool("查找替换") { showFindReplace = true }
                            EditorTool("宋体") { runJs("restoreSelection();document.execCommand('fontName',false,'SimSun');saveSelection();") }
                            EditorTool("黑体") { runJs("restoreSelection();document.execCommand('fontName',false,'Microsoft YaHei');saveSelection();") }
                        }
                    }
                    EditorPanel.IMAGE -> {
                        Text("图片素材", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("本地图片/相册") { imagePicker.launch(arrayOf("image/*")) }
                            EditorTool("双图组") { pendingImageGroupCount = 2; imageGroupPicker.launch(arrayOf("image/*")) }
                            EditorTool("三图组") { pendingImageGroupCount = 3; imageGroupPicker.launch(arrayOf("image/*")) }
                            EditorTool("插入网络图片") { dialogValue = ""; showImage = true }
                            EditorTool("双图并排") { pendingImageGroupCount = 2; imageGroupPicker.launch(arrayOf("image/*")) }
                            EditorTool("图片说明") { insert("<p style='text-align:center;color:#999;font-size:12px;margin-top:6px'>在此输入图片说明</p>") }
                            EditorTool("图片居中") { command("justifyCenter") }
                        }
                        if (selectedImageHtml.isNotBlank()) {
                            Text("图片调整", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 7.dp))
                            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                EditorTool("宽度100%") { runJs("setSelectedImageWidth('100%')") }
                                EditorTool("宽度75%") { runJs("setSelectedImageWidth('75%')") }
                                EditorTool("宽度50%") { runJs("setSelectedImageWidth('50%')") }
                                EditorTool("圆角") { runJs("setSelectedImageRadius('10px')") }
                                EditorTool("直角") { runJs("setSelectedImageRadius('0')") }
                                EditorTool("旋转90°") { runJs("rotateSelectedImage()") }
                                EditorTool("预览裁切1:1") { runJs("cropSelectedImage('1:1')") }
                                EditorTool("预览裁切4:3") { runJs("cropSelectedImage('4:3')") }
                                EditorTool("预览裁切16:9") { runJs("cropSelectedImage('16:9')") }
                                EditorTool("像素裁切1:1") { cropSelectedImagePixels(1f) }
                                EditorTool("像素裁切4:3") { cropSelectedImagePixels(4f / 3f) }
                                EditorTool("像素裁切16:9") { cropSelectedImagePixels(16f / 9f) }
                                EditorTool("自定义像素裁切") { openCustomImageCrop() }
                                EditorTool("裁切向上") { runJs("setSelectedImageObjectPosition('50% 20%')") }
                                EditorTool("裁切向下") { runJs("setSelectedImageObjectPosition('50% 80%')") }
                                EditorTool("裁切向左") { runJs("setSelectedImageObjectPosition('20% 50%')") }
                                EditorTool("裁切向右") { runJs("setSelectedImageObjectPosition('80% 50%')") }
                                EditorTool("裁切居中") { runJs("setSelectedImageObjectPosition('50% 50%')") }
                                EditorTool("原始比例") { runJs("resetSelectedImageCrop()") }
                                EditorTool("细边框") { runJs("setSelectedImageBorder('1px solid #dfe5e1')") }
                                EditorTool("无边框") { runJs("setSelectedImageBorder('0')") }
                                EditorTool("替换图片") { imageReplacementPicker.launch(arrayOf("image/*")) }
                                EditorTool("删除图片") { runJs("deleteSelectedImage()"); selectedImageHtml = "" }
                                EditorTool("组内左移") { runJs("moveSelectedImageInGroup(-1)") }
                                EditorTool("组内右移") { runJs("moveSelectedImageInGroup(1)") }
                                EditorTool("替代文字") { dialogValue = ""; showImageAlt = true }
                            }
                        }
                        if (vm.data.mediaAssets.isNotEmpty()) {
                            Text("本地图片库 · ${vm.data.mediaAssets.size} 张", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 7.dp))
                            OutlinedTextField(mediaSearchText, { mediaSearchText = it }, modifier = Modifier.fillMaxWidth().padding(top = 5.dp), singleLine = true, placeholder = { Text("搜索图片文件名或格式") })
                            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                filteredMediaAssets.forEach { asset ->
                                    EditorTool(asset.fileName.take(12)) {
                                        insert("<p><img src='https://editor.local/assets/${asset.id}' alt='${asset.fileName}' style='max-width:100%;height:auto;display:block;margin:14px auto'></p>")
                                    }
                                    EditorTool("预览") { previewAsset = asset }
                                    EditorTool("删") {
                                        val used = html.contains(asset.id) || coverAssetId == asset.id || vm.data.articles.any { it.id != articleId && (it.html.contains(asset.id) || it.coverAssetId == asset.id) } || vm.data.styles.any { it.html.contains(asset.id) || it.thumbnail == asset.id }
                                        if (used) vm.toast("该图片仍被文章或模板缩略图引用，不能删除")
                                        else {
                                            val mediaRoot = File(context.filesDir, "article_media").canonicalFile
                                            val mediaFile = File(context.filesDir, asset.relativePath).canonicalFile
                                            if (mediaFile.path.startsWith(mediaRoot.path + File.separator)) mediaFile.delete()
                                            vm.deleteMediaAsset(asset.id)
                                            vm.toast("图片已从素材库删除")
                                        }
                                    }
                                }
                            }
                            if (filteredMediaAssets.isEmpty()) Text("没有找到匹配的图片", color = Color.Gray, fontSize = 11.sp)
                        }
                        Text("本地图片已复制到应用私有目录；网络图片仍依赖原图链接可访问。", color = Color(0xFF929892), fontSize = 10.sp, modifier = Modifier.padding(top = 5.dp))
                    }
                    EditorPanel.TEXT2 -> {
                        Text2EditorPanel(
                            onCommand = { name, value -> command(name, value) },
                            onApplyCss = { property, value ->
                                val prop = property.replace("'", "")
                                val css = value.replace("'", "")
                                runJs("restoreSelection();(function(){var sel=window.getSelection();if(!sel||!sel.rangeCount)return;var range=sel.getRangeAt(0);if(range.collapsed){var node=range.startContainer;var el=node.nodeType===1?node:node.parentElement;if(el)el.style.setProperty('" + prop + "','" + css + "');return;}var span=document.createElement('span');span.style.setProperty('" + prop + "','" + css + "');try{range.surroundContents(span);}catch(e){var frag=range.extractContents();span.appendChild(frag);range.insertNode(span);}saveSelection();})();")
                            },
                            onApplyColor = { color, background ->
                                val commandName = if (background) "hiliteColor" else "foreColor"
                                runJs("restoreSelection();document.execCommand('" + commandName + "',false,'" + color + "');saveSelection();")
                            },
                            onEyedropper = { vm.toast("吸管取色：请先使用下方预设色；屏幕取色能力待接入") }
                        )
                    }
                    EditorPanel.TITLE -> {
                        Text("标题样式 · 选择后插入画布，可直接修改文字", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("编号标题") { insert("<section style='margin:22px 0 14px;padding:10px 14px;border-left:4px solid #159765;background:#f2f8f4'><p style='margin:0;font-size:19px;font-weight:700;color:#235b43'>01 / 在这里输入标题</p></section>") }
                            EditorTool("色块标题") { insert("<h2 style='margin:22px 0 14px;padding:9px 13px;background:#edf6f0;border-left:4px solid #159765;color:#235b43;font-size:19px'>在这里输入标题</h2>") }
                            EditorTool("边线标题") { insert("<h2 style='margin:22px 0 14px;padding-bottom:9px;border-bottom:1px solid #159765;color:#333;font-size:20px'>在这里输入标题</h2>") }
                            EditorTool("杂志标题") { insert("<section style='margin:24px 0;padding:18px 12px;border-top:2px solid #222;border-bottom:1px solid #aaa'><p style='font-size:24px;font-weight:700;letter-spacing:2px;margin:0'>SECTION TITLE</p><p style='font-size:11px;color:#999;letter-spacing:2px;margin:5px 0 0'>VOL. 01 / EDITORIAL</p></section>") }
                            EditorTool("双层标题") { insert("<section style='margin:20px 0'><p style='margin:0 0 5px;color:#159765;font-size:11px;letter-spacing:2px'>CHAPTER / 01</p><h2 style='margin:0;font-size:23px;line-height:1.45;color:#252525'>在这里输入主标题</h2></section>") }
                            EditorTool("居中标题") { insert("<h2 style='margin:24px 0;text-align:center;font-size:22px;line-height:1.5'>在这里输入标题</h2>") }
                            EditorTool("下划线标题") { insert("<h2 style='display:inline-block;margin:20px 0 14px;padding-bottom:5px;border-bottom:3px solid #159765;font-size:21px'>在这里输入标题</h2>") }
                            EditorTool("序号圆点标题") { insert("<h2 style='margin:20px 0 12px;font-size:20px'><span style='display:inline-block;margin-right:8px;color:#159765'>●</span>在这里输入标题</h2>") }
                        }
                    }
                    EditorPanel.LAYOUT -> {
                        Text("布局 · 选择版式后直接插入画布", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("自定义分栏") { layoutBuilderColumns = 2; layoutBuilderRatios = "1,1"; showLayoutBuilder = true }
                            EditorTool("双栏布局") { layoutBuilderColumns = 2; layoutBuilderRatios = "1,1"; layoutBuilderImageAssetId = ""; showLayoutBuilder = true }
                            EditorTool("三栏布局") { layoutBuilderColumns = 3; layoutBuilderRatios = "1,1,1"; layoutBuilderImageAssetId = ""; showLayoutBuilder = true }
                            EditorTool("图文左右排") { layoutBuilderColumns = 2; layoutBuilderRatios = "1,2"; layoutBuilderImageAssetId = ""; showLayoutBuilder = true }
                            EditorTool("图文上下排") { insert("<section style='margin:18px 0'><p style='margin:0 0 8px;padding:34px 12px;text-align:center;background:#f4f7f5;color:#89928b;border:1px dashed #cbd5ce'>请先插入本地图片</p><p style='margin:9px 0 4px;font-weight:700'>图片标题</p><p style='margin:0;color:#777;font-size:13px'>在这里填写图片说明。</p></section>") }
                            EditorTool("左右分割") { insert("<table style='width:100%;table-layout:fixed;border-collapse:collapse;margin:16px 0'><tr><td style='width:50%;vertical-align:top;padding:10px;background:#f5f7f5'>左侧内容</td><td style='width:50%;vertical-align:top;padding:10px'>右侧内容</td></tr></table>") }
                            EditorTool("居中内容") { insert("<section style='margin:20px auto;text-align:center;max-width:92%'><p style='margin:0;font-size:20px;font-weight:700'>居中标题</p><p style='margin:8px 0 0;color:#888;font-size:13px'>补充说明文字</p></section>") }
                            EditorTool("留白区块") { insert("<section style='height:32px;margin:0;padding:0'><p><br></p></section>") }
                            EditorTool("细分割线") { insert("<hr style='height:0;border:0;border-top:1px solid #e5e9e6;margin:22px 0'>") }
                            EditorTool("虚线分割") { insert("<hr style='height:0;border:0;border-top:1px dashed #cbd5ce;margin:22px 0'>") }
                        }
                    }
                    EditorPanel.CARD -> {
                        Text("卡片样式 · 常用内容块和信息卡片", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("引用卡片") { insert("<blockquote style='margin:18px 0;padding:14px 16px;background:#f4f7f5;border-left:3px solid #159765'><p style='margin:0'>在这里输入引用内容</p></blockquote>") }
                            EditorTool("提示卡片") { insert("<section style='margin:18px 0;padding:14px;background:#f1f8f4;border-radius:8px'><p style='margin:0 0 6px;color:#168653;font-weight:700'>温馨提示</p><p style='margin:0'>在这里输入提示内容</p></section>") }
                            EditorTool("重点卡片") { insert("<section style='margin:18px 0;padding:14px 16px;background:#fff8e9;color:#805d24;border-radius:7px;line-height:1.9'>在这里输入需要强调的内容</section>") }
                            EditorTool("信息卡片") { insert("<section style='margin:18px 0;padding:15px;background:#f5f7f6;border:1px solid #e4e9e5;border-radius:9px'><p style='margin:0 0 7px;font-weight:700'>信息标题</p><p style='margin:0;color:#666;font-size:13px;line-height:1.8'>在这里填写信息说明。</p></section>") }
                            EditorTool("作者卡片") { insert("<section style='margin:18px 0;padding:14px;background:#f6f7f6;border-radius:8px'><p style='margin:0 0 5px;font-weight:700'>关于作者</p><p style='margin:0;color:#777;font-size:13px'>在这里填写作者简介</p></section>") }
                            EditorTool("关注卡片") { insert("<section style='margin:24px 0;padding:18px 14px;text-align:center;background:#f3f8f4;border:1px solid #dcebe1'><p style='margin:0 0 6px;font-weight:700;color:#28724e'>感谢阅读</p><p style='margin:0;font-size:13px;color:#77857c'>关注「拾万句」，查看更多内容</p></section>") }
                            EditorTool("时间轴卡片") { insert("<section style='border-left:2px solid #b8d8c6;margin:18px 0;padding-left:16px'><p style='margin:0 0 5px;color:#159765;font-weight:700'>01 · 时间节点</p><p style='margin:0 0 16px'>在这里输入事件内容</p><p style='margin:0 0 5px;color:#159765;font-weight:700'>02 · 时间节点</p><p style='margin:0'>在这里输入事件内容</p></section>") }
                            EditorTool("数字清单卡") { insert("<section style='margin:18px 0;padding:14px;background:#f5f8f6;border-radius:8px'><p style='margin:0 0 10px;font-weight:700'>本期清单</p><ol style='padding-left:22px;line-height:2;margin:0'><li>第一项内容</li><li>第二项内容</li><li>第三项内容</li></ol></section>") }
                            EditorTool("图片说明卡") { insert("<section style='margin:18px 0;text-align:center'><p style='margin:0;padding:30px 12px;background:#f4f7f5;color:#89928b;border:1px dashed #cbd5ce'>请先插入本地图片</p><p style='margin:8px 0 0;color:#999;font-size:12px'>图片说明文字</p></section>") }
                        }
                    }
                    EditorPanel.COMPONENT -> {
                        Text("公众号排版组件 · 插入后可继续编辑", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("编号标题") { insert("<section style='margin:22px 0 14px;padding:10px 14px;border-left:4px solid #159765;background:#f2f8f4'><p style='margin:0;font-size:19px;font-weight:700;color:#235b43'>01 / 在这里输入标题</p></section>") }
                            EditorTool("引用卡片") { insert("<blockquote style='margin:18px 0;padding:14px 16px;background:#f4f7f5;border-left:3px solid #159765'><p style='margin:0'>在这里输入引用内容</p></blockquote>") }
                            EditorTool("提示卡片") { insert("<section style='margin:18px 0;padding:14px;background:#f1f8f4;border-radius:8px'><p style='margin:0 0 6px;color:#168653;font-weight:700'>温馨提示</p><p style='margin:0'>在这里输入提示内容</p></section>") }
                            EditorTool("分割线") { insert("<hr style='border:0;border-top:1px solid #dfe6e1;margin:24px 0'><p><br></p>") }
                            EditorTool("留白") { insert("<p style='height:24px;margin:0'><br></p>") }
                            EditorTool("数字列表") { insert("<ol><li>第一步</li><li>第二步</li><li>第三步</li></ol>") }
                            EditorTool("色块标题") { insert("<h2 style='margin:22px 0 14px;padding:9px 13px;background:#edf6f0;border-left:4px solid #159765;color:#235b43;font-size:19px'>在这里输入标题</h2>") }
                            EditorTool("边线标题") { insert("<h2 style='margin:22px 0 14px;padding-bottom:9px;border-bottom:1px solid #159765;color:#333;font-size:20px'>在这里输入标题</h2>") }
                            EditorTool("重点段落") { insert("<p style='margin:16px 0;padding:12px 14px;background:#fff8e9;color:#805d24;border-radius:5px;line-height:1.9'>在这里输入需要强调的内容</p>") }
                            EditorTool("首字下沉") { insert("<p style='line-height:2'><span style='float:left;font-size:42px;line-height:1;color:#159765;padding:4px 7px 0 0'>拾</span>在这里继续输入正文内容。</p>") }
                            EditorTool("时间轴") { insert("<section style='border-left:2px solid #b8d8c6;margin:18px 0;padding-left:16px'><p style='margin:0 0 5px;color:#159765;font-weight:700'>01 · 时间节点</p><p style='margin:0 0 16px'>在这里输入事件内容</p><p style='margin:0 0 5px;color:#159765;font-weight:700'>02 · 时间节点</p><p style='margin:0'>在这里输入事件内容</p></section>") }
                            EditorTool("表格") { insert("<table style='width:100%;border-collapse:collapse'><tr><th style='border:1px solid #ddd;padding:8px'>项目</th><th style='border:1px solid #ddd;padding:8px'>内容</th></tr><tr><td style='border:1px solid #ddd;padding:8px'>项目一</td><td style='border:1px solid #ddd;padding:8px'>填写内容</td></tr></table><p><br></p>") }
                            EditorTool("代码块") { insert("<pre style='padding:12px;background:#f4f5f4;white-space:pre-wrap;font-family:monospace;font-size:13px'>在此输入代码或等宽文本</pre>") }
                            EditorTool("关注引导") { insert("<section style='margin:24px 0;padding:18px 14px;text-align:center;background:#f3f8f4;border:1px solid #dcebe1'><p style='margin:0 0 6px;font-weight:700;color:#28724e'>感谢阅读</p><p style='margin:0;font-size:13px;color:#77857c'>关注「拾万句」，查看更多内容</p></section>") }
                            EditorTool("作者简介") { insert("<section style='margin:22px 0;padding:14px;background:#f6f7f6'><p style='margin:0 0 5px;font-weight:700'>关于作者</p><p style='margin:0;font-size:13px;color:#777'>在这里填写作者简介</p></section>") }
                            EditorTool("视频链接卡") { dialogValue = ""; linkInsertType = "video"; showLink = true }
                            EditorTool("音频链接卡") { dialogValue = ""; linkInsertType = "audio"; showLink = true }
                            if (selectedBlockHtml.contains("<table", true)) {
                                EditorTool("表格加行") { runJs("addTableRow()") }
                                EditorTool("表格删行") { runJs("removeTableRow()") }
                                EditorTool("表格加列") { runJs("addTableColumn()") }
                                EditorTool("表格删列") { runJs("removeTableColumn()") }
                            }
                        }
                    }
                    EditorPanel.SVG -> {
                        Text("SVG 与交互组件 · 插入后可在画布中继续编辑", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("SVG 呼吸圆点") { insert("<section style='margin:18px 0;text-align:center'><svg xmlns='http://www.w3.org/2000/svg' width='100%' height='72' viewBox='0 0 320 72' role='img'><circle cx='160' cy='36' r='12' fill='#159765'><animate attributeName='r' values='9;17;9' dur='1.8s' repeatCount='indefinite'/><animate attributeName='opacity' values='1;.45;1' dur='1.8s' repeatCount='indefinite'/></circle></svg><p style='margin:0;color:#888;font-size:12px'>动态呼吸效果</p></section>") }
                            EditorTool("SVG 流动线条") { insert("<section style='margin:18px 0'><svg xmlns='http://www.w3.org/2000/svg' width='100%' height='30' viewBox='0 0 320 30'><path d='M4 15 H316' stroke='#dce8e0' stroke-width='4' fill='none'/><path d='M4 15 H316' stroke='#159765' stroke-width='4' stroke-dasharray='40 280' fill='none'><animate attributeName='stroke-dashoffset' from='0' to='-320' dur='3s' repeatCount='indefinite'/></path></svg></section>") }
                            EditorTool("SVG 跳动标题") { insert("<section style='margin:18px 0;text-align:center'><svg xmlns='http://www.w3.org/2000/svg' width='100%' height='54' viewBox='0 0 320 54'><text x='160' y='37' text-anchor='middle' font-size='24' font-weight='700' fill='#159765'>拾万句<animate attributeName='opacity' values='1;.55;1' dur='2s' repeatCount='indefinite'/></text></svg></section>") }
                            EditorTool("点击展开内容") { insert("<details style='margin:16px 0;padding:13px 15px;background:#f3f7f4;border-radius:7px'><summary style='color:#168653;font-weight:700;cursor:pointer'>点击展开 / 收起</summary><p style='margin:10px 0 0;line-height:1.8'>这里填写点击后显示的补充内容。</p></details>") }
                            EditorTool("横向滑动卡片") { insert("<section style='display:flex;gap:10px;overflow-x:auto;white-space:normal;margin:16px 0;padding-bottom:8px'><div style='flex:0 0 78%;padding:16px;background:#f0f7f2;border-radius:8px'>卡片 01<br><span style='color:#888;font-size:12px'>左右滑动查看更多</span></div><div style='flex:0 0 78%;padding:16px;background:#f7f4ed;border-radius:8px'>卡片 02<br><span style='color:#888;font-size:12px'>第二张内容</span></div><div style='flex:0 0 78%;padding:16px;background:#f1f4fa;border-radius:8px'>卡片 03<br><span style='color:#888;font-size:12px'>第三张内容</span></div></section>") }
                            EditorTool("序列步骤") { insert("<section style='margin:18px 0;padding:14px;background:#f5f8f6;border-radius:8px'><p style='margin:0 0 10px;color:#159765;font-weight:700'>01　第一步</p><p style='margin:0 0 14px'>填写第一步说明</p><p style='margin:0 0 10px;color:#159765;font-weight:700'>02　第二步</p><p style='margin:0'>填写第二步说明</p></section>") }
                        }
                        Text("说明：SVG 动画依赖阅读端对 SVG/SMIL 的支持；交互组件以 HTML 原生交互为主，发布前需在公众号预览环境验证。", color = Color(0xFF929892), fontSize = 10.sp, modifier = Modifier.padding(top = 6.dp))
                    }
                    EditorPanel.STYLE -> {
                        Text("图文收藏 · 在图文模板卡片上点 ☆ 收藏后统一管理", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        if (categories.isEmpty() || vm.data.styles.none { it.isFavorite }) Text("暂无收藏。进入「图文模板」，点击模板卡片右上角的 ☆ 即可收藏。", color = Color.Gray, fontSize = 11.sp)
                        else {
                            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                categories.forEach { category -> EditorTool(category, activeCategory == category) { activeCategory = category } }
                            }
                            FlowRow(Modifier.fillMaxWidth().padding(top = 7.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                categoryStyles.forEach { style -> EditorTool(style.name) { insert(style.html) } }
                            }
                            if (selectedBlockHtml.isNotBlank() && !multiSelectMode) {
                                FlowRow(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    categoryStyles.forEach { style ->
                                        EditorTool("替换·${style.name}") { runJs("replaceSelectedBlockWithHtml(${JSONObject.quote(style.html)})") }
                                    }
                                }
                            }
                        }
                    }
                    EditorPanel.LAYER -> {
                        Text("图层与模块 · 当前文章正文的顶层内容列表", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 7.dp))
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                            EditorTool("刷新图层") { refreshLayerItems() }
                            Text("共 ${layerItems.size} 层", color = Color.Gray, fontSize = 10.sp)
                            Spacer(Modifier.weight(1f))
                            EditorTool(if (multiSelectMode) "退出多选" else "多选组合", multiSelectMode) {
                                multiSelectMode = !multiSelectMode
                                runJs("setMultiSelectMode(${multiSelectMode})")
                                selectedBlockHtml = ""
                            }
                        }
                        if (layerItems.isEmpty()) {
                            Text("点击「刷新图层」读取当前文章模块。可逐层选中、调整顺序、隐藏或锁定。", color = Color(0xFF8B948D), fontSize = 11.sp, modifier = Modifier.padding(vertical = 6.dp))
                        } else {
                            layerItems.forEachIndexed { index, layer ->
                                Row(
                                    Modifier.fillMaxWidth().padding(vertical = 3.dp).clip(RoundedCornerShape(8.dp))
                                        .background(if (index % 2 == 0) AppColors.Field else AppColors.Panel)
                                        .padding(horizontal = 7.dp, vertical = 5.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    Column(Modifier.weight(1f)) {
                                        Text("${index + 1}. ${layer.name.ifBlank { "未命名模块" }}", color = ink, fontSize = 10.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                        Text("${layer.tag.uppercase(Locale.ROOT)} · ${if (layer.visible) "显示" else "隐藏"} · ${if (layer.locked) "已锁定" else "可编辑"}", color = AppColors.TextDim, fontSize = 9.sp)
                                    }
                                    TextButton(onClick = { editor?.evaluateJavascript("selectLayer(${JSONObject.quote(layer.id)})", null) }, contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp)) { Text("选中", color = accent, fontSize = 9.sp) }
                                    TextButton(onClick = {
                                        val visible = !layer.visible
                                        runJs("setLayerVisibility(${JSONObject.quote(layer.id)},${visible})")
                                        layerItems = layerItems.map { if (it.id == layer.id) it.copy(visible = visible) else it }
                                    }, contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp)) { Text(if (layer.visible) "隐藏" else "显示", color = ink, fontSize = 9.sp) }
                                    TextButton(onClick = {
                                        val locked = !layer.locked
                                        runJs("setLayerLocked(${JSONObject.quote(layer.id)},${locked})")
                                        layerItems = layerItems.map { if (it.id == layer.id) it.copy(locked = locked) else it }
                                    }, contentPadding = PaddingValues(horizontal = 3.dp, vertical = 0.dp)) { Text(if (layer.locked) "解锁" else "锁定", color = ink, fontSize = 9.sp) }
                                    TextButton(onClick = { runJs("moveLayer(${JSONObject.quote(layer.id)},-1)"); refreshLayerItems() }, contentPadding = PaddingValues(horizontal = 2.dp, vertical = 0.dp)) { Text("↑", color = ink, fontSize = 12.sp) }
                                    TextButton(onClick = { runJs("moveLayer(${JSONObject.quote(layer.id)},1)"); refreshLayerItems() }, contentPadding = PaddingValues(horizontal = 2.dp, vertical = 0.dp)) { Text("↓", color = ink, fontSize = 12.sp) }
                                }
                            }
                        }
                        FlowRow(Modifier.fillMaxWidth().padding(top = 6.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            if (selectedBlockHtml.isNotBlank() && !multiSelectMode) {
                                EditorTool("模块样式") { showBlockProperties = true }
                                EditorTool("复制模块") { runJs("duplicateSelectedBlock()"); refreshLayerItems() }
                                EditorTool("删除模块") { runJs("deleteSelectedBlock()"); selectedBlockHtml = ""; refreshLayerItems() }
                                EditorTool("保存为样式") {
                                    vm.saveStyle(StyleModule(vm.newId(), "我的模块", "自定义组件", selectedBlockHtml, System.currentTimeMillis().toString()))
                                    vm.toast("已保存到「我的 - 样式」")
                                }
                            }
                            if (selectedBlockHtml.isNotBlank() && multiSelectMode) {
                                EditorTool("保存组合样式") {
                                    vm.saveStyle(StyleModule(vm.newId(), "组合组件", "组合组件", selectedBlockHtml, System.currentTimeMillis().toString(), type = "combination"))
                                    vm.toast("已保存组合组件到「我的 - 样式」")
                                    multiSelectMode = false
                                    runJs("setMultiSelectMode(false)")
                                }
                            }
                            EditorTool("插入链接") { dialogValue = ""; linkInsertType = "link"; showLink = true }
                        }
                    }
                    EditorPanel.CANVAS -> {
                        Text("画布设置 · 调整文章阅读区域的整体呈现", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        Text("内容宽度", color = ink, fontSize = 11.sp, modifier = Modifier.padding(top = 3.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("全宽") { runJs("root.style.width='100%';root.style.maxWidth='100%';root.style.margin='0 auto';") }
                            EditorTool("92%") { runJs("root.style.width='92%';root.style.maxWidth='680px';root.style.margin='0 auto';") }
                            EditorTool("680px") { runJs("root.style.width='100%';root.style.maxWidth='680px';root.style.margin='0 auto';") }
                            EditorTool("重置宽度") { runJs("root.style.width='';root.style.maxWidth='';root.style.margin='';") }
                        }
                        Text("画布背景", color = ink, fontSize = 11.sp, modifier = Modifier.padding(top = 7.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("纯白") { runJs("root.style.backgroundColor='#FFFFFF';") }
                            EditorTool("暖白") { runJs("root.style.backgroundColor='#FAF7F0';") }
                            EditorTool("浅灰") { runJs("root.style.backgroundColor='#F4F6F4';") }
                            EditorTool("透明") { runJs("root.style.backgroundColor='transparent';") }
                        }
                        Text("正文排版", color = ink, fontSize = 11.sp, modifier = Modifier.padding(top = 7.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("字号14") { runJs("root.querySelectorAll('p').forEach(e=>e.style.fontSize='14px');") }
                            EditorTool("字号16") { runJs("root.querySelectorAll('p').forEach(e=>e.style.fontSize='16px');") }
                            EditorTool("字号18") { runJs("root.querySelectorAll('p').forEach(e=>e.style.fontSize='18px');") }
                            EditorTool("行距1.6") { runJs("root.querySelectorAll('p').forEach(e=>e.style.lineHeight='1.6');") }
                            EditorTool("行距1.8") { runJs("root.querySelectorAll('p').forEach(e=>e.style.lineHeight='1.8');") }
                            EditorTool("行距2.0") { runJs("root.querySelectorAll('p').forEach(e=>e.style.lineHeight='2');") }
                        }
                        Text("画布留白", color = ink, fontSize = 11.sp, modifier = Modifier.padding(top = 7.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("无留白") { runJs("root.style.padding='0';") }
                            EditorTool("左右12") { runJs("root.style.padding='0 12px';") }
                            EditorTool("左右18") { runJs("root.style.padding='0 18px';") }
                            EditorTool("左右24") { runJs("root.style.padding='0 24px';") }
                        }
                        Text("以上画布参数只影响当前文章正文样式，不会修改其他文章。", color = Color(0xFF929892), fontSize = 10.sp, modifier = Modifier.padding(top = 6.dp))
                    }
                    EditorPanel.DOCUMENT -> {
                        Text("文章管理", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 7.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("立即保存") { saveDocument(true) }
                            EditorTool("文章信息") {
                                articleInfoSnapshot = listOf(subtitle, author, category, tagsText, summary, articleStatus, coverAssetId)
                                showArticleInfo = true
                            }
                            EditorTool("文章列表") { saveDocument(onComplete = { showArticleList = true }) }
                            EditorTool("版本记录") { saveDocument(); showRevisionList = true }
                            EditorTool("兼容检查") {
                                editor?.evaluateJavascript("document.getElementById('editor').innerHTML") { raw ->
                                    val current = runCatching { org.json.JSONTokener(raw ?: "null").nextValue() as? String }.getOrNull() ?: html
                                    compatibilityWarnings = articleCompatibilityWarnings(current)
                                    showCompatibilityReport = true
                                }
                            }
                        }
                        Text("导入与导出", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, top = 9.dp, bottom = 6.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("导入HTML") { htmlImporter.launch(arrayOf("text/html", "application/xhtml+xml", "text/plain")) }
                            EditorTool("导入Markdown") { markdownImporter.launch(arrayOf("text/markdown", "text/plain")) }
                            EditorTool("导入文章包") { articleJsonImporter.launch(arrayOf("application/json", "text/json")) }
                            EditorTool("更多导出/复制") { showMoreTools = true }
                        }
                    }
                    EditorPanel.TEMPLATE -> {
                        Text("图文模板 · 按标题、卡片、图片与布局分类选择", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp, bottom = 6.dp))
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("简约文章开头") { insert("<h1 style='font-size:25px;line-height:1.5;margin:18px 0'>在这里输入文章标题</h1><p style='color:#999;font-size:12px;margin-bottom:24px'>作者 · 拾万句</p><p>从这里开始写正文……</p>") }
                            EditorTool("杂志风标题") { insert("<section style='margin:24px 0;padding:18px 12px;border-top:2px solid #222;border-bottom:1px solid #aaa'><p style='font-size:24px;font-weight:700;letter-spacing:2px;margin:0'>SECTION TITLE</p><p style='font-size:11px;color:#999;letter-spacing:2px;margin:5px 0 0'>VOL. 01 / EDITORIAL</p></section>") }
                            EditorTool("文艺引用") { insert("<blockquote style='margin:24px 0;padding:18px;background:#f7f4ef;border:0;color:#685f54;font-size:17px;line-height:1.9'><p>“在这里写下一段值得被记住的话。”</p><p style='text-align:right;font-size:12px;color:#aaa'>—— 摘录</p></blockquote>") }
                            EditorTool("清单文章") { insert("<h2 style='font-size:22px;margin:24px 0 14px'>本期清单</h2><ol style='padding-left:22px;line-height:2'><li>第一项内容</li><li>第二项内容</li><li>第三项内容</li></ol>") }
                            EditorTool("结尾段落") { insert("<section style='margin:28px 0 12px;padding-top:16px;border-top:1px solid #e4e8e5'><p style='margin:0;color:#666;line-height:1.9'>愿你在平凡的日子里，也能找到值得珍藏的片刻。</p></section>") }

                        }
                    FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        EditorTool("导入模板包") { stylePackageImporter.launch(arrayOf("application/json", "text/json")) }
                        EditorTool("导出模板包") {
                            runCatching {
                            if (vm.data.styles.size > 100) error("样式超过 100 个，请分批导出")
                            if (vm.data.styles.sumOf { it.html.length } > 12 * 1024 * 1024) error("模板 HTML 总量超过 12 MB，请分批导出")
                            val pack = JSONObject().put("format", "shiwanju.styles.v1")
                            val rows = org.json.JSONArray()
                            vm.data.styles.forEach { style ->
                                rows.put(JSONObject().put("id", style.id).put("name", style.name).put("category", style.category)
                                    .put("html", style.html).put("isFavorite", style.isFavorite).put("type", style.type)
                                    .put("thumbnail", style.thumbnail).put("tags", org.json.JSONArray(style.tags)))
                            }
                            val assets = org.json.JSONArray()
                            var totalBytes = 0L
                            vm.data.mediaAssets.filter { asset -> vm.data.styles.any { it.html.contains(asset.id) || it.thumbnail == asset.id } }.forEach { asset ->
                                val root = File(context.filesDir, "article_media").canonicalFile
                                val file = File(context.filesDir, asset.relativePath).canonicalFile
                                if (file.path.startsWith(root.path + File.separator) && file.isFile) {
                                    val bytes = file.readBytes()
                                    totalBytes += bytes.size
                                    if (bytes.size > 12 * 1024 * 1024 || totalBytes > 36L * 1024 * 1024) error("模板引用图片超过导出容量限制")
                                    assets.put(JSONObject().put("id", asset.id).put("fileName", asset.fileName)
                                        .put("mimeType", asset.mimeType).put("base64", Base64.encodeToString(bytes, Base64.NO_WRAP)))
                                }
                            }
                            pack.put("styles", rows).put("assets", assets)
                            pendingExportStyleJson = pack.toString(2)
                            stylePackageExporter.launch("拾万句-样式模板包.json")
                            }.onFailure { vm.toast("模板包导出失败：${it.message ?: "无法读取素材"}") }
                        }
                    }
                    Text("模板类型", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 8.dp, bottom = 5.dp))
                    FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        listOf("全部", "标题", "卡片", "图片", "布局").forEach { kind ->
                            EditorTool(kind, templateKindFilter == if (kind == "全部") "" else kind) { templateKindFilter = if (kind == "全部" || templateKindFilter == kind) "" else kind }
                        }
                    }
                    Text("我的模板库", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 8.dp, bottom = 5.dp))
                    FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        EditorTool("整篇模板", templateLibraryTab == "full") { templateLibraryTab = "full"; templateTagFilter = "" }
                        EditorTool("局部组件", templateLibraryTab == "component") { templateLibraryTab = "component"; templateTagFilter = "" }
                        EditorTool("组合组件", templateLibraryTab == "combination") { templateLibraryTab = "combination"; templateTagFilter = "" }
                    }
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp), verticalAlignment = Alignment.CenterVertically) {
                        OutlinedTextField(templateSearchText, { templateSearchText = it }, modifier = Modifier.weight(1f), singleLine = true, placeholder = { Text("搜索模板名称或标签") })
                        EditorTool(if (favoriteTemplatesOnly) "仅收藏" else "全部", favoriteTemplatesOnly) { favoriteTemplatesOnly = !favoriteTemplatesOnly }
                        EditorTool(if (templateSortByName) "排序：按名称" else "排序：按更新时间") { templateSortByName = !templateSortByName }
                    }
                    if (availableTemplateTags.isNotEmpty()) {
                        FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            EditorTool("全部分类", templateTagFilter.isBlank()) { templateTagFilter = "" }
                            availableTemplateTags.forEach { tag ->
                                EditorTool(tag, templateTagFilter == tag) { templateTagFilter = if (templateTagFilter == tag) "" else tag }
                            }
                        }
                    }
                    if (filteredTemplates.isEmpty()) Text("暂无匹配模板，可将当前文章保存为整篇模板", color = Color.Gray, fontSize = 11.sp)
                    else {
                        filteredTemplates.chunked(2).forEach { rowTemplates ->
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                rowTemplates.forEach { template ->
                                    val sample = template.html.replace(Regex("<[^>]*>"), " ").replace("&nbsp;", " ")
                                        .replace(Regex("\\s+"), " ").trim().ifBlank { "图文排版模板" }.take(72)
                                    Surface(
                                        modifier = Modifier.weight(1f).clickable { templatePreview = template },
                                        shape = RoundedCornerShape(9.dp),
                                        color = Color(0xFFF4F7F5),
                                        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFE4EBE6))
                                    ) {
                                        Column(Modifier.fillMaxWidth().padding(10.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                            val isFullTemplate = template.type == "full" || template.category == "整篇模板"
                                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                                Text(if (isFullTemplate) "整篇模板" else if (template.type == "combination") "组合组件" else "局部组件", color = accent, fontSize = 9.sp, fontWeight = FontWeight.Medium)
                                                Text(if (template.isFavorite) "★" else "☆", color = if (template.isFavorite) accent else Color.Gray, modifier = Modifier.clickable { vm.saveStyle(template.copy(isFavorite = !template.isFavorite)) })
                                            }
                                            Text(template.name, color = ink, fontSize = 12.sp, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                            val thumbnailAsset = vm.data.mediaAssets.firstOrNull { it.id == template.thumbnail }
                                            val thumbnailBitmap = remember(template.thumbnail, thumbnailAsset?.relativePath) {
                                                thumbnailAsset?.let { asset ->
                                                    runCatching {
                                                        val root = File(context.filesDir, "article_media").canonicalFile
                                                        val file = File(context.filesDir, asset.relativePath).canonicalFile
                                                        if (file.path.startsWith(root.path + File.separator) && file.isFile) decodeArticleAssetPreview(file) else null
                                                    }.getOrNull()
                                                }
                                            }
                                            if (thumbnailBitmap != null) {
                                                Image(thumbnailBitmap.asImageBitmap(), contentDescription = template.name + "预览缩略图",
                                                    modifier = Modifier.fillMaxWidth().height(92.dp).clip(RoundedCornerShape(5.dp)), contentScale = ContentScale.Crop)
                                            } else {
                                                Surface(modifier = Modifier.fillMaxWidth().height(54.dp), color = Color(0xFFE9F0EB), shape = RoundedCornerShape(5.dp)) {
                                                    Box(contentAlignment = Alignment.Center) {
                                                        Text("打开预览后自动生成缩略图", color = Color(0xFF829087), fontSize = 9.sp)
                                                    }
                                                }
                                            }
                                            Text(sample, color = Color(0xFF68756D), fontSize = 10.sp, lineHeight = 14.sp, maxLines = 3, overflow = TextOverflow.Ellipsis)
                                            if (template.tags.isNotEmpty()) Text(template.tags.take(2).joinToString(" · "), color = Color(0xFF87958C), fontSize = 9.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                                                TextButton(onClick = { templatePreview = template }, contentPadding = PaddingValues(horizontal = 5.dp, vertical = 0.dp)) { Text("预览", fontSize = 10.sp, color = accent) }
                                                if (isFullTemplate) {
                                                    TextButton(onClick = { fullTemplateConfirm = template }, contentPadding = PaddingValues(horizontal = 5.dp, vertical = 0.dp)) { Text("应用全文", fontSize = 10.sp, color = accent) }
                                                } else {
                                                    TextButton(onClick = { insert(template.html) }, contentPadding = PaddingValues(horizontal = 5.dp, vertical = 0.dp)) { Text("插入", fontSize = 10.sp, color = accent) }
                                                    if (selectedBlockHtml.isNotBlank() && !multiSelectMode) {
                                                        TextButton(onClick = { runJs("replaceSelectedBlockWithHtml(${JSONObject.quote(template.html)})") }, contentPadding = PaddingValues(horizontal = 5.dp, vertical = 0.dp)) { Text("替换模块", fontSize = 10.sp, color = accent) }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                                if (rowTemplates.size == 1) Spacer(Modifier.weight(1f))
                        }
                    }
                }
                    }
                }
            }
                    }

                    }
                // Fixed primary navigation dock, as a sibling of the expandable tool sheet.
                Row(
                    Modifier.fillMaxWidth().height(50.dp)
                        .background(Color(0xFF181818)),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceAround
                ) {
                    Row(
                        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceAround
                    ) {
                        EditorPanel.values().filterNot { it in templateSubPanels }.forEach { panel ->
                            TextButton(
                                onClick = {
                                    showTemplateSubnav = panel == EditorPanel.TEMPLATE
                                    activePanel = if (panel == EditorPanel.TEMPLATE) templateSubPanel else panel
                                    floatingMenu = ""
                                    if (panel == EditorPanel.CANVAS) {
                                        showToolPopup = false
                                        showCanvasPopup = true
                                        toolPopupOffset = Offset.Zero
                                    } else {
                                        showCanvasPopup = false
                                        showToolPopup = true
                                        toolPanelHeightDp = if (panel == EditorPanel.TEXT2) 330f else 180f
                                    }
                                    if (panel == EditorPanel.LAYER) refreshLayerItems()
                                },
                                contentPadding = PaddingValues(horizontal = 9.dp, vertical = 3.dp)
                            ) {
                                Text(
                                    panel.label,
                                    color = if ((activePanel == panel || (panel == EditorPanel.TEMPLATE && showTemplateSubnav)) && (showToolPopup || showCanvasPopup)) Color.White else Color(0xFF777777),
                                    fontSize = if (activePanel == panel) 15.sp else 13.sp,
                                    fontWeight = if (activePanel == panel) FontWeight.Bold else FontWeight.Normal,
                                    maxLines = 1
                                )
                            }
                        }
                    }
                }

                    }
                    }
                    }
                    Box(
                        Modifier.fillMaxWidth().height(26.dp)
                            .pointerInput(Unit) {
                                detectDragGestures { change, dragAmount ->
                                    change.consume()
                                    val deltaDp = with(toolPanelDensity) { dragAmount.y.toDp() }
                                    toolPanelHeightDp = (toolPanelHeightDp - deltaDp.value).coerceIn(100f, 400f)
                                }
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Box(Modifier.width(42.dp).height(4.dp).background(Color(0xFF777777), RoundedCornerShape(50)))
                    }
                }
            }
            }
        }

    if (showCanvasPopup && !previewMode) {
        Dialog(onDismissRequest = { showCanvasPopup = false }) {
            var dragOffset by remember { mutableStateOf(Offset.Zero) }
            Surface(
                modifier = Modifier.fillMaxWidth(0.92f).offset { IntOffset(dragOffset.x.toInt(), dragOffset.y.toInt()) },
                shape = RoundedCornerShape(14.dp), color = Color(0xFF181818), shadowElevation = 18.dp
            ) {
                Column {
                    Row(
                        Modifier.fillMaxWidth().height(44.dp).background(Color(0xFF222222))
                            .pointerInput(Unit) {
                                detectDragGestures { change, drag ->
                                    change.consume()
                                    dragOffset = Offset(dragOffset.x + drag.x, dragOffset.y + drag.y)
                                }
                            }.padding(horizontal = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("⠿", color = AppColors.Theme, fontSize = 17.sp)
                        Text("画布工具", color = Color.White, fontSize = 13.sp, modifier = Modifier.weight(1f).padding(start = 8.dp))
                        IconButton(onClick = { showCanvasPopup = false }) { Icon(Icons.Outlined.Close, contentDescription = "关闭画布工具", tint = Color.White) }
                        IconButton(onClick = { showCanvasPopup = false }) { Icon(Icons.Outlined.Check, contentDescription = "确定画布设置", tint = AppColors.Theme) }
                    }
                    CompositionLocalProvider(LocalEditorToolDark provides true) {
                        Column(Modifier.fillMaxWidth().heightIn(min = 100.dp, max = 250.dp).verticalScroll(rememberScrollState()).padding(12.dp)) {
                            Text("内容宽度", color = Color(0xFFBBBBBB), fontSize = 11.sp)
                            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                EditorTool("全宽") { runJs("root.style.width='100%';root.style.maxWidth='100%';root.style.margin='0 auto';") }
                                EditorTool("92%") { runJs("root.style.width='92%';root.style.maxWidth='680px';root.style.margin='0 auto';") }
                                EditorTool("680px") { runJs("root.style.width='100%';root.style.maxWidth='680px';root.style.margin='0 auto';") }
                                EditorTool("重置宽度") { runJs("root.style.width='';root.style.maxWidth='';root.style.margin='';") }
                            }
                            Text("画布留白", color = Color(0xFFBBBBBB), fontSize = 11.sp, modifier = Modifier.padding(top = 10.dp))
                            FlowRow(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                EditorTool("默认") { runJs("root.style.padding='30px 22px 120px';") }
                                EditorTool("紧凑") { runJs("root.style.padding='18px 14px 80px';") }
                                EditorTool("宽松") { runJs("root.style.padding='42px 28px 140px';") }
                            }
                        }
                    }
                }
            }
        }
    }
    if (showHtmlImportPreview) {
        Dialog(onDismissRequest = { showHtmlImportPreview = false }) {
            Surface(shape = RoundedCornerShape(14.dp), color = Color.White, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("HTML 导入预览", color = ink, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                    Text("已清理脚本、事件属性和危险链接。请选择新建文章或替换当前正文。", color = Color.Gray, fontSize = 11.sp)
                    AndroidView(
                        modifier = Modifier.fillMaxWidth().height(360.dp),
                        factory = { ctx -> WebView(ctx).apply {
                            settings.javaScriptEnabled = false
                            settings.domStorageEnabled = false
                            setBackgroundColor(android.graphics.Color.WHITE)
                            loadDataWithBaseURL("https://editor.local/", pendingImportedHtml, "text/html", "UTF-8", null)
                        } },
                        update = { view -> view.loadDataWithBaseURL("https://editor.local/", pendingImportedHtml, "text/html", "UTF-8", null) }
                    )
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        TextButton(onClick = { showHtmlImportPreview = false }) { Text("取消", color = Color.Gray) }
                        TextButton(onClick = {
                            showArticleList = false
                            html = pendingImportedHtml
                            editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(pendingImportedHtml)});setEditable(true);", null)
                            pendingSave++
                            showHtmlImportPreview = false
                            vm.toast("已替换当前文章正文")
                        }) { Text("替换正文", color = accent) }
                        TextButton(onClick = {
                            newArticle()
                            title = "导入文章"
                            subtitle = ""; summary = ""; author = ""; category = ""; tagsText = ""
                            articleStatus = "draft"; coverAssetId = ""
                            html = pendingImportedHtml
                            editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(pendingImportedHtml)});setEditable(true);", null)
                            pendingSave++
                            showHtmlImportPreview = false
                            vm.toast("HTML 已作为新文章导入")
                        }) { Text("新建文章导入", color = accent) }
                    }
                }
            }
        }
    }
    if (templatePreview != null) {
        val template = templatePreview!!
        Dialog(onDismissRequest = { templatePreview = null }) {
            Surface(shape = RoundedCornerShape(14.dp), color = Color.White, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(template.name, color = ink, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
                    AndroidView(
                        modifier = Modifier.fillMaxWidth().height(380.dp),
                        factory = { ctx -> WebView(ctx).apply {
                            settings.javaScriptEnabled = false
                            settings.domStorageEnabled = false
                            settings.allowFileAccess = false
                            settings.allowContentAccess = false
                            setBackgroundColor(android.graphics.Color.WHITE)
                            webViewClient = object : WebViewClient() {
                                override fun onPageFinished(view: WebView?, url: String?) {
                                    super.onPageFinished(view, url)
                                    if (template.thumbnail.isBlank()) view?.postDelayed({ view?.let { captureTemplateThumbnail(it, ctx, template, vm) } }, 350)
                                }
                            }
                            loadDataWithBaseURL("https://editor.local/", template.html, "text/html", "UTF-8", null)
                        } },
                        update = { view ->
                            if (view.url == null && template.thumbnail.isBlank()) view.loadDataWithBaseURL("https://editor.local/", template.html, "text/html", "UTF-8", null)
                        }
                    )
                    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(2.dp)) {
                        if (template.origin == "user") {
                            TextButton(onClick = { dialogValue = template.name; editingTemplate = template; templatePreview = null }, contentPadding = PaddingValues(horizontal = 4.dp)) { Text("重命名", fontSize = 10.sp, color = accent) }
                            TextButton(onClick = { templateHtmlDraft = template.html; editingTemplateContent = template; templatePreview = null }, contentPadding = PaddingValues(horizontal = 4.dp)) { Text("编辑内容", fontSize = 10.sp, color = accent) }
                            TextButton(onClick = {
                                vm.saveStyle(template.copy(id = vm.newId(), name = template.name + " 副本", categoryId = "", origin = "user", updatedAt = System.currentTimeMillis().toString()))
                                vm.toast("已复制到我的模板库")
                            }, contentPadding = PaddingValues(horizontal = 4.dp)) { Text("复制", fontSize = 10.sp, color = accent) }
                            TextButton(onClick = { deletingTemplate = template; templatePreview = null }, contentPadding = PaddingValues(horizontal = 4.dp)) { Text("删除", fontSize = 10.sp, color = Color(0xFFCC5555)) }
                        } else {
                            TextButton(onClick = {
                                vm.saveStyle(template.copy(id = vm.newId(), name = template.name + " 副本", categoryId = "", origin = "user", updatedAt = System.currentTimeMillis().toString()))
                                vm.toast("已复制到我的模板库")
                            }, contentPadding = PaddingValues(horizontal = 4.dp)) { Text("复制到我的", fontSize = 10.sp, color = accent) }
                        }
                        TextButton(onClick = { templatePreview = null }, contentPadding = PaddingValues(horizontal = 4.dp)) { Text("关闭", fontSize = 10.sp, color = accent) }
                        if (template.type == "full" || template.category == "整篇模板") {
                            TextButton(onClick = { fullTemplateConfirm = template; templatePreview = null }) { Text("应用全文", color = accent) }
                        } else {
                            TextButton(onClick = { insert(template.html); templatePreview = null }) { Text("插入组件", color = accent) }
                            if (selectedBlockHtml.isNotBlank() && !multiSelectMode) {
                                TextButton(onClick = { runJs("replaceSelectedBlockWithHtml(${JSONObject.quote(template.html)})"); templatePreview = null }) { Text("替换模块", color = accent) }
                            }
                        }
                    }
                }
            }
        }
    }
    if (editingTemplate != null) {
        val target = editingTemplate!!
        EditorInputDialog("重命名模板", "输入新的模板名称", dialogValue, { dialogValue = it }, {
            val newName = dialogValue.trim()
            if (newName.isBlank()) vm.toast("模板名称不能为空")
            else {
                vm.saveStyle(target.copy(name = newName, updatedAt = System.currentTimeMillis().toString()))
                editingTemplate = null
                vm.toast("模板名称已更新")
            }
        }) { editingTemplate = null }
    }
    if (editingTemplateContent != null) {
        val target = editingTemplateContent!!
        Dialog(onDismissRequest = { editingTemplateContent = null }) {
            Surface(shape = RoundedCornerShape(14.dp), color = Color.White, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("编辑模板内容", color = ink, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                    Text(target.name, color = Color.Gray, fontSize = 12.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    OutlinedTextField(
                        value = templateHtmlDraft,
                        onValueChange = { templateHtmlDraft = it },
                        modifier = Modifier.fillMaxWidth().heightIn(min = 220.dp, max = 440.dp),
                        placeholder = { Text("在此编辑模板 HTML") },
                        textStyle = androidx.compose.ui.text.TextStyle(fontSize = 12.sp),
                        minLines = 10,
                        maxLines = 18
                    )
                    Text("保存时会过滤脚本、内嵌框架和危险链接；模板预览缩略图会在下次打开时重新生成。", color = Color.Gray, fontSize = 11.sp)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        TextButton(onClick = { editingTemplateContent = null }) { Text("取消", color = Color.Gray) }
                        TextButton(onClick = {
                            if (templateHtmlDraft.isBlank()) {
                                vm.toast("模板内容不能为空")
                            } else {
                                val safeHtml = sanitizeArticleHtml(templateHtmlDraft)
                                if (safeHtml.isBlank()) {
                                    vm.toast("模板内容无效，未保存")
                                } else {
                                    vm.saveStyle(target.copy(html = safeHtml, thumbnail = "", updatedAt = System.currentTimeMillis().toString()))
                                    editingTemplateContent = null
                                    templateHtmlDraft = ""
                                    vm.toast("模板内容已保存")
                                }
                            }
                        }) { Text("保存内容", color = accent) }
                    }
                }
            }
        }
    }
    if (deletingTemplate != null) {
        val target = deletingTemplate!!
        AlertDialog(
            onDismissRequest = { deletingTemplate = null },
            title = { Text("删除模板？") },
            text = { Text("确定删除「${target.name}」吗？删除后无法恢复。") },
            confirmButton = {
                TextButton(onClick = {
                    vm.deleteStyle(target.id)
                    deletingTemplate = null
                    vm.toast("模板已删除")
                }) { Text("删除", color = Color(0xFFCC5555)) }
            },
            dismissButton = { TextButton(onClick = { deletingTemplate = null }) { Text("取消") } }
        )
    }
    if (previewAsset != null) {
        Dialog(onDismissRequest = { previewAsset = null }) {
            Surface(shape = RoundedCornerShape(14.dp), color = Color.White, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(previewAsset!!.fileName, color = ink, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                    if (previewBitmap != null) {
                        Image(previewBitmap.asImageBitmap(), contentDescription = previewAsset!!.fileName,
                            modifier = Modifier.fillMaxWidth().heightIn(max = 440.dp), contentScale = ContentScale.Fit)
                    } else Text("图片文件不存在或无法解码", color = Color.Gray, fontSize = 12.sp)
                    Text("${previewAsset!!.mimeType} · ${previewAsset!!.sizeBytes / 1024} KB", color = Color.Gray, fontSize = 11.sp)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        TextButton(onClick = { previewAsset = null }) { Text("关闭", color = accent) }
                        TextButton(onClick = {
                            val asset = previewAsset!!
                            insert("<p><img src='https://editor.local/assets/${asset.id}' alt='${asset.fileName}' style='max-width:100%;height:auto;display:block;margin:14px auto'></p>")
                            previewAsset = null
                        }) { Text("插入文章", color = accent) }
                    }
                }
            }
        }
    }
    if (showImageAlt) EditorInputDialog("图片替代文字", "描述图片内容", dialogValue, { dialogValue = it }, {
        runJs("setSelectedImageAlt(${JSONObject.quote(dialogValue)});")
        showImageAlt = false
    }) { showImageAlt = false }
    if (showImage) EditorInputDialog("插入图片", "输入 https:// 开头的图片地址", dialogValue, { dialogValue = it }, {
        val url = dialogValue.trim()
        if (url.startsWith("https://")) insert("<img src='${url.replace("'", "%27")}' alt='图片' style='max-width:100%;height:auto;display:block;margin:14px auto'>")
        else vm.toast("请输入有效的 HTTPS 图片地址，避免混合内容被 WebView 拦截")
        showImage = false
    }) { showImage = false }
    if (showLink) EditorInputDialog(if (linkInsertType == "link") "插入链接" else if (linkInsertType == "video") "视频链接卡" else "音频链接卡", "输入 https:// 开头的网址", dialogValue, { dialogValue = it }, {
        val url = dialogValue.trim().replace("'", "%27")
        if (url.startsWith("https://") || url.startsWith("http://")) {
            when (linkInsertType) {
                "video" -> insert("<section style='margin:18px 0;padding:14px;background:#f3f6f4;border:1px solid #e0e8e2;border-radius:6px'><p style='margin:0 0 6px;font-weight:700;color:#2b6c4a'>视频内容</p><a href='${url}' target='_blank' style='color:#16865a'>点击打开视频</a><p style='margin:6px 0 0;color:#999;font-size:11px'>视频以外链卡片形式呈现，是否可访问取决于目标平台</p></section>")
                "audio" -> insert("<section style='margin:18px 0;padding:14px;background:#f7f4ed;border-radius:6px'><p style='margin:0 0 6px;font-weight:700;color:#79623c'>音频内容</p><a href='${url}' target='_blank' style='color:#9a7435'>点击收听音频</a><p style='margin:6px 0 0;color:#999;font-size:11px'>音频以外链卡片形式呈现，不代表公众号可直接播放</p></section>")
                else -> insert("<a href='${url}' target='_blank'>链接文字</a>")
            }
        } else vm.toast("请输入有效的 http/https 网址")
        showLink = false
        linkInsertType = "link"
    }) { showLink = false; linkInsertType = "link" }
    if (showDeleteConfirm != null) {
        val target = showDeleteConfirm!!
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = null },
            title = { Text("删除文章？") },
            text = { Text("将删除「${target.title}」及其版本快照。此操作不可撤销。") },
            confirmButton = { TextButton(onClick = {
                vm.deleteArticle(target.id)
                showDeleteConfirm = null
                if (target.id == articleId) {
                    articleId = vm.newId(); title = "未命名文章"; html = "<p><br></p>"
                    subtitle = ""; summary = ""; author = ""; category = ""; tagsText = ""
                    articleStatus = "draft"; coverAssetId = ""; previewMode = false
                    editor?.evaluateJavascript("setEditorHtml('<p><br></p>');setEditable(true);setPreviewInfo('','','','');", null)
                    saved = false; pendingSave++
                }
            }) { Text("删除", color = Color(0xFFCC5555)) } },
            dismissButton = { TextButton(onClick = { showDeleteConfirm = null }) { Text("取消") } }
        )
    }
    if (showRevisionList) {
        val revisions = vm.data.articleRevisions.filter { it.articleId == articleId }.sortedByDescending { it.createdAt }
        AlertDialog(
            onDismissRequest = { showRevisionList = false },
            title = { Text("历史版本（最近 30 个）") },
            text = {
                Column(Modifier.fillMaxWidth().heightIn(max = 420.dp).verticalScroll(rememberScrollState())) {
                    if (revisions.isEmpty()) Text("暂无历史快照。文章内容发生变化并自动保存后会生成快照。", color = Color.Gray, fontSize = 12.sp)
                    revisions.forEach { revision ->
                        Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(revision.title.ifBlank { "未命名文章" }, fontSize = 13.sp, color = ink)
                                Text("${formatArticleTimestamp(revision.createdAt)} · ${revision.html.replace(Regex("<[^>]*>"), "").length} 字 · ${revision.category.ifBlank { "未分类" }}", fontSize = 10.sp, color = Color.Gray)
                            }
                            TextButton(onClick = { revisionPreview = revision }) { Text("预览", color = ink) }
                            TextButton(onClick = {
                                if (vm.restoreArticleRevision(revision)) {
                                    title = revision.title; html = revision.html
                                    subtitle = revision.subtitle; summary = revision.summary; author = revision.author
                                    coverAssetId = revision.coverAssetId; category = revision.category
                                    tagsText = revision.tags.joinToString(", "); articleStatus = revision.status
                                    editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(revision.html)});setEditable(true);", null)
                                    showRevisionList = false
                                    pendingSave++
                                    vm.toast("已恢复历史版本（恢复前内容已另存为快照）")
                                }
                            }) { Text("恢复", color = accent) }
                        }
                        HorizontalDivider(color = Color(0xFFE9ECE9))
                    }
                }
            },
            confirmButton = { TextButton(onClick = { showRevisionList = false }) { Text("关闭") } }
        )
    }
    if (revisionPreview != null) {
        val revision = revisionPreview!!
        val previewHtml = "<!doctype html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>body{font:16px/1.9 sans-serif;padding:20px;color:#333}img{max-width:100%;height:auto}</style></head><body><h1>${escapeMarkdownText(revision.title)}</h1><p>${escapeMarkdownText(revision.subtitle)}</p><p style='color:#999;font-size:12px'>${escapeMarkdownText(revision.author)} · ${escapeMarkdownText(revision.category)}</p>${revision.html}</body></html>"
        Dialog(onDismissRequest = { revisionPreview = null }) {
            Surface(shape = RoundedCornerShape(14.dp), color = Color.White, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("历史版本预览 · ${formatArticleTimestamp(revision.createdAt)}", color = ink, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                    AndroidView(
                        modifier = Modifier.fillMaxWidth().height(400.dp),
                        factory = { ctx -> WebView(ctx).apply {
                            settings.javaScriptEnabled = false
                            settings.domStorageEnabled = false
                            setBackgroundColor(android.graphics.Color.WHITE)
                            loadDataWithBaseURL("https://editor.local/", previewHtml, "text/html", "UTF-8", null)
                        } },
                        update = { view -> view.loadDataWithBaseURL("https://editor.local/", previewHtml, "text/html", "UTF-8", null) }
                    )
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        TextButton(onClick = { revisionPreview = null }) { Text("关闭", color = Color.Gray) }
                        TextButton(onClick = {
                            if (vm.restoreArticleRevision(revision)) {
                                title = revision.title; html = revision.html
                                subtitle = revision.subtitle; summary = revision.summary; author = revision.author
                                coverAssetId = revision.coverAssetId; category = revision.category
                                tagsText = revision.tags.joinToString(", "); articleStatus = revision.status
                                editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(revision.html)});setEditable(true);", null)
                                showRevisionList = false; revisionPreview = null; pendingSave++
                                vm.toast("已恢复历史版本（恢复前内容已另存为快照）")
                            }
                        }) { Text("恢复此版本", color = accent) }
                    }
                }
            }
        }
    }
    if (fullTemplateConfirm != null) {
        val template = fullTemplateConfirm!!
        AlertDialog(
            onDismissRequest = { fullTemplateConfirm = null },
            title = { Text("应用整篇模板？") },
            text = { Text("将用「${template.name}」替换当前文章正文。建议先保存当前文章。") },
            confirmButton = { TextButton(onClick = {
                html = template.html
                editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(template.html)});", null)
                pendingSave++
                fullTemplateConfirm = null
                vm.toast("整篇模板已应用")
            }) { Text("替换正文", color = Color(0xFFCC5555)) } },
            dismissButton = { TextButton(onClick = { fullTemplateConfirm = null }) { Text("取消") } }
        )
    }
    if (showFindReplace) {
        AlertDialog(
            onDismissRequest = { showFindReplace = false },
            title = { Text("查找与替换") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(findValue, { findValue = it }, label = { Text("查找内容") }, singleLine = true)
                    OutlinedTextField(replaceValue, { replaceValue = it }, label = { Text("替换为") }, singleLine = true)
                    Text("仅替换正文文本，不修改 HTML 标签、链接地址和图片属性。", color = Color.Gray, fontSize = 11.sp)
                }
            },
            confirmButton = { TextButton(onClick = {
                if (findValue.isBlank()) vm.toast("请输入查找内容")
                else {
                    runJs("replaceAllText(${JSONObject.quote(findValue)},${JSONObject.quote(replaceValue)})")
                    showFindReplace = false
                    vm.toast("已执行正文文本替换")
                }
            }) { Text("全部替换", color = accent) } },
            dismissButton = { TextButton(onClick = { showFindReplace = false }) { Text("取消") } }
        )
    }
    if (showCustomImageCrop && customCropAsset != null) {
        Dialog(onDismissRequest = { showCustomImageCrop = false; customCropAsset = null }) {
            Surface(shape = RoundedCornerShape(14.dp), color = Color.White, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Text("自定义像素裁切", color = ink, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                    Text(customCropAsset!!.fileName, color = Color.Gray, fontSize = 11.sp, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    if (customCropPreviewBitmap != null) {
                        val cropBitmap = customCropPreviewBitmap!!
                        val latestCropLeft by rememberUpdatedState(cropLeft)
                        val latestCropTop by rememberUpdatedState(cropTop)
                        val latestCropWidth by rememberUpdatedState(cropWidth)
                        val latestCropHeight by rememberUpdatedState(cropHeight)
                        Box(
                            modifier = Modifier.fillMaxWidth()
                                .aspectRatio(cropBitmap.width.toFloat() / cropBitmap.height.toFloat())
                                .clip(RoundedCornerShape(6.dp))
                        ) {
                            Image(
                                cropBitmap.asImageBitmap(),
                                contentDescription = "原图与裁切区域",
                                modifier = Modifier.fillMaxSize(),
                                contentScale = ContentScale.FillBounds
                            )
                            Canvas(
                                modifier = Modifier.fillMaxSize().pointerInput(cropBitmap) {
                                    var dragMode = -1
                                    detectDragGestures(
                                        onDragStart = { point ->
                                            val w = size.width.toFloat().coerceAtLeast(1f)
                                            val h = size.height.toFloat().coerceAtLeast(1f)
                                            val l = latestCropLeft * w
                                            val t = latestCropTop * h
                                            val r = (latestCropLeft + latestCropWidth) * w
                                            val b = (latestCropTop + latestCropHeight) * h
                                            val handles = listOf(
                                                Offset(l, t), Offset(r, t), Offset(l, b), Offset(r, b)
                                            )
                                            val radius = 30.dp.toPx()
                                            val nearest = handles.indices.minByOrNull { i ->
                                                val dx = point.x - handles[i].x
                                                val dy = point.y - handles[i].y
                                                dx * dx + dy * dy
                                            }
                                            dragMode = if (nearest != null) {
                                                val dx = point.x - handles[nearest].x
                                                val dy = point.y - handles[nearest].y
                                                if (dx * dx + dy * dy <= radius * radius) nearest
                                                else if (point.x in l..r && point.y in t..b) 4 else -1
                                            } else -1
                                        },
                                        onDragEnd = { dragMode = -1 },
                                        onDragCancel = { dragMode = -1 },
                                        onDrag = { change, amount ->
                                            change.consume()
                                            val dx = amount.x / size.width.toFloat().coerceAtLeast(1f)
                                            val dy = amount.y / size.height.toFloat().coerceAtLeast(1f)
                                            val minSide = 0.10f
                                            when (dragMode) {
                                                0 -> {
                                                    val right = latestCropLeft + latestCropWidth
                                                    val bottom = latestCropTop + latestCropHeight
                                                    cropLeft = (latestCropLeft + dx).coerceIn(0f, right - minSide)
                                                    cropTop = (latestCropTop + dy).coerceIn(0f, bottom - minSide)
                                                    cropWidth = right - cropLeft
                                                    cropHeight = bottom - cropTop
                                                }
                                                1 -> {
                                                    val bottom = latestCropTop + latestCropHeight
                                                    val right = (latestCropLeft + latestCropWidth + dx).coerceIn(latestCropLeft + minSide, 1f)
                                                    cropTop = (latestCropTop + dy).coerceIn(0f, bottom - minSide)
                                                    cropWidth = right - cropLeft
                                                    cropHeight = bottom - cropTop
                                                }
                                                2 -> {
                                                    val right = latestCropLeft + latestCropWidth
                                                    val bottom = (latestCropTop + latestCropHeight + dy).coerceIn(latestCropTop + minSide, 1f)
                                                    cropLeft = (latestCropLeft + dx).coerceIn(0f, right - minSide)
                                                    cropWidth = right - cropLeft
                                                    cropHeight = bottom - cropTop
                                                }
                                                3 -> {
                                                    cropWidth = (latestCropWidth + dx).coerceIn(minSide, 1f - latestCropLeft)
                                                    cropHeight = (latestCropHeight + dy).coerceIn(minSide, 1f - latestCropTop)
                                                }
                                                4 -> {
                                                    cropLeft = (latestCropLeft + dx).coerceIn(0f, 1f - latestCropWidth)
                                                    cropTop = (latestCropTop + dy).coerceIn(0f, 1f - latestCropHeight)
                                                }
                                            }
                                        }
                                    )
                                }
                            ) {
                                val w = size.width
                                val h = size.height
                                val l = cropLeft * w
                                val t = cropTop * h
                                val r = (cropLeft + cropWidth) * w
                                val b = (cropTop + cropHeight) * h
                                val shade = Color.Black.copy(alpha = 0.48f)
                                drawRect(shade, Offset.Zero, Size(w, t))
                                drawRect(shade, Offset(0f, b), Size(w, h - b))
                                drawRect(shade, Offset(0f, t), Size(l, b - t))
                                drawRect(shade, Offset(r, t), Size(w - r, b - t))
                                drawRect(Color.White, Offset(l, t), Size(r - l, b - t), style = Stroke(2.dp.toPx()))
                                val handleRadius = 6.dp.toPx()
                                listOf(Offset(l, t), Offset(r, t), Offset(l, b), Offset(r, b)).forEach { handle ->
                                    drawCircle(Color.White, handleRadius + 2.dp.toPx(), handle)
                                    drawCircle(Color(0xFF159765), handleRadius, handle)
                                }
                            }
                        }
                        Text("直接拖动框内区域可移动裁切框，拖动四角圆点可调整宽高；下方滑块可精确微调。", color = Color.Gray, fontSize = 10.sp)
                    } else {
                        Text("无法生成预览，但仍可使用下方滑块调整裁切区域。", color = Color.Gray, fontSize = 11.sp)
                    }
                    Text("裁切区域位置 · 左侧 ${String.format(Locale.getDefault(), "%.0f", cropLeft * 100)}%", color = ink, fontSize = 11.sp)
                    CompactEditorSlider(value = cropLeft, onValueChange = { cropLeft = it.coerceAtMost(1f - cropWidth) }, valueRange = 0f..(1f - cropWidth).coerceAtLeast(0f))
                    Text("裁切区域位置 · 顶部 ${String.format(Locale.getDefault(), "%.0f", cropTop * 100)}%", color = ink, fontSize = 11.sp)
                    CompactEditorSlider(value = cropTop, onValueChange = { cropTop = it.coerceAtMost(1f - cropHeight) }, valueRange = 0f..(1f - cropHeight).coerceAtLeast(0f))
                    Text("裁切区域宽度 · ${String.format(Locale.getDefault(), "%.0f", cropWidth * 100)}%", color = ink, fontSize = 11.sp)
                    CompactEditorSlider(value = cropWidth, onValueChange = { cropWidth = it.coerceIn(0.10f, 1f); cropLeft = cropLeft.coerceAtMost(1f - cropWidth) }, valueRange = 0.10f..1f)
                    Text("裁切区域高度 · ${String.format(Locale.getDefault(), "%.0f", cropHeight * 100)}%", color = ink, fontSize = 11.sp)
                    CompactEditorSlider(value = cropHeight, onValueChange = { cropHeight = it.coerceIn(0.10f, 1f); cropTop = cropTop.coerceAtMost(1f - cropHeight) }, valueRange = 0.10f..1f)
                    Text("可分别调整裁切区域的左边距、上边距、宽度和高度；原图不会被覆盖，会生成一张新的本地素材。", color = Color.Gray, fontSize = 10.sp)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End, verticalAlignment = Alignment.CenterVertically) {
                        TextButton(onClick = { cropLeft = 0f; cropTop = 0f; cropWidth = 1f; cropHeight = 1f }) { Text("重置", color = Color.Gray) }
                        TextButton(onClick = { showCustomImageCrop = false; customCropAsset = null }) { Text("取消", color = Color.Gray) }
                        TextButton(onClick = { applyCustomImageCrop() }) { Text("生成裁切图", color = accent) }
                    }
                }
            }
        }
    }

    if (showLayoutBuilder) {
        Dialog(onDismissRequest = { showLayoutBuilder = false }) {
            Surface(shape = RoundedCornerShape(14.dp), color = Color.White, modifier = Modifier.fillMaxWidth()) {
                Column(
                    Modifier.fillMaxWidth().heightIn(max = 560.dp).verticalScroll(rememberScrollState()).padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("自定义分栏", color = ink, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                    Text("按公众号文章常用表格结构生成分栏，避免依赖复杂的 Flex 布局。每一栏插入后可分别编辑。", color = Color.Gray, fontSize = 11.sp)
                    Text("栏数", color = ink, fontSize = 12.sp)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        listOf(2, 3, 4).forEach { count ->
                            FilterChip(
                                selected = layoutBuilderColumns == count,
                                onClick = {
                                    layoutBuilderColumns = count
                                    layoutBuilderRatios = List(count) { "1" }.joinToString(",")
                                },
                                label = { Text("${count}栏") }
                            )
                        }
                    }
                    OutlinedTextField(
                        value = layoutBuilderRatios,
                        onValueChange = { layoutBuilderRatios = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text("各栏比例（逗号分隔，如 2,1 或 1,1,1）") }
                    )
                    OutlinedTextField(
                        value = layoutBuilderGap,
                        onValueChange = { layoutBuilderGap = it.filter { c -> c.isDigit() }.take(2) },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text("栏间距（0–24 px）") }
                    )
                    OutlinedTextField(
                        value = layoutBuilderBackground,
                        onValueChange = { layoutBuilderBackground = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text("分栏背景色（HEX，例如 #F4F7F5）") }
                    )
                    Text("首栏图片（可选）", color = ink, fontSize = 12.sp)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        FilterChip(
                            selected = layoutBuilderImageAssetId.isBlank(),
                            onClick = { layoutBuilderImageAssetId = "" },
                            label = { Text("不使用图片") }
                        )
                        TextButton(onClick = { layoutImagePicker.launch(arrayOf("image/*")) }) {
                            Text("导入图片", color = accent)
                        }
                    }
                    if (vm.data.mediaAssets.isNotEmpty()) {
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            vm.data.mediaAssets.filter { it.mimeType.startsWith("image/") }.take(30).forEach { asset ->
                                FilterChip(
                                    selected = layoutBuilderImageAssetId == asset.id,
                                    onClick = { layoutBuilderImageAssetId = asset.id },
                                    label = { Text(asset.fileName.take(14), maxLines = 1) }
                                )
                            }
                        }
                    }

                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        TextButton(onClick = { showLayoutBuilder = false }) { Text("取消", color = Color.Gray) }
                        TextButton(onClick = {
                            val ratios = layoutBuilderRatios.split(",").mapNotNull { it.trim().toFloatOrNull() }
                            val gap = layoutBuilderGap.toIntOrNull()
                            val valid = ratios.size == layoutBuilderColumns && ratios.all { it > 0f && it <= 10f } &&
                                gap != null && gap in 0..24 && Regex("^#[0-9a-fA-F]{6}$").matches(layoutBuilderBackground)
                            if (!valid) {
                                vm.toast("请检查栏数比例、间距和 HEX 背景色")
                            } else {
                                val total = ratios.sum()
                                val widths = ratios.map { (it / total * 10000).toInt() / 100f }
                                val cols = widths.mapIndexed { index, width ->
                                    "<col style='width:${width}%;'>"
                                }.joinToString("")
                                val selectedImage = vm.data.mediaAssets.firstOrNull { it.id == layoutBuilderImageAssetId && it.mimeType.startsWith("image/") }
                                val cells = widths.indices.joinToString("") { index ->
                                    val body = if (index == 0 && selectedImage != null) {
                                        "<img src='https://editor.local/assets/${selectedImage.id}' alt='${selectedImage.fileName}' style='display:block;width:100%;height:auto;margin:0 0 8px'><p style='margin:0'>图片说明文字</p>"
                                    } else {
                                        "<p style='margin:0'>第 ${index + 1} 栏内容</p>"
                                    }
                                    "<td style='vertical-align:top;padding:12px;background:${layoutBuilderBackground};word-break:break-word'>$body</td>"
                                }
                                val fragment = "<table role='presentation' style='width:100%;table-layout:fixed;border-collapse:separate;border-spacing:${gap}px 0;margin:16px 0'><colgroup>$cols</colgroup><tbody><tr>$cells</tr></tbody></table><p><br></p>"
                                insert(fragment)
                                showLayoutBuilder = false
                                vm.toast("已插入 ${layoutBuilderColumns} 栏自定义布局")
                            }
                        }) { Text("插入画布", color = accent) }
                    }
                }
            }
        }
    }

    if (showBlockProperties) {
        Dialog(onDismissRequest = { showBlockProperties = false }) {
            Surface(shape = RoundedCornerShape(14.dp), color = Color.White, modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth().heightIn(max = 560.dp).verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("模块属性", color = ink, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                    Text("可设置尺寸、间距、背景、边框、圆角、阴影、对齐和透明度。", color = Color.Gray, fontSize = 11.sp)
                    OutlinedTextField(blockWidth, { blockWidth = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("宽度（例如 100%、320px）") })
                    OutlinedTextField(blockPadding, { blockPadding = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("内边距（例如 14px）") })
                    OutlinedTextField(blockMargin, { blockMargin = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("上下间距（例如 12px）") })
                    OutlinedTextField(blockBackground, { blockBackground = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("背景色（HEX 或 transparent）") })
                    OutlinedTextField(blockBorder, { blockBorder = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("边框颜色（HEX）") })
                    OutlinedTextField(blockBorderWidth, { blockBorderWidth = it.filter { c -> c.isDigit() }.take(1) }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("边框宽度（0–8 px）") })
                    OutlinedTextField(blockBorderStyle, { blockBorderStyle = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("边框样式（solid / dashed / dotted）") })
                    OutlinedTextField(blockRadius, { blockRadius = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("圆角（例如 8px）") })
                    OutlinedTextField(blockShadow, { blockShadow = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("阴影（none / 0 2px 8px #0002）") })
                    OutlinedTextField(blockAlign, { blockAlign = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("内容对齐（left / center / right / justify）") })
                    OutlinedTextField(blockOpacity, { blockOpacity = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("透明度（0–100）") })
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                        TextButton(onClick = { showBlockProperties = false }) { Text("取消", color = Color.Gray) }
                        TextButton(onClick = {
                            val dimension = Regex("""^\d{1,3}(?:\.\d{1,2})?(?:px|%)$""")
                            val widthValue = Regex("""^(?:auto|\d{1,3}(?:\.\d{1,2})?(?:px|%))$""")
                            val colorValue = Regex("""^#[0-9a-fA-F]{6}$""")
                            val shadowValue = Regex("""^(?:none|0(?:px)?\s+\d{1,3}px\s+\d{1,3}px\s+#[0-9a-fA-F]{3,8})$""")
                            val gradientValue = Regex("""^linear-gradient\((?:45|90|135|180)deg,\s*#[0-9a-fA-F]{6}\s+\d{1,3}%,\s*#[0-9a-fA-F]{6}\s+\d{1,3}%\)$""")
                            val bgValid = blockBackground == "transparent" || colorValue.matches(blockBackground) || gradientValue.matches(blockBackground)
                            val borderWidthValue = blockBorderWidth.toIntOrNull()?.let { it in 0..8 } == true
                            val borderStyleValid = blockBorderStyle in listOf("solid", "dashed", "dotted")
                            val radiusValue = Regex("""^\d{1,3}(?:\.\d{1,2})?(?:px|%)(?:\s+\d{1,3}(?:\.\d{1,2})?(?:px|%)){0,3}$""")
                            val alignValid = blockAlign in listOf("left", "center", "right", "justify")
                            val opacityValid = blockOpacity.toIntOrNull()?.let { it in 0..100 } == true
                            if (!dimension.matches(blockPadding) || !dimension.matches(blockMargin) || !widthValue.matches(blockWidth) ||
                                !radiusValue.matches(blockRadius) || !colorValue.matches(blockBorder) || !bgValid ||
                                !borderWidthValue || !borderStyleValid || !shadowValue.matches(blockShadow) || !alignValid || !opacityValid) {
                                vm.toast("请检查宽度、间距、阴影、对齐和颜色格式")
                            } else {
                                runJs("applySelectedBlockStyle(${JSONObject.quote(blockPadding)},${JSONObject.quote(blockMargin)},${JSONObject.quote(blockWidth)},${JSONObject.quote(blockBackground)},${JSONObject.quote(blockBorder)},${JSONObject.quote(blockBorderWidth)},${JSONObject.quote(blockBorderStyle)},${JSONObject.quote(blockRadius)},${JSONObject.quote(blockShadow)},${JSONObject.quote(blockAlign)},${JSONObject.quote(blockOpacity)})")
                                showBlockProperties = false
                                vm.toast("模块样式已更新")
                            }
                        }) { Text("应用样式", color = accent) }
                    }
                }
            }
        }
    }

    if (showArticlePackagePreview) {
        val packagePreview = runCatching { JSONObject(pendingArticlePackageRaw) }.getOrNull()
        if (packagePreview != null) {
            val packageHtml = sanitizeArticleHtml(packagePreview.optString("html").ifBlank { "<p><br></p>" })
            val packageAssets = packagePreview.optJSONArray("assets") ?: org.json.JSONArray()
            val packageWordCount = packageHtml.replace(Regex("<[^>]*>"), "").length
            Dialog(onDismissRequest = { showArticlePackagePreview = false; pendingArticlePackageRaw = "" }) {
                Surface(shape = RoundedCornerShape(14.dp), color = Color.White, modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("文章包导入预览", color = ink, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                        Text(packagePreview.optString("title").ifBlank { "未命名文章" }, color = ink, fontSize = 18.sp, fontWeight = FontWeight.Medium, maxLines = 2, overflow = TextOverflow.Ellipsis)
                        Text(
                            listOf(packagePreview.optString("author"), packagePreview.optString("category"), if (packagePreview.optString("status") == "complete") "已完成" else "草稿")
                                .filter { it.isNotBlank() }.joinToString(" · ").ifBlank { "未设置作者和分类" },
                            color = Color.Gray, fontSize = 11.sp
                        )
                        Text("正文约 $packageWordCount 字 · 引用图片 ${packageAssets.length()} 张 · 将作为新文章导入，不会覆盖现有文章", color = accent, fontSize = 11.sp)
                        packagePreview.optString("summary").takeIf { it.isNotBlank() }?.let {
                            Text(it, color = Color.Gray, fontSize = 12.sp, maxLines = 3, overflow = TextOverflow.Ellipsis)
                        }
                        AndroidView(
                            modifier = Modifier.fillMaxWidth().height(300.dp),
                            factory = { ctx -> WebView(ctx).apply {
                                settings.javaScriptEnabled = false
                                settings.domStorageEnabled = false
                                setBackgroundColor(android.graphics.Color.WHITE)
                                loadDataWithBaseURL("https://editor.local/", packageHtml, "text/html", "UTF-8", null)
                            } },
                            update = { view -> view.loadDataWithBaseURL("https://editor.local/", packageHtml, "text/html", "UTF-8", null) }
                        )
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                            TextButton(onClick = { showArticlePackagePreview = false; pendingArticlePackageRaw = "" }) {
                                Text("取消", color = Color.Gray)
                            }
                            TextButton(onClick = {
                                val raw = pendingArticlePackageRaw
                                val importedMedia = mutableListOf<MediaAsset>()
                                runCatching {
                                    val pack = JSONObject(raw)
                                    val sourceHtml = pack.optString("html")
                                    if (sourceHtml.length > 12 * 1024 * 1024) error("文章 HTML 内容过大")
                                    val now = System.currentTimeMillis().toString()
                                    val idMap = mutableMapOf<String, String>()
                                    val assets = pack.optJSONArray("assets") ?: org.json.JSONArray()
                                    if (assets.length() > 40) error("单篇文章最多导入 40 张图片")
                                    val mediaDir = File(context.filesDir, "article_media").apply { mkdirs() }
                                    var totalBytes = 0L
                                    for (index in 0 until assets.length()) {
                                        val item = assets.optJSONObject(index) ?: continue
                                        val oldId = item.optString("id")
                                        if (oldId.isBlank()) error("文章包中存在缺少资源 ID 的图片")
                                        val mime = item.optString("mimeType", "image/jpeg")
                                        if (!mime.startsWith("image/")) error("文章包包含非图片媒体资源")
                                        val encoded = item.optString("base64")
                                        if (encoded.length > 16 * 1024 * 1024) error("单张图片数据过大")
                                        val bytes = Base64.decode(encoded, Base64.DEFAULT)
                                        if (bytes.size > 12 * 1024 * 1024) error("单张图片超过 12 MB")
                                        totalBytes += bytes.size
                                        if (totalBytes > 36L * 1024 * 1024) error("图片总大小超过 36 MB")
                                        var newId = vm.newId() + "_" + index
                                        while (vm.data.mediaAssets.any { it.id == newId } || importedMedia.any { it.id == newId }) newId = vm.newId()
                                        val rawName = item.optString("fileName", "image_$index.jpg").substringAfterLast('/').substringAfterLast('\\')
                                        val ext = rawName.substringAfterLast('.', "jpg").replace(Regex("[^A-Za-z0-9]"), "").take(8).ifBlank { "jpg" }
                                        val safeName = rawName.replace(Regex("[^A-Za-z0-9._-]"), "_").take(100).ifBlank { "image_$index.$ext" }
                                        val target = File(mediaDir, "$newId.$ext")
                                        target.writeBytes(bytes)
                                        val asset = MediaAsset(newId, safeName, mime, "article_media/${target.name}", target.length(), now)
                                        vm.saveMediaAsset(asset)
                                        importedMedia.add(asset)
                                        idMap[oldId] = newId
                                    }
                                    var importedHtml = sanitizeArticleHtml(sourceHtml.ifBlank { "<p><br></p>" })
                                    idMap.forEach { (oldId, newId) -> importedHtml = importedHtml.replace("/assets/$oldId", "/assets/$newId") }
                                    val tagsJson = pack.optJSONArray("tags") ?: org.json.JSONArray()
                                    val importedTags = (0 until minOf(tagsJson.length(), 50)).mapNotNull { tagsJson.optString(it).take(40).takeIf { tag -> tag.isNotBlank() } }
                                    val imported = ArticleDocument(
                                        id = vm.newId(), title = pack.optString("title", "导入文章").take(120).ifBlank { "导入文章" }, html = importedHtml,
                                        createdAt = now, updatedAt = now, subtitle = pack.optString("subtitle").take(200),
                                        summary = pack.optString("summary").take(1000), author = pack.optString("author").take(100),
                                        category = pack.optString("category").take(100), tags = importedTags,
                                        coverAssetId = idMap[pack.optString("coverAssetId")].orEmpty(),
                                        status = if (pack.optString("status") == "complete") "complete" else "draft",
                                        wordCount = importedHtml.replace(Regex("<[^>]*>"), "").length, isFavorite = pack.optBoolean("isFavorite", false)
                                    )
                                    saveDocument()
                                    vm.saveArticle(imported)
                                    articleId = imported.id; title = imported.title; html = imported.html
                                    subtitle = imported.subtitle; summary = imported.summary; author = imported.author
                                    category = imported.category; tagsText = imported.tags.joinToString(", ")
                                    articleStatus = imported.status; coverAssetId = imported.coverAssetId
                                    previewMode = false; showArticleList = false
                                    editor?.evaluateJavascript("setEditorHtml(${JSONObject.quote(imported.html)});setEditable(true);", null)
                                    pendingSave++
                                    showArticlePackagePreview = false
                                    pendingArticlePackageRaw = ""
                                    vm.toast("文章包已导入")
                                }.onFailure { error ->
                                    importedMedia.forEach { asset ->
                                        runCatching { File(context.filesDir, asset.relativePath).canonicalFile.let { file ->
                                            val root = File(context.filesDir, "article_media").canonicalFile
                                            if (file.path.startsWith(root.path + File.separator)) file.delete()
                                        } }
                                        vm.deleteMediaAsset(asset.id)
                                    }
                                    vm.toast("文章包导入失败：${error.message ?: "文件格式错误"}")
                                }
                            }) { Text("确认导入为新文章", color = accent) }
                        }
                    }
                }
            }
        }
    }
    if (showCompatibilityReport) {
        AlertDialog(
            onDismissRequest = { showCompatibilityReport = false },
            title = { Text("公众号兼容性检查") },
            text = {
                Column(Modifier.fillMaxWidth().heightIn(max = 420.dp).verticalScroll(rememberScrollState())) {
                    if (compatibilityWarnings.isEmpty()) Text("未发现常见风险项。实际发布效果仍以微信公众号编辑器的粘贴与预览为准。", color = Color(0xFF168653), fontSize = 13.sp)
                    compatibilityWarnings.forEachIndexed { index, warning ->
                        Text("${index + 1}. ${warning}", color = ink, fontSize = 12.sp, modifier = Modifier.padding(vertical = 4.dp))
                    }
                    Text("检查仅基于 HTML 结构做静态提示，不代表平台审核或发布保证。", color = Color.Gray, fontSize = 10.sp, modifier = Modifier.padding(top = 8.dp))
                }
            },
            confirmButton = { TextButton(onClick = { showCompatibilityReport = false }) { Text("知道了") } }
        )
    }
    if (showArticleInfo) {
        AlertDialog(
            onDismissRequest = {
                if (articleInfoSnapshot.size == 7) {
                    subtitle = articleInfoSnapshot[0]; author = articleInfoSnapshot[1]; category = articleInfoSnapshot[2]
                    tagsText = articleInfoSnapshot[3]; summary = articleInfoSnapshot[4]; articleStatus = articleInfoSnapshot[5]
                    coverAssetId = articleInfoSnapshot[6]
                }
                showArticleInfo = false
            },
            title = { Text("文章信息") },
            text = {
                Column(Modifier.fillMaxWidth().heightIn(max = 480.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(subtitle, { subtitle = it }, label = { Text("副标题") }, singleLine = true)
                    OutlinedTextField(author, { author = it }, label = { Text("作者") }, singleLine = true)
                    OutlinedTextField(category, { category = it }, label = { Text("分类") }, singleLine = true)
                    OutlinedTextField(tagsText, { tagsText = it }, label = { Text("标签（逗号分隔）") }, singleLine = true)
                    OutlinedTextField(summary, { summary = it }, label = { Text("文章摘要") }, minLines = 3)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("文章状态", color = ink, fontSize = 12.sp, modifier = Modifier.weight(1f))
                        TextButton(onClick = { articleStatus = if (articleStatus == "draft") "complete" else "draft" }) { Text(if (articleStatus == "draft") "草稿" else "已完成", color = accent) }
                    }
                    Text("封面图片", color = ink, fontSize = 12.sp)
                    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        EditorTool("不设置", coverAssetId.isBlank()) { coverAssetId = "" }
                        vm.data.mediaAssets.forEach { asset -> EditorTool(asset.fileName.take(10), coverAssetId == asset.id) { coverAssetId = asset.id } }
                    }
                    Text("文章信息与封面资源 ID 会随文章保存；封面图片暂作为文章素材关联，不自动上传公众号。", color = Color.Gray, fontSize = 11.sp)
                }
            },
            confirmButton = { TextButton(onClick = { showArticleInfo = false; pendingSave++ }) { Text("完成", color = accent) } },
            dismissButton = { TextButton(onClick = {
                if (articleInfoSnapshot.size == 7) {
                    subtitle = articleInfoSnapshot[0]; author = articleInfoSnapshot[1]; category = articleInfoSnapshot[2]
                    tagsText = articleInfoSnapshot[3]; summary = articleInfoSnapshot[4]; articleStatus = articleInfoSnapshot[5]
                    coverAssetId = articleInfoSnapshot[6]
                }
                showArticleInfo = false
            }) { Text("取消") } }
        )
    }
}

private fun editorToolGlyph(label: String): String {
    val key = label.trim()
    return when {
        key in listOf("撤销", "上一步") -> "↶"
        key in listOf("重做", "下一步") -> "↷"
        key.contains("保存") -> "▣"
        key.contains("预览") || key.contains("阅读") -> "◉"
        key.contains("返回") || key.contains("关闭") || key.contains("取消") -> "‹"
        key.contains("文字") || key.contains("字体") -> "Aa"
        key.contains("标题") -> "T"
        key.contains("图片") || key.contains("相册") || key.contains("封面") || key.contains("画布") -> "▧"
        key.contains("卡片") -> "▣"
        key.contains("组件") || key.contains("布局") || key.contains("分栏") -> "▦"
        key.equals("SVG", true) || key.contains("动画") -> "✧"
        key.contains("图层") || key.contains("层级") -> "▤"
        key.contains("模板") -> "▩"
        key.contains("收藏") || key.contains("喜欢") -> "☆"
        key.contains("文档") || key.contains("文章") -> "▤"
        key.contains("加粗") || key == "粗体" -> "B"
        key.contains("斜体") -> "I"
        key.contains("下划线") -> "U̲"
        key.contains("删除线") -> "S̶"
        key.contains("颜色") || key.contains("背景") -> "◒"
        key.contains("对齐") || key.contains("居中") -> "≡"
        key.contains("链接") -> "↗"
        key.contains("裁切") || key.contains("裁剪") -> "⌗"
        key.contains("旋转") -> "⟳"
        key.contains("替换") -> "⇄"
        key.contains("删除") -> "⌫"
        key.contains("复制") -> "▢"
        key.contains("插入") || key.contains("添加") || key.contains("新建") -> "+"
        key.contains("搜索") || key.contains("查找") -> "⌕"
        key.contains("表格") -> "▦"
        key.contains("列表") || key.contains("编号") -> "☷"
        key.contains("引用") -> "❞"
        key.contains("分割") -> "┄"
        key.contains("收藏") -> "☆"
        key.contains("导入") -> "⇧"
        key.contains("导出") -> "⇩"
        key.contains("设置") || key.contains("属性") -> "⚙"
        key.contains("完成") || key.contains("确定") -> "✓"
        key.contains("全部") || key.contains("草稿") || key.contains("已完成") -> "◉"
        else -> "◈"
    }
}

@Composable
private fun EditorTool(label: String, selected: Boolean = false, onClick: () -> Unit) {
    val dark = LocalEditorToolDark.current
    Column(
        modifier = Modifier
            .widthIn(min = 54.dp)
            .heightIn(min = 54.dp)
            .clip(RoundedCornerShape(10.dp))
            .background(if (selected) AppColors.Theme.copy(alpha = 0.14f) else if (dark) Color(0xFF222222) else AppColors.Field)
            .border(1.dp, if (selected) AppColors.Theme.copy(alpha = 0.48f) else if (dark) Color.Transparent else AppColors.Line, RoundedCornerShape(10.dp))
            .clickable(onClick = onClick)
            .padding(horizontal = 7.dp, vertical = 5.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Text(editorToolGlyph(label), color = if (selected) AppColors.Theme else if (dark) Color(0xFFDDDDDD) else AppColors.TextMain,
            fontSize = 19.sp, fontWeight = FontWeight.Medium, lineHeight = 21.sp)
        Text(label, color = if (selected) AppColors.Theme else if (dark) Color(0xFFDDDDDD) else AppColors.TextMain,
            fontSize = 9.sp, fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
            maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}



@Composable
private fun EditorInputDialog(title: String, hint: String, value: String, onChange: (String) -> Unit, onConfirm: () -> Unit, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = { OutlinedTextField(value, onChange, modifier = Modifier.fillMaxWidth(), placeholder = { Text(hint) }, singleLine = true) },
        confirmButton = { TextButton(onClick = onConfirm) { Text("确定") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } }
    )
}

private fun sanitizeArticleHtml(source: String): String {
    val doc = org.jsoup.Jsoup.parseBodyFragment(source)
    doc.select("script,iframe,object,embed,form").remove()
    doc.getAllElements().forEach { element ->
        val attrs = element.attributes().asList().map { it.key }
        attrs.filter { it.startsWith("on", true) }.forEach { element.removeAttr(it) }
        listOf("href", "src", "xlink:href").forEach { key ->
            val value = element.attr(key).trim().lowercase(Locale.ROOT)
            if (value.startsWith("javascript:") || value.startsWith("data:text/html") || value.startsWith("vbscript:") || value.startsWith("file:") || value.startsWith("content:") || value.startsWith("blob:")) element.removeAttr(key)
        }
    }
    return doc.body().html()
}


private fun escapeMarkdownText(value: String): String = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;")

private fun markdownInlineToHtml(source: String): String {
    var value = escapeMarkdownText(source)
    value = Regex("""!\[([^\]]*)\]\((https?://[^\s)]+)\)""").replace(value) { m -> "<img src=\"${m.groupValues[2]}\" alt=\"${m.groupValues[1]}\" style=\"max-width:100%;height:auto\">" }
    value = Regex("""\[([^\]]+)\]\((https?://[^\s)]+)\)""").replace(value) { m -> "<a href=\"${m.groupValues[2]}\">${m.groupValues[1]}</a>" }
    value = Regex("""\*\*(.+?)\*\*""").replace(value) { "<strong>${it.groupValues[1]}</strong>" }
    value = Regex("""(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)""").replace(value) { "<em>${it.groupValues[1]}</em>" }
    value = Regex("""~~(.+?)~~""").replace(value) { "<del>${it.groupValues[1]}</del>" }
    return value
}

private fun markdownToArticleHtml(markdown: String): String {
    val out = StringBuilder()
    var listType = ""
    var inCode = false
    val code = StringBuilder()
    fun closeList() {
        if (listType == "ul") out.append("</ul>") else if (listType == "ol") out.append("</ol>")
        listType = ""
    }
    markdown.lineSequence().forEach { raw ->
        val line = raw.trimEnd()
        val trimmed = line.trim()
        if (trimmed.startsWith("```")) {
            closeList()
            if (!inCode) { out.append("<pre><code>"); code.clear(); inCode = true }
            else { out.append(escapeMarkdownText(code.toString().trimEnd())).append("</code></pre>"); inCode = false }
            return@forEach
        }
        if (inCode) { code.append(line).append("\n"); return@forEach }
        if (trimmed.isEmpty()) { closeList(); return@forEach }
        val heading = Regex("^(#{1,4})\\s+(.+)$").matchEntire(trimmed)
        when {
            heading != null -> { closeList(); val level = heading.groupValues[1].length; out.append("<h$level>").append(markdownInlineToHtml(heading.groupValues[2])).append("</h$level>") }
            trimmed == "---" || trimmed == "***" -> { closeList(); out.append("<hr>") }
            trimmed.startsWith(">") -> { closeList(); out.append("<blockquote><p>").append(markdownInlineToHtml(trimmed.removePrefix(">").trim())).append("</p></blockquote>") }
            trimmed.startsWith("- ") || trimmed.startsWith("* ") || trimmed.startsWith("+ ") -> {
                if (listType != "ul") { closeList(); out.append("<ul>"); listType = "ul" }
                out.append("<li>").append(markdownInlineToHtml(trimmed.drop(2))).append("</li>")
            }
            Regex("^\\d+\\.\\s+").containsMatchIn(trimmed) -> {
                if (listType != "ol") { closeList(); out.append("<ol>"); listType = "ol" }
                out.append("<li>").append(markdownInlineToHtml(trimmed.replaceFirst(Regex("^\\d+\\.\\s+"), ""))).append("</li>")
            }
            else -> { closeList(); out.append("<p>").append(markdownInlineToHtml(trimmed)).append("</p>") }
        }
    }
    if (inCode) out.append(escapeMarkdownText(code.toString())).append("</code></pre>")
    closeList()
    return out.toString().ifBlank { "<p><br></p>" }
}
private fun cropArticleImageFile(source: File, target: File, ratio: Float, png: Boolean, positionX: Float = 0.5f, positionY: Float = 0.5f): Pair<Int, Int> {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(source.absolutePath, bounds)
    if (bounds.outWidth <= 0 || bounds.outHeight <= 0) error("无法读取图片尺寸")
    if (bounds.outWidth.toLong() * bounds.outHeight.toLong() > 80_000_000L) error("图片分辨率过高，请先压缩")
    var sample = 1
    while ((bounds.outWidth / sample).toLong() * (bounds.outHeight / sample).toLong() > 20_000_000L) sample *= 2
    val bitmap = BitmapFactory.decodeFile(source.absolutePath, BitmapFactory.Options().apply { inSampleSize = sample }) ?: error("图片解码失败")
    val currentRatio = bitmap.width.toFloat() / bitmap.height.toFloat()
    val cropWidth: Int
    val cropHeight: Int
    if (currentRatio > ratio) {
        cropHeight = bitmap.height
        cropWidth = (cropHeight * ratio).toInt().coerceIn(1, bitmap.width)
    } else {
        cropWidth = bitmap.width
        cropHeight = (cropWidth / ratio).toInt().coerceIn(1, bitmap.height)
    }
    val left = ((bitmap.width - cropWidth) * positionX.coerceIn(0f, 1f)).toInt()
    val top = ((bitmap.height - cropHeight) * positionY.coerceIn(0f, 1f)).toInt()
    val cropped = Bitmap.createBitmap(bitmap, left, top, cropWidth, cropHeight)
    target.outputStream().use { output ->
        if (png) cropped.compress(Bitmap.CompressFormat.PNG, 100, output)
        else cropped.compress(Bitmap.CompressFormat.JPEG, 92, output)
    }
    if (cropped !== bitmap) cropped.recycle()
    bitmap.recycle()
    return cropWidth to cropHeight
}

private fun cropArticleImageRectFile(
    source: File,
    target: File,
    leftFraction: Float,
    topFraction: Float,
    widthFraction: Float,
    heightFraction: Float,
    png: Boolean
): Pair<Int, Int> {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(source.absolutePath, bounds)
    if (bounds.outWidth <= 0 || bounds.outHeight <= 0) error("无法读取图片尺寸")
    if (bounds.outWidth.toLong() * bounds.outHeight.toLong() > 80_000_000L) error("图片分辨率过高，请先压缩")
    var sample = 1
    while ((bounds.outWidth / sample).toLong() * (bounds.outHeight / sample).toLong() > 20_000_000L) sample *= 2
    val bitmap = BitmapFactory.decodeFile(source.absolutePath, BitmapFactory.Options().apply { inSampleSize = sample })
        ?: error("图片解码失败")
    val cropWidth = (bitmap.width * widthFraction.coerceIn(0.10f, 1f)).toInt().coerceIn(1, bitmap.width)
    val cropHeight = (bitmap.height * heightFraction.coerceIn(0.10f, 1f)).toInt().coerceIn(1, bitmap.height)
    val left = (bitmap.width * leftFraction.coerceIn(0f, 1f)).toInt().coerceIn(0, bitmap.width - cropWidth)
    val top = (bitmap.height * topFraction.coerceIn(0f, 1f)).toInt().coerceIn(0, bitmap.height - cropHeight)
    val cropped = Bitmap.createBitmap(bitmap, left, top, cropWidth, cropHeight)
    target.outputStream().use { output ->
        if (png) cropped.compress(Bitmap.CompressFormat.PNG, 100, output)
        else cropped.compress(Bitmap.CompressFormat.JPEG, 92, output)
    }
    if (cropped !== bitmap) cropped.recycle()
    bitmap.recycle()
    return cropWidth to cropHeight
}

private fun decodeArticleAssetPreview(file: File): Bitmap? {
    val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
    BitmapFactory.decodeFile(file.absolutePath, bounds)
    if (bounds.outWidth <= 0 || bounds.outHeight <= 0) return null
    var sample = 1
    while (bounds.outWidth / sample > 1400 || bounds.outHeight / sample > 1400) sample *= 2
    val options = BitmapFactory.Options().apply { inSampleSize = sample; inPreferredConfig = Bitmap.Config.ARGB_8888 }
    return BitmapFactory.decodeFile(file.absolutePath, options)
}
private fun formatArticleTimestamp(raw: String): String = runCatching {
    val millis = raw.toLong()
    SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.getDefault()).format(Date(millis))
}.getOrDefault(raw)

private fun articleCompatibilityWarnings(html: String): List<String> {
    val warnings = mutableListOf<String>()
    if (Regex("""(?is)<img[^>]+src=["']https?://""").containsMatchIn(html)) warnings += "包含外链图片：复制到公众号后可能需要重新上传或替换为公众号素材。"
    if (Regex("""(?is)<table\b""").containsMatchIn(html)) warnings += "包含表格：请检查手机端是否出现横向溢出或列宽挤压。"
    if (Regex("""(?is)@font-face|https?://[^\s"']+\.(?:woff2?|ttf|otf)""").containsMatchIn(html)) warnings += "可能依赖外部字体文件，公众号环境不一定能加载。"
    if (Regex("""(?is)<(?:iframe|video|audio|object|embed)\b""").containsMatchIn(html)) warnings += "包含音视频或嵌入式媒体标签，公众号正文不一定支持直接承载，建议改用平台素材或链接卡片。"
    if (Regex("""(?is)<p[^>]*>\s*(?:<br\s*/?>)?\s*</p>""").findAll(html).count() > 5) warnings += "空段落较多，可能造成阅读间距过大。"
    if (Regex("""(?is)style=["'][^"']*(?:position\s*:\s*fixed|display\s*:\s*flex|grid)""").containsMatchIn(html)) warnings += "包含复杂布局 CSS，公众号可能清理或改变其显示效果。"
    if (Regex("""(?is)href=["'](?:javascript:|#|data:)""").containsMatchIn(html)) warnings += "存在脚本链接、空锚点或 data 链接，请检查链接是否有效。"
    if (Regex("""(?is)https?://editor\.local/assets/""").containsMatchIn(html)) warnings += "包含编辑器内部素材地址：该地址仅在 APP 内可读取，导出或粘贴前需转换为真实图片或重新上传。"
    if (Regex("""(?is)<img\b(?![^>]*\balt=)[^>]*>""").containsMatchIn(html)) warnings += "部分图片缺少替代文本（alt），建议补充图片说明以改善无障碍阅读。"
    if (Regex("""(?is)<(?:script|style|svg|canvas)\b""").containsMatchIn(html)) warnings += "包含脚本、样式表、SVG 或 Canvas 内容，公众号编辑器可能过滤或无法保留。"
    if (Regex("""(?is)style=["'][^"']*(?:position\s*:\s*(?:fixed|sticky|absolute)|display\s*:\s*(?:flex|grid)|transform\s*:|background-image\s*:|var\s*\()""").containsMatchIn(html)) warnings += "包含定位、弹性/网格布局、变换、背景图或 CSS 变量等复杂样式，粘贴后可能被公众号清理或重排。"
    val embeddedImageChars = Regex("""(?is)data:image/[^;]+;base64,([A-Za-z0-9+/=]+)""").findAll(html).sumOf { it.groupValues[1].length }
    if (embeddedImageChars > 0) warnings += if (embeddedImageChars > 1_400_000) "包含较大的 Base64 内嵌图片数据，剪贴板或公众号编辑器可能无法完整接收，建议改为公众号素材图片。" else "包含 Base64 内嵌图片：不同设备和公众号编辑器对内嵌图片的支持不一致，发布前请检查图片是否完整。"
    return warnings
}
private fun articleHtmlToMarkdown(html: String): String {
    var value = html
    value = value.replace(Regex("""(?is)<img[^>]*>""")) { tag ->
        val src = Regex("""(?is)src=["']([^"']+)["']""").find(tag.value)?.groupValues?.get(1).orEmpty()
        val alt = Regex("""(?is)alt=["']([^"']*)["']""").find(tag.value)?.groupValues?.get(1).orEmpty()
        if (src.isBlank()) alt else "![$alt]($src)"
    }
    value = value.replace(Regex("""(?is)<a[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""")) { link ->
        "[${link.groupValues[2].replace(Regex("<[^>]*>"), "").trim()}](${link.groupValues[1]})"
    }
    value = value.replace(Regex("""(?is)<h1[^>]*>(.*?)</h1>""")) { "\n# ${it.groupValues[1].replace(Regex("<[^>]*>"), "").trim()}\n\n" }
    value = value.replace(Regex("""(?is)<h2[^>]*>(.*?)</h2>""")) { "\n## ${it.groupValues[1].replace(Regex("<[^>]*>"), "").trim()}\n\n" }
    value = value.replace(Regex("""(?is)<h([34])[^>]*>(.*?)</h[34]>""")) { "\n### ${it.groupValues[2].replace(Regex("<[^>]*>"), "").trim()}\n\n" }
    value = value.replace(Regex("""(?is)<blockquote[^>]*>(.*?)</blockquote>""")) { "\n> ${it.groupValues[1].replace(Regex("<[^>]*>"), "").trim()}\n\n" }
    value = value.replace(Regex("""(?is)<li[^>]*>(.*?)</li>""")) { "- ${it.groupValues[1].replace(Regex("<[^>]*>"), "").trim()}\n" }
    value = value.replace(Regex("""(?is)<(strong|b)[^>]*>(.*?)</\1>""")) { "**${it.groupValues[2].replace(Regex("<[^>]*>"), "")}**" }
    value = value.replace(Regex("""(?is)<(em|i)[^>]*>(.*?)</\1>""")) { "*${it.groupValues[2].replace(Regex("<[^>]*>"), "")}*" }
    value = value.replace(Regex("""(?is)<br\s*/?>"""), "\n")
    value = value.replace(Regex("""(?is)</p>|</div>|</section>|</tr>"""), "\n\n")
    value = value.replace(Regex("""(?is)<hr[^>]*>"""), "\n---\n")
    value = value.replace(Regex("""(?is)<[^>]+>"""), "")
    value = org.jsoup.parser.Parser.unescapeEntities(value, false)
    return value.replace(Regex("""\n{3,}"""), "\n\n").trim()
}
