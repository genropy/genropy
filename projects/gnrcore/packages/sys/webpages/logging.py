import logging
#from gnr.core.gnrlog import get_all_handlers
from gnr.core.gnrbag import Bag
from gnr.core.gnrlog import get_gnr_log_configuration
from gnr.core.gnrdecorator import public_method
from gnr.app import pkglog as logger

#possible_handlers = get_all_handlers()


_level_display = {
    "CRITICAL": "magenta",
    "ERROR": "red",
    "WARNING": "yellow",
    "INFO": "green",
    "DEBUG": "blue"
}

possible_levels = logging._nameToLevel.keys()

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/framegrid:frameGrid"
    js_requires = 'logging'
    auth_main = '_DEV_'
    _conf_obj = "logging_conf_bag"
    
    def main(self, root, **kwargs):

        tc = root.tabContainer(height='400px')
        p1 = tc.contentPane(title='Loggers')

        p1.checkbox(value='^logging.all_loggers', label="All loggers")
        
        btn = p1.button("Reload configuration")

        root.data("logging_levels", ",".join(possible_levels))

        #root.data("logging_handlers", ",/,".join([f"{v[0]}:{v[1]}" for v in possible_handlers]))
        
        save_btn = p1.button('Save Configuration')
        save_btn.dataRpc(self.save_logging_conf,
                         logging_conf_bag=f"={self._conf_obj}")
        

        bc = p1.borderContainer(height='100%', width='auto')
        tg = bc.contentPane(region='center').treeGrid(
            autoCollapse=False,
            storepath=self._conf_obj, headers=True,
            connect_ondblclick="logging_tree_editor.ondblclick($1)"
        )

        tg.column('path', header='Logger')
        tg.column('level', size=100, header='Level')
        #tg.column('handlers', size=300, header='Handlers')

        # load the data on tree grid
        rpc = btn.dataRpc(self._conf_obj,
                          self.get_logging_configuration,
                          _lockScreen=True,
                          _onStart=True,
                          all_loggers='^logging.all_loggers'

                          )
        rpc.addCallback("""
        tree.widget.expandAll(tree, true);
        """,
                        tree=tg)

    @public_method
    def get_logging_configuration(self, *args, **kw):
        full_conf = get_gnr_log_configuration(
            all_loggers=kw.get("all_loggers",False)
        )
        result = Bag()
        for path, v in full_conf.items():
            #v['handlers'] = ",".join(v['handlers'])
            result.setItem(path, None, path=path, **v)
        return result

    @public_method
    def save_logging_conf(self, *args, **kw):
        conf = kw.get(self._conf_obj, None)
        if not conf:
            logger.error("Received empty logging configuration")

        self.app.db.application.save_logging_conf(conf, apply=True)

    
                    

