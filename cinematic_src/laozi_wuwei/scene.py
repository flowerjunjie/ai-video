"""老子无为 v3 — 8 takes, night look, 道德经深层解读.
Overlap fix: every item clears via t_out at the next take boundary; each take's
camera key sits on its real narration-line start (labels were drifting before)."""
from engine import (
    Film, BigText, Card, PaperDoc, StringLine,
    Stamp, PenMark, Counter, WHITE, MUSTARD, HILITE, RUST,
)

# Take structure. L(i) = start of narration line i. Clear a take's items right before its successor.
TAKES = [
    ("open",     1, 5),
    ("wangwei",  6, 10),
    ("sun",      11, 15),
    ("shui",     16, 20),
    ("buzheng",  21, 25),
    ("wuwei",    26, 30),
    ("buzuai",   31, 35),
    ("close",    36, 42),
]


def _clear(doc, take, nxt):
    return doc.L(nxt) - 0.15 if nxt else None


def build_film(doc):
    L, E, W = doc.L, doc.E, doc.W
    film = Film(doc.duration, fps=30, look="night")
    names = {n: (a, b) for n, a, b in TAKES}

    # T01_open: 为道日损的语境 — L1-L5
    t1 = L(1)
    c1 = _clear(doc, "open", names["wangwei"][0])
    film.add(BigText("五千字", 0, -1100, 700, t1 - 0.1, t_out=c1,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.add(Stamp("道", 2400, 200, 200, rot=-8, t_in=t1 + 0.6, t_out=c1, rgb=MUSTARD))
    film.cue("boom", t1 + 0.1, gain=0.3)

    t2 = L(4)
    film.add(BigText("为道日损", 0, -1100, 700, t2 - 0.1, t_out=c1,
                     bar=HILITE, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t2 + 0.1, gain=0.25)

    # T02_wangwei: 努力≠前进 — L6-L10
    t3 = L(6)
    c2 = _clear(doc, "wangwei", names["sun"][0])
    film.add(Card(0, -200, 3000, 500, t3 + 0.4, t_out=c2,
                  title="不是躺平", lines=("无为", "≠ 不妄为"),
                  accent=RUST, rot=-1.5, title_size=160))
    film.cue("boom", t3 + 0.4, gain=0.3)

    t4 = L(9)
    film.add(PaperDoc(0, -250, 2400, 600, rot=1.0, t_in=t4 + 0.4, t_out=c2,
                      header=[("道德经", 80, "serif"),("第40章", 56, "mono")],
                      sentence="反者道之动",
                      sentence_row=6, sentence_size=100,
                      rows=12, pin=True, seed=33))
    film.cue("riser", t4, dur=0.8)

    # T03_sun: 损什么、怎么损 — L11-L15
    t5 = L(11)
    c3 = _clear(doc, "sun", names["shui"][0])
    film.add(BigText("损什么", 0, -1100, 700, t5 - 0.1, t_out=c3,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t5 + 0.1, gain=0.3)

    t6 = L(13)
    film.add(PenMark("strike", 400, 200, 2200, 80, t_in=t6 + 0.3, t_out=c3, rgb=RUST))
    film.add(PenMark("strike", 400, 400, 2200, 80, t_in=t6 + 0.6, t_out=c3, rgb=RUST))
    film.add(PenMark("strike", 400, 600, 2200, 80, t_in=t6 + 0.9, t_out=c3, rgb=RUST))
    film.cue("boom", t6, gain=0.2)

    # T04_shui: 水不是弱 — L16-L20
    t7 = L(16)
    c4 = _clear(doc, "shui", names["buzheng"][0])
    film.add(Card(0, -200, 3000, 500, t7 + 0.4, t_out=c4,
                  title="上善若水", lines=("天下莫柔弱", "攻坚强者莫之能胜"),
                  accent=HILITE, rot=-1.0, title_size=140))
    film.add(StringLine((-400, 1500), (3200, 1000), t7 + 0.5, t_out=c4, dur=1.0, pins=True))
    film.cue("boom", t7 + 0.4, gain=0.3)

    t8 = L(19)
    film.add(BigText("刚克不了它", 0, -200, 340, t8 + 0.5, t_out=c4,
                     font="label", rgb=HILITE, shadow=False))
    film.cue("riser", t8, dur=0.8)

    # T05_buzheng: 不争不是不争取 — L21-L25
    t9 = L(21)
    c5 = _clear(doc, "buzheng", names["wuwei"][0])
    film.add(BigText("不争", 0, -1100, 700, t9 - 0.1, t_out=c5,
                     bar=HILITE, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t9 + 0.1, gain=0.3)

    t10 = L(22)
    film.add(PaperDoc(0, -250, 2400, 600, rot=-1.0, t_in=t10 + 0.4, t_out=c5,
                      header=[("道德经", 80, "serif"),("第8章", 56, "mono")],
                      sentence="后其身而身先",
                      sentence_row=6, sentence_size=100,
                      rows=12, pin=True, seed=44))
    film.cue("riser", t10, dur=0.8)

    # T06_wuwei: 无为而无不为 — L26-L30
    t11 = L(26)
    c6 = _clear(doc, "wuwei", names["buzuai"][0])
    film.add(BigText("无为而无不为", 0, -1100, 660, t11 - 0.1, t_out=c6,
                     bar=MUSTARD, type_on=0.6, rgb=WHITE, shadow=False))
    film.add(Counter(2400, 200, 240, 90, t11 + 0.5, t_out=c6, prefix="", suffix="%读错", rgb=RUST))
    film.cue("boom", t11 + 0.1, gain=0.35)

    t12 = L(28)
    film.add(Stamp("不妄", 2400, 200, 200, rot=8, t_in=t12 + 0.5, t_out=c6, rgb=MUSTARD))
    film.cue("riser", t12, dur=0.8)

    # T07_buzuai: 你不需要赢 — L31-L35
    t13 = L(31)
    c7 = _clear(doc, "buzuai", names["close"][0])
    film.add(Card(0, -200, 3000, 500, t13 + 0.4, t_out=c7,
                  title="不阻碍", lines=("删掉'应该'", "留下本来要做的"),
                  accent=HILITE, rot=1.0, title_size=160))
    film.cue("boom", t13 + 0.4, gain=0.3)

    t14 = L(34)
    film.add(PenMark("strike", 400, 600, 2200, 80, t_in=t14 + 0.3, t_out=c7, rgb=RUST))
    film.cue("boom", t14, gain=0.2)

    # T08_close: 损到不能再损 — L36-L42
    t15 = L(36)
    c8 = _clear(doc, "close", None)
    film.add(Card(0, -300, 2800, 500, t15 + 0.3, t_out=c8,
                  title="做减法", lines=("工作 · 关系 · 自我", "三条线"),
                  accent=HILITE, rot=0, title_size=140))
    film.cue("boom", t15 + 0.3, gain=0.2)

    t16 = L(41)
    film.add(BigText("无不为", 0, -400, 480, t16 + 0.5, t_out=c8,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("riser", t16, dur=1.0)

    t17 = L(42)
    film.add(PenMark("underline", 400, 200, 2200, 80, t_in=t17 + 0.3, t_out=c8, rgb=MUSTARD))

    # Camera keys on each take's REAL start line.
    film.shot(t1, 0, -300, 0.85)
    film.shot(t3, 100, -200, 1.0)
    film.shot(t5, 0, -200, 0.95)
    film.shot(t9, 0, -300, 0.85)
    film.shot(t13, 0, -100, 1.0)
    film.shot(t15, 0, -200, 0.9)

    film.fade_in = 0.5
    film.fade_out = 1.5
    film.room_tone = [[0, film.duration]]
    return film
