#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import tempfile
import pytest
import datetime

from gnr.core.gnrbag import Bag
from gnr.web.gnrwsgisite_proxy import gnrsiteregister as gsr

class TestBaseSiteRegisterMultiIndex(object):
    def setup_class(cls):
        cls.test_items = [
            {
                "register_item_id": f"item{x}",
                "connection_id": f"conn{x}",
                "user": f"user{x}"
            } for x in range(5)
        ]

        class FakeConnectionRegister(gsr.BaseRegister):
            multi_index_attrs = ['user']

        cls.obj = FakeConnectionRegister({})
        for item in cls.test_items:
            cls.obj.addRegisterItem(item)

    def test_methods(self):
        # ensure that modification to the object referenced
        # by the main index is reflected also in the other one
        r = self.obj.subscribe_path("item0", "mypath")
        assert r is None
        r = self.obj.get_item("item0")
        assert len(r['subscribed_paths']) == 1
        assert "mypath" in r['subscribed_paths']
        for item in self.obj._multi_indexes['user'][r['user']]:
            if item.get("register_item_id") == "item0":
                assert len(item['subscribed_paths']) == 1
                assert "mypath" in item['subscribed_paths']
        # dropping
        r = self.obj.drop_item("item0")
        assert r['user'] not in self.obj._multi_indexes['user']

