#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  gnrhtml.py
#
#  Created by Giovanni Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.

from gnr.core.gnrbag import Bag
from gnr.core.gnrstring import splitAndStrip
from gnr.core.gnrstructures import GnrStructData
from gnr.core.gnrsys import expandpath
from gnr.core.gnrdecorator import extract_kwargs


class GnrHtmlSrcError(Exception):
    pass
    
class GnrHtmlElem(object):
    def __init__(self, obj, tag):
        self.obj = obj
        self.tag = tag
        
    def __call__(self, *args, **kwargs):
        if self.tag in GnrHtmlSrc.html_autocontent_NS:
            if args:
                kwargs['content'], args = args[0], args[1:]
        child = self.obj.child(self.tag, *args, **kwargs)
        return child
        
class GnrHtmlSrc(GnrStructData):
    """Structure used to build server-side HTML pages. :ref:`Prints <print>` are based on this class"""
    
    html_base_NS = ['a', 'abbr', 'acronym', 'address', 'area', 'base', 'bdo', 'big', 'blockquote',
                    'body', 'br', 'button', 'caption', 'cite', 'code', 'col', 'colgroup', 'dd', 'del',
                    'dfn', 'dl', 'dt', 'em', 'fieldset', 'form', 'frame', 'frameset', 'head', 'hr', 'html',
                    'iframe', 'img', 'input', 'ins', 'kbd', 'label', 'legend', 'link', 'map', 'meta', 'noframes',
                    'noscript', 'object', 'ol', 'optgroup', 'option', 'param', 'samp', 'select', 'style',
                    'sub', 'sup', 'table', 'tbody', 'textarea', 'tfoot', 'th', 'thead', 'title', 'tr', 'tt',
                    'ul', 'var']
                    
    gnrNS = ['layout', 'row', 'cell']
        
    html_autocontent_NS = ['div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'td', 'li', 'b', 'i', 'small', 'strong',
                           'p', 'pre', 'q', ]
                           
    htmlNS = html_base_NS + html_autocontent_NS
        
    genroNameSpace = dict([(name.lower(), name) for name in htmlNS])
    genroNameSpace.update(dict([(name.lower(), name) for name in gnrNS]))
    
        
    def __getattr__(self, func_name):
        func_namelower = func_name.lower()
        if (func_name != func_namelower) and hasattr(self, func_namelower):
            return getattr(self, func_namelower)
        elif func_namelower in self.genroNameSpace:
            return GnrHtmlElem(self, '%s' % (self.genroNameSpace[func_namelower]))
            
        else:
            raise AttributeError(func_name)

    def makeRoot(cls, source=None,rootAttributes=None,parentWrapper=None):
        """Build the root through the :meth:`makeRoot()
        <gnr.core.gnrstructures.GnrStructData.makeRoot>` method and return it
        
        :param cls: the structure class
        :param page: the webpage instance
        :param source: the filepath of the xml file"""
        root = GnrStructData.makeRoot(source=source, protocls=cls,rootAttributes=rootAttributes)
        root._parentWrapper = parentWrapper
        return root

    makeRoot = classmethod(makeRoot)

    def defaultKwargs(self):
        return getattr(self.root,'default_kwargs',{})

    def style(self, style='', **kwargs):
        """Creates a ``<style>`` tag"""
        self.root.builder.head.child('style', content=style, **kwargs)
        
    def comment(self, content=None):
        """Creates an HTML comment tag (``<!-- -->``)"""
        self.child(tag='__flatten__', content='<!--%s-->' % content)
        
    def script(self, script='', _type="text/javascript", **kwargs):
        """Creates a ``<script>`` tag"""
        self.root.builder.head.child('script', content=script, _type=_type, **kwargs)
        
    def link(self, href='',_type=None, **kwargs ):
        """Creates a ``<link>`` tag"""
        self.root.builder.head.child('link', href=href,_type=_type, **kwargs)
        
    def csslink(self, href='', media='all', **kwargs ):
        """Shortcut to create a ``<link rel="stylesheet" type="text/css"">`` tag"""
        self.root.builder.head.child('link', href=href, rel="stylesheet", _type="text/css", media=media, **kwargs)
        
    def meta(self, name=None, content=None, http_equiv=None, **kwargs):
        """Creates a ``<meta>`` tag"""
        _attributes = dict()
        if http_equiv:
            _attributes['http-equiv'] = http_equiv
        self.root.builder.head.child('meta', name=name, _content=content, _attributes=_attributes, **kwargs)
        
    def child(self, tag, *args, **kwargs):
        """TODO"""
        for lbl in ['_class', 'class_', '_type', 'type_', '_for', 'for_']:
            if lbl in kwargs:
                kwargs[lbl.replace('_', '')] = kwargs.pop(lbl)
                
        #if 'name' in kwargs:
        #    kwargs['_name'] = kwargs.pop('name')
        return super(GnrHtmlSrc, self).child(tag, *args, **kwargs)
        
    def layout(self, name=None, um='mm', top=0, left=0, bottom=0, right=0, width=0, height=0,
               border_width=None,border_color=None, border_style='solid', row_border=True, cell_border=True,
               lbl_height=3, lbl_class='lbl_base', content_class='content_base',
               hasBorderTop=None, hasBorderLeft=None, hasBorderRight=None, hasBorderBottom=None,
               **kwargs):
        """Build a layout element and return it
        
        :param name: the layout name
        :param um: the layout's unit of measurement
        :param top: the height of the top region
        :param left: the width of the left region
        :param bottom: the height of the bottom region
        :param right: the width of the right region
        :param width: layout's width
        :param height: layout's height
        :param border_width: add the border width
        :param border_color: add the border color
        :param border_style: add the border style
        :param row_border: add the row border
        :param cell_border: add the cell border
        :param lbl_height: add the label height
        :param lbl_class: add the label class
        :param content_class: add the content class
        :param hasBorderTop: add the top border
        :param hasBorderLeft: add the left border
        :param hasBorderRight: add the right border
        :param hasBorderBottom: add the bottom border
        :param \*\*kwargs: you can pass:
        
            * *style*: a string with css style"""
        name = name or 'l_{}'.format('_'.join([p for p in self.fullpath.split('.') \
                            if p.startswith('layout_') \
                              or p.startswith('row_') \
                                or p.startswith('cell_')]))
        default_kwargs = self.defaultKwargs()
        if border_width is None:
            border_width = default_kwargs.get('layout_border_width') or default_kwargs.get('border_width',0)
        border_color = border_color or default_kwargs.get('layout_border_color') or default_kwargs.get('border_color','silver')
        border_style = border_style or default_kwargs.get('layout_border_style') or default_kwargs.get('border_style','solid')
        lbl_class = lbl_class or default_kwargs.get('lbl_class','lbl_base')
        content_class = content_class or default_kwargs.get('content_class','content_base')
        self.style(".%s_layout{border:%s%s %s %s;position:absolute;}" % (
        name, border_width, um, border_style, border_color))
            
        layout = self.child(tag='layout', **kwargs)
        layout.layout_name = name
        layout.layout_class = 'gnrlayout %s_layout' % name
        layout.um = um
        layout.top = float(top or 0)
        layout.left = float(left or 0)
        layout.bottom = float(bottom or 0)
        layout.right = float(right or 0)
        layout.width = float(width or 0)
        layout.height = float(height or 0)
        layout.rowborder_total_height = 0
        layout.last_row_border_height = 0
        layout.border_width = float(border_width or 0)
        layout.border_color = border_color
        layout.border_style = border_style
        layout.row_border = row_border
        layout.cell_border = cell_border
        layout.lbl_height = float(lbl_height or 0)
        layout.lbl_class = lbl_class
        layout.content_class = content_class
        layout.elastic_rows = []
        layout.hasBorderTop = hasBorderTop
        layout.hasBorderLeft = hasBorderLeft
        layout.hasBorderRight = hasBorderRight
        layout.hasBorderBottom = hasBorderBottom
        layout.nested = self.parentNode.getAttr('tag') == 'cell'
        return layout
            
    def row(self, height=0, row_border=None, cell_border=None,
            lbl_height=None, lbl_class=None, 
            content_class=None, border_width=None,**kwargs):
        """Build a :meth:`row <gnr.core.gnrhtml.GnrHtmlSrc.row>` and return it
        
        :param height: the row's height
        :param row_border: the row's border
        :param cell_border: the border of the row's cell
        :param lbl_height: the height of the row's label
        :param lbl_class: the class of the row's label
        :param content_class: the class of the row's content"""
        assert self.parentNode.getAttr('tag') == 'layout'
        layout = self
        row = self.child(tag='row', **kwargs)
        row.lbl_height = float(lbl_height or 0)
        row.lbl_class = lbl_class
        row.content_class = content_class
        if row_border is None:
            row.row_border = layout.row_border
        else:
            row.row_border = row_border
        row.border_width = (border_width or layout.border_width) * row.row_border
        if height:
            height = height - row.border_width
        row.height = float(height or 0)
        if cell_border is None:
            row.cell_border = layout.cell_border
        else:
            row.cell_border = cell_border
        layout.last_row_border_height = row.border_width
        layout.rowborder_total_height += layout.last_row_border_height
        row.idx = len(layout) - 1
        row.layout = layout
        row.elastic_cells = []
        row.cellborder_total_width = 0
        if not row.height:
            layout.elastic_rows.append(row)
        return row
            
    def cell(self, content=None, width=0, content_class=None,
             lbl=None, lbl_class=None, lbl_height=None, cell_border=None,border_width=None, **kwargs):
        """Build a :meth:`cell` and return it
        
        :param content: the row's content
        :param width: the row's width
        :param content_class: the row's content class
        :param lbl: the cell's label
        :param lbl_class: the class of the row's label
        :param lbl_height: the height of the row's label
        :param lbl_height: the border of the row's label
        
        * if you don't define the cell width, then it takes all the remaining space"""
        assert self.parentNode.getAttr('tag') == 'row'
        row = self
        cell = row.child(tag='cell', **kwargs)
        content_class = content_class or row.content_class or row.layout.content_class
        #cell = row.child(tag='cell',content=content, **kwargs)
        if not content is None:
            cell.child(tag='div', content=content, class_=content_class)
        cell.width = float(width or 0)
        cell.row = row
        cell.content_class = content_class
        cell.lbl = lbl
        cell.lbl_class = lbl_class
        cell.lbl_height = float(lbl_height or 0)
        
        if cell_border is None:
            cell.cell_border = row.cell_border
        else:
            cell.cell_border = cell_border
        cell.border_width = (border_width or row.border_width or row.layout.border_width) * cell.cell_border
        row.last_cell_border_width = cell.border_width
        row.cellborder_total_width += row.last_cell_border_width
        return cell
            
