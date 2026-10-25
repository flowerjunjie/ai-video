#!/usr/bin/env python3
"""
用AI讲古 · 短视频 MCP Server
开源、无GPU、零成本 — 本地 TTS(edge-tts) + ffmpeg 合成 + 字幕烧录

启动: python3 shortvideo_mcp.py
MCP client 配置:
  {"mcpServers": {"shortvideo": {"command": "python3", "args": ["/path/to/shortvideo_mcp.py"]}}}
"""
import json, os, re, subprocess, sys, textwrap, asyncio, tempfile, datetime, time
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载 .env(若存在, 只补缺失, 不覆盖已 set 的环境变量)
_ENV_FILE = os.path.join(BASE_DIR, ".env")
if os.path.exists(_ENV_FILE):
    for _ln in open(_ENV_FILE):
        _ln = _ln.strip()
        if _ln and not _ln.startswith("#") and "=" in _ln:
            _k, _v = _ln.split("=", 1)
            os.environ.setdefault(_k, _v)

SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
OUTPUT_DIR  = os.path.join(BASE_DIR, "output")
ASSETS_DIR  = os.path.join(BASE_DIR, "assets")
PUBLISH_DIR = os.path.join(BASE_DIR, "publish")
METRICS_DIR = os.path.join(BASE_DIR, "metrics")
os.makedirs(SCRIPTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR,  exist_ok=True)
os.makedirs(ASSETS_DIR,  exist_ok=True)
os.makedirs(PUBLISH_DIR, exist_ok=True)
os.makedirs(METRICS_DIR, exist_ok=True)

FONT  = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
# 默认换掉"新闻腔"YunyangNeural → YunjianNeural(激情·通透, 理性硬核不喊口号)。
# 换声: 设 SV_VOICE=zh-CN-YunxiNeural / zh-CN-YunjianNeural / zh-CN-XiaoxiaoNeural, 或 compose 时传 voice 参。
VOICE = os.environ.get("SV_VOICE", "zh-CN-YunjianNeural")  # 男声·激情·通透(默认, 比新闻腔生动)
# 去播音腔: 降速+降调造"慢热沉思"质感(有特色的声音, 非纯正播报)。全库存共享, 可用 env 覆盖。
TTS_RATE  = os.environ.get("SV_TTS_RATE",  "-15%")   # 慢热, 留白更足
TTS_PITCH = os.environ.get("SV_TTS_PITCH", "-10Hz")  # 低沉沉稳, 去新闻腔

# 大脑(AGNES OpenAI 兼容端点, 默认; Anthropic 兼容端点作 fallback)—— 运行时注入
#   AGNES_API_KEY / ANTHROPIC_API_KEY   : 凭证
#   AGNES_BASE_URL  (默认 https://apihub.agnes-ai.com/v1)
#   ANTHROPIC_BASE_URL
#   SV_MODEL  (默认 agnes-3.0-flash)   SV_PROVIDER (agnes|anthropic, 默认 auto)
AI_KEY        = os.environ.get("AGNES_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
AGNES_URL     = os.environ.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
ANTHRO_URL    = os.environ.get("ANTHROPIC_BASE_URL", "")
AI_MODEL      = os.environ.get("SV_MODEL", "agnes-3.0-flash")
SV_PROVIDER   = os.environ.get("SV_PROVIDER", "auto")  # auto: 有 AGNES_API_KEY 走 agnes, 否则 anthropic

# 素材库(占位符,先接上代码, 没 key 自动退回霓虹网格)
#   PEXELS_API_KEY / PIXABAY_API_KEY
PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "")
PIXABAY_KEY = os.environ.get("PIXABAY_API_KEY", "")
PEXELS_URL = "https://api.pexels.com/v1/search"

# ── 核心工具函数(与 pipeline.py 对齐) ─────────────────────────────────────────

def _run(cmd, timeout=300):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"cmd failed (exit {r.returncode}):\n{r.stderr[-3000:]}")
    return r

def _build_srt(segments, per_dur, out, cues=None):
    def ts(sec):
        h=int(sec//3600); m=int((sec%3600)//60); s=int(sec%60); ms=int((sec-int(sec))*1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    lines=[]
    if cues and len(cues) == len(segments):
        for i,(seg,(st,en)) in enumerate(zip(segments, cues)):
            lines.append(f"{i+1}\n{ts(st)} --> {ts(en)}\n{textwrap.shorten(seg,20)}\n")
    else:
        t=0
        for i,(seg,d) in enumerate(zip(segments, per_dur)):
            lines.append(f"{i+1}\n{ts(t)} --> {ts(t+d)}\n{textwrap.shorten(seg,20)}\n")
            t+=d
    open(out,"w").write("\n".join(lines))
    return out

def _build_ass(segments, chapters, total, out, font="Droid Sans Fallback", cues=None):
    """双行字幕: 顶部章节小字幕(古语/论点) + 底部口播逐句。
    segments=底部逐句, chapters=[(起始秒, 文案)] 顶部论点切换点。
    cues=[(start,end)] 与 segments 同序的逐句真实起止(TTS 时间戳);
    缺省 None 则回退等分。用 ASS 而非 srt, 因为只有 ASS 能同时烧两行且样式独立。"""
    def a_t(sec):
        # 标准 ASS H:MM:SS.CC — 秒与毫秒各自取模, 绝不让秒溢出 59.99
        h=int(sec//3600); m=int((sec%3600)//60); s=sec%60
        return f"{h}:{m:02d}:{s:05.2f}"
    script = [
        "[Script Info]",
        f"Title: 用AI讲古", "ScriptType: v4.00.000",
        "PlayResX: 1080", "PlayResY: 1920",
        "WrapStyle: 0", "ScaledBorderAndShadows: yes",
        "",
        "[V4+ Styles]",
        "Format: Style, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        # 底部逐句: 字号64(竖屏够看且不顶满), 距底MarginV=160
        # 顶部章节: 字号54金色标签, 加淡入淡出消除切换残影; 每段只闪现前3s后消失(降满屏密度)
        # 顶部行底缘≈100+54=154px; 底部行顶缘≈1920-160-64=1696px → 物理净距1542px, 顶底不撞
        # 你看到的"重叠"真实根因: ①章节标签全程不消失+底部逐句全程满=满屏密度 ②切换点新旧标签残影叠加
        f"Style: 底部,{font},64,&H00FFFFFF,&H00FFFFFF,&H000A0E1A,&H800A0E1A,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,160,1",
        f"Style: 顶部,{font},54,&H00E8C860,&H00FFFFFF,&H000A0E1A,&H800A0E1A,0,0,0,0,100,100,0,0,1,2,1,8,40,40,100,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    # 顶部章节行: 每段闪现前3s + 淡入淡出(\fad), 避免全程压顶+切换残影
    for (start, txt) in chapters:
        end = next((s for s, _ in chapters if s > start), total)
        flash_end = min(start + 3.0, end)  # 只闪现3s后消失
        script.append(f"Dialogue: 0,{a_t(start)},{a_t(flash_end)},顶部,,0,0,0,,{{\\fad(300,300)}}{txt}")
    # 底部逐句行: 优先用 TTS 逐句真实起止(cues), 让字幕跟配音走; 缺则等分兜底
    if cues and len(cues) == len(segments):
        for i, seg in enumerate(segments):
            st, en = cues[i]
            en = min(en, total)
            if en <= st: en = st + 0.1
            script.append(f"Dialogue: 1,{a_t(st)},{a_t(en)},底部,,0,0,0,,{textwrap.shorten(seg,18)}")
    else:
        t = 0.0
        seg_durs = [total/len(segments)]*len(segments) if segments else []
        for i, seg in enumerate(segments):
            d = seg_durs[i]
            script.append(f"Dialogue: 1,{a_t(t)},{a_t(t+d)},底部,,0,0,0,,{textwrap.shorten(seg,18)}")
            t += d
    open(out, "w").write("\n".join(script))
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

def _tts(text, out_mp3, voice=VOICE, rate="+0%", pitch="+0Hz", out_vtt=None):
    """edge-tts 免费配音。Bing 端点常对机房 IP 间歇 403 限流,
    重试 3 次、指数退避(2/4/8s), 末次失败才抛出。
    rate/pitch 可传 edge-tts 语调参, 默认不变; 全库存走 TTS_RATE/TTS_PITCH 环境变量。
    out_vtt: 给路径则同时落 VTT(逐句 word-boundary 时间戳), 供字幕对齐配音真实语速。"""
    last = None
    for i in range(3):
        try:
            cmd = ["edge-tts","--voice",voice,"--text",text,
                 f"--rate={rate}",f"--pitch={pitch}","--write-media",out_mp3]
            if out_vtt:
                cmd += ["--write-subtitles", out_vtt]
            _run(cmd, timeout=120)
            if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 0:
                return out_mp3
            last = RuntimeError("edge-tts 输出空文件")
        except Exception as e:
            last = e
        if i < 2:
            time.sleep([2,4,8][i])
    raise last or RuntimeError("edge-tts 连续 3 次失败, 可能被 Bing 限流")

def _vtt_ts(s):
    """edge-tts VTT 时间 '00:00:03,800' → 秒。"""
    m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)", s.strip())
    if not m:
        return float(s)
    return int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)) + int(m.group(4))/1000.0

