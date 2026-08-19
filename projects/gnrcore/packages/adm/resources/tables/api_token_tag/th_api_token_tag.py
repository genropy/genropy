# encoding: utf-8

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):
    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('tag_id', width='20em')
        r.fieldcell('@tag_id.note', width='100%')

    def th_order(self):
        return 'tag_id'

    def th_query(self):
        return dict(column='tag_id', op='contains', val='')


class ViewFromApiToken(BaseComponent):
    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('tag_id', width='20em', edit=True)
        r.fieldcell('@tag_id.note', width='100%')

    def th_order(self):
        return 'tag_id'
