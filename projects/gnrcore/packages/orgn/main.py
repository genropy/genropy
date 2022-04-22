#!/usr/bin/env python
# encoding: utf-8
from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage
class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='Organizer package',sqlschema='orgn',sqlprefix=True,
                    name_short='Organizer', name_long='Organizer', name_full='Organizer package')
                    
    def config_db(self, pkg):
        pass
        
    def sidebarPlugins(self):
        if self.getPreference('organizer_enabled'):
            return 'organizer','frameplugin_organizer'

    def onBuildingDbobj(self):
        config_entities = self.db.application.packages['orgn'].content['entities']
        for tbl in ('annotation','cal_event'):
            tbl_mixins = self.db.model.mixins['tbl.orgn.{tblname}'.format(tblname=tbl)]
            tbl_src = self.db.model.src['packages.orgn.tables.{tblname}'.format(tblname=tbl)]
            for m in [k for k in dir(tbl_mixins) if k.startswith('orgn_')]:
                pars = getattr(tbl_mixins,m)()
                pars['code'] = m[5:]
                self.configureEntity(tbl_src,**pars)
            if not config_entities:
                continue
            for k,pars in config_entities.digest('#k,#a'):
                pars['code'] = k
                self.configureEntity(tbl_src,**pars)


    def configureEntity(self,src,code=None,caption=None,tbl=None,pivot_date=None,**kwargs):
        pkg,tblname = tbl.split('.')
        tblsrc = self.db.model.src['packages.{pkg}.tables.{tblname}'.format(pkg=pkg,tblname=tblname)]
        tblattrs = tblsrc.attributes
        pkey = tblattrs.get('pkey')
        pkeycolAttrs = tblsrc.column(pkey).getAttr()
        rel = '{pkg}.{tblname}.{pkey}'.format(pkg=pkg,tblname=tblname,pkey=pkey)
        fkey = 'le_{tblname}_{pkey}'.format(tblname=tblname,pkey=pkey)
        curr_columns = src['columns']
        caption = caption or tblattrs['name_long']
        entity = '{code}:{caption}'.format(code=code,caption=caption)
        if caption.startswith('!!'):
            caption = '[{caption}]'.format(caption=caption)
        linked_attrs = {'linked_{k}'.format(k=k) :v for k,v in kwargs.items() if v is not None}
        if fkey in curr_columns:
            colsrc = src['columns'][fkey]
            related_column = colsrc.getAttr('relation')['related_column']
            rpkg,rtbl,rpkey = related_column.split('.')
            if '{rpkg}.{rtbl}'.format(rpkg=rpkg,rtbl=rtbl) == tbl:
                colattr = colsrc.attributes
                linked_entities = colattr['linked_entity'].split(',')
                linked_entities.append(entity)
                colattr['linked_entity'] = ','.join(linked_entities)
                colattr.update(**kwargs)
                return
            else:
                fkey = 'le_{}'.format(tbl.replace('.','_'))
        relation_name = '{}s'.format(src.attributes['fullname'].split('.')[1])
        src.column(fkey, dtype=pkeycolAttrs.get('dtype'),_sysfield=True,group='_',
                    name_long=tblattrs.get('name_long'),
                    size=pkeycolAttrs.get('size'),linked_entity=entity,
                    pivot_date=pivot_date,**linked_attrs).relation(rel,relation_name=relation_name,mode='foreignKey',onDelete='cascade')


class Table(GnrDboTable):
    pass