class GnrHtmlBuilder(object):
    """TODO"""
    styleAttrNames = ['height', 'width', 'top', 'left', 'right', 'bottom',
                      'visibility', 'overflow', 'float', 'clear', 'display',
                      'z_index', 'border', 'position', 'padding', 'margin',
                      'color', 'white_space', 'vertical_align', 'background', 'text',
                      'font'];
    @extract_kwargs(default=True)
    def __init__(self, page_height=None, page_width=None, page_margin_top=None,
                 page_margin_left=None, page_margin_right=None, page_margin_bottom=None,
                 showTemplateContent=None,
                 htmlTemplate=None, page_debug=False,page_styles=None, srcfactory=None, css_requires=None,
                 print_button=None, bodyAttributes=None,parent=None,default_kwargs=None,translationService=None,
                 localizer=None,localize_to=None,
                    from_language=None,to_language=None,**kwargs):
        self.srcfactory = srcfactory or GnrHtmlSrc
        self.htmlTemplate = htmlTemplate or Bag()
        top_layer = Bag()
        if len(self.htmlTemplate):
            top_layer =  self.htmlTemplate['#%i' %(len(self.htmlTemplate)-1)]
        self.nextLetterhead = None
        self.page_height = page_height or top_layer['main.page.height']
        self.page_width = page_width or top_layer['main.page.width']
        if not (self.page_height and self.page_width):
            raise GnrHtmlSrcError('Missing page dimensions')
        self.page_margin_top = page_margin_top or top_layer['main.page.top'] or 0
        self.page_margin_left = page_margin_left or top_layer['main.page.left'] or 0
        self.page_margin_right = page_margin_right or top_layer['main.page.right'] or 0
        self.page_margin_bottom = page_margin_bottom or top_layer['main.page.bottom'] or 0
        self.page_debug = page_debug
        self.page_styles = page_styles
        self.print_button = print_button
        self.css_requires = css_requires or []
        self.showTemplateContent = showTemplateContent
        self.parent = parent
        self.default_kwargs = default_kwargs
        self.from_language = from_language
        self.to_language = to_language
        self.localize_to = localize_to
        self.translationService = translationService
        self.localizer = localizer

    def initializeSrc(self, body_attributes=None,**kwargs):
        """TODO"""
        body_attributes = body_attributes or {}
        body_attributes.update(kwargs)
        self.root = self.srcfactory.makeRoot(parentWrapper=self)
        self.root.default_kwargs = self.default_kwargs
        self.root.builder = self
        self.htmlBag = self.root.html()
        self.head = self.htmlBag.head()
        self.body = self.htmlBag.body(margin='0mm',**body_attributes)
        self.head.meta(http_equiv="Content-Type", content="text/html; charset=UTF-8")
        for css_require in self.css_requires:
            self.head.csslink(href=css_require)
        self.body.style("""
                        .no_print{
                            display:none;
                        }
                        [visible_if=""]{
                            display:none;
                        }
                        [hidden_if]{
                            display:none;
                        }
                        [hidden_if=""]{
                            display:block;
                        }
                        span[hidden_if=""]{
                            display:inline;
                        }
                        """, media='print')
        self.body.style("""
                        [visible_if=""]{
                            display:none;
                        }
                        [hidden_if]{
                            display:none;
                        }
                        div[hidden_if=""]{
                            display:block;
                        }
                        tr[hidden_if=""]{
                            display:table-row;
                        }
                        table[hidden_if=""]{
                            display:table;
                        }
                        span[hidden_if=""]{
                            display:inline;
                        }
            """)
        self.body.style("""
                        #printButton{
                            position:fixed;right:30px;top:5px;z-index:100;
                            cursor:pointer;',onclick='window.print();
                            background:#3F5A8D; color:white; -moz-border-radius:8px;
                            -webkit-border-radius:8px;font-size:9pt;
                            padding:3px;padding-left:8px;
                            padding-right:8px;border:1px solid white;
                            -moz-box-shadow:4px 4px 5px gray;
                            -webkit-box-shadow:4px 4px 5px gray;
                            font-family:courier;
                        }
                        """)

        self.head.style(f"""
            @page{{
                margin:0;
                size:{self.page_width}mm {self.page_height}mm;
            }}
        """)


    def prepareTplLayout(self,letterhead_root):
        """Prepare the layout template
        :param tpl: the template"""
        height = self.page_height - self.page_margin_top - self.page_margin_bottom
        width = self.page_width - self.page_margin_left - self.page_margin_right
        for i,b in enumerate(self.htmlTemplate.values()):
            regions = self.letterhead_layer(letterhead_root,b,height=height,width=width,count=i)
        return regions['center_center']

    @property
    def current_page_number(self):
        if self.parent:
            return self.parent.current_page_number +1
        return len(self.body)


    def letterhead_layer(self,letterhead_root,letterheadBag,width=None,height=None,count=None):
        layout = letterhead_root.layout(top=0,left=0,border=0,width=width,height=height,z_index=count)
        regions = dict(center_center=layout)
        curpage = str(self.current_page_number)
        if letterheadBag['main.design'] == 'headline':
            for region in ('top', 'center', 'bottom'):
                height = float(letterheadBag['layout.%s?height' % region] or 0)
                if region == 'center' or height:
                    row = layout.row(height=height)
                    for subregion in ('left', 'center', 'right'):
                        width = float(letterheadBag['layout.%s.%s?width' % (region, subregion)] or 0)
                        if subregion == 'center' or width:
                            innerHTML = letterheadBag['layout.%s.%s.html' % (region, subregion)] or None
                            if innerHTML:
                                innerHTML = innerHTML.replace('#pp','#TOTPAGE')
                                innerHTML = innerHTML.replace('#p',curpage)
                                innerHTML = "%s::HTML" % innerHTML
                            regions['%s_%s' % (region, subregion)] = row.cell(content=innerHTML, width=width, border=0,
                                                                                overflow='hidden')
        elif letterheadBag['main.design'] == 'sidebar':
            mainrow = layout.row(height=0)
            for region in ('left', 'center', 'right'):
                width = float(letterheadBag['layout.%s?width' % region] or 0)
                if region == 'center' or width:
                    col = mainrow.cell(width=width, border=0).layout()
                    for subregion in ('top', 'center', 'bottom'):
                        height = float(letterheadBag['layout.%s.%s?height' % (region, subregion)] or 0)
                        if subregion == 'center' or height:
                            row = col.row(height=height)
                            innerHTML = letterheadBag['layout.%s.%s.html' % (region, subregion)] or None
                            if innerHTML:
                                innerHTML = innerHTML.replace('#pp','#TOTPAGE')
                                innerHTML = innerHTML.replace('#p',curpage)
                                innerHTML = "%s::HTML" % innerHTML
                            regions['%s_%s' % (region, subregion)] = row.cell(content=innerHTML, border=0,overflow='hidden')
        return regions

    def parentNotify(self,method,*args,**kwargs):
        if self.parent:
            h = getattr(self.parent,method,None)
            if h:
                h(*args,**kwargs)
            
    def newPage(self):
        """Create a new page"""
        firstpage = len(self.body) == 0
        border_color = 'white'
        extra_style= ''
        if self.page_debug:
            border_color = 'red' if self.page_debug is True else self.page_debug
            extra_style = '{} box-shadow:3px 3px 4px gray;'.format(extra_style)
        page_break = '' if firstpage else 'page-break-before:always;'
        page = self.body.div(style="""position:relative;
                                   width:%smm;
                                   height:%smm;
                                   border:.3mm solid %s; /*do not remove */
                                   top:0mm;
                                   left:0mm;
                                   %s
                                   %s""" % (self.page_width, self.page_height, border_color, extra_style,page_break))
        self.parentNotify('onNewPage',page)
        letterhead_root = page.div(style="""position:absolute;
                                   top:%imm;
                                   left:%imm;
                                   right:%imm;
                                   bottom:%imm;%s""" % (
        self.page_margin_top, self.page_margin_left,
        self.page_margin_right, self.page_margin_bottom,
        self.page_styles or ''))
        if self.htmlTemplate:
            if not firstpage and self.nextLetterhead:
                self.htmlTemplate = self.nextLetterhead
                self.adaptParentSizes()
            self.nextLetterhead = self.htmlTemplate.pop('next_letterhead')
            letterhead_root = self.prepareTplLayout(letterhead_root)
        else:
            height = self.page_height - self.page_margin_top - self.page_margin_bottom
            width = self.page_width - self.page_margin_left - self.page_margin_right
            letterhead_root = letterhead_root.layout(name='paper',top=0,left=0,border_width=0,width=width,height=height,_class='paper_layout').row().cell()
        if firstpage and self.print_button:
            letterhead_root.div(self.print_button, _class='no_print', id='printButton', onclick='window.print();')
        return letterhead_root
            
    def adaptParentSizes(self):
        parent = getattr(self,'parent')
        if not parent:
            return
        top_layer =  self.htmlTemplate['#%i' %(len(self.htmlTemplate)-1)]
        parent = self.parent
        parent.page_margin_top = float(top_layer['main.page.top'] or parent.page_margin_top)
        parent.page_margin_left = float(top_layer['main.page.left'] or parent.page_margin_left)
        parent.page_margin_right = float( top_layer['main.page.right'] or parent.page_margin_right)
        parent.page_margin_bottom = float(top_layer['main.page.bottom'] or parent.page_margin_bottom)
        parent.page_header_height = float( top_layer['layout.top?height'] or parent.page_header_height)
        parent.page_footer_height = float(top_layer['layout.bottom?height'] or parent.page_footer_height)
        parent.page_leftbar_width = float(top_layer['layout.left?width'] or parent.page_leftbar_width)
        parent.page_rightbar_width = float(top_layer['layout.right?width'] or parent.page_rightbar_width)


    def styleForLayout(self):
        """TODO"""
        self.head.style(""".x_br{border-top:none!important;border-left:none!important;}
                           .x_r{border-top:none!important;border-left:none!important;border-bottom:none!important;}
                           .x_b{border-top:none!important;border-left:none!important;border-right:none!important;}
                           .x_{border:none!important;}
                        """)
                            
    def toHtml_(self, filepath=None):
        if isinstance(filepath,str):
            filepath = expandpath(filepath)
        self.finalize(self.body)
        self.html = self.root.toXml(filename=filepath,
                                    omitRoot=True,
                                    autocreate=True,
                                    forcedTagAttr='tag',
                                    addBagTypeAttr=False, typeattrs=False, self_closed_tags=['meta', 'br', 'img'])
        return self.html
            
    def toHtml(self, filepath=None):
        """TODO
        
        :param filepath: TODO"""
        if isinstance(filepath,str):
            filepath = expandpath(filepath)
        self.finalize(self.body)
        html = self.root.toXml(filename=filepath,
                                    omitRoot=True,
                                    autocreate=True,
                                    forcedTagAttr='tag',
                                    translate_cb=self.localize_cb,
                                    addBagTypeAttr=False, typeattrs=False, self_closed_tags=['meta', 'br', 'img'],
                                    docHeader='<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd"> \n')
        if self.to_language:
            if self.translationService is not None:
                html = self.translationService.translate(html,to_language=self.to_language,
                                                    from_language=self.from_language)
        self.html = html
        return self.html
    
    def localize_cb(self,txt,language=None):
        if self.localizer:
            return self.localizer.translate(txt=txt,language=self.localize_to or language)
        return txt

    def toPdf(self,filename,**kwargs):
        from weasyprint import HTML
        html_doc = HTML(string=self.html)
        html_doc.write_pdf(target=filename)
            


    def calculate_style(self, attr, um, **kwargs):
        """TODO
        
        :param attr: TODO
        :param um: the unit of measurement"""
        style = attr.pop('style', '')
        style = style.replace('\n', '')
        style_dict = dict([(splitAndStrip(x, ':')) for x in style.split(';') if ':' in x])
        style_dict.update(kwargs)
        for name in ('width', 'height', 'top', 'left', 'right', 'bottom'):
            if name in attr:
                value = attr.pop(name)
                try:
                    value = float(value)
                    i_value = int(value)
                    if i_value == value:
                        value = i_value
                    value = '%s%s' % (value, um)
                except:
                    pass
                style_dict[name] = value
        attr['style'] = ''.join(['%s:%s;' % (k, v) for k, v in style_dict.items()])
            
    def styleMaker(self, attr):
        """TODO
        
        :param attr: TODO"""
        style = attr.pop('style', '')
        style = style.replace('\n', '')
        style_dict = dict([(splitAndStrip(x, ':')) for x in style.split(';') if ':' in x])
        for oneattr in list(attr.keys()):
            if oneattr in self.styleAttrNames or ('_' in oneattr and oneattr.split('_')[0] in self.styleAttrNames):
                style_dict[oneattr.replace('_', '-')] = attr.pop(oneattr)
        attr['style'] = ''.join(['%s:%s;' % (k, v) for k, v in style_dict.items()])
            
    def finalize(self, src):
        """TODO
        
        :param src: TODO"""
        self.styleMaker(src.attributes)
        for node in src:
            node_tag = node.getAttr('tag')
            node_value = node.value
            getattr(self, 'finalize_%s' % node_tag, self.finalize_pass)(src, node.attr, node.value)
            
            if node_value and isinstance(node_value, GnrHtmlSrc):
                self.finalize(node_value)
            getattr(self, 'finalize_%s_after' % node_tag, self.finalize_pass)(src, node.attr, node.value)
            self.styleMaker(node.attr)
            
    def finalize_layout(self, parent, attr, layout):
        """TODO
        
        :param parent: TODO
        :param attr: TODO
        :param layout: TODO"""
        borders = '%s%s' % (layout.border_width, layout.um)
        row_border_width = layout.rowborder_total_height - layout.last_row_border_height
        if layout.nested:
            layout.has_topBorder = layout.hasBorderTop if layout.hasBorderTop is not None else bool(
                    layout.top or parent.lbl)
            layout.has_leftBorder = layout.hasBorderLeft if layout.hasBorderLeft is not None else bool(layout.left)
            layout.has_rightBorder = layout.hasBorderRight if layout.hasBorderRight is not None else bool(layout.right)
            layout.has_bottomBorder = layout.hasBorderBottom if layout.hasBorderBottom is not None else bool(
                    layout.bottom)
                    
            layout.width = layout.width or parent.width - layout.left - layout.right - int(
                    layout.has_leftBorder) * layout.border_width - int(layout.has_rightBorder) * layout.border_width
            layout.height = layout.height or parent.height - layout.top - layout.bottom - int(
                    layout.has_topBorder) * layout.border_width - int(layout.has_bottomBorder) * layout.border_width
            borders = ' '.join(
                    ['%s%s' % (int(getattr(layout, 'has_%sBorder' % side)) * layout.border_width, layout.um) for side in
                     ('top', 'right', 'bottom', 'left')])
        rows = layout.values() #is not an iterator
        if layout.elastic_rows:
            if layout.height:
                fixed_height_rows = sum([(row.height) for row in rows if row.height])
                free_height = (layout.height - fixed_height_rows - row_border_width) 
                height = free_height/len(layout.elastic_rows)
                for row in layout.elastic_rows:
                    row.height = height
            else:
                raise GnrHtmlSrcError('No total height with elastic rows')
                ## Possibile ricerca in profondità
        if rows:
            layout.height = sum([row.height for row in rows]) + row_border_width
            rows[-1].row_border = False
        attr['top'] = layout.top
        attr['left'] = layout.left
        attr['bottom'] = layout.bottom
        attr['right'] = layout.right
        attr['height'] = layout.height
        attr['width'] = layout.width
        attr['class'] = ' '.join(x for x in [attr.get('class'), layout.layout_class] if x)
        kw = {'border-width': borders}
        self.calculate_style(attr, layout.um, **kw)
        layout.curr_y = 0
        attr['tag'] = 'div'
                    
    def finalize_row(self, layout, attr, row):
        """TODO
        
        :param layout: TODO
        :param attr: TODO
        :param row: TODO"""
        row.elastic_cells = [cell for cell in row.values() if not cell.width]
        if row.elastic_cells:
            elastic_cells_count = len(row.elastic_cells)
            if layout.width:
                totalcellborderwidth =  row.cellborder_total_width - row.last_cell_border_width
                fixed_width_sum = sum([(cell.width or 0)+cell.attributes.get('extra_width',0) for cell in row.values()])
                free_space = layout.width - fixed_width_sum - totalcellborderwidth
                elastic_width =  free_space / elastic_cells_count
                for cell in row.elastic_cells:
                    cell.width = elastic_width
            else:
                raise GnrHtmlSrcError('No total width with elastic cells')
                ## Possibile ricerca in profondità
        cells = row.values()
        if cells:
            cells[-1].cell_border = False
        attr['height'] = row.height
        attr['top'] = layout.curr_y
        attr['tag'] = 'div'
        attr['left'] = 0
        attr['right'] = 0
        attr['class'] = ' '.join(x for x in [attr.get('class'), 'layout_row'] if x)
        layout.curr_y += row.height + row.border_width
        self.calculate_style(attr, layout.um, position='absolute')
        row.curr_x = 0
                    
    def finalize_cell(self, row, attr, cell):
        """TODO
        
        :param row: TODO
        :param attr: TODO
        :param cell: TODO"""
        cell.height = row.height
        width = cell.width + attr.get('extra_width',0)
        cell.width = width
        if cell.lbl:
            self.setLabel(cell, attr)
        bottom_border_width = row.border_width
        right_border_width = cell.border_width
        attr['width'] = width
        attr['height'] = cell.height
        attr['tag'] = 'div'
        attr['top'] = 0
        attr['left'] = row.curr_x
        cell_class = 'x_br'
        if not bottom_border_width:
            cell_class = cell_class.replace('b', '')
        if not right_border_width:
            cell_class = cell_class.replace('r', '')
        else:
            attr['border_width'] = '{}mm'.format(right_border_width)
        attr['class'] = ' '.join(x for x in [attr.get('class'), row.layout.layout_class, cell_class] if x)
        row.curr_x += width + right_border_width
        self.calculate_style(attr, row.layout.um)
                     
    def setLabel(self, cell, attr):
        """TODO
        
        :param cell: TODO
        :param attr: TODO"""
        row = cell.row
        layout = row.layout
        um = row.layout.um
        lbl = cell.lbl
        lbl_height = cell.lbl_height or row.lbl_height or layout.lbl_height
        lbl_class = cell.lbl_class or row.lbl_class or layout.lbl_class
        content_class = cell.content_class or row.content_class or layout.content_class
        if len(cell) > 0:
            cur_content_node = cell.popNode('#0')
            cur_content_attr = cur_content_node.attr
            cur_content_value = cur_content_node.value
        else:
            cur_content_value = ''
            # set the label
        lbl_attr = {'class': lbl_class, 'top': 0, 'height': lbl_height, 'left': 0, 'right': 0}
        self.calculate_style(lbl_attr, um, position='absolute')
        cell.child('div', content=lbl, **lbl_attr)
        if isinstance(cur_content_value, GnrHtmlSrc):
            tag = cur_content_attr.pop('tag')
            cur_content_value.top = cur_content_value.top + lbl_height
            cell.child(tag, content=cur_content_value, **cur_content_attr)
        else:
            content_attr = {'class': content_class, 'top': lbl_height, 'left': 0, 'right': 0}
            self.calculate_style(content_attr, um, position='absolute')
            cell.child('div', content=cur_content_value, **content_attr)
                    
    def finalize_pass(self, src, attr, value):
        """TODO
        
        :param src: TODO
        :param attr: TODO
        :param value: TODO"""
        pass
        
