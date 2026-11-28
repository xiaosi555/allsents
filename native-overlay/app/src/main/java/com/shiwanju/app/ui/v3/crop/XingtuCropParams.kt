package com.shiwanju.app.ui.v3.crop

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Matrix
import android.graphics.Paint
import android.graphics.RectF
import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.max

/** 醒图 3.0 裁剪比例，比例值表示裁剪框宽/高。 */
enum class XingtuCropAspect(val title: String, val ratio: Float?) {
    FREE("自由", null),
    ORIGINAL("原始", null),
    R1X1("1:1", 1f),
    R3X4("3:4", 3f / 4f),
    R4X3("4:3", 4f / 3f),
    R9X16("9:16", 9f / 16f),
    R16X9("16:9", 16f / 9f),
    R2X3("2:3", 2f / 3f),
    R3X2("3:2", 3f / 2f),
}

/** 相对当前方向画面的归一化裁剪框。 */
data class XingtuCropRect(
    val x: Float = 0f,
    val y: Float = 0f,
    val width: Float = 1f,
    val height: Float = 1f,
) {
    val right: Float get() = x + width
    val bottom: Float get() = y + height

    fun clamped(): XingtuCropRect {
        val w = width.coerceIn(0.01f, 1f)
        val h = height.coerceIn(0.01f, 1f)
        val left = x.coerceIn(0f, 1f - w)
        val top = y.coerceIn(0f, 1f - h)
        return XingtuCropRect(left, top, w, h)
    }
}

/**
 * 裁剪变换顺序：水平翻转 → 顺时针 90° 倍数 → 拉直 → 裁剪。
 * straighten 正数表示顺时针角度；rect 位于旋转后的归一化画面坐标系。
 */
data class XingtuCropParams(
    val flippedHorizontally: Boolean = false,
    val quarterTurns: Int = 0,
    val straightenDegrees: Float = 0f,
    val rect: XingtuCropRect = XingtuCropRect(),
) {
    val isIdentity: Boolean
        get() = !flippedHorizontally && normalizedTurns == 0 &&
            abs(straightenDegrees) <= 0.01f && rect == XingtuCropRect()

    private val normalizedTurns: Int
        get() = ((quarterTurns % 4) + 4) % 4

    fun orientedSize(width: Int, height: Int): Pair<Int, Int> =
        if (normalizedTurns % 2 == 1) height to width else width to height

    fun rotateClockwise(): XingtuCropParams = copy(
        quarterTurns = (normalizedTurns + 1) % 4,
        rect = XingtuCropRect(1f - rect.bottom, rect.x, rect.height, rect.width),
    )

    fun flipHorizontal(): XingtuCropParams = copy(
        flippedHorizontally = !flippedHorizontally,
        quarterTurns = (4 - normalizedTurns) % 4,
        straightenDegrees = -straightenDegrees,
        rect = rect.copy(x = 1f - rect.right),
    )

    fun flipVertical(): XingtuCropParams = copy(
        flippedHorizontally = !flippedHorizontally,
        quarterTurns = ((2 - normalizedTurns) % 4 + 4) % 4,
        straightenDegrees = -straightenDegrees,
        rect = rect.copy(y = 1f - rect.bottom),
    )

    /** 返回原图像素坐标到旋转、翻转、拉直后画面的矩阵。 */
    private fun orientationMatrix(width: Int, height: Int): Matrix {
        val matrix = Matrix()
        if (flippedHorizontally) {
            matrix.postScale(-1f, 1f)
            matrix.postTranslate(width.toFloat(), 0f)
        }
        if (normalizedTurns != 0) {
            matrix.postRotate(90f * normalizedTurns)
            val bounds = RectF(0f, 0f, width.toFloat(), height.toFloat())
            matrix.mapRect(bounds)
            matrix.postTranslate(-bounds.left, -bounds.top)
        }
        val (orientedWidth, orientedHeight) = orientedSize(width, height)
        if (abs(straightenDegrees) > 0.01f) {
            val radians = abs(Math.toRadians(straightenDegrees.toDouble()))
            val scale = (
                cos(radians) + kotlin.math.sin(radians) *
                    max(orientedWidth.toDouble() / orientedHeight, orientedHeight.toDouble() / orientedWidth)
                ).toFloat()
            matrix.postTranslate(-orientedWidth / 2f, -orientedHeight / 2f)
            matrix.postRotate(straightenDegrees)
            matrix.postScale(scale, scale)
            matrix.postTranslate(orientedWidth / 2f, orientedHeight / 2f)
        }
        return matrix
    }

    private fun render(source: Bitmap, matrix: Matrix, width: Int, height: Int): Bitmap {
        val output = Bitmap.createBitmap(
            width.coerceAtLeast(1),
            height.coerceAtLeast(1),
            Bitmap.Config.ARGB_8888,
        )
        Canvas(output).drawBitmap(
            source,
            matrix,
            Paint(Paint.FILTER_BITMAP_FLAG or Paint.ANTI_ALIAS_FLAG),
        )
        return output
    }

    /** 裁剪界面实时预览使用：仅应用方向和拉直，不截取裁剪框。 */
    fun oriented(source: Bitmap): Bitmap {
        if (!flippedHorizontally && normalizedTurns == 0 && abs(straightenDegrees) <= 0.01f) {
            return source
        }
        val (width, height) = orientedSize(source.width, source.height)
        return render(source, orientationMatrix(source.width, source.height), width, height)
    }

    /** 确认时一次性输出最终像素裁剪结果；不修改 source。 */
    fun apply(source: Bitmap): Bitmap {
        val normalized = rect.clamped()
        val (width, height) = orientedSize(source.width, source.height)
        var left = floor(normalized.x * width + 1e-3f).toInt().coerceIn(0, width)
        var top = floor(normalized.y * height + 1e-3f).toInt().coerceIn(0, height)
        var right = ceil(normalized.right * width - 1e-3f).toInt().coerceIn(0, width)
        var bottom = ceil(normalized.bottom * height - 1e-3f).toInt().coerceIn(0, height)
        if (right - left < 1 || bottom - top < 1) {
            left = 0
            top = 0
            right = width
            bottom = height
        }
        val outputWidth = right - left
        val outputHeight = bottom - top

        if (!flippedHorizontally && normalizedTurns == 0 && abs(straightenDegrees) <= 0.01f) {
            if (left == 0 && top == 0 && outputWidth == source.width && outputHeight == source.height) {
                return source
            }
            return Bitmap.createBitmap(source, left, top, outputWidth, outputHeight)
        }

        val matrix = orientationMatrix(source.width, source.height)
        matrix.postTranslate(-left.toFloat(), -top.toFloat())
        return render(source, matrix, outputWidth, outputHeight)
    }

    companion object {
        fun centeredAspect(aspectRatio: Float): XingtuCropRect {
            require(aspectRatio > 0f && aspectRatio.isFinite())
            val width = if (aspectRatio >= 1f) 1f else aspectRatio
            val height = if (aspectRatio >= 1f) 1f / aspectRatio else 1f
            return XingtuCropRect((1f - width) / 2f, (1f - height) / 2f, width, height)
        }
    }
}
