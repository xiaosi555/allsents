#!/usr/bin/env python3
from pathlib import Path
import shutil
root=Path(".")
java=root/"source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app"
overlay=root/"native-overlay/app/src/main/java/com/shiwanju/app"
shutil.copy2(overlay/"ui/IconSplashScreen.kt",java/"ui/IconSplashScreen.kt")
main=java/"MainActivity.kt"
source=main.read_text(encoding="utf-8")
if "IconSplashScreen(vm.iconStyle)" not in source:
    start=source.index("        setContent {")
    end=source.index("\n        }\n    }\n}",start)+len("\n        }")
    replacement="""        setContent {
            val showSplash = androidx.compose.runtime.remember { androidx.compose.runtime.mutableStateOf(true) }
            ShiWanJuTheme(dark = vm.screen == "layout") {
                if (showSplash.value) {
                    com.shiwanju.app.ui.IconSplashScreen(vm.iconStyle) { showSplash.value = false }
                } else {
                    LaunchedEffect(vm.message) { vm.message?.let { Toast.makeText(this@MainActivity, it, Toast.LENGTH_SHORT).show(); vm.message = null } }
                    if (vm.screen == "layout") LayoutScreen(vm) else MyScreen(vm)
                }
            }
        }"""
    source=source[:start]+replacement+source[end:]
    main.write_text(source,encoding="utf-8")
print("Splash wired into MainActivity; original app content is preserved after timeout or tap-to-skip.")
