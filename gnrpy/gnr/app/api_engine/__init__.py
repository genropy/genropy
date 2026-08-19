"""gnr.app.api_engine — application-level facade for introspection and
JSON-safe read access to a GenroPy database.

Public surface:

    from gnr.app.api_engine import ApiEngine
    engine = ApiEngine('my_instance')   # or ApiEngine(my_app)

The engine bundles enumeration, relation-tree schema, per-column typing,
OpenAPI schema synthesis and safe query execution.
"""

from gnr.app.api_engine.core import ApiEngine, ApiEngineError

__all__ = ['ApiEngine', 'ApiEngineError']
