"""会場マップ（校舎の1階・2階の見取り図）を作り、index.html の会場マップの節へ埋め込む。

2026-11-26。本人の依頼で、パンフレットの「校舎内マップ」（手描き風・11/26 あずみさん）の中身を、
HPの見た目（紺の線・赤の番号）で描き直したもの。部屋の形と大きさは、
10/13に作った会場の3Dモデルの寸法データ（tools/venue_data.py。元は ~/narutobunkasai_venue3d/）から取る。
- 向きはパンフレットの地図と同じ（東が左・南が上。北は下）。パンフレットと見比べて迷わないように
- どの部屋に何が入るかは、パンフレットの地図からの読み。縁日＝3,4年生教室は、インスタの企画紹介の写真（「3・4年」の札）で確かめた。
  ほかは11/26に莉奈さんに確かめた（図工作業室も使わない・給食デザートは多目的ルーム・チョコバナナは1階廊下の窓際、のほかは合っている）。
  体育館の位置は図式（パンフレットでは2階の東の渡り廊下から入る）
- 図面は2020年の改修前のもの（職員室まわりの改修は入っていない）
- SVGは <img> ではなく index.html に直接埋め込む（番号から企画ページへ飛べるように）
- 2026-11-26（2回目、本人がスマホで見て）：
  ・入れない部屋を、はっきり灰色＋斜線＋「入れません」にした。企画の無い部屋も灰色にして、行ける所だけが白・色で浮くようにした
  ・字が細くて、ご高齢の方には読みにくい → 図の中の字はゴシックの太字にし、大きくした
  ・スマホで横スクロールしないと全体が見えない → 縦長の図（横長の図を時計回りに90度回した向き。東が上）も作り、
    スマホでは縦長の図を出す（字は回さず、まっすぐ読める）

    python -X utf8 tools/make_floor_map.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import venue_data as V  # noqa: E402

NAVY, MUTED, RED = "#14285A", "#4A5068", "#C8323C"
GRAY, GRAY_TXT = "#DEDAD2", "#6A6359"
COL = {"day": "#FCF1C9", "all": "#E3E7F4", "op": "#F4EDDD", "free": "#FFFFFF",
       "none": "url(#fm-hatch)", "plain": "url(#fm-hatch)", "hall": "#FFFFFF"}
FONT = '"Hiragino Sans","Hiragino Kaku Gothic ProN","Yu Gothic UI","Yu Gothic","Meiryo",sans-serif'

# 図面の部屋名 -> (塗り, 表示名, 小さい表示, 番号, 企画ページのid)。ここに無い部屋は「入れない部屋」（灰色・字なし）
A1 = {
    "図工室": ("none", "", "", None, None), "図工準備室": ("none", "", "", None, None),
    "購買室": ("free", "ベビー", "ルーム", None, None), "保健室": ("none", "", "", None, None),
    "多目的ルーム": ("all", "anon・いも棒", "給食デザート", "7", "shop"), "1,2年生教室": ("free", "飲食", "スペース", None, None),
    "コンピューター室": ("none", "", "", None, None), "放送調整室": ("op", "放送室", "", None, None),
    "男子WC": ("free", "お手洗い", "", None, None), "女子WC": ("free", "", "", None, None),
    "資料室": ("op", "資料室", "", None, None), "職員室": ("all", "TODAさん", "販売ブース", "8", None),
}
A2 = {
    "理科室": ("none", "", "", None, None), "理科準備室": ("none", "", "", None, None),
    "図書室": ("all", "プラネタリウム", "カフェ", "2", "planetarium"),
    "5,6年生教室": ("day", "ハンドメイド", "ワークショップ", "3", "resin"),
    "3,4年生教室": ("day", "縁日", "", "4", "ennichi"),
    "郷土資料室": ("op", "資料室", "見学できます", None, None),
    "音楽室": ("op", "本部", "出演者控え", None, None), "音楽準備室": ("none", "", "", None, None),
    "男子WC": ("none", "", "", None, None), "女子WC": ("none", "", "", None, None),
}


class View:
    """図面の座標（X=東, Y=北, m）を画面の座標へ。wide=東が左・南が上、tall=それを時計回りに90度（東が上・南が右）"""

    def __init__(self, tall, xmin, xmax, ymin, ymax, s):
        self.tall, self.s, self.pad = tall, s, 14
        self.xmin, self.xmax, self.ymin, self.ymax = xmin, xmax, ymin, ymax

    def p(self, x, y):
        if self.tall:
            return self.pad + (self.ymax - y) * self.s, self.pad + (self.xmax - x) * self.s
        return self.pad + (self.xmax - x) * self.s, self.pad + (y - self.ymin) * self.s

    def size(self):
        a, b = (self.xmax - self.xmin) * self.s, (self.ymax - self.ymin) * self.s
        return (b, a) if self.tall else (a, b)

    def box(self, x0, y0, x1, y1):
        (ax, ay), (bx, by) = self.p(x0, y0), self.p(x1, y1)
        return min(ax, bx), min(ay, by), abs(ax - bx), abs(ay - by)


def rect(v, q, fill, stroke=NAVY, sw=1.4, extra=""):
    x, y, w, h = v.box(*q)
    s = f' stroke="{stroke}" stroke-width="{sw}"' if sw else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}"{s}{extra}/>'


def label(x, y, t, size=13, color=NAVY, weight=700, anchor="middle"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}" stroke="#fff" stroke-width="3.5" '
            f'stroke-linejoin="round" paint-order="stroke">{t}</text>')  # 白いふちで、斜線や線の上でも読めるように


def marker(x, y, n, pid=None):
    m = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11.5" fill="{RED}" stroke="#fff" stroke-width="1.5"/>'
         f'<text x="{x:.1f}" y="{y+5:.1f}" font-size="14" font-weight="700" fill="#fff" text-anchor="middle">{n}</text>')
    return f'<a href="kikaku/?program={pid}">{m}</a>' if pid else m


def tag(v, xw, yw, text, n=None, pid=None, sub=None, size=14):
    """図面の座標に、企画の名前と番号を置く。番号は画面の上で名前のすぐ上（向きを変えても重ならない）"""
    x, y = v.p(xw, yw)
    out = [label(x, y + 5, text, size)]
    if sub:
        out.append(label(x, y + 20, sub, 11, MUTED, 500))
    if n:
        out.append(marker(x, y - 15, n, pid))
    return out


def center(v, rects):
    x0, y0, x1, y1 = max(rects, key=lambda r: (r[2]-r[0])*(r[3]-r[1]))
    return v.p((x0 + x1) / 2, (y0 + y1) / 2)


def floor(v, rooms, assign):
    b, l = [], []
    for r in rooms:  # 外周の太線（下に敷き、上の部屋で内側を隠す）
        if r["kind"] != "court":
            for q in r["rects"]:
                b.append(rect(v, q, "none", sw=3.4))
    for r in rooms:
        a = assign.get(r["name"])
        for q in r["rects"]:
            if r["kind"] == "court":
                b.append(rect(v, q, "#ECE9E2", sw=0.8, extra=' stroke-dasharray="3 3"'))
            elif r["kind"] == "open":
                b.append(rect(v, q, COL["hall"], sw=0))
            else:
                b.append(rect(v, q, COL[a[0]] if a else COL["plain"]))
        if r["name"] in ("階段室", "B階段室"):
            for (x0, y0, x1, y1) in r["rects"]:
                for i in range(1, int((x1 - x0) / 0.9)):
                    (ax, ay), (bx, by) = v.p(x0 + i * 0.9, y0 + 0.2), v.p(x0 + i * 0.9, y1 - 0.2)
                    b.append(f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{NAVY}" stroke-width=".7"/>')
            continue
        if not a:
            continue
        k, t1, t2, m, pid = a
        cx, cy = center(v, r["rects"])
        if k == "none":
            x0, y0, x1, y1 = max(r["rects"], key=lambda q: (q[2]-q[0])*(q[3]-q[1]))
            if min(x1 - x0, y1 - y0) >= 4.5:  # 小さい部屋（トイレなど）には字を入れない（隣と重なるため）
                l.append(label(cx, cy + 4.5, "入れません", 12, GRAY_TXT))
            continue
        off = 9 if m else 0
        if t1:
            l.append(label(cx, cy + off + (-7 if t2 else 5), t1, 14 if m else 12.5, NAVY if m else MUTED))
        if t2:
            l.append(label(cx, cy + off + 11, t2, 13 if m else 11.5, NAVY if m else MUTED))
        if m:
            l.append(marker(cx, cy - 22, m, pid))
    return b, l


def svg(fl, tall):
    if fl == 1:
        v = View(tall, -3.3, 72.0, -0.5, 33.0, 10.2) if tall else View(tall, -3.3, 72.0, -1.0, 35.5, 11.0)
        b, l = floor(v, V.F1, A1)
        tent = (32.0, 28.0, 44.0, 32.6) if tall else (34.5, 29.5, 41.5, 34.0)
        b.append(rect(v, tent, COL["day"], RED, 1.6, ' rx="3" stroke-dasharray="5 3"'))
        l += tag(v, (tent[0] + tent[2]) / 2, (tent[1] + tent[3]) / 2 + (0 if tall else 0.6), "焼きそば", "6", "shop", "外のテント", 13)
        (ax, ay), (bx, by) = v.p(40.35, 28.0 if tall else 29.3), v.p(40.35, 25.9)
        l.append(f'<path d="M{ax:.1f},{ay:.1f} L{bx:.1f},{by:.1f}" stroke="{RED}" stroke-width="2.4" marker-end="url(#fm-arr)"/>')
        if tall:
            l.append(label(ax - 4, ay + 22, "入口・出口", 12.5, RED, 700, "start"))
        else:
            ex, ey = v.p(40.35, 27.6)
            l.append(label(ex + 8, ey + 5, "入口・出口", 13, RED, 700, "start"))
        # 2026-11-26 莉奈さん（広報広告班 15:22）：チョコバナナだけ1階廊下の窓際
        l += tag(v, 35.0, 20.0, "チョコバナナ", "9", "shop", size=12.5)
        gx, gy = v.p(7.4, 16.8)
        l.append(label(gx, gy + 4, "下足室", 11.5, MUTED, 500))
        title = ("会場マップ 校舎1階と外。北側の入口から入る。入口の前の外のテントで焼きそば、1階の多目的ルームでanon・いも棒と給食デザート、"
                 "廊下の窓際でチョコバナナ、職員室でTODAさんの販売ブース。お手洗いは1階。灰色の部屋には入れない")
    else:
        v = View(tall, 6.0, 72.0, 3.5, 29.5, 12.0) if tall else View(tall, 6.0, 72.0, -1.0, 29.5, 11.0)
        b, l = floor(v, V.F2, A2)
        b.append(rect(v, (60.6, 12.0, 69.0, 14.4), COL["hall"], sw=1.2, extra=' stroke-dasharray="4 3"'))
        wx, wy = v.p(64.8, 11.0 if not tall else 9.0)
        l.append(label(wx, wy + 4, "渡り廊下", 11, MUTED, 500))
        b.append(rect(v, (69.0, 4.5 if tall else 1.0, 71.8, 26.0), COL["all"], sw=1.8))
        gx, gy = v.p(70.4, 13.5)
        if tall:
            l.append(label(gx + 10, gy + 5, "体育館へ（ステージ）", 13))
            l.append(marker(gx - 76, gy, "1", "stage"))
        else:
            l.append(f'<text x="{gx+5:.1f}" y="{v.p(70.4, 7.0)[1]:.1f}" font-size="13" fill="{NAVY}" font-weight="700" writing-mode="tb">体育館へ</text>')
            l.append(marker(*v.p(70.4, 3.6), "1", "stage"))
        l += tag(v, 19.2, 17.8, "フリマ", "5")
        cx, cy = v.p(37.0, 19.4)
        l.append(label(cx, cy + 4, "飲食スペース", 12, MUTED))
        tx, ty = v.p(45.75, 25.2)
        l.append(label(tx, ty + 4, "お手洗いは1階へ", 11, GRAY_TXT))
        title = ("会場マップ 校舎2階と体育館。2階にプラネタリウムカフェ、ハンドメイドワークショップ、縁日、資料室、フリマ。"
                 "東の渡り廊下から体育館のステージへ。2階のお手洗いは使えない。灰色の部屋には入れない")
    w, h = v.size()
    w += 2 * v.pad
    h += 2 * v.pad
    defs = ('<defs><pattern id="fm-hatch" width="8" height="8" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate(45)"><rect width="8" height="8" fill="{GRAY}"/>'
            '<line x1="0" y1="0" x2="0" y2="8" stroke="#BDB7AB" stroke-width="2.2"/></pattern>'
            f'<marker id="fm-arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>')
    # 方位（北の向き）：wide は北が下、tall は北が左
    ang = 0 if not tall else 90
    cxp, cyp = (w - 34, h - 38) if not tall else (34, h - 34)
    compass = (f'<g transform="translate({cxp:.0f},{cyp:.0f})"><circle r="14" fill="#fff" stroke="{NAVY}" stroke-width="1"/>'
               f'<g transform="rotate({ang})"><path d="M0,10 L-4.5,-3 L0,0 L4.5,-3 z" fill="{NAVY}"/></g>'
               f'<text x="{0 if not tall else -22}" y="{28 if not tall else 4.5}" font-size="11" font-weight="700" '
               f'text-anchor="middle" fill="{NAVY}">北</text></g>')
    cls = "floor-svg tall" if tall else "floor-svg wide"
    return (f'<svg class="{cls}" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="{title}" '
            f'xmlns="http://www.w3.org/2000/svg" font-family=\'{FONT}\'>{defs}'
            + "".join(b) + "".join(l) + compass + "</svg>")


def main():
    index = HERE.parent / "index.html"
    s = index.read_text(encoding="utf-8")
    for fl in (1, 2):
        pat = re.compile(rf"(<!-- floormap:{fl}f -->).*?(<!-- /floormap:{fl}f -->)", re.S)
        assert pat.search(s), f"index.html に floormap:{fl}f の目印がない"
        s = pat.sub(lambda m: m.group(1) + svg(fl, False) + svg(fl, True) + m.group(2), s)
    index.write_bytes(s.encode("utf-8"))
    print("ok")


if __name__ == "__main__":
    main()