class TestBaseSiteRegister(object):
    def setup_class(cls):
        cls.obj = gsr.BaseRegister({})
        cls.test_item_id = '1x2'
        cls.test_item = {
            "register_item_id": cls.test_item_id
            }
        
    def test_base_methods(self):
        # multi indexes
        assert len(self.obj._multi_indexes) == 0
        
        # addRegisterItem
        self.obj.addRegisterItem(self.test_item)

        for attr in ['datachanges', 'datachanges_idx', 'subscribed_paths']:
            assert attr in self.obj.registerItems[self.test_item_id]
        assert self.test_item_id in self.obj.itemsData

        # registerName
        assert self.obj.registerName == "BaseRegister"

        # keys
        assert self.test_item_id in self.obj.keys()
        # exists
        assert self.obj.exists(self.test_item_id)

        #items
        r = self.obj.items()
        assert len(r) == 1
        assert r[0][0] == self.test_item_id
        # if the same item_id is added, the list won't change
        self.obj.addRegisterItem(self.test_item)
        assert len(self.obj.items()) == 1
        r = self.obj.items(include_data=True)
        assert 'data' in r[0][1]

        # values
        r = self.obj.values()
        assert r[0]['register_item_id'] == self.test_item_id
        r = self.obj.values(include_data=True)
        assert 'data' in r[0]

        # get_item
        r = self.obj.get_item(self.test_item_id)
        assert r['register_item_id'] == self.test_item_id

        # request the item with its data
        r = self.obj.get_item(self.test_item_id, include_data=True)
        assert r['register_item_id'] == self.test_item_id
        assert 'data' in r


        # locking
        
        # reduce locking time
        gsr.LOCK_EXPIRY_SECONDS = 1
        r = self.obj.lock_item(self.test_item_id, reason="Unwanted")
        assert len(self.obj.locked_items) == 1
        assert r is True
        # lock the same with different reason
        self.obj.lock_item(self.test_item_id, reason="Unwanted 2")
        assert len(self.obj.locked_items) == 1 # SHOULD BE 2
        
        # lock the same with same reason
        r = self.obj.lock_item(self.test_item_id, reason="Unwanted")
        assert len(self.obj.locked_items) == 1
        assert r is True
        time.sleep(gsr.LOCK_EXPIRY_SECONDS*1.5)
        
        # locking after expiry time
        r = self.obj.lock_item(self.test_item_id, reason="Unwanted 2")
        assert len(self.obj.locked_items) == 0
        assert r is False


        # unlocking

        # non-existing item
        r = self.obj.unlock_item("asdasdasda")
        assert r is None
        
        self.obj.lock_item(self.test_item_id, reason="Unknown")
        self.obj.unlock_item(self.test_item_id, reason="Unknown")
        assert len(self.obj.locked_items) == 0
        
        self.obj.lock_item(self.test_item_id, reason="Unknown")
        r = self.obj.unlock_item(self.test_item_id, reason="Unknown 2")
        assert r is False
        assert len(self.obj.locked_items) == 1
        

        # refresh
        r = self.obj.refresh("unknown_id")
        assert r is None


        ts_attrs = ['last_user_ts', 'last_rpc_ts', 'refresh_ts']
        ts_attrs_int = ['last_user_ts', 'last_rpc_ts', 'last_refresh_ts']
        r = self.obj.refresh(self.test_item_id)
        for a in ts_attrs_int:
            assert r[a] is None
            
        r = self.obj.refresh(self.test_item_id,
                             **{x: 1 for x in ts_attrs})
        for a in ts_attrs_int:
            assert r[a] == 1
        
        # DROPPING!

        r = self.obj.drop_item(self.test_item_id)
        assert len(self.obj.items()) == 0
        assert r['register_item_id'] == self.test_item_id
        assert self.test_item_id not in self.obj.registerItems
        assert self.test_item_id not in self.obj.itemsData
        assert self.test_item_id not in self.obj.itemsTS

        r = self.obj.drop_item("Non-existing-id")
        assert r is None

        # UPDATING
        r = self.obj.update_item("non-existing-id")
        assert r is None
        
        self.obj.addRegisterItem(self.test_item)
        r = self.obj.update_item(self.test_item_id)
        assert r is not None
        assert r['register_item_id'] == self.test_item_id
        r = self.obj.update_item(self.test_item_id, {"_testing": 1})
        assert '_testing' in r
        assert r['_testing'] == 1


        # DATACHANGES
        # set a new datachange
        r = self.obj.set_datachange("non-existing-id"
                                    "mypath",
                                    1)
        assert r is None
        
        r = self.obj.set_datachange(self.test_item_id,
                                    "mypath",
                                    1)
        assert r is None
        r = self.obj.get_item(self.test_item_id)
        assert len(r['datachanges']) == 1
        assert r['datachanges_idx'] == 1
        assert r['datachanges'][0].path == "mypath"
        assert r['datachanges'][0].value == 1


        # get the datachange
        r = self.obj.get_datachanges("non-existing-id")
        assert r is None
        r = self.obj.get_datachanges(self.test_item_id)
        assert len(r) == 1

        r = self.obj.get_datachanges(self.test_item_id, reset=True)
        assert len(r) == 1
        r = self.obj.get_datachanges(self.test_item_id)
        assert len(r) == 0


        # set with replace
        self.obj.set_datachange(self.test_item_id,
                                "mypath",
                                1)
        r = self.obj.get_datachanges(self.test_item_id)
        self.obj.set_datachange(self.test_item_id,
                                "mypath",
                                2, replace=True)
        r = self.obj.get_datachanges(self.test_item_id)
        assert r[0].value == 2

        # reset
        r = self.obj.reset_datachanges(self.test_item_id)
        assert len(r['datachanges']) == 0


        # drop
        r = self.obj.drop_datachanges("non-existing-id", '')
        assert r is None
        
        r = self.obj.set_datachange(self.test_item_id,
                                    "mypath",
                                    1)
        self.obj.drop_datachanges(self.test_item_id, "non-existing-path")
        r = self.obj.get_item(self.test_item_id)
        assert len(r['datachanges']) == 1
        self.obj.drop_datachanges(self.test_item_id, "my")
        r = self.obj.get_item(self.test_item_id)
        assert len(r['datachanges']) == 0


        # subscriptions

        r = self.obj.subscribe_path(self.test_item_id, "mypath")
        assert r is None
        r = self.obj.get_item(self.test_item_id)
        assert len(r['subscribed_paths']) == 1
        assert "mypath" in r['subscribed_paths']

        # test for unique values
        self.obj.subscribe_path(self.test_item_id, "mypath")
        r = self.obj.get_item(self.test_item_id)
        assert len(r['subscribed_paths']) == 1
        self.obj.subscribe_path(self.test_item_id, "mypath2")
        r = self.obj.get_item(self.test_item_id)
        assert len(r['subscribed_paths']) == 2

        # load/dump

        with tempfile.NamedTemporaryFile() as fp:
            # dump all data
            
            self.obj.dump(fp)
            self.obj._reset_all_registers()
            assert len(self.obj.items()) == 0
            fp.seek(0)
            self.obj.load(fp)
            assert len(self.obj.items()) == 1
            

        # get dbenv

        r = self.obj.get_dbenv(self.test_item_id)
        assert isinstance(r, Bag)
        assert len(r) == 0


        # caching

        assert len(self.obj.cached_tables) ==0
        self.obj.invalidateTableCache(None)

        # offloading
        offload_test_item_id = 'rarelyused'
        offload_test_item = {
            "register_item_id": offload_test_item_id
            }
        
        self.obj.addRegisterItem(offload_test_item)
        assert len(self.obj.items()) == 2
        self.obj.offload_item(offload_test_item_id)
        assert len(self.obj.items()) == 1
        assert self.obj.item_is_offloaded(offload_test_item_id) is True
        assert self.obj.get_item(offload_test_item_id)['register_item_id'] == offload_test_item_id
        assert len(self.obj.items()) == 2
        assert offload_test_item_id in self.obj.registerItems

