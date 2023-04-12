# encoding: utf-8
class Menu(object):
    def config(self,root):
        biz = root.branch(u"!!Business intelligence")
        biz.thpage(u"!!Dashboards management", table="biz.dashboard",tags="admin")
        self.dashboardBranch(biz)

    def dashboardBranch(self,root,filterPkg=None,code=None,**kwargs):
        if filterPkg is True:
            filterPkg = None
        f = self.db.table('biz.dashboard').query(where='$pkgid=:pk' if filterPkg else None,pk=filterPkg, order_by='$code').fetch()
        if not f:
            return
        if filterPkg:
            pkgName = self.db.package(filterPkg).name_long
            b = root.branch(f'{pkgName} Dashboards',**kwargs)
        else:
            b = root.branch('!!All dashboards')
        for r in f:
            if r['private']:
                continue
            b.webpage(r['description'] or f"Dashboard {r['code']}",
                            filepath=f'/biz/dashboards/{r["pkgid"]}/{r["code"]}' )

