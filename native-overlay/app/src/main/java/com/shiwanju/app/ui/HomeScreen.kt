package com.shiwanju.app.ui

import android.content.Context
import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import coil.compose.AsyncImage
import com.shiwanju.app.data.TEXT_CATEGORIES
import com.shiwanju.app.engine.TextUtil

private val HtmlGreen = Color(0xFF22C55E)
private val HtmlBlack = Color(0xFF111111)
private val HtmlBg = Color(0xFFF3F4F6)
private val HtmlText = Color(0xFF1F2937)
private val HomeTabs = listOf("copy" to "文案", "type" to "类型", "upload" to "上传", "preview" to "预览", "cover" to "封面")
private val LayoutChoices = listOf(
    "moment" to "朋友圈版式",
    "douyin" to "抖音界面版",
    "breakline" to "文字断句版",
    "card" to "卡片版式",
    "purebg" to "背景纯文字"
)

@Composable
fun HomeScreen(vm: AppViewModel) {
    var tab by rememberSaveable { mutableStateOf("copy") }
    var uploadTab by rememberSaveable { mutableStateOf("code") }
    var expandedInput by rememberSaveable { mutableStateOf(false) }
    var coverUri by rememberSaveable { mutableStateOf("") }
    var douyinBgUri by rememberSaveable { mutableStateOf("") }
    val context = LocalContext.current
    val clipboard = LocalClipboardManager.current
    val account = vm.data.accounts.firstOrNull { it.id == vm.ui.accountId } ?: vm.data.accounts.firstOrNull()
    var appId by remember(account?.id, account?.appId) { mutableStateOf(account?.appId.orEmpty()) }

    val coverPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            runCatching { context.contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION) }
            coverUri = uri.toString()
        }
    }
    val backgroundPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) {
            runCatching { context.contentResolver.takePersistableUriPermission(uri, Intent.FLAG_GRANT_READ_URI_PERMISSION) }
            douyinBgUri = uri.toString()
        }
    }

    Column(Modifier.fillMaxSize().background(HtmlBg).systemBarsPadding()) {
        HeaderAndInput(
            input = vm.manualInput,
            onInput = vm::updateManualInput,
            onExpand = { expandedInput = true }
        )
        Row(Modifier.fillMaxWidth().background(Color.White), horizontalArrangement = Arrangement.SpaceEvenly) {
            HomeTabs.forEach { (key, label) ->
                val selected = tab == key
                Column(
                    Modifier.weight(1f).clickable { tab = key }.padding(vertical = 11.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(label, color = if (selected) HtmlGreen else Color(0xFF6B7280), fontSize = 14.sp, fontWeight = if (selected) FontWeight.SemiBold else FontWeight.Normal, maxLines = 1)
                    Spacer(Modifier.height(5.dp))
                    Box(Modifier.width(24.dp).height(2.dp).background(if (selected) HtmlGreen else Color.Transparent))
                }
            }
        }
        Box(Modifier.weight(1f).fillMaxWidth().background(Color.White)) {
            when (tab) {
                "copy" -> CopyHomePage(
                    vm = vm,
                    appId = appId,
                    onAppId = {
                        appId = it
                        account?.let { a -> vm.saveAccount(a.copy(appId = it)) }
                    },
                    coverUri = coverUri,
                    douyinBgUri = douyinBgUri,
                    onCover = { coverPicker.launch(arrayOf("image/*")) },
                    onBackground = { backgroundPicker.launch(arrayOf("image/*")) },
                    onRandom = { vm.rerollCopy() }
                )
                "type" -> TypeHomePage(vm)
                "upload" -> UploadHomePage(vm, uploadTab, { uploadTab = it }, clipboard)
                "preview" -> PreviewWebView(vm, Modifier.fillMaxSize().padding(horizontal = 0.dp))
                "cover" -> CoverHomePage(coverUri, douyinBgUri, { coverPicker.launch(arrayOf("image/*")) }, { backgroundPicker.launch(arrayOf("image/*")) })
            }
        }
        Row(Modifier.fillMaxWidth().height(54.dp).background(Color.White).border(width = 0.5.dp, color = Color(0xFFE5E7EB)), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(1f).fillMaxHeight().clickable { tab = "copy" }, contentAlignment = Alignment.Center) {
                Text("⌂  首页", color = HtmlGreen, fontSize = 13.sp, fontWeight = FontWeight.Medium)
            }
            Box(Modifier.weight(1f).fillMaxHeight().clickable { vm.screen = "my" }, contentAlignment = Alignment.Center) {
                Text("♙  我的", color = Color(0xFF9CA3AF), fontSize = 13.sp)
            }
        }
    }

    if (expandedInput) {
        Dialog(onDismissRequest = { expandedInput = false }, properties = DialogProperties(usePlatformDefaultWidth = false)) {
            Surface(Modifier.fillMaxSize(), color = Color.White, shape = RoundedCornerShape(0.dp)) {
                Column(Modifier.fillMaxSize().padding(20.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("输入文案", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, color = HtmlText, modifier = Modifier.weight(1f))
                        TextButton(onClick = { expandedInput = false }) { Text("收起") }
                    }
                    OutlinedTextField(
                        value = vm.manualInput,
                        onValueChange = vm::updateManualInput,
                        modifier = Modifier.fillMaxWidth().weight(1f),
                        placeholder = { Text("输入多条链接和摘录（建议两个换行符隔开）\n快手、抖音识别的文字输入，一键上传文案") },
                        minLines = 8
                    )
                    Button(
                        onClick = { vm.applyManualText(); expandedInput = false; tab = "preview" },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = HtmlGreen, contentColor = Color.White)
                    ) { Text("应用到预览") }
                }
            }
        }
    }
}