def _vtt_cues(segments, vtt_path, total, n_segs):
    """逐句真实起止 [(start,end)]。
    核心: 按每段字幕的**字数权重**把配音总时长(=total)分配给各段 →
    每段时长按字数正比, 起点严格连续(前段 end = 后段 start), 跟配音语速走, 永不塌缩/重复。
    VTT 词块数常 < 段数, 故不用词块对齐, 改用字数权重(字数多→段长, 与 TTS 语速正相关)。
    若 total 未知/为 0 则按字数权重归一兜底。"""
    n = max(n_segs, len(segments))
    if total <= 0:
        total = n * 3.0
    # 每段权重 = 该段字数(空段给最小权重, 保证不 0 时长)
    weights = [max(len(s.replace(" ","")), 1) for s in segments]
    total_w = sum(weights)
    t = 0.0
    cues = []
    for i in range(n):
        if i < len(weights):
            w = weights[i]
        else:
            w = total_w / n  # 段数超 VTT 时均摊
        d = total * w / total_w
        cues.append((round(t,2), round(t+d,2)))
        t += d
    return cues[:n_segs]

# ── 大脑:AGNES/Anthropic 自动生成脚本,无 key 走离线规则 fallback ──────────────

_SYS = (
    "你是'用AI讲古'短视频首席编剧。把古圣贤思想(AI时代生存操作系统)转成有张力的口播,\n"
    "像一位通透又克制的前辈,不是念稿子、不是科普、不是喊口号。\n"
    "\n【硬性合规】理性硬核,不贩卖焦虑、不做玄学承诺(禁用'改命/开光/消灾/转运/灵验'),"
    "一切落到'认知/方法/心学/底层逻辑';引用古语必须标注真实出处与篇目,拿不准就写成"
    "'古人有句话,大意是…',绝不编造字句。\n"
    "\n【叙事弧——每条必须走完,这是深度的核心】\n"
    "  ①钩子(0-3s):抛一个反常识或扎心的一句,逼用户停下,绝不平铺主题;\n"
    "  ②冲突:点破大多数人停在字面/停在情怀,戳中真正的痛点或矛盾;\n"
    "  ③古语+出处:亮出古圣贤原话,标出处,建立权威;\n"
    "  ④案例/场景:落到一个具体的当代场景(刷手机/加班/低谷/AI对话),让古语'活'起来;\n"
    "  ⑤金句:一句可被截图转发、能扎心的话,全片记忆点;\n"
    "  ⑥行动:给一个可立即做的小事,不画饼、不给'听完就变'的假承诺。\n"
    "\n【爆火卖点·硬性要求】\n"
    "  - 反常识钩子: 开头一句必须先立一个'反直觉、扎心、颠覆常识'的判断, 逼用户 3 秒内停下来;"
    "  用'你以为的X, 其实是Y'或'大多数人以为… 但真相是…'这类认知落差句式, 绝不平铺直叙讲道理。\n"
    "  - 认知落差贯穿: 中段把'大众停在字面/停在情怀'的认知误区戳破, 制造'我确实被戳中了'的代入, 这是传播的前提。\n"
    "  - 可截图金句: ⑤的金句要短狠、有节奏、能被单独截图转发当文案, 优先用对仗/反转/扎心判断句,\n"
    "  避免'听完就变'式鸡汤; 一句话让人想@朋友。\n"
    "  - 结尾留传播记忆点: 行动指引给一个具体到'今晚就能做'的小事, 降低执行门槛, 强化'看完就能用'。\n"
    "\n【人设口吻】短句、留白、敢下判断;多用'你看/你有没有想过/其实';"
    "禁止'家人们/宝子/点赞关注'等平台腔,保持一个'清醒又温和'的讲古人前辈质感。\n"
)

# 时长档位: 决定口播字数预算 + 分镜数 + 论点层数(多论点纵深, 避免拉长变注水)
#   word: 目标口播字数, scenes: 分镜数, args: 几层"古语×案例"论证
_DUR_TIER = {
    "60-90s":  dict(words=(280,420),  scenes=(12,16), args=3,
                    label="单主线深挖: 主古语+1个交叉古语印证+当代案例, 三层递进不平铺"),
    "3min":    dict(words=(650,820),  scenes=(20,28), args=3,
                    label="多论点纵深: 主古语+1-2个交叉论证古语, 各配当代案例, 层层推进不重复"),
    "5min":    dict(words=(1000,1300),scenes=(30,42), args=3,
                    label="长纵深: 主古语+2-3个交叉古语+当代场景推演+反思升华, 完整弧线, 每层换新角度"),
}

def _spec_for(duration: str):
    """按时长档生成规格说明, 拼进 AGNES prompt, 让大脑按目标深度写(非注水)。"""
    t = _DUR_TIER.get(duration)
    if not t:
        return ""
    return ("\n【本次规格·目标时长 %s】口播 %d-%d 字、分镜 %d-%d 个(每镜 5-7s)、"
            "要点数 %d 层。结构: %s。"
            "每层必须换新古语/新案例, 不许换汤不换药; 字幕分段逐句贴合、每句≤14字; "
            "顶部章节小字幕(古语/论点)标出 %s 个论点。"
            % (duration, t["words"][0], t["words"][1], t["scenes"][0], t["scenes"][1],
               t["args"], t["label"], t["args"]))

