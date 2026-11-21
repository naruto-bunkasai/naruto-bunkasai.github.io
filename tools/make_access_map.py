"""会場までの略図を、OpenStreetMapの道の形から作る。行き（assets/img/access-map-go.svg）と帰り（access-map-back.svg）の2枚。

2026-11-17。11/16に地元の佐藤さんと確かめた「国道11号から会場への入口は、県道41号との分かれ道（ヘアピンカーブ）の1か所だけ。
集落の細い道には入らない」を伝えるための図。道の形は tools/access-map-osm.json（Overpass APIで取ったもの）。
2026-11-21：帰りの道を足した。11/19の警備（アリス警備さん）の打ち合わせで、お寺の駐車場に停めた人以外は全員、
会場の北から東を回って県道41号へ出る（莉奈さん 11/19 18:31「学校周りを一周回って同じルート」と、警備員の配置図から読んだ。莉奈さんに確認中）。
2026-11-21：1枚に行きと帰りを重ねると、混ざって見える・★に線が集まって事故のように見える・国道11号の上で線が重なる（本人）ので、
行きと帰りを別の図にし、HPではタブで切り替える。
- 行き：国道11号の両方向から★（入口）まで赤の点線、★で折り返して入口からの道を駐車場（P）まで。集落の細い道には×（交差点の上ではなく、細い道を少し入った所）
- 帰り：駐車場から会場の東を回って県道41号へ（紫）。大麻方面は南へ、鳴門・引田方面は分かれ道から国道11号へ。★は描かない（線が★に集まって見えないように）

    python -X utf8 tools/make_access_map.py
"""
import json, math, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
d = json.load(open(ROOT / "tools" / "access-map-osm.json", encoding="utf-8"))

B = (34.2093, 134.4752, 34.2196, 134.4892)        # 南, 西, 北, 東
K = math.cos(math.radians(34.214))
W = 1000
H = round(W * (B[2] - B[0]) / ((B[3] - B[1]) * K))

def xy(lat, lon):
    return ((lon - B[1]) / (B[3] - B[1]) * W, (B[2] - lat) / (B[2] - B[0]) * H)

def path(g):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in (xy(p["lat"], p["lon"]) for p in g))

def ppx(P):
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in P)

J = (34.2137527, 134.481479)            # 国道11号と県道41号の分かれ道（入口）
ACCESS_WAY = 181040807                  # 県道41号から会場の西側を北へ上がる道（入口からの道）
SEA_SIDE_AT_J = 181040855               # 分かれ道から海側へ入る細い道
LOOP_WAYS = [181040724, 181040956, 181040916, 181041015, 181040900]   # 会場の北から東を回って県道41号へ出る道
ROUTE41 = 675645609                     # 県道41号（分かれ道から南へ）

els = [e for e in d["elements"] if e.get("geometry")]
WAYS = {e["id"]: e for e in els}
trunk = [e for e in els if e.get("tags", {}).get("highway") == "trunk"]
prim = [e for e in els if e.get("tags", {}).get("highway") == "primary"]
small = [e for e in els if e.get("tags", {}).get("highway") in ("residential", "unclassified")]
river = [e for e in els if e.get("tags", {}).get("name") == "折野川" and e["type"] == "way"]
school = next(e for e in els if e.get("tags", {}).get("amenity") == "school")
access = WAYS[ACCESS_WAY]

trunk_pts = {(round(p["lat"], 7), round(p["lon"], 7)) for e in trunk for p in e["geometry"]}
inside = lambda la, lo: B[0] < la < B[2] and B[1] < lo < B[3]
jx, jy = xy(*J)

def walk_from(P, i, step, dist):       # 点列Pのi番目から、step の向きに dist だけ進んだ点
    acc = 0.0
    while 0 <= i + step < len(P):
        a, b = P[i], P[i + step]; seg = math.hypot(b[0]-a[0], b[1]-a[1])
        if acc + seg >= dist:
            t = (dist - acc) / seg; return (a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t)
        acc += seg; i += step
    return P[i]

