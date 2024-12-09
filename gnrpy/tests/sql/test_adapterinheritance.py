import warnings
import pytest
import glob
import os.path
import gnr.sql.adapters
import importlib
import pprint

from gnr.sql.adapters import _gnrbaseadapter as ba

ADAPTER_DIR = os.path.dirname(gnr.sql.adapters.__file__)

class TestAdapterInheritance():

    
    @classmethod
    def setup_class(cls):
        cls.base_adapter = ba.SqlDbAdapter
        cls.all_adapters = {}
        cls.not_tested = {}
        for adapter_name in glob.glob(os.path.join(ADAPTER_DIR, 'gnr*py')):
            adapter_module = os.path.basename(adapter_name)[:-3]
            implementation_name = adapter_module[3:]
            module_full_path = f'gnr.sql.adapters.{adapter_module}'
            try:
                cls.all_adapters[implementation_name] = importlib.import_module(module_full_path).SqlDbAdapter
            except Exception as e:
                cls.not_tested[implementation_name] = e

    def _get_class_methods(self, cls):
        return {method for method in dir(cls) if callable(getattr(cls, method)) and not method.startswith("_")}
    
    def test_methods(self):
        base_adapter_methods = self._get_class_methods(self.base_adapter)
        extra_method_recap = {}
        for adapter_name, adapter_class in self.all_adapters.items():
            adapter_methods = self._get_class_methods(adapter_class)
            not_found_in_base = adapter_methods - base_adapter_methods
            extra_method_recap[adapter_name] = not_found_in_base


        found_extras = sum([len(v) for k, v in extra_method_recap.items()])
        if found_extras > 0:
            warnings.warn(f"Adapter public methods not found in base adapter: {extra_method_recap}")
            
    
