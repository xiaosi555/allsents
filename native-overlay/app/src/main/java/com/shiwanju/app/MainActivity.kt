package com.shiwanju.app

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.runtime.LaunchedEffect
import com.shiwanju.app.ui.AppViewModel
import com.shiwanju.app.ui.HomeScreen
import com.shiwanju.app.ui.LayoutScreen
import com.shiwanju.app.ui.MyScreen
import com.shiwanju.app.ui.ShiWanJuTheme

class MainActivity : ComponentActivity() {
    private val vm: AppViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            ShiWanJuTheme(dark = vm.screen == "layout") {
                LaunchedEffect(vm.message) {
                    vm.message?.let {
                        Toast.makeText(this@MainActivity, it, Toast.LENGTH_SHORT).show()
                        vm.message = null
                    }
                }
                when (vm.screen) {
                    "layout" -> LayoutScreen(vm)
                    "my" -> MyScreen(vm)
                    else -> HomeScreen(vm)
                }
            }
        }
    }
}
