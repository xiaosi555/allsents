package com.shiwanju.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private data class ThemeOption(val name: String, val hex: String)

private val themeOptions = listOf(
    ThemeOption("原版绿", "#01CC7A"), ThemeOption("珊瑚红", "#FF6B6B"),
    ThemeOption("海洋蓝", "#2688D9"), ThemeOption("电光紫", "#8B5CF6"),
    ThemeOption("活力橙", "#FF8A24"), ThemeOption("翡翠绿", "#16A66A"),
    ThemeOption("湖水青", "#16B8B0"), ThemeOption("玫瑰粉", "#F06292"),
    ThemeOption("柠檬黄", "#F4D21F"), ThemeOption("靛蓝", "#4656C9")
)

@Composable
fun ThemeSettingsPage(vm: AppViewModel) {
    val systemDark = isSystemInDarkTheme()
    LaunchedEffect(vm.appearanceMode, systemDark) {
        AppColors.setAppearanceMode(vm.appearanceMode, systemDark)
    }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 18.dp, vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(28.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(15.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SectionIcon("调色")
                Text("主题色", color = AppColors.MyText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
            }
            Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(18.dp)).background(AppColors.MyCard).padding(16.dp), verticalArrangement = Arrangement.spacedBy(15.dp)) {
                Box(Modifier.fillMaxWidth().height(145.dp).clip(RoundedCornerShape(18.dp)).background(Color(0xFFF2F5F6)), contentAlignment = Alignment.Center) {
                    Column(Modifier.fillMaxWidth(.82f).clip(RoundedCornerShape(13.dp)).background(Color.White).padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        repeat(3) { index ->
                            Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(9.dp)).background(if (index < 2) Color(0xFFEAF6FA) else Color(0xFFF4F4F4)).padding(9.dp), verticalAlignment = Alignment.CenterVertically) {
                                Box(Modifier.size(34.dp).clip(RoundedCornerShape(5.dp)).background(if (index < 2) AppColors.Theme else Color.LightGray))
                                Column(Modifier.weight(1f).padding(start = 9.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                                    Box(Modifier.fillMaxWidth(.9f).height(7.dp).clip(CircleShape).background(if (index < 2) AppColors.Theme.copy(alpha = .22f) else Color.LightGray.copy(alpha = .5f)))
                                    Box(Modifier.fillMaxWidth(.65f).height(7.dp).clip(CircleShape).background(if (index < 2) AppColors.Theme.copy(alpha = .22f) else Color.LightGray.copy(alpha = .5f)))
                                }
                            }
                        }
                    }
                }
                themeOptions.chunked(5).forEach { row ->
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        row.forEach { option ->
                            val selected = vm.themeColor.equals(option.hex, true)
                            Column(Modifier.weight(1f).clickable { vm.selectThemeColor(option.hex) }, horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Box(Modifier.fillMaxWidth().aspectRatio(1f).clip(RoundedCornerShape(11.dp)).background(Color(android.graphics.Color.parseColor(option.hex))).padding(3.dp), contentAlignment = Alignment.Center) {
                                    if (selected) Box(Modifier.fillMaxSize().clip(RoundedCornerShape(8.dp)).background(Color.Transparent).padding(2.dp)) {
                                        ShiWanJuLineIcon("成功", Color.White, Modifier.align(Alignment.Center).size(18.dp))
                                    }
                                }
                                Text(option.name, color = if (selected) AppColors.Theme else AppColors.MyText, fontSize = 10.sp, maxLines = 1)
                            }
                        }
                        repeat(5 - row.size) { Spacer(Modifier.weight(1f)) }
                    }
                }
            }
        }
        Column(verticalArrangement = Arrangement.spacedBy(15.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SectionIcon("对比度")
                Text("外观模式", color = AppColors.MyText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                listOf("system" to "跟随系统", "light" to "亮色", "dark" to "暗色").forEach { (mode, label) ->
                    val selected = vm.appearanceMode == mode
                    Box(
                        Modifier.weight(1f).height(68.dp).clip(RoundedCornerShape(12.dp))
                            .background(if (selected) AppColors.Theme.copy(alpha = .09f) else AppColors.MyCard)
                            .then(if (selected) Modifier.background(AppColors.Theme.copy(alpha = .06f), RoundedCornerShape(12.dp)) else Modifier)
                            .clickable { vm.selectAppearanceMode(mode, systemDark) },
                        contentAlignment = Alignment.Center
                    ) {
                        Text(label, color = if (selected) AppColors.Theme else AppColors.MyText, fontSize = 14.sp, fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal)
                    }
                }
            }
        }
        Column(verticalArrangement = Arrangement.spacedBy(15.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                SectionIcon("组件")
                Text("图标", color = AppColors.MyText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
            }
            IconSettingsSection(vm)
        }
    }
}

@Composable
private fun SectionIcon(key: String) {
    Box(Modifier.size(42.dp).clip(RoundedCornerShape(9.dp)).background(AppColors.Theme.copy(alpha = .10f)), contentAlignment = Alignment.Center) {
        ShiWanJuLineIcon(key, AppColors.Theme, Modifier.size(23.dp))
    }
}
