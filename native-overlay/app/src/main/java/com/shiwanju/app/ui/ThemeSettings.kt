package com.shiwanju.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private data class ThemeOption(val name: String, val hex: String, val checkColor: Color)

private val themeOptions = listOf(
    ThemeOption("珊瑚红", "#FF6B6B", Color.Black),
    ThemeOption("海洋蓝", "#2688D9", Color.White),
    ThemeOption("电光紫", "#8B5CF6", Color.White),
    ThemeOption("活力橙", "#FF8A24", Color.Black),
    ThemeOption("翡翠绿", "#16A66A", Color.White),
    ThemeOption("湖水青", "#16B8B0", Color.White),
    ThemeOption("玫瑰粉", "#F06292", Color.White),
    ThemeOption("柠檬黄", "#F4D21F", Color.Black),
    ThemeOption("靛蓝", "#4656C9", Color.White)
)

/** 第一阶段仅提供主题颜色选择。 */
@Composable
fun ThemeSettingsPage(vm: AppViewModel) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(26.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("主题颜色", color = AppColors.MyText, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
            Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
                themeOptions.chunked(3).forEach { options ->
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(10.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        options.forEach { option ->
                            val selected = vm.themeColor.equals(option.hex, ignoreCase = true)
                            Row(
                                Modifier.weight(1f).clickable { vm.selectThemeColor(option.hex) }.padding(vertical = 3.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(7.dp)
                            ) {
                                Box(
                                    Modifier.size(19.dp).clip(CircleShape)
                                        .background(Color(android.graphics.Color.parseColor(option.hex))),
                                    contentAlignment = Alignment.Center
                                ) {
                                    if (selected) Text("✓", color = option.checkColor, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                }
                                Text(
                                    option.name,
                                    color = if (selected) AppColors.Theme else Color(0xFF444444),
                                    fontSize = 12.sp,
                                    fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
                                    maxLines = 1
                                )
                            }
                        }
                        repeat(3 - options.size) { Spacer(Modifier.weight(1f)) }
                    }
                }
            }
        }
    }
}
