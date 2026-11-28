package com.shiwanju.app.ui

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

data class XingtuV2VersionInfo(val id: String, val label: String, val createdAt: Long)

/** Local draft persistence for the independent Xingtu V2 document. */
object XingtuV2Persistence {
    private const val PREFS = "xingtu_editor_v2"
    private const val KEY_DOCUMENT = "active_document"
    private const val KEY_VERSIONS = "document_versions"

    fun load(context: Context): XingtuV2Document? {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_DOCUMENT, null) ?: return null
        return decodeDocument(raw)
    }

    private fun decodeDocument(raw: String): XingtuV2Document? = runCatching {
        val root = JSONObject(raw)
        val canvasJson = root.optJSONObject("canvas") ?: JSONObject()
        val canvas = XingtuV2Canvas(
            width = canvasJson.optDouble("width", 1080.0).toFloat(),
            height = canvasJson.optDouble("height", 1440.0).toFloat(),
            backgroundColor = canvasJson.optLong("backgroundColor", 0xFFFFFFFF)
        )
        val objectsJson = root.optJSONArray("objects") ?: JSONArray()
        val objects = buildList {
            for (index in 0 until objectsJson.length()) {
                val item = objectsJson.optJSONObject(index) ?: continue
                val tJson = item.optJSONObject("transform") ?: JSONObject()
                val transform = XingtuV2Transform(
                    x = tJson.optDouble("x", 0.0).toFloat(),
                    y = tJson.optDouble("y", 0.0).toFloat(),
                    width = tJson.optDouble("width", 160.0).toFloat(),
                    height = tJson.optDouble("height", 64.0).toFloat(),
                    rotation = tJson.optDouble("rotation", 0.0).toFloat(),
                    scaleX = tJson.optDouble("scaleX", 1.0).toFloat(),
                    scaleY = tJson.optDouble("scaleY", 1.0).toFloat(),
                    alpha = tJson.optDouble("alpha", 1.0).toFloat()
                )
                val id = item.optString("id", "restored-$index")
                val visible = item.optBoolean("visible", true)
                val locked = item.optBoolean("locked", false)
                when (item.optString("kind")) {
                    "TEXT" -> add(XingtuV2Object.Text(
                        id = id, content = item.optString("content", ""),
                        fontFamily = item.optString("fontFamily", "default"),
                        fontSizeSp = item.optDouble("fontSizeSp", 24.0).toFloat(),
                        fontWeight = item.optInt("fontWeight", 400),
                        italic = item.optBoolean("italic", false),
                        color = item.optLong("color", 0xFF222222),
                        backgroundColor = item.optLong("backgroundColor", 0x00000000),
                        lineHeight = item.optDouble("lineHeight", 1.35).toFloat(),
                        letterSpacing = item.optDouble("letterSpacing", 0.0).toFloat(),
                        textAlign = item.optString("textAlign", "start"),
                        boxWidth = item.optDouble("boxWidth", 240.0).toFloat(),
                        boxHeight = item.optDouble("boxHeight", 72.0).toFloat(),
                        transform = transform, visible = visible, locked = locked
                    ))
                    "IMAGE" -> add(XingtuV2Object.Image(
                        id = id, assetUri = item.optString("assetUri", ""),
                        cropLeft = item.optDouble("cropLeft", 0.0).toFloat(),
                        cropTop = item.optDouble("cropTop", 0.0).toFloat(),
                        cropRight = item.optDouble("cropRight", 1.0).toFloat(),
                        cropBottom = item.optDouble("cropBottom", 1.0).toFloat(),
                        colorTemperature = item.optDouble("colorTemperature", 0.0).toFloat(),
                        saturation = item.optDouble("saturation", 1.0).toFloat(),
                        brightness = item.optDouble("brightness", 0.0).toFloat(),
                        contrast = item.optDouble("contrast", 1.0).toFloat(),
                        cornerRadius = item.optDouble("cornerRadius", 0.0).toFloat(),
                        borderWidth = item.optDouble("borderWidth", 0.0).toFloat(),
                        borderColor = item.optLong("borderColor", 0x00000000),
                        shadowRadius = item.optDouble("shadowRadius", 0.0).toFloat(),
                        flipHorizontal = item.optBoolean("flipHorizontal", false),
                        flipVertical = item.optBoolean("flipVertical", false),
                        transform = transform, visible = visible, locked = locked
                    ))
                    "COMPONENT" -> add(XingtuV2Object.Component(
                        id = id, componentType = item.optString("componentType", "rectangle"),
                        fillColor = item.optLong("fillColor", 0xFFF1F1F1),
                        cornerRadius = item.optDouble("cornerRadius", 0.0).toFloat(),
                        strokeColor = item.optLong("strokeColor", 0x00000000),
                        strokeWidth = item.optDouble("strokeWidth", 0.0).toFloat(),
                        transform = transform, visible = visible, locked = locked
                    ))
                }
            }
        }
        XingtuV2Document(
            id = root.optString("id", "xingtu-v2-document"),
            canvas = canvas, objects = objects,
            revision = root.optLong("revision", 0L)
        )
    }.getOrNull()

    fun exportToUri(context: Context, uri: android.net.Uri, document: XingtuV2Document) {
        save(context, document)
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_DOCUMENT, null) ?: return
        context.contentResolver.openOutputStream(uri, "wt")?.use { output ->
            output.write(raw.toByteArray(Charsets.UTF_8))
        }
    }

    fun importFromUri(context: Context, uri: android.net.Uri): XingtuV2Document? = runCatching {
        val raw = context.contentResolver.openInputStream(uri)?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }
            ?: return null
        val imported = decodeDocument(raw) ?: return null
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(KEY_DOCUMENT, raw).apply()
        imported
    }.getOrNull()

    fun listVersions(context: Context): List<XingtuV2VersionInfo> = runCatching {
        val raw = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY_VERSIONS, "[]") ?: "[]"
        val array = JSONArray(raw)
        buildList {
            for (index in 0 until array.length()) {
                val item = array.optJSONObject(index) ?: continue
                add(XingtuV2VersionInfo(
                    id = item.optString("id"),
                    label = item.optString("label"),
                    createdAt = item.optLong("createdAt")
                ))
            }
        }.sortedByDescending { it.createdAt }
    }.getOrDefault(emptyList())

    fun createVersion(context: Context, document: XingtuV2Document, label: String): List<XingtuV2VersionInfo> {
        save(context, document)
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val rawDocument = prefs.getString(KEY_DOCUMENT, null) ?: return listVersions(context)
        val versions = runCatching { JSONArray(prefs.getString(KEY_VERSIONS, "[]") ?: "[]") }.getOrDefault(JSONArray())
        val createdAt = System.currentTimeMillis()
        versions.put(JSONObject()
            .put("id", "version-$createdAt")
            .put("label", label)
            .put("createdAt", createdAt)
            .put("document", rawDocument))
        while (versions.length() > 20) versions.remove(0)
        prefs.edit().putString(KEY_VERSIONS, versions.toString()).apply()
        return listVersions(context)
    }

    fun restoreVersion(context: Context, id: String): XingtuV2Document? = runCatching {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val versions = JSONArray(prefs.getString(KEY_VERSIONS, "[]") ?: "[]")
        val selected = (0 until versions.length()).mapNotNull { versions.optJSONObject(it) }
            .firstOrNull { it.optString("id") == id } ?: return null
        prefs.edit().putString(KEY_DOCUMENT, selected.getString("document")).apply()
        load(context)
    }.getOrNull()

    fun save(context: Context, document: XingtuV2Document) {
        runCatching {
            val root = JSONObject()
                .put("id", document.id)
                .put("revision", document.revision)
                .put("canvas", JSONObject()
                    .put("width", document.canvas.width)
                    .put("height", document.canvas.height)
                    .put("backgroundColor", document.canvas.backgroundColor))
            val array = JSONArray()
            document.objects.forEach { item ->
                val t = item.transform
                val json = JSONObject()
                    .put("id", item.id)
                    .put("kind", item.kind.name)
                    .put("visible", item.visible)
                    .put("locked", item.locked)
                    .put("transform", JSONObject()
                        .put("x", t.x).put("y", t.y)
                        .put("width", t.width).put("height", t.height)
                        .put("rotation", t.rotation).put("scaleX", t.scaleX)
                        .put("scaleY", t.scaleY).put("alpha", t.alpha))
                when (item) {
                    is XingtuV2Object.Text -> json
                        .put("content", item.content).put("fontFamily", item.fontFamily)
                        .put("fontSizeSp", item.fontSizeSp).put("fontWeight", item.fontWeight)
                        .put("italic", item.italic).put("color", item.color).put("backgroundColor", item.backgroundColor)
                        .put("lineHeight", item.lineHeight).put("letterSpacing", item.letterSpacing)
                        .put("textAlign", item.textAlign).put("boxWidth", item.boxWidth)
                        .put("boxHeight", item.boxHeight)
                    is XingtuV2Object.Image -> json
                        .put("assetUri", item.assetUri).put("cropLeft", item.cropLeft)
                        .put("cropTop", item.cropTop).put("cropRight", item.cropRight)
                        .put("cropBottom", item.cropBottom).put("colorTemperature", item.colorTemperature)
                        .put("saturation", item.saturation).put("brightness", item.brightness)
                        .put("contrast", item.contrast)
                        .put("cornerRadius", item.cornerRadius).put("borderWidth", item.borderWidth)
                        .put("borderColor", item.borderColor).put("shadowRadius", item.shadowRadius)
                        .put("flipHorizontal", item.flipHorizontal).put("flipVertical", item.flipVertical)
                    is XingtuV2Object.Component -> json
                        .put("componentType", item.componentType).put("fillColor", item.fillColor)
                        .put("cornerRadius", item.cornerRadius).put("strokeColor", item.strokeColor)
                        .put("strokeWidth", item.strokeWidth)
                }
                array.put(json)
            }
            root.put("objects", array)
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putString(KEY_DOCUMENT, root.toString()).apply()
        }
    }
}
