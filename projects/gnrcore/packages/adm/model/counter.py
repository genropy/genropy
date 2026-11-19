# encoding: utf-8

import re
from datetime import datetime, timezone

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method

BASE = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('counter', pkey='codekey',
                        pkey_columns='pkg,tbl,code,fld,period',
                        name_long='!!Counter',multi_tenant=True)
        self.sysFields(tbl, id=False, ins=True, upd=True)
        tbl.column('codekey', size=':80', readOnly='y', name_long='!!Codekey', indexed='y')
        tbl.column('code', size=':12', readOnly='y', name_long='!!Code')
        tbl.column('pkg', size=':12', readOnly='y', name_long='!!Package')
        tbl.column('tbl', size=':30', readOnly='y', name_long='!!Table')
        tbl.column('fld', size=':30', readOnly='y', name_long='!!Counter Field')
        tbl.column('period',size=':10',name_long='!!Period',indexed='y')
        tbl.column('counter', 'L', name_long='!!Counter')
        tbl.column('last_used', 'D', name_long='!!Last used')
        tbl.column('holes', 'X', name_long='!!Holes')
        tbl.column('errors','X', name_long='!!Errors')
        

    def getFieldSequences(self,tblobj,field=None):
        pars = getattr(tblobj,'counter_%s' %field)()
        N_start,N_end = self._getBoundaries(**pars)['N']
        if N_start is None:
            return
        placeholder = '*'* (N_end-N_start)
        #columns="overlay($%s placing '%s' from %i for %i) as dc" %(field,placeholder,N_start+1,len(placeholder))
        columns = "substr($%(fld)s, 1,%(nstart)i) || '%(placeholder)s' || substr($%(fld)s,%(lst)i) AS dc" %dict(fld=field,nstart=N_start,placeholder=placeholder,lst=N_start+len(placeholder)+1)
        dc = tblobj.query(columns = columns,subtable='*',
                            distinct=True,where=" NOT ($%s IS NULL OR $%s='') " %(field,field)).fetch()
        return sorted([r['dc'] for r in dc if r['dc']])


    def initializeApplicationSequences(self,thermo_wrapper=None):
        packages = thermo_wrapper(list(self.db.packages.values()),message=lambda p,n,m: 'Sequences for package %s' %p.name) if thermo_wrapper else list(self.db.packages.values())
        for pkg in packages:
            self.initializePackageSequences(pkg,thermo_wrapper=thermo_wrapper)

    def initializePackageSequences(self,pkgobj,thermo_wrapper=None):
        tables = pkgobj['tables']
        if not tables:
            return
        tables = thermo_wrapper(tables.values(),message=lambda t,n,m: 'Sequences for table %s' %t.name,line_code='tbl') if thermo_wrapper else tables.values()
        for tblobj in tables:
            self.initializeTableSequences(tblobj.dbtable,thermo_wrapper=thermo_wrapper)

    def initializeTableSequences(self,tblobj,thermo_wrapper=None):
        counter_fields = thermo_wrapper(tblobj.counterColumns(),message=lambda f,n,m: 'Sequences for field %s' %f,line_code='field') if thermo_wrapper else tblobj.counterColumns()
        for field in counter_fields:
            sequences = self.getFieldSequences(tblobj,field=field)
            self.alignSequences(tblobj,field=field,to_align=sequences,thermo_wrapper=thermo_wrapper)

    def alignSequences(self,tblobj,field=None,to_align=None,fix_duplicate=None,thermo_wrapper=None):
        if isinstance(to_align,str):
            to_align = to_align.split(',')
        pars = getattr(tblobj,'counter_%s' %field)()
        boundaries = self._getBoundaries(**pars)
        if boundaries['N'][0] is not None:
            to_align = thermo_wrapper(to_align,line_code='sequences',message='Sequence') if thermo_wrapper else to_align
            for sq in to_align:
                self._alignOneSequence(tblobj,sq=sq,field=field,boundaries=boundaries,fix_duplicate=fix_duplicate,**pars)
