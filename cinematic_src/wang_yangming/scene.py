"""王阳明事上磨练 v3 — 10 takes, night look, 心学深层解读.
Overlap fix: every item clears via t_out at the next take boundary; each take's
camera key sits on its real narration-line start (labels were drifting before)."""
from engine import (
    Film, BigText, Card, PaperDoc, StringLine,
    Stamp, PenMark, Counter, WHITE, MUSTARD, HILITE, RUST,
)

# Take structure. L(i) = start of narration line i. Clear a take's items right before its successor.
TAKES = [
    ("open",      1, 5),
    ("xinji",     6, 10),
    ("liangzhi",  11, 15),
    ("zhuangzuo", 16, 20),
    ("zei",       21, 25),
    ("pai",       26, 30),
    ("moli",      31, 35),
    ("modaopai",  36, 40),
    ("zhixing",   41, 45),
    ("close",     46, 50),
]


def _clear(doc, take, nxt):
    return doc.L(nxt) - 0.15 if nxt else None


def build_film(doc):
    L, E, W = doc.L, doc.E, doc.W
    film = Film(doc.duration, fps=30, look="night")
    names = {n: (a, b) for n, a, b in TAKES}

    # T01_open: 五十七岁的危机 — L1-L5
    t1 = L(1)
    c1 = _clear(doc, "open", names["xinji"][0])
    film.add(BigText("王阳明", 0, -1100, 700, t1 - 0.1, t_out=c1,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.add(Stamp("1508", 2400, 200, 180, rot=-8, t_in=t1 + 0.6, t_out=c1, rgb=MUSTARD))
    film.cue("boom", t1 + 0.1, gain=0.3)

    t2 = L(3)
    film.add(BigText("龙场", 260, -300, 280, t2 + 0.5, t_out=c1,
                     font="label", rgb=HILITE, shadow=False))
    film.cue("boom", t2, gain=0.25)

    # T02_xinji: 心即理 — L6-L10
    t3 = L(6)
    c2 = _clear(doc, "xinji", names["liangzhi"][0])
    film.add(Card(0, -200, 3000, 500, t3 + 0.4, t_out=c2,
                  title="心即理", lines=("朱熹向外穷理", "阳明说：理就是心"),
                  accent=HILITE, rot=-1.5, title_size=160))
    film.cue("boom", t3 + 0.4, gain=0.3)

    t4 = L(9)
    film.add(PaperDoc(0, -250, 2400, 600, rot=1.0, t_in=t4 + 0.4, t_out=c2,
                      header=[("传习录", 80, "serif"),("答顾东桥书", 56, "mono")],
                      sentence="理不在外",
                      sentence_row=6, sentence_size=100,
                      rows=12, pin=True, seed=33))
    film.add(PenMark("ellipse", 2200, 500, 280, 120, t_in=t4 + 0.8, t_out=c2, rgb=HILITE))
    film.cue("riser", t4, dur=0.8)

    # T03_liangzhi: 良知 — L11-L15
    t5 = L(11)
    c3 = _clear(doc, "liangzhi", names["zhuangzuo"][0])
    film.add(Card(0, -200, 3000, 500, t5 + 0.4, t_out=c3,
                  title="四句教", lines=("无善无恶心之体", "知善知恶是良知"),
                  accent=MUSTARD, rot=1.5, title_size=120))
    film.cue("boom", t5 + 0.4, gain=0.3)

    t6 = L(14)
    film.add(BigText("不是知识", 0, -200, 340, t6 + 0.5, t_out=c3,
                     font="label", rgb=RUST, shadow=False))
    film.cue("riser", t6, dur=0.8)

    # T04_zhuangzuo: 假装不知道 — L16-L20
    t7 = L(16)
    c4 = _clear(doc, "zhuangzuo", names["zei"][0])
    film.add(BigText("假装不知道", 0, -1100, 700, t7 - 0.1, t_out=c4,
                     bar=RUST, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t7 + 0.1, gain=0.3)

    t8 = L(19)
    film.add(StringLine((-400, 1500), (3200, 1000), t8 + 0.5, t_out=c4, dur=1.0, pins=True))
    film.add(Counter(2400, 200, 240, 1, t8 + 0.5, t_out=c4, prefix="你早就", suffix="知道", rgb=MUSTARD))
    film.cue("riser", t8, dur=0.8)

    # T05_zei: 破心中贼 — L21-L25
    t9 = L(21)
    c5 = _clear(doc, "zei", names["pai"][0])
    film.add(BigText("破心中贼", 0, -1100, 700, t9 - 0.1, t_out=c5,
                     bar=RUST, type_on=0.5, rgb=WHITE, shadow=False))
    film.add(Stamp("1519", 2400, 200, 180, rot=-8, t_in=t9 + 0.6, t_out=c5, rgb=RUST))
    film.cue("boom", t9 + 0.1, gain=0.3)

    t10 = L(23)
    film.add(PaperDoc(0, -250, 2400, 600, rot=-1.0, t_in=t10 + 0.4, t_out=c5,
                      header=[("宁王乱后", 80, "serif"),("1519", 56, "mono")],
                      sentence="破山中贼易 破心中贼难",
                      sentence_row=6, sentence_size=80,
                      rows=12, pin=True, seed=44))
    film.cue("riser", t10, dur=0.8)

    # T06_pai: 贼=怕 — L26-L30
    t11 = L(26)
    c6 = _clear(doc, "pai", names["moli"][0])
    film.add(Card(0, -200, 3000, 500, t11 + 0.4, t_out=c6,
                  title="三个怕", lines=("怕输 · 怕丢脸", "怕认错"),
                  accent=RUST, rot=-1.0, title_size=160))
    film.cue("boom", t11 + 0.4, gain=0.3)

    t12 = L(29)
    film.add(PenMark("strike", 400, 600, 2200, 80, t_in=t12 + 0.3, t_out=c6, rgb=RUST))
    film.add(PenMark("strike", 400, 750, 2200, 80, t_in=t12 + 0.6, t_out=c6, rgb=RUST))
    film.add(PenMark("strike", 400, 900, 2200, 80, t_in=t12 + 0.9, t_out=c6, rgb=RUST))
    film.cue("boom", t12, gain=0.2)

    # T07_moli: 事上磨练 — L31-L35
    t13 = L(31)
    c7 = _clear(doc, "moli", names["modaopai"][0])
    film.add(BigText("事上磨练", 0, -1100, 700, t13 - 0.1, t_out=c7,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t13 + 0.1, gain=0.35)

    t14 = L(34)
    film.add(Card(0, -200, 3000, 500, t14 + 0.4, t_out=c7,
                  title="不是冥想", lines=("不脱离现实", "带着怕做"),
                  accent=HILITE, rot=1.0, title_size=140))
    film.cue("riser", t14, dur=0.8)

    # T08_modaopai: 磨到不怕 — L36-L40
    t15 = L(36)
    c8 = _clear(doc, "modaopai", names["zhixing"][0])
    film.add(BigText("磨到不怕", 0, -1100, 700, t15 - 0.1, t_out=c8,
                     bar=HILITE, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t15 + 0.1, gain=0.3)

    t16 = L(39)
    film.add(Counter(2400, 200, 240, 0, t16 + 0.4, t_out=c8, prefix="磨掉", suffix="", rgb=MUSTARD))
    film.cue("riser", t16, dur=0.8)

    # T09_zhixing: 知行合一 — L41-L45
    t17 = L(41)
    c9 = _clear(doc, "zhixing", names["close"][0])
    film.add(Card(0, -200, 3000, 500, t17 + 0.4, t_out=c9,
                  title="知行合一", lines=("知而不行", "只是未知"),
                  accent=MUSTARD, rot=-1.0, title_size=160))
    film.cue("boom", t17 + 0.4, gain=0.3)

    t18 = L(44)
    film.add(PenMark("underline", 400, 800, 2200, 80, t_in=t18 + 0.3, t_out=c9, rgb=HILITE))

    # T10_close: 心·怕·磨 — L46-L50
    t19 = L(46)
    c10 = _clear(doc, "close", None)
    film.add(Card(0, -300, 2800, 500, t19 + 0.3, t_out=c10,
                  title="心 · 怕 · 磨", lines=("选一件事做", "写一句'我早就知道'", "删一件怕的事"),
                  accent=HILITE, rot=0, title_size=120))
    film.cue("boom", t19 + 0.3, gain=0.2)

    t20 = L(49)
    film.add(BigText("带着怕做", 0, -400, 480, t20 + 0.5, t_out=c10,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("riser", t20, dur=1.0)

    # Camera keys on each take's REAL start line.
    film.shot(t1, 0, -300, 0.85)
    film.shot(t3, 100, -200, 1.0)
    film.shot(t7, 0, -200, 0.95)
    film.shot(t11, 0, -300, 0.85)
    film.shot(t15, 0, -100, 1.0)
    film.shot(t19, 0, -200, 0.9)

    film.fade_in = 0.5
    film.fade_out = 1.5
    film.room_tone = [[0, film.duration]]
    return film
