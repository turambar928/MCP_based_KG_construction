#!/usr/bin/python3
"""Redraw the three Paper1 method figures as editable SVG and vector PDF.
Run with system Python (PyGObject, librsvg, pycairo); no network/model calls.
The original image1/2/3.png files are preserved; previews use *_preview.png.
"""
from pathlib import Path
from html import escape
import re
import gi
import cairo

gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg

HERE = Path(__file__).resolve().parent
INK, MUTED, LINE = '#243447', '#5B6979', '#C5D0DA'
BLUE, GREEN, ORANGE, PURPLE, RED = '#316B98', '#39816F', '#B96B33', '#766699', '#B35252'
BL, GL, OL, PL = '#F0F6FB', '#EFF7F3', '#FCF4EB', '#F5F2FA'

class Figure:
    def __init__(self, height, title, description):
        self.h = height
        self.s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="{height}" viewBox="0 0 1000 {height}" role="img">',
                  f'<title>{escape(title)}</title><desc>{escape(description)}</desc>', '<defs>']
        self.markers = {c:f'a{i}' for i,c in enumerate([INK,BLUE,GREEN,ORANGE,PURPLE,RED,MUTED])}
        for c,n in self.markers.items():
            self.s.append(f'<marker id="{n}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{c}"/></marker>')
        self.s += ['</defs>', '<rect width="1000" height="100%" fill="white"/>']
    def box(self,x,y,w,h,fill='white',stroke=LINE,r=9,dash=False):
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.3"'+(' stroke-dasharray="5 4"' if dash else '')+'/>')
    def text(self,x,y,t,size=20,color=INK,bold=False,anchor='start',italic=False):
        content=escape(t)
        subs=str.maketrans('ₜₐᵢ₀₁₂₃₊','tai0123+')
        content=re.sub(r'[ₜₐᵢ₀₁₂₃₊]+',lambda m:'<tspan baseline-shift="sub" font-size="70%">'+m[0].translate(subs)+'</tspan>',content)
        content=content.replace('⁻','<tspan baseline-shift="super" font-size="70%">−</tspan>')
        self.s.append(f'<text x="{x}" y="{y}" font-family="Times New Roman" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{"bold" if bold else "normal"}" font-style="{"italic" if italic else "normal"}">{content}</text>')
    def lines(self,x,y,lines,size=20,color=INK,step=26,**kw):
        for i,t in enumerate(lines):self.text(x,y+i*step,t,size,color,**kw)
    def path(self,d,color=INK,arrow=False,dash=False,width=1.7):
        self.s.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"'+(f' marker-end="url(#{self.markers.get(color,"a0")})"' if arrow else '')+(' stroke-dasharray="5 4"' if dash else '')+'/>')
    def circle(self,x,y,r,fill='white',stroke=BLUE):
        self.s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
    def heading(self,x,y,n,title,color=BLUE):
        self.circle(x+11,y-7,11,color,color)
        self.text(x+11,y-1,str(n),17,'white',True,'middle')
        self.text(x+29,y,title,23,INK,True)
    def node(self,x,y,label,color=BLUE,r=16):
        self.circle(x,y,r,'white',color);self.text(x,y+6,label,18,color,True,'middle')
    def document(self,x,y,w,h,title,lines,color=ORANGE):
        self.box(x,y,w,h,'white',LINE,6)
        self.path(f'M {x+13} {y+14} V {y+h-14}',color,width=3)
        self.text(x+25,y+30,title,20,color,True)
        self.lines(x+25,y+61,lines,17,step=25)
    def save(self,name):
        path=HERE/f'{name}.svg';path.write_text('\n'.join(self.s+['</svg>'])+'\n')
        handle=Rsvg.Handle.new_from_file(str(path))
        v=Rsvg.Rectangle();v.x=v.y=0;v.width=1000;v.height=self.h
        # Natural width 145 mm. Manuscript scales to its existing text width.
        scale=(145/25.4*72)/1000
        pdf=cairo.PDFSurface(str(HERE/f'{name}.pdf'),1000*scale,self.h*scale)
        pdf.set_metadata(cairo.PDF_METADATA_TITLE,name+' — Paper1 method')
        ctx=cairo.Context(pdf);ctx.scale(scale,scale);handle.render_document(ctx,v);pdf.finish()
        png=cairo.ImageSurface(cairo.FORMAT_ARGB32,2000,self.h*2)
        ctx=cairo.Context(png);ctx.scale(2,2);handle.render_document(ctx,v)
        png.write_to_png(str(HERE/f'{name}_preview.png'))


def architecture():
    f=Figure(565,'Profile-based sequential repair architecture',
      'A document and its field graph are assessed into four quality scores and four graph statistics. A learned router returns a repair trigger and a scope prior. Fixed model proposals and rule-derived edits are evaluated on trial states. One feasible positive-utility edit is committed, then reassessed. Receipt text is a schematic example, not an experimental result.')
    f.heading(20,32,1,'Input graph')
    f.heading(249,32,2,'Quality profile',GREEN)
    f.heading(499,32,3,'Neural routing',PURPLE)
    f.heading(748,32,4,'Edit selection',GREEN)
    # Concrete field graph and source, rather than generic KG icons.
    f.box(20,57,197,330,BL)
    f.text(36,86,'Document graph Gₜ',20,BLUE,True)
    f.node(62,162,'d₁')
    f.box(124,117,77,35,'white',BLUE,5);f.text(162,140,'ALPHA',17,BLUE,anchor='middle')
    f.box(124,184,77,35,OL,ORANGE,5);f.text(162,207,'49.00',19,ORANGE,anchor='middle')
    f.path('M 78 154 L 117 135',BLUE,True)
    f.path('M 78 173 L 117 201',ORANGE,True)
    f.text(83,115,'merchant',16,MUTED)
    f.text(78,221,'total',17,ORANGE)
    f.document(34,250,169,118,'Source X',['Merchant: ALPHA','Total: 42.00'],ORANGE)
    # Shared profile encodes quality + graph statistics.
    f.box(249,57,217,330,GL)
    f.text(265,86,'Four quality scores',21,GREEN,True)
    for i,(label,col) in enumerate([('Incidence',BLUE),('Uniqueness',BLUE),('Rule consistency',GREEN),('Source support',ORANGE)]):
        y=118+i*45
        f.circle(269,y-6,3,col,col)
        f.text(279,y,label,19)
        f.path(f'M 265 {y+13} H 448','#D8E5DF',width=1)
    f.path('M 265 279 H 450',LINE,width=1)
    f.text(265,305,'Four graph statistics',20,GREEN,True)
    f.lines(265,333,['Nodes · triples','Density · violations'],19,step=25)
    # Schematic learned network; no invented layer widths.
    f.box(499,57,217,330,PL)
    f.text(607,87,'8 inputs → router',21,PURPLE,True,'middle')
    layers=[(527,[125,151,177,203]),(583,[132,164,196]),(632,[141,187]),(687,[143,185])]
    for (x,ys),(xx,yys) in zip(layers,layers[1:]):
        for y in ys:
            for yy in yys:f.path(f'M {x} {y} L {xx} {yy}','#D8D0E5',width=1)
    for x,ys in layers:
        for y in ys:f.circle(x,y,5,'white',PURPLE)
    f.text(607,235,'Repair trigger p(repair)',19,PURPLE,anchor='middle')
    f.text(607,266,'Scope prior π',21,PURPLE,True,'middle')
    for x,w,label,col in [(513,55,'Local',BLUE),(573,58,'Graph',GREEN),(636,66,'Source',ORANGE)]:
        f.box(x,283,w,28,'white',col,4);f.text(x+w/2,303,label,16,col,anchor='middle')
    f.lines(607,341,['Hard flags or candidates','override a low trigger.'],18,MUTED,step=23,anchor='middle')
    # Compact candidate / selection mechanism.
    f.box(748,57,232,330,'white')
    f.text(764,87,'Candidate edits',21,GREEN,True)
    f.lines(764,118,['Fixed model bundles','+ rule-derived proposals'],19,step=25)
    for x,label,col in [(762,'−',ORANGE),(834,'↔',BLUE),(906,'+',GREEN)]:
        f.circle(x+20,179,17,'white',col);f.text(x+20,185,label,23,col,True,'middle')
    for x,label in [(782,'Delete'),(854,'Retype'),(926,'Add')]:f.text(x,214,label,18,anchor='middle')
    f.path('M 864 226 V 245',GREEN,True)
    f.box(764,252,200,51,GL,GREEN,6)
    f.text(864,275,'Trial graphs',20,GREEN,True,'middle')
    f.text(864,295,'Bounds + utility U(a)',18,anchor='middle')
    f.lines(864,334,['Choose one feasible edit','with maximal U(a) > 0.'],19,step=26,anchor='middle')
    for a,b in [(217,249),(466,499),(716,748)]:f.path(f'M {a} 224 H {b-6}',INK,True)
    # Accepted-state band and closed loop.
    f.path('M 864 387 V 417',GREEN,True)
    f.box(249,425,731,72,GL,GREEN,8)
    f.text(266,451,'Commit one edit → Gₜ₊₁',22,GREEN,True)
    f.text(266,479,'Retain the decision log; reassess the accepted graph.',19)
    f.box(768,440,84,39,'white',ORANGE,5);f.text(810,466,'49.00',22,ORANGE,anchor='middle')
    f.path('M 865 460 H 894',GREEN,True)
    f.box(905,440,60,39,'white',GREEN,5);f.text(935,466,'42.00',21,GREEN,anchor='middle')
    f.path('M 249 460 H 232 V 402 H 357 V 394',GREEN,True,dash=True)
    f.text(20,536,'Sequential variant: reassess after each accepted edit; stop if no feasible positive-utility edit remains.',19,MUTED)
    f.save('image1')


def scopes():
    f=Figure(615,'Three diagnostic scopes for one document graph',
      'Local, graph and source checks inspect the same document graph. A schematic example shows duplicate edges and an isolated node, a relation outside the schema, and a value absent from the source. The results form a shared report. Source occurrence alone is not a relation-level truth test.')
    # A shared document and schema anchor all three panels.
    f.box(20,17,960,105,'#F8FAFC',LINE)
    f.text(38,47,'One document · three views',23,INK,True)
    f.text(38,80,'Source X',20,ORANGE,True)
    f.text(137,80,'Merchant: ALPHA     Total: 42.00',21)
    f.path('M 553 34 V 105',LINE,width=1)
    f.text(573,49,'Task schema',21,GREEN,True)
    f.text(573,80,'Head: d₁     Relations: merchant, total',20)
    # Three parallel views, with different visual evidence.
    for x,n,title,col in [(20,1,'Local scope',BLUE),(347,2,'Graph scope',GREEN),(674,3,'Source scope',ORANGE)]:
        f.heading(x,167,n,title,col)
    f.box(20,188,306,319,BL,'#C2D8E9')
    f.text(37,219,'Incidence + duplicates',22,BLUE,True)
    f.node(70,289,'d₁',BLUE,20)
    f.box(196,267,110,43,'white',BLUE,6);f.text(251,294,'ALPHA',20,BLUE,anchor='middle')
    f.path('M 91 281 Q 140 245 189 280',BLUE,True)
    f.path('M 91 294 Q 139 328 189 296',ORANGE,True)
    f.text(140,248,'merchant',18,BLUE,anchor='middle')
    f.node(78,363,'u',ORANGE,16)
    f.text(113,369,'isolated node',19,ORANGE)
    f.path('M 38 394 H 308',LINE,width=1)
    f.lines(38,424,['Repeated fact → duplicate flag','No incident edge → local flag'],19,step=28)
    f.text(38,486,'Scores: incidence, uniqueness',18,BLUE)
    f.box(347,188,306,319,GL,'#C5DBD2')
    f.text(364,219,'Head + relation schema',22,GREEN,True)
    f.node(393,289,'d₁',GREEN,20)
    f.box(527,267,106,43,'white',GREEN,6);f.text(580,294,'ALPHA',20,GREEN,anchor='middle')
    f.path('M 415 289 H 519',ORANGE,True)
    f.text(467,267,'seller',20,ORANGE,anchor='middle')
    f.box(363,336,275,43,'white',ORANGE,5)
    f.text(500,364,'seller is not permitted',21,ORANGE,anchor='middle')
    f.path('M 364 394 H 635',LINE,width=1)
    f.lines(364,424,['H(t): head matches d₁','R(t): relation is permitted'],20,step=28)
    f.text(364,486,'Score: rule consistency',18,GREEN)
    f.box(674,188,306,319,OL,'#E7D1BC')
    f.text(691,219,'Value ↔ source text',22,ORANGE,True)
    f.document(691,239,271,97,'Source excerpt',[],ORANGE)
    f.box(714,292,140,31,OL,'none',3)
    f.text(722,314,'Total: 42.00',19,ORANGE,True)
    f.text(691,369,'Graph value: 49.00 → absent',20,RED)
    f.path('M 691 394 H 962',LINE,width=1)
    f.lines(691,424,['S(t; X): nonempty value','occurs in the source'],20,step=28)
    f.text(691,486,'Score: source support',18,ORANGE)
    for x,c in [(173,BLUE),(500,GREEN),(827,ORANGE)]:f.path(f'M {x} 507 V 531',c)
    f.path('M 173 531 H 827',MUTED)
    f.path('M 500 531 V 548',INK,True)
    f.box(147,555,706,43,'#F8FAFC',LINE,6)
    f.text(500,583,'Shared report: duplicate counts · failed checks · observed relations',21,INK,anchor='middle')
    f.save('image2')


def selection():
    f=Figure(685,'Profile-conditioned trial evaluation and edit selection',
      'A learned trigger and scope prior condition candidate evaluation. Candidates come from fixed model bundles and detected violations. Each candidate is applied independently to a copy of the current graph. Restoration, regression, density and nonempty-graph checks establish feasibility. The selector commits only the highest positive-utility feasible edit, logs all decisions, and reassesses. Generic trial sketches do not represent measured scores.')
    f.heading(20,33,1,'Route',PURPLE)
    f.heading(263,33,2,'Propose',BLUE)
    f.heading(512,33,3,'Evaluate trials',GREEN)
    f.heading(791,33,4,'Select',GREEN)
    # Router column, with explicit feature input and override.
    f.box(20,58,212,340,PL,'#D5CEE2')
    f.text(36,88,'Current graph Gₜ',22,PURPLE,True)
    f.lines(36,120,['4 profile scores','+ 4 graph statistics'],20,step=27)
    f.path('M 126 160 V 182',PURPLE,True)
    f.box(36,192,180,53,'white',PURPLE,6)
    f.text(126,225,'Learned router',22,PURPLE,True,'middle')
    f.text(36,277,'p(repair) + scope prior π',19,PURPLE)
    f.path('M 36 294 H 216',LINE,width=1)
    f.lines(36,321,['Hard violations or','supplied candidates','override a low trigger.'],19,MUTED,step=26)
    # Proposal objects.
    f.box(263,58,218,340,BL,'#C2D8E9')
    f.box(278,78,188,93,'white','#C2D8E9',6)
    f.text(293,108,'Model proposals',21,BLUE,True)
    f.lines(293,136,['Fixed edit bundles','grouped by relation'],18,step=23)
    f.box(278,187,188,93,'white','#C2D8E9',6)
    f.text(293,217,'Rule proposals',21,BLUE,True)
    f.lines(293,245,['Detected violations','+ explicit source fields'],18,step=23)
    f.path('M 372 281 V 305',BLUE,True)
    for x,label,col in [(279,'Delete',ORANGE),(343,'Retype',BLUE),(408,'Add',GREEN)]:
        f.box(x,315,58,31,'white',col,4);f.text(x+29,337,label,17,col,anchor='middle')
    f.text(372,377,'Deduplicate candidates',19,BLUE,anchor='middle')
    # Trial fan-out: all trials start from Gt, not from each other.
    f.box(512,58,248,340,GL,'#C5DBD2')
    f.text(528,88,'Independent copies of Gₜ',21,GREEN,True)
    for i,y in enumerate([107,184,261]):
        f.box(528,y,216,63,'white','#C5DBD2',5)
        f.text(543,y+38,['a₁','a₂','a₃'][i],21,GREEN,True)
        f.path(f'M 574 {y+32} H 597',GREEN,True)
        for x,yy in [(616,y+22),(646,y+44),(688,y+22)]:f.circle(x,yy,5,'white',GREEN)
        f.path(f'M 621 {y+24} L 641 {y+41} L 683 {y+24}',GREEN,width=1.3)
        if i!=0:f.path(f'M 621 {y+22} H 683',ORANGE,dash=i==1,width=1.4)
        f.text(718,y+40,'Gₐ',19,GREEN,anchor='middle')
    f.text(636,350,'Recompute profile and flags',19,GREEN,anchor='middle')
    f.text(636,377,'Check bounds; calculate U(a)',19,anchor='middle')
    # Feasible + positive + argmax sequence.
    f.box(791,58,189,340,'white')
    f.text(885,89,'Feasible?',22,GREEN,True,'middle')
    f.path('M 885 103 V 123',GREEN,True)
    f.text(885,155,'U(a) > 0?',23,GREEN,True,'middle')
    f.path('M 885 169 V 189',GREEN,True)
    f.box(807,202,157,70,GL,GREEN,6)
    f.text(885,231,'Highest utility',21,GREEN,True,'middle')
    f.text(885,255,'among eligible edits',18,anchor='middle')
    f.path('M 885 282 V 303',GREEN,True)
    f.text(885,333,'Commit one edit',22,GREEN,True,'middle')
    f.text(885,367,'Gₜ → Gₜ₊₁',22,GREEN,anchor='middle')
    f.path('M 232 227 H 256',INK,True)
    f.path('M 481 227 H 505',INK,True)
    f.path('M 760 227 H 784',INK,True)
    # Criteria lane linked to trial evaluation. Scope prior is explicitly an input.
    f.path('M 126 398 V 423 H 460 V 444',PURPLE,True,dash=True)
    f.text(272,415,'Scope prior π',18,PURPLE)
    f.box(20,455,461,114,PL,'#D5CEE2',7)
    f.text(36,484,'Utility U(a)',22,PURPLE,True)
    f.lines(36,513,['Quality gain + hard-violation reduction − edit cost','+ log scope prior + proposal confidence'],20,step=27)
    f.box(512,455,468,114,GL,'#C5DBD2',7)
    f.text(528,484,'Trial-state constraints',22,GREEN,True)
    f.lines(528,513,['Restoration bounds · bounded component regression','Density bound · nonempty-graph guard'],20,step=27)
    f.path('M 636 455 V 405',GREEN,True)
    f.path('M 481 511 H 496 V 434 H 572 V 405',PURPLE,True,dash=True)
    # Accepted graph returns to profiling; stopping condition is visually distinct.
    f.path('M 980 347 H 991 V 605 H 9 V 227 H 14',GREEN,True,dash=True)
    f.box(190,588,620,34,'white','none',0)
    f.text(500,612,'Reassess the committed graph; repeat within the 12-step horizon.',21,GREEN,anchor='middle')
    f.text(500,645,'Stop if no eligible edit exists or the 12-step horizon is reached.',19,MUTED,anchor='middle')
    f.text(500,673,'Early exit: no supplied candidates, and either a low trigger without hard flags or no detected violations.',18,MUTED,anchor='middle')
    f.save('image3')

if __name__ == '__main__':
    architecture()
    scopes()
    selection()
