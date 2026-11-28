package com.shiwanju.app.ui

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** 醒图 2.0 独立页面；不调用旧 ArticleEditorScreen。 */
@Composable
fun XingtuEditorV2Screen(onBack: () -> Unit) {
    var history by remember {
        mutableStateOf(XingtuV2History(XingtuV2Document(
            id = "xingtu-v2-document",
            objects = listOf(XingtuV2Object.Text(
                id = "sample-heading", content = "在画布上开始创作",
                fontSizeSp = 24f,
                transform = XingtuV2Transform(x = 80f, y = 220f, width = 280f, height = 70f)
            ))
        )))
    }
    var activeTool by remember { mutableStateOf("文字") }
    BackHandler(onBack = onBack)
    val colors = MaterialTheme.colorScheme

    Column(Modifier.fillMaxSize().background(colors.background).navigationBarsPadding()) {
        Row(
            Modifier.fillMaxWidth().height(48.dp).padding(horizontal = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("‹", fontSize = 30.sp, color = colors.onSurface, modifier = Modifier.clickable { onBack() }.padding(horizontal = 8.dp))
            Text("醒图", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = colors.onSurface)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("↶", fontSize = 22.sp, color = if (history.undoStack.isEmpty()) colors.onSurface.copy(alpha = .35f) else colors.onSurface,
                    modifier = Modifier.clickable(enabled = history.undoStack.isNotEmpty()) { history = history.undo() }.padding(horizontal = 8.dp))
                Text("↷", fontSize = 22.sp, color = if (history.redoStack.isEmpty()) colors.onSurface.copy(alpha = .35f) else colors.onSurface,
                    modifier = Modifier.clickable(enabled = history.redoStack.isNotEmpty()) { history = history.redo() }.padding(horizontal = 8.dp))
                Text("完成", fontSize = 13.sp, color = colors.primary, modifier = Modifier.clickable { onBack() }.padding(start = 10.dp))
            }
        }
        Box(
            Modifier.fillMaxWidth().weight(1f).background(colors.surfaceVariant.copy(alpha = .35f)),
            contentAlignment = Alignment.Center
        ) {
            BoxWithConstraints(Modifier.fillMaxWidth().padding(horizontal = 22.dp).fillMaxHeight(.88f), contentAlignment = Alignment.Center) {
                Box(
                    Modifier.width(maxWidth).height(maxHeight).clip(RoundedCornerShape(2.dp))
                        .background(Color.White).border(1.dp, colors.outlineVariant)
                ) {
                    Canvas(Modifier.fillMaxSize()) {
                        drawRect(Color.White)
                        drawRect(Color(0xFFE8E8E8), style = Stroke(width = 1.dp.toPx()))
                    }
                    history.document.objects.filter { it.visible }.forEach { item ->
                        when (item) {
                            is XingtuV2Object.Text -> Text(
                                text = item.content, color = Color(item.color), fontSize = item.fontSizeSp.sp,
                                fontWeight = if (item.id in history.document.selectedIds) FontWeight.Bold else FontWeight.Normal,
                                textAlign = TextAlign.Start,
                                modifier = Modifier.align(Alignment.TopStart).padding(start = 18.dp, top = 22.dp)
                                    .clickable { history = history.dispatch(XingtuV2Action.Select(setOf(item.id))) }
                            )
                            is XingtuV2Object.Image -> Unit
                            is XingtuV2Object.Component -> Unit
                        }
                    }
                    if (history.document.selectedIds.isNotEmpty()) {
                        Text("已选择 " + history.document.selectedIds.size + " 个对象",
                            color = colors.primary, fontSize = 11.sp,
                            modifier = Modifier.align(Alignment.BottomCenter).padding(bottom = 10.dp))
                    }
                }
            }
        }
        Row(
            Modifier.fillMaxWidth().height(64.dp).background(colors.surface).padding(horizontal = 8.dp),
            horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically
        ) {
            listOf("文字", "图片", "图层", "组件").forEach { tool ->
                val selected = activeTool == tool
                Column(
                    Modifier.weight(1f).fillMaxHeight().clickable { activeTool = tool }.padding(vertical = 8.dp),
                    horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center
                ) {
                    Text(when (tool) { "文字" -> "T"; "图片" -> "▧"; "图层" -> "▤"; else -> "◇" },
                        color = if (selected) colors.primary else colors.onSurfaceVariant, fontSize = 21.sp, fontWeight = FontWeight.Medium)
                    Text(tool, color = if (selected) colors.primary else colors.onSurfaceVariant, fontSize = 11.sp)
                }
            }
        }
    }
}
