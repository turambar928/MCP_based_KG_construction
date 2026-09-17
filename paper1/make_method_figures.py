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
        fig.savefig(OUT/f'{name}.{ext}',bbox_inches='tight',pad_inches=.03)
    plt.close(fig)


def architecture():
    fig,ax=canvas(8.35)
    # Preserve the author's five-column composition and three module colors.
    text(ax,.94,6.05,'Input knowledge\ngraph',7.7,weight='bold')
    graph(ax,.94,4.7,1.65,2.0)
    icon(ax,'document',.94,3.15,.4,MUTED)
    text(ax,.94,2.65,'Supplied source\nevidence',6.6,color=MUTED)
    box(ax,2.0,2.0,3.2,5.98,TEAL,WHITE,lw=1.1)
    text(ax,3.6,7.58,'Multi-scale quality\nassessment',8.1,TEAL,'bold')
    metrics=[('network','Node connectivity',r'$Q_{\mathrm{conn}}$'),
             ('duplicate','Triple uniqueness',r'$Q_{\mathrm{uniq}}$'),
             ('rules','Logical consistency',r'$Q_{\mathrm{logic}}$'),
             ('search','Semantic appropriateness',r'$Q_{\mathrm{sem}}$')]
    for i,(kind,title,symbol) in enumerate(metrics):
        y=6.23-i*1.03
        box(ax,2.16,y,2.88,.9,'#B4D6D3',TL,lw=.6)
        icon(ax,kind,2.61,y+.45,.49,TEAL)
        text(ax,3.91,y+.59,title,6.7)
        text(ax,3.91,y+.25,symbol,7.4,TEAL)
    text(ax,3.6,2.48,'Entity  /  graph  /  context',6.6,TEAL)
    arrow(ax,(3.6,2.0),(3.6,1.83),TEAL)
    box(ax,2.0,1.36,3.2,.46,TEAL,TL,radius=.08)
    text(ax,3.6,1.6,r'$\mathbf{s}=(Q_{\mathrm{conn}},Q_{\mathrm{uniq}},Q_{\mathrm{logic}},Q_{\mathrm{sem}})$',7)

    box(ax,5.57,2.9,2.48,3.96,BLUE,WHITE,lw=1.1)
    text(ax,6.81,6.36,'Neural repair\ndecision network',7.9,BLUE,'bold')
    mlp(ax,6.81,5.10,1.86,1.2)
    box(ax,5.75,3.11,2.12,1.12,'#AAC2DE',BL,lw=.6)
    text(ax,6.81,3.87,r'Input: $[\mathbf{s};\mathbf{g}]$',7.4,BLUE)
    text(ax,6.81,3.46,r'Output: $(p_{\mathrm{repair}},\pi)$',7.4,BLUE)
    text(ax,6.81,2.48,'Repair trigger +\nsoft prior over three scales',6.6,MUTED)

    box(ax,8.42,2.0,3.62,5.98,PURPLE,WHITE,lw=1.1)
    text(ax,10.23,7.58,'Hybrid completion\nengine',8.1,PURPLE,'bold')
    box(ax,8.58,6.04,3.30,.98,'#C8BFDB',PL,lw=.6)
    icon(ax,'shield',8.98,6.53,.52,PURPLE)
    text(ax,10.6,6.68,'Constraint-driven\noptimization',6.8,weight='bold')
    text(ax,10.6,6.23,'Local gain + action cost',6.5,MUTED)
    box(ax,8.58,4.97,3.3,.86,'#C8BFDB',PL,lw=.6)
    icon(ax,'route',8.98,5.4,.50,PURPLE)
    text(ax,10.6,5.55,'Scale-aware routing',7,weight='bold')
    text(ax,10.6,5.18,r'Soft guidance from $\pi$',6.7,MUTED)
    arrow(ax,(10.23,4.97),(10.23,4.76),PURPLE)
    for x,w,kind,title,scope,c in [
            (8.56,1.29,'document','Source-grounded\ncompletion','Entity',TEAL),
            (9.94,.91,'hierarchy','Rule-based\ninference','Graph',BLUE),
            (10.94,.94,'robot','LLM\nreasoning','Context',PURPLE)]:
        box(ax,x,3.20,w,1.53,c,WHITE,lw=.6)
        icon(ax,kind,x+w/2,4.27,.48,c)
        text(ax,x+w/2,3.82,title,6.1)
        text(ax,x+w/2,3.40,scope,6.3,c,'bold')
    arrow(ax,(10.23,3.2),(10.23,2.98),PURPLE)
    box(ax,8.58,2.17,3.3,.78,PURPLE,PL,lw=.75)
    icon(ax,'shield',8.98,2.56,.44,PURPLE)
    text(ax,10.60,2.70,'Trial graph + gate',6.7,weight='bold')
    text(ax,10.60,2.36,'Commit accepted edits only',6.4,MUTED)

    text(ax,13.34,6.05,'Updated knowledge\ngraph',7.7,weight='bold')
    graph(ax,13.34,4.7,1.60,2.0,repaired=True)
    text(ax,13.34,3.2,'Accepted edits\n+ audit record',6.6,TEAL)
    for a,b in [((1.72,4.98),(2,4.98)),((5.2,4.98),(5.57,4.98)),((8.05,4.98),(8.42,4.98))]:
        arrow(ax,a,b,BLUE)
    route(ax,[(12.04,2.55),(12.26,2.55),(12.26,4.98),(12.52,4.98)],PURPLE)
    route(ax,[(13.34,2.70),(13.34,.98),(.94,.98),(.94,2.3)],TEAL,True)
    box(ax,4.22,.69,6.0,.57,WHITE,WHITE,lw=0)
    text(ax,7.22,.98,'Reassess accepted edits; stop by explicit criteria',7.0,TEAL,'bold',
         bbox={'facecolor':WHITE,'edgecolor':'none','pad':3})
    text(ax,7.22,.38,'Low repair probability  ·  no violations  ·  no positive feasible action  ·  iteration cap',6.5,MUTED)
    export(fig,'image1')


