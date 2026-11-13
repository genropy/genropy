# encoding: utf-8

import re
from datetime import datetime

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

    def assignCounter(self,tblobj=None,field=None,record=None):
        self.releaseReplacedSequence(tblobj=tblobj,field=field,record=record)
        if record.get(field):
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
        

    def _recyclingPars(self,tblobj=None,field=None,record=None):
        "the counter pars when the field recycles its numbers by date, else None"
        counter_pars = getattr(tblobj,'counter_%s' %field)(record=record)
        if not counter_pars or not counter_pars.get('recycle'):
            return None
        date_field = counter_pars.get('date_field')
        if not date_field or not record[date_field]:
            return None
        return counter_pars

    def _sequenceNumber(self,counter_pars=None,sequence=None):
        N_start,N_end = self._getBoundaries(**counter_pars)['N']
        digits = sequence[N_start:N_end] if N_start is not None else None
        return int(digits) if digits and digits.isdigit() else None

    def _asDate(self,value):
        return value.date() if isinstance(value,datetime) else value

    def releaseReplacedSequence(self,tblobj=None,field=None,record=None):
        """A draft holding a number (kept, or chosen among the free ones) that a save replaces or
        clears gives it back: without this the number was neither in use nor free, lost.
        Drafts only: a confirmed record may have its number rewritten on purpose (fix_duplicate)"""
        pkey = record.get(tblobj.pkey)
        if not pkey or not tblobj.draftField or not tblobj.isDraft(record):
            return
        counter_pars = self._recyclingPars(tblobj=tblobj,field=field,record=record)
        if not counter_pars:
            return
        date_field = counter_pars['date_field']
        stored = tblobj.query(columns='$%s,$%s' %(field,date_field),where='$%s=:pkey' %tblobj.pkey,pkey=pkey,
                              excludeDraft=False,excludeLogicalDeleted=False,subtable='*').fetch()
        if not stored or not stored[0][field] or stored[0][field]==record.get(field):
            return
        held = dict(record)
        held[field] = stored[0][field]
        held[date_field] = stored[0][date_field] or record[date_field]
        self.releaseCounter(tblobj=tblobj,field=field,record=held)

    def claimSequence(self,tblobj=None,field=None,record=None):
        """A number of its series set in the record before the counter assigns one:
        - a free number (in a hole) is taken out of its hole, which is split around it, dated so that
          the series stays in date order;
        - a number above the counter (a record written again with the number it had, after its
          release took the counter back, or a number forced ahead on purpose) takes the counter up to
          it, also when the series has no counter yet.
        A value in use already (assigned, kept on a draft) or of another series is left alone"""
        counter_pars = self._recyclingPars(tblobj=tblobj,field=field,record=record)
        if not counter_pars:
            return
        sequence = record[field]
        number = self._sequenceNumber(counter_pars=counter_pars,sequence=sequence)
        if number is None or self.formatSequence(tblobj=tblobj,field=field,record=record,counter=number)!=sequence:
            return
        codekey = self.getCounterPkey(tblobj=tblobj,field=field,record=record)
        current = self.record(codekey,ignoreMissing=True).output('record')
        if not current:
            #the first number of its series, set by hand: the series starts at its starting value,
            #then the counter goes up to it like for any number above it
            current = self.newCounterRecord(tblobj=tblobj,field=field,record=record)
            current['counter'] = counter_pars.get('starting_value') or 0
            self.insert(current)
        date = self._asDate(record[counter_pars['date_field']])
        if not self._holeOf(current,number):
            if number > (current['counter'] or 0):
                self._raiseCounter(codekey,number,date,sequence=sequence,counter_pars=counter_pars,
                                   fieldname=tblobj.column(field).name_long or field)
            return
        with self.recordToUpdate(codekey,mode='record') as counter_record:
            hole = self._holeOf(counter_record,number)
            if not hole:
                return
            hole_key,cnt_from,cnt_to,date_from,date_to = hole
            if (date_from and date<date_from) or (date_to and date>date_to):
                raise self.exception('business_logic',
                        msg=self._translate('!![en]%(sequence)s can be dated from %(date_from)s to %(date_to)s') %dict(
                                sequence=sequence,date_from=date_from or '-',date_to=date_to or '-'))
            holes = counter_record['holes']
            holes.popNode(hole_key)
            if cnt_from<number:
                holes.setItem(str(cnt_from),None,cnt_from=cnt_from,cnt_to=number-1,date_from=date_from,date_to=date)
            if number<cnt_to:
                holes.setItem(str(number+1),None,cnt_from=number+1,cnt_to=cnt_to,date_from=date,date_to=date_to)
            holes.sort('#a.cnt_from')
            counter_record['holes'] = holes

    def _raiseCounter(self,codekey,number,date,sequence=None,counter_pars=None,fieldname=None):
        "the counter goes up to number: the numbers between are free, dated by the last used and this one"
        with self.recordToUpdate(codekey,mode='record') as counter_record:
            counter = counter_record['counter'] or 0
            if number <= counter:
                return
            last_used = self._asDate(counter_record['last_used'])
            if date and last_used and date<last_used and not counter_pars.get('date_tolerant'):
                msgTpl = counter_pars.get('message_dateError','!!Incompatible date assigning %(fieldname)s counter')
                raise self.exception('business_logic',msg=self._translate(msgTpl) %dict(
                                            fieldname=self._translate(fieldname),last_used=last_used,sequence=sequence))
            holes = counter_record['holes']
            if isinstance(holes,str):
                holes = Bag(holes)
            holes = holes or Bag()
            if number > counter+1:
                holes.setItem(str(counter+1),None,cnt_from=counter+1,cnt_to=number-1,
                              date_from=last_used,date_to=date)
                holes.sort('#a.cnt_from')
            counter_record['holes'] = holes
            counter_record['counter'] = number
            counter_record['last_used'] = date

    def _holeOf(self,counter_record,number):
        "(key, cnt_from, cnt_to, date_from, date_to) of the hole holding number"
        holes = counter_record['holes'] if counter_record else None
        if isinstance(holes,str):
            holes = Bag(holes)
        if not holes:
            return None
        for hole_key,cnt_from,cnt_to,date_from,date_to in holes.digest('#k,#a.cnt_from,#a.cnt_to,#a.date_from,#a.date_to'):
            if cnt_from<=number<=cnt_to:
                return hole_key,cnt_from,cnt_to,self._asDate(date_from),self._asDate(date_to)
        return None

    def holeSequences(self,tblobj=None,field=None,record=None,limit=500):
        """The free numbers of the record's series, each with the dates it accepts: a list of
        dict(sequence,counter,date_from,date_to), lowest number first"""
        counter_pars = self._recyclingPars(tblobj=tblobj,field=field,record=record)
        if not counter_pars:
            return []
        codekey = self.getCounterPkey(tblobj=tblobj,field=field,record=record)
        counter_record = self.record(codekey,ignoreMissing=True).output('record')
        holes = counter_record['holes'] if counter_record else None
        if isinstance(holes,str):
            holes = Bag(holes)
        result = []
        if not holes:
            return result
        holes.sort('#a.cnt_from')
        for cnt_from,cnt_to,date_from,date_to in holes.digest('#a.cnt_from,#a.cnt_to,#a.date_from,#a.date_to'):
            for number in range(cnt_from,cnt_to+1):
                if len(result)>=limit:
                    return result
                result.append(dict(counter=number,
                                   sequence=self.formatSequence(tblobj=tblobj,field=field,record=record,counter=number),
                                   date_from=self._asDate(date_from),date_to=self._asDate(date_to)))
        return result

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
        #a record going back to draft may keep its numbers: the caller names it in the environment
        if self.db.currentEnv.get('counter_keep') == '%s:%s' %(tblobj.fullname,record.get(tblobj.pkey)):
            return
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
