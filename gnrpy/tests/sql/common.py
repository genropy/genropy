import os
import os.path
from testing.postgresql import Postgresql

from gnr.core.gnrbag import Bag

class BaseGnrSqlTest:
    """
    Base class for grn.sql testing
    """
    @classmethod
    def setup_class(cls):
        """
        Setup testing environment
        """
        base_path = os.path.join(os.path.dirname(__file__), "data")
        cls.CONFIG = Bag(os.path.join(base_path, 'configTest.xml'))
        cls.SAMPLE_XMLSTRUCT = os.path.join(base_path, 'dbstructure_base.xml')
        cls.SAMPLE_XMLDATA = os.path.join(base_path, 'dbdata_base.xml')
        cls.SAMPLE_XMLSTRUCT_FINAL = os.path.join(base_path, 'dbstructure_final.xml')
        
        if "CI" in os.environ:
            # we are running inside the bitbucket CI
            cls.pg_conf = dict(host="127.0.0.1",
                               port="5432",
                               user="postgres",
                               password="postgres")
        else:
            cls.pg_instance = Postgresql()
            cls.pg_conf = cls.pg_instance.dsn()

    @classmethod    
    def teardown_class(cls):
        """
        Teardown testing enviroment
        """
        if not "CI" in os.environ:
            cls.pg_instance.stop()


def configurePackage(pkg):
    pkg.attributes.update(comment='video package', name_short='video', name_long='video', name_full='video')

    people = pkg.table('people', name_short='people', name_long='People',
                       rowcaption='name,year:%s (%s)', pkey='id')
    people.column('id', 'L')
    people.column('name', name_short='N.', name_long='Name')
    people.column('year', 'L', name_short='Yr', name_long='Birth Year')
    people.column('nationality', name_short='Ntl', name_long='Nationality')

    cast = pkg.table('cast', name_short='cast', name_long='Cast',
                     rowcaption='', pkey='id')
    cast.column('id', 'L')
    cast.column('movie_id', 'L', name_short='Mid',
                name_long='Movie id').relation('movie.id')
    cast.column('person_id', 'L', name_short='Prs',
                name_long='Person id').relation('people.id')
    cast.column('role', name_short='Rl.', name_long='Role')
    cast.column('prizes', name_short='Priz.', name_long='Prizes', size='40')

    movie = pkg.table('movie', name_short='Mv', name_long='Movie',
                      rowcaption='title', pkey='id')
    movie.column('id', 'L')
    movie.column('title', name_short='Ttl.', name_long='Title',
                 validate_case='capitalize', validate_len='3:40')
    movie.column('genre', name_short='Gnr', name_long='Genre',
                 validate_case='upper', validate_len='3:10', indexed='y')
    movie.column('year', 'L', name_short='Yr', name_long='Year', indexed='y')
    movie.column('nationality', name_short='Ntl', name_long='Nationality')
    movie.column('description', name_short='Dsc', name_long='Movie description')

    dvd = pkg.table('dvd', name_short='Dvd', name_long='Dvd', pkey='code')
    dvd_id = dvd.column('code', 'L')
    dvd.column('movie_id', 'L',name_short='Mid', name_long='Movie id').relation('movie.id')
    dvd.column('purchasedate', 'D', name_short='Pdt', name_long='Purchase date')
    dvd.column('available', name_short='Avl', name_long='Available')
