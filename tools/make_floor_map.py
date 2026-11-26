"""会場マップ（校舎の1階・2階の見取り図）を作り、index.html の会場マップの節へ埋め込む。

2026-11-26。本人の依頼で、パンフレットの「校舎内マップ」（手描き風・11/26 あずみさん）の中身を、
HPの見た目（紺の細い線・明朝体・赤の番号）で描き直したもの。部屋の形と大きさは、
10/13に作った会場の3Dモデルの寸法データ（tools/venue_data.py。元は ~/narutobunkasai_venue3d/）から取る。
- 向きはパンフレットの地図と同じ（東が左・南が上。北は下）。パンフレットと見比べて迷わないように
- どの部屋に何が入るかは、パンフレットの地図からの読み。縁日＝3,4年生教室は、インスタの企画紹介の写真（「3・4年」の札）で確かめた。
  ほかは莉奈さんに確認中。体育館の位置は図式（パンフレットでは2階の東の渡り廊下から入る）
- 図面は2020年の改修前のもの（職員室まわりの改修は入っていない）
- SVGは <img> ではなく index.html に直接埋め込む（ページの明朝体を使い、番号から企画ページへ飛べるように）

    python -X utf8 tools/make_floor_map.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import venue_data as V  # noqa: E402

S = 11.0          # 1mあたりのpx
XMAX = 72.0       # 東の端（東を左に描く）
PAD = 16
NAVY, MUTED, RED = "#14285A", "#5E6478", "#C8323C"
COL = {"day": "#FCF1C9", "all": "#E8EAF2", "op": "#F4EDDD", "free": "#FFFFFF",
       "none": "url(#fm-hatch)", "plain": "#F7F5EF", "hall": "#FDFBF4"}


def sx(x): return PAD + (XMAX - x) * S
def sy(y): return PAD + (y + 1.0) * S


# 図面の部屋名 -> (塗り, 表示名, 小さい表示, 番号, 企画ページのid)
A1 = {
    "図工室": ("none", "", "", None, None), "図工準備室": ("op", "図工作業室", "", None, None),
    "購買室": ("free", "ベビー", "ルーム", None, None), "保健室": ("none", "", "", None, None),
    "多目的ルーム": ("all", "anon・いも棒", "", "7", "shop"), "1,2年生教室": ("free", "飲食", "スペース", None, None),
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
    "男子WC": ("plain", "", "", None, None), "女子WC": ("plain", "", "", None, None),
}


def rect(x0, y0, x1, y1, fill, stroke=NAVY, sw=1.3, extra=""):
    s = f' stroke="{stroke}" stroke-width="{sw}"' if sw else ""
    return (f'<rect x="{sx(x1):.1f}" y="{sy(y0):.1f}" width="{(x1-x0)*S:.1f}" '
            f'height="{(y1-y0)*S:.1f}" fill="{fill}"{s}{extra}/>')


def label(x, y, t, size=11.5, color=NAVY, weight=500, anchor="middle"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{t}</text>')


def marker(x, y, n, pid=None):
    m = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="{RED}"/>'
         f'<text class="n" x="{x:.1f}" y="{y+4.3:.1f}" font-size="12.5" fill="#fff" text-anchor="middle">{n}</text>')
    return f'<a href="kikaku/?program={pid}">{m}</a>' if pid else m


def center(rects):
    x0, y0, x1, y1 = max(rects, key=lambda r: (r[2]-r[0])*(r[3]-r[1]))
    return sx((x0 + x1) / 2), sy((y0 + y1) / 2)


def floor(rooms, assign):
    b, l = [], []
    for r in rooms:  # 外周の太線（下に敷き、上の部屋で内側を隠す）
        if r["kind"] != "court":
            for q in r["rects"]:
                b.append(rect(*q, "none", sw=3.2))
    for r in rooms:
        a = assign.get(r["name"])
        for q in r["rects"]:
            if r["kind"] == "court":
                b.append(rect(*q, "#EFEDE6", sw=0.8, extra=' stroke-dasharray="3 3"'))
            elif r["kind"] == "open":
                b.append(rect(*q, COL["hall"], sw=0))
            else:
                b.append(rect(*q, COL[a[0]] if a else COL["plain"]))
        if r["name"] in ("階段室", "B階段室"):
            for (x0, y0, x1, y1) in r["rects"]:
                for i in range(1, int((x1 - x0) / 0.9)):
                    xx = sx(x0 + i * 0.9)
                    b.append(f'<line x1="{xx:.1f}" y1="{sy(y0)+2:.1f}" x2="{xx:.1f}" y2="{sy(y1)-2:.1f}" '
                             f'stroke="{NAVY}" stroke-width=".6"/>')
            continue
        if not a:
            continue
        k, t1, t2, m, pid = a
        cx, cy = center(r["rects"])
        if k == "none":
            l.append(label(cx, cy + 4, "使いません", 10, MUTED))
            continue
        off = 8 if m else 0
        if t1:
            l.append(label(cx, cy + off + (-6 if t2 else 4), t1, 12.5 if m else 11, weight=700 if m else 500))
        if t2:
            l.append(label(cx, cy + off + 10, t2, 11.5 if m else 10.5, NAVY if m else MUTED))
        if m:
            l.append(marker(cx, cy - 20, m, pid))
    return b, l


def svg(fl):
    if fl == 1:
        b, l = floor(V.F1, A1)
        b.append(rect(35.0, 29.5, 41.0, 33.5, COL["day"], RED, 1.3, ' rx="3" stroke-dasharray="5 3"'))
        l += [label(sx(38.0), sy(31.7), "焼きそば", 11.5, weight=700),
              label(sx(38.0), sy(33.0), "外のテント", 9.5, MUTED), marker(sx(38.0), sy(28.6), "6", "shop")]
        px = sx(40.35)
        l.append(f'<path d="M{px:.1f},{sy(28.6):.1f} L{px:.1f},{sy(25.8):.1f}" stroke="{RED}" '
                 f'stroke-width="2" marker-end="url(#fm-arr)"/>')
        l.append(label(px + 6, sy(27.6), "入口・出口", 11, RED, 700, "start"))
        l += [label(sx(28.2), sy(18.8), "給食デザート", 10.5, weight=700), marker(sx(28.2), sy(16.6), "9", "shop"),
              label(sx(37.2), sy(19.8), "チョコバナナ", 10.5, weight=700), marker(sx(37.2), sy(17.6), "10", "shop"),
              label(sx(7.4), sy(17.3), "下足室", 10, MUTED)]
        h = sy(35.5) + PAD
        title = "会場マップ 校舎1階と外。北側の入口から入る。外のテントで焼きそば、1階の多目的ルームでanon・いも棒、廊下で給食デザートとチョコバナナ、職員室でTODAさんの販売ブース。お手洗いは1階"
    else:
        b, l = floor(V.F2, A2)
        b.append(rect(60.6, 12.0, 69.0, 14.4, COL["hall"], sw=1.1, extra=' stroke-dasharray="4 3"'))
        l.append(label(sx(64.8), sy(16.0), "渡り廊下", 9.5, MUTED))
        b.append(rect(69.0, 1.0, 71.8, 26.0, COL["all"], sw=1.6))
        l.append(f'<text x="{sx(70.4)+4:.1f}" y="{sy(8.0):.1f}" font-size="12" fill="{NAVY}" font-weight="700" '
                 f'writing-mode="tb">体育館へ</text>')
        l.append(marker(sx(70.4), sy(4.0), "1", "stage"))
        l += [label(sx(19.2), sy(18.4), "フリマ", 12.5, weight=700), marker(sx(19.2), sy(15.7), "5"),
              label(sx(37.2), sy(19.8), "飲食スペース", 10.5),
              label(sx(45.7), sy(25.6), "お手洗いは1階へ", 9.5, MUTED)]
        h = sy(29.5) + PAD
        title = "会場マップ 校舎2階と体育館。2階にプラネタリウムカフェ、ハンドメイドワークショップ、縁日、資料室、フリマ。東の渡り廊下から体育館のステージへ。2階のお手洗いは使えない"
    w = sx(-3.3 if fl == 1 else 6.0) + PAD   # 2階は校舎の西の端（給食室の上）が無いので、その分を切る
    defs = ('<defs><pattern id="fm-hatch" width="7" height="7" patternUnits="userSpaceOnUse" '
            'patternTransform="rotate(45)"><rect width="7" height="7" fill="#fff"/>'
            '<line x1="0" y1="0" x2="0" y2="7" stroke="#CFCBC2" stroke-width="2"/></pattern>'
            f'<marker id="fm-arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" '
            f'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{RED}"/></marker></defs>')
    compass = (f'<g transform="translate({w-40:.0f},{h-36:.0f})"><circle r="13" fill="none" stroke="{NAVY}" '
               f'stroke-width=".8"/><path d="M0,9 L-4,-3 L0,0 L4,-3 z" fill="{NAVY}"/>'
               f'<text class="n" y="26" font-size="10" text-anchor="middle" fill="{NAVY}">N</text></g>')
    return (f'<svg class="floor-svg" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="{title}" '
            f'xmlns="http://www.w3.org/2000/svg">{defs}' + "".join(b) + "".join(l) + compass + "</svg>")


def main():
    index = HERE.parent / "index.html"
    s = index.read_text(encoding="utf-8")
    for fl in (1, 2):
        pat = re.compile(rf"(<!-- floormap:{fl}f -->).*?(<!-- /floormap:{fl}f -->)", re.S)
        assert pat.search(s), f"index.html に floormap:{fl}f の目印がない"
        s = pat.sub(lambda m: m.group(1) + svg(fl) + m.group(2), s)
    index.write_bytes(s.encode("utf-8"))
    print("ok")


if __name__ == "__main__":
    main()
