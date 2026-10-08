# -*- coding: utf-8 -*-

"""treeGrid: a hierarchical Bag shown as a tree with columns

The server builds one Bag from `adm.pkginfo` and `adm.tblinfo`: a node per package,
carrying the package row as attributes, and a node per table under it - the table
id is `pkg.table`, so the dot itself nests every table under its package. The
treeGrid shows the node label in the tree column and reads the other columns from
the node attributes; a missing attribute shows the column's `emptyValue`.
"""

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def isDeveloper(self):
        return True

    def test_1_packages(self, root, **kwargs):
        """The tree is built with the page; expand a package to see its tables"""
        root.data('.tree_source', self.getPackageTree())
        root.dataFormula('.tree', 'tree_source.deepCopy()', tree_source='=.tree_source', _onStart=1000)
        bc = root.borderContainer(height='500px')
        left = bc.contentPane(region='left', width='600px', splitter=True)
        bc.contentPane(region='center')
        tree = left.treeGrid(storepath='.tree', headers=True)
        tree.column('label', header='Name', contentCb='return this.label')
        tree.column('pkgid', size=100, header='Package')
        tree.column('description', size=200, emptyValue='-', header='Description')

    def test_2_dynamic(self, root, **kwargs):
        """Start loads the tree from the server and builds the treeGrid client-side, with thirty columns"""
        bc = root.borderContainer(height='600px')
        bc.contentPane(region='top').button('Start', fire='.start')
        center = bc.contentPane(region='center')
        bc.contentPane(region='right', splitter=True, width='100px')
        rpc = bc.dataRpc('.packagedata', self.getPackageTree, cells=True, _fired='^.start', _lockScreen=True)
        rpc.addCallback("""
            treeroot._value.popNode('tr');
            treeroot.freeze();
            var treeGrid = treeroot._('treeGrid','tr',{'storepath':'.packagedata'});
            treeGrid._('column',{field:'label',name:'Name',size:200,contentCb:"return this.label"});
            for (var i=0; i<30; i++){
                treeGrid._('column',{field:'s_'+_F(i,'00'),size:35,name:'C'+_F(i,'00')});
            }
            treeroot.unfreeze();
            return result;
            """, treeroot=center)

    @public_method
    def getPackageTree(self, cells=False):
        b = Bag()
        for row in self.db.table('adm.pkginfo').query(columns='$pkgid,$prj', addPkeyColumn=False,
                                                      order_by='$pkgid').fetch():
            b.setItem(row['pkgid'], Bag(), **dict(row))
        for row in self.db.table('adm.tblinfo').query(columns='$tblid,$pkgid,$description', addPkeyColumn=False,
                                                      order_by='$tblid').fetch():
            attrs = dict(row)
            if cells:
                attrs.update({'s_%02i' % k: k for k in range(30)})
            b.setItem(row['tblid'], None, **attrs)
        return b