def _provider():
    """auto: 有 AGNES_API_KEY 走 agnes(openai端点), 否则 anthropic。"""
    if os.environ.get("AGNES_API_KEY") or SV_PROVIDER in ("agnes","auto"):
        if os.environ.get("AGNES_API_KEY") and (SV_PROVIDER in ("agnes","auto") or not os.environ.get("ANTHROPIC_API_KEY")):
            return "agnes"
    return "anthropic"

def _gen_script_ai(topic, column, tone, duration: str = "60-90s"):
    """调用 AGNES(OpenAI 兼容,默认)或 Anthropic 生成完整脚本 dict。无 key 返回 None。"""
    if not AI_KEY:
        return None
    spec = _spec_for(duration)
    args_n = _DUR_TIER.get(duration, _DUR_TIER["60-90s"])["args"]
    # 关键词数量随档位递增: 短片6 / 3min8 / 5min10, 画面池化后多镜错用, 根治重复画面
    n_kw = {"60-90s": 6, "3min": 8, "5min": 10}.get(duration, 6)
    fields = ("钩子/冲突/古语/古语出处/当代案例/金句/行动指引/口播/字幕分段"
              f"/分镜[{{画面,时长}}]/标题候选[3]/封面文案/引文校验/免费素材关键词[{n_kw}](多写,覆盖叙事每个场景)")
    if args_n >= 2:
        fields += f"/章节字幕[{args_n}](每个论点一句顶部小字幕,含古语关键词)"
    user = (f"主题: {topic}\n栏目: {column}\n语调: {tone}\n"
            f"目标时长档位: {duration}\n"
            f"请只输出 JSON(无 markdown 代码块),字段:\n{fields}。\n"
            "口播必须是一条完整叙事(非要点罗列), 按目标字数写足;"
            "分镜对齐叙事逐镜推进; 字幕分段逐句贴合口播、每句≤14字。" + spec)
    prov = _provider()
    mtok = 6000 if duration == "5min" else (4000 if duration == "3min" else 2500)
    try:
        if prov == "agnes":
            import openai
            cli = openai.OpenAI(api_key=AI_KEY, base_url=AGNES_URL)
            r = cli.chat.completions.create(model=AI_MODEL, max_tokens=mtok,
                  messages=[{"role":"system","content":_SYS},
                            {"role":"user","content":user}])
            txt = r.choices[0].message.content or ""
        else:
            import anthropic
            cli = anthropic.Anthropic(api_key=AI_KEY, base_url=ANTHRO_URL or None)
            r = cli.messages.create(model=AI_MODEL, max_tokens=mtok, system=_SYS,
                  messages=[{"role":"user","content":user}])
            txt = "".join(b.text for b in r.content if getattr(b,"type","")=="text")
        txt = txt.strip().lstrip("`").rstrip("`")
        data = json.loads(txt[txt.find("{"):txt.rfind("}")+1])
        for k in ("标题候选","分镜","字幕分段"):
            data.setdefault(k, [])
        return data
    except Exception as e:
        return {"_error": str(e)[:200]}

def _gen_script_offline(topic, column, tone):
    """无 key 兜底:同样走六段式叙事骨架(钩子→冲突→古语→案例→金句→行动),
    比旧版有真实古语占位+可行动钩子,深度对齐 AGNES;标注为骨架待人工雕琢。"""
    kb = ("古人说,知者不惑。你被{t}绕进去,不是它太难,是你在用情绪答题,不是用脑子。"
          "AI能给你一万条建议,却没有一条是你自己'想透'的。"
          "别急着翻篇,先把{t}当成一道题慢慢拆——拆到心里那个'哦,原来如此',才算真懂。"
          "今天别求多,就做对跟{t}相关的一件小事。事上磨练,磨一磨,人就定一分。").format(t=topic)
    return {
        "id": None, "栏目": column,
        "钩子": f"你有没有觉得,关于{topic},你懂的道理,一件都做不到?",
        "冲突": "不是道理不对,是你停在'知道',没到'看清';停在情怀,没到方法。",
        "古语": "知者不惑 / 事上磨练(占位,需人工核实真实篇目出处)",
        "古语出处": "占位·需人工核实(离线骨架未连AI)",
        "当代案例": "你刷了十条关于{t}的视频,合上手机,该怎么做还是不知道——这就是停在字面.".format(t=topic),
        "金句": "真正稀缺的,不是信息,是你把知落到行的那一下。",
        "行动指引": "今天只做跟{t}相关的一件小事,做完再睡.".format(t=topic),
        "标题候选": [f"{topic} · 为什么懂了也做不到", f"{topic} · 别停在字面", f"{topic} · 一句入心"],
        "封面文案": f"{topic} · 理性视角",
        "口播": kb,
        "字幕分段": [f"关于{topic},你懂的道理", "一件都没做到吧", "不是道理错",
                    "是你停在'知道'", "知者不惑,是看清", "AI给不了你那一下",
                    f"把{topic}当道题拆", "拆到心里'哦'"],
        "分镜": [{"画面": "黑场,一行字砸出钩子", "时长": 5},
                 {"画面": "反复滑动手机的疲惫特写", "时长": 5},
                 {"画面": "古卷展开,数字粒子浮现", "时长": 5},
                 {"画面": "'知者不惑'四字逐字显现", "时长": 5},
                 {"画面": "书桌前独自拆解问题", "时长": 5},
                 {"画面": "电路与文字交叠", "时长": 5},
                 {"画面": "眼瞳聚焦,粒子汇聚", "时长": 5},
                 {"画面": "果断落笔/写下第一件事", "时长": 5},
                 {"画面": "古与未来并置", "时长": 5},
                 {"画面": "黑场,单光点定格金句", "时长": 5}],
        "引文校验": "离线骨架:古语为占位,发布前必须人工核实真实出处",
        "免费素材关键词": ["zen meditation", "study desk focus", "circuit board macro", "night window light"],
        "_engine": "offline-fallback(v2-六段式)",
    }

def _gen_script(topic, column, tone, duration: str = "60-90s"):
    ai = _gen_script_ai(topic, column, tone, duration)
    if ai and "_error" not in ai:
        ai["_engine"] = f"{_provider()}/{AI_MODEL}"
        ai["目标时长"] = duration
        return ai
    reason = (ai or {}).get("_error", "key 未配置")
    off = _gen_script_offline(topic, column, tone)
    off["_engine"] = "offline-fallback"
    off["_ai_error"] = reason
    off["目标时长"] = duration
    return off

