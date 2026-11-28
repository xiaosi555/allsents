#!/usr/bin/env python3
"""Migrate every Compose Material Icon call to the shared semantic linear icon API."""
from pathlib import Path
import re

ROOT=Path("source/ShiWanJu-Android/app/src/main/java")
UI=ROOT/"com/shiwanju/app/ui"
REGISTRY=UI/"HomeAndIconLibrary.kt"
if not UI.is_dir() or not REGISTRY.is_file(): raise SystemExit("Android UI source or icon registry missing.")
LABELS={
"ArrowBack":"返回","ArrowForward":"前进","Close":"关闭","Check":"确认","Add":"添加","Remove":"移除","Delete":"删除","Edit":"编辑","Save":"保存","Search":"搜索","Settings":"设置","Home":"主页","MoreHoriz":"更多","MoreVert":"更多操作","Undo":"撤销","Redo":"重做","Refresh":"刷新","Image":"图片","Photo":"照片","PhotoLibrary":"相册","CameraAlt":"相机","Folder":"文件夹","History":"历史记录","TextFields":"文字","FormatSize":"字号","FormatAlignCenter":"居中对齐","FormatAlignLeft":"左对齐","FormatAlignRight":"右对齐","Brush":"画笔","Crop":"裁剪","RotateRight":"旋转","Layers":"图层","Widgets":"组件","Palette":"调色","AutoFixHigh":"滤镜","Opacity":"透明度","BorderAll":"边框","Lock":"锁定","LockOpen":"解锁","Visibility":"显示","VisibilityOff":"隐藏","ContentCopy":"复制","ContentPaste":"粘贴","Share":"分享","Download":"导出","Upload":"导入","Favorite":"收藏","Star":"星标","AccountCircle":"我的","Person":"用户","Notifications":"通知","Help":"帮助","Info":"提示","Warning":"警告","Error":"错误","CheckCircle":"成功","ExpandMore":"展开","ExpandLess":"收起","KeyboardArrowDown":"向下","KeyboardArrowUp":"向上","Tune":"调整","FilterList":"筛选","Sort":"排序","GridView":"网格","ViewList":"列表","ViewQuilt":"排版","Article":"文章","PhotoCamera":"醒图","CloudUpload":"云上传","FileUpload":"导入","FileDownload":"导出","CalendarMonth":"日历","Schedule":"时间","Link":"链接","OpenInNew":"打开","Fullscreen":"全屏","FullscreenExit":"退出全屏","ZoomIn":"放大","ZoomOut":"缩小","CenterFocusStrong":"定位","AlignHorizontalCenter":"水平居中","AlignVerticalCenter":"垂直居中","Flip":"翻转","FlipCameraAndroid":"翻转","RotateLeft":"向左旋转","FormatColorFill":"填充","FormatColorText":"文字颜色","TextFormat":"文字样式","FormatBold":"加粗","FormatItalic":"斜体","FormatUnderlined":"下划线","FormatLineSpacing":"行距","SpaceBar":"间距","AspectRatio":"比例","LayersClear":"清空图层","PlaylistAdd":"添加项目","Menu":"菜单","ArrowUpward":"上移","ArrowDownward":"下移","DragHandle":"拖动","Done":"完成","DoneAll":"全部完成","Cancel":"取消","Clear":"清除","CloseFullscreen":"关闭全屏","More":"更多","Circle":"圆形"}
def key_for(n): return re.sub(r"(?<!^)(?=[A-Z])","-",n).lower()
def category(label):
 if any(x in label for x in ("图片","相册","照片","相机","文件夹","导入","导出","下载","上传")): return "素材"
 if any(x in label for x in ("文字","字号","字体","加粗","斜体","裁剪","旋转","图层","组件","对齐","调色","滤镜","透明度","边框","锁定","显示","隐藏","复制","粘贴")): return "编辑"
 if any(x in label for x in ("主页","排版","秀米","醒图","我的","设置","搜索","返回","更多")): return "导航"
 if any(x in label for x in ("历史","日历","时间")): return "数据"
 return "通用"
