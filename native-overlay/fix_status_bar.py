from pathlib import Path

p = Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/MainActivity.kt")
s = p.read_text(encoding="utf-8")

if "import androidx.compose.runtime.SideEffect" not in s:
    s = s.replace("import androidx.compose.runtime.LaunchedEffect\n", "import androidx.compose.runtime.LaunchedEffect\nimport androidx.compose.runtime.SideEffect\n")
if "import androidx.core.view.WindowCompat" not in s:
    s = s.replace("import androidx.activity.viewModels\n", "import androidx.activity.viewModels\nimport androidx.core.view.WindowCompat\n")
if "import com.shiwanju.app.ui.AppColors" not in s:
    s = s.replace("import com.shiwanju.app.ui.AppViewModel\n", "import com.shiwanju.app.ui.AppViewModel\nimport com.shiwanju.app.ui.AppColors\n")

anchor = '''            ShiWanJuTheme(dark = vm.screen == "layout") {
                if (showSplash.value) {'''
replacement = '''            ShiWanJuTheme(dark = vm.screen == "layout") {
                // Edge-to-edge status bar icons must contrast with the active page surface.
                SideEffect {
                    WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars =
                        !AppColors.IsDark
                }
                if (showSplash.value) {'''
if anchor not in s:
    raise SystemExit("MainActivity theme/status-bar insertion anchor not found")
s = s.replace(anchor, replacement, 1)
p.write_text(s, encoding="utf-8")
print("Status-bar icon contrast now follows the active app theme.")