def _polish_ai(data):
    """雕琢已有脚本的文案:把口播重写得更扎心(钩子更强/金句更狠/案例更具体),
    同步重写字幕分段与分镜画面。有 key 走 AGNES/Anthropic, 无 key 返回 None。"""
    if not AI_KEY:
        return None
    prov = _provider()
    old = json.dumps({k: data.get(k) for k in
        ("主题","口播","古语","当代案例","金句","行动指引") if data.get(k)},
        ensure_ascii=False)
    user = (f"这是'用AI讲古'一条视频现有脚本:\n{old}\n\n"
            "请只输出一版雕琢后的 JSON(无代码块),字段: "
            "口播/字幕分段/分镜[{画面,时长}]。\n"
            "要求:①保留原古语与出处不改;②把口播写成六段式(钩子→冲突→古语→案例→金句→行动),"
            "280-420字(宁多勿短, 深度优先, 对标60-90s成片)、短句有张力、去套话、每句都在'留人';"
            "③【爆火卖点】开头钩子必须先立一个反常识/扎心/认知落差判断(用'你以为的X, 其实是Y'句式), 逼用户停下;"
            "中段戳破大众认知误区制造'被戳中'代入;金句要短狠有节奏、能被截图转发当文案、让人想@朋友;"
            "行动给一个今晚就能做的具体小事;④金句单独一行要能脱离上下文成立;⑤分镜 12-16 个对齐六段,每镜5-7s;⑥字幕逐句贴合、每句≤14字。")
    sys_ = _SYS + "\n【本次任务】只在给定的古语/出处/案例/金句基础上雕琢口播表达,不新造古语。"
    try:
        if prov == "agnes":
            import openai
            cli = openai.OpenAI(api_key=AI_KEY, base_url=AGNES_URL)
            r = cli.chat.completions.create(model=AI_MODEL, max_tokens=2000,
                  messages=[{"role":"system","content":sys_},
                            {"role":"user","content":user}])
            txt = r.choices[0].message.content or ""
        else:
            import anthropic
            cli = anthropic.Anthropic(api_key=AI_KEY, base_url=ANTHRO_URL or None)
            r = cli.messages.create(model=AI_MODEL, max_tokens=2000, system=sys_,
                  messages=[{"role":"user","content":user}])
            txt = "".join(b.text for b in r.content if getattr(b,"type","")=="text")
        ptxt = txt.strip().lstrip("`").rstrip("`")
        p = json.loads(ptxt[ptxt.find("{"):ptxt.rfind("}")+1])
        got = {k: p[k] for k in ("口播","字幕分段","分镜") if k in p}
        if "口播" not in got:
            raise ValueError(f"AGNES 返回缺 口播 字段: keys={list(p.keys())[:8]}")
        return got
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {str(e)[:160]}"}

# ── 素材库:Pexels/Pixabay,无 key 退回霓虹网格 ───────────────────────────────

# 中文素材关键词 → 独立英文 Pexels 检索词映射(保证每镜 B-roll 画面不同)。
# Pexels 检索词必须是英文; 直接扔中文会 0 命中。同一主题词组映射到不同画面,
# 避免所有分镜塌成一张 "zen meditation" 呆板图。未命中映射的中文词退回一个
# 多样化英文词池, 仍保证多镜多样。
_ZH2EN = {
    "王阳明": "Wang Yangming statue contemplation",
    "阳明": "Wang Yangming statue contemplation",
    "王阳明雕像": "stone statue ancient scholar",
    "雕像": "stone statue ancient philosopher",
    "龙场": "misty mountain forest",
    "山": "misty mountain forest",
    "办公室": "empty office desk night",
    "办公室深夜加班": "person working office late night",
    "加班": "person working office late night",
    "深夜": "city street night neon",
    "大脑": "human brain anatomy",
    "大脑解剖图": "human brain anatomy diagram",
    "大脑解剖": "human brain anatomy diagram",
    "雨夜": "rainy street night neon",
    "雨夜街头": "rainy street night neon",
    "雨": "rainy street night neon",
    "街头": "city street night",
    "禅": "zen meditation",
    "冥想": "zen meditation calm",
    "冥想打坐": "meditation silhouette calm",
    "打坐": "meditation silhouette calm",
    "庄子": "ancient Chinese philosophy scroll",
    "逍遥游": "ancient Chinese philosophy scroll",
    "鱼": "koi fish pond zen",
    "蝴蝶": "butterfly closeup",
    "河": "calm river forest",
    "道": "ink calligraphy landscape",
    "水": "flowing water calm",
    "山间": "misty mountain forest",
    "竹林": "bamboo forest mist",
    "大鹏鸟": "majestic eagle flying above clouds",
    "大鹏": "majestic eagle flying above clouds",
    "鹏": "majestic eagle flying above clouds",
    "大鹏鸟CG": "majestic eagle flying above clouds",
    "办公室加班": "person working office late night",
    "手机": "person staring phone screen dark",
    "手机屏幕": "person staring phone screen dark",
    "手机刷屏": "person staring phone screen dark",
    "镜子": "mirror reflection person",
    "镜子倒影": "mirror reflection person",
    "倒影": "calm water reflection",
    "古代书籍": "ancient chinese book scroll",
    "古书": "ancient chinese book scroll",
    "书籍": "ancient chinese book scroll",
    "书籍特写": "ancient chinese book scroll closeup",
    "古代书籍特写": "ancient chinese book scroll closeup",
    "火焰": "fire particles abstract",
    "火焰粒子": "fire particles abstract",
    "抽象火焰": "fire particles abstract",
    "抽象火焰粒子动画": "fire particles abstract",
    "城市人群": "city crowd silhouette black white",
    "城市剪影": "city crowd silhouette black white",
    "城市人群黑白剪影": "city crowd silhouette black white",
    "人群剪影": "crowd silhouette",
    "自然空镜": "calm forest light sunbeams",
    "树": "sunlight through forest trees",
    "树的光": "sunlight through forest trees",
    "安静自然": "calm nature stillness",
    "安静自然空镜（树/光）": "sunlight through forest trees",
}
# 兜底多样化英文词池(映射未命中时按序取, 仍不同画面)
_FALLBACK_EN = [
    "ancient chinese philosophy", "zen meditation calm",
    "misty mountain forest", "ink calligraphy landscape",
    "human brain concept", "person working late night office",
]

