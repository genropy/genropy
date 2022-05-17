# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        itgeo_italia = root.branch(u"!![it]Geo Italia", tags="admin")
        itgeo_italia.thpage(u"!![it]Nazione", table="glbl.nazione", tags="")
        itgeo_italia.thpage(u"!![it]Regione", table="glbl.regione", tags="")
        itgeo_italia.thpage(u"!![it]Provincia", table="glbl.provincia", tags="")
        itgeo_italia.thpage(u"!![it]Comune", table="glbl.comune", tags="")
        itgeo_italia.thpage(u"!![it]Nuts", table="glbl.nuts", tags="")

