package com.shiwanju.app.ui

/** 醒图 2.0 独立画布文档模型，不依赖旧版 WebView/DOM 状态。 */
enum class XingtuV2ObjectKind { TEXT, IMAGE, COMPONENT }

data class XingtuV2Transform(
    val x: Float = 0f, val y: Float = 0f,
    val width: Float = 160f, val height: Float = 64f,
    val rotation: Float = 0f, val scaleX: Float = 1f, val scaleY: Float = 1f,
    val alpha: Float = 1f
)

sealed class XingtuV2Object {
    abstract val id: String
    abstract val transform: XingtuV2Transform
    abstract val visible: Boolean
    abstract val locked: Boolean
    abstract val kind: XingtuV2ObjectKind

    data class Text(
        override val id: String, val content: String,
        val fontFamily: String = "default", val fontSizeSp: Float = 24f,
        val color: Long = 0xFF222222, val lineHeight: Float = 1.35f,
        val letterSpacing: Float = 0f, val textAlign: String = "start",
        val boxWidth: Float = 240f, val boxHeight: Float = 72f,
        override val transform: XingtuV2Transform = XingtuV2Transform(width = 240f, height = 72f),
        override val visible: Boolean = true, override val locked: Boolean = false
    ) : XingtuV2Object() { override val kind = XingtuV2ObjectKind.TEXT }

    data class Image(
        override val id: String, val assetUri: String,
        val cropLeft: Float = 0f, val cropTop: Float = 0f,
        val cropRight: Float = 1f, val cropBottom: Float = 1f,
        val colorTemperature: Float = 0f, val saturation: Float = 1f,
        val brightness: Float = 0f,
        override val transform: XingtuV2Transform = XingtuV2Transform(),
        override val visible: Boolean = true, override val locked: Boolean = false
    ) : XingtuV2Object() { override val kind = XingtuV2ObjectKind.IMAGE }

    data class Component(
        override val id: String, val componentType: String,
        val fillColor: Long = 0xFFF1F1F1, val cornerRadius: Float = 0f,
        val strokeColor: Long = 0x00000000, val strokeWidth: Float = 0f,
        override val transform: XingtuV2Transform = XingtuV2Transform(),
        override val visible: Boolean = true, override val locked: Boolean = false
    ) : XingtuV2Object() { override val kind = XingtuV2ObjectKind.COMPONENT }
}

data class XingtuV2Canvas(
    val width: Float = 1080f, val height: Float = 1440f,
    val backgroundColor: Long = 0xFFFFFFFF
)

data class XingtuV2Document(
    val id: String, val canvas: XingtuV2Canvas = XingtuV2Canvas(),
    val objects: List<XingtuV2Object> = emptyList(),
    val selectedIds: Set<String> = emptySet(), val revision: Long = 0L
) {
    fun selectedObjects(): List<XingtuV2Object> =
        objects.filter { it.id in selectedIds && it.visible }
}

sealed class XingtuV2Action {
    data class Select(val ids: Set<String>, val additive: Boolean = false) : XingtuV2Action()
    data class TransformObject(val id: String, val transform: XingtuV2Transform) : XingtuV2Action()
    data class SetVisibility(val id: String, val visible: Boolean) : XingtuV2Action()
    data class SetLocked(val id: String, val locked: Boolean) : XingtuV2Action()
    data class ReplaceObject(val value: XingtuV2Object) : XingtuV2Action()
    data class InsertObject(val value: XingtuV2Object) : XingtuV2Action()
    data class DeleteObjects(val ids: Set<String>) : XingtuV2Action()
    data class Reorder(val id: String, val targetIndex: Int) : XingtuV2Action()
    data class SetCanvas(val canvas: XingtuV2Canvas) : XingtuV2Action()
}

