#!/usr/bin/env python3
from pathlib import Path
import re, shutil

root=Path(".")
base=root/"source/ShiWanJu-Android/app/src/main"
java=base/"java/com/shiwanju/app"
shutil.copy2(root/"native-overlay/app/src/main/java/com/shiwanju/app/ui/IconSettings.kt", java/"ui/IconSettings.kt")

# Persist the selected icon style independently from business backup data.
store_path=java/"data/Store.kt"
s=store_path.read_text(encoding="utf-8")
if "var iconStyle: String" not in s:
    anchor='    // ---- 界面状态 ----'
    if anchor not in s: raise SystemExit("Store icon preference anchor missing")
    s=s.replace(anchor,'''    // ---- 外观偏好：桌面图标风格 ----
    var iconStyle: String
        get() = prefs.getString("icon_style", "original") ?: "original"
        set(value) {
            if (value in ICON_STYLE_IDS) prefs.edit().putString("icon_style", value).apply()
        }

'''+anchor,1)
    s=s.replace('class Store(private val ctx: Context) {','class Store(private val ctx: Context) {\n    companion object { val ICON_STYLE_IDS = setOf("original","cowboy","code","line","plush","sky","space","graffiti","playful","8bit","sketch") }',1)
store_path.write_text(s,encoding="utf-8")

vm_path=java/"ui/AppViewModel.kt"
s=vm_path.read_text(encoding="utf-8")
if "var iconStyle by mutableStateOf(store.iconStyle)" not in s:
    s=s.replace('    var themeColor by mutableStateOf(store.themeColor); private set','    var themeColor by mutableStateOf(store.themeColor); private set\n    var iconStyle by mutableStateOf(store.iconStyle); private set',1)
if "fun selectIconStyle(style: String)" not in s:
    anchor='    // ------------------------------------------------------------------ 基础'
    method='''    fun selectIconStyle(style: String) {
        if (style !in com.shiwanju.app.data.Store.ICON_STYLE_IDS) return
        val app = getApplication<android.app.Application>()
        val pm = app.packageManager
        val names = com.shiwanju.app.data.Store.ICON_STYLE_IDS
        val target = "com.shiwanju.app.Launcher" + style.replaceFirstChar { it.uppercase() }
        runCatching {
            names.forEach { id ->
                val cls = "com.shiwanju.app.Launcher" + id.replaceFirstChar { it.uppercase() }
                pm.setComponentEnabledSetting(
                    android.content.ComponentName(app, cls),
                    if (cls == target) android.content.pm.PackageManager.COMPONENT_ENABLED_STATE_ENABLED
                    else android.content.pm.PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                    android.content.pm.PackageManager.DONT_KILL_APP
                )
            }
        }.onFailure { toast("图标切换失败：请重新打开应用后重试") }
        store.iconStyle = style
        iconStyle = style
        toast("已切换桌面图标")
    }

'''
    if anchor not in s: raise SystemExit("ViewModel icon method anchor missing")
    s=s.replace(anchor,method+anchor,1)
vm_path.write_text(s,encoding="utf-8")

my_path=java/"ui/MyScreens.kt"
s=my_path.read_text(encoding="utf-8")
s=s.replace('"settings" -> "设置"; "accounts"','"settings" -> "设置"; "icons" -> "图标风格"; "accounts"',1)
if '"icons" -> IconSettingsPage(vm)' not in s:
    s=s.replace('                "settings" -> ThemeSettingsPage(vm)','                "settings" -> ThemeSettingsPage(vm)\n                "icons" -> IconSettingsPage(vm)',1)
s=s.replace('ListRow("设置", "主题颜色") { go("settings") }','ListRow("设置", "主题颜色") { go("settings") }\n    ListRow("图标风格", "11 种桌面图标") { go("icons") }',1)
my_path.write_text(s,encoding="utf-8")

# The activity itself is no longer the launcher; one alias per style allows live icon switching.
manifest=base/"AndroidManifest.xml"
m=manifest.read_text(encoding="utf-8")
m=re.sub(r'\s*<intent-filter>\s*<action android:name="android.intent.action.MAIN"\s*/>\s*<category android:name="android.intent.category.LAUNCHER"\s*/>\s*</intent-filter>','',m,count=1)
if 'android:name=".LauncherOriginal"' not in m:
    aliases=[]
    ids=["original","cowboy","code","line","plush","sky","space","graffiti","playful","8bit","sketch"]
    for id in ids:
        cap=id[0].upper()+id[1:]
        aliases.append(f'''        <activity-alias
            android:name=".Launcher{cap}"
            android:targetActivity=".MainActivity"
            android:enabled="{'true' if id=='original' else 'false'}"
            android:exported="true"
            android:icon="@drawable/icon_style_{id}"
            android:label="@string/app_name">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity-alias>''')
    m=m.replace('    </application>',"\n".join(aliases)+"\n    </application>",1)
manifest.write_text(m,encoding="utf-8")
print("Phase 2 icon settings, persistence, and 11 launcher aliases patched.")
