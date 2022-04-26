# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from time import sleep
from imdb import IMDb

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