def scales():
    fig,ax=canvas(7.7)
    centers=[2.36,7.20,12.04]
    colors=[BLUE,TEAL,ORANGE]
    for i,(cx,c,fc,title,sub) in enumerate(zip(centers,colors,[BL,TL,OL],
            ['Entity scale','Graph scale','Context scale'],
            ['Local explicit connections','Multi-hop logical constraints','Source and contextual alignment'])):
        circle(ax,cx-1.57,7.18,.21,c,c)
        text(ax,cx-1.57,7.18,str(i+1),8,WHITE,'bold')
        text(ax,cx+.15,7.18,title,9,c,'bold')
        text(ax,cx,6.73,sub,7.1,MUTED)
        circle(ax,cx,4.40,2.16,c,fc,.65,True,zorder=0)
    # Entity scale: retain the radial icon graph, with administrative relations.
    cx,cy=2.36,4.4
    pts=[(0,1.42,'document','defines'),(-1.45,.5,'building','issued by'),
         (1.42,.5,'database','uses'),(-.9,-1.18,'person','applies to'),
         (.9,-1.18,'network','part of')]
    for dx,dy,kind,label in pts:
        line(ax,[(cx,cy),(cx+dx,cy+dy)],BLUE,.95)
        node(ax,cx+dx,cy+dy,kind,BLUE,.3)
        lx=cx+dx*.66; ly=cy+dy*.66
        if dx==0:
            lx+=.55
            ly+=.20
        elif dy > 0: ly+=.52
        else: ly+=.20
        text(ax,lx,ly,label,6.6,BLUE,bbox={'facecolor':BL,'edgecolor':'none','pad':.4})
    node(ax,cx,cy,'document',BLUE,.42)
    icon(ax,'search',cx,2.68,.52,BLUE)
    # Graph scale: observed and candidate relations, with a rule-family inset.
    graph(ax,7.2,4.88,3.60,2.60,details=True)
    box(ax,5.32,2.4,3.76,.85,TEAL,WHITE,lw=.6)
    for j,(kind,title) in enumerate([('hierarchy','Hierarchy'),('shield','Type/schema'),('rules','Relation validity')]):
        xx=5.96+j*1.24
        icon(ax,kind,xx,2.94,.28,TEAL)
        text(ax,xx,2.60,title,6.4,TEAL)
    # Context scale: document cards around a shared graph, without causal claims.
    graph(ax,12.04,4.44,1.94,1.56,details=False)
    for dx,dy,label in [(-1.24,1.15,'Source A'),(1.24,1.15,'Source B'),
                        (-1.24,-1.12,'Source C'),(1.24,-1.12,'Source D')]:
        xx,yy=12.04+dx,4.44+dy
        line(ax,[(xx-(.51 if dx>0 else -.51),yy-(.32 if dy>0 else -.32)),
                 (12.04+dx*.3,4.44+dy*.3)],ORANGE,.75,True)
        box(ax,xx-.51,yy-.49,1.02,.98,ORANGE,WHITE,lw=.6)
        text(ax,xx,yy+.29,label,6.7,ORANGE)
        icon(ax,'document',xx-.22,yy-.12,.34,ORANGE)
        for off in [-.26,-.12,.02]: line(ax,[(xx+.04,yy+off),(xx+.37,yy+off)],GRID,.8)
    text(ax,12.04,6.02,'Shared entities',6.5,ORANGE)
    text(ax,12.04,2.83,'Evidence support',6.5,ORANGE)
    # Scope expansion arrows between the circular fields.
    for x,c in [(4.58,BLUE),(9.42,TEAL)]:
        arrow(ax,(x-.19,4.35),(x+.53,4.35),c,lw=1.5)
        text(ax,x+.17,3.95,'expand',6.3,c)
    for cx,c,fc,label in zip(centers,colors,[BL,TL,OL],
            ['Connectivity + uniqueness','Schema and relation checks','Semantic plausibility + evidence']):
        box(ax,cx-2.13,1.57,4.26,.49,c,fc,lw=.6)
        text(ax,cx,1.82,label,7,c)
    for j,(cx,c,title) in enumerate(zip(centers,colors,['LOCAL','GRAPH-WIDE','CONTEXTUAL'])):
        text(ax,cx,1.12,title,6.8,c,'bold')
        circle(ax,cx,.77,.075,c,c)
        if j<2: line(ax,[(cx+.12,.77),(centers[j+1]-.12,.77)],c,1.6)
    arrow(ax,(12.17,.77),(13.94,.77),ORANGE,lw=1.6)
    text(ax,7.2,.30,'From explicit local relations to graph logic and contextual evidence.',7,MUTED)
    export(fig,'image2')