class TestGlobalRegister(object):
    def setup_class(cls):
        cls.obj = gsr.GlobalRegister({})

    def test_methods(self):
        self.obj.create("bubustest")
        # the first entry it automatically created
        # with identifier "*", apparently with no
        # specific reason
        assert len(self.obj.items()) == 2
        self.obj.drop("bubustest")
        assert len(self.obj.items()) == 1

class TestUserRegister(object):
    def setup_class(cls):
        cls.obj = gsr.UserRegister({})

    def test_methods(self):
        self.obj.create("Cardinal Biggles", 1, "cardinal")
        assert len(self.obj.items()) == 1

        self.obj.drop("Cardinal Biggles", _testing=True)
        assert len(self.obj.items()) == 0

        
class TestPageRegister(object):
    def setup_class(cls):
        cls.obj = gsr.PageRegister({})
        cls.test_page_id = 0x84
        cls.test_page_name = "My wonderful page"
        cls.test_page_conn = "conn12345"
        
    def test_methods(self):
        assert len(self.obj.items()) == 0
        self.obj.create(self.test_page_id, pagename = self.test_page_name)
        assert len(self.obj.items()) == 1
        r = self.obj.get_item(self.test_page_id)
        assert r['register_item_id'] == self.test_page_id
        assert r['connection_id'] is None

        assert len(self.obj.pages()) == 1
        self.obj.drop(self.test_page_id)
        assert len(self.obj.pages()) == 0

        self.obj.create(self.test_page_id, pagename = self.test_page_name)
        self.obj.drop(self.test_page_id, cascade=True, _testing=True)
        r = self.obj.pages()

        # subscribed tables
        r = self.obj.filter_subscribed_tables([1,2,3])
        assert len(r) is 0
        assert isinstance(r, list)

        with pytest.raises(TypeError):
            r = self.obj.filter_subscribed_tables(1)

        self.obj.create(self.test_page_id, pagename = self.test_page_name)
        self.obj.subscribeTable(self.test_page_id, table='mytable',
                                subscribe=True)
        assert self.test_page_id in self.obj.subscribed_table_page_keys("mytable")

        self.obj.subscribeTable(self.test_page_id, table='mytable',
                                subscribe=False)
        assert self.test_page_id not in self.obj.subscribed_table_page_keys("mytable")

        self.obj.subscribeTable(self.test_page_id, table='mytable',
                                subscribe=True)
        r = self.obj.subscribed_table_page_items("mytable")
        assert r[0][0] == self.test_page_id
        assert "mytable" in r[0][1]['subscribed_tables']

        r = self.obj.subscribed_table_pages("mytable")
        assert r[0]['register_item_id'] == self.test_page_id
        assert "mytable" in r[0]['subscribed_tables']


        
        # connections

        r = self.obj.connection_page_keys(self.test_page_conn)
        assert len(r) is 0
        r = self.obj.connection_page_items(self.test_page_conn)
        assert len(r) is 0
        # clean the register, add a page with a connection
        self.obj.drop(self.test_page_id)
        self.obj.create(self.test_page_id,
                        connection_id=self.test_page_conn,
                        user="babbala",
                        pagename = self.test_page_name)
        r = self.obj.connection_page_keys(self.test_page_conn)
        assert len(r) is 1
        assert self.test_page_id in r
        r = self.obj.connection_page_items(self.test_page_conn)
        assert len(r) is 1
        assert r[0][0] == self.test_page_id


        # pages with connections
        r = self.obj.pages(connection_id=self.test_page_conn)
        assert len(r) == 1
        r = self.obj.pages(connection_id=self.test_page_conn,
                           user="babbala")
        assert len(r) == 1
        r = self.obj.pages(connection_id=self.test_page_conn,
                           user="babbala2")
        assert len(r) == 0

        r = self.obj.pages(filters="*")
        assert len(r) == 1
        r = self.obj.pages(filters=False)
        assert len(r) == 1

        # pages filtering
        r = self.obj.pages(filters=f"user:babbala AND connection:{self.test_page_conn}")
        assert len(r) == 1
        assert isinstance(r[0], Bag)
        
        r = self.obj.pages(filters=f"user:babba* AND connection:{self.test_page_conn}")
        assert len(r) == 1
        assert isinstance(r[0], Bag)
        
        r = self.obj.pages(filters=f"user:babbala2 AND connection:{self.test_page_conn}")
        assert len(r) == 0
        r = self.obj.pages(filters=f"connection:unknown AND auanagana:1 AND user:foobar")
        assert len(r) == 0

        # profilers
        profiler = "HELLO I AM A PROFILER"
        self.obj.updatePageProfilers(self.test_page_id, profiler)
        assert profiler in self.obj.pageProfilers.values()

        # set store subscription
        r = self.obj.setStoreSubscription(self.test_page_id)
        assert r is None
        
        r = self.obj.get_item_data(self.test_page_id)

        self.obj.pageInMaintenance(self.test_page_id, _testing=True)
        r = self.obj.pageInMaintenance("non-existing")
        assert r is None

        # setInClientData
        test_path = "/cirmolo"
        test_value = 2
        r = self.obj.setInClientData(test_path, value=test_value)
        assert r is None
        
        r = self.obj.setInClientData(test_path, value=test_value,
                                     page_id=self.test_page_id,
                                     reason="My reason")
        
        r = self.obj.get_item(self.test_page_id)
        assert len(r['datachanges']) == 1
        data_change = r['datachanges'][0]
        assert data_change.path == test_path
        assert data_change.value == test_value

        r = self.obj.setInClientData(test_path, value=test_value,
                                     filters="user:babbala",
                                     reason="My reason 2")
        
        r = self.obj.get_item(self.test_page_id)
        assert len(r['datachanges']) == 2
        data_change = r['datachanges'][0]
        assert data_change.path == test_path
        assert data_change.value == test_value

        # testing filters passing
        r = self.obj.setInClientData(test_path, value=test_value,
                                     filters="user:unknown AND path:/antani" ,
                                     reason="My unknown reason")

        
        test_bag = Bag()
        test_bag.addItem('/vialemanidalnaso', 3, _client_path="/")
        r = self.obj.setInClientData(test_bag, page_id=self.test_page_id)
        r = self.obj.get_item(self.test_page_id)
        assert len(r['datachanges']) == 3

        # pending context
        r = self.obj.setPendingContext(self.test_page_id, ())
        assert r is None
        self.obj.setPendingContext("non-existing-page", ())
        with pytest.raises(TypeError):
            self.obj.setPendingContext("non-existing-page",
                                       [('/path', 'foo', {'bar': 1})]
                                       )
        self.obj.setPendingContext(self.test_page_id,
                                   [('/path', 'foo', {'bar': 1})]
                                   )
        r = self.obj.get_item(self.test_page_id)
        assert "/path" in r['subscribed_paths']

        self.obj.setPendingContext(self.test_page_id,
                                   [('/path', Bag(), {'bar': 1})]
                                   )
        r = self.obj.get_item(self.test_page_id)
        assert "/path" in r['subscribed_paths']

        self.obj.create(self.test_page_id, pagename = self.test_page_name,
                        subscribed_tables="mytable")
        r = self.obj.subscribed_table_page_items("mytable")
        assert r[0][0] == self.test_page_id
        assert "mytable" in r[0][1]['subscribed_tables']
        
