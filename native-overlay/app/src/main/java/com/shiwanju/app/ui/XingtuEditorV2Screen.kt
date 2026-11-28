package com.shiwanju.app.ui

import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.shape.RectangleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlin.math.roundToInt
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/** 醒图 2.0 独立原生画布。旧版 ArticleEditorScreen 保持独立，不参与本页状态。 */
@Composable
fun XingtuEditorV2Screen(onBack: () -> Unit) {
    val context = LocalContext.current
    var history by remember {
        mutableStateOf(XingtuV2History(XingtuV2Persistence.load(context) ?: XingtuV2Document(
            id = "xingtu-v2-document",
            objects = listOf(
                XingtuV2Object.Text(
                    id = "sample-heading", content = "在画布上开始创作",
                    fontSizeSp = 24f,
                    transform = XingtuV2Transform(x = 90f, y = 170f, width = 520f, height = 100f)
                ),
                XingtuV2Object.Component(
                    id = "sample-card", componentType = "rectangle",
                    fillColor = 0xFFF2F2F2, cornerRadius = 18f,
                    transform = XingtuV2Transform(x = 90f, y = 340f, width = 620f, height = 250f)
                )
            )
        )))
    }
    var multiSelect by remember { mutableStateOf(false) }
    var activeMultiTransform by remember { mutableStateOf(false) }
    var activeCanvasPanel by remember { mutableStateOf(false) }
    var groupScale by remember { mutableFloatStateOf(1f) }
    var groupRotation by remember { mutableFloatStateOf(0f) }
    var showLayers by remember { mutableStateOf(false) }
    var showVersions by remember { mutableStateOf(false) }
    var showComponentPicker by remember { mutableStateOf(false) }
    var savedVersions by remember { mutableStateOf(emptyList<XingtuV2VersionInfo>()) }
    var replaceTargetId by remember { mutableStateOf<String?>(null) }
    var activePanel by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(history.document.selectedIds) {
        if (activePanel != null || activeMultiTransform || activeCanvasPanel) history = history.endTransform()
        activePanel = null
        showComponentPicker = false
        activeCanvasPanel = false
        groupScale = 1f
        groupRotation = 0f
        activeMultiTransform = false
    }
    var panelHeight by remember { mutableFloatStateOf(220f) }
    var viewportScale by remember { mutableFloatStateOf(1f) }
    var viewportPanX by remember { mutableFloatStateOf(0f) }
    var viewportPanY by remember { mutableFloatStateOf(0f) }
    var snapGuideX by remember { mutableStateOf<Float?>(null) }
    var snapGuideY by remember { mutableStateOf<Float?>(null) }
    val colors = MaterialTheme.colorScheme
    val density = LocalDensity.current.density

    val exportDocumentLauncher = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri ->
        if (uri != null) XingtuV2Persistence.exportToUri(context, uri, history.document)
    }
    val importDocumentLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            XingtuV2Persistence.importFromUri(context, uri)?.let { imported ->
                history = XingtuV2History(imported)
                activePanel = null
                activeCanvasPanel = false
                activeMultiTransform = false
            }
        }
    }

    val addComponent: (String) -> Unit = { type ->
        val count = history.document.objects.count { it.kind == XingtuV2ObjectKind.COMPONENT } + 1
        val isLine = type == "line"
        history = history.dispatch(XingtuV2Action.InsertObject(
            XingtuV2Object.Component(
                id = "component-${System.nanoTime()}", componentType = type,
                fillColor = if (isLine) 0xFF333333 else 0xFFEDEFF2,
                cornerRadius = if (type == "rounded-rectangle") 18f else 0f,
                strokeColor = 0xFF555555, strokeWidth = if (type == "ellipse") 1f else 0f,
                transform = XingtuV2Transform(
                    x = 130f, y = 260f + count * 80f,
                    width = 460f, height = if (isLine) 8f else 180f
                )
            )
        ))
        showComponentPicker = false
    }

    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            runCatching {
                context.contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            val targetId = replaceTargetId
            if (targetId != null) {
                val existing = history.document.objects.firstOrNull { it.id == targetId } as? XingtuV2Object.Image
                if (existing != null) {
                    history = history.updateObjectLive(existing.copy(
                        assetUri = uri.toString(),
                        cropLeft = 0f, cropTop = 0f, cropRight = 1f, cropBottom = 1f
                    ))
                }
                history = history.endTransform()
                replaceTargetId = null
            } else {
                val image = XingtuV2Object.Image(
                    id = "image-${System.nanoTime()}",
                    assetUri = uri.toString(),
                    transform = XingtuV2Transform(x = 120f, y = 180f, width = 520f, height = 420f)
                )
                history = history.dispatch(XingtuV2Action.InsertObject(image))
            }
            showLayers = false
        } else if (replaceTargetId != null) {
            history = history.endTransform()
            replaceTargetId = null
        }
    }

    LaunchedEffect(history.document.revision) {
        delay(350)
        XingtuV2Persistence.save(context, history.document)
    }

    BackHandler {
        when {
            activePanel != null -> {
                history = history.endTransform()
                activePanel = null
            }
            activeCanvasPanel -> {
                history = history.endTransform()
                activeCanvasPanel = false
            }
            activeMultiTransform -> {
                history = history.endTransform()
                activeMultiTransform = false
            }
            showVersions -> showVersions = false
            showLayers -> showLayers = false
            showComponentPicker -> showComponentPicker = false
            else -> {
                XingtuV2Persistence.save(context, history.document)
                onBack()
            }
        }
    }
    Column(Modifier.fillMaxSize().background(colors.background).navigationBarsPadding()) {
        Row(
            Modifier.fillMaxWidth().height(50.dp).padding(horizontal = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("‹", fontSize = 30.sp, color = colors.onSurface,
                modifier = Modifier.clickable { XingtuV2Persistence.save(context, history.document); onBack() }.padding(horizontal = 8.dp))
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text("醒图 2.0", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = colors.onSurface)
                Text("原生画布 · ${history.document.objects.size} 个对象", fontSize = 10.sp, color = colors.onSurfaceVariant)
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("↶", fontSize = 22.sp,
                    color = if (history.undoStack.isEmpty()) colors.onSurface.copy(alpha = .3f) else colors.onSurface,
                    modifier = Modifier.clickable(enabled = history.undoStack.isNotEmpty()) { history = history.undo() }.padding(horizontal = 7.dp))
                Text("↷", fontSize = 22.sp,
                    color = if (history.redoStack.isEmpty()) colors.onSurface.copy(alpha = .3f) else colors.onSurface,
                    modifier = Modifier.clickable(enabled = history.redoStack.isNotEmpty()) { history = history.redo() }.padding(horizontal = 7.dp))
                Text("版本", fontSize = 11.sp, color = colors.onSurfaceVariant,
                    modifier = Modifier.clickable {
                        savedVersions = XingtuV2Persistence.listVersions(context)
                        showVersions = !showVersions
                    }.padding(horizontal = 6.dp))
                Text("完成", fontSize = 13.sp, color = colors.primary,
                    modifier = Modifier.clickable { XingtuV2Persistence.save(context, history.document); onBack() }.padding(start = 8.dp))
            }
        }

        Box(
            Modifier.fillMaxWidth().weight(1f)
                .background(colors.surfaceVariant.copy(alpha = .35f)),
            contentAlignment = Alignment.Center
        ) {
            BoxWithConstraints(
                Modifier.fillMaxSize().pointerInput(viewportScale) {
                    detectTransformGestures { _, pan, zoom, _ ->
                        if (zoom != 1f || pan != androidx.compose.ui.geometry.Offset.Zero) {
                            viewportScale = (viewportScale * zoom).coerceIn(0.5f, 3f)
                            viewportPanX += pan.x
                            viewportPanY += pan.y
                        }
                    }
                },
                contentAlignment = Alignment.Center
            ) {
                val canvasWidth = minOf(maxWidth - 28.dp, maxHeight * .75f)
                val canvasHeight = canvasWidth * (history.document.canvas.height / history.document.canvas.width)
                val scaleX = canvasWidth.value / history.document.canvas.width
                val scaleY = canvasHeight.value / history.document.canvas.height
                Box(
                    Modifier.width(canvasWidth).height(canvasHeight)
                        .graphicsLayer {
                            this.scaleX = viewportScale
                            this.scaleY = viewportScale
                            translationX = viewportPanX
                            translationY = viewportPanY
                        }
                        .clip(RoundedCornerShape(2.dp))
                        .background(Color(history.document.canvas.backgroundColor))
                        .border(1.dp, colors.outlineVariant)
                ) {
                    history.document.objects.forEach { item ->
                        if (item.visible) {
                            val t = item.transform
                            val selected = item.id in history.document.selectedIds
                            val objectModifier = Modifier
                                .offset {
                                    IntOffset(
                                        (t.x * scaleX * density).roundToInt(),
                                        (t.y * scaleY * density).roundToInt()
                                    )
                                }
                                .size((t.width * t.scaleX * scaleX).dp, (t.height * t.scaleY * scaleY).dp)
                                .graphicsLayer {
                                    rotationZ = t.rotation
                                    alpha = t.alpha.coerceIn(0f, 1f)
                                }
                                .then(if (selected) Modifier.border(1.5.dp, colors.primary) else Modifier)
                                .pointerInput(item.id, scaleX, scaleY, density) {
                                    detectTapGestures {
                                        history = history.dispatch(
                                            XingtuV2Action.Select(setOf(item.id), additive = multiSelect)
                                        )
                                    }
                                }
                                .pointerInput(item.id, scaleX, scaleY, density) {
                                    var gestureStarted = false
                                    detectDragGestures(
                                        onDragStart = {
                                            if (!item.locked) {
                                                snapGuideX = null
                                                snapGuideY = null
                                                history = history.beginTransform()
                                                gestureStarted = true
                                            }
                                        },
                                        onDragEnd = {
                                            if (gestureStarted) history = history.endTransform()
                                            snapGuideX = null
                                            snapGuideY = null
                                        },
                                        onDragCancel = {
                                            if (gestureStarted) history = history.endTransform()
                                            snapGuideX = null
                                            snapGuideY = null
                                        }
                                    ) { change, drag ->
                                        if (gestureStarted) {
                                            change.consume()
                                            val current = history.document.objects.firstOrNull { it.id == item.id } ?: return@detectDragGestures
                                            val old = current.transform
                                            val dx = (drag.x / density) / (scaleX * viewportScale)
                                            val dy = (drag.y / density) / (scaleY * viewportScale)
                                            if (history.document.selectedIds.size > 1 && item.id in history.document.selectedIds) {
                                                snapGuideX = null
                                                snapGuideY = null
                                                history = history.updateSelectedOffset(dx, dy)
                                            } else {
                                                val proposedX = old.x + dx
                                                val proposedY = old.y + dy
                                                val visualWidth = old.width * old.scaleX
                                                val visualHeight = old.height * old.scaleY
                                                val xTargets = mutableListOf(
                                                    0f to 0f,
                                                    (history.document.canvas.width - visualWidth) / 2f to history.document.canvas.width / 2f,
                                                    (history.document.canvas.width - visualWidth) to history.document.canvas.width
                                                )
                                                val yTargets = mutableListOf(
                                                    0f to 0f,
                                                    (history.document.canvas.height - visualHeight) / 2f to history.document.canvas.height / 2f,
                                                    (history.document.canvas.height - visualHeight) to history.document.canvas.height
                                                )
                                                history.document.objects.filter { it.id != item.id && it.visible }.forEach { other ->
                                                    val ot = other.transform
                                                    val ow = ot.width * ot.scaleX
                                                    val oh = ot.height * ot.scaleY
                                                    xTargets += ot.x to ot.x
                                                    xTargets += (ot.x + (ow - visualWidth) / 2f) to (ot.x + ow / 2f)
                                                    xTargets += (ot.x + ow - visualWidth) to (ot.x + ow)
                                                    yTargets += ot.y to ot.y
                                                    yTargets += (ot.y + (oh - visualHeight) / 2f) to (ot.y + oh / 2f)
                                                    yTargets += (ot.y + oh - visualHeight) to (ot.y + oh)
                                                }
                                                val nearestX = xTargets.minByOrNull { kotlin.math.abs(it.first - proposedX) }
                                                    ?.takeIf { kotlin.math.abs(it.first - proposedX) <= 8f / (scaleX * viewportScale) }
                                                val nearestY = yTargets.minByOrNull { kotlin.math.abs(it.first - proposedY) }
                                                    ?.takeIf { kotlin.math.abs(it.first - proposedY) <= 8f / (scaleY * viewportScale) }
                                                snapGuideX = nearestX?.second
                                                snapGuideY = nearestY?.second
                                                history = history.updateTransform(
                                                    item.id, old.copy(x = nearestX?.first ?: proposedX, y = nearestY?.first ?: proposedY)
                                                )
                                            }
                                        }
                                    }
                                }

                            when (item) {
                                is XingtuV2Object.Text -> Box(objectModifier.padding(2.dp), contentAlignment = Alignment.CenterStart) {
                                    Text(
                                        text = item.content,
                                        color = Color(item.color),
                                        fontSize = (item.fontSizeSp * scaleX * sqrt((t.scaleX * t.scaleY).coerceAtLeast(0.01f))).coerceIn(8f, 160f).sp,
                                        fontFamily = when (item.fontFamily) {
                                            "serif" -> FontFamily.Serif
                                            "mono" -> FontFamily.Monospace
                                            "cursive" -> FontFamily.Cursive
                                            else -> FontFamily.SansSerif
                                        },
                                        fontWeight = FontWeight(item.fontWeight.coerceIn(100, 900)),
                                        fontStyle = if (item.italic) FontStyle.Italic else FontStyle.Normal,
                                        lineHeight = (item.fontSizeSp * item.lineHeight * scaleX * sqrt((t.scaleX * t.scaleY).coerceAtLeast(0.01f))).sp,
                                        letterSpacing = (item.letterSpacing * scaleX * t.scaleX).sp,
                                        textAlign = when (item.textAlign) {
                                            "center" -> TextAlign.Center
                                            "end" -> TextAlign.End
                                            else -> TextAlign.Start
                                        },
                                        modifier = Modifier.fillMaxSize()
                                    )
                                }
                                is XingtuV2Object.Component -> {
                                    val shape = when (item.componentType) {
                                        "ellipse" -> CircleShape
                                        "rounded-rectangle" -> RoundedCornerShape((item.cornerRadius * scaleX).dp)
                                        else -> RectangleShape
                                    }
                                    if (item.componentType == "line") {
                                        Box(objectModifier.background(Color(item.fillColor)))
                                    } else {
                                        Box(objectModifier.clip(shape)
                                            .background(Color(item.fillColor))
                                            .border((item.strokeWidth * scaleX).dp, Color(item.strokeColor), shape))
                                    }
                                }
                                is XingtuV2Object.Image -> {
                                    val bitmap by produceState<androidx.compose.ui.graphics.ImageBitmap?>(null, item.assetUri, item.cropLeft, item.cropTop, item.cropRight, item.cropBottom) {
                                        value = withContext(Dispatchers.IO) {
                                            runCatching {
                                                context.contentResolver.openInputStream(Uri.parse(item.assetUri))?.use { stream ->
                                                    val source = BitmapFactory.decodeStream(stream) ?: return@use null
                                                    val left = (source.width * item.cropLeft.coerceIn(0f, 0.95f)).toInt()
                                                    val top = (source.height * item.cropTop.coerceIn(0f, 0.95f)).toInt()
                                                    val right = (source.width * item.cropRight.coerceIn(item.cropLeft + 0.05f, 1f)).toInt()
                                                    val bottom = (source.height * item.cropBottom.coerceIn(item.cropTop + 0.05f, 1f)).toInt()
                                                    val cropped = Bitmap.createBitmap(
                                                        source, left, top,
                                                        (right - left).coerceAtLeast(1),
                                                        (bottom - top).coerceAtLeast(1)
                                                    )
                                                    if (cropped !== source) source.recycle()
                                                    cropped.asImageBitmap()
                                                }
                                            }.getOrNull()
                                        }
                                    }
                                    Box(objectModifier.clip(RoundedCornerShape(2.dp)).background(Color(0xFFE9E9E9))) {
                                        if (bitmap != null) {
                                            Image(bitmap = bitmap!!, contentDescription = "画布图片",
                                                modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop,
                                                colorFilter = ColorFilter.colorMatrix(v2ImageColorMatrix(item)))
                                        } else {
                                            Text("图片", color = Color.DarkGray, fontSize = 12.sp,
                                                modifier = Modifier.align(Alignment.Center))
                                        }
                                    }
                                }
                            }
                            if (selected && !item.locked) {
                                val handlePoints = listOf(
                                    Triple(0f, 0f, -1 to -1), Triple(.5f, 0f, 0 to -1), Triple(1f, 0f, 1 to -1),
                                    Triple(0f, .5f, -1 to 0), Triple(1f, .5f, 1 to 0),
                                    Triple(0f, 1f, -1 to 1), Triple(.5f, 1f, 0 to 1), Triple(1f, 1f, 1 to 1)
                                )
                                handlePoints.forEach { (hx, hy, edge) ->
                                    Box(
                                        Modifier.offset {
                                            val radians = Math.toRadians(t.rotation.toDouble())
                                            val cx = t.x + t.width * t.scaleX / 2f
                                            val cy = t.y + t.height * t.scaleY / 2f
                                            val px = t.x + t.width * t.scaleX * hx
                                            val py = t.y + t.height * t.scaleY * hy
                                            val rotatedX = cx + (px - cx) * cos(radians).toFloat() - (py - cy) * sin(radians).toFloat()
                                            val rotatedY = cy + (px - cx) * sin(radians).toFloat() + (py - cy) * cos(radians).toFloat()
                                            IntOffset(
                                                ((rotatedX * scaleX - 7f) * density).roundToInt(),
                                                ((rotatedY * scaleY - 7f) * density).roundToInt()
                                            )
                                        }
                                        .size(14.dp).clip(CircleShape)
                                        .background(colors.surface)
                                        .border(1.5.dp, colors.primary, CircleShape)
                                        .pointerInput(item.id, scaleX, scaleY, edge) {
                                            detectDragGestures(
                                                onDragStart = { history = history.beginTransform() },
                                                onDragEnd = { history = history.endTransform() },
                                                onDragCancel = { history = history.endTransform() }
                                            ) { change, drag ->
                                                change.consume()
                                                val current = history.document.objects.firstOrNull { it.id == item.id } ?: return@detectDragGestures
                                                val old = current.transform
                                                val screenDx = (drag.x / density) / (scaleX * viewportScale)
                                                val screenDy = (drag.y / density) / (scaleY * viewportScale)
                                                val radians = Math.toRadians(old.rotation.toDouble())
                                                val dx = (screenDx * cos(radians).toFloat() + screenDy * sin(radians).toFloat()) / old.scaleX.coerceAtLeast(0.01f)
                                                val dy = (-screenDx * sin(radians).toFloat() + screenDy * cos(radians).toFloat()) / old.scaleY.coerceAtLeast(0.01f)
                                                var x = old.x
                                                var y = old.y
                                                var width = old.width
                                                var height = old.height
                                                if (edge.first < 0) {
                                                    val nextWidth = (width - dx).coerceAtLeast(24f)
                                                    x += (width - nextWidth) * old.scaleX
                                                    width = nextWidth
                                                } else if (edge.first > 0) {
                                                    width = (width + dx).coerceAtLeast(24f)
                                                }
                                                if (edge.second < 0) {
                                                    val nextHeight = (height - dy).coerceAtLeast(24f)
                                                    y += (height - nextHeight) * old.scaleY
                                                    height = nextHeight
                                                } else if (edge.second > 0) {
                                                    height = (height + dy).coerceAtLeast(24f)
                                                }
                                                history = history.updateTransform(
                                                    item.id, old.copy(x = x, y = y, width = width, height = height)
                                                )
                                            }
                                        }
                                    )
                                }
                                Box(
                                    Modifier.offset {
                                        val radians = Math.toRadians(t.rotation.toDouble())
                                        val cx = t.x + t.width * t.scaleX / 2f
                                        val cy = t.y + t.height * t.scaleY / 2f
                                        val handleX = cx - (t.height * t.scaleY / 2f + 34f) * sin(radians).toFloat()
                                        val handleY = cy - (t.height * t.scaleY / 2f + 34f) * cos(radians).toFloat()
                                        IntOffset(
                                            ((handleX * scaleX - 6f) * density).roundToInt(),
                                            ((handleY * scaleY - 6f) * density).roundToInt()
                                        )
                                    }
                                    .size(12.dp).clip(CircleShape).background(colors.primary)
                                    .pointerInput(item.id, t.height, scaleY, viewportScale) {
                                        var totalDragX = 0f
                                        var totalDragY = 0f
                                        var startRotation = t.rotation
                                        detectDragGestures(
                                            onDragStart = {
                                                totalDragX = 0f
                                                totalDragY = 0f
                                                startRotation = history.document.objects.firstOrNull { it.id == item.id }?.transform?.rotation ?: t.rotation
                                                history = history.beginTransform()
                                            },
                                            onDragEnd = { history = history.endTransform() },
                                            onDragCancel = { history = history.endTransform() }
                                        ) { change, drag ->
                                            change.consume()
                                            totalDragX += drag.x
                                            totalDragY += drag.y
                                            val radius = t.height * t.scaleY / 2f + 34f
                                            val startRadians = Math.toRadians(startRotation.toDouble())
                                            val startVectorX = radius * sin(startRadians).toFloat()
                                            val startVectorY = -radius * cos(startRadians).toFloat()
                                            val dragCanvasX = totalDragX / density / (scaleX * viewportScale)
                                            val dragCanvasY = totalDragY / density / (scaleY * viewportScale)
                                            val initialAngle = atan2(startVectorY.toDouble(), startVectorX.toDouble())
                                            val currentAngle = atan2(
                                                (startVectorY + dragCanvasY).toDouble(),
                                                (startVectorX + dragCanvasX).toDouble()
                                            )
                                            var deltaAngle = Math.toDegrees(currentAngle - initialAngle).toFloat()
                                            while (deltaAngle > 180f) deltaAngle -= 360f
                                            while (deltaAngle < -180f) deltaAngle += 360f
                                            val current = history.document.objects.firstOrNull { it.id == item.id } ?: return@detectDragGestures
                                            history = history.updateTransform(
                                                item.id, current.transform.copy(rotation = startRotation + deltaAngle)
                                            )
                                        }
                                    }
                                )
                            }
                        }
                    }
                    snapGuideX?.let { guide ->
                        Box(
                            Modifier.offset { IntOffset((guide * scaleX * density).roundToInt(), 0) }
                                .width(1.dp).fillMaxHeight().background(colors.primary.copy(alpha = .65f))
                        )
                    }
                    snapGuideY?.let { guide ->
                        Box(
                            Modifier.offset { IntOffset(0, (guide * scaleY * density).roundToInt()) }
                                .height(1.dp).fillMaxWidth().background(colors.primary.copy(alpha = .65f))
                        )
                    }
                }
            }
            Row(
                Modifier.align(Alignment.TopEnd).padding(10.dp)
                    .clip(RoundedCornerShape(10.dp)).background(colors.surface.copy(alpha = .94f))
                    .padding(horizontal = 4.dp, vertical = 3.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(2.dp)
            ) {
                Text("−", color = colors.onSurface, fontSize = 18.sp,
                    modifier = Modifier.clickable { viewportScale = (viewportScale / 1.15f).coerceIn(.5f, 3f) }.padding(horizontal = 8.dp, vertical = 4.dp))
                Text("${(viewportScale * 100).roundToInt()}%", color = colors.onSurfaceVariant, fontSize = 10.sp)
                Text("+", color = colors.onSurface, fontSize = 18.sp,
                    modifier = Modifier.clickable { viewportScale = (viewportScale * 1.15f).coerceIn(.5f, 3f) }.padding(horizontal = 8.dp, vertical = 4.dp))
                Text("复位", color = colors.primary, fontSize = 11.sp,
                    modifier = Modifier.clickable {
                        viewportScale = 1f
                        viewportPanX = 0f
                        viewportPanY = 0f
                    }.padding(horizontal = 7.dp, vertical = 5.dp))
            }
            if (history.document.selectedIds.isNotEmpty()) {
                Text(
                    "${history.document.selectedIds.size} 个对象已选中" + if (multiSelect) " · 多选" else "",
                    color = colors.primary, fontSize = 11.sp,
                    modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp)
                )
            }
        }

        if (showVersions) {
            Column(Modifier.fillMaxWidth().heightIn(max = 250.dp).background(colors.surface).padding(horizontal = 12.dp, vertical = 8.dp)) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("版本记录（最多保留 20 个）", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = colors.onSurface)
                    ObjectToolChip("导入 JSON") {
                        importDocumentLauncher.launch(arrayOf("application/json", "text/plain"))
                    }
                    ObjectToolChip("导出 JSON") {
                        exportDocumentLauncher.launch("xingtu-v2-document.json")
                    }
                    ObjectToolChip("保存当前版本") {
                        savedVersions = XingtuV2Persistence.createVersion(
                            context, history.document, "版本 ${savedVersions.size + 1}"
                        )
                    }
                }
                LazyColumn {
                    items(savedVersions, key = { it.id }) { version ->
                        Row(Modifier.fillMaxWidth().height(42.dp), verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(version.label, color = colors.onSurface, fontSize = 12.sp)
                                Text(java.text.SimpleDateFormat("MM-dd HH:mm", java.util.Locale.getDefault()).format(java.util.Date(version.createdAt)),
                                    color = colors.onSurfaceVariant, fontSize = 10.sp)
                            }
                            ObjectToolChip("恢复") {
                                XingtuV2Persistence.restoreVersion(context, version.id)?.let { restored ->
                                    history = XingtuV2History(restored)
                                    activePanel = null
                                    activeCanvasPanel = false
                                    activeMultiTransform = false
                                }
                                showVersions = false
                            }
                        }
                    }
                }
            }
        }

        if (showLayers) {
            Column(Modifier.fillMaxWidth().heightIn(max = 220.dp).background(colors.surface).padding(horizontal = 12.dp, vertical = 8.dp)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text("图层", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = colors.onSurface)
                    Text("多选", color = if (multiSelect) colors.primary else colors.onSurfaceVariant,
                        modifier = Modifier.clickable { multiSelect = !multiSelect }.padding(6.dp))
                }
                LazyColumn {
                    items(history.document.objects.asReversed(), key = { it.id }) { item ->
                        Row(Modifier.fillMaxWidth().height(38.dp).clickable {
                            history = history.dispatch(XingtuV2Action.Select(setOf(item.id), additive = multiSelect))
                        }.padding(horizontal = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                            Text(if (item.id in history.document.selectedIds) "●" else "○",
                                color = colors.primary, fontSize = 12.sp, modifier = Modifier.padding(end = 8.dp))
                            Text(when (item) {
                                is XingtuV2Object.Text -> item.content
                                is XingtuV2Object.Image -> "图片"
                                is XingtuV2Object.Component -> "组件 · ${item.componentType}"
                            }, color = colors.onSurface, fontSize = 12.sp, modifier = Modifier.weight(1f), maxLines = 1)
                            val layerIndex = history.document.objects.indexOfFirst { it.id == item.id }
                            Text("↑", color = colors.onSurfaceVariant,
                                modifier = Modifier.clickable(enabled = layerIndex < history.document.objects.lastIndex) {
                                    history = history.dispatch(XingtuV2Action.Reorder(item.id, layerIndex + 1))
                                }.padding(horizontal = 4.dp))
                            Text("↓", color = colors.onSurfaceVariant,
                                modifier = Modifier.clickable(enabled = layerIndex > 0) {
                                    history = history.dispatch(XingtuV2Action.Reorder(item.id, layerIndex - 1))
                                }.padding(horizontal = 4.dp))
                            Text(if (item.visible) "显示" else "隐藏",
                                color = colors.onSurfaceVariant, fontSize = 10.sp,
                                modifier = Modifier.clickable {
                                    history = history.dispatch(XingtuV2Action.SetVisibility(item.id, !item.visible))
                                }.padding(horizontal = 6.dp))
                            Text(if (item.locked) "已锁" else "锁定",
                                color = colors.onSurfaceVariant, fontSize = 10.sp,
                                modifier = Modifier.clickable {
                                    history = history.dispatch(XingtuV2Action.SetLocked(item.id, !item.locked))
                                }.padding(horizontal = 6.dp))
                            Text("×", color = colors.error, fontSize = 18.sp,
                                modifier = Modifier.clickable {
                                    history = history.dispatch(XingtuV2Action.DeleteObjects(setOf(item.id)))
                                }.padding(horizontal = 6.dp))
                        }
                    }
                }
            }
        }

        if (showComponentPicker) {
            Row(Modifier.fillMaxWidth().background(colors.surface).horizontalScroll(rememberScrollState()).padding(horizontal = 10.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ObjectToolChip("矩形") { addComponent("rectangle") }
                ObjectToolChip("圆角矩形") { addComponent("rounded-rectangle") }
                ObjectToolChip("圆形") { addComponent("ellipse") }
                ObjectToolChip("线条") { addComponent("line") }
                ObjectToolChip("关闭") { showComponentPicker = false }
            }
        }

        val selectedObject = history.document.selectedObjects().singleOrNull()
        if (activeCanvasPanel) {
            XingtuV2CanvasPanel(
                canvas = history.document.canvas,
                panelHeight = panelHeight,
                onPanelHeightChange = { panelHeight = it.coerceIn(200f, 400f) },
                onUpdate = { history = history.updateCanvasLive(it) },
                onClose = {
                    history = history.endTransform()
                    activeCanvasPanel = false
                }
            )
        } else if (activeMultiTransform && history.document.selectedIds.size > 1) {
            XingtuV2MultiTransformPanel(
                panelHeight = panelHeight,
                onPanelHeightChange = { panelHeight = it.coerceIn(200f, 400f) },
                scale = groupScale,
                rotation = groupRotation,
                onScaleChange = { value ->
                    history = history.updateSelectedGroup(value / groupScale, 0f)
                    groupScale = value
                },
                onRotationChange = { value ->
                    history = history.updateSelectedGroup(1f, value - groupRotation)
                    groupRotation = value
                },
                onClose = {
                    history = history.endTransform()
                    activeMultiTransform = false
                }
            )
        } else if (activePanel != null && selectedObject != null) {
            XingtuV2PropertyPanel(
                selectedObject = selectedObject,
                tab = activePanel!!,
                panelHeight = panelHeight,
                onPanelHeightChange = { panelHeight = it.coerceIn(200f, 400f) },
                onClose = {
                    history = history.endTransform()
                    activePanel = null
                },
                onUpdate = { history = history.updateObjectLive(it) },
                onReplaceImage = {
                    if (activePanel == null) history = history.beginTransform()
                    replaceTargetId = selectedObject.id
                    imagePicker.launch(arrayOf("image/*"))
                }
            )
        } else if (history.document.selectedIds.size > 1) {
            Row(
                Modifier.fillMaxWidth().height(58.dp).background(colors.surface)
                    .horizontalScroll(rememberScrollState()).padding(horizontal = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text("${history.document.selectedIds.size} 个对象", color = colors.primary, fontSize = 12.sp)
                ObjectToolChip("整体变换") {
                    history = history.beginTransform()
                    groupScale = 1f
                    groupRotation = 0f
                    activeMultiTransform = true
                }
                ObjectToolChip("左对齐") { history = history.alignSelected("left") }
                ObjectToolChip("水平居中") { history = history.alignSelected("center-x") }
                ObjectToolChip("右对齐") { history = history.alignSelected("right") }
                ObjectToolChip("顶对齐") { history = history.alignSelected("top") }
                ObjectToolChip("垂直居中") { history = history.alignSelected("center-y") }
                ObjectToolChip("底对齐") { history = history.alignSelected("bottom") }
                ObjectToolChip("水平分布") { history = history.distributeSelected(true) }
                ObjectToolChip("垂直分布") { history = history.distributeSelected(false) }
                ObjectToolChip("共同移动") { activePanel = null }
                ObjectToolChip("删除所选") {
                    history = history.dispatch(XingtuV2Action.DeleteObjects(history.document.selectedIds))
                    activePanel = null
                }
                ObjectToolChip("取消多选") {
                    history = history.dispatch(XingtuV2Action.Select(emptySet()))
                    multiSelect = false
                    activePanel = null
                }
                ObjectToolChip("图层") { showLayers = true }
            }
        } else if (selectedObject != null) {
            Row(
                Modifier.fillMaxWidth().height(58.dp).background(colors.surface)
                    .horizontalScroll(rememberScrollState()).padding(horizontal = 8.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                when (selectedObject) {
                    is XingtuV2Object.Text -> listOf("编辑", "字体", "样式", "排版", "透明度", "变换").forEach { tab ->
                        ObjectToolChip(tab) {
                            if (activePanel == null) history = history.beginTransform()
                            activePanel = tab
                        }
                    }
                    is XingtuV2Object.Image -> listOf("替换", "裁剪", "调色", "透明度", "变换").forEach { tab ->
                        ObjectToolChip(tab) {
                            if (tab == "替换") {
                                history = history.beginTransform()
                                replaceTargetId = selectedObject.id
                                imagePicker.launch(arrayOf("image/*"))
                            } else {
                                if (activePanel == null) history = history.beginTransform()
                                activePanel = tab
                            }
                        }
                    }
                    is XingtuV2Object.Component -> listOf("形状", "填充", "圆角", "边框", "变换").forEach { tab ->
                        ObjectToolChip(tab) {
                            if (activePanel == null) history = history.beginTransform()
                            activePanel = tab
                        }
                    }
                }
                ObjectToolChip("复制") {
                    val id = selectedObject.id
                    history = history.dispatch(XingtuV2Action.DuplicateObject(id, "copy-${System.nanoTime()}"))
                    activePanel = null
                }
                ObjectToolChip("图层") { showLayers = !showLayers }
                ObjectToolChip("删除") {
                    history = history.dispatch(XingtuV2Action.DeleteObjects(history.document.selectedIds))
                    activePanel = null
                }
            }
        } else {
            Row(
                Modifier.fillMaxWidth().height(68.dp).background(colors.surface).padding(horizontal = 6.dp),
                horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically
            ) {
                BottomTool("文字", "T", colors.primary) {
                    val count = history.document.objects.count { it.kind == XingtuV2ObjectKind.TEXT } + 1
                    history = history.dispatch(XingtuV2Action.InsertObject(
                        XingtuV2Object.Text(
                            id = "text-${System.nanoTime()}", content = "双击编辑文字$count",
                            transform = XingtuV2Transform(x = 110f, y = 180f + count * 100f, width = 520f, height = 90f)
                        )
                    ))
                    showLayers = false
                }
                BottomTool("图片", "▧", colors.primary) { imagePicker.launch(arrayOf("image/*")) }
                BottomTool("图层", "▤", colors.primary) { showLayers = !showLayers }
                BottomTool("组件", "◇", colors.primary) {
                    showComponentPicker = !showComponentPicker
                    showLayers = false
                }
                BottomTool("画布", "▣", colors.primary) {
                    history = history.beginTransform()
                    activeCanvasPanel = true
                    showLayers = false
                }
            }
        }
    }
}

@Composable
private fun RowScope.BottomTool(label: String, symbol: String, activeColor: Color, onClick: () -> Unit) {
    Column(
        Modifier.weight(1f).fillMaxHeight().clickable(onClick = onClick).padding(vertical = 7.dp),
        horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center
    ) {
        Text(symbol, color = activeColor, fontSize = 21.sp, fontWeight = FontWeight.Medium)
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 11.sp)
    }
}


