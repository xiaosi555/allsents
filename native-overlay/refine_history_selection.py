from pathlib import Path
p=Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/AppViewModel.kt")
s=p.read_text(encoding="utf-8")
s=s.replace('val hids = u.historyIds.filter { id -> data.history.any { it.id == id } }','val hids = u.historyIds.filter { id -> id != "1791721426948" && id != "1791721454725" && data.history.any { it.id == id } }')
s=s.replace('if (data.history.isEmpty()) return toast("暂无往期条目，请到【我的】-更多-往期中添加")','if (data.history.none { it.id != "1791721426948" && it.id != "1791721454725" }) return toast("暂无文字版往期条目，请到【我的】-更多-往期中添加")')
s=s.replace('''val item = data.history.firstOrNull { it.id == id }
            ?: data.history.firstOrNull { it.id == selectedId }
            ?: data.history.first()''','''val available = data.history.filterNot { it.id == "1791721426948" || it.id == "1791721454725" }
        val item = available.firstOrNull { it.id == id }
            ?: available.firstOrNull { it.id == selectedId }
            ?: available.first()''')
p.write_text(s,encoding="utf-8")
print("Text-only history selection validation complete")