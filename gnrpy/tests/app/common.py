"""
Common objects for gnr.app testing, mostly custom Genropy environment
"""
import os
import os.path

class BaseGnrAppTest:
    """
    Base class for testing environment
    """
    @classmethod
    def setup_class(cls):
        """ 
        Setup the testing environment 
        """
        cls.local_dir = os.path.dirname(__file__)
        os.environ['GENRO_GNRFOLDER'] = cls.local_dir
        cls.test_genro_root = os.path.abspath(os.path.join(cls.local_dir, "..", "..", ".."))
        cls.test_app_path = os.path.join(cls.test_genro_root, "projects")
        cls.ENV_FILENAME = os.path.join(cls.local_dir, "environment.xml")
        with open(cls.ENV_FILENAME, "w", encoding='utf-8') as env_file_fd:
            env_file_fd.write(f"""<?xml version="1.0" ?>
            <GenRoBag>
  <environment>
    <gnrhome value="{cls.test_genro_root}/"/>
  </environment>
  <projects>
    <genropy path="{cls.test_genro_root}/projects"/>
    <custom path="{cls.test_genro_root}/genropy_projects"/>
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
  <gnrdaemon host="localhost" port="40404" hmac_key="glhwdtmk5kqf"/>
</GenRoBag>
""")
    @classmethod
    def teardown_class(cls):
        """Teardown testing environment"""
        os.unlink(cls.ENV_FILENAME)
        os.environ.pop("GENRO_GNRFOLDER")