@Composable
private fun ObjectToolChip(label: String, onClick: () -> Unit) {
    Text(
        label,
        color = MaterialTheme.colorScheme.onSurface,
        fontSize = 12.sp,
        modifier = Modifier.clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .clickable(onClick = onClick).padding(horizontal = 13.dp, vertical = 10.dp)
    )
}

@Composable
private fun XingtuV2PropertyPanel(
    selectedObject: XingtuV2Object,
    tab: String,
    panelHeight: Float,
    onPanelHeightChange: (Float) -> Unit,
    onClose: () -> Unit,
    onUpdate: (XingtuV2Object) -> Unit,
    onReplaceImage: () -> Unit
) {
    val colors = MaterialTheme.colorScheme
    val density = LocalDensity.current.density
    Column(
        Modifier.fillMaxWidth().height(panelHeight.dp).background(colors.surface)
            .border(1.dp, colors.outlineVariant)
    ) {
        Row(
            Modifier.fillMaxWidth().height(42.dp).padding(horizontal = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("×", color = colors.onSurface, fontSize = 22.sp, modifier = Modifier.clickable { onClose() }.padding(horizontal = 8.dp))
            Box(
                Modifier.weight(1f).fillMaxHeight().pointerInput(panelHeight) {
                    detectDragGestures { change, drag ->
                        change.consume()
                        onPanelHeightChange(panelHeight - drag.y / density)
                    }
                },
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                    Box(Modifier.width(36.dp).height(4.dp).clip(CircleShape).background(colors.outlineVariant))
                    Text(tab, color = colors.onSurfaceVariant, fontSize = 10.sp)
                }
            }
            Text("✓", color = colors.primary, fontSize = 18.sp, modifier = Modifier.clickable { onClose() }.padding(horizontal = 8.dp))
        }
        Column(Modifier.fillMaxWidth().weight(1f).padding(horizontal = 14.dp).verticalScroll(rememberScrollState())) {
            when (selectedObject) {
                is XingtuV2Object.Text -> when (tab) {
                    "编辑" -> OutlinedTextField(
                        value = selectedObject.content,
                        onValueChange = { onUpdate(selectedObject.copy(content = it)) },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("文字内容") },
                        minLines = 2,
                        maxLines = 4
                    )
                    "字体" -> {
                        V2ValueSlider("字号", selectedObject.fontSizeSp, 8f..120f) {
                            onUpdate(selectedObject.copy(fontSizeSp = it))
                        }
                        V2ValueSlider("字重", selectedObject.fontWeight.toFloat(), 100f..900f) {
                            onUpdate(selectedObject.copy(fontWeight = (it / 100f).roundToInt() * 100))
                        }
                        Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            ObjectToolChip("无衬线") { onUpdate(selectedObject.copy(fontFamily = "default")) }
                            ObjectToolChip("宋体") { onUpdate(selectedObject.copy(fontFamily = "serif")) }
                            ObjectToolChip("等宽") { onUpdate(selectedObject.copy(fontFamily = "mono")) }
                            ObjectToolChip("手写") { onUpdate(selectedObject.copy(fontFamily = "cursive")) }
                            ObjectToolChip(if (selectedObject.italic) "取消斜体" else "斜体") {
                                onUpdate(selectedObject.copy(italic = !selectedObject.italic))
                            }
                        }
                    }
                    "排版" -> {
                        V2ValueSlider("文本框宽度", selectedObject.transform.width, 24f..1080f) {
                            onUpdate(selectedObject.copy(
                                boxWidth = it,
                                transform = selectedObject.transform.copy(width = it)
                            ))
                        }
                        V2ValueSlider("文本框高度", selectedObject.transform.height, 24f..1440f) {
                            onUpdate(selectedObject.copy(
                                boxHeight = it,
                                transform = selectedObject.transform.copy(height = it)
                            ))
                        }
                        V2ValueSlider("行距", selectedObject.lineHeight, 0.8f..2.5f) {
                            onUpdate(selectedObject.copy(lineHeight = it))
                        }
                        V2ValueSlider("字距", selectedObject.letterSpacing, -2f..12f) {
                            onUpdate(selectedObject.copy(letterSpacing = it))
                        }
                        Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            ObjectToolChip("左对齐") { onUpdate(selectedObject.copy(textAlign = "start")) }
                            ObjectToolChip("居中") { onUpdate(selectedObject.copy(textAlign = "center")) }
                            ObjectToolChip("右对齐") { onUpdate(selectedObject.copy(textAlign = "end")) }
                        }
                    }
                    "样式" -> {
                        Text("文字颜色", color = colors.onSurface, fontSize = 12.sp)
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(vertical = 10.dp)) {
                            listOf(0xFF222222, 0xFF666666, 0xFFE64A4A, 0xFF2878D0, 0xFF159765).forEach { value ->
                                Box(Modifier.size(30.dp).clip(CircleShape).background(Color(value))
                                    .border(1.dp, colors.outlineVariant, CircleShape)
                                    .clickable { onUpdate(selectedObject.copy(color = value)) })
                            }
                        }
                    }

                    "透明度" -> V2ValueSlider("透明度", selectedObject.transform.alpha, 0f..1f) {
                        onUpdate(selectedObject.copy(transform = selectedObject.transform.copy(alpha = it)))
                    }
                    "变换" -> V2TransformControls(selectedObject.transform) {
                        onUpdate(selectedObject.copy(transform = it))
                    }
                }
                is XingtuV2Object.Image -> when (tab) {
                    "裁剪" -> {
                        Text("裁剪范围（原图比例）", color = colors.onSurfaceVariant, fontSize = 11.sp)
                        V2ValueSlider("左侧", selectedObject.cropLeft, 0f..(selectedObject.cropRight - 0.05f).coerceAtLeast(0.01f)) {
                            onUpdate(selectedObject.copy(cropLeft = it))
                        }
                        V2ValueSlider("顶部", selectedObject.cropTop, 0f..(selectedObject.cropBottom - 0.05f).coerceAtLeast(0.01f)) {
                            onUpdate(selectedObject.copy(cropTop = it))
                        }
                        V2ValueSlider("右侧", selectedObject.cropRight, (selectedObject.cropLeft + 0.05f).coerceAtMost(0.99f)..1f) {
                            onUpdate(selectedObject.copy(cropRight = it))
                        }
                        V2ValueSlider("底部", selectedObject.cropBottom, (selectedObject.cropTop + 0.05f).coerceAtMost(0.99f)..1f) {
                            onUpdate(selectedObject.copy(cropBottom = it))
                        }
                    }
                    "调色" -> {
                        V2ValueSlider("色温", selectedObject.colorTemperature, -100f..100f) {
                            onUpdate(selectedObject.copy(colorTemperature = it))
                        }
                        V2ValueSlider("亮度", selectedObject.brightness, -1f..1f) {
                            onUpdate(selectedObject.copy(brightness = it))
                        }
                        V2ValueSlider("饱和度", selectedObject.saturation, 0f..2f) {
                            onUpdate(selectedObject.copy(saturation = it))
                        }
                    }
                    "透明度" -> V2ValueSlider("透明度", selectedObject.transform.alpha, 0f..1f) {
                        onUpdate(selectedObject.copy(transform = selectedObject.transform.copy(alpha = it)))
                    }
                    "变换" -> V2TransformControls(selectedObject.transform) {
                        onUpdate(selectedObject.copy(transform = it))
                    }
                    else -> Text("替换图片", color = colors.primary, modifier = Modifier.clickable { onReplaceImage() }.padding(12.dp))
                }
                is XingtuV2Object.Component -> when (tab) {
                    "形状" -> {
                        Text("组件形状", color = colors.onSurface, fontSize = 12.sp)
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(vertical = 8.dp),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            listOf("rectangle" to "矩形", "rounded-rectangle" to "圆角矩形", "ellipse" to "圆形", "line" to "线条").forEach { (type, label) ->
                                ObjectToolChip(if (selectedObject.componentType == type) "✓ $label" else label) {
                                    onUpdate(selectedObject.copy(componentType = type))
                                }
                            }
                        }
                        if (selectedObject.componentType == "line") {
                            Text("线条粗细", color = colors.onSurfaceVariant, fontSize = 11.sp)
                            V2ValueSlider("粗细", selectedObject.strokeWidth.coerceAtLeast(1f), 1f..40f) {
                                onUpdate(selectedObject.copy(strokeWidth = it))
                            }
                        }
                    }
                    "填充" -> {
                        Text("组件填充色", color = colors.onSurface, fontSize = 12.sp)
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(vertical = 10.dp),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            listOf(0xFFEDEFF2, 0xFFFFFFFF, 0xFF222222, 0xFF159765, 0xFF2878D0, 0xFFE64A4A, 0xFFFFB020).forEach { value ->
                                Box(Modifier.size(30.dp).clip(CircleShape).background(Color(value))
                                    .border(if (selectedObject.fillColor == value) 2.dp else 1.dp,
                                        if (selectedObject.fillColor == value) colors.primary else colors.outlineVariant, CircleShape)
                                    .clickable { onUpdate(selectedObject.copy(fillColor = value)) })
                            }
                        }
                    }
                    "圆角" -> V2ValueSlider("圆角", selectedObject.cornerRadius, 0f..80f) {
                        onUpdate(selectedObject.copy(cornerRadius = it))
                    }
                    "边框" -> {
                        V2ValueSlider("边框宽度", selectedObject.strokeWidth, 0f..40f) {
                            onUpdate(selectedObject.copy(strokeWidth = it))
                        }
                        Text("边框颜色", color = colors.onSurface, fontSize = 12.sp)
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(vertical = 8.dp),
                            horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            listOf(0xFF222222, 0xFF666666, 0xFFFFFFFF, 0xFFE64A4A, 0xFF2878D0, 0xFF159765, 0xFFFFB020).forEach { value ->
                                Box(Modifier.size(30.dp).clip(CircleShape).background(Color(value))
                                    .border(if (selectedObject.strokeColor == value) 2.dp else 1.dp,
                                        if (selectedObject.strokeColor == value) colors.primary else colors.outlineVariant, CircleShape)
                                    .clickable { onUpdate(selectedObject.copy(strokeColor = value)) })
                            }
                        }
                    }
                    "变换" -> V2TransformControls(selectedObject.transform) {
                        onUpdate(selectedObject.copy(transform = it))
                    }
                }
            }
        }
    }
}