@Composable
private fun HeaderAndInput(input: String, onInput: (String) -> Unit, onExpand: () -> Unit) {
    Box(Modifier.fillMaxWidth().height(180.dp).background(HtmlGreen)) {
        Column(Modifier.fillMaxWidth().padding(top = 12.dp, start = 20.dp, end = 20.dp)) {
            Row(
                Modifier.fillMaxWidth().height(95.dp).clip(RoundedCornerShape(12.dp)).background(HtmlBlack).padding(horizontal = 16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text("拾万句®", color = Color.White, fontSize = 23.sp, fontWeight = FontWeight.Bold)
                    Text("名句摘录、朋友圈文案", color = Color(0xFFD1D5DB), fontSize = 12.sp)
                }
                Box(Modifier.size(66.dp).border(3.dp, Color.White, CircleShape), contentAlignment = Alignment.Center) {
                    Text("微", color = Color.White, fontSize = 31.sp, fontWeight = FontWeight.Bold)
                }
            }
        }
        Row(
            Modifier.align(Alignment.BottomCenter).padding(horizontal = 12.dp).fillMaxWidth().height(80.dp)
                .clip(RoundedCornerShape(12.dp)).background(Color.White).padding(start = 12.dp, end = 6.dp, top = 7.dp, bottom = 7.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextField(
                value = input,
                onValueChange = onInput,
                modifier = Modifier.weight(1f).fillMaxHeight(),
                placeholder = { Text("输入多条链接和摘录（建议两个换行符隔开）\n快手、抖音识别的文字输入 一键上传文案", fontSize = 11.sp, lineHeight = 15.sp) },
                textStyle = androidx.compose.ui.text.TextStyle(fontSize = 12.sp, color = Color(0xFF6B7280)),
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = Color.Transparent, unfocusedContainerColor = Color.Transparent,
                    focusedIndicatorColor = Color.Transparent, unfocusedIndicatorColor = Color.Transparent
                )
            )
            TextButton(onClick = onExpand) { Text("⤢", color = Color(0xFF9CA3AF), fontSize = 22.sp) }
        }
    }
}

