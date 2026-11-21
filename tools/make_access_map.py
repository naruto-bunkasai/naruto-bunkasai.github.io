"""会場までの略図（assets/img/access-map.svg）を、OpenStreetMapの道の形から作る。

2026-11-17。11/16に地元の佐藤さんと確かめた「国道11号から会場への入口は、県道41号との分かれ道（ヘアピンカーブ）の1か所だけ。
集落の細い道には入らない」を伝えるための図。道の形は tools/access-map-osm.json（Overpass APIで取ったもの）。
2026-11-21：帰りの道（紫の線）を足した。11/19の警備（アリス警備さん）の打ち合わせで、お寺の駐車場に停めた人以外は全員、
会場の北から東を回って県道41号へ出る（莉奈さん 11/19 18:31「学校周りを一周回って同じルート」と、警備員の配置図から読んだ。莉奈さんに確認中）。

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

J = (34.2137527, 134.481479)            # 国道11号と県道41号の分かれ道（入口）
ACCESS_WAY = 181040807                  # 県道41号から会場の西側を北へ上がる道（入口からの道）
SEA_SIDE_AT_J = 181040855               # 分かれ道から海側へ入る細い道

els = [e for e in d["elements"] if e.get("geometry")]
trunk = [e for e in els if e.get("tags", {}).get("highway") == "trunk"]
prim = [e for e in els if e.get("tags", {}).get("highway") == "primary"]
small = [e for e in els if e.get("tags", {}).get("highway") in ("residential", "unclassified")]
river = [e for e in els if e.get("tags", {}).get("name") == "折野川" and e["type"] == "way"]
school = next(e for e in els if e.get("tags", {}).get("amenity") == "school")
access = next(e for e in els if e["id"] == ACCESS_WAY)

trunk_pts = {(round(p["lat"], 7), round(p["lon"], 7)) for e in trunk for p in e["geometry"]}
inside = lambda la, lo: B[0] < la < B[2] and B[1] < lo < B[3]

# 国道11号から細い道が分かれる所（入口の分かれ道を除く）に × を付ける
crosses = set()
for e in small:
    for p in e["geometry"]:
        k = (round(p["lat"], 7), round(p["lon"], 7))
        x_, y_ = xy(*k)
        if x_ > W - 150 and y_ < 90: continue              # 「鳴門方面」の文字と重なる端は描かない
        if k in trunk_pts and inside(*k) and (abs(k[0] - J[0]) > 1e-6 or e["id"] == SEA_SIDE_AT_J):
            if e["id"] == SEA_SIDE_AT_J:
                g = e["geometry"]; k = (g[1]["lat"], g[1]["lon"])   # 分かれ道のすぐ海側に置く
            crosses.add(k)

NAVY, RED, GRAY = "#14285A", "#C8323C", "#5E6478"
out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">',
       '<title id="t">会場までの略図</title>',
       '<desc id="d">国道11号を通り、県道41号との分かれ道（ヘアピンカーブ）からだけ会場へ入る。国道11号から集落の細い道には入らない。帰りは会場の北から東を回って県道41号へ出て、大麻方面は南へ、鳴門・引田方面は分かれ道へ戻って国道11号へ。</desc>',
       f'<rect width="{W}" height="{H}" fill="#FDFBF4"/>',
       '<g fill="none" stroke-linecap="round" stroke-linejoin="round">']
for e in river: out.append(f'<path d="{path(e["geometry"])}" stroke="#A9D3EE" stroke-width="5"/>')
for e in small: out.append(f'<path d="{path(e["geometry"])}" stroke="#D9D6CE" stroke-width="5"/>')
for e in prim: out.append(f'<path d="{path(e["geometry"])}" stroke="{GRAY}" stroke-width="11"/>')
for e in trunk: out.append(f'<path d="{path(e["geometry"])}" stroke="{NAVY}" stroke-width="16"/>')
out.append('</g>')
# 会場
out.append(f'<path d="{path(school["geometry"])}Z" fill="#F6E3E3" stroke="{RED}" stroke-width="4"/>')
# 入口からの道（赤の点線）。会場の北西の角まで（その先は描かない）
top = min(p["lat"] for p in school["geometry"]) + 0.85 * (max(p["lat"] for p in school["geometry"]) - min(p["lat"] for p in school["geometry"]))
ag = list(access["geometry"])
if ag[0]["lat"] > ag[-1]["lat"]: ag.reverse()          # 入口（南）から北へ
# 2026-11-21：行きと帰りが混ざって見えると言われたので、行きは駐車場（帰り道の出発点）まで伸ばし、矢印を付ける
out.append(f'<defs><marker id="ahr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="3" markerHeight="3" orient="auto"><path d="M0,0 L10,5 L0,10Z" fill="{RED}"/></marker></defs>')
out.append(f'<path d="{path(ag)}" fill="none" stroke="{RED}" stroke-width="10" stroke-linecap="round" stroke-dasharray="2 16" marker-end="url(#ahr)"/>')
# × 印
for la, lo in sorted(crosses):
    x, y = xy(la, lo); r = 13
    out.append(f'<g stroke="#fff" stroke-width="12" stroke-linecap="round"><path d="M{x-r:.1f},{y-r:.1f}L{x+r:.1f},{y+r:.1f}M{x+r:.1f},{y-r:.1f}L{x-r:.1f},{y+r:.1f}"/></g>')
    out.append(f'<g stroke="{RED}" stroke-width="6" stroke-linecap="round"><path d="M{x-r:.1f},{y-r:.1f}L{x+r:.1f},{y+r:.1f}M{x+r:.1f},{y-r:.1f}L{x-r:.1f},{y+r:.1f}"/></g>')
# 入口 ★
jx, jy = xy(*J)
def star(cx, cy, R, r):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5; rr = R if i % 2 == 0 else r
        pts.append(f"{cx + rr * math.cos(a):.1f},{cy + rr * math.sin(a):.1f}")
    return " ".join(pts)
out.append(f'<polygon points="{star(jx, jy, 30, 13)}" fill="#F3D774" stroke="{RED}" stroke-width="4"/>')

T = 'font-family="Shippori Mincho, Hiragino Mincho ProN, Yu Mincho, serif" font-weight="700"'
def label(x, y, text, size=30, fill=NAVY, anchor="start", halo=True):
    s = f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" {T}'
    if halo: out.append(s + f' stroke="#FDFBF4" stroke-width="8" paint-order="stroke">{text}</text>')
    else: out.append(s + f'>{text}</text>')
# 会場の名前
sx = sum(xy(p["lat"], p["lon"])[0] for p in school["geometry"]) / len(school["geometry"])
sy = sum(xy(p["lat"], p["lon"])[1] for p in school["geometry"]) / len(school["geometry"])
# 2026-11-21：帰り道（紫）と重ならないよう、「会場」は建物の上に、名前は右下の空いた所に置く
label(sx, sy + 12, "会場", 34, RED, "middle")
label(640, 742, "会場：TODAベリーファーム", 22, NAVY)
label(640, 772, "（旧北灘西小学校）", 22, NAVY)
# 入口
# 文字の★は地図の★と形も色も違って見えるので使わない。引き出し線で★につなぐ
lx, ly = jx - 75, jy - 120                         # 海側の空いている所（左上）に置く
out.append(f'<path d="M{jx-4:.0f},{jy-34:.0f} L{lx+6:.0f},{ly+48:.0f}" stroke="{RED}" stroke-width="3" fill="none"/>')
label(lx + 10, ly + 4, "入口はここだけ", 32, RED, "end")
label(lx + 10, ly + 40, "（ヘアピンカーブ）", 24, RED, "end")
# 道と方面
label(W - 20, 128, "鳴門方面 →", 28, NAVY, "end")
label(20, H - 40, "← 引田方面", 28, NAVY)
label(xy(34.2101, 134.4836)[0] + 22, H - 40, "県道41号 ↓ 大麻方面", 26, GRAY)
label(xy(34.2176, 134.4838)[0] - 10, xy(34.2176, 134.4838)[1] + 5, "国道11号", 28, NAVY, "end")
# 帰りの道（紫）。会場の北（入口からの道の終わり）→東の道を南へ→県道41号に出る→大麻方面は南へ、鳴門・引田方面は分かれ道へ戻って国道11号へ
PURPLE = "#6B48B3"
W_ = {e["id"]: e for e in els}
def chain(ids):
    pts = []
    for i in ids:
        g = [(p["lat"], p["lon"]) for p in W_[i]["geometry"]]
        if pts:
            d0 = (g[0][0]-pts[-1][0])**2 + (g[0][1]-pts[-1][1])**2
            d1 = (g[-1][0]-pts[-1][0])**2 + (g[-1][1]-pts[-1][1])**2
            if d1 < d0: g.reverse()
        pts += g
    return pts
loop = chain([181040724, 181040956, 181040916, 181041015, 181040900])
p41 = [(p["lat"], p["lon"]) for p in W_[675645609]["geometry"]]
k = min(range(len(p41)), key=lambda i: (p41[i][0]-loop[-1][0])**2 + (p41[i][1]-loop[-1][1])**2)
to_j = p41[k:]                       # 県道41号を分かれ道（入口）へ戻る
to_south = list(reversed(p41[k-5:k+1]))   # 大麻方面へ
# 2026-11-21：★に矢印が刺さると事故のように見えると言われたので、★の手前で線を止め、★の先から国道11号の両方向へ矢印を出す
jx0, jy0 = xy(*J)
def px(pts): return [xy(a, b) for a, b in pts]
def cut_before(P, R):                # P（ピクセル）の終わりを、★から半径Rの手前で止める
    outp = [P[0]]
    for a, b in zip(P, P[1:]):
        if math.hypot(b[0]-jx0, b[1]-jy0) >= R: outp.append(b); continue
        t0, t1 = 0.0, 1.0
        for _ in range(30):
            m = (t0 + t1) / 2; q = (a[0]+(b[0]-a[0])*m, a[1]+(b[1]-a[1])*m)
            if math.hypot(q[0]-jx0, q[1]-jy0) > R: t0 = m
            else: t1 = m
        outp.append((a[0]+(b[0]-a[0])*t0, a[1]+(b[1]-a[1])*t0)); break
    return outp
def walk(P, R0, R1):                 # ★から外へ向かう点列Pの、半径R0〜R1の部分
    seg = []
    for a, b in zip(P, P[1:]):
        for m in [x/20 for x in range(21)]:
            q = (a[0]+(b[0]-a[0])*m, a[1]+(b[1]-a[1])*m)
            d = math.hypot(q[0]-jx0, q[1]-jy0)
            if R0 <= d <= R1: seg.append(q)
            if d > R1: return seg
    return seg
tg = min(trunk, key=lambda e: min(math.hypot(xy(p["lat"], p["lon"])[0]-jx0, xy(p["lat"], p["lon"])[1]-jy0) for p in e["geometry"]))   # ★を通る国道11号の区間
tp = px([(p["lat"], p["lon"]) for p in tg["geometry"]])
ti = min(range(len(tp)), key=lambda i: math.hypot(tp[i][0]-jx0, tp[i][1]-jy0))
to_11a = walk(tp[ti:], 46, 125)                 # 国道11号を一方へ
to_11b = walk(list(reversed(tp[:ti+1])), 46, 125)   # 国道11号をもう一方へ
segs = [px(loop), cut_before(px(to_j), 46), px(to_south), to_11a, to_11b]
def ppx(P): return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in P)
out.append(f'<defs><marker id="ah" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="3.2" markerHeight="3.2" orient="auto"><path d="M0,0 L10,5 L0,10Z" fill="{PURPLE}"/></marker></defs>')
for i_, P in enumerate(segs):
    if i_ < 3: out.append(f'<path d="{ppx(P)}" fill="none" stroke="#FDFBF4" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>')
for i_, P in enumerate(segs):
    end = "" if i_ == 1 else ' marker-end="url(#ah)"'          # ★の手前で止める線には矢印を付けない
    out.append(f'<path d="{ppx(P)}" fill="none" stroke="{PURPLE}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"{end}/>')
mx, my = xy(*loop[len(loop)//2])
label(mx + 24, my, "帰り", 30, PURPLE)
label(mx + 24, my + 32, "（会場の東を回る）", 22, PURPLE)
label(545, 592, "鳴門・引田方面は", 20, PURPLE, "end")
label(545, 618, "入口の分かれ道から", 20, PURPLE, "end")
label(545, 644, "国道11号へ", 20, PURPLE, "end")
# 駐車場（行きの終わり＝帰りの出発点）
sx0, sy0 = xy(*loop[0])
out.append(f'<circle cx="{sx0:.1f}" cy="{sy0:.1f}" r="19" fill="{NAVY}" stroke="#FDFBF4" stroke-width="4"/>')
out.append(f'<text x="{sx0:.1f}" y="{sy0+8:.1f}" font-size="24" text-anchor="middle" fill="#fff" font-family="sans-serif" font-weight="700">P</text>')
label(sx0, sy0 - 30, "駐車場", 22, NAVY, "middle")
# 行きのラベル
label(545, 398, "行き", 26, RED)
# 凡例（地図の中）
out.append(f'<g><rect x="20" y="130" width="330" height="92" rx="8" fill="#FDFBF4" stroke="#D9D6CE" stroke-width="2"/>'
           f'<path d="M38,160 L98,160" stroke="{RED}" stroke-width="9" stroke-linecap="round" stroke-dasharray="2 14"/>'
           f'<path d="M38,198 L98,198" stroke="{PURPLE}" stroke-width="8" stroke-linecap="round"/></g>')
label(112, 168, "行き（入口→駐車場）", 20, RED, halo=False)
label(112, 206, "帰り", 20, PURPLE, halo=False)
# 方位と出典
out.append(f'<g transform="translate(60,70)"><path d="M0,-34 L12,6 L0,0 L-12,6Z" fill="{NAVY}"/><text y="34" font-size="22" text-anchor="middle" fill="{NAVY}" {T}>N</text></g>')
label(W - 14, H - 12, "地図データ © OpenStreetMap contributors", 15, GRAY, "end")
out.append("</svg>")
(ROOT / "assets" / "img" / "access-map.svg").write_text("\n".join(out), encoding="utf-8", newline="\n")
print("ok", W, H, len(crosses), "crosses")