def _fetch_images(keywords, workdir):
    """按关键词拉 Pexels 免费图片(curl 实现, 避免 urllib 代理问题)。
    每个关键词独立映射到英文检索词, 保证多镜画面不重复; 未命中走兜底池。
    返回 [(关键词, 图片路径), ...]; 无 key 或拉取失败返回 []。"""
    if not PEXELS_KEY:
        return []
    import shlex, urllib.parse
    got = []
    seen_en = set()   # 去重: 已用过的英文检索词不再重复, 逼画面多样化
    fb_i = 0
    for i, kw in enumerate(keywords[:8]):
        try:
            q = _ZH2EN.get(str(kw).strip(), "").strip()
            if not q:
                # 中文未映射 → 兜底池下一个词; 仍去重避免同图
                while fb_i < len(_FALLBACK_EN) and _FALLBACK_EN[fb_i] in seen_en:
                    fb_i += 1
                q = _FALLBACK_EN[fb_i % len(_FALLBACK_EN)] if fb_i < len(_FALLBACK_EN) else f"philosophy calm {i}"
                fb_i += 1
            elif q in seen_en:
                # 映射命中但英文词已用过 → 直接跳过, 别重复同图
                continue
            seen_en.add(q)
            qenc = urllib.parse.quote(q)
            # per_page=4: 同关键词拉多张, 池化后多镜错用, 根治"重复画面"
            api = ["curl", "-s", "--max-time", "20",
                  f"https://api.pexels.com/v1/search?query={qenc}&per_page=4",
                  "-H", f"Authorization: {PEXELS_KEY}"]
            out = subprocess.run(api, capture_output=True, text=True, timeout=25).stdout
            photos = json.loads(out).get("photos", [])
            if not photos:
                continue
            # 每张独立下载, 命名 img_{i}_{j}.jpg, 全部入池
            for j, ph in enumerate(photos):
                s = ph.get("src", {})
                url = (s.get("large2x") if isinstance(s, dict) else None) or \
                      (s.get("large") if isinstance(s, dict) else None) or \
                      ph.get("url") or ""
                if not url:
                    continue
                p = os.path.join(workdir, f"img_{i}_{j}.jpg")
                dl = ["curl", "-s", "-L", "--max-time", "30", "-o", p,
                      "-H", "User-Agent: Mozilla/5.0", url]
                subprocess.run(dl, timeout=35)
                if os.path.getsize(p) > 1000:
                    got.append((kw, p))
        except Exception:
            continue
    return got

def _xfade_concat(vids, out, fade=0.5):
    """段间 0.5s 交叉溶解(爆款顺滑感)。段数>12 时回退硬切 concat 防重编码超时。
    每接一段总时长减 fade, 最终片长 = Σdur - (n-1)*fade。"""
    n = len(vids)
    if n <= 1:
        _run(["ffmpeg","-y","-i",vids[0],"-c","copy",out], timeout=120)
        return
    # 重片(>7段)全量 xfade 重编码 1080x1920 代价大且易超时 → 硬切兜底
    if n > 7:
        listp = out + ".list.txt"
        open(listp,"w").write("\n".join(f"file '{v}'" for v in vids))
        _run(["ffmpeg","-y","-f","concat","-safe","0","-i",listp,"-c","copy",out], timeout=300)
        return
    inputs = []
    for v in vids:
        inputs += ["-i", v]
    # 逐段时长(秒), xfade offset 需累加: off_i = Σdur[0..i] - i*fade
    durs = []
    for v in vids:
        durs.append(float(subprocess.check_output(
            ["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",v],
            text=True).strip()))
    # 链式 xfade: step1 → [v1], step2: [v1]+[2:v] → [v2], ... 中间标签 vN, 末段 → [vout]
    parts = []
    off = durs[0] - fade
    parts.append(f"[0:v][1:v]xfade=transition=fade:duration={fade}:offset={off:.2f}[v1]")
    for i in range(2, n):
        off = off + durs[i-1] - fade
        tail = "[vout]" if i == n-1 else f"[v{i}]"
        parts.append(f"[v{i-1}][{i}:v]xfade=transition=fade:duration={fade}:offset={off:.2f}{tail}")
    vf = ";".join(parts)
    _run(["ffmpeg","-y"] + inputs + ["-filter_complex", vf,
          "-map","[vout]","-an","-c:v","libx264","-pix_fmt","yuv420p","-r","30", out],
         timeout=600)

def _image_to_kenburns(img, dur, out, timeout=300):
    """图片 + 缓慢缩放平移(Ken Burns)→ 9:16 视频, 真实画面质感。单镜≤8s, 超长由调用方切段。"""
    _run(["ffmpeg","-y","-loop","1","-i",img,"-t",str(dur),
          "-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
               "zoompan=z='1.05+0.04*in':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
               f"d={max(1,int(dur*30))}:s=1080x1920:fps=30,format=yuv420p",
          "-c:v","libx264","-pix_fmt","yuv420p","-r","30","-an", out], timeout=timeout)
    return out

# ── 合规 + 回流选题 ───────────────────────────────────────────────────────────

_BANNED = ["改命","开光","消灾","招财","转运","祖荫","灵验","包治","根治","神效"]

def _check_banned(text: str):
    """合规护栏: 命中禁词即返回(防玄学承诺/贩卖焦虑), 供发布物料逐条校验。"""
    hits = [w for w in _BANNED if w in text]
    return {"命中": hits, "通过": not hits}

def _suggest_topics_ai(rows, n):
    """用 AGNES/Anthropic 读回流数据, 出下一批 n 个高潜选题。无 key/失败返回 None。"""
    if not AI_KEY:
        return None
    hot = sorted(rows, key=lambda r: r.get("完播率",0), reverse=True)
    brief = "\n".join(f"- {r['id']}: 完播{r.get('完播率',0)}% 播放{r.get('播放',0)}" for r in hot[:10])
    user = (f"已有数据回流:\n{brief}\n\n"
            f"完播率高的题材请深耕换角度, 完播低的规避。"
            f"给我 {n} 个下一批短视频选题(仍属'用AI讲古·释道儒/王阳明×AI认知'定位),"
            "每个一行, 只输出 选题1 / 选题2 ... (无编号无解释), 理性硬核、不卖焦虑。")
    prov = _provider()
    try:
        import re
        if prov == "agnes":
            import openai
            cli = openai.OpenAI(api_key=AI_KEY, base_url=AGNES_URL)
            r = cli.chat.completions.create(model=AI_MODEL, max_tokens=400,
                  messages=[{"role":"system","content":"你是'用AI讲古'选题策略师, 只输出选题列表。"},
                            {"role":"user","content":user}])
            txt = r.choices[0].message.content or ""
        else:
            import anthropic
            cli = anthropic.Anthropic(api_key=AI_KEY, base_url=ANTHRO_URL or None)
            r = cli.messages.create(model=AI_MODEL, max_tokens=400,
                  system="你是'用AI讲古'选题策略师, 只输出选题列表。",
                  messages=[{"role":"user","content":user}])
            txt = "".join(b.text for b in r.content if getattr(b,"type","")=="text")
        topics = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        topics = [re.sub(r"^\d+[\.、\s]*|选题\d*[:：]?\s*", "", t).strip() for t in topics]
        topics = [t for t in topics if t][:n]
        return topics or None
    except Exception:
        return None

# ── MCP server ─────────────────────────────────────────────────────────────────

from mcp.server.mcpserver import MCPServer
mcp = MCPServer("shortvideo", instructions="用AI讲古 · 零成本短视频生成工具链")

