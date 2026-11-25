from pathlib import Path

ROOT = Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app")
def edit(relative, old, new, expected=1):
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"Required page source missing: {path}")
    source = path.read_text(encoding="utf-8")
    count = source.count(old)
    if count != expected:
        raise SystemExit(f"{relative}: expected {expected} anchor(s), found {count}: {old}")
    path.write_text(source.replace(old, new, expected), encoding="utf-8")

# Keep edge-to-edge enabled. Each full-screen route owns exactly one root inset.
# Do not combine decorFitsSystemWindows(true) with Compose inset modifiers.
activity = ROOT / "MainActivity.kt"
a = activity.read_text(encoding="utf-8")
if "WindowCompat.setDecorFitsSystemWindows(window, true)" in a:
    a = a.replace("WindowCompat.setDecorFitsSystemWindows(window, true)", "")
    activity.write_text(a, encoding="utf-8")

# Existing full-screen roots already use systemBarsPadding; the two legacy
# subpages only reserved the status bar and therefore let bottom controls
# overlap gesture navigation.
edit("ui/HistoryArticlesPage.kt",
     ".background(Color(0xFFF6F6F6)).statusBarsPadding()) {",
     ".background(Color(0xFFF6F6F6)).systemBarsPadding()) {")
edit("ui/OfficialAccountPage.kt",
     ".background(Color(0xFFF0F0F0)).statusBarsPadding()) {",
     ".background(Color(0xFFF0F0F0)).systemBarsPadding()) {")

# Independent Xiumi editor was the only primary full-screen editor without a
# root inset. Add it once; leave its internal canvas/toolbar spacing untouched.
edit("ui/XiumiArticleLayoutScreen.kt",
     "Column(Modifier.fillMaxSize().background(Color(0xFFF2F3F4))) {",
     "Column(Modifier.fillMaxSize().background(Color(0xFFF2F3F4)).systemBarsPadding()) {")

# Verify the five main routes have one root system-bars inset.
checks = {
    "ui/LayoutScreen.kt": ".background(AppColors.Bg).systemBarsPadding().imePadding()",
    "ui/MyScreens.kt": ".background(AppColors.MyBg).systemBarsPadding()",
    "ui/HistoryArticlesPage.kt": ".background(Color(0xFFF6F6F6)).systemBarsPadding()",
    "ui/OfficialAccountPage.kt": ".background(Color(0xFFF0F0F0)).systemBarsPadding()",
    "ui/ArticleEditorScreen.kt": ".background(pageBg).systemBarsPadding()",
    "ui/XiumiArticleLayoutScreen.kt": ".background(Color(0xFFF2F3F4)).systemBarsPadding()",
}
for relative, marker in checks.items():
    if marker not in (ROOT / relative).read_text(encoding="utf-8"):
        raise SystemExit(f"Root system-bar inset verification failed: {relative}")

print("Verified one root systemBarsPadding for home/layout, My, History, Official Account, original editor and Xiumi editor.")
