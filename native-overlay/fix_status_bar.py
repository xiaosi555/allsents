from pathlib import Path
import re

p = Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/MainActivity.kt")
s = p.read_text(encoding="utf-8")

# Use AndroidX edge-to-edge consistently. Do not override its decor-fitting
# policy with setDecorFitsSystemWindows(true); Compose routes reserve insets.
s = re.sub(r"(?m)^\s*WindowCompat\.setDecorFitsSystemWindows\(window,\s*(?:true|false)\)\s*\n?", "", s)

if "import androidx.compose.runtime.SideEffect" not in s:
    anchor = "import androidx.compose.runtime.LaunchedEffect\n"
    if anchor not in s: raise SystemExit("Missing Compose SideEffect import anchor")
    s = s.replace(anchor, anchor + "import androidx.compose.runtime.SideEffect\n", 1)
if "import androidx.core.view.WindowCompat" not in s:
    anchor = "import androidx.activity.enableEdgeToEdge\n"
    if anchor not in s: raise SystemExit("Missing WindowCompat import anchor")
    s = s.replace(anchor, anchor + "import androidx.core.view.WindowCompat\n", 1)
if "import com.shiwanju.app.ui.AppColors" not in s:
    anchor = "import com.shiwanju.app.ui.AppViewModel\n"
    if anchor not in s: raise SystemExit("Missing AppColors import anchor")
    s = s.replace(anchor, anchor + "import com.shiwanju.app.ui.AppColors\n", 1)

anchor = '            ShiWanJuTheme(dark = vm.screen == "layout") {'
if "isAppearanceLightStatusBars" not in s:
    if anchor not in s: raise SystemExit("Missing theme anchor for status bar contrast")
    s = s.replace(anchor, anchor + """
                SideEffect {
                    WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars =
                        !AppColors.IsDark
                }""", 1)

if "enableEdgeToEdge()" not in s:
    raise SystemExit("Edge-to-edge setup is missing")
if "WindowCompat.setDecorFitsSystemWindows(window, true)" in s:
    raise SystemExit("Conflicting decorFitsSystemWindows(true) remains")
p.write_text(s, encoding="utf-8")
final = p.read_text(encoding="utf-8")
if "isAppearanceLightStatusBars" not in final or "SideEffect {" not in final:
    raise SystemExit("Final MainActivity is missing theme-aware status-bar icon contrast.")
if "WindowCompat.setDecorFitsSystemWindows(window, true)" in final:
    raise SystemExit("Conflicting decorFitsSystemWindows(true) remains in final MainActivity.")
print("Verified final MainActivity: edge-to-edge enabled and status-bar icon contrast follows active theme.")