@Composable
private fun XingtuV2CanvasPanel(
    canvas: XingtuV2Canvas,
    panelHeight: Float,
    onPanelHeightChange: (Float) -> Unit,
    onUpdate: (XingtuV2Canvas) -> Unit,
    onClose: () -> Unit
) {
    val colors = MaterialTheme.colorScheme
    val density = LocalDensity.current.density
    Column(Modifier.fillMaxWidth().height(panelHeight.dp).background(colors.surface).border(1.dp, colors.outlineVariant)) {
        Row(Modifier.fillMaxWidth().height(42.dp).padding(horizontal = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("×", color = colors.onSurface, fontSize = 22.sp, modifier = Modifier.clickable { onClose() }.padding(horizontal = 8.dp))
            Box(Modifier.weight(1f).fillMaxHeight().pointerInput(panelHeight) {
                detectDragGestures { change, drag ->
                    change.consume()
                    onPanelHeightChange((panelHeight - drag.y / density).coerceIn(200f, 400f))
                }
            }, contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(Modifier.width(36.dp).height(4.dp).clip(CircleShape).background(colors.outlineVariant))
                    Text("画布设置", color = colors.onSurfaceVariant, fontSize = 10.sp)
                }
            }
            Text("✓", color = colors.primary, fontSize = 18.sp, modifier = Modifier.clickable { onClose() }.padding(horizontal = 8.dp))
        }
        Column(Modifier.fillMaxWidth().weight(1f).padding(horizontal = 14.dp).verticalScroll(rememberScrollState())) {
            V2ValueSlider("画布宽度", canvas.width, 320f..3000f) { onUpdate(canvas.copy(width = it)) }
            V2ValueSlider("画布高度", canvas.height, 320f..4000f) { onUpdate(canvas.copy(height = it)) }
            Text("背景颜色", color = colors.onSurface, fontSize = 12.sp)
            Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                listOf(0xFFFFFFFF, 0xFFF5F5F5, 0xFF222222, 0xFFFFF1D2, 0xFFE7F2FF, 0xFFFFE9E9).forEach { color ->
                    Box(Modifier.size(30.dp).clip(CircleShape).background(Color(color))
                        .border(1.dp, colors.outlineVariant, CircleShape)
                        .clickable { onUpdate(canvas.copy(backgroundColor = color)) })
                }
            }
        }
    }
}

