#!/usr/bin/env python3
"""
用AI讲古 · 短视频 MCP Server
开源、无GPU、零成本 — 本地 TTS(edge-tts) + ffmpeg 合成 + 字幕烧录

启动: python3 shortvideo_mcp.py
MCP client 配置:
  {"mcpServers": {"shortvideo": {"command": "python3", "args": ["/path/to/shortvideo_mcp.py"]}}}
"""
import json, os, subprocess, sys, textwrap, asyncio, tempfile
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
OUTPUT_DIR  = os.path.join(BASE_DIR, "output")
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
os.makedirs(SCRIPTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR,  exist_ok=True)
os.makedirs(ASSETS_DIR,  exist_ok=True)

FONT  = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
VOICE = "zh-CN-YunyangNeural"  # 男声·专业·可靠

# 大脑(AGNES / Anthropic 兼容端点)—— 运行时注入
#   ANTHROPIC_API_KEY / AGNES_API_KEY  : 凭证
#   ANTHROPIC_BASE_URL / AGNES_BASE_URL : AGNES 网关地址
#   SV_MODEL                            : 模型名(默认 claude-sonnet-4-6)
AI_KEY      = os.environ.get("AGNES_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
AI_BASE_URL = os.environ.get("AGNES_BASE_URL") or os.environ.get("ANTHROPIC_BASE_URL") or None
AI_MODEL    = os.environ.get("SV_MODEL", "claude-sonnet-4-6")

# 素材库(占位符,先接上代码, 没 key 自动退回霓虹网格)
#   PEXELS_API_KEY / PIXABAY_API_KEY
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_KEY = os.environ.get("PIXABAY_API_KEY", "")
PEXELS_URL = "https://api.pexels.com/videos"
PIXABAY_URL = "https://pixabay.com/api/videos/"

# ── 核心工具函数(与 pipeline.py 对齐) ─────────────────────────────────────────

def _run(cmd, timeout=300):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"cmd failed (exit {r.returncode}):\n{r.stderr[-3000:]}")
    return r

