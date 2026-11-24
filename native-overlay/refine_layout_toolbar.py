from pathlib import Path
import re
p=Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/LayoutScreen.kt")
s=p.read_text(encoding="utf-8")
if "import androidx.compose.foundation.Image\n" not in s:
 s=s.replace("import androidx.compose.foundation.BorderStroke\n","import androidx.compose.foundation.BorderStroke\nimport androidx.compose.foundation.Image\n")
if "import androidx.compose.ui.res.painterResource\n" not in s:
 s=s.replace("import androidx.compose.ui.platform.LocalDensity\n","import androidx.compose.ui.platform.LocalDensity\nimport androidx.compose.ui.res.painterResource\n")
if "import com.shiwanju.app.R\n" not in s:
 s=s.replace("import com.shiwanju.app.data.LayoutItem\n","import com.shiwanju.app.R\nimport com.shiwanju.app.data.LayoutItem\n")
toolbar='''@Composable
private fun TopBar(vm: AppViewModel) {
    Row(Modifier.fillMaxWidth().height(56.dp).padding(horizontal = 14.dp), verticalAlignment = Alignment.CenterVertically) {
        Image(painter = painterResource(R.drawable.app_logo), contentDescription = "拾万句", contentScale = ContentScale.Fit, modifier = Modifier.size(width = 28.dp, height = 27.dp))
        Spacer(Modifier.weight(1f))
        Text(vm.charCount.toString() + "字", color = AppColors.TextDim, fontSize = 12.sp)
        Spacer(Modifier.width(10.dp))
        ThemeChip(if (vm.editing) "完成" else "编辑", vm.editing) { vm.toggleEditing() }
        IconButton(onClick = { vm.screen = "article_editor" }, modifier = Modifier.size(38.dp)) {
            Icon(Icons.Outlined.Article, contentDescription = "文章编辑器", tint = AppColors.TextMain, modifier = Modifier.size(21.dp))
        }
    }
}'''
s,n=re.subn(r'@Composable\nprivate fun TopBar\(vm: AppViewModel\) \{.*?\n\}',lambda m:toolbar,s,count=1,flags=re.S)
if n!=1: raise SystemExit("Layout TopBar anchor not found")
old='''    var showFolderName by remember { mutableStateOf(true) }
    LaunchedEffect(listState) {
        snapshotFlow { listState.isScrollInProgress to listState.lastScrolledForward }.collect { (scrolling, forward) ->
            if (scrolling) showFolderName = !forward
        }
    }'''
new='''    var showFolderName by remember { mutableStateOf(true) }
    val density = androidx.compose.ui.platform.LocalDensity.current
    LaunchedEffect(listState) {
        val stepPx = with(density) { 72.dp.toPx() }
        val thresholdPx = with(density) { 52.dp.toPx() }
        var previousPosition = 0f
        var direction = 0
        var accumulated = 0f
        var initialized = false
        snapshotFlow { listState.firstVisibleItemIndex to listState.firstVisibleItemScrollOffset }.collect { (index, offset) ->
            val position = index * stepPx + offset
            if (!initialized) { previousPosition = position; initialized = true } else {
                val delta = position - previousPosition
                previousPosition = position
                if (kotlin.math.abs(delta) > 0.5f) {
                    val nextDirection = if (delta > 0f) 1 else -1
                    if (nextDirection != direction) { direction = nextDirection; accumulated = 0f }
                    accumulated += kotlin.math.abs(delta)
                    if (accumulated >= thresholdPx) { showFolderName = direction > 0; accumulated = 0f }
                }
            }
        }
    }'''
if old not in s: raise SystemExit("ImagePanel scroll threshold anchor not found")
s=s.replace(old,new,1)
s=s.replace('vm.data.history.forEach { h -> GridCard','vm.data.history.filterNot { it.id == "1791721426948" || it.id == "1791721454725" }.forEach { h -> GridCard')
p.write_text(s,encoding="utf-8")
print("Layout toolbar, scroll threshold and text-history selector complete")