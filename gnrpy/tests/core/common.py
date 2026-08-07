"""
Common objects for gnr.app testing, mostly custom Genropy environment
"""
import os
import os.path
import tempfile
import shutil
import random

import gnr.app.gnrapp as ga
from gnr.dev.makers.instance import InstanceMaker

class BaseGnrTest:
    """
    Base class for testing environment
    """
    @classmethod
    def setup_class(cls):
        """ 
        Setup the testing environment 
        """
        cls.local_dir = os.path.dirname(__file__)
        cls.tmp_conf_dir = tempfile.mkdtemp(prefix=f"{cls.local_dir}/")
        fconf = os.path.join(cls.tmp_conf_dir, "gnr")
        os.mkdir(fconf)
        cls.conf_dir = fconf
        os.environ['GENRO_GNRFOLDER'] = cls.conf_dir
        cls.daemon_port = random.randint(40000,45000)
        cls.test_genro_root = os.path.abspath(os.path.join(cls.local_dir, *[".."]*3))
        cls.test_app_path = os.path.join(cls.test_genro_root, "projects")
        
        cls.test_instance_name = "gnrtest"
        cls.test_instance_path = os.path.join(cls.tmp_conf_dir, cls.test_instance_name, "instances")
        cls.ENV_FILENAME = os.path.join(cls.conf_dir, "environment.xml")
        with open(cls.ENV_FILENAME, "w", encoding='utf-8') as env_file_fd:
            env_file_fd.write(f"""<?xml version="1.0" ?>
<GenRoBag>
  <environment>
    <gnrhome value="{cls.test_genro_root}/"/>
  </environment>
  <projects>
    <genropy path="{cls.test_genro_root}/projects"/>
    <custom path="{cls.test_genro_root}/genropy_projects"/>
    <custom path="{cls.tmp_conf_dir}"/>
  </projects>
  <packages>
    <genropy path="{cls.test_genro_root}/packages"/>
  </packages>
  <static>
    <js>
      <dojo_11 path="{cls.test_genro_root}/dojo_libs/dojo_11" cdn=""/>
      <gnr_11 path="{cls.test_genro_root}/gnrjs/gnr_d11"/>
    </js>
  </static>
  <resources>
    <genropy path="{cls.test_genro_root}/resources"/>
  </resources>
  <webtools>
    <genropy path="{cls.test_genro_root}/webtools"/>
  </webtools>
  <gnrdaemon host="localhost" port="{cls.daemon_port}" hmac_key="whoknows"/>
</GenRoBag>
""")
        os.mkdir(os.path.join(cls.conf_dir, "instanceconfig"))
        with open(os.path.join(cls.conf_dir, "instanceconfig", "default.xml"), "w", encoding='utf-8') as fp:
            fp.write(f"""<?xml version="1.0" ?>
<GenRoBag>
        <packages/>
        <authentication>
                <xml_auth defaultTags="user,xml">
                        <admin pwd="password" tags="superadmin,_DEV_,admin,user"/>
                </xml_auth>
        </authentication>
        <api_keys>
           <foobar value="hellothere"/>
        </api_keys>
</GenRoBag>""")
        os.mkdir(os.path.join(cls.conf_dir, "siteconfig"))
        with open(os.path.join(cls.conf_dir, "siteconfig", "default.xml"), "w", encoding='utf-8') as fp:
            fp.write(f"""<?xml version="1.0" ?>
<GenRoBag>
        <wsgi debug="True::B" reload="True::B" port="8080"/>
        <gui css_theme="{os.environ.get('GNR_CSS_THEME', 'mimi')}"/>
        <jslib dojo_version="11" gnr_version="11"/>
        <resources>
                <common/>
                <js_libs/>
        </resources>
        <gnrdaemon host="localhost" port="{cls.daemon_port}" hmac_key="whoknows"/>
</GenRoBag>""")

        # create a fake testing instance
        os.makedirs(cls.test_instance_path)
        instance_maker = InstanceMaker(cls.test_instance_name, base_path=cls.test_instance_path, packages=[])
        instance_maker.do()

        

        # os.mkdir(os.path.join(cls.test_instance_path, "gnrtest"))
        # os.mkdir(os.path.join(cls.test_instance_path, "gnrtest", "config"))
        cls.test_instance_config_path = os.path.join(cls.test_instance_path, cls.test_instance_name,
                                                     "config", "instanceconfig.xml")
        shutil.copy(os.path.join(cls.local_dir, "..", "datafiles", "instanceconfig.xml"),
                    cls.test_instance_config_path)
        
    @classmethod
    def teardown_class(cls):
        """Teardown testing environment"""
        shutil.rmtree(cls.tmp_conf_dir)
        os.environ.pop("GENRO_GNRFOLDER", None)

class BaseGnrAppTest(BaseGnrTest):
    app_name = 'gnrdevelop'
    
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls._tempdir = tempfile.mkdtemp()
        cls.app = ga.GnrApp(cls.app_name, db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(cls._tempdir, 'testing'),
        ))

    @classmethod
    def teardown_class(cls):
        super().teardown_class()
        if cls._tempdir and os.path.exists(cls._tempdir):
            shutil.rmtree(cls._tempdir)

def checkInstance(instance_name):
    """Attempt to load a Genropy instance.
    Returns the GnrApp object or None if not available."""
    try:
        return ga.GnrApp(instance_name)
    except:
        return None

def build_missing_schema_dbs(instance_name):
    """Create the sqlite schema files an instance needs but does not ship.

    With sqlite every package schema lives in its own ``<sqlschema>.db`` file
    beside the main database. Some of those files hold runtime data only and are
    not versioned, so on a fresh checkout the schemas they carry do not exist at
    all: the adapter creates the files empty on connect and the first query fails
    with ``no such table``.

    The database is built in a temporary folder and the schema files produced
    there are copied over the empty ones. Building from scratch is the only path
    sqlite supports, since the adapter cannot ALTER an existing column: schema
    files that already hold data are left untouched.

    Does nothing on non sqlite instances.

    :param instance_name: name of the instance to provision
    :return: the list of schemas that have been built"""
    app = ga.GnrApp(instance_name)
    if app.db.implementation != 'sqlite':
        return []
    datadir = os.path.dirname(app.db.dbname)
    schema_files = {pkg.sqlschema: os.path.join(datadir, f"{pkg.sqlschema}.db")
                    for pkg in app.db.packages.values()
                    if pkg.sqlschema and pkg.sqlschema != app.db.main_schema}
    missing = sorted(sqlschema for sqlschema, path in schema_files.items()
                     if not os.path.exists(path) or os.path.getsize(path) == 0)
    if not missing:
        return []
    tempdir = tempfile.mkdtemp()
    try:
        fresh = ga.GnrApp(instance_name, db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(tempdir, os.path.basename(app.db.dbname))))
        fresh.db.model.check(applyChanges=True)
        for sqlschema in missing:
            shutil.copy(os.path.join(tempdir, f"{sqlschema}.db"), schema_files[sqlschema])
    finally:
        shutil.rmtree(tempdir, ignore_errors=True)
    return missing
