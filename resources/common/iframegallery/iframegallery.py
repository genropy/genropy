from gnr.core.gnrbag import Bag
from gnr.web.gnrbaseclasses import BaseComponent

class IframeGallery(BaseComponent):
    py_requires = 'public:Public' 

    def pbl_avatarTemplate(self):
        return '<div>$user</div>'

    def configuration(self):
        raise NotImplementedError('You must override configuration')

    def main(self,root,**kwargs):
        self.iframeGalleryStart(root,**kwargs)

    def iframeGalleryStart(self,root,**kwargs):
        frame = root.framePane(datapath='main')
        self.ig_header(frame)
        self.ig_footer(frame)
        configuration = self.configuration()
        pages = Bag()        
        mainsc = frame.center.stackContainer(selectedPage='^main.currentPage')
        for idx,conf in enumerate(configuration):
            conf.setdefault('pageName',f'p_{idx:02}')
            pages.addItem(conf['pageName'],None,code=conf['pageName'],caption=conf['title'])
            if conf.get('url'):
                pane = mainsc.contentPane(title=conf['title'],overflow='hidden',pageName=conf['pageName'])
                pane.iframe(src=conf['url'],height='100%',width='100%',border=0)
            elif conf['method']:
                getattr(self,conf['method'])(mainsc,pageName=conf['pageName'],title=conf['title'])
        #frame.bottom.slotBar('*,logo,*',height='10px',childname='lastbar')
        root.data('main.availablePages',pages)
        root.data('main.currentPage',configuration[0]['pageName'])
        root.data('main.currentPageTitle',configuration[0]['title'])

    def ig_footer(self,frame):
        sb = frame.bottom.slotBar('3,applogo,genrologo,*,logout,debugping,3',_class='slotbar_toolbar ig_bottom',height='22px')
        applogo = sb.applogo.div()
        if hasattr(self,'application_logo'):
            applogo.div(_class='application_logo_container',height='18px').img(src=self.application_logo,height='100%')
        sb.genrologo.div(_class='application_logo_container',height='18px').img(src='/_rsrc/common/images/made_with_genropy_small.png',height='100%')
        sb.logout.div(connect_onclick="genro.logout()",_class='iconbox icnBaseUserLogout switch_off',tip='!!Logout')
        sb.debugping.div(_class='ping_semaphore')


    def ig_header(self,frame):
        mainbar = frame.top.slotBar('5,stackSwitch,*,currentPageTitle,*,username,5',height='30px',_class='ig_top')
        mainbar.username.div(width='20px',overflow='visible',position='absolute'
                            ).div(self.user,font_weight='bold',
                            position='absolute',top='-8px',right='20px')
        mainbar.stackSwitch.div(width='20px').menudiv(storepath='main.availablePages',
                                selected_caption='main.currentPageTitle',
                                selected_code='main.currentPage',
                                iconClass='iconbox application_menu')
        mainbar.currentPageTitle.div('^main.currentPageTitle')
