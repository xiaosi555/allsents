#!/usr/bin/env python3
from pathlib import Path
import re
import shutil

root = Path(".")
base = root / "source/ShiWanJu-Android/app/src/main"
java = base / "java/com/shiwanju/app"

# Copy a theme-only settings screen. This phase deliberately excludes icon selection.
shutil.copy2(
    root / "native-overlay/app/src/main/java/com/shiwanju/app/ui/ThemeSettings.kt",
    java / "ui/ThemeSettings.kt"
)

# AppColors is Compose state so every existing AppColors.Theme reference updates live.
theme_path = java / "ui/Theme.kt"
theme = theme_path.read_text(encoding="utf-8")
if "import androidx.compose.runtime.getValue" not in theme:
    theme = theme.replace(
        "import androidx.compose.runtime.Composable",
        "import androidx.compose.runtime.Composable\nimport androidx.compose.runtime.getValue\nimport androidx.compose.runtime.mutableStateOf\nimport androidx.compose.runtime.setValue",
        1
    )
old_colors = """    val Theme = Color(0xFFCCFF00)
    val OnTheme = Color(0xFF000000)"""
new_colors = """    private var themeState by mutableStateOf(Color(0xFF01CC7A))
    private var onThemeState by mutableStateOf(Color(0xFFFFFFFF))
    val Theme: Color get() = themeState
    val OnTheme: Color get() = onThemeState

    private var darkAppearance by mutableStateOf(false)
    fun setAppearanceMode(mode: String, systemDark: Boolean) {
        darkAppearance = when (mode) {
            "dark" -> true
            "light" -> false
            else -> systemDark
        }
    }

    /** 与 000_拾万句.html 的 --theme / --theme-on 亮度规则保持一致。 */
    fun setThemeColor(hex: String) {
        if (!Regex("^#[0-9A-Fa-f]{6}$").matches(hex)) return
        val parsed = android.graphics.Color.parseColor(hex)
        val r = android.graphics.Color.red(parsed)
        val g = android.graphics.Color.green(parsed)
        val b = android.graphics.Color.blue(parsed)
        val luminance = .299 * r + .587 * g + .114 * b
        themeState = Color(parsed)
        onThemeState = if (luminance > 150) Color.Black else Color.White
    }"""
if old_colors not in theme:
    raise SystemExit("Required theme patch anchor missing (AppColors constants): Theme.kt")
theme = theme.replace(old_colors, new_colors, 1)
theme_path.write_text(theme, encoding="utf-8")

# Persist only this UI preference in SharedPreferences; business JSON remains untouched.
store_path = java / "data/Store.kt"
store = store_path.read_text(encoding="utf-8")
store_anchor = "    var appearanceMode: String
        get() = prefs.getString("appearance_mode", "system") ?: "system"
        set(value) { if (value in listOf("system", "light", "dark")) prefs.edit().putString("appearance_mode", value).apply() }

    // ---- 界面状态 ----"
store_insert = """    // ---- 外观偏好：主题颜色（不写入业务数据文件） ----
    var themeColor: String
        get() = prefs.getString("theme_color", "#01CC7A") ?: "#01CC7A"
        set(value) {
            if (Regex("^#[0-9A-Fa-f]{6}$").matches(value)) {
                prefs.edit().putString("theme_color", value.uppercase()).apply()
            }
        }

"""
if "var themeColor: String" not in store:
    if store_anchor not in store:
        raise SystemExit("Required theme patch anchor missing (Store UI state section): Store.kt")
    store = store.replace(store_anchor, store_insert + store_anchor, 1)
    store_path.write_text(store, encoding="utf-8")

# Expose preference to Compose and apply it before the first screen is drawn.
vm_path = java / "ui/AppViewModel.kt"
vm = vm_path.read_text(encoding="utf-8")
vm_anchor = "    var textViewMode by mutableStateOf(store.textViewMode); private set\n"
vm_insert = "    var themeColor by mutableStateOf(store.themeColor); private set\n"
if "var themeColor by mutableStateOf(store.themeColor)" not in vm:
    if vm_anchor not in vm:
        raise SystemExit("Required theme patch anchor missing (ViewModel preference state): AppViewModel.kt")
    vm = vm.replace(vm_anchor, vm_anchor + vm_insert, 1)
if "AppColors.setThemeColor(themeColor)" not in vm:
    init_match = re.search(r"(?m)^    init \{\s*$", vm)
    if not init_match:
        raise SystemExit("Required theme patch anchor missing (ViewModel init declaration): AppViewModel.kt")
    insert_at = init_match.end()
    vm = vm[:insert_at] + "\n        if (themeColor.equals(\"#CCFF00\", ignoreCase = true)) {\n            store.themeColor = \"#01CC7A\"\n            themeColor = \"#01CC7A\"\n        }\n        AppColors.setThemeColor(themeColor)
        AppColors.setAppearanceMode(appearanceMode, false)" + vm[insert_at:]
