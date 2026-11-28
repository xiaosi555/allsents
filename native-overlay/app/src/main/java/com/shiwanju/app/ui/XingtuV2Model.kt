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
        val fontWeight: Int = 400, val italic: Boolean = false,
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
        val flipHorizontal: Boolean = false, val flipVertical: Boolean = false,
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
    data class DuplicateObject(val id: String, val newId: String) : XingtuV2Action()
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
            is XingtuV2Action.DuplicateObject -> {
                val source = document.objects.firstOrNull { it.id == action.id && !it.locked }
                if (source == null) document else {
                    val duplicate = when (source) {
                        is XingtuV2Object.Text -> source.copy(id = action.newId,
                            transform = source.transform.copy(x = source.transform.x + 24f, y = source.transform.y + 24f))
                        is XingtuV2Object.Image -> source.copy(id = action.newId,
                            transform = source.transform.copy(x = source.transform.x + 24f, y = source.transform.y + 24f))
                        is XingtuV2Object.Component -> source.copy(id = action.newId,
                            transform = source.transform.copy(x = source.transform.x + 24f, y = source.transform.y + 24f))
                    }
                    document.copy(objects = document.objects + duplicate, selectedIds = setOf(action.newId))
                }
            }
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
        is XingtuV2Object.Text -> v.copy(transform = t, boxWidth = t.width, boxHeight = t.height)
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
    val redoStack: List<XingtuV2Document> = emptyList(),
    private val transformSnapshot: XingtuV2Document? = null
) {
    fun beginTransform(): XingtuV2History = copy(transformSnapshot = document)

    fun updateTransform(id: String, transform: XingtuV2Transform): XingtuV2History {
        val updated = XingtuV2Reducer.reduce(document, XingtuV2Action.TransformObject(id, transform))
        return if (updated == document) this else copy(document = updated)
    }

    fun endTransform(): XingtuV2History {
        val snapshot = transformSnapshot ?: return this
        return if (snapshot == document) copy(transformSnapshot = null)
        else copy(undoStack = (undoStack + snapshot).takeLast(100), redoStack = emptyList(), transformSnapshot = null)
    }

    /** Move all currently selected unlocked objects by one shared canvas-space delta. */
    fun updateSelectedOffset(dx: Float, dy: Float): XingtuV2History {
        val selected = document.selectedIds
        if (selected.isEmpty()) return this
        val updated = document.copy(objects = document.objects.map { item ->
            if (item.id in selected && !item.locked) {
                val t = item.transform
                val next = t.copy(x = t.x + dx, y = t.y + dy)
                when (item) {
                    is XingtuV2Object.Text -> item.copy(transform = next)
                    is XingtuV2Object.Image -> item.copy(transform = next)
                    is XingtuV2Object.Component -> item.copy(transform = next)
                }
            } else item
        }, revision = document.revision + 1)
        return if (updated == document) this else copy(document = updated)
    }

    /** Align selected objects by their visual, unrotated bounds. */
    fun alignSelected(mode: String): XingtuV2History {
        val selected = document.selectedObjects().filterNot { it.locked }
        if (selected.size < 2) return this
        val left = selected.minOf { it.transform.x }
        val top = selected.minOf { it.transform.y }
        val right = selected.maxOf { it.transform.x + it.transform.width * it.transform.scaleX }
        val bottom = selected.maxOf { it.transform.y + it.transform.height * it.transform.scaleY }
        val changed = document.objects.map { item ->
            if (item !in selected) item else {
                val t = item.transform
                val w = t.width * t.scaleX
                val h = t.height * t.scaleY
                val x = when (mode) {
                    "left" -> left
                    "center-x" -> (left + right - w) / 2f
                    "right" -> right - w
                    else -> t.x
                }
                val y = when (mode) {
                    "top" -> top
                    "center-y" -> (top + bottom - h) / 2f
                    "bottom" -> bottom - h
                    else -> t.y
                }
                val next = t.copy(x = x, y = y)
                when (item) {
                    is XingtuV2Object.Text -> item.copy(transform = next)
                    is XingtuV2Object.Image -> item.copy(transform = next)
                    is XingtuV2Object.Component -> item.copy(transform = next)
                }
            }
        }
        val next = document.copy(objects = changed, revision = document.revision + 1)
        return if (next == document) this else copy(document = next, undoStack = undoStack + document, redoStack = emptyList())
    }

    /** Distribute selected objects evenly between the outermost objects. */
    fun distributeSelected(horizontal: Boolean): XingtuV2History {
        val selected = document.selectedObjects().filterNot { it.locked }
        if (selected.size < 3) return this
        val ordered = if (horizontal) selected.sortedBy { it.transform.x } else selected.sortedBy { it.transform.y }
        val start = if (horizontal) ordered.first().transform.x else ordered.first().transform.y
        val end = ordered.last().let { item ->
            if (horizontal) item.transform.x + item.transform.width * item.transform.scaleX
            else item.transform.y + item.transform.height * item.transform.scaleY
        }
        val total = ordered.sumOf { item ->
            (if (horizontal) item.transform.width * item.transform.scaleX else item.transform.height * item.transform.scaleY).toDouble()
        }.toFloat()
        val gap = (end - start - total) / (ordered.size - 1)
        var cursor = start
        val positions = mutableMapOf<String, Float>()
        ordered.forEachIndexed { index, item ->
            positions[item.id] = cursor
            cursor += (if (horizontal) item.transform.width * item.transform.scaleX else item.transform.height * item.transform.scaleY)
            if (index < ordered.lastIndex) cursor += gap
        }
        val changed = document.objects.map { item ->
            val position = positions[item.id] ?: return@map item
            val t = item.transform
            val next = if (horizontal) t.copy(x = position) else t.copy(y = position)
            when (item) {
                is XingtuV2Object.Text -> item.copy(transform = next)
                is XingtuV2Object.Image -> item.copy(transform = next)
                is XingtuV2Object.Component -> item.copy(transform = next)
            }
        }
        val next = document.copy(objects = changed, revision = document.revision + 1)
        return if (next == document) this else copy(document = next, undoStack = undoStack + document, redoStack = emptyList())
    }

    /** Duplicate every selected unlocked object as one undoable operation. */
    fun duplicateSelected(idPrefix: String): XingtuV2History {
        val selected = document.selectedObjects().filterNot { it.locked }
        if (selected.isEmpty()) return this
        val copies = selected.mapIndexed { index, source ->
            val newId = "$idPrefix-$index"
            when (source) {
                is XingtuV2Object.Text -> source.copy(id = newId,
                    transform = source.transform.copy(x = source.transform.x + 24f, y = source.transform.y + 24f))
                is XingtuV2Object.Image -> source.copy(id = newId,
                    transform = source.transform.copy(x = source.transform.x + 24f, y = source.transform.y + 24f))
                is XingtuV2Object.Component -> source.copy(id = newId,
                    transform = source.transform.copy(x = source.transform.x + 24f, y = source.transform.y + 24f))
            }
        }
        val next = document.copy(
            objects = document.objects + copies,
            selectedIds = copies.map { it.id }.toSet(),
            revision = document.revision + 1
        )
        return copy(document = next, undoStack = undoStack + document, redoStack = emptyList())
    }

    /** Uniformly scale and rotate the selected group around its collective center. */
    fun updateSelectedGroup(scaleFactor: Float, rotationDelta: Float): XingtuV2History {
        val selected = document.selectedObjects().filterNot { it.locked }
        if (selected.isEmpty()) return this
        val left = selected.minOf { it.transform.x }
        val top = selected.minOf { it.transform.y }
        val right = selected.maxOf { it.transform.x + it.transform.width * it.transform.scaleX }
        val bottom = selected.maxOf { it.transform.y + it.transform.height * it.transform.scaleY }
        val centerX = (left + right) / 2f
        val centerY = (top + bottom) / 2f
        val radians = Math.toRadians(rotationDelta.toDouble())
        val c = kotlin.math.cos(radians).toFloat()
        val sn = kotlin.math.sin(radians).toFloat()
        val factor = scaleFactor.coerceIn(0.1f, 5f)
        val updatedObjects = document.objects.map { item ->
            if (item !in selected) item else {
                val t = item.transform
                val objectCenterX = t.x + t.width * t.scaleX / 2f
                val objectCenterY = t.y + t.height * t.scaleY / 2f
                val dx = (objectCenterX - centerX) * factor
                val dy = (objectCenterY - centerY) * factor
                val nextCenterX = centerX + dx * c - dy * sn
                val nextCenterY = centerY + dx * sn + dy * c
                val next = t.copy(
                    x = nextCenterX - t.width * factor * t.scaleX / 2f,
                    y = nextCenterY - t.height * factor * t.scaleY / 2f,
                    width = t.width * factor,
                    height = t.height * factor,
                    rotation = t.rotation + rotationDelta
                )
                when (item) {
                    is XingtuV2Object.Text -> item.copy(transform = next, boxWidth = next.width, boxHeight = next.height)
                    is XingtuV2Object.Image -> item.copy(transform = next)
                    is XingtuV2Object.Component -> item.copy(transform = next)
                }
            }
        }
        val updated = document.copy(objects = updatedObjects, revision = document.revision + 1)
        return if (updated == document) this else copy(document = updated)
    }

    /** Live canvas property update; the open canvas panel owns one undo transaction. */
    fun updateCanvasLive(canvas: XingtuV2Canvas): XingtuV2History {
        val updated = document.copy(canvas = canvas, revision = document.revision + 1)
        return if (updated == document) this else copy(document = updated)
    }

    /** Apply live panel edits without creating one undo entry per slider tick. */
    fun updateObjectLive(value: XingtuV2Object): XingtuV2History {
        val updated = XingtuV2Reducer.reduce(document, XingtuV2Action.ReplaceObject(value))
        return if (updated == document) this else copy(document = updated)
    }

    fun dispatch(action: XingtuV2Action): XingtuV2History {
        val updated = XingtuV2Reducer.reduce(document, action)
        return if (updated == document) this else copy(document = updated, undoStack = (undoStack + document).takeLast(100), redoStack = emptyList())
    }
    fun undo(): XingtuV2History {
        // An open property panel/gesture is one transaction. Undo it as a whole
        // instead of leaving a stale snapshot that would be re-added on panel close.
        val activeSnapshot = transformSnapshot
        if (activeSnapshot != null) {
            return copy(
                document = activeSnapshot,
                redoStack = (redoStack + document).takeLast(100),
                // Keep the panel transaction open from the restored baseline so
                // edits made after undo are still committed as one undo step.
                transformSnapshot = activeSnapshot
            )
        }
        if (undoStack.isEmpty()) return this
        return copy(
            document = undoStack.last(),
            undoStack = undoStack.dropLast(1),
            redoStack = (redoStack + document).takeLast(100)
        )
    }
    fun redo(): XingtuV2History {
        if (transformSnapshot != null || redoStack.isEmpty()) return this
        return copy(
            document = redoStack.last(),
            undoStack = (undoStack + document).takeLast(100),
            redoStack = redoStack.dropLast(1)
        )
    }
}
