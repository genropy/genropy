COVER_OPTS=--cov-report=html --cov=gnr.core

tests:
	py.test *.py $(COVER_OPTS) --cov=gnr.core

bag:
	py.test gnrbag_test.py $(COVER_OPTS) --cov=gnr.core.gnrbag --cov=gnr.core.gnrbagxml

date:
	py.test	gnrdate_test.py $(COVER_OPTS) --cov=gnr.core.gnrdate

string:
	py.test gnrstring_test.py $(COVER_OPTS) --cov=gnr.core.gnrstring

locale:
	py.test gnrlocale_test.py $(COVER_OPTS) --cov=gnr.core.gnrlocale

resolver:
	py.test gnrresolver_test.py $(COVER_OPTS) --cov=gnr.core
