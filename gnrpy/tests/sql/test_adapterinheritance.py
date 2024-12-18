import glob
import os.path
import gnr.sql.adapters
import importlib

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

    def _get_class_methods_names(self, cls):
        return {method for method in dir(cls) if callable(getattr(cls, method)) and not method.startswith("_")}

    def _get_class_methods(self, cls):
        return {getattr(cls, method) for method in dir(cls) if callable(getattr(cls, method)) and not method.startswith("_")}

    def test_docstrings(self):
        missing_docs = []
        for method in self._get_class_methods(self.base_adapter):
            if not method.__doc__:
                missing_docs.append(method.__name__)

        assert len(missing_docs) < 1, f"Base adapter public methods without documentation: {missing_docs}"
        
    def test_methods(self):
        base_adapter_methods = self._get_class_methods_names(self.base_adapter)
        extra_method_recap = {}
        for adapter_name, adapter_class in self.all_adapters.items():
            print(adapter_class, type(adapter_class))
            adapter_methods = self._get_class_methods_names(adapter_class)
            not_found_in_base = adapter_methods - base_adapter_methods
            if not_found_in_base:
                extra_method_recap[adapter_name] = not_found_in_base

        found_extras = sum([len(v) for k, v in extra_method_recap.items()])
        assert found_extras < 1, f"Adapter public methods not found in base adapter: {extra_method_recap}"
            
    
