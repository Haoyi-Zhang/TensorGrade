"""Vector drawing primitives; copied into each independent project generator."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, Circle, FancyArrowPatch

plt.rcParams.update({'font.family':'STIXGeneral', 'mathtext.fontset':'stix',
                     'font.size':9, 'pdf.fonttype':42, 'ps.fonttype':42,
                     'text.usetex':False, 'axes.unicode_minus':False})
CM = 1 / 2.54

class Drawing:
    def __init__(self, bounds):
        x0,y0,x1,y1 = bounds
        self.fig = plt.figure(figsize=((x1-x0)*CM,(y1-y0)*CM))
        self.ax = self.fig.add_axes([0,0,1,1], xlim=(x0,x1), ylim=(y0,y1))
        self.ax.set_aspect('equal'); self.ax.axis('off')
        self.nodes = {}
        self.labels = []

    def text(self,x,y,label,size=9,ha='center',va='center'):
        artist=self.ax.text(x,y,label,fontsize=size,ha=ha,va=va,
                            linespacing=1.15,clip_on=False,zorder=4)
        self.labels.append([artist,None])
        return artist

    def box(self,name,x,y,w,h,label,dashed=False,shape='rect',size=9):
        style = {'edgecolor':'black','facecolor':'white','linewidth':.55,
                 'linestyle':(0,(4,3)) if dashed else 'solid', 'zorder':2}
        if shape == 'diamond':
            obj = Polygon([(x-w/2,y),(x,y+h/2),(x+w/2,y),(x,y-h/2)],**style)
        elif shape == 'circle': obj = Circle((x,y),w/2,**style)
        else: obj = Rectangle((x-w/2,y-h/2),w,h,**style)
        self.ax.add_patch(obj); self.text(x,y,label,size)
        self.labels[-1][1]=(x-w/2,y-h/2,x+w/2,y+h/2)
        self.nodes[name] = (x,y,w,h,shape)

    def point(self,name,side):
        x,y,w,h,_ = self.nodes[name]
        return {'n':(x,y+h/2),'s':(x,y-h/2),'e':(x+w/2,y),
                'w':(x-w/2,y),'nw':(x-w/2,y+h/2),
                'ne':(x+w/2,y+h/2),'c':(x,y)}[side]

    def line(self,points,dashed=False):
        xs,ys=zip(*points)
        self.ax.plot(xs,ys,color='black',linewidth=.55,
                     linestyle=(0,(4,3)) if dashed else 'solid',zorder=1)

    def arrow(self,p,q,dashed=False,via=()):
        points=[p,*via,q]
        if via:self.line(points[:-1],dashed)
        self.ax.add_patch(FancyArrowPatch(points[-2],points[-1],
                         arrowstyle='-|>',mutation_scale=7.5,linewidth=.55,
                         color='black',shrinkA=0,shrinkB=0,
                         linestyle=(0,(4,3)) if dashed else 'solid',zorder=1))

    def edge(self,a,b,sa='s',sb='n',**kwargs):
        self.arrow(self.point(a,sa),self.point(b,sb),**kwargs)

    def frame(self,x,y,w,h):
        self.ax.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='black',
                                   linewidth=.55,linestyle=(0,(4,3)),zorder=0))

    def save(self,out,name):
        # Fixed physical canvas: do not enlarge or rasterize the scientific figure.
        self.fig.canvas.draw()
        renderer=self.fig.canvas.get_renderer()
        x0,x1=self.ax.get_xlim();y0,y1=self.ax.get_ylim()
        for artist,node in self.labels:
            b=artist.get_window_extent(renderer).transformed(self.ax.transData.inverted())
            if b.x0<x0-.02 or b.x1>x1+.02 or b.y0<y0-.02 or b.y1>y1+.02:
                raise ValueError(name+': clipped label '+repr(artist.get_text()))
            if node and (b.x0<node[0]-.02 or b.x1>node[2]+.02 or b.y0<node[1]-.02 or b.y1>node[3]+.02):
                raise ValueError(name+': label exceeds node '+repr(artist.get_text()))
        self.fig.savefig(out/(name+'.pdf'),format='pdf',
                         metadata={'Creator':'Python Matplotlib','Producer':None,
                                   'CreationDate':None,'ModDate':None})
        plt.close(self.fig)

def pipeline(out):
    d=Drawing((0,0,15.8,8))
    for name,x,y,w,h,label in [
        ("diff",1.65,6.65,2.7,1,"Frozen\nproduction diff"),
        ("scope",5.1,6.65,2.7,1.1,"All hunks\nclosed?"),
        ("adapt",9.1,6.65,3.1,1,"Source adapter\n$f_b,f_a,I,A$"),
        ("bounded",13.3,6.65,3.0,1,"Bounded checks\nand mutants"),
        ("proof",9.1,3.65,3.1,1,"Universal equality\nargument"),
        ("lift",5.1,3.65,2.7,1.1,"Downstream\ncongruence?"),
        ("grade",1.65,3.65,2.7,1,"Tensor observation\ncontract"),
        ("abstain",5.1,1,5.3,1,"Abstain; retain record\nin denominator")]:
        d.box(name,x,y,w,h,label,size=8.5,dashed=name=="abstain")
    for a,b in [("diff","scope"),("scope","adapt"),("adapt","bounded")]:d.edge(a,b,sa="e",sb="w")
    d.edge("adapt","proof")
    for a,b in [("proof","lift"),("lift","grade")]:d.edge(a,b,sa="w",sb="e")
    d.text(7,7.35,"yes",size=8);d.text(3.4,4.35,"yes",size=8)
    d.text(13.3,5.55,"Executable validation",size=8)
    d.arrow(d.point("bounded","e"),d.point("proof","e"),via=((15.55,6.65),(15.55,3.65)))
    d.arrow(d.point("scope","s"),d.point("abstain","w"),dashed=True,
            via=((5.1,5.2),(.1,5.2),(.1,1)))
    d.text(2.8,5.4,"incomplete",size=8)
    d.edge("lift","abstain",dashed=True);d.text(5.75,2.35,"no",size=8)
    d.arrow(d.point("proof","s"),d.point("abstain","e"),dashed=True,via=((9.1,1),))
    d.text(9.65,2,"failure",size=8)
    d.save(out,"evidence-pipeline")

def grades(out):
    d=Drawing((0,0,13.3,7.25))
    ns=[("e",1.5,.5,"$\\varnothing$"),("s",1.5,1.65,"$S$"),
        ("z",1.5,2.8,"$SZ$"),("v",1.5,3.95,"$SZV$"),("o",1.5,5.1,"$SZVO$"),
        ("sm",5.0,2.8,"$SM$"),("zm",5.0,3.95,"$SZM$"),
        ("vm",5.0,5.1,"$SZVM$"),("om",5.0,6.25,"$SZVOM$")]
    for name,x,y,label in ns:d.box(name,x,y,2.2,.65,label)
    for a,b in [("e","s"),("s","z"),("z","v"),("v","o"),("sm","zm"),("zm","vm"),("vm","om")]:
        d.edge(a,b,sa="n",sb="s")
    for a,b in [("s","sm"),("z","zm"),("v","vm"),("o","om")]:d.edge(a,b,sa="e",sb="w")
    for i,label in enumerate(("$S$: shape","$Z$: numerical nonzero support","$V$: exact value","$O$: potential-contribution order","$M$: stored support")):
        d.text(7.25,5.9-i*.7,label,ha="left",size=8.5)
    d.text(7.25,1.6,"Arrows add guarantees.\nJuxtaposition denotes a set.",ha="left",size=8.5)
    d.save(out,"grade-lattice")

def components(out):
    d=Drawing((0,0,13.7,4.3))
    for name,x,lab in [("0",2.0,"0"),("1",4.0,"1"),("2",9.7,"2"),("3",11.7,"3")]:
        d.box(name,x,2.4,.65,.65,"$"+lab+"$",shape="circle")
    d.line([d.point("0","e"),d.point("1","w")]);d.line([d.point("2","e"),d.point("3","w")])
    for x in (1.15,8.85):d.frame(x,1.65,3.7,1.5)
    d.text(3,3.7,"$d_0=d_1=\\lambda_A\\ne0$")
    d.text(10.7,3.7,"$d_2=d_3=\\lambda_B\\ne0$")
    d.text(3,1.1,"$(Cx)_0=x_0+x_1$");d.text(10.7,1.1,"$(Cx)_1=x_2+x_3$")
    d.text(6.85,.35,"Solid: a compatible co-occurring pair. Dashed: an independently scaled component.",size=8)
    d.save(out,"consumer-components")

def main():
    a=argparse.ArgumentParser();a.add_argument("--outdir",type=Path,default=Path(__file__).resolve().parents[1]/"paper"/"figures")
    out=a.parse_args().outdir;out.mkdir(parents=True,exist_ok=True)
    for draw in (pipeline,grades,components):draw(out)
if __name__=="__main__":main()