@Composable
private fun CopyHomePage(
    vm: AppViewModel,
    appId: String,
    onAppId: (String) -> Unit,
    coverUri: String,
    douyinBgUri: String,
    onCover: () -> Unit,
    onBackground: () -> Unit,
    onRandom: () -> Unit
) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(
            Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(HtmlGreen).padding(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(Modifier.weight(1f)) {
                Text("拾万句", color = Color.Black, fontSize = 22.sp, fontWeight = FontWeight.Bold)
                Text("名句摘录、朋友圈文案", color = Color.Black, fontSize = 12.sp)
            }
            Button(onClick = onRandom, colors = ButtonDefaults.buttonColors(containerColor = HtmlBlack, contentColor = Color.White)) { Text("随机文案", fontSize = 12.sp) }
        }
        Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp)).background(Color(0xFFF9FAFB)).border(1.dp, Color(0xFFE5E7EB), RoundedCornerShape(10.dp)), verticalAlignment = Alignment.CenterVertically) {
            TextField(
                value = appId, onValueChange = onAppId, modifier = Modifier.weight(1f),
                placeholder = { Text("AppID") }, singleLine = true,
                colors = TextFieldDefaults.colors(focusedContainerColor = Color.Transparent, unfocusedContainerColor = Color.Transparent, focusedIndicatorColor = Color.Transparent, unfocusedIndicatorColor = Color.Transparent)
            )
            Text("获取APP_ID", color = Color(0xFF9CA3AF), fontSize = 10.sp, modifier = Modifier.padding(horizontal = 10.dp))
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            CategoryCard(Modifier.weight(1f), "▤", "名句摘录", "读书笔记、诗词佳句", vm.ui.textCat == "名句") { selectHomeCategory(vm, "名句") }
            CategoryCard(Modifier.weight(1f), "▣", "朋友圈文案", "朋友圈日常分享", vm.ui.textCat == "朋友圈") { selectHomeCategory(vm, "朋友圈") }
        }
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
            listOf(3, 6, 9).forEach { n ->
                SelectChip("${n}句", vm.ui.quantity == n) { vm.setQuantity(n) }
            }
            OutlinedTextField(
                value = vm.ui.quantity.toString(), onValueChange = { it.filter(Char::isDigit).take(2).toIntOrNull()?.let(vm::setQuantity) },
                modifier = Modifier.weight(1f).height(52.dp), singleLine = true, label = { Text("自定义句数", fontSize = 10.sp) }
            )
        }
        Text("选择版式", color = HtmlText, fontSize = 15.sp, fontWeight = FontWeight.SemiBold)
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            LayoutChoices.chunked(3).forEach { group ->
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    group.forEach { (key, label) ->
                        val selected = selectedLayoutKey(vm) == key
                        val supported = key != "douyin"
                        Box(
                            Modifier.weight(1f).clip(RoundedCornerShape(10.dp)).background(if (selected) Color(0xFFF0FDF4) else Color.White)
                                .border(if (selected) 2.dp else 1.dp, if (selected) HtmlGreen else Color(0xFFE5E7EB), RoundedCornerShape(10.dp))
                                .clickable(enabled = supported) {
                                    val item = vm.data.layout.firstOrNull { l -> layoutMatches(l.name, key) }
                                    if (item != null) vm.selectLayout(item.id) else vm.toast("当前没有对应的原生模板")
                                }.padding(vertical = 12.dp, horizontal = 4.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(label, color = if (supported) HtmlText else Color(0xFF9CA3AF), fontSize = 11.sp, textAlign = TextAlign.Center)
                        }
                    }
                    repeat(3 - group.size) { Spacer(Modifier.weight(1f)) }
                }
            }
        }
        Text("风格", color = HtmlText, fontSize = 14.sp, fontWeight = FontWeight.Medium)
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            listOf("拾万句", "句在川", "一日拾句", "小盆友").forEachIndexed { i, s ->
                Box(Modifier.clip(CircleShape).background(listOf(HtmlGreen, Color(0xFFF472B6), Color(0xFF3B82F6), Color.Black)[i]).padding(horizontal = 14.dp, vertical = 8.dp)) {
                    Text(s, color = Color.White, fontSize = 11.sp)
                }
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            OutlinedButton(onClick = onCover, modifier = Modifier.weight(1f)) { Text(if (coverUri.isEmpty()) "＋ 上传封面图" else "已选择封面", fontSize = 11.sp) }
            OutlinedButton(onClick = onBackground, modifier = Modifier.weight(1f)) { Text(if (douyinBgUri.isEmpty()) "＋ 抖音背景图" else "已选择背景图", fontSize = 11.sp) }
        }
        Text("选择文案模块", color = HtmlText, fontSize = 14.sp, fontWeight = FontWeight.Medium)
        val modules = vm.data.files.text.filter { it.category == vm.ui.textCat }
        if (modules.isEmpty()) Text("暂无文案模块，请到【我的】-文案中添加", color = Color(0xFF9CA3AF), fontSize = 11.sp)
        else Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            modules.forEach { module -> SelectChip(module.name, vm.ui.copyModuleId == module.id) { vm.selectCopyModule(module.id) } }
        }
        Text("已选择：${vm.data.files.text.firstOrNull { it.id == vm.ui.copyModuleId }?.name ?: "尚未选择文案模块"}", color = Color(0xFF9CA3AF), fontSize = 11.sp)
        TextButton(onClick = { vm.screen = "layout" }) { Text("打开高级排版编辑器", color = HtmlGreen) }
        Spacer(Modifier.height(10.dp))
    }
}