@Composable
private fun XingtuV2MultiTransformPanel(
    panelHeight: Float,
    onPanelHeightChange: (Float) -> Unit,
    scale: Float,
    rotation: Float,
    onScaleChange: (Float) -> Unit,
    onRotationChange: (Float) -> Unit,
    onClose: () -> Unit
) {
    val colors = MaterialTheme.colorScheme
    val density = LocalDensity.current.density
    Column(Modifier.fillMaxWidth().height(panelHeight.dp).background(colors.surface).border(1.dp, colors.outlineVariant)) {
        Row(Modifier.fillMaxWidth().height(42.dp).padding(horizontal = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("×", color = colors.onSurface, fontSize = 22.sp, modifier = Modifier.clickable { onClose() }.padding(horizontal = 8.dp))
            Box(Modifier.weight(1f).fillMaxHeight().pointerInput(panelHeight) {
                detectDragGestures { change, drag ->
                    change.consume()
                    onPanelHeightChange((panelHeight - drag.y / density).coerceIn(200f, 400f))
                }
            }, contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(Modifier.width(36.dp).height(4.dp).clip(CircleShape).background(colors.outlineVariant))
                    Text("多选整体变换", color = colors.onSurfaceVariant, fontSize = 10.sp)
                }
            }
            Text("✓", color = colors.primary, fontSize = 18.sp, modifier = Modifier.clickable { onClose() }.padding(horizontal = 8.dp))
        }
        Column(Modifier.fillMaxWidth().weight(1f).padding(horizontal = 14.dp).verticalScroll(rememberScrollState())) {
            V2ValueSlider("整体缩放", scale, 0.2f..3f, onScaleChange)
            V2ValueSlider("整体旋转", rotation, -180f..180f, onRotationChange)
        }
    }
}

