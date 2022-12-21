# encoding: utf-8
try:
    from holidays import country_holidays
except:
    country_holidays = False

class CalendarConnector(object):
    def __init__(self,tblobj,linkedTblSrc,column=None,name=None,name_long=None,caption_field=None):
        self.tblobj = tblobj
        self.linkedTblSrc = linkedTblSrc
        self.linkedTblAttr = linkedTblSrc.attributes
        column = linkedTblSrc.column(column)
        self.linkedColAttr = column.attributes
        self.linkedTableFullname = self.linkedTblAttr['fullname']
        self.linkedColName = column.parentNode.label
        caption_field = caption_field or self.linkedTblAttr.get('caption_field')
        tablecode = self.linkedTableFullname.replace(".","_")
        name = name or  f'{tablecode}_{self.linkedColName}'
        name_long = name_long or self.linkedTblAttr.get('name_plural') or self.linkedTblAttr.get('name_long')
        column.relation('sys.calendar.date',relation_name=name,
                        many_name=name_long,
                        one_name='!![it]SysCaneldar')
    

        self.tblobj.src.aliasColumn(f'relcaption_{tablecode}',f'@{name}.{caption_field}',
                    name_long=f'{name_long} caption')
    
    def aggregate(self,column=None,aggr=None,condition=None,dtype='N',**kwargs):
        colname = f'{self.linkedTableFullname.replace(".","_")}_{column}_{aggr.lower()}'
        where = f'${self.linkedColName}=#THIS.date'
        if condition:
            where = f'({where}) AND ({condition})'
        self.tblobj.src.formulaColumn(colname,
            select=dict(table=self.linkedTableFullname,columns=f'{aggr}(${column})',where =where),
            dtype=dtype,**kwargs)

class Table(object):
    def config_db(self,pkg):
        tbl=pkg.table('calendar', pkey='date', name_long='!![en]Calendar', name_plural='!![en]Calendar Days',caption_field='date')
        tbl.column('date', dtype='D', name_long='!![en]Date',indexed=True,unique=True)        
        tbl.formulaColumn('year_month',"to_char('YYYY-MM')",dtype='L', name_long='!![en]Month')        
        
        tbl.pyColumn('holiday',name_long='!![en]Holiday',_addClass='holiday')
        
        tbl.formulaColumn('dow','EXTRACT(ISODOW FROM $date)',dtype='L')
        tbl.formulaColumn('weekend',"""$dow>5""",dtype='B',_addClass='weekend')

        tbl.pyColumn('day_cal',dtype='A',group='*',py_method='templateColumn', 
                template_name='day_cal',template_localized=True)

    def onDbUpgrade_createDays(self):
        if self.query(limit=1).count():
            return
        sql = """
            INSERT INTO sys.sys_calendar
            SELECT generate_series(date'1900-01-01', '2100-01-01', '1 day') AS date;
        """
        self.db.execute(sql)

    def pyColumn_holiday(self,record=None,field=None):
        if not country_holidays:
            return None
        currentEnv = self.db.currentEnv
        locale = currentEnv.get('locale')
        if not locale:
            locale = self.db.application.locale
        sep = '_' if '_' in locale else '-'
        country = locale.split(sep)[1].upper()
        holiday_dict = currentEnv.get(f'{country}_holidays') 
        if not holiday_dict:
            holiday_dict = country_holidays(country)
            currentEnv[f'{country}_holidays'] = holiday_dict
        return holiday_dict.get(record['date'])

    
    def calendarConnector(self,linkedTblSrc,column,**kwargs):
        return CalendarConnector(tblobj=self,linkedTblSrc=linkedTblSrc,column=column,**kwargs)