def optimization():
    fig,ax=canvas(11.55)
    # Left diagnostic cards preserve the author's vertical multiscale structure.
    box(ax,.18,2.12,2.53,7.30,MUTED,WHITE,lw=.95)
    text(ax,1.445,8.97,'Diagnostics\n(multi-scale)',8.4,weight='bold')
    for y,kind,title,body,c,fc in [
        (6.45,'network','Entity scale','Isolated nodes\nRedundant triples\nMissing attributes',BLUE,BL),
        (4.45,'hierarchy','Graph scale','Hierarchy reversals\nSchema conflicts\nInvalid relations',TEAL,TL),
        (2.45,'search','Context scale','Unsupported values\nSemantic errors\nEvidence gaps',PURPLE,PL)]:
        box(ax,.35,y,2.19,1.80,c,fc,lw=.6)
        icon(ax,kind,.72,y+1.41,.37,c)
        text(ax,1.60,y+1.41,title,7.4,c,'bold')
        text(ax,1.445,y+.69,body,6.9)
    text(ax,3.2,6.44,'Profile $\mathbf{s}$\n+ violations',6.5,MUTED)
    arrow(ax,(2.71,5.97),(3.70,5.97),MUTED)

    # Central constraint panel: illustrative symbols, no fabricated trajectory.
    box(ax,3.70,8.42,7.00,2.62,BLUE,WHITE,lw=1.05)
    icon(ax,'shield',4.12,10.59,.48,BLUE)
    text(ax,4.59,10.59,'Constraint-driven optimization',8.5,BLUE,'bold',ha='left')
    for x,kind,title,body in [
        (4.62,'target','Constraint set','Logic / schema\n/ domain rules'),
        (6.34,'region','Feasible region','Quality bounds\n+ density ceiling'),
        (8.06,'gain','Local gain','Trial-graph\nquality estimate'),
        (9.77,'balance','Action cost','Least-destructive\noperation hierarchy')]:
        icon(ax,kind,x,9.74,.63,BLUE)
        text(ax,x,9.19,title,7.3,weight='bold')
        text(ax,x,8.77,body,6.5,MUTED)
    # Constraints feed the actual acceptance gate, not a bypass to the output.
    route(ax,[(10.70,9.77),(11.11,9.77),(11.11,3.42),(11.47,3.42)],BLUE)
    text(ax,11.10,8.00,'bounds',6.3,BLUE,rotation=90,
         bbox={'facecolor':WHITE,'edgecolor':'none','pad':1.2})
    arrow(ax,(7.2,8.42),(7.2,8.08),BLUE)

    box(ax,3.70,5.11,7,2.94,TEAL,WHITE,lw=1.05)
    icon(ax,'route',4.12,7.63,.45,TEAL)
    text(ax,4.59,7.63,'Profile-guided, scale-aware routing',8.2,TEAL,'bold',ha='left')
    text(ax,7.20,7.10,r'$(p_{\mathrm{repair}},\pi)=f_{\varphi}([\mathbf{s};\mathbf{g}])$; trigger if $p_{\mathrm{repair}}\geq\tau_{\mathrm{repair}}$',7.2)
    for j,(x,kind,title,body,c) in enumerate([
        (4.90,'network','Entity','Local structure',BLUE),
        (7.20,'hierarchy','Graph','Logical constraints',TEAL),
        (9.50,'search','Context','Source semantics',PURPLE)]):
        if j: line(ax,[(x-1.15,5.62),(x-1.15,6.80)],GRID,.7,True)
        icon(ax,kind,x,6.49,.43,c)
        text(ax,x,6.04,title,7.6,c,'bold')
        text(ax,x,5.69,body,6.7,MUTED)
    text(ax,7.20,5.32,'Scale probabilities bias candidate selection; they do not fix an action.',6.7,TEAL)
    arrow(ax,(7.20,5.11),(7.20,4.77),TEAL)

    box(ax,3.70,1.56,7,3.18,ORANGE,WHITE,lw=1.05)
    text(ax,7.20,4.37,'Repair modalities and candidate actions',8.4,ORANGE,'bold')
    for j,(x,kind,title,body,c) in enumerate([
        (4.90,'document','Source-grounded\ncompletion','Copy supplied evidence',TEAL),
        (7.20,'hierarchy','Rule-based\ninference','Apply domain templates',BLUE),
        (9.50,'robot','LLM\nreasoning','Resolve semantic gaps',PURPLE)]):
        icon(ax,kind,x,3.75,.46,c)
        text(ax,x,3.23,title,7.1,c,'bold')
        text(ax,x,2.75,body,6.5,MUTED)
    line(ax,[(3.88,2.48),(10.52,2.48)],GRID,.65,True)
    for x,kind,label,c in [(4.90,'delete','Delete',ORANGE),(7.20,'retype','Retype',BLUE),
                            (9.50,'complete','Complete',TEAL)]:
        icon(ax,kind,x-.48,2.13,.32,c)
        text(ax,x+.13,2.13,label,7.1,c,'bold')
    text(ax,7.20,1.77,r'Operation penalties: $\lambda_{\mathrm{del}} > \lambda_{\mathrm{ret}} > \lambda_{\mathrm{cmp}}$',7.2)
    arrow(ax,(10.70,2.98),(11.47,2.98),ORANGE)

    # Right column: explicit gate before output; rejection preserves the graph.
    box(ax,11.47,5.10,2.69,3.35,TEAL,WHITE,lw=.95)
    text(ax,12.815,7.94,'Updated knowledge\ngraph',8,TEAL,'bold')
    graph(ax,12.815,6.77,2.20,1.40,repaired=True)
    text(ax,12.815,5.57,'Accepted edits only\nRecorded decisions',7,TEAL)
    box(ax,11.47,2.23,2.69,2.06,PURPLE,PL,lw=.95)
    icon(ax,'shield',11.86,3.91,.35,PURPLE)
    text(ax,13.02,3.91,'Trial + gate',7.8,PURPLE,'bold')
    text(ax,12.815,3.19,'Quality bounds\nDensity / regression guard\nPositive utility',6.6)
    text(ax,12.815,2.54,'Reject: retain current graph',6.5,PURPLE)
    arrow(ax,(12.815,4.29),(12.815,5.10),TEAL)
    text(ax,13.25,4.67,'accept',6.6,TEAL)
    route(ax,[(12.815,2.23),(12.815,.87),(1.445,.87),(1.445,2.12)],TEAL,True)
    box(ax,4.5,.59,5.4,.59,WHITE,WHITE,lw=0)
    text(ax,7.2,.87,'Reassess the current graph and check stopping criteria',7,TEAL,'bold',
         bbox={'facecolor':WHITE,'edgecolor':'none','pad':3})
    text(ax,7.2,.29,'Stop: low trigger probability, no violations, no positive feasible action, or iteration limit.',6.7,MUTED)
    export(fig,'image3')


if __name__ == '__main__':
    architecture()
    scales()
    optimization()
    print('Wrote 3 vector PDF/SVG method figures; original PNG references preserved.')
