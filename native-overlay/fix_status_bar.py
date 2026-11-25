from pathlib import Path
import re

p = Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/MainActivity.kt")
s = p.read_text(encoding="utf-8")

if "import androidx.compose.runtime.SideEffect" not in s:
    s = s.replace("import androidx.compose.runtime.LaunchedEffect\n", "import androidx.compose.runtime.LaunchedEffect\nimport androidx.compose.runtime.SideEffect\n")
if "import androidx.core.view.WindowCompat" not in s:
    s = s.replace("import androidx.activity.viewModels\n", "import androidx.activity.viewModels\nimport androidx.core.view.WindowCompat\n")
if "import com.shiwanju.app.ui.AppColors" not in s:
    s = s.replace("import com.shiwanju.app.ui.AppViewModel\n", "import com.shiwanju.app.ui.AppViewModel\nimport com.shiwanju.app.ui.AppColors\n")

# Keep Android's system-bar insets outside the Compose content on every route.
# This is intentionally a single Activity-level policy: pages must not each add
# another top inset, which would create inconsistent/doubled title-bar spacing.
if "WindowCompat.setDecorFitsSystemWindows(window, true)" not in s:
    on_create = re.search(r"(?m)^(\s*)override fun onCreate\([^\n]*\)\s*\{", s)
    if not on_create:
        raise SystemExit("MainActivity onCreate anchor not found")
    indent = on_create.group(1) + "    "
    pos = on_create.end()
    s = s[:pos] + "\n" + indent + "// Apply status/navigation safe insets consistently to every page.\n" + indent + "WindowCompat.setDecorFitsSystemWindows(window, true)" + s[pos:]

# Keep status-bar icon contrast synchronized with the active theme.
anchor = '            ShiWanJuTheme(dark = vm.screen == "layout") {'
replacement = anchor + """
                SideEffect {
                    WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars =
                        !AppColors.IsDark
                }"""
if "isAppearanceLightStatusBars" not in s:
    if anchor not in s:
        raise SystemExit("MainActivity theme anchor not found")
    s = s.replace(anchor, replacement, 1)

p.write_text(s, encoding="utf-8")
print("Global status/navigation safe-area policy and status-bar icon contrast applied.")