@Composable
private fun V2ValueSlider(label: String, value: Float, range: ClosedFloatingPointRange<Float>, onChange: (Float) -> Unit) {
    Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(label, color = MaterialTheme.colorScheme.onSurface, fontSize = 12.sp)
            var numberText by remember { mutableStateOf(String.format("%.1f", value)) }
            LaunchedEffect(value) {
                val typed = numberText.toFloatOrNull()
                if (typed == null || kotlin.math.abs(typed - value) > 0.0001f) {
                    numberText = String.format("%.1f", value)
                }
            }
            OutlinedTextField(
                value = numberText,
                onValueChange = { input ->
                    numberText = input
                    input.toFloatOrNull()?.let { onChange(it.coerceIn(range.start, range.endInclusive)) }
                },
                modifier = Modifier.width(92.dp).height(42.dp),
                singleLine = true,
                textStyle = MaterialTheme.typography.labelSmall,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal)
            )
        }
        Slider(value = value.coerceIn(range.start, range.endInclusive), onValueChange = onChange, valueRange = range)
    }
}

@Composable
@Composable
private fun V2NumberField(label: String, value: Float, onValueChange: (Float) -> Unit, modifier: Modifier = Modifier) {
    var text by remember { mutableStateOf(String.format(java.util.Locale.US, "%.1f", value)) }
    LaunchedEffect(value) {
        val parsed = text.toFloatOrNull()
        if (parsed == null || kotlin.math.abs(parsed - value) > 0.0001f) {
            text = String.format(java.util.Locale.US, "%.1f", value)
        }
    }
    OutlinedTextField(
        value = text,
        onValueChange = { next ->
            text = next.filter { it.isDigit() || it == '.' || it == '-' }
            text.toFloatOrNull()?.let(onValueChange)
        },
        modifier = modifier,
        label = { Text(label, fontSize = 10.sp) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal)
    )
}

