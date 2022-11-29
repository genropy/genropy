# encoding: utf-8
class Menu(object):
    def config(self,root):
        biz = root.branch(u"!!Business intelligence")
        biz.thpage(u"!!Dashboards management", table="biz.dashboard",tags="admin")
        self.dashboardBranch(biz)

    def dashboardBranch(self,root,pkg=None,code=None):
        if pkg is True:
            pkg = None
        f = self.db.table('biz.dashboard').query(where='$pkgid=:pk' if pkg else None,pk=pkg).fetch()
        if not f:
            return
        if pkg:
            pkgName = self.db.package(pkg).name_long
            b = root.branch(f'{pkgName} Dashboards')
        else:
            b = root.branch('!!All dashboards')
        for r in f:
            if r['private']:
                continue
            b.webpage(r['description'] or f"Dashboard {r['code']}",
                            filepath=f'/biz/dashboards/{r["pkgid"]}/{r["code"]}' )

