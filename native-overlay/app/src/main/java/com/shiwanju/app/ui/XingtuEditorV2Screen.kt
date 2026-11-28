package com.shiwanju.app.ui

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
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.math.roundToInt

/** 醒图 2.0 独立原生画布。旧版 ArticleEditorScreen 保持独立，不参与本页状态。 */
@Composable
fun XingtuEditorV2Screen(onBack: () -> Unit) {
    var history by remember {
        mutableStateOf(XingtuV2History(XingtuV2Document(
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
    var showLayers by remember { mutableStateOf(false) }
    val colors = MaterialTheme.colorScheme
    val context = LocalContext.current
    val density = LocalDensity.current.density

    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            val image = XingtuV2Object.Image(
                id = "image-${System.nanoTime()}",
                assetUri = uri.toString(),
                transform = XingtuV2Transform(x = 120f, y = 180f, width = 520f, height = 420f)
            )
            history = history.dispatch(XingtuV2Action.InsertObject(image))
            showLayers = false
        }
    }

    BackHandler(onBack = onBack)
    Column(Modifier.fillMaxSize().background(colors.background).navigationBarsPadding()) {
        Row(
            Modifier.fillMaxWidth().height(50.dp).padding(horizontal = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("‹", fontSize = 30.sp, color = colors.onSurface,
                modifier = Modifier.clickable { onBack() }.padding(horizontal = 8.dp))
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
                Text("完成", fontSize = 13.sp, color = colors.primary,
                    modifier = Modifier.clickable { onBack() }.padding(start = 8.dp))
            }
        }

        Box(
            Modifier.fillMaxWidth().weight(1f)
                .background(colors.surfaceVariant.copy(alpha = .35f)),
            contentAlignment = Alignment.Center
        ) {
            BoxWithConstraints(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                val canvasWidth = minOf(maxWidth - 28.dp, maxHeight * .75f)
                val canvasHeight = canvasWidth * (history.document.canvas.height / history.document.canvas.width)
                val scaleX = canvasWidth.value / history.document.canvas.width
                val scaleY = canvasHeight.value / history.document.canvas.height
                Box(
                    Modifier.width(canvasWidth).height(canvasHeight)
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
                                .size((t.width * scaleX).dp, (t.height * scaleY).dp)
                                .graphicsLayer {
                                    rotationZ = t.rotation
                                    scaleX = t.scaleX
                                    scaleY = t.scaleY
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
                                    detectTransformGestures { _, pan, zoom, rotation ->
                                        if (!item.locked) {
                                            val current = history.document.objects.firstOrNull { it.id == item.id } ?: item
                                            val old = current.transform
                                            val next = old.copy(
                                                x = old.x + (pan.x / density) / scaleX,
                                                y = old.y + (pan.y / density) / scaleY,
                                                width = (old.width * zoom).coerceIn(24f, 1080f),
                                                height = (old.height * zoom).coerceIn(24f, 1440f),
                                                rotation = old.rotation + rotation
                                            )
                                            history = history.dispatch(XingtuV2Action.TransformObject(item.id, next))
                                        }
                                    }
                                }

                            when (item) {
                                is XingtuV2Object.Text -> Box(objectModifier.padding(2.dp), contentAlignment = Alignment.CenterStart) {
                                    Text(
                                        text = item.content,
                                        color = Color(item.color),
                                        fontSize = (item.fontSizeSp * scaleX).coerceIn(8f, 48f).sp,
                                        textAlign = when (item.textAlign) {
                                            "center" -> TextAlign.Center
                                            "end" -> TextAlign.End
                                            else -> TextAlign.Start
                                        },
                                        modifier = Modifier.fillMaxSize()
                                    )
                                }
                                is XingtuV2Object.Component -> Box(
                                    objectModifier.clip(RoundedCornerShape(item.cornerRadius.dp))
                                        .background(Color(item.fillColor))
                                        .border(item.strokeWidth.dp, Color(item.strokeColor), RoundedCornerShape(item.cornerRadius.dp))
                                )
                                is XingtuV2Object.Image -> {
                                    val bitmap by produceState<androidx.compose.ui.graphics.ImageBitmap?>(null, item.assetUri) {
                                        value = withContext(Dispatchers.IO) {
                                            runCatching {
                                                context.contentResolver.openInputStream(Uri.parse(item.assetUri))?.use {
                                                    BitmapFactory.decodeStream(it)?.asImageBitmap()
                                                }
                                            }.getOrNull()
                                        }
                                    }
                                    Box(objectModifier.clip(RoundedCornerShape(2.dp)).background(Color(0xFFE9E9E9))) {
                                        if (bitmap != null) {
                                            Image(bitmap = bitmap!!, contentDescription = "画布图片",
                                                modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                                        } else {
                                            Text("图片", color = Color.DarkGray, fontSize = 12.sp,
                                                modifier = Modifier.align(Alignment.Center))
                                        }
                                    }
                                }
                            }
                            if (selected && !item.locked) {
                                Box(
                                    Modifier.offset {
                                        IntOffset(
                                            (((t.x + t.width) * scaleX - 7f) * density).roundToInt(),
                                            (((t.y + t.height) * scaleY - 7f) * density).roundToInt()
                                        )
                                    }
                                    .size(14.dp).clip(CircleShape).background(colors.primary)
                                    .pointerInput(item.id, scaleX, scaleY) {
                                        detectDragGestures { change, drag ->
                                            change.consume()
                                            val current = history.document.objects.firstOrNull { it.id == item.id } ?: return@detectDragGestures
                                            val next = current.transform.copy(
                                                width = (current.transform.width + (drag.x / density) / scaleX).coerceIn(24f, 1080f),
                                                height = (current.transform.height + (drag.y / density) / scaleY).coerceIn(24f, 1440f)
                                            )
                                            history = history.dispatch(XingtuV2Action.TransformObject(item.id, next))
                                        }
                                    }
                                )
                            }
                        }
                    }
                }
            }
            if (history.document.selectedIds.isNotEmpty()) {
                Text(
                    "${history.document.selectedIds.size} 个对象已选中" + if (multiSelect) " · 多选" else "",
                    color = colors.primary, fontSize = 11.sp,
                    modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp)
                )
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
                            Text(if (item.locked) "已锁" else "锁定",
                                color = colors.onSurfaceVariant, fontSize = 10.sp,
                                modifier = Modifier.clickable {
                                    history = history.dispatch(XingtuV2Action.SetLocked(item.id, !item.locked))
                                }.padding(horizontal = 8.dp))
                            Text("×", color = colors.error, fontSize = 18.sp,
                                modifier = Modifier.clickable {
                                    history = history.dispatch(XingtuV2Action.DeleteObjects(setOf(item.id)))
                                }.padding(horizontal = 6.dp))
                        }
                    }
                }
            }
        }

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
            BottomTool("图片", "▧", colors.primary) { imagePicker.launch("image/*") }
            BottomTool("图层", "▤", colors.primary) { showLayers = !showLayers }
            BottomTool("组件", "◇", colors.primary) {
                val count = history.document.objects.count { it.kind == XingtuV2ObjectKind.COMPONENT } + 1
                history = history.dispatch(XingtuV2Action.InsertObject(
                    XingtuV2Object.Component(
                        id = "component-${System.nanoTime()}", componentType = "rectangle",
                        fillColor = 0xFFEDEFF2, cornerRadius = 14f,
                        transform = XingtuV2Transform(x = 130f, y = 260f + count * 80f, width = 460f, height = 180f)
                    )
                ))
                showLayers = false
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
