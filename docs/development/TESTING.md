# Testing Genropy Framework

This guide will describe the needed steps to execute unit test for the
Genropy framework.

## Installation
Install genropy with the 'developer' profile, for example:

```
  cd genropy/gnrpy && pip install -e .[developer]
```

This will provide all the needed dependencies to run tests.


## Execute the tests

Python unit tests are localted in gnrpy/tests folder, so executing

```
cd gnrpy/tests && make
```

or, alternatively

```
cd gnrpy/tests && pytest
```
	
will execute all the tests. Since tests are organized per framework
sub-modules, you can test single part of if. The folders tests/app,
tests/core, tests/sql represents the framework sub-packages.

The makefile provided sets up coverage html output for convenience.

## A note about Postgres databases

The sql databases are execute against multiple adapters
automatically. When using a postgres-base adapter, it tests
automatically spins up a temporary postgres instance to be used for
tests, using testing.postgresql package. The DSN is provided
automatically so there is nothing to do.

If you need to use a pre-existing postgres server, you can setup the
following environment variables:

* GNR_TEST_PG_HOST
* GNR_TEST_PG_PORT
* GNR_TEST_PG_USER
* GNR_TEST_PG_PASSWORD

Variables names are self-explaining.

When tests are executed in a Github Action CI context, a temporary
service with postgres will be spin up automatically.





## Comparing the PDF engines (weasyprint vs wkhtmltopdf)

Genropy renders prints through two interchangeable `htmltopdf` service
implementations, `weasyprint` and `wk` (wkhtmltopdf), and they do not produce
the same PDF from the same HTML. `gnrpy/tests/core/htmltopdf_enginediff_test.py`
tests the harness that measures the gap; the harness itself lives in
`gnr.utils.pdfcompare` and `gnr.utils.htmltopdfdiff` so that an application's
own test suite can use it on its own prints.

The comparison renders one source document with both engines and fits the
`position * scale + offset` transform between the two renderings of each page.
That separates three different problems:

- **offset**: the engines disagree on the page margins. wkhtmltopdf applies its
  own margins even to a document declaring `@page {margin: 0}`, so the content
  starts a few millimeters inside the page. Fixed by aligning the margins.
- **scale**: wkhtmltopdf lays the document out on a wide viewport and fits it
  into the printable area, shrinking the whole print by a constant factor.
  Fixed by a zoom, not by margins.
- **residual**: what neither an offset nor a zoom explains. A residual means
  the engines broke lines or paginated differently, and no global setting will
  reconcile them.

Both engines are optional: the tests are skipped unless `weasyprint` is
importable and the `wkhtmltopdf` binary is on the PATH.

### Comparing the prints of an application

To run the comparison over a real application's prints (Erpy, Genromed, any
instance), collect the prints as HTML and point the suite at the folder:

1. In the instance, set the `sys.pdf_render` preference `keep_html` so that
   every rendered print is saved under `site:print_debug`.
2. Run the prints you want to check.
3. Run the suite against that folder:

```
cd gnrpy
GNR_PRINT_FIXTURES=/path/to/site/print_debug/2026-09-14 \
    pytest tests/core/htmltopdf_enginediff_test.py -k application_prints -s
```

The test renders every print with both engines, prints the per-page summary and
writes a browsable HTML report with a false-colour overlay per page. The overlay
is aligned on the fitted transform, so a print the engines only disagree on by
margins comes out black and white while a real layout difference lights up: the
reference rendering drives the red channel and the compared one green and blue,
so shared ink stays black, ink only in the reference shows up cyan and ink only
in the compared rendering shows up red.

The test asserts only that every print is renderable and comparable, not that
the engines agree: the differences are what is being investigated, so they are
reported rather than treated as failures.
