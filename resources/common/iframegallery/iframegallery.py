from gnr.core.gnrdecorator import customizable,metadata
from gnr.core.gnrlang import objectExtract
from gnr.core.gnrbag import Bag
from gnr.web.gnrbaseclasses import BaseComponent

class IframeGallery(BaseComponent):
    py_requires = 'public:Public' 

    def pbl_avatarTemplate(self):
        return '<div>$user<div>'

    def configuration(self):
        raise NotImplementedError('You must override configuration')

    def main(self,root,**kwargs):
        self.iframeGalleryStart(root,**kwargs)

    def iframeGalleryStart(self,root,**kwargs):
        frame = root.framePane(datapath='main')
        mainbar = frame.top.slotToolbar('5,stackSwitch,*,currentPageTitle,*,username,5',background='white',color='#444',font_size='1.3em',height='30px')
        configuration = self.configuration()
        pages = Bag()        
        mainbar.username.div(width='15em').div(self.user,font_weight='bold',text_align='right')
        box = mainbar.stackSwitch.div(width='15em')
        box.div(width='20px').menudiv(storepath='main.availablePages',
                                selected_caption='main.currentPageTitle',
                                selected_code='main.currentPage',
                                iconClass='iconbox application_menu')
        mainbar.currentPageTitle.div('^main.currentPageTitle')
        mainsc = frame.center.stackContainer(selectedPage='^main.currentPage')
        for idx,conf in enumerate(configuration):
            conf.setdefault('pageName',f'p_{idx:02}')
            pages.addItem(conf['pageName'],None,code=conf['pageName'],caption=conf['title'])
            if conf.get('url'):
                pane = mainsc.contentPane(title=conf['title'],overflow='hidden',pageName=conf['pageName'])
                pane.iframe(src=conf['url'],height='100%',width='100%',border=0)
            elif conf['method']:
                getattr(self,conf['method'])(mainsc,pageName=conf['pageName'],title=conf['title'])
        frame.bottom.slotBar('*,logo,*',height='10px')
        root.data('main.availablePages',pages)
        root.data('main.currentPage',configuration[0]['pageName'])
        root.data('main.currentPageTitle',configuration[0]['title'])