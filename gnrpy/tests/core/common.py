"""
Common objects for gnr.app testing, mostly custom Genropy environment
"""
import os
import os.path
import tempfile
import shutil
import random
from gnr.app.gnrdeploy import InstanceMaker

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
        <gui css_theme="modern"/>
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
        os.environ.pop("GENRO_GNRFOLDER")

class BaseGnrAppTest(BaseGnrTest):
    pass
