"""Detroit-shaped isometric map. Geometry in lon/lat (approximate) -> world units -> iso SVG.
Swap CITY / DISTRICTS for the real council_districts_2026.geojson when it lands."""
import random, math
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union

W_LON, E_LON, S_LAT, N_LAT = -83.30, -82.90, 42.245, 42.455
KX = 86/(E_LON-W_LON); KY = 60/(N_LAT-S_LAT)
def w(lon,lat): return ((lon-W_LON)*KX, (N_LAT-lat)*KY)
S=11.0; C=0.866
def iso(x,y,z=0): return ((x+0.22*y)*S*1.0, y*S*0.80 - z*S*0.9)
def J(pts): return " ".join(f"{a:.1f},{b:.1f}" for a,b in pts)
def ring(poly,z=0): return [iso(*w(lon,lat),z) for lon,lat in poly.exterior.coords]
def ringw(poly,z=0): return [iso(x,y,z) for x,y in poly.exterior.coords]

# ---- approximate geometry (lon, lat) ----
CITY_LL=[(-83.287,42.4502),(-82.968,42.4502),(-82.948,42.4440),(-82.910,42.4180),(-82.925,42.3900),(-82.945,42.3570),
 (-82.990,42.3440),(-83.045,42.3280),(-83.080,42.3100),(-83.120,42.2900),(-83.160,42.2580),(-83.178,42.2780),
 (-83.150,42.3050),(-83.140,42.3200),(-83.155,42.3450),(-83.210,42.3520),(-83.287,42.3550)]
HAMTRAMCK_LL=[(-83.080,42.4130),(-83.040,42.4130),(-83.040,42.3830),(-83.070,42.3830),(-83.080,42.3930)]
HIGHLAND_LL=[(-83.125,42.4170),(-83.085,42.4170),(-83.085,42.3930),(-83.110,42.3930),(-83.125,42.4030)]
REGIONS={
 1:[(-83.40,42.385),(-83.195,42.385),(-83.195,42.50),(-83.40,42.50)],
 2:[(-83.195,42.405),(-83.06,42.405),(-83.06,42.50),(-83.195,42.50)],
 3:[(-83.06,42.395),(-82.80,42.395),(-82.80,42.50),(-83.06,42.50)],
 4:[(-83.00,42.20),(-82.80,42.20),(-82.80,42.395),(-83.00,42.395)],
 5:[(-83.058,42.20),(-83.00,42.20),(-83.00,42.395),(-83.06,42.395),(-83.06,42.405),(-83.12,42.405),(-83.12,42.335),(-83.058,42.335)],
 6:[(-83.40,42.20),(-83.058,42.20),(-83.058,42.335),(-83.40,42.335)],
 7:[(-83.40,42.335),(-83.12,42.335),(-83.12,42.405),(-83.195,42.405),(-83.195,42.385),(-83.40,42.385)],
}
DCOL={1:"#F59E0B",2:"#10B981",3:"#EF4444",4:"#A371F7",5:"#4C8DFF",6:"#DB61A2",7:"#2EC4B6"}
def toW(pts): return Polygon([w(*p) for p in pts])
HOLES=unary_union([toW(HAMTRAMCK_LL),toW(HIGHLAND_LL)])
CITY=toW(CITY_LL).difference(HOLES)
DIST={d:toW(r).intersection(CITY) for d,r in REGIONS.items()}
def dist_of(pt):
    for d,g in DIST.items():
        if g.contains(pt): return d
    return None

ARTS=[ # name, load, lon/lat polyline
 ("Michigan Ave",0.32,[(-83.046,42.331),(-83.090,42.331),(-83.150,42.326),(-83.210,42.318)]),
 ("Woodward Ave",0.41,[(-83.046,42.331),(-83.065,42.360),(-83.085,42.385),(-83.110,42.418),(-83.135,42.4502)]),
 ("Gratiot Ave",0.47,[(-83.046,42.334),(-83.020,42.355),(-82.990,42.385),(-82.968,42.4502)]),
 ("Grand River Ave",0.44,[(-83.050,42.334),(-83.090,42.355),(-83.160,42.390),(-83.240,42.430),(-83.270,42.4502)]),
 ("W Vernor Hwy",0.55,[(-83.070,42.325),(-83.100,42.315),(-83.135,42.300)]),
 ("I-94",0.62,[(-83.200,42.360),(-83.120,42.365),(-83.070,42.370),(-83.000,42.380),(-82.930,42.400)]),
 ("Jefferson Ave",0.38,[(-83.040,42.331),(-82.990,42.346),(-82.950,42.360)]),
]
MC_LL=(-83.0777,42.3289); NL_LL=(-83.0745,42.3305); RC_LL=(-83.0395,42.3293)
ROUTE_LL=[MC_LL,(-83.060,42.336),(-83.030,42.346),(-83.000,42.356),(-82.975,42.362)]
ROUTE=[w(*p) for p in ROUTE_LL]
BAND=LineString(ROUTE).buffer(2.4, cap_style=1)
RIVER_LL=[(-82.945,42.357),(-82.990,42.344),(-83.045,42.328),(-83.080,42.310),(-83.120,42.290),(-83.160,42.258),
 (-83.17,42.235),(-83.13,42.235),(-83.08,42.270),(-83.03,42.300),(-82.97,42.320),(-82.90,42.345),(-82.90,42.37)]