private fun selectHomeCategory(vm: AppViewModel, category: String) {
    vm.selectTextCat(category)
    vm.data.files.text.firstOrNull { it.category == category }?.let { vm.selectCopyModule(it.id) }
}

private fun selectedLayoutKey(vm: AppViewModel): String {
    val name = vm.data.layout.getOrNull(vm.layoutIndex)?.name.orEmpty()
    return when {
        name.contains("朋友圈") -> "moment"
        name.contains("文字断句") -> "breakline"
        name.contains("卡片") -> "card"
        name.contains("断章") || name.contains("序引") -> "purebg"
        else -> ""
    }
}

private fun layoutMatches(name: String, key: String): Boolean = when (key) {
    "moment" -> name.contains("朋友圈")
    "breakline" -> name.contains("文字断句")
    "card" -> name.contains("卡片")
    "purebg" -> name.contains("断章") || name.contains("序引")
    else -> false
}

@Composable
private fun CategoryCard(modifier: Modifier = Modifier, icon: String, title: String, desc: String, selected: Boolean, onClick: () -> Unit) {
    Column(
        modifier.clip(RoundedCornerShape(10.dp)).background(if (selected) Color(0xFFF0FDF4) else Color(0xFFF3F4F6))
            .border(1.dp, if (selected) HtmlGreen else Color(0xFFE5E7EB), RoundedCornerShape(10.dp)).clickable(onClick = onClick).padding(12.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(icon, color = Color(0xFF4B5563), fontSize = 19.sp)
            Spacer(Modifier.width(8.dp))
            Text(title, color = HtmlText, fontSize = 13.sp, fontWeight = FontWeight.Medium)
        }
        Text(desc, color = Color(0xFF9CA3AF), fontSize = 10.sp, modifier = Modifier.padding(top = 4.dp))
    }
}

@Composable
private fun TypeHomePage(vm: AppViewModel) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("内容类型", color = HtmlText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
        Text("HTML 原型只预留了类型页面入口，未定义更多类型字段；这里先提供与现有数据模型一致的两种文案分类。", color = Color(0xFF9CA3AF), fontSize = 12.sp)
        TEXT_CATEGORIES.forEach { cat ->
            CategoryCard(Modifier.fillMaxWidth(), "✦", cat, if (cat == "朋友圈") "朋友圈日常分享" else "读书笔记、诗词佳句", vm.ui.textCat == cat) { selectHomeCategory(vm, cat); vm.toast("已切换到$cat") }
        }
    }
}