@mcp.tool()
def write_script(topic: str, column: str = "觉醒·读古人", tone: str = "理性硬核",
                 force: bool = False, duration: str = "60-90s") -> dict:
    """
    生成短视频完整脚本(六段式深度:钩子/冲突/古语/案例/金句/行动),写入 scripts/ 目录。
    参数: topic=主题关键词, column=栏目名, tone=语调,
          force=若同 id 已存在, 是否强制用新脚本覆盖(重做存量时设 True),
          duration=时长档位: "60-90s"(单论点)/ "3min"(多论点,~700字)/ "5min"(长纵深,~1100字)
    返回: {id, path, 口播字数, 分镜数, 字幕段数, 目标时长}
    """
    import re
    if duration not in _DUR_TIER:
        duration = "60-90s"
    safe_id = re.sub(r"[^a-z0-9一-鿿]+","_", topic.strip()) or "untitled"
    path = os.path.join(SCRIPTS_DIR, f"{safe_id}.json")
    existed = os.path.exists(path)
    if existed and not force:
        return {"ok": False, "msg": f"已存在: {path}, 用 force=True 覆盖重做, 或换主题", "id": safe_id}
    data = _gen_script(topic, column, tone, duration)
    data["id"] = safe_id
    # 护栏: 清洗分镜时长 — AGNES 偶尔返回 "5s"/"3.5s" 等字符串, 强制转 float
    for sc in data.get("分镜", []):
        v = sc.get("时长", 3)
        try:
            sc["时长"] = float(str(v).rstrip("s").strip() or 3)
        except (ValueError, TypeError):
            sc["时长"] = 3.0
    json.dump(data, open(path,"w"), ensure_ascii=False, indent=2)
    eng = data.get("_engine", "")
    return {"ok": True, "id": safe_id, "path": path,
            "overwritten": existed,
            "engine": eng or "unknown",
            "ai_error": data.get("_ai_error"),
            "口播字数": len(data.get("口播","")), "分镜数": len(data.get("分镜",[])),
            "目标时长": duration,
            "msg": ("已用 AGNES 生成深度脚本" if eng.startswith("agnes")
                    else f"AGNES 未生效({data.get('_ai_error','key 未配置')}),已生成六段式离线骨架"),
            "compose_hint": f"调用 compose_video('{safe_id}') 出成片"}

@mcp.tool()
def tts_voice(text: str, out: str = "", voice: str = VOICE) -> dict:
    """
    edge-tts 免费配音。voice 可选值(默认 zh-CN-YunjianNeural, 激情通透, 比新闻腔生动):
      zh-CN-YunjianNeural (男声·激情, 默认/最生动)
      zh-CN-YunxiNeural   (男声·阳光·从容)
      zh-CN-YunyangNeural (男声·专业·可靠, 偏新闻腔)
      zh-CN-XiaoxiaoNeural(女声·温暖)
      zh-CN-YunxiaNeural  (男声·可爱/卡通)
    返回: {mp3路径, 字节数, voice}
    """
    out = out or os.path.join(tempfile.gettempdir(), f"sv_tts_{os.getpid()}.mp3")
    _tts(text, out, voice, rate=TTS_RATE, pitch=TTS_PITCH)
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
    # 强制转为 float: AGNES 偶尔把"时长"返回成 "5s"/"5 sec" 字符串, 防 compose 崩
    def _dur_of(sc):
        try:
            return float(str(sc.get("时长", 3)).split()[0].rstrip("sec ").strip() or 3)
        except (ValueError, IndexError):
            return 3.0
    per_dur = [_dur_of(sc) for sc in scenes]
    total = sum(per_dur)
    # 先跑 TTS 测时长 + 落 VTT 逐句时间戳(供字幕对齐配音真实语速)
    mp3 = os.path.join(workdir,"voice.mp3")
    vtt = os.path.join(workdir,"voice.vtt")
    _tts(data["口播"], mp3, voice, rate=TTS_RATE, pitch=TTS_PITCH, out_vtt=vtt)
    dur_audio = float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",mp3],
        text=True).strip())
    scale = 1.0 if dur_audio <= total else dur_audio / total
    # 目标时长地板: 3min/5min 档强推下限(150/270s, 不足补拍尾镜保证纵深);
    # 60-90s 短脚本档地板取配音实际时长(不足不强推60s, 避免尾部静默过冲)
    _TIER = data.get("目标时长", "60-90s")
    _FLOOR = {"3min": 150, "5min": 270}
    if os.environ.get("SV_MIN_DUR"):
        TARGET_FLOOR = float(os.environ["SV_MIN_DUR"])
    elif _TIER in _FLOOR:
        TARGET_FLOOR = _FLOOR[_TIER]
    else:
        TARGET_FLOOR = dur_audio  # 短脚本档: 跟配音走, 画面=配音时长, 无静默
    if scale * total < TARGET_FLOOR:
        extra_scaled = TARGET_FLOOR - scale * total      # 还差多少秒
        per_dur[-1] = per_dur[-1] + extra_scaled / scale # 补回未缩放镜长
    # 素材: 有 Pexels key 就拉真实图片做 Ken Burns B-roll, 没有退回霓虹网格
    imgs = _fetch_images(data.get("免费素材关键词", []), workdir)
    vids = []
    MAX_CLIP = 8.0  # 单镜画面≤8s, 超长按同素材切段, 避免长镜 KenBurns 超时
    ci = 0
    for i, d in enumerate(per_dur):
        target = d * scale
        if target > MAX_CLIP + 1e-6:
            # 切成多段 ≤8s, 同素材错序循环, 保证画面不重复呆板
            n = int(max(1, round(target / MAX_CLIP)))
            seg = target / n
            for k in range(n):
                if imgs:
                    kw, ip = imgs[(i*3 + k) % len(imgs)]
                    _image_to_kenburns(ip, seg, os.path.join(workdir, f"scene_{ci}.mp4"))
                else:
                    _render_scene(seg, workdir, ci)
                vids.append(os.path.join(workdir, f"scene_{ci}.mp4"))
                ci += 1
        else:
            if imgs:
                kw, ip = imgs[i % len(imgs)]
                _image_to_kenburns(ip, target, os.path.join(workdir, f"scene_{ci}.mp4"))
            else:
                _render_scene(target, workdir, ci)
            vids.append(os.path.join(workdir, f"scene_{ci}.mp4"))
            ci += 1
    _assets_used = bool(imgs)
    # 拼接: 段间 0.5s 交叉溶解(爆款顺滑感); 段数>12 的重片内部自动回退硬切防超时
    body = os.path.join(workdir,"body.mp4")
    _xfade_concat(vids, body, fade=0.5)
    # 字幕: 有"章节字幕"(多论点)走双行 ASS(顶部古语章节 + 底部口播), 否则单行 srt
    chapters = data.get("章节字幕") or []
    srt_segs = data.get("字幕分段") or [f"[镜{sc.get('画面','')[:20]}]" for sc in scenes]
    srt_durs = [d*scale for d in per_dur]
    real_total = total * scale
    # 逐句真实起止(TTS 时间戳), 字幕跟配音走; 缺则 _build_* 内部等分兜底
    cues = _vtt_cues(srt_segs, vtt, real_total, len(srt_segs))
    sub_opts = ""
    if chapters:
        # 章节按等分对齐到论点切换时刻
        ch_n = len(chapters)
        step = real_total / ch_n
        chapters_aligned = [(round(i*step,1), textwrap.shorten(c,14)) for i,c in enumerate(chapters)]
        ass = os.path.join(workdir,"sub.ass")
        _build_ass(srt_segs, chapters_aligned, real_total, ass, cues=cues)
        sub_opts = "ass=" + ass.replace(":","\\:")
    else:
        srt = os.path.join(workdir,"sub.srt")
        _build_srt(srt_segs, srt_durs, srt, cues=cues)
        srt_esc = srt.replace(":","\\:")
        sub_opts = ("subtitles=" + srt_esc + ":"
                    f"fontsdir={FONT}:force_style="
                    "'FontName=Droid Sans Fallback,FontSize=32,FontColour=&H00FFFFFF,"
                    "OutlineColour=&H000a0e1a,Outline=2,MarginV=160,Alignment=2'")
    out_mp4 = os.path.join(OUTPUT_DIR, f"{script_id}.mp4")
    # ── BGM: 优先真实音乐(用户放的素材或 SV_BGM 环境变量), 缺失则合成可听垫音 ──
    # 真实音乐来源优先级: assets/bgm/<id>.m4a|mp3|wav → env SV_BGM → 合成
    bgm_src = None
    _BGM_DIR = os.path.join(ASSETS_DIR, "bgm")
    for _ext in ("m4a","mp3","wav","flac","ogg"):
        _p = os.path.join(_BGM_DIR, f"{script_id}.{_ext}")
        if os.path.exists(_p): bgm_src = _p; break
    if bgm_src is None and os.environ.get("SV_BGM"):
        bgm_src = os.environ["SV_BGM"]
    bgm = os.path.join(workdir, "bgm.wav")
    if bgm_src:
        # 真实音乐: 循环填满配音时长 + 响度压到 -20 LUFS(低于配音 -16, 不抢人声)
        _run(["ffmpeg","-y","-stream_loop","-1","-i",bgm_src,
              "-t",f"{real_total:.1f}","-af","loudnorm=I=-20:TP=-3,afade=t=in:st=0:d=2,afade=t=out:st={max(0,real_total-2.5):.1f}:d=2.5",
              "-ac","2","-ar","44100",bgm], timeout=120)
    else:
        # 合成可听垫音: 三音和弦 + 慢 LFO + 限幅归一到 -18dB(垫底可闻不抢人声)
        _run(["ffmpeg","-y",
              "-f","lavfi","-i",f"sine=frequency=66:duration={real_total:.1f}",
              "-f","lavfi","-i",f"sine=frequency=99:duration={real_total:.1f}",
              "-f","lavfi","-i",f"sine=frequency=132:duration={real_total:.1f}",
              "-filter_complex",
              "[0]volume=1.0[t0];[1]volume=0.6[t1];[2]volume=0.3[t2];"
              "[t0][t1]amix=inputs=2:normalize=0[m1];[m1][t2]amix=inputs=2:normalize=0[m2];"
              f"[m2]tremolo=f=0.25:d=0.4,volume=8,aecho=0.8:0.7:400:0.3,"
              f"loudnorm=I=-18:TP=-3,afade=t=in:st=0:d=2,afade=t=out:st={max(0,real_total-2.5):.1f}:d=2.5[out]",
              "-map","[out]","-ac","2","-ar","44100",bgm], timeout=120)
    _run([
        "ffmpeg","-y","-i",body,"-i",mp3,"-i",bgm,"-vf",
        f"{sub_opts},"
        f"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1",
        # 音频: 配音(主, -16 LUFS) + BGM衬底(副, 合成 0.7 / 真实 1.0) 混音, 总响度 -16 LUFS
        "-filter_complex",
        f"[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[voc];"
        f"[2:a]volume={'1.0' if bgm_src else '0.7'}[bg];"
        f"[voc][bg]amix=inputs=2:duration=first:normalize=0[mix];"
        f"[mix]loudnorm=I=-16:TP=-1.5[L]",
        "-map","0:v","-map","[L]","-c:v","libx264","-preset","veryfast","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","192k","-t", f"{real_total:.1f}",
        out_mp4
    ], timeout=900)
    # 封面
    cover = os.path.join(OUTPUT_DIR, f"{script_id}_cover.png")
    _run(["ffmpeg","-y","-ss",str(total*0.35),"-i",out_mp4,"-frames:v","1",cover], timeout=60)
    sz = os.path.getsize(out_mp4) / 1024 / 1024
    # 成片真实时长(含补拍尾镜), 而非仅音频时长
    dur_video = float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",out_mp4],
        text=True).strip())
    return {"ok": True, "mp4": out_mp4, "cover": cover,
            "duration_s": round(dur_video,1), "audio_s": round(dur_audio,1),
            "size_mb": round(sz,1),
            "visual": "free-B-roll" if _assets_used else "neon-grid(fallback, 配 PEXELS/PIXABAY key 后自动升级)"}