def test0(pane):
    d = 180
    layout = pane.layout(width=d, height=d, um='mm', top=10, left=10, border_width=3, lbl_height=4,
                         lbl_class='z1', content_class='content', _class='mmm')
                         
    layout.style(".z1{font-size:7pt;background-color:silver;text-align:center}")
    layout.style(".content{font-size:12pt;text-align:center;}")
    layout.style(".myclass{font-size:18pt;text-align:center;background-color:green;}")
    layout.style(".uuu{color:red;}")
    layout.style(".mmm{font-family:courier;}")
    layout.script("aaaaaaaaaaa")
    x = d / 3.
    r = layout.row(_class='uuu')
    r.cell('foo', lbl='name', _class='myclass')
    r.cell('bar', width=x, lbl='weight')
    r.cell('<b>spam</b>::HTML', lbl='time')
    r = layout.row(height=x)
    r.cell('foo', lbl='cc')
    subtable = r.cell(width=x)
    r.cell('baz', lbl='dd')
    r = layout.row()
    r.cell('foo', lbl='alfa')
    r.cell('bar', width=x, lbl='beta')
    r.cell('baz', lbl='gamma')
    layout = subtable.layout(name='inner', um='mm', border_width=1, top=0, left=0, right=0, bottom=0,
                             border_color='green',
                             lbl_height=4, lbl_class='z1', content_class='content')
    x = x / 2.
    r = layout.row()
    r.cell('foo')
    r.cell('bar', width=x)
    r.cell('baz')
    r = layout.row(height=x)
    r.cell('foo')
    r.cell('bar', width=x)
    r.cell('baz')
    r = layout.row()
    r.cell('foo')
    r.cell('bar', width=x)
    r.cell('baz')
                    
