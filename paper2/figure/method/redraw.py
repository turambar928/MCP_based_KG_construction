#!/usr/bin/python3
"""Editable SVG masters -> vector PDF and PNG via system librsvg/Cairo.
Run: /usr/bin/python3 paper2/figure/method/redraw.py
No model calls. Historical experiment generators remain unchanged.
"""
from pathlib import Path
from html import escape
import gi
import cairo
import re

gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg

HERE = Path(__file__).resolve().parent
INK, MUTED, LINE = '#243447', '#596879', '#BDCAD5'
BLUE, ORANGE, GREEN, PURPLE = '#316B98', '#B96B33', '#39816F', '#766699'
PALE_BLUE, PALE_ORANGE, PALE_GREEN = '#F0F6FB', '#FCF4EB', '#EFF7F3'

class Figure:
    def __init__(self, height, title, description):
        self.h = height
        self.s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img">',
                  f'<title>{escape(title)}</title><desc>{escape(description)}</desc>',
                  '<defs>']
        for name, col in [('ink', INK), ('blue', BLUE), ('orange', ORANGE), ('green', GREEN), ('purple', PURPLE)]:
            self.s.append(f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{col}"/></marker>')
        self.s += ['</defs>', '<rect width="1200" height="100%" fill="white"/>']
    def box(self,x,y,w,h,fill='white',stroke=LINE,r=10,dash=False):
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"'+(' stroke-dasharray="6 5"' if dash else '')+'/>')
    def text(self,x,y,t,size=19,color=INK,bold=False,anchor='start',italic=False):
        content = escape(t)
        # Use positioned Times New Roman glyphs instead of Unicode fallback fonts.
        subs = str.maketrans('ₜ₊₁', 't+1')
        content = re.sub(r'[ₜ₊₁]+', lambda m: '<tspan baseline-shift="sub" font-size="70%">' + m[0].translate(subs) + '</tspan>', content)
        content = content.replace('⁻', '<tspan baseline-shift="super" font-size="70%">−</tspan>')
        self.s.append(f'<text x="{x}" y="{y}" font-family="Times New Roman" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{"bold" if bold else "normal"}" font-style="{"italic" if italic else "normal"}">{content}</text>')
    def lines(self,x,y,lines,size=19,color=INK,step=25,**kw):
        for i,t in enumerate(lines): self.text(x,y+i*step,t,size,color,**kw)
    def path(self,d,color=INK,arrow=False,dash=False,width=1.8):
        marker = {INK:'ink',BLUE:'blue',ORANGE:'orange',GREEN:'green',PURPLE:'purple'}.get(color,'ink')
        self.s.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"'+(f' marker-end="url(#{marker})"' if arrow else '')+(' stroke-dasharray="6 5"' if dash else '')+'/>')
    def circle(self,x,y,r,fill,stroke='none'):
        self.s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
    def heading(self,x,y,n,title,color=BLUE):
        self.circle(x+12,y-7,12,color)
        self.text(x+12,y-1,str(n),17,'white',True,'middle')
        self.text(x+33,y,title,23,INK,True)
    def save(self,name):
        p=HERE/f'{name}.svg'
        p.write_text('\n'.join(self.s+['</svg>'])+'\n')
        handle=Rsvg.Handle.new_from_file(str(p))
        viewport=Rsvg.Rectangle()
        viewport.x=viewport.y=0
        viewport.width=1200
        viewport.height=self.h
        # 174 mm wide at inclusion scale: text stays vector and fonts are embedded.
        scale=(174/25.4*72)/1200
        surface=cairo.PDFSurface(str(HERE/f'{name}.pdf'),1200*scale,self.h*scale)
        surface.set_metadata(cairo.PDF_METADATA_TITLE,name.replace('_',' ').title())
        ctx=cairo.Context(surface);ctx.scale(scale,scale)
        handle.render_document(ctx,viewport)
        surface.finish()
        raster=cairo.ImageSurface(cairo.FORMAT_ARGB32,2400,self.h*2)
        ctx=cairo.Context(raster);ctx.scale(2,2)
        handle.render_document(ctx,viewport)
        raster.write_to_png(str(HERE/f'{name}.png'))


def cooptimization():
    f=Figure(610,'RL graph–rule co-optimization',
        'A fixed-registry scheduling environment supplies fourteen features and an eight-action mask. A Double-DQN policy chooses one graph or rule operation. The environment updates graph and rule quality and returns reward. A separate training lane shows replay and target updates.')
    f.heading(20,33,1,'Environment')
    f.heading(292,33,2,'Observation')
    f.heading(552,33,3,'RL policy')
    f.heading(830,33,4,'One operation')
    f.box(20,56,235,325,PALE_BLUE)
    f.text(38,85,'Graph Gₜ',21,BLUE,True)
    # Miniature graph: duplicate edges are highlighted.
    for d in ['M 62 138 L 123 114','M 123 114 L 208 147','M 62 138 L 121 184','M 121 184 L 208 147']:
        f.path(d,BLUE,True,width=1.5)
    f.path('M 121 175 Q 162 133 202 141',ORANGE,True,width=2)
    for x,y,t in [(62,138,'A'),(123,114,'B'),(208,147,'C'),(121,184,'D')]:
        f.circle(x,y,15,'white',BLUE);f.text(x,y+6,t,17,BLUE,True,'middle')
    f.text(151,213,'duplicate edge',17,ORANGE,anchor='middle')
    f.path('M 38 221 H 237',LINE,width=1)
    f.text(38,249,'Active rules Rₜ',21,ORANGE,True)
    f.box(38,265,198,38,'white',ORANGE,5)
    f.text(49,290,'Duplicate validator',18)
    f.box(38,311,198,38,'white',ORANGE,5)
    f.text(49,336,'Relation validator',18)
    f.text(137,370,'Fixed validator registry',17,MUTED,anchor='middle')
    # State encoding; 14 bars grouped 4 + 3 + 4 + 3.
    f.box(292,56,222,325,'white')
    f.text(308,85,'14 features · oₜ',21,BLUE,True)
    x=310
    for count,col in [(4,BLUE),(3,ORANGE),(4,GREEN),(3,PURPLE)]:
        for i in range(count):
            f.box(x,105,9,30,col,col,2);x+=12
        x+=4
    f.lines(309,164,['Graph quality','Rule quality','Remaining defects','Budget + active fractions'],18,step=28)
    f.path('M 308 267 H 498',LINE,width=1)
    f.text(308,296,'8-action mask · mₜ',20,BLUE,True)
    for i in range(8):
        active=i in [1,3,4,5]
        f.box(310+i*23,312,18,23,BLUE if active else '#EDF0F3',BLUE if active else LINE,3)
        f.text(319+i*23,329,'1' if active else '0',15,'white' if active else MUTED,anchor='middle')
    f.text(309,362,'Graph + rule identities',17,MUTED)
    # Policy and compact network architecture.
    f.box(552,56,235,325,PALE_BLUE)
    f.text(669,86,'Double DQN',23,BLUE,True,'middle')
    layers=[(580,[126,155,184,213]),(634,[136,169,202]),(689,[145,193]),(753,[126,155,184,213])]
    for (x,ys),(xx,yys) in zip(layers,layers[1:]):
        for y in ys:
            for yy in yys:f.path(f'M {x} {y} L {xx} {yy}', '#CEDCE8',width=.9)
    for x,ys in layers:
        for y in ys:f.circle(x,y,6,BLUE if x in [580,753] else 'white',BLUE)
    for x,t in [(580,'14'),(634,'32'),(689,'16'),(753,'8')]:f.text(x,239,t,18,MUTED,anchor='middle')
    f.text(669,271,'Online action values',19,anchor='middle')
    f.box(573,292,193,42,'white',BLUE,6)
    f.text(669,319,'Mask → select aₜ',21,BLUE,True,'middle')
    f.text(669,362,'ε-greedy during training',17,MUTED,anchor='middle')
    # Two classes, eight actions in total.
    f.box(830,56,350,157,PALE_BLUE,BLUE)
    f.text(847,85,'Graph operations',21,BLUE,True)
    f.lines(848,115,['Remove isolated nodes · deduplicate','Restore relations · remove dangling edges'],18,step=26)
    f.circle(857,177,9,'white',BLUE); f.circle(923,177,9,'white',BLUE)
    f.path('M 868 173 H 911',ORANGE,True)
    f.path('M 868 184 H 911',BLUE,True)
    f.path('M 946 177 H 982',INK,True)
    f.circle(1006,177,9,'white',BLUE);f.circle(1072,177,9,'white',BLUE)
    f.path('M 1018 177 H 1060',BLUE,True)
    f.text(1100,183,'Gₜ₊₁',20,BLUE)
    f.box(830,227,350,154,PALE_ORANGE,ORANGE)
    f.text(847,257,'Rule operations',21,ORANGE,True)
    f.lines(848,285,['Acquire deletion / augmentation / both','Prune low-precision validators'],18,step=25)
    for x,t in [(851,'Rₜ'),(913,'+ r'),(1052,'Rₜ₊₁')]:
        f.box(x,328,55 if x<1000 else 94,34,'white',ORANGE,4);f.text(x+(27 if x<1000 else 47),351,t,20,ORANGE,anchor='middle')
    f.path('M 983 345 H 1038',ORANGE,True)
    # Main data flow and branch.
    f.path('M 255 235 H 285',INK,True)
    f.path('M 514 235 H 545',INK,True)
    f.path('M 787 235 H 808 V 140 H 823',INK,True)
    f.path('M 808 235 V 304 H 823',INK,True)
    f.text(800,228,'aₜ',17,anchor='end')
    # Reward and environment transition.
    f.path('M 1180 135 H 1191 V 414 H 137 V 388',GREEN,True)
    f.path('M 1180 304 H 1191',GREEN)
    f.box(291,394,570,40,PALE_GREEN,GREEN,7)
    f.text(576,420,'Update G, R → quality gains − costs − new-violation penalty',19,GREEN,anchor='middle')
    f.text(140,451,'Next observation and mask are recomputed from the updated environment.',18,MUTED)
    # Training band, connected through the logged transition.
    f.box(20,477,1160,115,'#F8F7FB','#D5CEE2',8)
    f.text(38,507,'Learning from transitions',21,PURPLE,True)
    f.text(38,535,'Replay: (oₜ, aₜ, rₜ, oₜ₊₁, done, mₜ₊₁)',18)
    f.text(38,566,'Reward rₜ uses graph and rule quality gains.',18,MUTED)
    f.path('M 875 414 V 461 H 468 V 492',PURPLE,True,dash=True)
    f.path('M 445 539 H 510',PURPLE,True,dash=True)
    f.box(527,495,268,76,'white','#D5CEE2',6)
    f.text(661,522,'Online network θ',20,PURPLE,True,'middle')
    f.text(661,550,'Masked selection · Huber loss',18,anchor='middle')
    f.path('M 803 531 H 883',PURPLE,True,dash=True)
    f.text(847,565,'100-step copy',16,MUTED,anchor='middle')
    f.box(900,495,261,76,'white','#D5CEE2',6)
    f.text(1030,522,'Target network θ⁻',20,PURPLE,True,'middle')
    f.text(1030,550,'Evaluate bootstrap action',18,anchor='middle')
    f.save('cooptimization')


def dual_strategy():
    f=Figure(650,'Dual-strategy rule generation',
        'A fire-enforcement document supplies two generation branches. Deletion supplies original text, masked text and removed fragments. Augmentation generates supplementary clauses and rules in one response. Both retain provenance; exact typed patterns enter a separate offline execution bridge. English examples are shortened translations from archived document E06FCBC8B4E263C04595AD197B9A8718.')
    f.heading(20,33,1,'Source')
    f.heading(250,33,2,'Complementary generation')
    f.heading(926,33,3,'Candidate archive',GREEN)
    # Shared source card.
    f.box(20,179,195,255,PALE_BLUE)
    f.box(39,199,39,49,'white',BLUE,3)
    for y in [212,223,234]:f.path(f'M 46 {y} H 70',BLUE,width=1.2)
    f.text(39,278,'Fire enforcement',21,BLUE,True)
    f.lines(39,309,['Source document T','+ document ID'],19,step=27)
    f.lines(39,377,['Rectification order;','enforcement after','failure to comply.'],18,MUTED,step=23)
    # Branching same source.
    f.path('M 215 300 H 233 V 200 H 250',BLUE,True)
    f.path('M 233 300 V 473 H 250',ORANGE,True)
    # Deletion lane.
    f.box(250,56,646,260,PALE_BLUE,'#C2D8E9')
    f.text(269,86,'A  Deletion completion',23,BLUE,True)
    f.text(876,85,'1 call',18,BLUE,anchor='end')
    f.box(269,102,274,192,'white','#C2D8E9',6)
    f.text(283,128,'Inputs: T, masked T⁻, spans F',18,BLUE,True)
    f.lines(283,159,['… after an order to rectify,','continued noncompliance …'],18,step=23)
    f.path('M 298 153 H 511',ORANGE,width=1.6)
    f.path('M 403 188 V 204',BLUE,True)
    f.box(279,215,254,36,PALE_BLUE,'none',4)
    f.text(290,239,'… [missing span] …',19,BLUE)
    f.text(283,277,'F: “after an order to rectify”',17,MUTED)
    f.path('M 548 203 H 579',BLUE,True)
    f.box(590,102,285,192,'white','#C2D8E9',6)
    f.text(605,128,'LLM → rule candidates',20,BLUE,True)
    f.text(605,164,'Procedural candidate',18,MUTED)
    f.lines(605,197,['Continued noncompliance','after a rectification order','leads to enforcement.'],20,step=27)
    f.text(605,279,'Shared response schema',17,MUTED)
    # Augmentation lane.
    f.box(250,340,646,268,PALE_ORANGE,'#E7D1BC')
    f.text(269,370,'B  Augmentation expansion',23,ORANGE,True)
    f.text(876,369,'1 call',18,ORANGE,anchor='end')
    f.box(269,387,161,195,'white','#E7D1BC',6)
    f.text(284,416,'Source T',21,ORANGE,True)
    f.lines(284,448,['Request up to','three additional','clauses and','rule candidates.'],18,step=26)
    f.path('M 437 486 H 472',ORANGE,True)
    f.box(482,387,393,195,'white','#E7D1BC',6)
    f.text(497,416,'LLM → one joint response',21,ORANGE,True)
    f.box(497,430,361,70,PALE_ORANGE,'none',5)
    f.text(509,454,'+ Generated clause',18,ORANGE,True)
    f.text(509,481,'Reinspect rectification after the penalty.',18)
    f.text(497,530,'Procedural candidate',18,MUTED)
    f.text(497,558,'After penalty → conduct reinspection.',19)
    # Provenance-preserving output and supported execution subset.
    f.path('M 896 199 H 919',BLUE,True)
    f.path('M 896 485 H 910 V 277 H 919',ORANGE,True)
    f.box(926,102,254,248,PALE_GREEN,'#C5DBD2')
    f.text(943,132,'Shared categories',21,GREEN,True)
    f.lines(943,166,['Type declarations','Allowed / forbidden patterns','Hierarchy / procedure'],18,step=26)
    f.path('M 943 235 H 1163','#C5DBD2',width=1)
    f.text(943,264,'Source lineage',20,GREEN,True)
    f.lines(943,292,['Document · strategy · response','Category · candidate position'],17,step=25)
    f.path('M 1053 350 V 380',GREEN,True)
    f.box(926,390,254,102,'white',GREEN,7)
    f.text(943,419,'Exact typed subset',20,GREEN,True)
    f.text(943,447,'(subject type, relation, object type)',16)
    f.text(943,475,'→ Offline execution bridge',18,GREEN)
    f.box(926,515,254,93,'#F7F8FA',LINE,7)
    f.text(943,545,'Other candidates',20,MUTED,True)
    f.lines(943,573,['Retained with provenance','for further validation'],18,MUTED,step=23)
    f.path('M 1180 300 H 1190 V 557 H 1182',INK,True,dash=True)
    f.text(20,637,'Example: shortened English translations from one archived fire-enforcement document; generated clauses are proposals.',18,MUTED)
    f.save('dual_strategy')

if __name__ == '__main__':
    cooptimization()
    dual_strategy()