@Composable
private fun UploadHomePage(vm: AppViewModel, subTab: String, onSubTab: (String) -> Unit, clipboard: androidx.compose.ui.platform.ClipboardManager) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Button(onClick = { vm.rerollCopy() }, modifier = Modifier.weight(1f), colors = ButtonDefaults.buttonColors(containerColor = HtmlGreen)) { Text("文案随机", color = Color.White) }
            OutlinedButton(onClick = { vm.applyManualText() }, modifier = Modifier.weight(1f)) { Text("文案一键同步") }
        }
        Button(
            onClick = {
                vm.applyManualText()
                onSubTab("code")
                vm.toast("HTML 已生成，可复制代码后粘贴到公众号编辑器；当前不执行公众号后台发布")
            },
            modifier = Modifier.fillMaxWidth().height(54.dp),
            colors = ButtonDefaults.buttonColors(containerColor = HtmlGreen, contentColor = Color.White)
        ) { Text("同步到公众号", fontSize = 16.sp) }
        var countText by remember(vm.ui.quantity) { mutableStateOf(vm.ui.quantity.toString()) }
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center) {
            Text("数量", color = Color(0xFF6B7280), fontSize = 12.sp)
            Spacer(Modifier.width(6.dp))
            OutlinedTextField(
                value = countText,
                onValueChange = { raw -> countText = raw.filter(Char::isDigit).take(2); countText.toIntOrNull()?.let(vm::setQuantity) },
                modifier = Modifier.width(72.dp).height(52.dp),
                singleLine = true
            )
            Spacer(Modifier.width(4.dp))
            Text("句", color = Color(0xFF6B7280), fontSize = 12.sp)
        }
        Row(Modifier.fillMaxWidth().border(width = 0.5.dp, color = Color(0xFFE5E7EB)), horizontalArrangement = Arrangement.SpaceEvenly) {
            listOf("code" to "生成HTML代码", "view" to "预览HTML").forEach { (k, label) ->
                TextButton(onClick = { onSubTab(k) }) {
                    Text(label, color = if (subTab == k) HtmlGreen else Color(0xFF6B7280), fontWeight = if (subTab == k) FontWeight.SemiBold else FontWeight.Normal)
                }
            }
        }
        if (subTab == "code") {
            OutlinedTextField(value = vm.previewHtml, onValueChange = {}, readOnly = true, modifier = Modifier.fillMaxWidth().height(260.dp), label = { Text("HTML 代码") })
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedButton(onClick = { clipboard.setText(AnnotatedString(vm.previewHtml)); vm.toast("已复制 HTML 代码") }) { Text("复制代码") }
                OutlinedButton(onClick = { clipboard.setText(AnnotatedString(vm.previewHtml)); vm.toast("已全选并复制 HTML 代码") }) { Text("全选复制") }
            }
        } else {
            OutlinedButton(onClick = { vm.js?.invoke("selectAllContent()") }) { Text("全选预览内容") }
            PreviewWebView(vm, Modifier.fillMaxWidth().height(420.dp))
        }
        Text("提示：当前实现生成可粘贴的 HTML，不会直接调用微信公众号发布接口。", color = Color(0xFF9CA3AF), fontSize = 11.sp)
    }
}

@Composable
private fun CoverHomePage(cover: String, background: String, onCover: () -> Unit, onBackground: () -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("封面与背景", color = HtmlText, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
        Text("选择本机图片用于封面或抖音背景。HTML 原型仅提供上传入口，尚未定义图片尺寸、裁剪和发布规则。", color = Color(0xFF9CA3AF), fontSize = 12.sp)
        ImagePickerCard("公众号封面图", cover, onCover)
        ImagePickerCard("抖音背景图", background, onBackground)
    }
}

@Composable
private fun ImagePickerCard(title: String, uri: String, onPick: () -> Unit) {
    Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(Color(0xFFF9FAFB)).padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, color = HtmlText, fontSize = 14.sp, fontWeight = FontWeight.Medium)
        if (uri.isNotEmpty()) AsyncImage(uri, null, Modifier.fillMaxWidth().height(170.dp).clip(RoundedCornerShape(8.dp)), contentScale = ContentScale.Fit)
        else Box(Modifier.fillMaxWidth().height(120.dp).background(Color(0xFFE5E7EB), RoundedCornerShape(8.dp)), contentAlignment = Alignment.Center) { Text("尚未选择图片", color = Color(0xFF9CA3AF), fontSize = 12.sp) }
        OutlinedButton(onClick = onPick) { Text(if (uri.isEmpty()) "选择图片" else "更换图片") }
    }
}

@Composable
private fun SelectChip(text: String, selected: Boolean, onClick: () -> Unit) {
    Box(Modifier.clip(RoundedCornerShape(8.dp)).background(if (selected) HtmlGreen else Color(0xFFF9FAFB))
        .border(1.dp, if (selected) HtmlGreen else Color(0xFFE5E7EB), RoundedCornerShape(8.dp)).clickable(onClick = onClick).padding(horizontal = 14.dp, vertical = 9.dp)) {
        Text(text, color = if (selected) Color.White else Color(0xFF6B7280), fontSize = 12.sp)
    }
}