class TestConnectionRegister(object):
    def setup_class(cls):
        cls.obj = gsr.ConnectionRegister({})
        cls.test_user = "cardinal"
        cls.test_conn_id = "connection-1234"
    def test_methods(self):
        # create
        r = self.obj.create(self.test_conn_id,
                            connection_name="connection-name-1234",
                            user=self.test_user,
                            user_id=1,
                            user_name="cardinal",
                            user_agent="SpanishInquisitionWebkit 1833")

        assert r['user_name'] == 'cardinal'
        assert len(self.obj.items()) == 1

        # drop
        r = self.obj.drop(self.test_conn_id, _testing=True)
        assert r is None
        assert len(self.obj.items()) == 0

        # cascading
        # create
        r = self.obj.create(self.test_conn_id,
                            connection_name="connection-name-1234",
                            user=self.test_user,
                            user_id=1,
                            user_name="cardinal",
                            user_agent="SpanishInquisitionWebkit 1833")
        
        r = self.obj.drop(self.test_conn_id, cascade=True,
                          _testing=True)
        assert r is None
        assert len(self.obj.items()) == 0

        # iterations
        r = self.obj.create(self.test_conn_id,
                            connection_name="connection-name-1234",
                            user=self.test_user,
                            user_id=1,
                            user_name="cardinal",
                            user_agent="SpanishInquisitionWebkit 1833")
        
        # connections
        r = self.obj.connections()
        assert len(r) == 1

        r = self.obj.connections(user=self.test_user)
        assert len(r) == 1
        r = self.obj.connections(user=self.test_user, include_data=True)
        assert len(r) == 1


                
        r = self.obj.user_connection_keys("cardinal")
        assert self.test_conn_id in r

        r = self.obj.user_connection_items("cardinal")
        assert r[0][0] == self.test_conn_id 

