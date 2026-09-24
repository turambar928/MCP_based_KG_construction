#!/usr/bin/env python3
"""Reconstruct the author's PNG designs as editable, source-aligned vector figures.

The three image*.png files are references and are never overwritten. All visible
marks in the PDF/SVG outputs are drawn as text or vector paths, without rasters.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon

from figure_style import apply_style, INK, MUTED, GRID, WHITE

apply_style()
OUT = Path(__file__).resolve().parent / 'figure' / 'method'
BLUE, TEAL, PURPLE, ORANGE = '#2463A5', '#138C8B', '#66509A', '#C57828'
BL, TL, PL, OL = '#EEF4FB', '#EDF8F6', '#F4F0FA', '#FCF4E9'


def canvas(height):
    fig = plt.figure(figsize=(7.15, 7.15 * height / 14.4))
    ax = fig.add_axes([0.005, 0.005, 0.99, 0.99])
    ax.set(xlim=(0, 14.4), ylim=(0, height), aspect='equal')
    ax.axis('off')
    return fig, ax


def text(ax, x, y, label, size=7, color=INK, weight='normal', ha='center', **kw):
    return ax.text(x, y, label, fontsize=size, color=color, fontweight=weight,
                   ha=ha, va='center', linespacing=1.22, zorder=8, **kw)


def line(ax, points, color=MUTED, lw=0.8, dashed=False, zorder=2):
    ax.plot(*zip(*points), color=color, lw=lw, ls=(0, (3, 2)) if dashed else '-',
            solid_capstyle='round', zorder=zorder)


def arrow(ax, a, b, color=MUTED, lw=1, dashed=False, rad=0):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle='-|>', mutation_scale=8,
                 color=color, linewidth=lw, linestyle=(0, (3, 2)) if dashed else '-',
                 connectionstyle=f'arc3,rad={rad}', shrinkA=1, shrinkB=1, zorder=3))


def route(ax, points, color=MUTED, dashed=False):
    line(ax, points[:-1], color, 1, dashed)
    arrow(ax, points[-2], points[-1], color, dashed=dashed)


def box(ax, x, y, w, h, color=GRID, fill=WHITE, lw=0.8, radius=0.11):
    p = FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad=0,rounding_size={radius}',
                      edgecolor=color, facecolor=fill, linewidth=lw, zorder=1)
    ax.add_patch(p)
    return p


def circle(ax, x, y, r, color, fill=WHITE, lw=0.8, dashed=False, zorder=4):
    ax.add_patch(Circle((x, y), r, edgecolor=color, facecolor=fill, linewidth=lw,
                       linestyle=(0, (4, 3)) if dashed else '-', zorder=zorder))


def icon(ax, kind, x, y, s=0.5, color=BLUE):
    """Small line-art icons in data coordinates; s is the full icon width."""
    def L(points, lw=1):
        line(ax, [(x+u*s, y+v*s) for u,v in points], color, lw, zorder=6)
    def C(u,v,r,fill=WHITE):
        circle(ax, x+u*s, y+v*s, r*s, color, fill, zorder=6)
    def P(points, fill=WHITE):
        ax.add_patch(Polygon([(x+u*s,y+v*s) for u,v in points], closed=True,
                             facecolor=fill, edgecolor=color, lw=0.9, zorder=6))
    if kind == 'person':
        C(0, .24, .18, color)
        ax.add_patch(Ellipse((x,y-.18*s), .62*s,.42*s, color=color,zorder=6))
    elif kind == 'document':
        P([(-.34,-.48),(.34,-.48),(.34,.25),(.12,.48),(-.34,.48)])
        L([(.12,.48),(.12,.25),(.34,.25)])
        for v in [-.24,-.04,.14]: L([(-.2,v),(.18,v)], .8)
    elif kind == 'building':
        P([(-.48,.22),(0,.5),(.48,.22)], color)
        for u in [-.3,0,.3]: L([(u,-.3),(u,.14)], 1.5)
        L([(-.5,-.42),(.5,-.42)], 1.5)
        L([(-.44,-.29),(.44,-.29)])
    elif kind == 'database':
        for v in [-.28,0,.28]:
            ax.add_patch(Ellipse((x,y+v*s), .84*s,.3*s,facecolor=WHITE,
                                 edgecolor=color,lw=1,zorder=6))
        L([(-.42,-.28),(-.42,.28)])
        L([(.42,-.28),(.42,.28)])
    elif kind in ('network','hierarchy'):
        pts=[(-.4,-.3),(0,.35),(.4,-.3)]
        if kind=='network': L([pts[0],pts[2]])
        L([pts[0],pts[1],pts[2]])
        for u,v in pts: C(u,v,.10,color)
    elif kind == 'shield':
        P([(-.43,.35),(0,.5),(.43,.35),(.37,-.12),(0,-.5),(-.37,-.12)])
        L([(-.22,0),(-.04,-.18),(.24,.19)],1.4)
    elif kind == 'check':
        C(0,0,.45)
        L([(-.23,0),(-.04,-.19),(.25,.21)],1.3)
    elif kind == 'search':
        C(-.10,.12,.31)
        L([(.15,-.14),(.46,-.46)],2)
        L([(-.27,.12),(-.14,0),(.07,.24)])
    elif kind == 'rules':
        for v in [-.3,0,.3]:
            L([(-.44,v),(-.36,v-.08),(-.22,v+.08)])
            L([(-.08,v),(.43,v)])
    elif kind == 'duplicate':
        for dx,dy in [(-.1,.08),(.12,-.1)]:
            P([(-.34+dx,-.33+dy),(.24+dx,-.33+dy),(.24+dx,.36+dy),(-.34+dx,.36+dy)])
        L([(-.11,-.05),(.18,-.05)])
    elif kind == 'route':
        L([(0,-.45),(0,.42)],1.2)
        L([(0,-.05),(-.4,.28)],1.2)
        L([(0,-.05),(.4,.28)],1.2)
        for u,v in [(0,.42),(-.4,.28),(.4,.28)]: C(u,v,.08,color)
    elif kind == 'robot':
        box(ax,x-.42*s,y-.32*s,.84*s,.62*s,color,WHITE,radius=.12*s)
        C(-.18,.03,.05,color); C(.18,.03,.05,color)
        L([(-.14,-.17),(.14,-.17)])
        L([(0,.3),(0,.48)]); C(0,.53,.05,color)
    elif kind == 'target':
        for r in [.45,.29,.12]: C(0,0,r)
        L([(0,0),(.49,.48)],1.4)
    elif kind == 'gain':
        for u,h in [(-.33,.25),(-.07,.46),(.2,.68)]:
            box(ax,x+u*s,y-.4*s,.16*s,h*s,color,color,radius=.01)
        L([(-.4,.02),(.39,.48)])
    elif kind == 'balance':
        L([(0,-.45),(0,.45)]); L([(-.44,.27),(.44,.27)])
        L([(-.22,-.45),(.22,-.45)],1.5)
        for u in [-.32,.32]:
            P([(u,.27),(u-.18,-.17),(u+.18,-.17)])
    elif kind == 'region':
        ax.add_patch(Ellipse((x,y), .96*s,.65*s,facecolor=BL,edgecolor=color,
                             lw=1,ls=(0,(3,2)),zorder=6))
        C(-.08,0,.10,color)
    elif kind in ('complete','delete','retype'):
        C(0,0,.43)
        if kind=='complete':
            L([(-.23,0),(.23,0)],1.3); L([(0,-.23),(0,.23)],1.3)
        elif kind=='delete': L([(-.23,0),(.23,0)],1.3)
        else:
            L([(-.22,-.2),(.23,.23)],2)
            L([(-.23,-.23),(-.25,-.04)])


def node(ax,x,y,kind,color=BLUE,r=.23):
    circle(ax,x,y,r,color,WHITE,lw=.7)
    icon(ax,kind,x,y,r*1.22,color)


def graph(ax,x,y,w=1.45,h=1.8,repaired=False,details=True):
    pts=[(-.4,.22),(-.12,.46),(.35,.3),(0,.04),(-.32,-.22),(.39,-.15),(.06,-.48)]
    edges=[(0,1),(1,3),(1,2),(2,3),(0,4),(3,4),(2,5),(3,6),(4,6),(5,6)]
    for k,(a,b) in enumerate(edges):
        line(ax,[(x+pts[a][0]*w,y+pts[a][1]*h),(x+pts[b][0]*w,y+pts[b][1]*h)],
             TEAL if repaired and k in (4,7) else '#95A4B0', .7,
             dashed=not repaired and k in (4,7))
    kinds=['document','building','person','database','person','document','network']
    for i,(u,v) in enumerate(pts):
        color=TEAL if i in (2,4,6) else BLUE
        if details: node(ax,x+u*w,y+v*h,kinds[i],color,r=min(w*.11,.22))
        else: circle(ax,x+u*w,y+v*h,.068,color,color)


def mlp(ax,x,y,w=1.7,h=1.25):
    sizes=[3,4,4,2]
    columns=[]
    for j,n in enumerate(sizes):
        columns.append([(x-w/2+j*w/3,y+(i-(n-1)/2)*h/3) for i in range(n)])
    for first,second in zip(columns,columns[1:]):
        for a in first:
            for b in second: line(ax,[a,b],'#AAC2DE',.45)
    for col in columns:
        for px,py in col: circle(ax,px,py,.09,BLUE,BL,lw=.75)


def export(fig,name):
    OUT.mkdir(parents=True,exist_ok=True)
    for ext in ('pdf','svg'):
        fig.savefig(OUT/f'.{name}.tmp.{ext}',bbox_inches='tight',pad_inches=.03)
    for ext in ('pdf','svg'):
        (OUT/f'.{name}.tmp.{ext}').replace(OUT/f'{name}.{ext}')
    svg_path = OUT/f'{name}.svg'
    svg_path.write_text(
        '\n'.join(line.rstrip() for line in svg_path.read_text().splitlines()) + '\n'
    )
    plt.close(fig)


def section_label(ax, x, y, number, title, color):
    circle(ax, x, y, .15, color, color)
    text(ax, x, y, str(number), 7.2, WHITE, 'bold')
    text(ax, x+.28, y, title, 8.6, color, 'bold', ha='left')


def architecture():
    fig,ax=canvas(8.2)
    text(ax,7.2,7.94,'PROFILE-BASED SEQUENTIAL REPAIR',8.3,MUTED,'bold')
    text(ax,7.2,7.59,'Fixed-proposal evaluation with model edits and rule-derived candidates',7.3,MUTED)
    # Keep the original five-column layout; distinguish assessment, routing,
    # and selection rather than assigning one provider to each scope.
    text(ax,.92,6.21,'Current\ngraph',8.7,weight='bold')
    graph(ax,.92,4.76,1.62,2.12)
    icon(ax,'document',.92,3.23,.48,MUTED)
    text(ax,.92,2.63,'Source text\nand metadata',7.5,MUTED)

    box(ax,2.00,2.05,3.2,5.3,TEAL,WHITE,lw=1)
    section_label(ax,2.30,6.97,1,'Assessment',TEAL)
    metrics=[('network','Non-isolated nodes',r'$Q_{\mathrm{inc}}$'),
             ('duplicate','Triple uniqueness',r'$Q_{\mathrm{uniq}}$'),
             ('rules','Rule consistency',r'$Q_{\mathrm{rule}}$'),
             ('search','Source support',r'$Q_{\mathrm{src}}$')]
    for i,(kind,title,symbol) in enumerate(metrics):
        y=5.63-i*1.03
        box(ax,2.17,y,2.86,.89,'#C7E0DC',TL,lw=.55)
        icon(ax,kind,2.53,y+.45,.43,TEAL)
        text(ax,3.84,y+.59,title,7.5)
        text(ax,3.84,y+.23,symbol,8.3,TEAL)
    text(ax,3.60,2.25,r'Profile $\mathbf{s}$ + graph statistics $\mathbf{g}$',7.4,TEAL)

    box(ax,5.58,2.88,2.46,3.66,BLUE,WHITE,lw=1)
    section_label(ax,5.88,6.17,2,'Routing',BLUE)
    mlp(ax,6.81,5.12,1.72,1.03)
    text(ax,6.81,4.23,r'$f_{\varphi}([\mathbf{s};\mathbf{g}])$',8.6,BLUE)
    box(ax,5.77,3.09,2.08,.83,'#C7D7E8',BL,lw=.55)
    text(ax,6.81,3.65,r'$p_{\mathrm{repair}},\ \pi$',8.4,BLUE)
    text(ax,6.81,3.31,'Trigger + scope prior',7.3)
    text(ax,6.81,2.38,'Hard violations\noverride a low trigger',7.3,MUTED)

    box(ax,8.43,2.05,3.62,5.3,PURPLE,WHITE,lw=1)
    section_label(ax,8.73,6.97,3,'Edit selection',PURPLE)
    text(ax,10.24,6.42,'Model edits + rule proposals',7.6)
    for x,kind,label in [(9.10,'delete','Delete'),(10.24,'retype','Retype'),(11.38,'complete','Add')]:
        icon(ax,kind,x,5.97,.36,PURPLE)
        text(ax,x,5.58,label,7.6,PURPLE)
    arrow(ax,(10.24,5.34),(10.24,5.10),PURPLE)
    box(ax,8.63,4.15,3.22,.93,'#D3CAE3',PL,lw=.55)
    text(ax,10.24,4.77,'Evaluate trial graphs',8,weight='bold')
    text(ax,10.24,4.41,'Quality bounds + edit utility',7.5,MUTED)
    arrow(ax,(10.24,4.14),(10.24,3.89),PURPLE)
    box(ax,8.63,2.39,3.22,1.48,PURPLE,PL,lw=.75)
    icon(ax,'shield',9.02,3.36,.41,PURPLE)
    text(ax,10.60,3.48,'Select one edit',8,weight='bold')
    text(ax,10.60,3.07,'Feasible; highest\npositive utility',7.5)
    text(ax,10.24,2.59,'Otherwise stop',7.3,PURPLE)

    text(ax,13.37,6.21,'Updated\ngraph',8.7,weight='bold')
    graph(ax,13.37,4.76,1.62,2.12,repaired=True)
    text(ax,13.37,3.15,'One committed edit\n+ decision log',7.5,TEAL)
    for a,b in [((1.74,4.85),(2,4.85)),((5.2,4.85),(5.58,4.85)),((8.04,4.85),(8.43,4.85))]:
        arrow(ax,a,b,BLUE)
    route(ax,[(12.05,3.10),(12.28,3.10),(12.28,4.85),(12.55,4.85)],PURPLE)
    # Accepted state feeds assessment, not the source-document icon.
    route(ax,[(13.37,2.70),(13.37,1.38),(3.60,1.38),(3.60,2.05)],TEAL,True)
    text(ax,8.08,1.38,'Reassess the accepted graph',8.1,TEAL,'bold',
         bbox={'facecolor':WHITE,'edgecolor':'none','pad':3})
    arrow(ax,(4.02,.62),(4.58,.62),BLUE)
    text(ax,4.75,.62,'Forward flow',7.5,MUTED,ha='left')
    arrow(ax,(8.04,.62),(8.60,.62),TEAL,dashed=True)
    text(ax,8.77,.62,'State feedback',7.5,MUTED,ha='left')
    export(fig,'image1')


def scales():
    fig,ax=canvas(7.85)
    text(ax,7.2,7.57,'THREE COMPLEMENTARY DIAGNOSTIC SCOPES',8.3,MUTED,'bold')
    centers=[2.36,7.20,12.04]
    colors=[BLUE,TEAL,ORANGE]
    for i,(cx,c,fc,title,sub) in enumerate(zip(centers,colors,[BL,TL,OL],
            ['Local scope','Graph scope','Source scope'],
            ['Incidence and redundancy','Checks on relations','Values in source text'])):
        circle(ax,cx-1.65,6.94,.16,c,c)
        text(ax,cx-1.65,6.94,str(i+1),7.5,WHITE,'bold')
        text(ax,cx+.13,6.94,title,9.4,c,'bold')
        text(ax,cx,6.48,sub,7.8,MUTED)
        circle(ax,cx,4.20,2.08,c,fc,.7,True,zorder=0)
    # Retain the radial author illustration, with legible relation labels.
    cx,cy=2.36,4.20
    pts=[(0,1.33,'document','defines'),(-1.40,.43,'building','issued by'),
         (1.40,.43,'database','uses'),(-.87,-1.11,'person','applies to'),
         (.87,-1.11,'network','part of')]
    for dx,dy,kind,label in pts:
        line(ax,[(cx,cy),(cx+dx,cy+dy)],BLUE,.9)
        node(ax,cx+dx,cy+dy,kind,BLUE,.27)
        lx=cx+dx*.65; ly=cy+dy*.66
        if dx==0: lx+=.60;ly+=.08
        elif dy>0: ly+=.48
        else: ly+=.12
        text(ax,lx,ly,label,7.2,BLUE,bbox={'facecolor':BL,'edgecolor':'none','pad':1})
    node(ax,cx,cy,'document',BLUE,.40)
    text(ax,cx,2.68,'Node incidence; duplicates',7.2,BLUE)

    graph(ax,7.2,4.78,3.28,2.49,details=True)
    box(ax,5.39,2.47,3.62,.84,TEAL,WHITE,lw=.65)
    for xx,kind,title in [(6.28,'hierarchy','Hierarchy rules'),(8.12,'rules','Relation checks')]:
        icon(ax,kind,xx,3.02,.28,TEAL)
        text(ax,xx,2.67,title,7.1,TEAL)

    box(ax,10.46,5.02,3.16,.94,ORANGE,WHITE,lw=.7)
    icon(ax,'document',10.81,5.50,.39,ORANGE)
    text(ax,12.29,5.64,'Associated document',7.8,ORANGE,'bold')
    text(ax,12.29,5.28,'Candidate field values',7.3,MUTED)
    graph(ax,12.04,3.79,2.30,1.59,details=False)
    arrow(ax,(12.04,5.02),(12.04,4.62),ORANGE)
    text(ax,12.04,2.68,'Match values to source text',7.2,ORANGE)

    # Parallel scopes feed a shared report; no implication of graph expansion.
    for cx,c,fc,label in zip(centers,colors,[BL,TL,OL],
            ['Incidence + uniqueness','Rule consistency','Source support']):
        box(ax,cx-2.08,1.55,4.16,.47,c,fc,lw=.6)
        text(ax,cx,1.785,label,8,c)
        line(ax,[(cx,1.55),(cx,1.20)],c,.9)
    line(ax,[(centers[0],1.20),(centers[2],1.20)],MUTED,.85)
    arrow(ax,(7.2,1.20),(7.2,.91),MUTED)
    box(ax,4.15,.35,6.10,.55,GRID,WHITE,lw=.65)
    text(ax,7.2,.625,'Shared diagnostic report for one document graph',8,weight='bold')
    export(fig,'image2')


def optimization():
    fig,ax=canvas(11.80)
    text(ax,7.2,11.52,'PROFILE-BASED SEQUENTIAL SELECTION',8.3,MUTED,'bold')
    # Left column retains the original three diagnostic cards.
    box(ax,.15,2.10,2.65,8.96,MUTED,WHITE,lw=.85)
    section_label(ax,.49,10.64,1,'Assess graph',MUTED)
    for y,kind,title,body,c,fc in [
        (7.56,'network','Local scope','Isolated nodes\nRedundant triples',BLUE,BL),
        (5.04,'hierarchy','Graph scope','Empty fields / loops\nInvalid relations\nHierarchy-rule flags',TEAL,TL),
        (2.52,'search','Source scope','Unsupported values\nSource-match rate',PURPLE,PL)]:
        box(ax,.32,y,2.31,2.18,c,fc,lw=.65)
        icon(ax,kind,.70,y+1.75,.35,c)
        text(ax,1.63,y+1.75,title,8,c,'bold')
        text(ax,1.475,y+.86,body,7.6)
    text(ax,1.475,10.10,r'Profile $\mathbf{s}$; statistics $\mathbf{g}$',7.4,MUTED)
    arrow(ax,(2.80,6.94),(3.52,6.94),TEAL)

    # Utility and bounds are inputs to trial evaluation, not to the MLP.
    box(ax,3.52,8.76,7.11,2.30,BLUE,WHITE,lw=1)
    icon(ax,'shield',3.85,10.65,.33,BLUE)
    text(ax,4.13,10.65,'Trial evaluation criteria',8.6,BLUE,'bold',ha='left')
    for x,kind,title,body in [
        (4.66,'region','Feasibility','Restoration bounds\nDensity / edit guards'),
        (7.08,'gain','Quality gain','Profile change\nHard-violation reduction'),
        (9.48,'balance','Utility terms','Edit cost, scope prior\nand confidence')]:
        icon(ax,kind,x,10.04,.44,BLUE)
        text(ax,x,9.63,title,8,weight='bold')
        text(ax,x,9.16,body,7.4,MUTED)
    route(ax,[(10.63,9.62),(10.99,9.62),(10.99,5.00),(11.35,5.00)],BLUE)
    text(ax,10.99,7.54,'bounds + utility',7,BLUE,rotation=90,
         bbox={'facecolor':WHITE,'edgecolor':'none','pad':2})

    box(ax,3.52,5.84,7.11,2.59,TEAL,WHITE,lw=1)
    section_label(ax,3.85,8.04,2,'Profile-conditioned routing',TEAL)
    text(ax,7.075,7.52,r'$(p_{\mathrm{repair}},\pi)=f_{\varphi}([\mathbf{s};\mathbf{g}])$',8.8)
    box(ax,3.76,6.68,6.63,.55,'#C7E0DC',TL,lw=.5)
    text(ax,7.075,6.955,r'Proceed if $p_{\mathrm{repair}}\geq\tau_{\mathrm{repair}}$ OR a hard violation exists',7.7,TEAL)
    text(ax,7.075,6.37,'Local prior     /     Graph prior     /     Source prior',8)
    text(ax,7.075,6.03,'No detected violations: stop',7.5,MUTED)
    arrow(ax,(7.075,5.84),(7.075,5.50),TEAL)

    box(ax,3.52,2.10,7.11,3.38,ORANGE,WHITE,lw=1)
    section_label(ax,3.85,5.08,3,'Construct candidate edits',ORANGE)
    # The replay adapter supplies fixed model bundles; the runtime also derives
    # deterministic candidates from detected violations.
    for x,kind,title,body,c in [
        (5.32,'robot','Fixed model proposals','One edit bundle per relation',PURPLE),
        (8.83,'rules','Rule proposals','Edits from detected violations',BLUE)]:
        icon(ax,kind,x,4.48,.46,c)
        text(ax,x,4.05,title,8,c,'bold')
        text(ax,x,3.65,body,7.4,MUTED)
    line(ax,[(3.77,3.33),(10.38,3.33)],GRID,.65,True)
    for x,kind,label,c in [(4.83,'delete','Delete',ORANGE),(7.08,'retype','Retype',BLUE),(9.33,'complete','Add',TEAL)]:
        icon(ax,kind,x-.46,2.97,.30,c)
        text(ax,x+.15,2.97,label,8,c,'bold')
    text(ax,7.075,2.46,'Fixed costs: delete 0.30  >  retype 0.16  >  add 0.06',7.6,MUTED)
    arrow(ax,(10.63,3.27),(11.35,3.27),ORANGE)

    # The explicit winner-selection box consumes all trials, then commits one.
    box(ax,11.35,2.10,2.90,3.72,PURPLE,PL,lw=.95)
    section_label(ax,11.68,5.43,4,'Trial + select',PURPLE)
    text(ax,12.8,4.79,'Evaluate all\ncandidate trial graphs',7.7)
    line(ax,[(11.58,4.31),(14.02,4.31)],'#C8BFDB',.65)
    text(ax,12.8,3.96,'Keep feasible edits\nwith positive utility',7.7)
    text(ax,12.8,3.17,'Select highest utility',8,PURPLE,'bold')
    text(ax,12.8,2.53,'None eligible:\nstop; keep current graph',7.4,MUTED)
    arrow(ax,(12.8,5.82),(12.8,6.16),TEAL)

    box(ax,11.35,6.18,2.90,3.20,TEAL,WHITE,lw=.95)
    section_label(ax,11.68,8.95,5,'Commit one edit',TEAL)
    graph(ax,12.8,7.78,2.15,1.47,repaired=True)
    text(ax,12.8,6.65,'Updated graph\n+ decision log',7.7,TEAL)
    # Feedback starts at the committed state and returns to assessment.
    route(ax,[(14.25,7.50),(14.36,7.50),(14.36,1.42),(1.475,1.42),(1.475,2.10)],TEAL,True)
    text(ax,7.20,1.42,'Reassess the accepted graph; repeat within the iteration limit',8,TEAL,'bold',
         bbox={'facecolor':WHITE,'edgecolor':'none','pad':3})
    text(ax,7.2,.83,r'Stop: ($p_{\mathrm{repair}}<\tau_{\mathrm{repair}}$ AND no hard violation), OR no detected violations,',7.6,MUTED)
    text(ax,7.2,.40,'OR no feasible positive-utility edit, OR iteration limit reached.',7.6,MUTED)
    export(fig,'image3')


if __name__ == '__main__':
    architecture()
    scales()
    optimization()
    print('Wrote 3 vector PDF/SVG method figures; original PNG references preserved.')
