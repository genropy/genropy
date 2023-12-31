COVER_OPTS=--cov-report=html

tests:
	py.test *.py $(COVER_OPTS) --cov=gnr.core

bag:
	py.test gnrbag_test.py $(COVER_OPTS) --cov=gnr.core.gnrbag --cov=gnr.core.gnrbagxml

date:
	py.test	gnrdate_test.py $(COVER_OPTS) --cov=gnr.core.gnrdate

string:
	py.test gnrstring_test.py $(COVER_OPTS) --cov=gnr.core.gnrstring

locale:
	py.test locale_test.py $(COVER_OPTS) --cov=gnr.core.gnrlocale

resolver:
	py.test resolver_test.py $(COVER_OPTS) --cov=gnr.core
