from gnr.web.gnrbaseclasses import BaseComponent
SIZES = ['48','72','96','144','168','192','384','512']

class PWAPreferencePane(BaseComponent):
    def pwaPreferencePane(self,parent,title='PWA',**kwargs):
        bc = parent.borderContainer(datapath='.pwa',title=title,**kwargs)
        fb = bc.contentPane(region='top',padding='10px').mobileFormBuilder(cols=3)
        fb.textbox(value='^.name',lbl='Name')
        fb.textbox(value='^.short_name',lbl='Short name')
        fb.textbox(value='^.description',lbl='Description',colspan=2)
        fb.textbox(value='^.display',lbl='Display')
        fb.textbox(value='^.background_color',lbl='Background color')
        center = bc.borderContainer(region='center')
        center.contentPane(region='top').div('Upload PWA images',_class='preference_subtitle')
        box = center.contentPane(region='center',margin='10px').div(style="""display: flex;
                                                    flex-wrap: wrap;
                                                    align-content: center;
                                                    justify-content: space-evenly;
                                                    align-items: center;
                                            """,datapath='.icons')
        for size in SIZES:
            filename = f"logo_{size}.png"
            image_container = box.div(display='inline-block',margin='5px')
            image_container.div(f'{size}x{size}',text_align='center',color='silver')
            image_container.img(src=f'^.{filename}', edit=True,
                                    upload_filename=filename, 
                                     upload_folder='site:pwa/images',
                                     placeholder=True,
                                     crop_border='2px solid silver',
                                     height=f'{size}px',width=f'{size}px',
                                     crop_height=f'{size}px',crop_width=f'{size}px')