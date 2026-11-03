"""Draw the conceptual schema (MultiDim notation) as SVG.

Usage: uv run python scripts/conceptual_schema.py   -> docs/figures/conceptual_schema.svg
The PNG used in the README is the same drawing exported from a browser.
"""
import sys
from pathlib import Path

W, H = 1500, 1080
NAVY, NAVY2, INK, INK2, RULE, BG = "#0d2238", "#14304f", "#0f1419", "#48515a", "#c9d1d9", "#ffffff"
ORANGE, GREEN, BURG, TEAL = "#e8743b", "#1f9d6b", "#8c2f45", "#2a6f97"
F = "IBM Plex Sans, Segoe UI, Arial, sans-serif"
M = "IBM Plex Mono, Consolas, monospace"
out = []
add = out.append


def text(x, y, s, size=14, fill=INK, weight=400, anchor="start", font=F, italic=False):
    st = ' font-style="italic"' if italic else ""
    add(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}" font-weight="{weight}" text-anchor="{anchor}"{st}>{s}</text>')


def level(x, y, name, key, attrs, w=210, spatial=False, color=TEAL):
    """A MultiDim level: name band, identifier (underlined), attributes."""
    h = 34 + 22 * (1 + len(attrs)) + 10
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{BG}" stroke="{color}" stroke-width="1.6"/>')
    add(f'<path d="M{x} {y+6} a6 6 0 0 1 6 -6 h{w-12} a6 6 0 0 1 6 6 v28 h-{w} z" fill="{color}"/>')
    text(x + 12, y + 22, name, 15, "#ffffff", 600)
    if spatial:  # spatial level marker (MultiDim uses a pictogram)
        add(f'<g transform="translate({x+w-30},{y+8})"><rect width="18" height="18" rx="3" fill="none" stroke="#ffffff" stroke-width="1.4"/>'
            f'<path d="M3 13 L8 6 L12 11 L15 8" fill="none" stroke="#ffffff" stroke-width="1.4"/></g>')
    yy = y + 56
    text(x + 12, yy, key, 13, INK, 500, font=M)
    add(f'<line x1="{x+12}" y1="{yy+3}" x2="{x+12+7.8*len(key)}" y2="{yy+3}" stroke="{INK}" stroke-width="1"/>')
    for a in attrs:
        yy += 22
        text(x + 12, yy, a, 13, INK2, font=M)
    return (x, y, w, h)


def fact(x, y, name, measures, w=250, spatial=None):
    h = 40 + 22 * len(measures) + (34 if spatial else 0) + 12
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{NAVY}" stroke="{NAVY}"/>')
    text(x + w / 2, y + 26, name, 17, "#ffffff", 600, "middle")
    add(f'<line x1="{x+14}" y1="{y+38}" x2="{x+w-14}" y2="{y+38}" stroke="#2b4a6c"/>')
    yy = y + 60
    for m in measures:
        text(x + 16, yy, m, 13, "#dfe8f1", font=M)
        yy += 22
    if spatial:
        add(f'<rect x="{x+12}" y="{yy-14}" width="{w-24}" height="26" rx="5" fill="{NAVY2}" stroke="{ORANGE}"/>')
        text(x + 22, yy + 4, spatial, 12.5, "#ffd9c4", font=M)
    return (x, y, w, h)


def edge(a, b, label=None, card=("", ""), lx=0, ly=0, dash=False):
    (x1, y1), (x2, y2) = a, b
    d = ' stroke-dasharray="5 4"' if dash else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{INK2}" stroke-width="1.4"{d}/>')
    if label:
        mx, my = x1 + (x2 - x1) * 0.78 + lx, y1 + (y2 - y1) * 0.78 + ly  # near the dimension end
        add(f'<rect x="{mx-4-3.6*len(label)}" y="{my-12}" width="{8+7.2*len(label)}" height="18" rx="4" fill="#f3f5f7"/>')
        text(mx, my + 1, label, 12, INK2, 500, "middle", italic=True)
    for (cx, cy), c in ((a, card[0]), (b, card[1])):
        if c:
            pass


def hier(a, b, name):
    """Hierarchy link between child level a (bottom/left) and parent b, with criterion name."""
    (x1, y1), (x2, y2) = a, b
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{TEAL}" stroke-width="1.6"/>')
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    add(f'<path d="M{mx-9} {my} L{mx} {my-9} L{mx+9} {my} L{mx} {my+9} Z" fill="#ffffff" stroke="{TEAL}" stroke-width="1.4"/>')
    text(mx, my + 26, name, 12, TEAL, 500, "middle", italic=True)