#
    @public_method
    def alignCounter(self,pkey=None):
        counter_record = self.record(pkey).output('dict')
        tblobj = self.db.table('%(pkg)s.%(tbl)s' %counter_record)
        field = counter_record['fld']
        counter_pars = getattr(tblobj,'counter_%s' %field)()
        boundaries = self._getBoundaries(**counter_pars)
        sq = counter_pars['format']
        sq = sq.replace('$K',counter_record['code'])
        sq = sq.replace('$N','N').replace('$Y','Y').replace('$M','M').replace('$D','')
        sq = list(sq)
        N_start,N_end = boundaries['N']
        sq[N_start:N_end] = list('*'*(N_end-N_start))
        period = counter_record['period']
        if period:
            period_year = counter_record['period'][0:4]
            period_month = counter_record['period'][4:6]
            period_day = counter_record['period'][6:8]
            if period_year:
                period_year = list(period_year)
                Y_start,Y_end = boundaries['Y']
                if Y_end-Y_start<4:
                    sq[Y_start:Y_end] = period_year[2:]
                else:
                    sq[Y_start:Y_end] = period_year
            if period_month:
                sq[boundaries['M'][0]:boundaries['M'][1]] = list(period_month)
            if period_day:
                sq[boundaries['D'][0]:boundaries['D'][1]] = list(period_day)
        self._alignOneSequence(tblobj,field=field,sq=''.join(sq),boundaries=boundaries,**counter_pars)
        self.db.commit()

    def _alignOneSequence(self,tblobj,field=None,sq=None,boundaries=None,date_field=None,format=None,code=None,fix_duplicate=None,**kwargs):
        #sq example  XY/2010-****  $K/$YYYY-$NNNN
        period = {}
        for k in 'YMD':
            b = boundaries[k]
            period[k] = sq[b[0]:b[1]] if b[0] is not None else ''
        kbound = boundaries['K']
        pars_code = code
        code = sq[kbound[0]:kbound[1]] if kbound[0] is not None else None
        N_start,N_end = boundaries['N']
        placeholder = '*'* (N_end-N_start)
        delta = len(placeholder)
        columns='$%s,substr($%s ,%i, %i) AS cnt' %(field,field,N_start+1,delta)
        if date_field:
            columns='%s,$%s' %(columns,date_field)
        dccol = "substr($%(fld)s, 1,%(nstart)i) || '%(placeholder)s' || substr($%(fld)s,%(lst)i)" %dict(fld=field,nstart=N_start,placeholder=placeholder,lst=N_start+delta+1)
        l = tblobj.query(columns=columns ,
                        where="%s = :sq" %dccol,
                        sq=sq,excludeDraft=False,subtable='*',
                        excludeLogicalDeleted=False).fetch()
        i = 0
        errors = Bag()
        holes = Bag()
        prev_date = None
        prevcnt = None
        cnt = 0
        l = sorted(l,key=lambda r: r['cnt'])   
        if l and date_field and period['Y'] and len(period['Y']) <4:
            period['Y'] = str(l[0][date_field].year)
        if period:
            period = '%(Y)s%(M)s%(D)s' %period
        
        period =period or None
        for r in l:
            i+=1
            if not r['cnt'].isdigit():
                continue
            cnt = int(r['cnt'])
            if date_field:
                rdate = r[date_field]
                if not rdate:
                    print('missing date')
                    errors.setItem('missing_date.%i' %i,None,cnt=cnt)
                    continue
                if prev_date and prev_date>rdate:
                    err = dict(record_id=r['pkey'])
                    err['cnt'] = cnt
                    err['cnt_date'] = rdate
                    err['prev_date'] = prev_date
                    errors.setItem('wrongOrder.%i' %i,None, **err)
                #prev_date = rdate
            if prevcnt and prevcnt==cnt:
                if r[field].endswith('_'):
                    pass
                elif fix_duplicate:
                    with tblobj.recordToUpdate(pkey=r['pkey']) as record_to_fix:
                        record_to_fix[field] = '%s_' %r[field]
                else:
                    err = dict(cnt=cnt)
                    errors.setItem('duplicates.%i' %i,None,**err)
                i-=1
            elif cnt>i:
                h = dict(record_id=r['pkey'],date_from=None,date_to=None)
                h['cnt_from'] = i
                h['cnt_to'] = cnt-1
                if date_field:
                    h['date_from'] = prev_date
                    h['date_to'] = rdate
                holes.setItem(str(i),None, **h)
                i = cnt
            prevcnt = cnt
            if date_field:
                prev_date = rdate
        errors=errors or None
        holes=holes or None
        record = dict(pkg=tblobj.pkg.name,tbl=tblobj.name,fld=field,
                        period=period,code=code or pars_code,counter=cnt,
                        last_used=prev_date,holes=holes,errors=errors)
        codekey = self.newPkeyValue(record)
        with self.recordToUpdate(codekey=codekey,insertMissing=True) as counter_record:
            counter_record.update(record)

    def _getBoundaries(self,format=None,code=None,**kwargs):
        format = format.replace('$K','$%s' %('K'*len(code)))
        result = dict()
        for k in 'YMDKN':
            f = format
            for n in 'YMDKN'.replace(k,''):
                f = f.replace('$%s' %n,n)
            s = re.search("(\\$%s+)" %k,f)
            s = s.span() if s else None
            result[k] = (s[0],s[1]-1) if s else (None,None)
        return result

    def getCounterPkey(self,tblobj=None,field=None,record=None):
        return self.pkeyValue(self.newCounterRecord(tblobj=tblobj,field=field,record=record))

    def newCounterRecord(self,tblobj=None,field=None,record=None):
        counter_pars = getattr(tblobj,'counter_%s' %field)(record=record)
        counter_record = Bag(code=counter_pars['code'],pkg=tblobj.pkg.name,tbl=tblobj.name,fld=field)
        date_field = counter_pars.get('date_field')
        format = counter_pars.get('format','')
        if date_field:
            if not record[date_field]:
                raise self.exception('business_logic', msg=self._translate('!!Missing %s. Mandatory for counter %s') %(date_field,field))
            ymd = self.getYmd(record[date_field])
            period = []
            if '$Y' in format:
                period.append(ymd[0])
            if '$M' in format:
                period.append(ymd[1])
            if '$D' in format:
                period.append(ymd[2])
            if period:
                counter_record['period'] = ''.join(period)
        return counter_record

    def _insertCounterRow(self,codekey,counter_record,counter=None):
        # two first claims of a series may insert it together: a failed insert would roll
        # back the whole save, so the second does nothing and the row of the first is used
        row = dict(counter_record.items())
        tsType = self.column('__ins_ts').dtype
        now = datetime.now(timezone.utc) if tsType == 'DHZ' else datetime.now()
        row.update(codekey=codekey,counter=counter,__ins_ts=now,__mod_ts=now)
        sqlnames = self.model.sqlnamemapper
        sql = 'INSERT INTO %s(%s) VALUES (%s) ON CONFLICT (%s) DO NOTHING;' % (
            self.model.sqlfullname,','.join(sqlnames[k] for k in row),
            ','.join(':%s' % k for k in row),sqlnames['codekey'])
        self.db.execute(sql,row,dbtable=self.fullname)

    def assignCounter(self,tblobj=None,field=None,record=None,old_record=None):
        """Assign, claim or change the number of record, as sys.counter.assignCounter:
        a number changed or cleared on update gives the old one back (recycling counter), a number
        set in the record (insert, or changed on update) is claimed, a record without number gets
        the next one"""
        value = record.get(field)
        old_value = old_record.get(field) if old_record else None
        if old_value and old_value!=value:
            self.releaseReplacedSequence(tblobj=tblobj,field=field,old_record=old_record)
        if value:
            if old_record is None or value!=old_value:
                self.claimSequence(tblobj=tblobj,field=field,record=record)
            return
        counter_pars = getattr(tblobj,'counter_%s' %field)(record=record)
        if not counter_pars or (tblobj.isDraft(record) and not counter_pars.get('assignIfDraft')):
            return
        #if not 'unique' in tblobj.column(field).attributes:
        #    print 'MISSING UNIQUE ATTRIBUTE IN FIELD %s IN TABLE %s' %(field,tblobj.fullname)
        record[field] = self.getSequence(tblobj=tblobj,field=field,record=record,update=True)
        if counter_pars.get('onAssigned'):
            counter_pars['onAssigned'](record=record,field=field)
        

    def guessNextSequence(self,tblobj=None,field=None,record=None):
        counter,counterInfo = self.getCounter(tblobj=tblobj,field=field,record=record,update=False)
        sequence = self.formatSequence(tblobj=tblobj,field=field,record=record,counter=counter)
        return sequence,counterInfo

    def getSequence(self,tblobj=None,field=None,record=None,update=False):
        counter,counterInfo = self.getCounter(tblobj=tblobj,field=field,record=record,update=update)
        return self.formatSequence(tblobj=tblobj,field=field,record=record,counter=counter)

    def convertCustomBase(self,counter,base):
        result = []
        b = len(base)
        while counter !=0:
            r = counter % b
            counter = int(counter/b)
            result.append(base[r])
        result.reverse()
        return ''.join(result)

    def formatSequence(self,tblobj=None,field=None,record=None, counter=None):
        counter_pars = getattr(tblobj,'counter_%s' %field)(record=record)
        base = counter_pars.get('base')
        if base:
            if base and isinstance(base,int):
                base = BASE[0:base]
            counter = self.convertCustomBase(counter,base)
        else:
            counter = str(counter)
        output = counter_pars['format']
        code = counter_pars['code']
        x = '$N%s' % output.split('$N')[1]
        output = output.replace(x, counter.zfill(len(x) - 1))
        output = output.replace('$K', code)        
        date_field = counter_pars.get('date_field')
        date = record[date_field] if date_field else None
        if date_field and not date:
            raise self.exception('business_logic',msg=self._translate('!!Missing %s. Mandatory for counter %s') %(date_field,field))
        if date:
            ymd = self.getYmd(date)
            output = output.replace('$YYYY', ymd[0])
            output = output.replace('$YY', ymd[0][2:])
            output = output.replace('$MM', ymd[1])
            output = output.replace('$DD', ymd[2])
        return output

    def getCounter(self,tblobj=None,field=None,record=None,update=False):
        counter_pars = getattr(tblobj,'counter_%s' %field)(record=record)
        if counter_pars.get('rootstore'):
            with self.db.tempEnv(storename=self.db.rootstore):
                return self._getCounter(tblobj=tblobj,field=field,record=record,update=update,counter_pars=counter_pars)
        return self._getCounter(tblobj=tblobj,field=field,record=record,update=update,counter_pars=counter_pars)

    def _recycleCounter(self,holes,date,counterInfo):
        holes.sort('#a.cnt_from')
        for hole_key,cnt_from,cnt_to,date_from,date_to in holes.digest('#k,#a.cnt_from,#a.cnt_to,#a.date_from,#a.date_to'):
            if isinstance(date_from,datetime):
                date_from = date_from.date()
            if isinstance(date_to,datetime):
                date_to = date_to.date()
            if (date_from is None or date >= date_from) and (date_to is None or date<=date_to):
                counter = cnt_from
                cnt_from += 1
                if cnt_from>cnt_to:
                    holes.pop(hole_key)
                else:
                    #the numbers left in the hole come after this one: they cannot take an earlier date
                    if date and (date_from is None or date>date_from):
                        date_from = date
                    holes.setAttr(hole_key,dict(cnt_from=cnt_from,date_from=date_from))
                counterInfo.update(recycled=True,cnt=counter)
                break
        return counterInfo

    def _getCounter(self,tblobj,field=None,record=None,update=None,counter_pars=None):
        counterInfo = dict()
        codekey = self.getCounterPkey(tblobj=tblobj,field=field,record=record)
        date_field = counter_pars.get('date_field')
        recycle = counter_pars.get('recycle') if date_field else False
        date = None
        if date_field:
            date = record[date_field]
            if not date:
                raise self.exception('business_logic', msg=self._translate('!!Missing date %s for counter %s') %(date_field,field))
            if isinstance(date,datetime):
                date = date.date()
        counter_record = self.record(codekey,ignoreMissing=True,for_update=update).output('record')
        counter_record = counter_record or self.newCounterRecord(tblobj=tblobj,field=field,record=record)
        last_used = counter_record['last_used']
        counter = None
        holes = counter_record['holes']
        if holes and recycle:
            counterInfo = self._recycleCounter(holes,date,counterInfo)
            counter = counterInfo.get('cnt')
        if counter is None:
            counter = (counter_record['counter'] or counter_pars.get('starting_value') or  0) + 1
            counter_record['last_used'] = date
            counter_record['counter'] = counter
            if date and  last_used and date< last_used:
                msgTpl = counter_pars.get('message_dateError','!!Incompatible date assigning %(fieldname)s counter')
                fieldname = self._translate(tblobj.column(field).name_long or field)
                if not counter_pars.get('date_tolerant'):
                    raise self.exception('business_logic',msg=self._translate(msgTpl) %dict(fieldname=fieldname,last_used=last_used))
        if update:
            if counter_record['codekey']:
                oldrec = dict(counter_record)
                self.update(counter_record,oldrec)
            else:
                self.insert(counter_record)
            counterInfo['codekey'] = counter_record['codekey']
        return counter,counterInfo

    def _translate(self, txt):
        return self.db.localizer.translate(txt, language=self.db.currentEnv.get('locale'))

    def releaseCounter(self,tblobj=None,field=None,record=None):
        codekey = self.getCounterPkey(tblobj=tblobj,field=field,record=record)
        counter_pars = getattr(tblobj,'counter_%s' %field)(record=record)
        date_field = counter_pars.get('date_field')
        N_start,N_end = self._getBoundaries(**counter_pars)['N']
        date = record[date_field] if date_field else None
        if date_field and not date:
            raise self.exception('business_logic',msg=self._translate('!!Missing %s. Mandatory for counter %s') %(date_field,field))
        with self.recordToUpdate(codekey,mode='record',ignoreMissing=True) as counter_record:
            if not counter_record:
                return
            sequence = record[field]
            record[field] = None
            releasing_counter = int(sequence[N_start:N_end])
            series = SequenceSeries(tblobj, field=field, date_field=date_field, sequence=sequence,
                                    N_start=N_start, N_end=N_end, exclude_pkey=record.get(tblobj.pkey))
            holes = counter_record['holes'] or Bag()
            counter_record['holes'] = holes
            #every number between the nearest numbers in use (drafts holding one included) is free:
            #the released one, the holes next to it and numbers lost without a hole. They make one
            #hole, dated by those two numbers
            before = series.nearest(releasing_counter, below=True)
            after = series.nearest(releasing_counter, below=False)
            cnt_from = (before[0] if before else (counter_pars.get('starting_value') or 0)) + 1
            if after is None:
                #nothing in use above: the tail of the series. The counter goes back to the highest
                #number in use; holes above it would be handed out again by counter+1, so they go
                counter_record['counter'], counter_record['last_used'] = (cnt_from - 1, before[1] if before else None)
                for hole_key,h_cnt_to in holes.digest('#k,#a.cnt_to'):
                    if h_cnt_to >= cnt_from:
                        holes.popNode(hole_key)
            else:
                #the counter can never stay below a number in use: a counter left behind
                #(e.g. by an earlier release) would hand out numbers that already exist
                highest = series.highest()
                if highest[0] > (counter_record['counter'] or 0):
                    counter_record['counter'], counter_record['last_used'] = highest
                cnt_to = after[0] - 1
                for hole_key,h_cnt_from,h_cnt_to in holes.digest('#k,#a.cnt_from,#a.cnt_to'):
                    if h_cnt_from <= cnt_to and h_cnt_to >= cnt_from:
                        holes.popNode(hole_key)
                holes.setItem(str(cnt_from), None, cnt_from=cnt_from,
                          cnt_to=cnt_to, date_from=before[1] if before else None, date_to=after[1])
            holes.sort('#a.cnt_from')
        if counter_pars.get('onReleased'):
            counter_pars['onReleased'](record=record,field=field)

    # ------------------------------------------------------------------
    # a number set by hand, and the counter API of gnrdbo (TableBase.*CounterColumn)
    # ------------------------------------------------------------------

    def _asDate(self,value):
        return value.date() if isinstance(value,datetime) else value

    def _sequenceNumber(self,counter_pars=None,sequence=None):
        "the number of a formatted sequence, or None when the text does not hold one"
        N_start,N_end = self._getBoundaries(**counter_pars)['N']
        if N_start is None or not sequence:
            return None
        digits = sequence[N_start:N_end]
        base = counter_pars.get('base')
        if base:
            base = BASE[0:base] if isinstance(base,int) else base
            if not digits or any(c not in base for c in digits):
                return None
            number = 0
            for c in digits:
                number = number*len(base)+base.index(c)
            return number
        return int(digits) if digits.isdigit() else None

    def _series(self,tblobj=None,field=None,counter_pars=None,sequence=None,exclude_pkey=None):
        N_start,N_end = self._getBoundaries(**counter_pars)['N']
        return SequenceSeries(tblobj,field=field,date_field=counter_pars.get('date_field'),sequence=sequence,
                              N_start=N_start,N_end=N_end,exclude_pkey=exclude_pkey)

    def _holes(self,counter_record):
        holes = counter_record['holes'] if counter_record else None
        if isinstance(holes,str):
            holes = Bag(holes)
        return holes or Bag()

    def claimSequence(self,tblobj=None,field=None,record=None):
        """A number of its series set in the record before the counter assigns one:
        - held by another record of the table: refused;
        - free (in a hole of a recycling counter): it leaves its hole, which is split around it,
          inside the dates of the hole;
        - above the counter: the counter goes up to it; for a recycling counter the numbers between,
          down to the nearest one in use, are free;
        - below the counter and in no hole: a number lost, or given to this very record earlier in the
          same save, taken as it is.
        Whether a number is in use is read from the table, never inferred from the counter: a number
        below the counter and in no hole is not necessarily in use (#1904). A value that is not a
        number of the series is left alone"""
        counter_pars = getattr(tblobj,'counter_%s' %field)(record=record)
        if not counter_pars:
            return
        date_field = counter_pars.get('date_field')
        if date_field and not record[date_field]:
            return
        sequence = record[field]
        number = self._sequenceNumber(counter_pars=counter_pars,sequence=sequence)
        if number is None or self.formatSequence(tblobj=tblobj,field=field,record=record,counter=number)!=sequence:
            return
        series = self._series(tblobj=tblobj,field=field,counter_pars=counter_pars,sequence=sequence,
                              exclude_pkey=record.get(tblobj.pkey))
        codekey = self.getCounterPkey(tblobj=tblobj,field=field,record=record)
        if not self.existsRecord(codekey):
            self._insertCounterRow(codekey,self.newCounterRecord(tblobj=tblobj,field=field,record=record),
                                   counter=counter_pars.get('starting_value') or 0)
        date = self._asDate(record[date_field]) if date_field else None
        with self.recordToUpdate(codekey,mode='record') as counter_record:
            if series.holds(sequence):
                raise self.exception('business_logic',
                        msg=self._translate('!![en]%(sequence)s is already in use') %dict(sequence=sequence))
            hole = self._holeOf(counter_record,number) if counter_pars.get('recycle') and date_field else None
            if hole:
                self._takeFromHole(counter_record,hole,number,date,sequence=sequence,counter_pars=counter_pars)
            elif number > (counter_record['counter'] or 0):
                self._raiseCounter(counter_record,number,date,tblobj=tblobj,field=field,
                                   counter_pars=counter_pars,series=series)

    def _takeFromHole(self,counter_record,hole,number,date,sequence=None,counter_pars=None):
        hole_key,cnt_from,cnt_to,date_from,date_to = hole
        if date and not counter_pars.get('date_tolerant') and \
                ((date_from and date<date_from) or (date_to and date>date_to)):
            raise self.exception('business_logic',
                    msg=self._translate('!![en]%(sequence)s can be dated from %(date_from)s to %(date_to)s') %dict(
                            sequence=sequence,date_from=date_from or '-',date_to=date_to or '-'))
        holes = self._holes(counter_record)
        holes.popNode(hole_key)
        if cnt_from<number:
            holes.setItem(str(cnt_from),None,cnt_from=cnt_from,cnt_to=number-1,date_from=date_from,date_to=date or date_to)
        if number<cnt_to:
            holes.setItem(str(number+1),None,cnt_from=number+1,cnt_to=cnt_to,date_from=date or date_from,date_to=date_to)
        holes.sort('#a.cnt_from')
        counter_record['holes'] = holes

    def _raiseCounter(self,counter_record,number,date,tblobj=None,field=None,counter_pars=None,series=None):
        """the locked counter_record goes up to number. For a recycling counter the numbers between,
        down to the nearest one in use, are free, dated by that number (or the last used) and this one"""
        counter = counter_record['counter'] or 0
        floor,floor_date = counter,self._asDate(counter_record['last_used'])
        recycle = counter_pars.get('recycle') and counter_pars.get('date_field')
        if recycle:
            below = series.nearest(number,below=True)
            if below and below[0] > counter:
                floor,floor_date = below
        if date and floor_date and date<floor_date and not counter_pars.get('date_tolerant'):
            msgTpl = counter_pars.get('message_dateError','!!Incompatible date assigning %(fieldname)s counter')
            fieldname = self._translate(tblobj.column(field).name_long or field)
            raise self.exception('business_logic',msg=self._translate(msgTpl) %dict(fieldname=fieldname,last_used=floor_date))
        if recycle and number > floor+1:
            holes = self._holes(counter_record)
            holes.setItem(str(floor+1),None,cnt_from=floor+1,cnt_to=number-1,date_from=floor_date,date_to=date)
            holes.sort('#a.cnt_from')
            counter_record['holes'] = holes
        counter_record['counter'] = number
        counter_record['last_used'] = date

    def _holeOf(self,counter_record,number):
        "(key, cnt_from, cnt_to, date_from, date_to) of the hole holding number"
        for hole_key,cnt_from,cnt_to,date_from,date_to in self._holes(counter_record).digest('#k,#a.cnt_from,#a.cnt_to,#a.date_from,#a.date_to'):
            if cnt_from<=number<=cnt_to:
                return hole_key,cnt_from,cnt_to,self._asDate(date_from),self._asDate(date_to)
        return None

    def releaseReplacedSequence(self,tblobj=None,field=None,old_record=None):
        """The number of old_record, changed or cleared on update, goes back to the free numbers of a
        recycling counter, as with sys.counter. Not while another record still holds it"""
        counter_pars = getattr(tblobj,'counter_%s' %field)(record=old_record)
        date_field = counter_pars.get('date_field') if counter_pars else None
        if not counter_pars or not counter_pars.get('recycle') or not date_field or not old_record.get(date_field):
            return
        sequence = old_record[field]
        if self._sequenceNumber(counter_pars=counter_pars,sequence=sequence) is None:
            return
        series = self._series(tblobj=tblobj,field=field,counter_pars=counter_pars,sequence=sequence,
                              exclude_pkey=old_record.get(tblobj.pkey))
        if series.holds(sequence):
            return
        self.releaseCounter(tblobj=tblobj,field=field,record=dict(old_record))

    def realignCounter(self,tblobj=None,field=None,record=None,floor=None):
        """Forget the counter of the series of record (every series of field without record) and
        rebuild it from the numbers in the table: the counter on the highest one, the holes between
        them. floor, with record: a number the counter must not stay below (numbers in use outside
        the table)"""
        if record is None:
            self.sql_deleteSelection(where='$pkg=:pkg AND $tbl=:tbl AND $fld=:fld',
                                     pkg=tblobj.pkg.name,tbl=tblobj.name,fld=field)
            self.alignSequences(tblobj,field=field,to_align=self.getFieldSequences(tblobj,field=field) or [])
            return
        counter_pars = getattr(tblobj,'counter_%s' %field)(record=record)
        if not counter_pars:
            return
        codekey = self.getCounterPkey(tblobj=tblobj,field=field,record=record)
        self.sql_deleteSelection(where='$codekey=:codekey',codekey=codekey)
        boundaries = self._getBoundaries(**counter_pars)
        N_start,N_end = boundaries['N']
        sample = self.formatSequence(tblobj=tblobj,field=field,record=record,counter=0)
        if self._series(tblobj=tblobj,field=field,counter_pars=counter_pars,sequence=sample).highest():
            self._alignOneSequence(tblobj,field=field,boundaries=boundaries,
                                   sq='%s%s%s' %(sample[:N_start],'*'*(N_end-N_start),sample[N_end:]),**counter_pars)
        if floor:
            if not self.existsRecord(codekey):
                current = self.newCounterRecord(tblobj=tblobj,field=field,record=record)
                current['counter'] = counter_pars.get('starting_value') or 0
                self.insert(current)
            with self.recordToUpdate(codekey,mode='record') as counter_record:
                if (counter_record['counter'] or 0) < floor:
                    counter_record['counter'] = floor

    def freeSequences(self,tblobj=None,field=None,record=None,limit=500):
        """The free numbers of the series of record, lowest first, each with the dates it accepts:
        a list of dict(number, sequence, date_from, date_to)"""
        counter_pars = getattr(tblobj,'counter_%s' %field)(record=record)
        if not counter_pars or not counter_pars.get('recycle') or not counter_pars.get('date_field'):
            return []
        counter_record = self.record(self.getCounterPkey(tblobj=tblobj,field=field,record=record),
                                     ignoreMissing=True).output('record')
        holes = self._holes(counter_record)
        holes.sort('#a.cnt_from')
        result = []
        for cnt_from,cnt_to,date_from,date_to in holes.digest('#a.cnt_from,#a.cnt_to,#a.date_from,#a.date_to'):
            for number in range(cnt_from,cnt_to+1):
                if len(result)>=limit:
                    return result
                result.append(dict(number=number,
                                   sequence=self.formatSequence(tblobj=tblobj,field=field,record=record,counter=number),
                                   date_from=self._asDate(date_from),date_to=self._asDate(date_to)))
        return result

    def lastSequence(self,tblobj=None,field=None,record=None):
        """dict(number, date) of the last number given in the series of record: its starting value
        and no date when the series has none"""
        counter_pars = getattr(tblobj,'counter_%s' %field)(record=record)
        counter_record = self.record(self.getCounterPkey(tblobj=tblobj,field=field,record=record),
                                     ignoreMissing=True).output('dict') or {}
        return dict(number=counter_record.get('counter') or counter_pars.get('starting_value') or 0,
                    date=self._asDate(counter_record.get('last_used')))

    def getYmd(self, date, phyear=False):
        """Return a tuple (year, month, date) of strings from a date.
        
        :param date: the datetime
        :param phyear: the fiscal year (not yet implemented)"""
        if not date:
            return ('0000', '00', '00')
        if phyear:
            #to be completed
            pass
        else:
            return (str(date.year), str(date.month).zfill(2), str(date.day).zfill(2))


    def getDuplicates(self,table=None,field=None,code=None):
        result = Bag()
        f = self.db.table(table).query(columns='$%s AS fldval, count($%s) AS cnt' %(field,field),
                            where = "$%s LIKE :c AND $%s IS NOT NULL" %(field,field),
                            c='%%%s%%' %code,group_by='$%s' %field,
                          having="count($%s)>1" %field,addPkeyColumn=False,excludeDraft=False).fetch()
        for fldval,cnt in f:
            result[fldval.replace('.','_')] = Bag(dict(fldval=fldval,cnt=cnt))
        return result

    def use_dbstores(self,forced_dbstore=None, env_forced_dbstore=None,**kwargs):
        return True