def test1(pane):
    layout = pane.layout(width='150', height=150, um='mm', top=10, left=10, border_width=.3,
                         lbl_height=4, lbl_class='z1', content_class='content')
    layout.style(".z1{font-size:7pt;background-color:silver;text-align:center}")
    layout.style(".z2{font-size:9pt;background-color:pink;text-align:right;}")
    layout.style(".content{font-size:12pt;text-align:center;}")
                    
    r = layout.row(height=20)
    r.cell('foo', width=40, lbl='name')
    r.cell()
    r.cell('bar', width=22)
    r.cell('<b>spam</b>::HTML', width=18)
    r.cell()
    r.cell('eggs', width=30)
    sublayout = layout.row().cell()
    r = layout.row(height=40)
    r.cell('maa', width=60, lbl='name')
    r.cell()
    r.cell('dooo', width=60)
    sl = sublayout.layout(width='150', height=70, um='mm', top=0, left=0, border_width=.3,
                          lbl_height=4, lbl_class='z1', content_class='content')
    r = sl.row(height=10)
    r.cell('xx', width=10)
    r.cell()
    r.cell('yy', width=20)
    sl.row().cell()
    r = sl.row(height=30)
    r.cell('tt', width=40)
    r.cell('kkkkk')
    r.cell('mmm', width=40)
                    