def split_args(s):
 out=[]; start=0; d=0; q=None; esc=False
 for i,ch in enumerate(s):
  if q:
   if esc: esc=False
   elif ch=="\\": esc=True
   elif ch==q: q=None
   continue
  if ch in "\"'": q=ch
  elif ch in "([{<": d+=1
  elif ch in ")]}>": d=max(0,d-1)
  elif ch=="," and d==0: out.append(s[start:i].strip()); start=i+1
 if s[start:].strip(): out.append(s[start:].strip())
 return out
def end_call(s,start):
 d=0; q=None; esc=False
 for i in range(start,len(s)):
  ch=s[i]
  if q:
   if esc: esc=False
   elif ch=="\\": esc=True
   elif ch==q: q=None
   continue
  if ch in "\"'": q=ch
  elif ch=="(": d+=1
  elif ch==")":
   d-=1
   if d==0:return i
 return -1
files=list(ROOT.rglob("*.kt")); registry=REGISTRY.read_text(encoding="utf-8")
items={k:v for k,v in {
"home":("主页","导航"),"layout":("排版","导航"),"xiumi":("秀米排版","导航"),"xingtu":("醒图","导航"),"xingtu2":("醒图 2.0","导航"),"profile":("我的","导航"),"icon-library":("图标库","导航"),"search":("搜索","通用"),"settings":("设置","通用"),"more":("更多","通用"),"back":("返回","通用"),"close":("关闭","通用"),"confirm":("确认","通用"),"add":("添加","通用"),"save":("保存","通用"),"undo":("撤销","通用"),"redo":("重做","通用"),"image":("图片","素材"),"gallery":("相册","素材"),"camera":("相机","素材"),"folder":("文件夹","素材"),"history":("历史记录","数据"),"text":("文字","编辑"),"font":("字体","编辑"),"brush":("画笔","编辑"),"crop":("裁剪","编辑"),"rotate":("旋转","编辑"),"layers":("图层","编辑"),"widgets":("组件","编辑"),"align":("对齐","编辑"),"palette":("调色","编辑"),"filter":("滤镜","编辑"),"opacity":("透明度","编辑"),"border":("边框","编辑"),"lock":("锁定","编辑"),"visible":("显示","编辑"),"delete":("删除","编辑"),"copy":("复制","编辑"),"upload":("导入","素材"),"download":("导出","素材"),"favorite":("收藏","通用")}.items()}
converted=0; remaining=[]
for path in files:
 if path==REGISTRY: continue
 src=path.read_text(encoding="utf-8"); edits=[]
 for m in re.finditer(r"(?<![A-Za-z0-9_])Icon\s*\(",src):
  end=end_call(src,m.end()-1)
  if end<0: continue
  args=split_args(src[m.end():end])
  if not args: continue
  first=args[0]; mat=re.fullmatch(r"Icons\.(?:Outlined|Filled|Rounded|TwoTone|Sharp|Default)\.([A-Za-z0-9_]+)",first); vec=re.fullmatch(r'AppIconVector\("([^"]+)"\)',first); shared=re.fullmatch(r"AppIconVectors\.(?:Outlined|Default|Filled|Rounded|TwoTone|Sharp)([A-Za-z0-9_]+)",first)
  if not mat and not vec and not shared: continue
  if mat:
   name=mat.group(1); key=key_for(name); label=LABELS.get(name,name)
  elif vec:
   key=vec.group(1); label=next((v[0] for k,v in items.items() if k==key),key.replace("-"," "))
  else:
   name=shared.group(1); key=key_for(name); label=LABELS.get(name,name)
  items[key]=(label,category(label))
  named={}; pos=[]
  for arg in args[1:]:
   if "=" in arg: k,v=arg.split("=",1); named[k.strip()]=v.strip()
   else: pos.append(arg)
  tint=named.get("tint") or (pos[1] if len(pos)>1 else "LocalContentColor.current")
  modifier=named.get("modifier") or (pos[2] if len(pos)>2 else "Modifier")
  edits.append((m.start(),end+1,f'AppIcon("{key}", modifier = {modifier}, tint = {tint})'))
 for a,b,repl in reversed(edits): src=src[:a]+repl+src[b:]
 if edits:
  if not re.search(r"Icons\.(?:Outlined|Filled|Rounded|TwoTone|Sharp|Default)\.",src):
   src=re.sub(r"(?m)^import androidx\.compose\.material\.icons\..*\n","",src)
  package=re.search(r"(?m)^package ([\w.]+)",src)
  if package and package.group(1)!="com.shiwanju.app.ui" and "import com.shiwanju.app.ui.AppIcon" not in src:
   src=re.sub(r"(?m)^package [^\n]+\n",lambda m:m.group(0)+"\nimport com.shiwanju.app.ui.AppIcon\n",src,count=1)
  path.write_text(src,encoding="utf-8"); converted+=len(edits)
 if re.search(r"Icons\.(?:Outlined|Filled|Rounded|TwoTone|Sharp|Default)\.",src): remaining.append(str(path))