add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
add(f'<rect width="{W}" height="{H}" fill="#f3f5f7"/>')
text(40, 52, "Conceptual schema", 24, INK, 600)
text(40, 78, "MultiDim notation (Vaisman &amp; Zimányi). Two fact relationships share four dimensions; the trip fact uses Time and Cell in two roles each.", 14, INK2)

# facts
P = fact(300, 430, "Position", ["SpeedOverGround (kn)", "CourseOverGround (°)", "Heading (°)"], spatial="Location: point")
T = fact(950, 430, "Trip", ["NoReports", "Duration (min)", "Length (km)", "AvgSpeed (kn)"], spatial="Trajectory: tgeompoint")

# dimensions
S = level(625, 130, "Ship", "MMSI", ["Name", "IMO", "Callsign", "Length, Width"], w=250)
ST = level(330, 150, "ShipType", "TypeName", [], w=170, color=GREEN)
TC = level(1000, 150, "Transponder", "Class", [], w=170, color=GREEN)
N = level(40, 450, "NavStatus", "StatusName", [], w=180)
TI = level(420, 700, "Hour", "HourKey", ["Hour (0-23)"])
DP = level(230, 880, "DayPart", "PartName", [], w=160, color=GREEN)
DY = level(560, 880, "Day", "Date", [], w=160, color=GREEN)
C = level(870, 700, "Cell", "CellKey", ["Row, Col", "LatMin, LonMin"], w=220, spatial=True)

# ship hierarchies (horizontal links)
hier((S[0], S[1] + 62), (ST[0] + ST[2], ST[1] + 42), "Type")
hier((S[0] + S[2], S[1] + 62), (TC[0], TC[1] + 42), "Class")
# time hierarchies
hier((TI[0] + 40, TI[1] + TI[3]), (DP[0] + DP[2] / 2, DP[1]), "Part of day")
hier((TI[0] + TI[2] - 40, TI[1] + TI[3]), (DY[0] + DY[2] / 2, DY[1]), "Calendar")

# fact links
edge((P[0] + P[2] - 30, P[1]), (S[0] + 50, S[1] + S[3]))
edge((T[0] + 30, T[1]), (S[0] + S[2] - 50, S[1] + S[3]))
edge((P[0], P[1] + 70), (N[0] + N[2], N[1] + 40))
edge((P[0] + 70, P[1] + P[3]), (TI[0] + 60, TI[1]))
edge((P[0] + P[2] - 40, P[1] + P[3]), (C[0] + 40, C[1]))
edge((T[0] + 40, T[1] + T[3]), (TI[0] + TI[2] - 30, TI[1]), "StartTime", lx=10, ly=-12)
edge((T[0] + 100, T[1] + T[3]), (TI[0] + TI[2], TI[1] + 40), "EndTime", lx=40, ly=16)
edge((T[0] + T[2] - 90, T[1] + T[3]), (C[0] + C[2] - 60, C[1]), "StartCell", lx=-4, ly=-6)
edge((T[0] + T[2] - 20, T[1] + T[3]), (C[0] + C[2], C[1] + 40), "EndCell", lx=36, ly=-8)

# legend
ly = 1000
add(f'<rect x="40" y="{ly-22}" width="26" height="18" rx="5" fill="{NAVY}"/>'); text(74, ly-8, "Fact relationship with measures", 12.5, INK2)
add(f'<rect x="300" y="{ly-22}" width="26" height="18" rx="3" fill="#fff" stroke="{TEAL}" stroke-width="1.6"/>'); text(334, ly-8, "Level (underlined = identifier)", 12.5, INK2)
add(f'<path d="M565 {ly-13} l9 -9 l9 9 l-9 9 z" fill="#fff" stroke="{TEAL}" stroke-width="1.4"/>'); text(590, ly-8, "Hierarchy, named by its criterion (child to parent, many to one)", 12.5, INK2)
add(f'<rect x="1000" y="{ly-22}" width="26" height="18" rx="4" fill="{NAVY2}" stroke="{ORANGE}"/>'); text(1034, ly-8, "Spatial or temporal measure", 12.5, INK2)
text(40, ly + 22, "Grain: Position = one ship at one second (9,145,393 rows). Trip = one ship's movement until a reporting gap of more than 30 minutes (4,488 rows). Cell = 0.25° grid over 53-59 N, 2-17 E.", 12.5, INK2)
text(40, ly + 44, "Implemented as a star schema in sql/40_star_schema.sql: dim_ship (type and class kept as attributes), dim_time (hour, day_part, day), dim_cell, dim_nav_status, fact_position, fact_trip.", 12.5, INK2)
add("</svg>")
target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "docs" / "figures" / "conceptual_schema.svg"
target.write_text("\n".join(out), encoding="utf-8")
print(f"Wrote {target}")