def within(P, R0, R1):                 # ★から外へ向かう点列Pの、★から半径R0〜R1の部分（細かく刻む）
    seg = []
    for a, b in zip(P, P[1:]):
        for m in [x/20 for x in range(21)]:
            q = (a[0]+(b[0]-a[0])*m, a[1]+(b[1]-a[1])*m)
            dd = math.hypot(q[0]-jx, q[1]-jy)
            if R0 <= dd <= R1 and (not seg or math.hypot(q[0]-seg[-1][0], q[1]-seg[-1][1]) > 1): seg.append(q)
            if dd > R1: return seg
    return seg

def chain(ids):
    pts = []
    for i in ids:
        g = [(p["lat"], p["lon"]) for p in WAYS[i]["geometry"]]
        if pts:
            d0 = (g[0][0]-pts[-1][0])**2 + (g[0][1]-pts[-1][1])**2
            d1 = (g[-1][0]-pts[-1][0])**2 + (g[-1][1]-pts[-1][1])**2
            if d1 < d0: g.reverse()
        pts += g
    return [xy(a, b) for a, b in pts]

# 国道11号のうち★を通る区間。★から両方向へ（外向き）
tg = min(trunk, key=lambda e: min(math.hypot(xy(p["lat"], p["lon"])[0]-jx, xy(p["lat"], p["lon"])[1]-jy) for p in e["geometry"]))
tp = [xy(p["lat"], p["lon"]) for p in tg["geometry"]]
ti = min(range(len(tp)), key=lambda i: math.hypot(tp[i][0]-jx, tp[i][1]-jy))
TRUNK_OUT = [tp[ti:], list(reversed(tp[:ti+1]))]

# 入口からの道（南から北へ）。終わり＝駐車場（帰りの出発点）
ag = [xy(p["lat"], p["lon"]) for p in access["geometry"]]
if access["geometry"][0]["lat"] > access["geometry"][-1]["lat"]: ag.reverse()

# 帰り：会場の北→東→県道41号。そこから南（大麻方面）と、分かれ道へ戻る
loop = chain(LOOP_WAYS)
p41 = [xy(p["lat"], p["lon"]) for p in WAYS[ROUTE41]["geometry"]]
k41 = min(range(len(p41)), key=lambda i: math.hypot(p41[i][0]-loop[-1][0], p41[i][1]-loop[-1][1]))
to_j = p41[k41:]
to_south = list(reversed(p41[k41-5:k41+1]))
PARK = loop[0]

# 集落の細い道の×（交差点の上ではなく、細い道を少し入った所）
crosses = []
for e in small:
    g = e["geometry"]
    for idx, p in enumerate(g):
        kk = (round(p["lat"], 7), round(p["lon"], 7))
        x_, y_ = xy(*kk)
        if x_ > W - 150 and y_ < 90: continue              # 「鳴門方面」の文字と重なる端は描かない
        if kk in trunk_pts and inside(*kk) and (abs(kk[0] - J[0]) > 1e-6 or e["id"] == SEA_SIDE_AT_J):
            P = [xy(q["lat"], q["lon"]) for q in g]
            step = 1 if idx < len(g) - 1 else -1
            pos = walk_from(P, idx, step, 70 if e["id"] == SEA_SIDE_AT_J else 34)
            if all(math.hypot(pos[0]-c[0], pos[1]-c[1]) > 20 for c in crosses): crosses.append(pos)

NAVY, RED, GRAY, PURPLE, CREAM = "#14285A", "#C8323C", "#5E6478", "#6B48B3", "#FDFBF4"
T = 'font-family="Shippori Mincho, Hiragino Mincho ProN, Yu Mincho, serif" font-weight="700"'

def star(cx, cy, R, r):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5; rr = R if i % 2 == 0 else r
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return " ".join(pts)

