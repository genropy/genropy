from gnr.core.gnrbag import Bag
from gnr.core.gnrstructures import GnrStructData
from gnr.core.gnrlang import GnrException
from reportlab.pdfgen import canvas

from reportlab import lib as pdflib

class GnrPdfElem(object):
    def __init__(self, obj, tag, tagType):
        self.obj = obj
        self.tag = tag
        self.tagType = tagType
        
    def __call__(self, *args, **kwargs):
        if not 'tagType' in kwargs:
            kwargs['tagType'] = self.tagType
        child = self.obj.child(self.tag, *args, **kwargs)
        return child
        
class GnrPdfSrc(GnrStructData):
    """TODO"""
    pdfDrawNS = ['line', 'grid', 'bezier', 'arc', 'rect', 'ellipse', 'wedge', 'circle', 'roundRect',
                 'drawString', 'drawRightString', 'drawCentredString']
    pdfStatusNS = ['setFillColorCMYK', 'setStrokeColorCMYK',
                   'setFillColorRGB', 'setStrokeColorRGB',
                   'setFillGray', 'setStrokeGray',
                   'setFillColor', 'setStrokeColor',
                   'setFont', 'setLineWidth', 'setLineCap', 'setLineJoin',
                   'setMiterLimit', 'setDash']
    gnrDrawNS = ['string']
    gnrStatusNS = ['pane', 'page', 'textObject']
    pdfNameSpace = dict([(name.lower(), (name, 'RD')) for name in pdfDrawNS])
    pdfNameSpace.update(dict([(name.lower(), (name, 'RS')) for name in pdfStatusNS]))
    pdfNameSpace.update(dict([(name.lower(), (name, 'GD')) for name in gnrDrawNS]))
    pdfNameSpace.update(dict([(name.lower(), (name, 'GS')) for name in gnrStatusNS]))
        
    def __getattr__(self, fname):
        fnamelower = fname.lower()
        if fnamelower in self.pdfNameSpace:
            return GnrPdfElem(self, *self.pdfNameSpace[fnamelower])
        elif hasattr(self, fname):
            return getattr(self, fname)
        else:
            raise AttributeError("object has no attribute '%s'" % fname)
            
    def setFont(self, psfontname, size, leading=None):
        """TODO
        
        :param psfontname: TODO
        :param size: TODO
        :param leading: TODO. 
        """
        self.child('setFont', psfontname=psfontname, size=size, leading=leading)
        
    def drawString(self, x=None, y=None, text=None, **kwargs):
        """TODO
        
        :param x: TODO. 
        :param y: TODO. 
        :param text: TODO. 
        """
        self.child('drawString', x=x, y=y, text=text, **kwargs)
        
class GnrPdf(object):
    """TODO"""
    autoConvert = ('x', 'y', 'height', 'width', 'radius',
                   'x1', 'x2', 'x3', 'x4', 'y1', 'y2', 'y3', 'y4'
                                                             'lowerx', 'lowery', 'upperx', 'uppery')
                                                             
    def __init__(self, filename='test.pdf', pagesize='A4', unit='inch'):
        if isinstance(pagesize, str):
            pagesize = getattr(pdflib.pagesizes, pagesize, pdflib.pagesizes.A4)
        if isinstance(unit, str):
            unit = getattr(pdflib.units, unit, pdflib.units.inch)
        self.canvas = canvas.Canvas(filename, pagesize)
        self.root = GnrPdfSrc.makeRoot()
        self.unit = unit
        self._pendingDraw = False
        self._log = []
        
    def log(self, txt, *args, **kwargs):
        """TODO
        
        :param txt: TODO
        """
        self._log.append('%s - %s - %s' % (txt, str(args), str(kwargs)))
        
    def toXml(self, *args, **kwargs):
        """TODO"""
        return self.root.toXml(*args, **kwargs)
        
    def draw(self):
        """TODO"""
        self._draw(self.root)
        
    def _draw(self, bag):
        for node in bag.nodes:
            attr = dict(node.attr)
            tag = attr.pop('tag')
            for k in list(attr.keys()):
                if k.endswith('_'):
                    v = attr.pop(k) or 0
                    attr[k[:-1]] = float(v) * self.unit
            drawer = getattr(self, '_drawNode_%s' % tag, self._drawNode)
            drawer(node, attr, tag)
            
    def string(self, align='L', **kwargs):
        """TODO
        
        :param align: TODO"""
        if align.lower() in ('r', 'right'):
            self.canvas.drawRightString(**kwargs)
        elif align.lower() in ('c', 'center'):
            self.canvas.drawCentredString(**kwargs)
        else:
            self.canvas.drawString(**kwargs)
            
    def _drawNode_textObject(self, node, attr, tag):
        textobject = canvas.beginText()
        x, y = attr.get('y', 0), attr.get('y', 0)
        textobject.setTextOrigin(x, y)
        self.canvas.drawText(textobject)
        
    def _drawNode_pane(self, node, attr, tag):
        value = node.getStaticValue()
        if isinstance(value, Bag) and value:
            self.canvas.saveState()
            self.log("saveState")
            x, y = attr.get('y', 0), attr.get('y', 0)
            self.canvas.translate(x, y)
            self.log("translate", x, y)
            self._draw(value)
            self.canvas.restoreState()
            self.log("restoreState")
            
    def _drawNode_page(self, node, attr, tag):
        self.page(**attr)
        value = node.getStaticValue()
        if isinstance(value, Bag) and value:
            self._draw(value)
            
    def _drawNode(self, node, attr, tag):
        self._pageInProgress = True
        tagType = attr.pop('tagType', 'RS')
        h = getattr(self, tag, None)
        if not h:
            h = getattr(self.canvas, tag, None)
        if h:
            h(**attr)
            self.log(tag, **attr)
            
            if tagType.endswith('D'):
                self._pendingDraw = True
        value = node.getStaticValue()
        if isinstance(value, Bag) and value:
            raise GnrException("child values in draw command !!!!")
            
    def page(self, x=0, y=0, **kwargs):
        """TODO
        
        :param x: TODO
        :param y: TODO"""
        if self._pendingDraw:
            self.canvas.showPage()
            self.log("showPage")
            self._pendingDraw = False
        self.canvas.translate(x, y)
        self.log("translate", x, y)
        
    def save(self):
        """TODO"""
        self.canvas.save()
        
if __name__ == '__main__':
    pdf = GnrPdf('testbag.pdf')
    root = pdf.root
    p = root.page(x=2, y=2)
    for k in range(10):
        p.drawString(x=k * 10, y=k * 10, text="Hello World page 1_ %s" % str(k))
        
    p = root.page()
    for k in range(10):
        p.drawString(x=k * 20, y=k * 20, text="Hello World page 2 _ %s" % str(k))
        
    p = root.page()
    for k in range(10):
        p.drawString(x=k * 30, y=k * 30, text="Hello World page 3 _ %s" % str(k))
        
    root.toXml('test.xml')
    pdf.draw()
    pdf.save()
