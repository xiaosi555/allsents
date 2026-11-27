#!/usr/bin/env python3
"""Keep the active article-editing target visible above the IME and tool sheet."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / "source/ShiWanJu-Android/app/src/main/java/com/shiwanju/app/ui/ArticleEditorScreen.kt"
ERROR = ROOT / "editor_target_visibility_patch_error.txt"
s = EDITOR.read_text(encoding="utf-8")

def once(old: str, new: str, label: str):
    global s
    if new in s:
        return
    count = s.count(old)
    if count != 1:
        ERROR.write_text(f"{label}: expected 1 anchor, found {count}\\n", encoding="utf-8")
        raise SystemExit(f"Editor target visibility patch anchor mismatch [{label}]: {count}")
    s = s.replace(old, new, 1)
    print("Editor target visibility patch:", label)

once(
    "function selectedParagraph(){const sel=window.getSelection();let e=sel&&sel.anchorNode?(sel.anchorNode.nodeType===3?sel.anchorNode.parentElement:sel.anchorNode):null;while(e&&e!==root&&!/^(P|H1|H2|H3|H4|BLOCKQUOTE|LI|PRE)$/.test(e.tagName))e=e.parentElement;return e&&e!==root?e:null;}",
    """function selectedParagraph(){const sel=window.getSelection();let e=sel&&sel.anchorNode?(sel.anchorNode.nodeType===3?sel.anchorNode.parentElement:sel.anchorNode):null;while(e&&e!==root&&!/^(P|H1|H2|H3|H4|BLOCKQUOTE|LI|PRE)$/.test(e.tagName))e=e.parentElement;return e&&e!==root?e:null;}
                            let nativeOcclusionPx=0;
                            function ensureEditorTargetVisible(occlusionPx){
                              nativeOcclusionPx=Math.max(0,Number(occlusionPx)||0);
                              let target=activeImage;
                              if(!target&&savedRange&&savedRange.startContainer){
                                target=savedRange.startContainer.nodeType===3?savedRange.startContainer.parentElement:savedRange.startContainer;
                                while(target&&target!==root&&!/^(P|H1|H2|H3|H4|BLOCKQUOTE|LI|PRE|IMG|TABLE|DIV)$/.test(target.tagName))target=target.parentElement;
                              }
                              if(!target||target===root)target=selectedParagraph();
                              if(!target||target===root)return;
                              const rect=target.getBoundingClientRect();
                              const safeTop=12;
                              const safeBottom=Math.max(safeTop+48,window.innerHeight-nativeOcclusionPx-20);
                              let delta=0;
                              if(rect.bottom>safeBottom)delta=rect.bottom-safeBottom;
                              else if(rect.top<safeTop)delta=rect.top-safeTop;
                              if(Math.abs(delta)>2)window.scrollBy({top:delta,behavior:'smooth'});
                            }
                            window.addEventListener('resize',()=>setTimeout(()=>ensureEditorTargetVisible(nativeOcclusionPx),100));""",
    "selection target visibility helper"
)

once(
    "    val animatedToolPanelHeight = toolPanelHeightDp.coerceIn(100f, 400f).dp",
    """    val animatedToolPanelHeight = toolPanelHeightDp.coerceIn(100f, 400f).dp
    val editorWindowDensity = LocalDensity.current
    val editorImeBottomPx = WindowInsets.ime.getBottom(editorWindowDensity)
    LaunchedEffect(showToolPopup, showCanvasPopup, toolPanelHeightDp, editorImeBottomPx, activePanel) {
        delay(140)
        val coveredPanelPx = with(editorWindowDensity) {
            (if (showToolPopup) toolPanelHeightDp else if (showCanvasPopup) 200f else 0f).dp.toPx()
        }
        editor?.evaluateJavascript("ensureEditorTargetVisible(${coveredPanelPx.toInt()})", null)
    }""",
    "react to IME and secondary panel visibility"
)

once(
    "    Box(Modifier.fillMaxSize().background(pageBg).systemBarsPadding()) {",
    "    Box(Modifier.fillMaxSize().background(pageBg).systemBarsPadding().imePadding()) {",
    "resize editor layout above software keyboard"
)

EDITOR.write_text(s, encoding="utf-8")
