# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from time import sleep

from gnr.core.gnrlang import GnrException
from gnr.app.gnrdeploy import PathResolver

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"

    def windowTitle(self):
        return 'RemoteSelect'  

    def test_0_remoteSelect_pkg(self,pane):
        "Define a Rpc method and use it in remoteSelect to get package name"
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.remoteSelect(value='^.package',width='25em',lbl='Package',
                        method=self.getPackages, hasDownArrow=True)

    @public_method
    def getPackages(self,_querystring=None,_id=None,**kwargs):
        result=Bag()
        for pkg_code,pkg in self.db.application.packages.items():
            result.setItem(pkg_code, None, caption=pkg.attributes['name_long'], _pkey=pkg_code)
        print(x)
        return result,dict(columns='caption', headers='Package')

    def test_1_remoteSelect_user(self,pane):
        "Define a Rpc method and use it in remoteSelect"
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.remoteSelect(value='^.user',width='25em',lbl='User',auxColumns='status,auth_tags',
                        method=self.getUserCustomRpc)

    @public_method
    def getUserCustomRpc(self,_querystring=None,_id=None,**kwargs):
        result = Bag()
        if _id:
            f = self.db.table('adm.user').query(where='$id = :u',u=_id).fetch()
        else:
            sleep(2)
            f = self.db.table('adm.user').query(where='$username ILIKE :u',u='%s%%' %_querystring.replace('*','')).fetch()
        for i,r in enumerate(f):
            result.setItem('%s_%s' %(r['id'],i),None,caption='%s - %s' %(r['username'], r['auth_tags']),
                status=r['status'],auth_tags=r['auth_tags'],_pkey=r['id'],username=r['username'])
        return result,dict(columns='username,status,auth_tags',headers='Name,Status,Tags')

    def test_2_remoteSelect_with_api(self, pane, **kwargs):
        """Use remote select to connect with service and get results.
        Run pip install imdbpy first to retrieve movie data"""
        fb = pane.formbuilder(cols=1)
        fb.remoteSelect(value='^.movie_id',lbl='Movie title', method=self.getMovieId, 
                            auxColumns='title,kind,year', selected_cover='.cover')
        fb.img(src='^.cover', hidden='^.cover?=!#v', width='200px', height='266px')
        fb.div('^.movie_id', lbl='Movie ID: ')

    @public_method
    def getMovieId(self,_querystring=None,**kwargs):
        try:
            from imdb import IMDb
        except:
            raise GnrException('This test requires library imdb')
        ia = IMDb()
        result = Bag()
        movies = ia.search_movie(_querystring)
        for movie in movies:
            movie_id = movie.movieID
            title=movie.get('title')
            year=str(movie.get('year'))
            result.addItem(movie_id, None, title=title, year=year,
                                kind=movie.get('kind'), cover=movie.get('full-size cover url'), 
                                _pkey=movie_id, caption='{title} ({year})'.format(title=title, year=year))
        return result,dict(columns='title,kind,year', headers='Title,Kind,Year')  

    def test_3_remoteSelect_list(self,pane):
        "Define a Rpc method and use it in remoteSelect to show a list of items"
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.remoteSelect(value='^.weekday',width='25em',lbl='Week Day',
                        method=self.getWeekDays, hasDownArrow=True)

    @public_method
    def getWeekDays(self,_querystring=None,_id=None,**kwargs):
        result=Bag()
        weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in weekdays:
            result.setItem('w_%s' %(day), None, caption=day, _pkey='%s' %(day))
        return result,dict(columns='caption', headers='Weekday')

    def test_4_remoteSelect_files(self,pane):
        "Define a Rpc method and use it in remoteSelect to get package name"
        fb = pane.formbuilder(cols=1, border_spacing='4px')
        fb.filteringSelect(value='^.dirname', lbl='Directory name', values='alpha:Alpha,beta:Beta')
        fb.remoteSelect(value='^.file',width='25em',lbl='File',
                        condition_dirname='=.dirname',
                        method=self.getFiles,
                        hasDownArrow=True)

    @public_method
    def getFiles(self,dirname=None,**kwargs):
        result=Bag()
        dirnode = self.site.storageNode('rsrc:pkg_test','tables','prov_test','remote_test',dirname)
        for fn in dirnode.children():
            result.setItem(fn.cleanbasename, None, caption=fn.cleanbasename.title(), _pkey=fn.basename)
        return result,dict(columns='caption', headers='File')

    def test_5_printResources(self, pane):
        "Find and select print resources"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.remoteSelect(value='^.printres',lbl='Print resource', method=self.getPrintResources, 
                                    auxColumns='pkg,tbl,res', hasDownArrow=True,
                                    selected_pkg='.pkg', selected_tbl='.tbl')

    @public_method
    def getPrintResources(self, _querystring=None, **kwargs):
        path_resolver = PathResolver()
        project_path = path_resolver.project_name_to_path('sandbox')
        result = Bag()
        packages = self.db.model.src['packages'].keys()
        for p in packages:
            tables = self.db.model.src[f'packages.{p}.tables']
            if not tables:
                continue
            for t in tables.keys():
                print_nodes = self.db.application.site.storageNode(project_path,'packages',p,'resources','tables',t,'print')
                if not print_nodes.children():
                    continue
                print_res = [h.basename for h in print_nodes.children() if h.basename.endswith('.py')]
                for res in print_res:
                    res_key = res.split('.')[0]
                    result.setItem(res_key, None, pkg=p, tbl=t, caption=res, _pkey=res_key)
        return result,dict(columns='pkg,tbl,caption', headers='Package,Table,Print res')