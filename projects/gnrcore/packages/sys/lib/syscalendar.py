class SysCalendar(object):
    def __init__(self,column=None,name=None,name_long=None,caption_field=None,relation_name=None):
       self.column = column
       #self.column = column
       #self.tblNode = self.column.parentNode
       #self.src =  self.tblNode.parent.parent
       #relation_name = relation_name or f'{self.tblNode.name}s'
       #self.relation = self.column.relation('sys.calendar.date',relation_name)
       #caption_field = caption_field or self.tblNode.attributes.get('caption_field')
       #tblcalendar = self.src.package('sys').table('calendar')
       #tblcalendar.attributes[]

    def addTotalizer(self,**kwargs):
        print('addTotalizer',**kwargs)