if "fun selectThemeColor(hex: String)" not in vm:
    base_anchor = "    // ------------------------------------------------------------------ 基础\n"
    if base_anchor not in vm:
        raise SystemExit("Required theme patch anchor missing (ViewModel base section): AppViewModel.kt")
    select_method = """    fun selectAppearanceMode(mode: String, systemDark: Boolean) {
        if (mode !in listOf("system", "light", "dark")) return
        store.appearanceMode = mode
        appearanceMode = mode
        AppColors.setAppearanceMode(mode, systemDark)
    }

    fun selectThemeColor(hex: String) {
        if (!Regex("^#[0-9A-Fa-f]{6}$").matches(hex)) return
        val normalized = hex.uppercase()
        store.themeColor = normalized
        themeColor = normalized
        AppColors.setThemeColor(normalized)
    }

"""
    vm = vm.replace(base_anchor, select_method + base_anchor, 1)
vm_path.write_text(vm, encoding="utf-8")

# Add Settings above Accounts and route to a theme-only page.
my_path = java / "ui/MyScreens.kt"
my = my_path.read_text(encoding="utf-8")
old_title = 'val title = when (route) { "accounts" -> "账号"; "texts" -> "文案"; "layouts" -> "版式"; "more" -> "更多"; "backup" -> "备份"; "official" -> "公众号"; "history_articles" -> "历史文章"; else -> "我的" }'
new_title = 'val title = when (route) { "settings" -> "设置"; "accounts" -> "账号"; "texts" -> "文案"; "layouts" -> "版式"; "more" -> "更多"; "backup" -> "备份"; "official" -> "公众号"; "history_articles" -> "历史文章"; else -> "我的" }'
if '"settings" -> ThemeSettingsPage(vm)' not in my:
    if old_title not in my:
        raise SystemExit("Required theme patch anchor missing (My page title): MyScreens.kt")
    my = my.replace(old_title, new_title, 1)
    branch_anchor = '                "accounts" -> AccountsPage(vm)'
    if branch_anchor not in my:
        raise SystemExit("Required theme patch anchor missing (My page route): MyScreens.kt")
    my = my.replace(branch_anchor, '                "settings" -> ThemeSettingsPage(vm)\n' + branch_anchor, 1)
    home_start = my.find("private fun HomePage")
    home_end = my.find("// ---------------------------------------------------------------------- 账号", home_start)
    if home_start < 0 or home_end < 0:
        raise SystemExit("Required theme patch anchor missing (HomePage section): MyScreens.kt")
    home = my[home_start:home_end]
    if 'ListRow("设置"' not in home:
        home_anchor = "    val d = vm.data\n"
        if home_anchor not in home:
            raise SystemExit("Required theme patch anchor missing (HomePage data row): MyScreens.kt")
        home = home.replace(home_anchor, home_anchor + '    ListRow("设置", "主题颜色") { go("settings") }\n', 1)
        my = my[:home_start] + home + my[home_end:]
    my_path.write_text(my, encoding="utf-8")

# Fail fast if the theme-only phase is incomplete or icon selection leaked into this stage.
settings = (java / "ui/ThemeSettings.kt").read_text(encoding="utf-8")
my = my_path.read_text(encoding="utf-8")
vm = vm_path.read_text(encoding="utf-8")
if settings.count('ThemeOption("') != 10:
    raise SystemExit("Theme settings must contain exactly 10 options")
if "IconChoice" in settings or "APPEARANCE_ICONS" in settings:
    raise SystemExit("Icon selection must remain in phase 2")
for token in ["fun setThemeColor(hex: String)", "val Theme: Color get()", "val OnTheme: Color get()"]:
    if token not in theme_path.read_text(encoding="utf-8"):
        raise SystemExit("Theme state check failed: " + token)
if "theme_color" not in store_path.read_text(encoding="utf-8"):
    raise SystemExit("Theme preference persistence check failed")
if "fun selectThemeColor(hex: String)" not in vm or "AppColors.setThemeColor(themeColor)" not in vm:
    raise SystemExit("Theme ViewModel wiring check failed")
if 'ListRow("设置", "主题颜色")' not in my or '"settings" -> ThemeSettingsPage(vm)' not in my:
    raise SystemExit("Settings entry or route check failed")
print("Phase 1 theme color checks passed: 9 colors, persistence, live Compose state, settings route; icon feature excluded.")