object XingtuV2Reducer {
    fun reduce(document: XingtuV2Document, action: XingtuV2Action): XingtuV2Document {
        val next = when (action) {
            is XingtuV2Action.Select -> {
                val valid = action.ids.intersect(document.objects.map { it.id }.toSet())
                document.copy(selectedIds = if (action.additive) (document.selectedIds - valid) + (valid - document.selectedIds) else valid)
            }
            is XingtuV2Action.TransformObject ->
                document.copy(objects = document.objects.map {
                    if (it.id == action.id && !it.locked) withTransform(it, action.transform) else it
                })
            is XingtuV2Action.SetVisibility ->
                document.copy(objects = document.objects.map { if (it.id == action.id) visibility(it, action.visible) else it })
            is XingtuV2Action.SetLocked ->
                document.copy(objects = document.objects.map { if (it.id == action.id) locked(it, action.locked) else it })
            is XingtuV2Action.ReplaceObject ->
                document.copy(objects = document.objects.map { if (it.id == action.value.id && !it.locked) action.value else it })
            is XingtuV2Action.InsertObject ->
                document.copy(objects = document.objects.filterNot { it.id == action.value.id } + action.value, selectedIds = setOf(action.value.id))
            is XingtuV2Action.DeleteObjects ->
                document.copy(objects = document.objects.filterNot { it.id in action.ids && !it.locked }, selectedIds = document.selectedIds - action.ids)
            is XingtuV2Action.Reorder -> {
                val list = document.objects.toMutableList()
                val old = list.indexOfFirst { it.id == action.id }
                if (old < 0 || list[old].locked) document else {
                    val item = list.removeAt(old)
                    list.add(action.targetIndex.coerceIn(0, list.size), item)
                    document.copy(objects = list)
                }
            }
            is XingtuV2Action.SetCanvas -> document.copy(canvas = action.canvas)
        }
        return if (next == document) document else next.copy(revision = document.revision + 1)
    }

    private fun withTransform(v: XingtuV2Object, t: XingtuV2Transform): XingtuV2Object = when (v) {
        is XingtuV2Object.Text -> v.copy(transform = t)
        is XingtuV2Object.Image -> v.copy(transform = t)
        is XingtuV2Object.Component -> v.copy(transform = t)
    }
    private fun visibility(v: XingtuV2Object, value: Boolean): XingtuV2Object = when (v) {
        is XingtuV2Object.Text -> v.copy(visible = value)
        is XingtuV2Object.Image -> v.copy(visible = value)
        is XingtuV2Object.Component -> v.copy(visible = value)
    }
    private fun locked(v: XingtuV2Object, value: Boolean): XingtuV2Object = when (v) {
        is XingtuV2Object.Text -> v.copy(locked = value)
        is XingtuV2Object.Image -> v.copy(locked = value)
        is XingtuV2Object.Component -> v.copy(locked = value)
    }
}

/** 快照历史：每个变换动作都会产生可撤销快照；后续将把连续手势合并为单次历史事务。 */
data class XingtuV2History(
    val document: XingtuV2Document,
    val undoStack: List<XingtuV2Document> = emptyList(),
    val redoStack: List<XingtuV2Document> = emptyList()
) {
    private var transformSnapshot: XingtuV2Document? = null

    fun beginTransform(): XingtuV2History = copy().also { it.transformSnapshot = document }

    fun updateTransform(id: String, transform: XingtuV2Transform): XingtuV2History {
        val updated = XingtuV2Reducer.reduce(document, XingtuV2Action.TransformObject(id, transform))
        return if (updated == document) this else copy(document = updated)
    }

    fun endTransform(): XingtuV2History {
        val snapshot = transformSnapshot ?: return this
        return if (snapshot == document) copy().also { it.transformSnapshot = null }
        else copy(undoStack = undoStack + snapshot, redoStack = emptyList()).also { it.transformSnapshot = null }
    }

    fun dispatch(action: XingtuV2Action): XingtuV2History {
        val updated = XingtuV2Reducer.reduce(document, action)
        return if (updated == document) this else copy(document = updated, undoStack = undoStack + document, redoStack = emptyList())
    }
    fun undo(): XingtuV2History {
        if (undoStack.isEmpty()) return this
        return copy(document = undoStack.last(), undoStack = undoStack.dropLast(1), redoStack = redoStack + document)
    }
    fun redo(): XingtuV2History {
        if (redoStack.isEmpty()) return this
        return copy(document = redoStack.last(), undoStack = undoStack + document, redoStack = redoStack.dropLast(1))
    }
}