@Composable
private fun V2TransformControls(transform: XingtuV2Transform, onChange: (XingtuV2Transform) -> Unit) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        V2NumberField("X 坐标", transform.x, { onChange(transform.copy(x = it)) }, Modifier.weight(1f))
        V2NumberField("Y 坐标", transform.y, { onChange(transform.copy(y = it)) }, Modifier.weight(1f))
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        V2NumberField("宽度", transform.width, { onChange(transform.copy(width = it.coerceAtLeast(1f))) }, Modifier.weight(1f))
        V2NumberField("高度", transform.height, { onChange(transform.copy(height = it.coerceAtLeast(1f))) }, Modifier.weight(1f))
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        V2NumberField("缩放 X", transform.scaleX, { onChange(transform.copy(scaleX = it.coerceIn(0.1f, 10f))) }, Modifier.weight(1f))
        V2NumberField("缩放 Y", transform.scaleY, { onChange(transform.copy(scaleY = it.coerceIn(0.1f, 10f))) }, Modifier.weight(1f))
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        V2NumberField("旋转角度", transform.rotation, { onChange(transform.copy(rotation = it.coerceIn(-360f, 360f))) }, Modifier.weight(1f))
        V2NumberField("透明度 0–1", transform.alpha, { onChange(transform.copy(alpha = it.coerceIn(0f, 1f))) }, Modifier.weight(1f))
    }
    V2ValueSlider("X 坐标", transform.x, -1080f..2160f) { onChange(transform.copy(x = it)) }
    V2ValueSlider("Y 坐标", transform.y, -1440f..2880f) { onChange(transform.copy(y = it)) }
    V2ValueSlider("宽度", transform.width, 1f..2160f) { onChange(transform.copy(width = it)) }
    V2ValueSlider("高度", transform.height, 1f..2880f) { onChange(transform.copy(height = it)) }
    V2ValueSlider("缩放 X", transform.scaleX, 0.1f..10f) { onChange(transform.copy(scaleX = it)) }
    V2ValueSlider("缩放 Y", transform.scaleY, 0.1f..10f) { onChange(transform.copy(scaleY = it)) }
    V2ValueSlider("透明度", transform.alpha, 0f..1f) { onChange(transform.copy(alpha = it)) }
    V2ValueSlider("旋转角度", transform.rotation, -360f..360f) { onChange(transform.copy(rotation = it)) }
}

private fun v2ImageColorMatrix(item: XingtuV2Object.Image): ColorMatrix {
    val saturation = item.saturation.coerceIn(0f, 2f)
    val inverse = 1f - saturation
    val red = inverse * 0.213f
    val green = inverse * 0.715f
    val blue = inverse * 0.072f
    val brightness = item.brightness.coerceIn(-1f, 1f) * 0.25f
    val temperature = item.colorTemperature.coerceIn(-100f, 100f) / 100f * 0.12f
    return ColorMatrix(floatArrayOf(
        red + saturation, green, blue, 0f, brightness + temperature,
        red, green + saturation, blue, 0f, brightness,
        red, green, blue + saturation, 0f, brightness - temperature,
        0f, 0f, 0f, 1f, 0f
    ))
}
