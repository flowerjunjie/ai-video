"""曾国藩日课 v3 — 9 takes, 48 lines, night look, 深层自省方法论."""
from engine import (
    Film, BigText, Card, PaperDoc, StringLine,
    Stamp, PenMark, Counter, WHITE, MUSTARD, HILITE, RUST,
)


def build_film(doc):
    L, E, W = doc.L, doc.E, doc.W
    film = Film(doc.duration, fps=30, look="night")

    # T01_open: 日记不是忏悔 — L1-L5
    t1 = L(1)
    film.add(BigText("曾国藩", 0, -1200, 720, t1 - 0.1, t_out=None,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.add(Stamp("日记", 2400, 400, 180, rot=-8, t_in=t1 + 0.6, rgb=MUSTARD))
    film.cue("boom", t1 + 0.1, gain=0.3)

    t2 = L(2)
    film.add(BigText("1843", 260, -300, 280, t2 + 0.5, t_out=None,
                     font="label", rgb=MUSTARD, shadow=False))
    film.cue("boom", t2, gain=0.2)

    # T02_zhaojian: 写给自己照的 — L6-L10
    t3 = L(6)
    film.add(Card(0, 600, 3000, 1500, t3 + 0.4,
                  title="照见", lines=("日课十二条", "主敬 · 静坐 · 读书"),
                  accent=HILITE, rot=-1.5, title_size=140))
    film.cue("boom", t3 + 0.4, gain=0.3)

    t4 = L(9)
    film.add(PaperDoc(0, 600, 2400, 1400, rot=1.0, t_in=t4 + 0.4,
                      header=[("日课", 80, "serif"),("十二条", 56, "mono")],
                      sentence="写下来才发现",
                      sentence_row=6, sentence_size=100,
                      rows=12, pin=True, seed=33))
    film.cue("riser", t4, dur=0.8)

    # T03_shenjie: 不求甚解 — L11-L15
    t5 = L(11)
    film.add(BigText("不求甚解", 0, -1200, 720, t5 - 0.1, t_out=None,
                     bar=HILITE, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t5 + 0.1, gain=0.3)

    t6 = L(13)
    film.add(Card(0, 600, 3000, 1500, t6 + 0.4,
                  title="两遍法", lines=("第一遍求通", "第二遍才解"),
                  accent=MUSTARD, rot=1.5, title_size=140))
    film.cue("riser", t6, dur=0.8)

    # T04_zhanju: 曾国藩最大的敌人 — L16-L20
    t7 = L(16)
    film.add(BigText("资质甚鲁", 0, -1200, 720, t7 - 0.1, t_out=None,
                     bar=RUST, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t7 + 0.1, gain=0.3)

    t8 = L(18)
    film.add(Card(0, 600, 3000, 1500, t8 + 0.4,
                  title="战惧", lines=("不是勇敢", "是：我害怕，但我还是做"),
                  accent=RUST, rot=-1.0, title_size=140))
    film.add(Stamp("怕", 2400, 400, 200, rot=8, t_in=t8 + 0.8, rgb=RUST))
    film.cue("riser", t8, dur=0.8)

    # T05_bugui: 不贪名 — L21-L25
    t9 = L(21)
    film.add(BigText("不贵难得之货", 0, -1200, 720, t9 - 0.1, t_out=None,
                     bar=HILITE, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t9 + 0.1, gain=0.3)

    t10 = L(23)
    film.add(PaperDoc(0, 600, 2400, 1400, rot=-1.0, t_in=t10 + 0.4,
                      header=[("道德经", 80, "serif"),("第3章", 56, "mono")],
                      sentence="权力越大越怕变假",
                      sentence_row=6, sentence_size=100,
                      rows=12, pin=True, seed=44))
    film.cue("riser", t10, dur=0.8)

    # T06_beikanjian: 假我 — L26-L30
    t11 = L(26)
    film.add(Card(0, 600, 3000, 1500, t11 + 0.4,
                  title="被看见", lines=("不是怕曝光", "是怕发现自己是假的"),
                  accent=RUST, rot=1.0, title_size=140))
    film.add(Stamp("假", 2400, 400, 200, rot=-8, t_in=t11 + 0.8, rgb=RUST))
    film.cue("boom", t11 + 0.4, gain=0.3)

    t12 = L(29)
    film.add(StringLine((-400, 1500), (3200, 1000), t12 + 0.5, dur=1.0, pins=True))
    film.cue("riser", t12, dur=0.8)

    # T07_zuodui: 方向>努力 — L31-L35
    t13 = L(31)
    film.add(BigText("做对的事", 0, -1200, 720, t13 - 0.1, t_out=None,
                     bar=MUSTARD, type_on=0.5, rgb=WHITE, shadow=False))
    film.add(Counter(2400, 500, 240, 100, t13 + 0.5, prefix="倍", suffix="", rgb=MUSTARD))
    film.cue("boom", t13 + 0.1, gain=0.3)

    t14 = L(33)
    film.add(Card(0, 600, 3000, 1500, t14 + 0.4,
                  title="结硬寨", lines=("不追聪明", "追扎实"),
                  accent=HILITE, rot=-1.0, title_size=160))
    film.cue("riser", t14, dur=0.8)

    # T08_moli: 磨掉假我 — L36-L40
    t15 = L(36)
    film.add(BigText("磨掉", 0, -1200, 720, t15 - 0.1, t_out=None,
                     bar=RUST, type_on=0.5, rgb=WHITE, shadow=False))
    film.cue("boom", t15 + 0.1, gain=0.3)

    t16 = L(39)
    film.add(PenMark("strike", 400, 800, 2200, 80, t_in=t16 + 0.3, rgb=RUST))
    film.add(PenMark("underline", 400, 1000, 2200, 80, t_in=t16 + 0.6, rgb=HILITE))
    film.cue("riser", t16, dur=0.8)

    # T09_close: 照·认·见·对 — L41-L48
    t17 = L(41)
    film.add(Card(0, 800, 2800, 1400, t17 + 0.3,
                  title="照 · 认 · 见 · 对", lines=("写一句日记", "删一件应该的事", "做一件结硬寨"),
                  accent=HILITE, rot=0, title_size=120))
    film.cue("boom", t17 + 0.3, gain=0.2)

    t18 = L(46)
    film.add(BigText("删一件", 0, -400, 480, t18 + 0.5, t_out=None,
                     bar=RUST, type_on=0.4, rgb=WHITE, shadow=False))
    film.cue("riser", t18, dur=0.8)

    t19 = L(48)
    film.add(PenMark("underline", 400, 200, 2200, 80, t_in=t19 + 0.3, rgb=MUSTARD))

    film.shot(t1, 0, -400, 0.85)
    film.shot(t3, 100, -200, 1.0)
    film.shot(t5, 0, -100, 0.95)
    film.shot(t9, 0, -400, 0.85)
    film.shot(t13, 0, 0, 1.0)
    film.shot(t17, 0, -100, 0.9)

    film.fade_in = 0.5
    film.fade_out = 1.5
    film.room_tone = [[0, film.duration]]
    return film
