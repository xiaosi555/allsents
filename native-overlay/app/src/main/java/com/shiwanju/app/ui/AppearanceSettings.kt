package com.shiwanju.app.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shiwanju.app.R

private data class ThemeChoice(val name: String, val hex: String)
private data class IconChoice(val key: String, val name: String, val res: Int)

private val themeChoices = listOf(
    ThemeChoice("珊瑚红", "#FF6B6B"), ThemeChoice("海洋蓝", "#2688D9"), ThemeChoice("电光紫", "#8B5CF6"),
    ThemeChoice("活力橙", "#FF8A24"), ThemeChoice("翡翠绿", "#16A66A"), ThemeChoice("湖水青", "#16B8B0"),
    ThemeChoice("玫瑰粉", "#F06292"), ThemeChoice("柠檬黄", "#F4D21F"), ThemeChoice("靛蓝", "#4656C9")
)

private val iconChoices = listOf(
    IconChoice("original", "原版", R.drawable.icon_style_original),
    IconChoice("cowboy", "牛仔", R.drawable.icon_style_cowboy),
    IconChoice("code", "代码", R.drawable.icon_style_code),
    IconChoice("line", "简笔画", R.drawable.icon_style_line),
    IconChoice("plush", "毛绒", R.drawable.icon_style_plush),
    IconChoice("sky", "天空", R.drawable.icon_style_sky),
    IconChoice("space", "深空", R.drawable.icon_style_space),
    IconChoice("graffiti", "涂鸦", R.drawable.icon_style_graffiti),
    IconChoice("kids", "童趣", R.drawable.icon_style_kids),
    IconChoice("pixel", "8-Bit", R.drawable.icon_style_pixel),
    IconChoice("sketch", "手稿", R.drawable.icon_style_sketch)
)

@Composable
fun AppearancePage(vm: AppViewModel) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(26.dp)
    ) {
        Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("主题颜色", color = AppColors.MyText, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
            themeChoices.chunked(3).forEach { row ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    row.forEach { item ->
                        val selected = vm.themeColor.equals(item.hex, ignoreCase = true)
                        Row(
                            Modifier.weight(1f).clickable { vm.selectThemeColor(item.hex) }.padding(vertical = 5.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(7.dp)
                        ) {
                            Box(Modifier.size(19.dp).clip(CircleShape).background(Color(android.graphics.Color.parseColor(item.hex))), contentAlignment = Alignment.Center) {
                                if (selected) Icon(Icons.Default.Check, contentDescription = "已选", tint = Color.White, modifier = Modifier.size(13.dp))
                            }
                            Text(item.name, color = if (selected) AppColors.Theme else AppColors.MyText, fontSize = 12.sp, fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal, maxLines = 1)
                        }
                    }
                    repeat(3 - row.size) { Spacer(Modifier.weight(1f)) }
                }
            }
        }
        Column(verticalArrangement = Arrangement.spacedBy(15.dp)) {
            Text("图标风格", color = AppColors.MyText, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
            iconChoices.chunked(4).forEach { row ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.Top) {
                    row.forEach { item ->
                        val selected = vm.iconStyle == item.key
                        Column(
                            Modifier.weight(1f).clickable { vm.selectIconStyle(item.key) },
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(7.dp)
                        ) {
                            Box(Modifier.fillMaxWidth().aspectRatio(1f).clip(RoundedCornerShape(14.dp))) {
                                Image(painterResource(item.res), contentDescription = item.name, modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Fit)
                                if (selected) Box(Modifier.align(Alignment.TopEnd).padding(5.dp).size(19.dp).clip(CircleShape).background(AppColors.Theme), contentAlignment = Alignment.Center) {
                                    Icon(Icons.Default.Check, contentDescription = "已选", tint = AppColors.OnTheme, modifier = Modifier.size(13.dp))
                                }
                            }
                            Text(item.name, color = if (selected) AppColors.Theme else AppColors.MyText, fontSize = 12.sp, fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal, textAlign = TextAlign.Center, maxLines = 1)
                        }
                    }
                    repeat(4 - row.size) { Spacer(Modifier.weight(1f)) }
                }
            }
        }
    }
}