def _build_srt(segments, per_dur, out):
    def ts(sec):
        h=int(sec//3600); m=int((sec%3600)//60); s=int(sec%60); ms=int((sec-int(sec))*1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    t=0; lines=[]
    for i,(seg,d) in enumerate(zip(segments, per_dur)):
        lines.append(f"{i+1}\n{ts(t)} --> {ts(t+d)}\n{textwrap.shorten(seg,20)}\n")
        t+=d
    open(out,"w").write("\n".join(lines))
    return out

def _render_scene(dur, workdir, idx):
    p = os.path.join(workdir, f"scene_{idx}.mp4")
    filt = (
        "color=c=0x0a0e1a:s=1080x1920:r=30,format=yuv420p,"
        "drawgrid=w=100:h=100:t=1:c=0x14315a@0.6,"
        "vignette=PI/3"
    )
    _run(["ffmpeg","-y","-f","lavfi","-i",filt,
         "-t",str(dur),"-c:v","libx264","-pix_fmt","yuv420p","-r","30",
         "-s","1080x1920", p], timeout=120)
    return p

def _tts(text, out_mp3, voice=VOICE):
    _run(["edge-tts","--voice",voice,"--text",text,"--write-media",out_mp3], timeout=120)
    return out_mp3

# ── 大脑:AGNES/Anthropic 自动生成脚本,无 key 走离线规则 fallback ──────────────

_SYS = (
    "你是'用AI讲古'短视频编剧。把古圣贤思想(AI时代生存操作系统)转成口播。\n"
    "硬性要求:①理性硬核,不贩卖焦虑、不做玄学承诺(禁用'改命/开光/消灾',改用'认知/方法/心学');\n"
    "②引用古语必须标注真实出处,不确定的不写;③口播 80-150 字、语速约4字/秒;④分镜6-8个、各3-5秒。"
)

def _gen_script_ai(topic, column, tone):
    """调用 AGNES(Anthropic 兼容)生成完整脚本 dict。无 key 时返回 None。"""
    if not AI_KEY:
        return None
    import anthropic
    client = anthropic.Anthropic(api_key=AI_KEY, base_url=AI_BASE_URL) if AI_BASE_URL \
        else anthropic.Anthropic(api_key=AI_KEY)
    user = (f"主题: {topic}\n栏目: {column}\n语调: {tone}\n"
            "请输出 JSON,字段: 口播/字幕分段/分镜[{画面,时长}]/标题候选[3]/封面文案/引文出处/引文校验")
    try:
        resp = client.messages.create(
            model=AI_MODEL, max_tokens=1500, system=_SYS,
            messages=[{"role":"user","content":user}])
        txt = "".join(b.text for b in resp.content if getattr(b,"type","")=="text")
        data = json.loads(txt[txt.find("{"):txt.rfind("}")+1])
        data.setdefault("标题候选", [])
        data.setdefault("分镜", [])
        data.setdefault("字幕分段", [])
        return data
    except Exception as e:
        return {"_error": str(e)[:200]}

def _gen_script_offline(topic, column, tone):
    """无 key 兜底:规则化骨架,可手动覆写。"""
    n = 7
    return {
        "id": None, "栏目": column,
        "标题候选": [f"{topic} · 换个角度读", f"{topic} · 一句入心", f"{topic} · 理性视角"],
        "封面文案": f"{topic} · 理性视角",
        "口播": f"关于{topic},多数人停在字面,停在情怀。但{tone}地看,它其实是AI时代的一套生存算法:{topic}给出的,不是答案,是'怎么看'的方法。真正稀缺的,不是信息,是你把它落到行动的那一下。先把{topic}想透,再做,心就定一分。",
        "字幕分段": [f"关于{topic},多数人停在字面", "停在情怀,没看穿底层逻辑",
                    f"{tone}地看,它是一套生存算法", f"{topic}给的不是答案,是方法",
                    "真正稀缺的,是把知落到行", "先把事想透,心就定一分"],
        "分镜": [{"画面": "黑场展开,古卷+数字粒子", "时长": 4},
                 {"画面": "书桌/专注特写", "时长": 4},
                 {"画面": "电路与文字叠加", "时长": 4},
                 {"画面": "眼瞳聚焦,粒子汇聚", "时长": 4},
                 {"画面": "果断落笔瞬间", "时长": 4},
                 {"画面": "古与未来并置", "时长": 4},
                 {"画面": "黑场,单光点定格", "时长": 4}],
        "引文出处": "待填写", "引文校验": "无AI生成,待人工核实古语",
        "_engine": "offline-fallback",
    }

def _gen_script(topic, column, tone):
    ai = _gen_script_ai(topic, column, tone)
    if ai and "_error" not in ai:
        ai["_engine"] = f"agnes/{AI_MODEL}"
        return ai
    off = _gen_script_offline(topic, column, tone)
    off["_engine"] = "offline-fallback"
    return off

# ── 素材库:Pexels/Pixabay,无 key 退回霓虹网格 ───────────────────────────────

def _fetch_assets(keywords, workdir):
    """按关键词拉免费 B-roll mp4。有 PEXELS_KEY/PIXABAY_KEY 才真拉;否则返回 []。"""
    if not (PEXELS_KEY or PIXABAY_KEY):
        return []
    import urllib.request, urllib.parse
    got = []
    for i, kw in enumerate(keywords[:3]):
        try:
            if PEXELS_KEY:
                u = f"{PEXELS_URL}?query={urllib.parse.quote(kw)}&per_page=1&size=medium"
                req = urllib.request.Request(u, headers={"Authorization": PEXELS_KEY})
                d = json.load(urllib.request.urlopen(req, timeout=20))
                url = d["videos"][0]["video_files"][0]["link"]
            elif PIXABAY_KEY:
                u = f"{PIXABAY_URL}?key={PIXABAY_KEY}&video_type=animation&min_width=720&{urllib.parse.urlencode({'q': kw})}"
                d = json.load(urllib.request.urlopen(u, timeout=20))
                url = d["hits"][0]["videos"]["small"]["url"]
            p = os.path.join(workdir, f"asset_{i}.mp4")
            urllib.request.urlretrieve(url, p)
            got.append(p)
        except Exception:
            continue
    return got

# ── MCP server ─────────────────────────────────────────────────────────────────

from mcp.server.mcpserver import MCPServer
mcp = MCPServer("shortvideo", instructions="用AI讲古 · 零成本短视频生成工具链")

@mcp.tool()
def write_script(topic: str, column: str = "觉醒·读古人", tone: str = "理性硬核") -> dict:
    """
    生成短视频完整脚本(口播/分镜/字幕/标题/封面文案),写入 scripts/ 目录。
    参数: topic=主题关键词, column=栏目名(主栏目/流量款/话题款), tone=语调
    返回: {id, path, 口播字数, 分镜数, 字幕段数}
    """
    import re
    safe_id = re.sub(r"[^a-z0-9一-鿿]+","_", topic.strip()) or "untitled"
    path = os.path.join(SCRIPTS_DIR, f"{safe_id}.json")
    if os.path.exists(path):
        return {"ok": False, "msg": f"已存在: {path}, 请先备份或删除", "id": safe_id}
    data = _gen_script(topic, column, tone)
    data["id"] = safe_id
    json.dump(data, open(path,"w"), ensure_ascii=False, indent=2)
    return {"ok": True, "id": safe_id, "path": path,
            "engine": data.get("_engine"),
            "msg": ("已用 AGNES 生成完整脚本" if data.get("_engine","").startswith("agnes")
                    else "AGNES key 未配置,已生成离线骨架,请覆写口播/分镜"),
            "compose_hint": f"填好后调用 compose_video('{safe_id}') 出成片"}

@mcp.tool()
def tts_voice(text: str, out: str = "", voice: str = VOICE) -> dict:
    """
    edge-tts 免费配音。voice 可选值:
      zh-CN-YunyangNeural (男声·专业·可靠, 默认)
      zh-CN-YunjianNeural (男声·激情)
      zh-CN-YunxiNeural   (男声·阳光)
      zh-CN-XiaoxiaoNeural(女声·温暖)
      zh-CN-YunxiaNeural  (男声·可爱/卡通)
    返回: {mp3路径, 字节数}
    """
    out = out or os.path.join(tempfile.gettempdir(), f"sv_tts_{os.getpid()}.mp3")
    _tts(text, out, voice)
    sz = os.path.getsize(out)
    return {"ok": True, "mp3": out, "bytes": sz, "voice": voice}

@mcp.tool()
def compose_video(script_id: str, voice: str = VOICE) -> dict:
    """
    从 scripts/<script_id>.json 一键合成完整短视频(画面+配音+字幕+封面)。
    返回: {mp4路径, 封面路径, 时长秒, 文件大小MB}
    """
    spath = os.path.join(SCRIPTS_DIR, f"{script_id}.json")
    if not os.path.exists(spath):
        return {"ok": False, "msg": f"找不到脚本: {spath}, 先调用 write_script"}
    data = json.load(open(spath))
    if not data.get("口播","").strip() or not data.get("分镜"):
        return {"ok": False, "msg": "脚本缺少 口播 或 分镜, 请先补充再调用"}

    workdir = os.path.join(ASSETS_DIR, script_id)
    os.makedirs(workdir, exist_ok=True)
    # 若没有字幕分段, 从分镜数 × 时长推算等宽
    scenes = data["分镜"]
    per_dur = [sc.get("时长",3) for sc in scenes]
    total = sum(per_dur)
    # 先跑 TTS 测时长
    mp3 = os.path.join(workdir,"voice.mp3")
    _tts(data["口播"], mp3, voice)
    dur_audio = float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",mp3],
        text=True).strip())
    scale = 1.0 if dur_audio <= total else dur_audio / total
    # 素材: 有 Pexels/Pixabay key 就拉真实 B-roll, 没有退回霓虹网格
    broll = _fetch_assets(data.get("免费素材关键词", []), workdir)
    vids = []
    for i, d in enumerate(per_dur):
        if broll:
            a = broll[i % len(broll)]
            _run(["ffmpeg","-y","-stream_loop","-1","-i",a,"-t",str(d),
                  "-vf","scale=1080:1920:force_original_aspect_ratio=increase,"
                       "crop=1080:1920,setsar=1","-c:v","libx264","-pix_fmt","yuv420p",
                  "-r","30","-an", os.path.join(workdir, f"scene_{i}.mp4")], timeout=120)
            vids.append(os.path.join(workdir, f"scene_{i}.mp4"))
        else:
            vids.append(_render_scene(d*scale, workdir, i))
    _assets_used = bool(broll)
    # 拼接
    listp = os.path.join(workdir,"list.txt")
    open(listp,"w").write("\n".join(f"file '{v}'" for v in vids))
    body = os.path.join(workdir,"body.mp4")
    _run(["ffmpeg","-y","-f","concat","-safe","0","-i",listp,"-c","copy",body], timeout=120)
    # 字幕
    srt = os.path.join(workdir,"sub.srt")
    # 从分镜或字幕分段生成
    srt_segs = data.get("字幕分段") or [f"[镜{sc.get('画面','')[:20]}]" for sc in scenes]
    srt_durs = [d*scale for d in per_dur]
    _build_srt(srt_segs, srt_durs, srt)
    srt_esc = srt.replace(":","\\:")
    out_mp4 = os.path.join(OUTPUT_DIR, f"{script_id}.mp4")
    _run([
        "ffmpeg","-y","-i",body,"-i",mp3,"-vf",
        f"subtitles={srt_esc}:fontsdir={FONT}:force_style="
        f"'FontName=Droid Sans Fallback,FontSize=15,FontColour=&H00FFFFFF,"
        f"OutlineColour=&H000a0e1a,Outline=2,MarginV=90,Alignment=2',"
        f"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-shortest",out_mp4
    ], timeout=300)
    # 封面
    cover = os.path.join(OUTPUT_DIR, f"{script_id}_cover.png")
    _run(["ffmpeg","-y","-ss",str(total*0.35),"-i",out_mp4,"-frames:v","1",cover], timeout=60)
    sz = os.path.getsize(out_mp4) / 1024 / 1024
    return {"ok": True, "mp4": out_mp4, "cover": cover,
            "duration_s": round(dur_audio,1), "size_mb": round(sz,1),
            "visual": "free-B-roll" if _assets_used else "neon-grid(fallback, 配 PEXELS/PIXABAY key 后自动升级)"}

@mcp.tool()
def list_scripts() -> list:
    """列出 scripts/ 目录下所有脚本 JSON 文件。"""
    return sorted(f[:-5] for f in os.listdir(SCRIPTS_DIR) if f.endswith(".json"))

if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
