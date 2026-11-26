"""齐物论 v3 — 8 takes, 42 lines, night look, deep philosophical chain."""
from engine import (
    Film, BigText, Card, PaperDoc, StringLine,
    Stamp, PenMark, Counter, WHITE, MUSTARD, HILITE, RUST,
)


def build_film(doc):
    L, E, W = doc.L, doc.E, doc.W
    film = Film(doc.duration, fps=30, look="night")

    # T01_sangwo: 丧我 — L1-L5
    t1 = L(1)
    film.add(BigText("齐物论", 0, -1200, 720, t1 - 0.1, t_out=None,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.add(Stamp("丧我", 2400, 400, 180, rot=-8, t_in=t1 + 0.6, rgb=MUSTARD))
    film.cue("boom", t1 + 0.1, gain=0.3)

    t2 = L(3)
    film.add(BigText("天地与我并生", 0, -400, 480, t2 - 0.1, t_out=None,
                     bar=HILITE, type_on=0.4, rgb=WHITE, shadow=False))

    t3 = L(5)
    film.add(PenMark("underline", 400, 300, 2200, 80, t_in=t3 + 0.3, rgb=HILITE))
    film.cue("boom", t3, gain=0.25)

    # T02_ying: 世界在看你 — L6-L10
    t4 = L(6)
    film.add(Card(0, 600, 3000, 1500, t4 + 0.4,
                  title="世界在看你", lines=("不是你看的", "是你投射的"),
                  accent=HILITE, rot=-1.5, title_size=160))
    film.cue("boom", t4 + 0.4, gain=0.3)

    t5 = L(9)
    film.add(PaperDoc(0, 600, 2400, 1400, rot=1.0, t_in=t5 + 0.4,
                      header=[("齐物论", 80, "serif"),("影子", 56, "mono")],
                      sentence="你心里那套标准",
                      sentence_row=6, sentence_size=100,
                      rows=12, pin=True, seed=33))
    film.add(PenMark("ellipse", 2200, 500, 280, 120, t_in=t5 + 0.8, rgb=HILITE))
    film.cue("riser", t5, dur=0.8)

    # T03_fangsheng: 方生方死 — L11-L15
    t6 = L(11)
    film.add(BigText("方生方死", 0, -1200, 720, t6 - 0.1, t_out=None,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.add(StringLine((-400, 1500), (3200, 1000), t6 + 0.5, dur=1.0, pins=True))
    film.cue("boom", t6 + 0.1, gain=0.3)

    t7 = L(14)
    film.add(Card(0, 600, 3000, 1500, t7 + 0.4,
                  title="递归消解", lines=("用来分的东西", "本身也被分"),
                  accent=RUST, rot=1.5, title_size=140))
    film.add(Stamp("线", 2400, 400, 200, rot=8, t_in=t7 + 0.8, rgb=RUST))
    film.cue("riser", t7, dur=0.8)

    # T04_tianlai: 天籁 — L16-L20
    t8 = L(16)
    film.add(BigText("天籁", 0, -1200, 720, t8 - 0.1, t_out=None,
                     bar=HILITE, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t8 + 0.1, gain=0.3)

    t9 = L(19)
    film.add(PaperDoc(0, 600, 2400, 1400, rot=-1.0, t_in=t9 + 0.4,
                      header=[("天籁者", 80, "serif"),("吹万不同", 56, "mono")],
                      sentence="不偏向任何一个",
                      sentence_row=6, sentence_size=100,
                      rows=12, pin=True, seed=44))
    film.cue("riser", t9, dur=0.8)

    # T05_beixuanze: 被选择 — L21-L25
    t10 = L(21)
    film.add(Card(0, 600, 3000, 1500, t10 + 0.4,
                  title="被选择", lines=("你以为你在选", "你只是被选的"),
                  accent=RUST, rot=1.5, title_size=180))
    film.add(Stamp("被", 2400, 400, 200, rot=8, t_in=t10 + 0.8, rgb=RUST))
    film.cue("boom", t10 + 0.4, gain=0.3)

    t11 = L(24)
    film.add(BigText("算法比你更早", 0, -200, 340, t11 + 0.5, t_out=None,
                     font="label", rgb=RUST, shadow=False))
    film.add(StringLine((-400, 1500), (3200, 1000), t11 + 0.5, dur=1.0, pins=True))
    film.cue("riser", t11, dur=0.8)

    # T06_qiwu: 齐物 — L26-L30
    t12 = L(26)
    film.add(BigText("齐物", 0, -1200, 720, t12 - 0.1, t_out=None,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t12 + 0.1, gain=0.35)

    t13 = L(29)
    film.add(Counter(2400, 500, 240, 0, t13 + 0.4, prefix="画出来的线", suffix="", rgb=MUSTARD))
    film.cue("riser", t13, dur=0.8)

    # T07_bushi: 不是虚无 — L31-L35
    t14 = L(31)
    film.add(Card(0, 600, 3000, 1500, t14 + 0.4,
                  title="不是虚无", lines=("放下裁判权", "不是取消选择"),
                  accent=HILITE, rot=-1.0, title_size=140))
    film.cue("boom", t14 + 0.4, gain=0.3)

    t15 = L(34)
    film.add(PenMark("underline", 400, 1500, 2200, 80, t_in=t15 + 0.3, rgb=HILITE))

    # T08_shoushu: 收束 — L36-L42
    t16 = L(36)
    film.add(Card(0, 800, 2800, 1400, t16 + 0.3,
                  title="齐 · 影 · 线", lines=("内耗", "比较", "选择焦虑"),
                  accent=HILITE, rot=0, title_size=140))
    film.cue("boom", t16 + 0.3, gain=0.2)

    t17 = L(41)
    film.add(BigText("不再做裁判", 0, -400, 480, t17 + 0.5, t_out=None,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("riser", t17, dur=1.0)

    film.shot(t1, 0, -400, 0.85)
    film.shot(t4, 100, -200, 1.0)
    film.shot(t6, 0, -100, 0.95)
    film.shot(t10, 0, -400, 0.85)
    film.shot(t14, 0, 0, 1.0)

    film.fade_in = 0.5
    film.fade_out = 1.5
    film.room_tone = [[0, film.duration]]
    return film
