from pathlib import Path

ROOT = Path("source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app")
targets = {
    "ui/LayoutScreen.kt": [
        (".background(AppColors.Bg).systemBarsPadding().imePadding()", ".background(AppColors.Bg).imePadding()", 1),
    ],
    "ui/MyScreens.kt": [
        (".background(AppColors.MyBg).systemBarsPadding()) {", ".background(AppColors.MyBg)) {", 1),
    ],
    "ui/HistoryArticlesPage.kt": [
        (".background(AppColors.MyBg).statusBarsPadding()) {", ".background(AppColors.MyBg)) {", 1),
    ],
    "ui/OfficialAccountPage.kt": [
        (".background(AppColors.MyBg).statusBarsPadding()) {", ".background(AppColors.MyBg)) {", 1),
    ],
    "ui/ArticleEditorScreen.kt": [
        (".background(pageBg).systemBarsPadding()) {", ".background(pageBg)) {", 1),
    ],
}

for relative, replacements in targets.items():
    path = ROOT / relative
    if not path.is_file():
        raise SystemExit(f"Required page source missing: {path}")
    source = path.read_text(encoding="utf-8")
    for old, new, expected in replacements:
        count = source.count(old)
        if count != expected:
            raise SystemExit(f"{relative}: expected {expected} root safe-area anchor(s), found {count}: {old}")
        source = source.replace(old, new, expected)
    path.write_text(source, encoding="utf-8")

# Verify no primary screen root still adds a second system-bar inset.
checks = {
    "ui/LayoutScreen.kt": "Column(Modifier.fillMaxSize().background(AppColors.Bg).imePadding())",
    "ui/MyScreens.kt": "Column(Modifier.fillMaxSize().background(AppColors.MyBg)) {",
    "ui/HistoryArticlesPage.kt": "Column(Modifier.fillMaxSize().background(AppColors.MyBg)) {",
    "ui/OfficialAccountPage.kt": "Column(Modifier.fillMaxSize().background(AppColors.MyBg)) {",
    "ui/ArticleEditorScreen.kt": "Column(Modifier.fillMaxSize().background(pageBg)) {",
}
for relative, expected in checks.items():
    if expected not in (ROOT / relative).read_text(encoding="utf-8"):
        raise SystemExit(f"Safe-area root verification failed: {relative}")

# Keep the independent Xiumi editor root free of per-page insets; the Activity
# now reserves the same system-bar safe region for every route.
xiumi = (ROOT / "ui/XiumiArticleLayoutScreen.kt").read_text(encoding="utf-8")
if "Column(Modifier.fillMaxSize().background(Color(0xFFF2F3F4)))" not in xiumi:
    raise SystemExit("Independent Xiumi editor root changed; inspect before patching.")

print("Verified global safe-area handling for Layout, My, History, Official Account, Article Editor and Xiumi routes.")