def testRowsInner(cell):
    innerLayout = cell.layout(name='inner', um='mm', top=0, left=0, bottom=3, right=0, border_width=1.2,
                              border_color='navy', lbl_height=4,
                              lbl_class='z1', hasBorderLeft=True)
    row = innerLayout.row()
    row.cell('aaa', width=30, lbl='bb', background_color='lime')
    row.cell('bbb', width=0, lbl='aa')
                    
def testRows(pane):
    layout = pane.layout(name='outer', width=180, height=130, um='mm',
                         top=1, left=1,
                         border_width=3, border_color='red',
                         lbl_height=4,
                         lbl_class='z1')
                         
    layout.style(".z1{font-size:7pt;background-color:silver;text-align:center}")
    
    for h in [20, 0, 0, 20]:
        row = layout.row(height=h)
        #row.cell('hhh',lbl='foo', width=60)
        row.cell(lbl='bar')
        testRowsInner(row.cell(lbl='foo', width=60))
        #testRowsInner(row.cell(lbl='bar'))
                    
if __name__ == '__main__':
    builder = GnrHtmlBuilder()
    builder.initializeSrc()
    builder.styleForLayout()
    test1(builder.body)
    #builder.toHtml('../../../../_testhtml/test1.html')
    builder.toPdf('piero.pdf')
