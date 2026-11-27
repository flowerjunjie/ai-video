"""齐物论 v3 — 8 takes, night look, deep philosophical chain.
Overlap fix: every item clears via t_out at the next take boundary, and each
take's camera key sits on the real narration-line start (labels were drifting
before, so stale items re-projected into the next take)."""
from engine import (
    Film, BigText, Card, PaperDoc, StringLine,
    Stamp, PenMark, Counter, WHITE, MUSTARD, HILITE, RUST,
)

# Take structure. Each entry: (name, first-line, last-line).
# L(i) = start of narration line i. Clear a take's items right before its successor.
TAKES = [
    ("sangwo",   1, 5),
    ("ying",     6, 10),
    ("fangsheng", 11, 15),
    ("tianlai",  16, 20),
    ("beixuanze", 21, 25),
    ("qiwu",     26, 30),
    ("bushi",    31, 35),
    ("shoushu",  36, 42),
]


def _clear(doc, take, nxt):
    """t_out that fades this take's items out right before the next take opens."""
    return doc.L(nxt) - 0.15 if nxt else None


def build_film(doc):
    L, E, W = doc.L, doc.E, doc.W
    film = Film(doc.duration, fps=30, look="night")
    names = {n: (a, b) for n, a, b in TAKES}

    # T01_sangwo: 丧我 — L1-L5
    t1 = L(1)
    c1 = _clear(doc, "sangwo", names["ying"][0])
    film.add(BigText("齐物论", 0, -1100, 700, t1 - 0.1, t_out=c1,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.add(Stamp("丧我", 2400, 200, 180, rot=-8, t_in=t1 + 0.6, t_out=c1, rgb=MUSTARD))
    film.cue("boom", t1 + 0.1, gain=0.3)

    t2 = L(3)
    film.add(BigText("天地与我并生", 0, -400, 480, t2 - 0.1, t_out=c1,
                     bar=HILITE, type_on=0.4, rgb=WHITE, shadow=False))

    t3 = L(5)
    film.add(PenMark("underline", 400, 300, 2200, 80, t_in=t3 + 0.3, t_out=c1, rgb=HILITE))
    film.cue("boom", t3, gain=0.25)

    # T02_ying: 世界在看你 — L6-L10. One focal card in the lower band; an underline
    # lands on it. No second paper doc competing for the same band.
    t4 = L(6)
    c2 = _clear(doc, "ying", names["fangsheng"][0])
    film.add(Card(0, -200, 3000, 500, t4 + 0.4, t_out=c2,
                  title="世界在看你", lines=("不是你看的", "是你投射的"),
                  accent=HILITE, rot=-1.5, title_size=160))
    film.cue("boom", t4 + 0.4, gain=0.3)

    t5 = L(9)
    film.add(PenMark("underline", 400, 1120, 2200, 80, t_in=t5 + 0.6, t_out=c2, rgb=HILITE))
    film.cue("riser", t5, dur=0.8)

    # T03_fangsheng: 方生方死 — L11-L15. Hero word up top (hero band), card below.
    t6 = L(11)
    c3 = _clear(doc, "fangsheng", names["tianlai"][0])
    film.add(BigText("方生方死", 0, -900, 560, t6 - 0.1, t_out=c3,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t6 + 0.1, gain=0.3)

    t7 = L(14)
    film.add(Card(0, -200, 3000, 500, t7 + 0.4, t_out=c3,
                  title="递归消解", lines=("用来分的东西", "本身也被分"),
                  accent=RUST, rot=1.5, title_size=140))
    film.add(Stamp("线", 2400, 200, 200, rot=8, t_in=t7 + 0.8, t_out=c3, rgb=RUST))
    film.cue("riser", t7, dur=0.8)

    # T04_tianlai: 天籁 — L16-L20. Hero word up top, paper doc in the lower band.
    t8 = L(16)
    c4 = _clear(doc, "tianlai", names["beixuanze"][0])
    film.add(BigText("天籁", 0, -900, 560, t8 - 0.1, t_out=c4,
                     bar=HILITE, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t8 + 0.1, gain=0.3)

    t9 = L(19)
    film.add(PaperDoc(0, -250, 2400, 600, rot=-1.0, t_in=t9 + 0.4, t_out=c4,
                      header=[("天籁者", 80, "serif"),("吹万不同", 56, "mono")],
                      sentence="不偏向任何一个",
                      sentence_row=6, sentence_size=100,
                      rows=12, pin=True, seed=44))
    film.cue("riser", t9, dur=0.8)

    # T05_beixuanze: 被选择 — L21-L25. Card in the lower band; the "算法" note sits in
    # the hero band ABOVE it (clear gap) instead of tucked inside the card.
    t10 = L(21)
    c5 = _clear(doc, "beixuanze", names["qiwu"][0])
    film.add(Card(0, -200, 3000, 500, t10 + 0.4, t_out=c5,
                  title="被选择", lines=("你以为你在选", "你只是被选的"),
                  accent=RUST, rot=1.5, title_size=180))
    film.add(Stamp("被", 2400, 200, 200, rot=8, t_in=t10 + 0.8, t_out=c5, rgb=RUST))
    film.cue("boom", t10 + 0.4, gain=0.3)

    t11 = L(24)
    film.add(BigText("算法比你更早", 0, -900, 360, t11 + 0.5, t_out=c5,
                     font="label", rgb=RUST, shadow=False))
    film.cue("riser", t11, dur=0.8)

    # T06_qiwu: 齐物 — L26-L30
    t12 = L(26)
    c6 = _clear(doc, "qiwu", names["bushi"][0])
    film.add(BigText("齐物", 0, -1100, 700, t12 - 0.1, t_out=c6,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t12 + 0.1, gain=0.35)

    t13 = L(29)
    film.add(Counter(2400, 200, 240, 0, t13 + 0.4, t_out=c6, prefix="画出来的线", suffix="", rgb=MUSTARD))
    film.cue("riser", t13, dur=0.8)

    # T07_bushi: 不是虚无 — L31-L35
    t14 = L(31)
    c7 = _clear(doc, "bushi", names["shoushu"][0])
    film.add(Card(0, -200, 3000, 500, t14 + 0.4, t_out=c7,
                  title="不是虚无", lines=("放下裁判权", "不是取消选择"),
                  accent=HILITE, rot=-1.0, title_size=140))
    film.cue("boom", t14 + 0.4, gain=0.3)

    t15 = L(34)
    film.add(PenMark("underline", 400, 800, 2200, 80, t_in=t15 + 0.3, t_out=c7, rgb=HILITE))

    # T08_shoushu: 收束 — L36-L42
    t16 = L(36)
    c8 = _clear(doc, "shoushu", None)
    film.add(Card(0, -300, 2800, 500, t16 + 0.3, t_out=c8,
                  title="齐 · 影 · 线", lines=("内耗", "比较", "选择焦虑"),
                  accent=HILITE, rot=0, title_size=140))
    film.cue("boom", t16 + 0.3, gain=0.2)

    t17 = L(41)
    film.add(BigText("不再做裁判", 0, -400, 480, t17 + 0.5, t_out=c8,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("riser", t17, dur=1.0)

    # Camera keys sit on each take's REAL start line so the focus stays on the live take.
    film.shot(t1, 0, -300, 0.85)
    film.shot(t4, 100, -200, 1.0)
    film.shot(t6, 0, -200, 0.95)
    film.shot(t10, 0, -300, 0.85)
    film.shot(t14, 0, -100, 1.0)

    film.fade_in = 0.5
    film.fade_out = 1.5
    film.room_tone = [[0, film.duration]]
    return film
