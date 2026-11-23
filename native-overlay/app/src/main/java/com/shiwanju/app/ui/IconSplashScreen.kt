package com.shiwanju.app.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
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
import kotlinx.coroutines.delay

private data class SplashStyle(val background: Color, val foreground: Color, val icon: Int)

@Composable
fun IconSplashScreen(style: String, onFinished: () -> Unit) {
    val spec = when (style) {
        "cowboy" -> SplashStyle(Color(0xFF173B58), Color(0xFFE8D7B6), R.drawable.icon_style_cowboy)
        "code" -> SplashStyle(Color(0xFF06140E), Color(0xFF61FF91), R.drawable.icon_style_code)
        "line" -> SplashStyle(Color(0xFFF8F7F1), Color(0xFF263B42), R.drawable.icon_style_line)
        "plush" -> SplashStyle(Color(0xFFC77D91), Color(0xFFFFF0D9), R.drawable.icon_style_plush)
        "sky" -> SplashStyle(Color(0xFF79C7EF), Color(0xFF173B58), R.drawable.icon_style_sky)
        "space" -> SplashStyle(Color(0xFF050812), Color(0xFFD8E7FF), R.drawable.icon_style_space)
        "graffiti" -> SplashStyle(Color(0xFFDCEEFF), Color(0xFF165CC5), R.drawable.icon_style_graffiti)
        "playful" -> SplashStyle(Color(0xFFFFD95D), Color(0xFF654A12), R.drawable.icon_style_playful)
        "8bit" -> SplashStyle(Color(0xFF77718D), Color(0xFFF7E8C8), R.drawable.icon_style_8bit)
        "sketch" -> SplashStyle(Color(0xFF123B2D), Color(0xFFE7E0BE), R.drawable.icon_style_sketch)
        else -> SplashStyle(Color(0xFF1769C2), Color.White, R.drawable.icon_style_original)
    }
    var seconds by remember(style) { mutableIntStateOf(3) }
    var finished by remember(style) { mutableStateOf(false) }
    LaunchedEffect(style) {
        repeat(3) {
            delay(1000)
            seconds = 2 - it
        }
        if (!finished) onFinished()
    }
    Box(
        Modifier.fillMaxSize().background(spec.background).clickable {
            if (!finished) {
                finished = true
                onFinished()
            }
        }
    ) {
        Column(Modifier.align(Alignment.Center), horizontalAlignment = Alignment.CenterHorizontally) {
            Image(
                painter = painterResource(spec.icon),
                contentDescription = "拾万句",
                contentScale = androidx.compose.ui.layout.ContentScale.Fit,
                modifier = Modifier.size(104.dp).clip(RoundedCornerShape(20.dp))
            )
            Spacer(Modifier.height(22.dp))
            Text("拾万句", color = spec.foreground, fontSize = 28.sp,
                fontWeight = FontWeight.SemiBold, letterSpacing = 0.08.sp)
            Spacer(Modifier.height(10.dp))
            Text("一句两句拾万句", color = spec.foreground.copy(alpha = 0.78f),
                fontSize = 12.sp, letterSpacing = 0.12.sp, textAlign = TextAlign.Center)
        }
        Text(
            "跳过 ${seconds}s", color = spec.foreground.copy(alpha = 0.72f), fontSize = 11.sp,
            modifier = Modifier.align(Alignment.BottomEnd).padding(end = 18.dp, bottom = 22.dp)
                .clickable { if (!finished) { finished = true; onFinished() } }
                .padding(4.dp)
        )
    }
}