class MockDaemon(object):
    def register(self, *args, **kwargs):
        pass
    
class MockGnrSiteRegisterServer(object):
    def __init__(self, sitename=None,
                 daemon_uri=None,
                 storage_path=None,
                 debug=None):
        self.sitename = sitename
        self.gnr_daemon_uri = daemon_uri
        self.debug = debug
        self.storage_path = storage_path
        self._running = False
        self.daemon = MockDaemon()

        
class TestSiteRegister(object):
    def setup_class(cls):
        server = MockGnrSiteRegisterServer(sitename="Testing",
                                           daemon_uri="localhost",
                                           storage_path="/tmp",
                                           debug=None)
        cls.obj = gsr.SiteRegister(server, sitename="Test Site",
                                   storage_path="/tmp/testsite")
        cls.test_conn_id = "conn1234"
        cls.test_conn_id2 = "conn5678"
        cls.test_page_id = "page1234"
        cls.test_user_id = "user1234"
        cls.test_user_id2 = "user5678"
        
    def test_on_site_stop(self, capfd):
        self.obj.on_site_stop()
        out, err = capfd.readouterr()
        assert out == "site stopped\n"

    def test_configuration(self):
        self.obj.setConfiguration()
        assert self.obj.cleanup_interval == 120
        assert self.obj.page_max_age == 120
        assert self.obj.guest_connection_max_age == 40
        assert self.obj.connection_max_age == 600

        test_conf = [
            ('interval', 'cleanup_interval', 1),
            ('page_max_age', 'page_max_age', 2),
            ('guest_connection_max_age', 'guest_connection_max_age', 3),
            ('connection_max_age', 'connection_max_age', 4)
        ]
        
        self.obj.setConfiguration({x[0]: x[2] for x in test_conf})
        for conf_key in test_conf:
            assert getattr(self.obj, conf_key[1]) == conf_key[2]
        
    def test_methods(self):
        r = self.obj.checkCachedTables("mytable")
        assert r is None
        # inject data
        self.obj.page_register.cached_tables['mytable']
        assert len(self.obj.page_register.cached_tables) == 1
        r = self.obj.checkCachedTables("mytable")
        assert len(self.obj.page_register.cached_tables) == 0

        r = self.obj.new_connection(self.test_conn_id,
                                    user=self.test_user_id)
        
        with pytest.raises(AssertionError):
            r = self.obj.new_connection(self.test_conn_id)

        assert len(self.obj.user_register.items()) == 1
        assert len(self.obj.connection_register.items()) == 1

        assert len(self.obj.page_register.items()) == 0
        self.obj.new_page(self.test_page_id,
                          connection_id=self.test_conn_id,
                          user=self.test_user_id)

        assert len(self.obj.page_register.items()) == 1
        assert self.test_page_id in self.obj.connection_page_keys(self.test_conn_id)
        r = self.obj.drop_pages(self.test_conn_id)
        assert len(self.obj.connection_register.items()) == 1
        assert len(self.obj.page_register.items()) == 0
        assert r is None

        assert len(self.obj.user_register.items()) == 1
        r = self.obj.drop_connections(self.test_user_id)
        assert len(self.obj.connection_register.items()) == 0
        assert len(self.obj.user_register.items()) == 1

        r = self.obj.drop_user(self.test_user_id)
        assert r is None
        assert len(self.obj.user_register.items()) == 0
        
        self.obj.new_connection(self.test_conn_id,
                                user=self.test_user_id)
        r = self.obj.user_connection_items(self.test_user_id)
        assert len(r) == 1
        r = self.obj.user_connections(self.test_user_id)
        assert len(r) == 1
        assert self.test_user_id == r[0]['user']
        

        self.obj.new_page(self.test_page_id,
                          connection_id=self.test_conn_id,
                          user=self.test_user_id)

        r = self.obj.connection_page_items(self.test_conn_id)
        assert len(r) == 1
        r = self.obj.connection_pages(self.test_conn_id)
        assert len(r) == 1

        r = self.obj.subscribed_table_pages()
        assert len(r) == 0


        r = self.obj.connection(self.test_conn_id)
        assert r['register_item_id'] == self.test_conn_id
        assert r['user'] == self.test_user_id
        
        r = self.obj.pages(connection_id=self.test_conn_id)
        assert r[0]['register_item_id'] == self.test_page_id
        assert r[0]['user'] == self.test_user_id

        r = self.obj.pages(connection_id=self.test_conn_id,
                           index_name="myindex")
        
        r = self.obj.user(self.test_user_id)
        assert r
        assert r['user'] == self.test_user_id
        r = self.obj.users()
        assert r
        assert r[0]['user'] == self.test_user_id

        r = self.obj.page(self.test_page_id)
        assert r
        assert r['register_item_id'] == self.test_page_id

        r = self.obj.counters()
        # we only have 1 item per register
        for k, v in r.items():
            assert v == 1


        assert len(self.obj.users()) == 1
        r = self.obj.new_connection(self.test_conn_id2,
                                    user=self.test_user_id2)
        assert len(self.obj.users()) == 2
        self.obj.change_connection_user(self.test_conn_id,
                                        user=self.test_user_id2)
        r = self.obj.connection(self.test_conn_id)
        assert r['user'] == self.test_user_id2
        assert len(self.obj.users()) == 1

        # since test_user_id has been dropped automatically with the
        # change _connection, switch the connection back to it will
        # recreate it in the register
        self.obj.change_connection_user(self.test_conn_id,
                                        user=self.test_user_id)
        assert len(self.obj.users()) == 2

        r = self.obj.refresh("non-existing-page")
        assert r is None

        now = datetime.datetime.now()
        r = self.obj.refresh(self.test_page_id)
        assert (r['last_refresh_ts']-now).seconds < 2

        
        r = self.obj.page(self.test_page_id)
        self.obj.drop_connection(self.test_conn_id)
        r = self.obj.refresh(self.test_page_id)
        assert r is None

        # get_register
        r = self.obj.get_register("connection")
        assert r is self.obj.connection_register

        # cleanup
        r = self.obj.cleanup()
        assert r is None
        self.obj.last_cleanup -= self.obj.cleanup_interval*5
        r = self.obj.cleanup()
        assert len(r) == 0
        