# Every custom semantic label used by editor tools is also a replaceable catalog entry.
for path in files:
 if path==REGISTRY: continue
 src=path.read_text(encoding="utf-8")
 for label in re.findall(r'ShiWanJuLineIcon\("([^"]+)"',src):
  items[label]=(label,category(label))
 for call in re.finditer(r"\bEditorTool\s*\(",src):
  end=end_call(src,call.end()-1)
  if end>=0:
   args=split_args(src[call.end():end])
   if args:
    for label in re.findall(r'"([^"]+)"',args[0]):
     items[label]=(label,category(label))
 # Route all shared-renderer call sites through AppIcon so user overrides apply globally.
 updated=re.sub(r"(?<!fun )ShiWanJuLineIcon\(", "AppIcon(", src)
 if updated!=src: path.write_text(updated,encoding="utf-8")
entries=",\n".join(f' AppIconItem("{k}","{v[0]}","{v[1]}")' for k,v in sorted(items.items()))
block=f'''private data class AppIconItem(val key:String,val title:String,val category:String)
private val appIconItems = listOf(
{entries}
)

/** Semantic icon registry. Every screen resolves a stable key to the same line icon. */
@Composable fun AppIcon(key:String,modifier:Modifier=Modifier,tint:Color=LocalContentColor.current) {{
 val requested=appIconItems.firstOrNull{{it.key==key || it.title==key}}?.key ?: key
 val resolved=AppIconRegistry.resolve(LocalContext.current,requested)
 val item=appIconItems.firstOrNull{{it.key==resolved || it.title==resolved}}
 ShiWanJuLineIcon(item?.title?:resolved,tint,modifier)
}}
'''
registry,n=re.subn(r"private data class AppIconItem.*?private data class HomePageItem",block+"\nprivate data class HomePageItem",registry,count=1,flags=re.S)
if n!=1: raise SystemExit("Could not replace the old Material-vector icon registry.")
registry=re.sub(r"internal object AppIconVectors \{.*?\n\}\n\n","",registry,count=1,flags=re.S)
registry=re.sub(r"(?m)^import androidx\.compose\.material\.icons\..*\n","",registry)
registry=re.sub(r"(?m)^import androidx\.compose\.ui\.graphics\.vector\.ImageVector\n","",registry)
REGISTRY.write_text(registry,encoding="utf-8")
if remaining: raise SystemExit("Unconverted Material icons remain: "+", ".join(remaining))
glyphs=[]
for p in files:
 for i,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
  if re.search(r'Text\(\s*"[^"]*[↻⌫ⓘ▧▦▤◇⊞▣♡⠿☰☷☻⚙★☆♥✚✎⌂⌕]',line): glyphs.append(f"{p.name}:{i}")
print(f"Semantic registry: {len(items)} keys; migrated {converted} Material Icon composables across {len(files)} Kotlin files.")
print(f"Legacy glyph text candidates remaining: {len(glyphs)}")
for g in glyphs[:100]: print("GLYPH",g)