@mcp.tool()
def polish_script(script_id: str) -> dict:
    """
    雕琢已有脚本的文案:把口播重写为六段式(钩子→冲突→古语→案例→金句→行动),
    去套话、加张力、留人,同步刷新字幕分段与分镜画面。古语/出处保持不变。
    需要 AGNES/Anthropic key; 无 key 时返回离线提示(不硬改)。
    返回: {脚本路径, 旧字数, 新字数, 新分镜数, 引擎, 新口播}
    """
    spath = os.path.join(SCRIPTS_DIR, f"{script_id}.json")
    if not os.path.exists(spath):
        return {"ok": False, "msg": f"找不到脚本: {spath}"}
    data = json.load(open(spath))
    old = data.get("口播", "")
    polished = _polish_ai(data)
    if not polished or (isinstance(polished, dict) and "_error" in polished):
        err = polished.get("_error") if isinstance(polished, dict) else "key 未配置"
        return {"ok": False, "engine_error": err,
                "msg": f"雕琢未生效({err})。可人工改 scripts/{script_id}.json 的 口播/字幕分段/分镜, 再 compose_video。",
                "旧口播": old}
    data.update(polished)
    data["_polished"] = True
    data["_polish_engine"] = f"{_provider()}/{AI_MODEL}"
    json.dump(data, open(spath, "w"), ensure_ascii=False, indent=2)
    return {"ok": True, "path": spath, "id": script_id,
            "旧字数": len(old), "新字数": len(data.get("口播","")),
            "新分镜数": len(data.get("分镜",[])),
            "引擎": data.get("_polish_engine"),
            "新口播": data.get("口播",""),
            "下一步": f"compose_video('{script_id}') 重出成片"}

