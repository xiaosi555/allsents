from pathlib import Path
import re

p = Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/MainActivity.kt")
s = p.read_text(encoding="utf-8")

for old, new in [
    ("import androidx.compose.runtime.LaunchedEffect\n", "import androidx.compose.runtime.LaunchedEffect\nimport androidx.compose.runtime.SideEffect\n"),
    ("import androidx.activity.viewModels\n", "import androidx.activity.viewModels\nimport androidx.core.view.WindowCompat\n"),
    ("import com.shiwanju.app.ui.AppViewModel\n", "import com.shiwanju.app.ui.AppViewModel\nimport com.shiwanju.app.ui.AppColors\n"),
]:
    if new.splitlines()[-1] not in s:
        if old not in s: raise SystemExit("Missing import anchor: " + old.strip())
        s = s.replace(old, new, 1)

# enableEdgeToEdge() changes decor fitting to false. Apply the single global
# safe-area policy AFTER it, otherwise edge-to-edge silently overrides the policy.
s = re.sub(r"(?m)^\s*WindowCompat\.setDecorFitsSystemWindows\(window, true\)\s*\n?", "", s)
edge = re.search(r"(?m)^(\s*)enableEdgeToEdge\(\)\s*$", s)
if edge:
    indent = edge.group(1)
    insert = indent + "WindowCompat.setDecorFitsSystemWindows(window, true)\n"
    s = s[:edge.end()] + "\n" + insert + s[edge.end():]
else:
    anchor = re.search(r"(?m)^(\s*)super\.onCreate\(savedInstanceState\)\s*$", s)
    if not anchor: raise SystemExit("MainActivity safe-area insertion anchor not found")
    indent = anchor.group(1)
    s = s[:anchor.end()] + "\n" + indent + "WindowCompat.setDecorFitsSystemWindows(window, true)" + s[anchor.end():]

anchor = '            ShiWanJuTheme(dark = vm.screen == "layout") {'
replacement = anchor + """
                SideEffect {
                    WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars =
                        !AppColors.IsDark
                }"""
if "isAppearanceLightStatusBars" not in s:
    if anchor not in s: raise SystemExit("MainActivity theme anchor not found")
    s = s.replace(anchor, replacement, 1)

if s.count("WindowCompat.setDecorFitsSystemWindows(window, true)") != 1:
    raise SystemExit("Expected exactly one global decor-fitting policy")
if edge and s.index("WindowCompat.setDecorFitsSystemWindows(window, true)") < s.index("enableEdgeToEdge()"):
    raise SystemExit("Safe-area policy must follow enableEdgeToEdge()")
p.write_text(s, encoding="utf-8")
print("Global safe-area policy applied after enableEdgeToEdge; status-bar icon contrast follows theme.")
