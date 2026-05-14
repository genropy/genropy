"""HTML5 element catalog — ported from the W3C Validator RELAX NG schema.

112 elements with sub_tags validation metadata. The list mirrors
`genro_builders/contrib/html/html5_elements.py`; do not edit manually —
regenerate from the upstream `html5_schema.bag.json` if the schema
changes.

The sub_tags strings encode the allowed child elements of each tag and
are stored as `_widget_metadata` on the decorated function. They are
NOT consumed at runtime by GnrDomSrc; future validation passes can opt
into them via the decorator metadata.
"""

from __future__ import annotations

from gnr.web.widgets import WidgetMixinBase, element


class HtmlWidgets(WidgetMixinBase):
    """HTML5 element mixin. Declares the standard HTML5 tag namespace
    consumed by `GnrDomSrc.__getattr__` through `AllWidgets`."""

    @element()
    def a(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def abbr(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def address(self): ...

    @element()
    def area(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def article(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def aside(self): ...

    @element()
    def audio(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def b(self): ...

    @element()
    def base(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def bdi(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def bdo(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def blockquote(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def body(self): ...

    @element()
    def br(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def button(self): ...

    @element()
    def canvas(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def caption(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def cite(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def code(self): ...

    @element()
    def col(self): ...

    @element(sub_tags='col,script,template')
    def colgroup(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def data(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,option,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def datalist(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def dd(self): ...

    @element(name='del')
    def del_(self): ...

    @element(sub_tags='summary')
    def details(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def dfn(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def dialog(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def div(self): ...

    @element(sub_tags='div,dt,script,template')
    def dl(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def dt(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def em(self): ...

    @element()
    def embed(self): ...

    @element(sub_tags='legend')
    def fieldset(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def figcaption(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figcaption,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def figure(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def footer(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def form(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h1(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h2(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h3(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h4(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h5(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def h6(self): ...

    @element(sub_tags='base,link,meta,noscript,script,style,template,title')
    def head(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def header(self): ...

    @element(sub_tags='h1,h2,h3,h4,h5,h6,p,script,template')
    def hgroup(self): ...

    @element()
    def hr(self): ...

    @element(sub_tags='head')
    def html(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def i(self): ...

    @element()
    def iframe(self): ...

    @element()
    def img(self): ...

    @element()
    def input(self): ...

    @element()
    def ins(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def kbd(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def label(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,h1,h2,h3,h4,h5,h6,hgroup,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def legend(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def li(self): ...

    @element()
    def link(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def main(self): ...

    @element()
    def map(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def mark(self): ...

    @element(sub_tags='li,script,template')
    def menu(self): ...

    @element()
    def meta(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def meter(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def nav(self): ...

    @element()
    def noscript(self): ...

    @element()
    def object(self): ...

    @element(sub_tags='li,script,template')
    def ol(self): ...

    @element(sub_tags='option,script,template')
    def optgroup(self): ...

    @element()
    def option(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def output(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def p(self): ...

    @element(sub_tags='img,script,source,template')
    def picture(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def pre(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def progress(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def q(self): ...

    @element()
    def rp(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def rt(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def ruby(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def s(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def samp(self): ...

    @element()
    def script(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def search(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def section(self): ...

    @element(sub_tags='hr,optgroup,option,script,template')
    def select(self): ...

    @element()
    def slot(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def small(self): ...

    @element()
    def source(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def span(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def strong(self): ...

    @element()
    def style(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def sub(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,h1,h2,h3,h4,h5,h6,hgroup,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def summary(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def sup(self): ...

    @element(sub_tags='caption,colgroup,script,tbody,template,tfoot,thead,tr')
    def table(self): ...

    @element(sub_tags='script,template,tr')
    def tbody(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def td(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,caption,cite,code,col,colgroup,data,datalist,del,details,dfn,dialog,div,dl,dt,em,embed,fieldset,figcaption,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,legend,li,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,optgroup,option,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,source,span,strong,style,sub,summary,sup,table,tbody,td,template,textarea,tfoot,th,thead,time,tr,track,u,ul,var,video,wbr',
    )
    def template(self): ...

    @element()
    def textarea(self): ...

    @element(sub_tags='script,template,tr')
    def tfoot(self): ...

    @element(
        sub_tags='a,abbr,address,area,article,aside,audio,b,bdi,bdo,blockquote,br,button,canvas,cite,code,data,datalist,del,details,dfn,dialog,div,dl,em,embed,fieldset,figure,footer,form,h1,h2,h3,h4,h5,h6,header,hgroup,hr,i,iframe,img,input,ins,kbd,label,link,main,map,mark,menu,meta,meter,nav,noscript,object,ol,output,p,picture,pre,progress,q,ruby,s,samp,script,search,section,select,slot,small,span,strong,sub,sup,table,template,textarea,time,u,ul,var,video,wbr',
    )
    def th(self): ...

    @element(sub_tags='script,template,tr')
    def thead(self): ...

    @element()
    def time(self): ...

    @element()
    def title(self): ...

    @element(sub_tags='script,td,template,th')
    def tr(self): ...

    @element()
    def track(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def u(self): ...

    @element(sub_tags='li,script,template')
    def ul(self): ...

    @element(
        sub_tags='a,abbr,area,audio,b,bdi,bdo,br,button,canvas,cite,code,data,datalist,del,dfn,em,embed,i,iframe,img,input,ins,kbd,label,link,map,mark,meta,meter,noscript,object,output,picture,progress,q,ruby,s,samp,script,select,slot,small,span,strong,sub,sup,template,textarea,time,u,var,video,wbr',
    )
    def var(self): ...

    @element()
    def video(self): ...

    @element()
    def wbr(self): ...
