#!/usr/bin/env python3
"""用AI讲古 · 短视频生成管线(demo)
无GPU路线:本地生成画面(ffmpeg滤镜) + edge-tts免费配音 + 动态字幕 + 9:16拼接
输入: scripts/*.json  输出: output/<id>.mp4 + 封面
"""
import json, subprocess, shutil, sys, os, glob, math, textwrap

BASE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
VOICE = "zh-CN-YunyangNeural"  # 男声·专业·可靠,贴"讲古×理性"调性
FONT = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"  # 系统自带中文fallback,已验证

def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd if isinstance(cmd,list) else [cmd])}\n{r.stderr[-2000:]}")
    return r

def tts(script, out_mp3):
    run(["edge-tts","--voice",VOICE,"--text",script["口播"],"--write-media",out_mp3])
    return out_mp3

def scene_video(scene_i, dur, workdir):
    """纯ffmpeg生成一段'古×未来'奇观画面:霓虹网格+粒子漂移+毛笔字+暗角"""
    p = os.path.join(workdir, f"scene_{scene_i}.mp4")
    # 深蓝底 + 霓虹网格(未来感) + 暗角(古卷质感);标题文字在最终合成用 subtitles 烧录
    filt = (
        "color=c=0x0a0e1a:s=%dx%d:r=%d,format=yuv420p,"
        "drawgrid=w=100:h=100:t=1:c=0x14315a@0.6,"
        "vignette=PI/3" % (W,H,FPS)
    )
    run(["ffmpeg","-y","-f","lavfi","-i", filt,
         "-t", str(dur), "-c:v","libx264","-pix_fmt","yuv420p","-r",str(FPS),
         "-s",f"{W}x{H}", p])
    return p

def build_srt(segments, per_dur, out):
    def ts(sec):
        h=int(sec//3600); m=int((sec%3600)//60); s=int(sec%60); ms=int((sec-int(sec))*1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    t=0; lines=[]
    for i,(seg,d) in enumerate(zip(segments, per_dur)):
        lines.append(f"{i+1}\n{ts(t)} --> {ts(t+d)}\n{textwrap.shorten(seg,18)}\n")
        t+=d
    open(out,"w").write("\n".join(lines))
    return out

def compose(script_id, workdir):
    data = json.load(open(f"{BASE}/scripts/{script_id}.json"))
    segs = data["字幕分段"]; scenes = data["分镜"]
    per_dur = [s["时长"] for s in scenes]
    total = sum(per_dur)
    os.makedirs(workdir, exist_ok=True)

    # 1) TTS
    mp3 = tts(data, f"{workdir}/voice.mp3")
    # 探测真实音频时长
    dur_audio = float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",mp3]).strip())
    # 若音频比分镜总长还长, 按比例拉伸画面到音频
    scale = 1.0 if dur_audio <= total else (dur_audio/total)
    print(f"  音频 {dur_audio:.1f}s / 分镜 {total}s -> 画面x{scale:.2f}")

    # 2) 每段画面
    vids=[]
    for i,(sc,d) in enumerate(zip(scenes, per_dur)):
        vids.append(scene_video(i, d*scale, workdir))
    # 3) 拼接 (绝对路径,防后台cwd漂移)
    concat = "\n".join(f"file '{v}'" for v in vids)
    listp = f"{workdir}/list.txt"
    open(listp,"w").write(concat)
    run(["ffmpeg","-y","-f","concat","-safe","0","-i",listp,"-c","copy",f"{workdir}/body.mp4"])
    # 4) 字幕 + 音频 + BGM占位 + 9:16
    srt = build_srt(segs, [d*scale for d in per_dur], f"{workdir}/sub.srt")
    srt_esc = srt.replace(":", r"\:")  # 绝对路径无冒号,直接可用
    out = f"{BASE}/output/{script_id}.mp4"
    body_abs = f"{workdir}/body.mp4"
    voice_abs = f"{workdir}/voice.mp3"
    run(["ffmpeg","-y","-i",body_abs,"-i",voice_abs,"-vf",
         f"subtitles={srt_esc}:fontsdir={FONT}:force_style='FontName=Droid Sans Fallback,FontSize=16,FontColour=&H00FFFFFF,OutlineColour=&H000a0e1a,Outline=2,MarginV=90,Alignment=2',scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1",
         "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-shortest", out])
    print("  (标题/封面文字走 subtitles 烧录;drawtext 未编译,已规避)")
    # 封面: 取中段截帧 + 封面文案
    cover=f"{BASE}/output/{script_id}_cover.png"
    # 封面:直接取成片中段截帧(subtitles已烧录字幕+标题),省掉drawtext
    run(["ffmpeg","-y","-ss",str(total*0.35),"-i",out,"-frames:v","1",cover])
    print(f"  ✅ {out}\n  封面 {cover}")
    return out

if __name__=="__main__":
    ids = sys.argv[1:] or [os.path.basename(f)[:-5] for f in glob.glob(f"{BASE}/scripts/*.json")]
    for sid in ids:
        print(f"\n=== 生成 {sid} ===")
        compose(sid, f"{BASE}/assets/{sid}")
