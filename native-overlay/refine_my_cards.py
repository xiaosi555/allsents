from pathlib import Path
import re
p=Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/MyScreens.kt")
s=p.read_text(encoding="utf-8")
s=s.replace('.shadow(1.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp))','.clip(RoundedCornerShape(12.dp))')
s=s.replace('import androidx.compose.ui.draw.shadow\n','')
s=s.replace('vm.data.history.forEach { h ->','vm.data.history.filterNot { it.id == "1791721426948" || it.id == "1791721454725" }.forEach { h ->')
s=re.sub(r'(?m)^(\s*)ListRow\(h\.name\.ifEmpty.*\n',r'\1ListRow(h.name.ifEmpty { h.title.ifEmpty { "未命名往期" } }, count.toString() + " 条内容 · 文字版") { editKey = h.id }\n',s)
s=s.replace('Field("图片地址（每行一个）", images, { images = it }, 3, "留空则使用文字版往期")','')
p.write_text(s,encoding="utf-8")
print("My page card and text-history UI refinements complete")