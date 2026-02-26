# -*- coding: utf-8 -*-

"""Edge case tests for Grouplet widget - mixin clash and recursion scenarios"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler"""

    def test_1_rpc_mixin_clash(self, pane):
        """Two grouplets with same RPC name - verify no mixin clash"""
        bc = pane.borderContainer(height='400px')
        top = bc.contentPane(region='top', height='60px', padding='10px',
                             background='#f0f0f0', border_bottom='1px solid silver')
        top.div("""Both grouplets define a @public_method named testRpc.
                   When loaded as mixins the serialized RPC names become:
                   *|grouplets/rpctesting/rpc_foo;testRpc and *|grouplets/rpctesting/rpc_bar;testRpc.
                   The dataRpc in each formlet references self.testRpc which gets serialized
                   with the correct mixin path at render time.
                   Left button should show 'foo + timestamp', right button 'bar + timestamp'.""")
        left = bc.contentPane(region='left', width='50%', splitter=True)
        right = bc.contentPane(region='center')
        left.grouplet(value='^.rpc_foo', resource='rpctesting/rpc_foo')
        right.grouplet(value='^.rpc_bar', resource='rpctesting/rpc_bar')

    def test_2_rpc_mixin_clash_topic(self, pane):
        """Two grouplets with same RPC name inside the same remote construction - verify no mixin clash"""
        bc = pane.borderContainer(height='400px')
        top = bc.contentPane(region='top', height='60px', padding='10px',
                             background='#f0f0f0', border_bottom='1px solid silver')
        top.div("""Same as test_1 but both grouplets are loaded as a topic via resource='rpctesting',
                   so both rpc_foo and rpc_bar are constructed within the same remote call.
                   Even in this case there is no mixin clash: serialized RPC names remain distinct
                   (*|grouplets/rpctesting/rpc_foo;testRpc vs *|grouplets/rpctesting/rpc_bar;testRpc)
                   because each formlet's dataRpc is serialized with its own mixin path.""")
        bc.contentPane(region='center').grouplet(value='^.rpctesting', resource='rpctesting')

    def test_3_submethod_clash(self, pane):
        """Internal sub-method clash - verify mixin execution order prevents conflicts"""
        bc = pane.borderContainer(height='400px')
        top = bc.contentPane(region='top', height='80px', padding='10px',
                             background='#f0f0f0', border_bottom='1px solid silver')
        top.div("""Both grouplets alfa and beta define an internal method mainInfo(fb)
                   with different content. When beta is mixed in, its mainInfo overwrites
                   alfa's at class level. However this is not a problem: gr_loadGrouplet
                   mixes in each resource and executes grouplet_main immediately before
                   loading the next one, so all sub-calls resolve to the correct method
                   during execution. Alfa should show 'Built by alfa', beta 'Built by beta'.""")
        bc.contentPane(region='center').grouplet(value='^.submethodtesting',
                                                 resource='submethodtesting')

    def test_4_deferred_submethod_clash(self, pane):
        """Deferred sub-method clash - trying to break the mixin isolation postulate"""
        bc = pane.borderContainer(height='400px')
        top = bc.contentPane(region='top', height='100px', padding='10px',
                             background='#f0f0f0', border_bottom='1px solid silver')
        top.div("""Stress test: both grouplets define a @public_method buildContent that internally
                   calls self.mainInfo() (a non-public method). The call is deferred (triggered by
                   button click), so all mixins have already happened when it fires.
                   getPublicMethod re-mixes the correct resource before executing, which should
                   restore mainInfo to the correct version. Alfa button should show 'deferred alfa',
                   beta button should show 'deferred beta'. If both show 'deferred beta', the
                   postulate is broken.""")
        bc.contentPane(region='center').grouplet(value='^.deferredtesting',
                                                 resource='deferredtesting')

    def test_5_recursive_grouplet(self, pane):
        """Recursive grouplet - a grouplet that loads itself inside a lazy TabContainer"""
        bc = pane.borderContainer(height='400px')
        top = bc.contentPane(region='top', height='80px', padding='10px',
                             background='#f0f0f0', border_bottom='1px solid silver')
        top.div("""A grouplet that contains itself: a TabContainer with a Data tab (two textboxes)
                   and a Nested tab that loads the same resource on a relative datapath.
                   Since TabContainer uses lazy loading, recursion only triggers when the user
                   clicks the Nested tab. Each level creates a new data scope at .nested,
                   allowing infinite nesting: .field1, .nested.field1, .nested.nested.field1...""")
        bc.contentPane(region='center').grouplet(value='^.recursive',
                                                 resource='recursive_grouplet')