BELLE_LL=[(-82.995,42.343),(-82.975,42.348),(-82.958,42.341),(-82.978,42.335)]

def loadcol(l,P): return P["light"] if l<.5 else P["busy"] if l<.75 else P["heavy"] if l<.9 else P["full"]

def chip(X,Y,text,color,P,LS,sub=None):
    f1=15*LS; f2=13*LS
    wd=len(text)*f1*0.58+(f1*2 if color else f1*1.6)
    if sub: wd=max(wd,len(sub)*f2*0.58+f1*2)
    h=(f1+f2+18*LS) if sub else (f1+16*LS); rx=X-wd/2
    s=f'<rect x="{rx:.1f}" y="{Y-h/2:.1f}" width="{wd:.0f}" height="{h:.0f}" rx="{8*LS:.0f}" fill="{P["chip"]}" fill-opacity="0.94" stroke="{P["chipline"]}"></rect>'
    tx=rx+(f1*1.6 if color else f1*0.8)
    if color: s+=f'<circle cx="{rx+f1*0.85:.1f}" cy="{Y-(f2*0.55 if sub else 0):.1f}" r="{5*LS:.1f}" fill="{color}"></circle>'
    if sub: s+=f'<text x="{tx:.1f}" y="{Y-2*LS:.1f}" fill="{P["chiptext"]}" font-size="{f1:.0f}" font-weight="600">{text}</text><text x="{tx:.1f}" y="{Y+f2+2*LS:.1f}" fill="{P["chipsub"]}" font-size="{f2:.0f}">{sub}</text>'
    else: s+=f'<text x="{tx:.1f}" y="{Y+f1*0.35:.1f}" fill="{P["chiptext"]}" font-size="{f1:.0f}" font-weight="600">{text}</text>'
    return s