@mcp.tool()
def prepare_publish(ids, platform: str = "抖音", schedule: str = "今天 18:00") -> dict:
    """
    半自动发布:从 scripts/<id>.json + output/<id>.* 生成各平台发布物料包(标题/封面/标签/合规/AI标注),
    输出 publish/发布计划.json + 可复制文案。不直接调平台 API(个人号无企业发布资质),
    物料齐了人一键粘贴/上传即可。
    参数: ids=脚本id列表(或 "all"), platform=抖音/视频号/B站, schedule=建议发布时间
    返回: {发布计划路径, 物料条数, 各条摘要}
    """
    import re
    all_ids = list_scripts()
    if ids in ("all", "*", None):
        ids = all_ids
    elif isinstance(ids, str):
        ids = [s.strip() for s in re.split(r"[,\s]+", ids) if s.strip()]
    plan = []
    for sid in ids:
        spath = os.path.join(SCRIPTS_DIR, f"{sid}.json")
        if not os.path.exists(spath):
            plan.append({"id": sid, "ok": False, "msg": "脚本不存在"}); continue
        d = json.load(open(spath))
        titles = d.get("标题候选") or []
        cover_text = d.get("封面文案", "")
        kw = d.get("免费素材关键词") or []
        mp4 = os.path.join(OUTPUT_DIR, f"{sid}.mp4")
        cover = os.path.join(OUTPUT_DIR, f"{sid}_cover.png")
        tags = [d.get("栏目", "用AI讲古"), "王阳明", "认知", "哲学", "成长",
                *kw[:3]]
        plan.append({
            "id": sid, "ok": True,
            "平台": platform, "排期": schedule,
            "标题": (titles[0] if titles else f"{sid} · 换个角度读"),
            "标题备选": titles[1:],
            "封面文案": cover_text,
            "标签": ["#" + t for t in tags],
            "标签串": " ".join("#" + t for t in tags),
            "正文字案": d.get("口播", "")[:120],
            "合规标注": "内容由 AI 生成(依据各平台 AI 内容披露规则)",
            "禁用语检查": _check_banned(d.get("口播", "") + " " + " ".join(titles)),
            "成片": mp4 if os.path.exists(mp4) else "(未合成,先 compose_video)",
            "封面": cover if os.path.exists(cover) else "(未合成)",
        })
    outp = os.path.join(PUBLISH_DIR, "发布计划.json")
    json.dump({"platform": platform, "schedule": schedule,
               "生成时间": datetime.datetime.now().isoformat(timespec="seconds"),
               "物料": plan}, open(outp, "w"), ensure_ascii=False, indent=2)
    # 可复制文本(逐条 标题+标签+AI标注), 人工粘贴用
    copyp = os.path.join(PUBLISH_DIR, "复制文案.txt")
    with open(copyp, "w") as f:
        for m in plan:
            if m.get("ok"):
                f.write(f"[{m['id']}] {m['标题']}\n{m['标签串']}\n{m['合规标注']}\n\n")
    return {"ok": True, "plan_path": outp, "copy_path": copyp,
            "count": len(plan),
            "summary": [{"id": m["id"], "ok": m.get("ok"),
                         "title": m.get("标题"),
                         "违规": m.get("禁用语检查")} for m in plan]}

@mcp.tool()
def import_metrics(metrics: list, source: str = "手动复制") -> dict:
    """
    手动导入各平台数据回流:把(人工)复制下来的 播放/完播率/点赞/评论/转发
    结构化落盘到 metrics/, 供 auto_next_topics 分析。零 API 依赖。
    参数: metrics=[{id, 平台, 播放, 完播率(%), 点赞, 评论, 转发}, ...]
    返回: {落盘路径, 条数, 平均完播率, 数据最好/最差的 id}
    """
    import datetime, statistics
    if isinstance(metrics, str):
        metrics = json.loads(metrics)
    rows = []
    for m in metrics:
        row = {"id": m.get("id", ""), "平台": m.get("平台", "抖音"),
               "播放": int(m.get("播放", 0)),
               "完播率": float(m.get("完播率", 0)),
               "点赞": int(m.get("点赞", 0)),
               "评论": int(m.get("评论", 0)),
               "转发": int(m.get("转发", 0))}
        # 交互率 = (赞+评+转)/播放, 衡量内容钩子强度
        row["交互率"] = round((row["点赞"]+row["评论"]+row["转发"])/row["播放"], 4) if row["播放"] else 0
        # 关联脚本标题, 便于回流归因
        spath = os.path.join(SCRIPTS_DIR, f"{row['id']}.json")
        if os.path.exists(spath):
            row["栏目"] = json.load(open(spath)).get("栏目", "")
        rows.append(row)
    outp = os.path.join(METRICS_DIR, f"回流_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    json.dump({"source": source, "rows": rows}, open(outp, "w"), ensure_ascii=False, indent=2)
    # 同步一份"最新"快照, 供 auto_next_topics 直接读
    latest = os.path.join(METRICS_DIR, "最新回流.json")
    json.dump(rows, open(latest, "w"), ensure_ascii=False, indent=2)
    com = [r["完播率"] for r in rows if r["完播率"]] or [0]
    best = max(rows, key=lambda r: r["完播率"]) if rows else None
    worst = min(rows, key=lambda r: r["完播率"]) if rows else None
    return {"ok": True, "path": outp, "latest": latest, "count": len(rows),
            "avg完播率": round(statistics.mean(com), 1),
            "最好": (best["id"] if best else None, best["完播率"] if best else 0),
            "最差": (worst["id"] if worst else None, worst["完播率"] if worst else 0)}

@mcp.tool()
def auto_next_topics(n: int = 5) -> dict:
    """
    数据回流闭环的大脑:读 metrics/最新回流.json, 用 AGNES 分析哪类题材完播高,
    生成下批 n 个选题并直接写进 scripts/(喂回 write_script), 完成"发→收→学→再产"。
    无回流数据/无 key 时返回引导, 不硬造。
    返回: {分析结论, 新选题脚本路径列表, 引擎}
    """
    latest = os.path.join(METRICS_DIR, "最新回流.json")
    if not os.path.exists(latest):
        return {"ok": False, "msg": "尚无回流数据, 先 import_metrics 导入一期数据"}
    rows = json.load(open(latest))
    if not rows:
        return {"ok": False, "msg": "回流为空"}
    rank = sorted(rows, key=lambda r: r.get("完播率", 0), reverse=True)
    top_ids = [r["id"] for r in rank[:3]]
    # 低完播 = 尾部且不与头部重叠(小样本下防止"最高=最低"的假象)
    low = [r["id"] for r in reversed(rank[-3:])]
    low = [x for x in low if x not in top_ids] or ([rank[-1]["id"]] if len(rows) > 1 else [])
    insight = {
        "高完播题材": top_ids,
        "低完播题材": low,
        "平均完播率": round(sum(r.get("完播率",0) for r in rows)/len(rows),1),
        "样本数": len(rows),
    }
    # 有 key 让 AGNES 出"下一批"选题; 无 key 退回"复制高完播题材换角度"的规则
    ai_topics = _suggest_topics_ai(rows, n) if AI_KEY else None
    if ai_topics:
        topics, engine = ai_topics, f"{_provider()}/{AI_MODEL}"
    else:
        topics = [f"{r['id']} · 换个角度重讲" for r in rank[:n]]
        engine = "offline-repeat-highcomple"
    created, skipped = [], []
    for i, t in enumerate(topics[:n]):
        safe = re.sub(r"[^a-z0-9一-鿿]+", "_", t.strip()) or f"next_{i}"
        p = os.path.join(SCRIPTS_DIR, f"{safe}.json")
        if os.path.exists(p):
            skipped.append(safe); continue
        r = write_script(t, column="觉醒·读古人", tone="理性硬核")
        (created if r.get("ok") else skipped).append(safe)
    return {"ok": True, "insight": insight, "新选题": created,
            "跳过已存在": skipped, "引擎": engine,
            "下一步": f"逐条 compose_video('{created[0]}') 出片"}

@mcp.tool()
def list_scripts() -> list:
    """列出 scripts/ 目录下所有脚本 JSON 文件。"""
    return sorted(f[:-5] for f in os.listdir(SCRIPTS_DIR) if f.endswith(".json"))

if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
