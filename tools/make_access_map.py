"""会場までの略図（assets/img/access-map.svg）を、OpenStreetMapの道の形から作る。

2026-11-17。11/16に地元の佐藤さんと確かめた「国道11号から会場への入口は、県道41号との分かれ道（ヘアピンカーブ）の1か所だけ。
集落の細い道には入らない」を伝えるための図。道の形は tools/access-map-osm.json（Overpass APIで取ったもの）。
帰りの道は11/19の警備の打ち合わせの後に足す。

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
       '<desc id="d">国道11号を通り、県道41号との分かれ道（ヘアピンカーブ）からだけ会場へ入る。国道11号から集落の細い道には入らない。</desc>',
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
ag = [p for p in ag if p["lat"] <= top + 0.0002]
out.append(f'<path d="{path(ag)}" fill="none" stroke="{RED}" stroke-width="10" stroke-linecap="round" stroke-dasharray="2 16"/>')
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
label(sx + 120, sy - 10, "会場", 40, RED)
label(sx + 120, sy + 28, "TODAベリーファーム", 24, NAVY)
label(sx + 120, sy + 58, "（旧北灘西小学校）", 24, NAVY)
# 入口
label(jx - 30, jy + 70, "★ 入口はここだけ", 32, RED, "end")
label(jx - 30, jy + 108, "（ヘアピンカーブ）", 24, RED, "end")
# 道と方面
label(W - 20, 128, "鳴門方面 →", 28, NAVY, "end")
label(20, H - 40, "← 引田方面", 28, NAVY)
label(xy(34.2101, 134.4836)[0] + 22, H - 40, "県道41号 ↓ 大麻方面", 26, GRAY)
label(xy(34.2176, 134.4838)[0] - 10, xy(34.2176, 134.4838)[1] + 5, "国道11号", 28, NAVY, "end")
# 方位と出典
out.append(f'<g transform="translate(60,70)"><path d="M0,-34 L12,6 L0,0 L-12,6Z" fill="{NAVY}"/><text y="34" font-size="22" text-anchor="middle" fill="{NAVY}" {T}>N</text></g>')
label(W - 14, H - 12, "地図データ © OpenStreetMap contributors", 15, GRAY, "end")
out.append("</svg>")
(ROOT / "assets" / "img" / "access-map.svg").write_text("\n".join(out), encoding="utf-8", newline="\n")
print("ok", W, H, len(crosses), "crosses")