class SequenceSeries(object):
    """The numbers in use in the series of a sequence: same code and period, any number.
    Drafts and logically deleted records holding a number are in use too, as in alignSequences"""

    LIKE_ESCAPE = '!'

    def __init__(self, tblobj, field=None, date_field=None, sequence=None,
                 N_start=None, N_end=None, exclude_pkey=None):
        self.tblobj = tblobj
        self.field = field
        self.date_field = date_field
        self.prefix = sequence[:N_start]
        self.suffix = sequence[N_end:]
        self.size = N_end - N_start
        self.exclude_pkey = exclude_pkey

    def sequence(self, counter):
        return '%s%s%s' % (self.prefix, str(counter).zfill(self.size), self.suffix)

    def _escaped(self, txt):
        for c in (self.LIKE_ESCAPE, '%', '_'):
            txt = txt.replace(c, self.LIKE_ESCAPE + c)
        return txt

    def _first(self, where=None, order_by=None, **kwargs):
        wlist = ["$%s LIKE :series ESCAPE '%s'" % (self.field, self.LIKE_ESCAPE)]
        if where:
            wlist.append(where % dict(field=self.field))
        if self.exclude_pkey is not None:
            wlist.append('$%s != :exclude_pkey' % self.tblobj.pkey)
        columns = '$%s' % self.field
        if self.date_field:
            columns = '%s,$%s' % (columns, self.date_field)
        rows = self.tblobj.query(columns=columns, where=' AND '.join(wlist),
                                 order_by=order_by % dict(field=self.field), limit=1,
                                 series='%s%s%s' % (self._escaped(self.prefix), '_' * self.size, self._escaped(self.suffix)),
                                 exclude_pkey=self.exclude_pkey,
                                 excludeDraft=False, excludeLogicalDeleted=False, subtable='*',
                                 **kwargs).fetch()
        if not rows:
            return None
        digits = rows[0][self.field][len(self.prefix):len(self.prefix) + self.size]
        if not digits.isdigit():
            return None
        date = rows[0][self.date_field] if self.date_field else None
        if isinstance(date, datetime):
            date = date.date()
        return int(digits), date

    def holds(self, sequence):
        "True when a record other than exclude_pkey holds sequence"
        wlist = ['$%s = :sequence' % self.field]
        if self.exclude_pkey is not None:
            wlist.append('$%s != :exclude_pkey' % self.tblobj.pkey)
        return bool(self.tblobj.query(columns='$%s' % self.field, where=' AND '.join(wlist), limit=1,
                                      sequence=sequence, exclude_pkey=self.exclude_pkey, addPkeyColumn=False,
                                      excludeDraft=False, excludeLogicalDeleted=False, subtable='*').fetch())

    def highest(self):
        "(number, date) of the highest number in use, None if the series is empty"
        return self._first(order_by='$%(field)s DESC')

    def nearest(self, counter, below=True):
        "(number, date) of the number in use nearest to counter, below or above it; None if there is none"
        if below:
            return self._first(where='$%(field)s < :limit_sequence', order_by='$%(field)s DESC',
                               limit_sequence=self.sequence(counter))
        return self._first(where='$%(field)s > :limit_sequence', order_by='$%(field)s',
                           limit_sequence=self.sequence(counter))