def build(mode):
    go = mode == "go"
    out = []
    def label(x, y, text, size=30, fill=NAVY, anchor="start", halo=True):
        s = f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" {T}'
        out.append(s + (f' stroke="{CREAM}" stroke-width="8" paint-order="stroke">' if halo else ">") + f"{text}</text>")
    title = "会場までの略図（行き）" if go else "会場からの略図（帰り）"
    desc = ("国道11号を通り、県道41号との分かれ道（ヘアピンカーブ）の★からだけ会場へ入る。鳴門方面から来たら★で折り返し、入口からの道を上って駐車場（P）へ。国道11号から集落の細い道（×）には入らない。"
            if go else
            "お寺の駐車場に停めた方以外は、駐車場（P）から会場の北と東を回って県道41号へ出る。大麻方面はそのまま県道41号を南へ、鳴門方面・引田方面は県道41号を分かれ道まで戻り、国道11号へ。")
    out += [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">',
            f'<title id="t">{title}</title>', f'<desc id="d">{desc}</desc>',
            f'<rect width="{W}" height="{H}" fill="{CREAM}"/>',
            '<defs>'
            f'<marker id="ahr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="3" markerHeight="3" orient="auto"><path d="M0,0 L10,5 L0,10Z" fill="{RED}"/></marker>'
            f'<marker id="ah" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="3.2" markerHeight="3.2" orient="auto"><path d="M0,0 L10,5 L0,10Z" fill="{PURPLE}"/></marker>'
            '</defs>',
            '<g fill="none" stroke-linecap="round" stroke-linejoin="round">']
    for e in river: out.append(f'<path d="{path(e["geometry"])}" stroke="#A9D3EE" stroke-width="5"/>')
    for e in small: out.append(f'<path d="{path(e["geometry"])}" stroke="#D9D6CE" stroke-width="5"/>')
    for e in prim: out.append(f'<path d="{path(e["geometry"])}" stroke="{GRAY}" stroke-width="11"/>')
    for e in trunk: out.append(f'<path d="{path(e["geometry"])}" stroke="{NAVY}" stroke-width="16"/>')
    out.append('</g>')
    out.append(f'<path d="{path(school["geometry"])}Z" fill="#F6E3E3" stroke="{RED}" stroke-width="4"/>')

    if go:
        # 国道11号の両方向から★まで（外から★へ）。途中に矢印
        for Bo in TRUNK_OUT:
            far = list(reversed(within(Bo, 150, 300)))
            near = list(reversed(within(Bo, 0, 154)))
            for P_, arrow in ((far, True), (near, False)):
                if len(P_) < 2: continue
                m = ' marker-end="url(#ahr)"' if arrow else ""
                out.append(f'<path d="{ppx(P_)}" fill="none" stroke="{CREAM}" stroke-width="12" stroke-linecap="round" stroke-dasharray="2 16"/>')
                out.append(f'<path d="{ppx(P_)}" fill="none" stroke="{RED}" stroke-width="8" stroke-linecap="round" stroke-dasharray="2 16"{m}/>')
        # ★で折り返して入口からの道を駐車場まで
        out.append(f'<path d="{ppx(ag)}" fill="none" stroke="{RED}" stroke-width="10" stroke-linecap="round" stroke-dasharray="2 16" marker-end="url(#ahr)"/>')
        for x, y in crosses:
            r = 13
            for col, w_ in (("#fff", 12), (RED, 6)):
                out.append(f'<g stroke="{col}" stroke-width="{w_}" stroke-linecap="round"><path d="M{x-r:.1f},{y-r:.1f}L{x+r:.1f},{y+r:.1f}M{x+r:.1f},{y-r:.1f}L{x-r:.1f},{y+r:.1f}"/></g>')
        out.append(f'<polygon points="{star(jx, jy, 30, 13)}" fill="#F3D774" stroke="{RED}" stroke-width="4"/>')
    else:
        # 帰り：駐車場→県道41号→（南へ）／（分かれ道から国道11号の両方向へ）。★は描かず、分かれ道を通り抜ける1本の線にする
        segs = [loop, to_south] + [to_j + within(Bo, 1, 170) for Bo in TRUNK_OUT]
        for P_ in segs:
            out.append(f'<path d="{ppx(P_)}" fill="none" stroke="{CREAM}" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>')
        for P_ in segs:
            out.append(f'<path d="{ppx(P_)}" fill="none" stroke="{PURPLE}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#ah)"/>')

    # 駐車場
    sx0, sy0 = PARK
    out.append(f'<circle cx="{sx0:.1f}" cy="{sy0:.1f}" r="19" fill="{NAVY}" stroke="{CREAM}" stroke-width="4"/>')
    out.append(f'<text x="{sx0:.1f}" y="{sy0+8:.1f}" font-size="24" text-anchor="middle" fill="#fff" font-family="sans-serif" font-weight="700">P</text>')
    label(sx0, sy0 - 30, "駐車場", 22, NAVY, "middle")
    # 会場
    sx = sum(xy(p["lat"], p["lon"])[0] for p in school["geometry"]) / len(school["geometry"])
    sy = sum(xy(p["lat"], p["lon"])[1] for p in school["geometry"]) / len(school["geometry"])
    label(sx, sy + 12, "会場", 34, RED, "middle")
    label(640, 742, "会場：TODAベリーファーム", 22, NAVY)
    label(640, 772, "（旧北灘西小学校）", 22, NAVY)

    if go:
        # 入口（引き出し線で★につなぐ。文字の★は地図の★と形も色も違って見えるので使わない）
        lx, ly = jx - 75, jy - 120
        out.append(f'<path d="M{jx-4:.0f},{jy-34:.0f} L{lx+6:.0f},{ly+48:.0f}" stroke="{RED}" stroke-width="3" fill="none"/>')
        label(lx + 10, ly + 4, "入口はここだけ", 32, RED, "end")
        label(lx + 10, ly + 40, "（ヘアピンカーブ）", 24, RED, "end")
        label(545, 398, "行き", 26, RED)
    else:
        mx, my = loop[len(loop)//2]
        label(mx + 24, my, "帰り", 30, PURPLE)
        label(mx + 24, my + 32, "（会場の東を回る）", 22, PURPLE)
        label(jx - 30, jy - 70, "鳴門・引田方面は", 22, PURPLE, "end")
        label(jx - 30, jy - 42, "分かれ道から国道11号へ", 22, PURPLE, "end")
        label(565, H - 140, "大麻方面は", 22, PURPLE, "end")
        label(565, H - 112, "そのまま南へ", 22, PURPLE, "end")

    # 道と方面
    label(W - 20, 128, "鳴門方面 →", 28, NAVY, "end")
    label(20, H - 40, "← 引田方面", 28, NAVY)
    label(xy(34.2101, 134.4836)[0] + 22, H - 40, "県道41号 ↓ 大麻方面", 26, GRAY)
    label(xy(34.2176, 134.4838)[0] - 10, xy(34.2176, 134.4838)[1] + 5, "国道11号", 28, NAVY, "end")

    # 図の名前（スクショで送られても、どちらの図か分かるように）
    if go:
        out.append(f'<g><rect x="20" y="130" width="450" height="92" rx="8" fill="{CREAM}" stroke="#D9D6CE" stroke-width="2"/>'
                   f'<path d="M38,160 L98,160" stroke="{RED}" stroke-width="9" stroke-linecap="round" stroke-dasharray="2 14"/></g>')
        label(112, 168, "行き（国道11号→入口→駐車場）", 20, RED, halo=False)
        label(38, 206, "×　入らないでください（集落の道）", 20, RED, halo=False)
    else:
        out.append(f'<g><rect x="20" y="130" width="450" height="92" rx="8" fill="{CREAM}" stroke="#D9D6CE" stroke-width="2"/>'
                   f'<path d="M38,160 L98,160" stroke="{PURPLE}" stroke-width="8" stroke-linecap="round"/></g>')
        label(112, 168, "帰り（駐車場→会場の東→県道41号）", 20, PURPLE, halo=False)
        label(38, 206, "お寺の駐車場の方は、誘導員の案内に従ってください", 17, NAVY, halo=False)
    out.append(f'<g transform="translate(60,70)"><path d="M0,-34 L12,6 L0,0 L-12,6Z" fill="{NAVY}"/><text y="34" font-size="22" text-anchor="middle" fill="{NAVY}" {T}>N</text></g>')
    label(W - 14, H - 12, "地図データ © OpenStreetMap contributors", 15, GRAY, "end")
    out.append("</svg>")
    (ROOT / "assets" / "img" / f"access-map-{mode}.svg").write_text("\n".join(out), encoding="utf-8", newline="\n")

for mode in ("go", "back"):
    build(mode)
print("ok", W, H, len(crosses), "crosses")