def build(P, LS=1.4, seed=1114, tagged=True):
    random.seed(seed); o=[]
    # river + Belle Isle
    o.append(f'<polygon points="{J(ring(Polygon(RIVER_LL)))}" fill="{P["water"]}"></polygon>')
    o.append(f'<polygon points="{J(ring(Polygon(BELLE_LL)))}" fill="{P["park"]}"></polygon>')
    # city ground (streets show through gaps)
    o.append(f'<polygon points="{J(ringw(toW(CITY_LL)))}" fill="{P["street"]}"></polygon>')
    for h in [toW(HAMTRAMCK_LL),toW(HIGHLAND_LL)]:
        o.append(f'<polygon points="{J(ringw(h))}" fill="{P["enclave"]}"></polygon>')
    # district tints
    for d,g in DIST.items():
        for part in getattr(g,"geoms",[g]):
            o.append(f'<polygon class="dz" data-d="{d}" points="{J(ringw(part))}" fill="{DCOL[d]}" fill-opacity="0.10"></polygon>')
    # proposal band
    o.append(f'<g class="proposal"><polygon points="{J(ringw(BAND))}" fill="{P["band"]}" fill-opacity="0.1" stroke="{P["band"]}" stroke-opacity="0.45" stroke-width="1.2" stroke-dasharray="5 4"></polygon></g>')
    # arterials
    for name,l,pts in ARTS:
        pp=[iso(*w(*p)) for p in pts]; c=loadcol(l,P)
        o.append(f'<polyline points="{J(pp)}" fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"></polyline><polyline points="{J(pp)}" fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"></polyline>')
    art_lines=[LineString([w(*p) for p in pts]).buffer(0.6) for _,_,pts in ARTS]
    art_u=unary_union(art_lines)
    # blocks + buildings
    mc=Point(w(*MC_LL)); dt=Point(w(*RC_LL)); bl=[]; blds=[]
    parks=[(-83.240,42.370,4),(-83.140,42.345,2.5),(-83.200,42.420,2.5)]
    park_geoms=[Point(w(lo,la)).buffer(r) for lo,la,r in parks]
    for gx in range(0,86,4):
        for gy in range(0,60,4):
            cell=box(gx+0.45,gy+0.45,gx+3.55,gy+3.55)
            c=cell.centroid
            if not CITY.contains(c): continue
            cell=cell.difference(art_u)
            if cell.geom_type=="MultiPolygon": cell=max(cell.geoms,key=lambda q:q.area)
            if cell.is_empty or cell.area<2 or cell.geom_type!="Polygon": continue
            park=any(pg.contains(c) for pg in park_geoms)
            bl.append((cell,park))
            if park: continue
            ddt=c.distance(dt)
            x0,y0,x1,y1=cell.bounds
            n=2 if (x1-x0)>2 and (y1-y0)>2 else 1
            lw=(x1-x0)/n; lh=(y1-y0)/n
            for p in range(n):
                for q in range(n):
                    if random.random()<0.3 and ddt>4: continue
                    bx0=x0+p*lw+0.2; by0=y0+q*lh+0.2
                    fp=box(bx0,by0,bx0+lw*random.uniform(.5,.8),by0+lh*random.uniform(.5,.8))
                    if not cell.contains(fp.centroid) or fp.centroid.distance(mc)<1.6: continue
                    if ddt<3: h=random.uniform(2.5,8)
                    elif ddt<6: h=random.uniform(1,3)
                    else: h=random.choice([.35,.4,.45,.5,.6,.75]) if random.random()<.92 else random.uniform(.9,1.6)
                    blds.append((fp,h,None))
    m=Point(w(*MC_LL)); blds.append((box(m.x-1.1,m.y-0.9,m.x+1.1,m.y+0.9),4.2,"mc"))
    n_=Point(w(*NL_LL)); blds.append((box(n_.x+1.3,n_.y-0.6,n_.x+2.6,n_.y+0.9),0.9,"nl"))
    r=Point(w(*RC_LL)); blds.append((box(r.x-0.5,r.y-0.5,r.x+0.5,r.y+0.5),12,"rc"))
    for cell,park in bl:
        o.append(f'<polygon points="{J(ringw(cell))}" fill="{P["park"] if park else P["block"]}"></polygon>')
    for fp,h,sp in sorted(blds,key=lambda b:(round(b[0].bounds[3],1),b[0].bounds[0])):
        x0,y0,x1,y1=fp.bounds
        top=[iso(x0,y0,h),iso(x1,y0,h),iso(x1,y1,h),iso(x0,y1,h)]
        fx=[iso(x1,y0),iso(x1,y1),iso(x1,y1,h),iso(x1,y0,h)]; fy=[iso(x0,y1),iso(x1,y1),iso(x1,y1,h),iso(x0,y1,h)]
        k="nl" if sp=="nl" else "mc" if sp in("mc","rc") else "ib" if BAND.contains(fp.centroid) else "b"
        t,sx,sy=P[k]
        o.append(f'<polygon points="{J(fx)}" fill="{sx}"></polygon><polygon points="{J(fy)}" fill="{sy}"></polygon><polygon points="{J(top)}" fill="{t}"></polygon>')
    # residents
    n=0
    while n<420:
        x=random.uniform(0,86); y=random.uniform(0,60); pt=Point(x,y)
        if not CITY.contains(pt): continue
        n+=1; ib=BAND.contains(pt); rr=random.random()
        st=("s" if rr<.58 else "n" if rr<.76 else "o") if ib else ("s" if rr<.38 else "n" if rr<.68 else "o")
        X,Y=iso(x,y,.15)
        o.append(f'<circle class="res res-{st}" cx="{X:.1f}" cy="{Y:.1f}" r="2.8" fill="{P[st]}" stroke="#FFFFFF" stroke-width="0.8"></circle>')
    # dim overlays for unselected districts (toggled by the picker)
    for d,g in DIST.items():
        for part in getattr(g,"geoms",[g]):
            o.append(f'<polygon class="dim" data-d="{d}" points="{J(ringw(part))}" fill="{P["dim"]}" fill-opacity="0.62"></polygon>')
    # district outlines, then city outline
    for d,g in DIST.items():
        for part in getattr(g,"geoms",[g]):
            o.append(f'<polygon class="dline" data-d="{d}" points="{J(ringw(part))}" fill="none" stroke="{DCOL[d]}" stroke-width="3" stroke-linejoin="round"></polygon>')
    o.append(f'<polygon points="{J(ringw(toW(CITY_LL)))}" fill="none" stroke="{P["outline"]}" stroke-width="4" stroke-linejoin="round"></polygon>')
    for h in [toW(HAMTRAMCK_LL),toW(HIGHLAND_LL)]:
        o.append(f'<polygon points="{J(ringw(h))}" fill="none" stroke="{P["outline"]}" stroke-width="2.5" stroke-dasharray="6 4"></polygon>')
    # drone route
    ra=[iso(x,y,3.4) for x,y in ROUTE]; rg=[iso(x,y) for x,y in ROUTE]
    o.append('<g class="proposal">')
    o.append(f'<polyline points="{J(rg)}" fill="none" stroke="{P["route"]}" stroke-opacity="0.35" stroke-width="1.2" stroke-dasharray="2 4"></polyline>')
    for a,b in [(ra[0],rg[0]),(ra[-1],rg[-1])]: o.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{P["route"]}" stroke-opacity="0.5"></line>')
    o.append(f'<polyline points="{J(ra)}" fill="none" stroke="{P["route"]}" stroke-opacity="0.2" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"></polyline><polyline points="{J(ra)}" fill="none" stroke="{P["route"]}" stroke-width="2.4" stroke-dasharray="8 5" stroke-linecap="round" stroke-linejoin="round"></polyline>')
    for p in (ra[0],ra[-1]): o.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="5" fill="#FFFFFF" stroke="{P["route"]}" stroke-width="2.2"></circle>')
    o.append('</g>')
    # labels
    for d,g in DIST.items():
        rp=g.representative_point() if g.geom_type!="MultiPolygon" else max(g.geoms,key=lambda q:q.area).representative_point()
        X,Y=iso(rp.x,rp.y,0.5); o.append(f'<g class="dlabel" data-d="{d}">'+chip(X,Y,f"District {d}",DCOL[d],P,LS)+'</g>')
    for name,ll in [("Hamtramck",(-83.056,42.392)),("Highland Park",(-83.108,42.410))]:
        X,Y=iso(*w(*ll),0.3); o.append(f'<text x="{X:.1f}" y="{Y:.1f}" text-anchor="middle" fill="{P["outline"]}" font-size="{12*LS:.0f}" font-weight="700" opacity="0.85">{name}</text>')
    X,Y=iso(*w(-83.035,42.305)); o.append(f'<text x="{X:.1f}" y="{Y:.1f}" text-anchor="middle" fill="#FFFFFF" font-size="{16*LS:.0f}" font-weight="700" font-style="italic" opacity="0.9" transform="rotate(-14 {X:.1f} {Y:.1f})">Detroit River</text>')
    X,Y=iso(*w(-83.010,42.275)); o.append(f'<text x="{X:.1f}" y="{Y:.1f}" text-anchor="middle" fill="{P["outline"]}" font-size="{15*LS:.0f}" font-weight="600" opacity="0.55">Windsor, Ontario</text>')
    X,Y=iso(*w(*MC_LL),0); o.append(f'<g class="proposal"><line x1="{X:.1f}" y1="{Y:.1f}" x2="{X+30:.1f}" y2="{Y+140:.1f}" stroke="{P["outline"]}" stroke-width="2"></line><circle cx="{X:.1f}" cy="{Y:.1f}" r="4" fill="{P["outline"]}"></circle>'+chip(X+30,Y+160,"Michigan Central · Newlab",None,P,LS)+'</g>')
    # bounds
    xs=[iso(*w(lo,la))[0] for lo,la in CITY_LL]; ys=[iso(*w(lo,la))[1] for lo,la in CITY_LL]
    return "\n".join(o),(min(xs),min(ys)-30,max(xs),max(ys)+20)

GAME=dict(street="#EEF2E8",block="#CFE0BF",park="#8DBB74",enclave="#DCE3D4",water="#7FB3D5",band="#1E3A8A",
 b=("#FFFDF7","#CFC6B6","#E2DACB"),ib=("#FFF1DA","#D6B98F","#E8CFA8"),mc=("#F3EEE4","#B3A893","#C9BFAC"),nl=("#3B82F6","#1D4ED8","#2563EB"),
 s="#1D4ED8",n="#64748B",o="#EA580C",route="#1E293B",chip="#FFFFFF",chipline="#94A3B8",chiptext="#0F172A",chipsub="#334155",
 light="#15803D",busy="#CA8A04",heavy="#EA580C",full="#DC2626",dim="#A9C894",outline="#1E293B")
if __name__=="__main__":
    svg,b=build(GAME); print(len(svg),[round(v) for v in b], {d:round(g.area,1) for d,g in DIST.items()})
