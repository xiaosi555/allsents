from pathlib import Path
import re
base=Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui")
p=base/"ThemeSettings.kt";s=p.read_text(encoding="utf-8")
s,n=re.subn(r'Column\(Modifier\.fillMaxWidth\(\)\.clip\(RoundedCornerShape\(18\.dp\)\)\.background\(AppColors\.MyCard\)\.padding\(16\.dp\), verticalArrangement = Arrangement\.spacedBy\(15\.dp\)\) \{','Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(15.dp)) {',s,count=1)
if n!=1: print("WARNING: theme color outer card anchor not found")
p.write_text(s,encoding="utf-8")
p=base/"IconSettings.kt";s=p.read_text(encoding="utf-8")
s="\n".join(line for line in s.split("\n") if 'Text("图标风格"' not in line and 'Text("选择后会切换手机桌面图标' not in line)
p.write_text(s,encoding="utf-8")
print("Settings refinements complete")