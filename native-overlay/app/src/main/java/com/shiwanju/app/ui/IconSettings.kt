package com.shiwanju.app.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.shiwanju.app.R

private data class IconStyleOption(val id: String, val name: String, val image: Int)

private val iconStyles = listOf(
    IconStyleOption("original","原版",R.drawable.icon_style_original),
    IconStyleOption("cowboy","牛仔",R.drawable.icon_style_cowboy),
    IconStyleOption("code","代码",R.drawable.icon_style_code),
    IconStyleOption("line","简笔画",R.drawable.icon_style_line),
    IconStyleOption("plush","毛绒",R.drawable.icon_style_plush),
    IconStyleOption("sky","天空",R.drawable.icon_style_sky),
    IconStyleOption("space","深空",R.drawable.icon_style_space),
    IconStyleOption("graffiti","涂鸦",R.drawable.icon_style_graffiti),
    IconStyleOption("playful","童趣",R.drawable.icon_style_playful),
    IconStyleOption("8bit","8-Bit",R.drawable.icon_style_8bit),
    IconStyleOption("sketch","手稿",R.drawable.icon_style_sketch),
    IconStyleOption("classic","深蓝",R.drawable.icon_style_classic)
)

@Composable
fun IconSettingsSection(vm: AppViewModel) {
    Column(
        Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text("图标风格", color = AppColors.MyText, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
        Text("选择后会切换手机桌面图标；原版图形轮廓保持一致。", color = Color(0xFF8A8A8A), fontSize = 12.sp)
        iconStyles.chunked(4).forEach { row ->
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                row.forEach { option ->
                    val selected = vm.iconStyle == option.id
                    Column(
                        Modifier.weight(1f).clickable { vm.selectIconStyle(option.id) }.padding(vertical = 3.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(5.dp)
                    ) {
                        Box(Modifier.fillMaxWidth().aspectRatio(1f)) {
                            Image(
                                painter = painterResource(option.image),
                                contentDescription = option.name,
                                contentScale = androidx.compose.ui.layout.ContentScale.Fit,
                                modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(13.dp))
                            )
                            if (selected) {
                                Box(
                                    Modifier.align(Alignment.TopEnd).padding(3.dp).size(19.dp)
                                        .clip(CircleShape).background(AppColors.Theme),
                                    contentAlignment = Alignment.Center
                                ) {
                                    ShiWanJuLineIcon("成功", AppColors.OnTheme, Modifier.size(13.dp))
                                }
                            }
                        }
                        Text(
                            option.name,
                            color = if (selected) AppColors.Theme else AppColors.MyText,
                            fontSize = 12.sp,
                            fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal,
                            textAlign = TextAlign.Center,
                            maxLines = 1
                        )
                    }
                }
                repeat(4-row.size) { Spacer(Modifier.weight(1f)) }
            }
        }
    }
}
