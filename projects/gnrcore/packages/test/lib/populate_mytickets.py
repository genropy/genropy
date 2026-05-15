"""Populate `test.myticket` with sample tickets — one or more per
grouplet category, with realistic-ish extra_data sub-Bags.

Usage:
    python populate_mytickets.py [instance_name]

Default instance: `sandboxpg`. Existing rows are NOT deleted; the
script just appends. Re-running adds more tickets.
"""
import sys
from datetime import date, timedelta
from decimal import Decimal

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag


SAMPLES = [
    # (ticket_type, subject, status, days_ago, extra_data dict)
    ('commercial/offer', 'Offer for Acme Corp Q2',
     'open', 3,
     dict(estimated_budget=Decimal('15000.00'),
          offer_deadline=date.today() + timedelta(days=14),
          products_of_interest='Cloud platform, premium support')),
    ('commercial/offer', 'Offer for Globex renewal',
     'in_progress', 8,
     dict(estimated_budget=Decimal('42000.00'),
          offer_deadline=date.today() + timedelta(days=30),
          products_of_interest='Enterprise tier, training package')),
    ('commercial/company', 'New lead — Initech',
     'open', 1,
     dict(company_name='Initech',
          industry='Software',
          company_size='medium')),
    ('commercial/contract', 'Renew contract with Stark Industries',
     'in_progress', 12,
     dict(contract_type='renewal',
          duration_months=24,
          sla_level='premium')),
    ('administrative/billing', 'Invoice 2026-0142 overdue',
     'open', 5,
     dict(invoice_number='2026-0142',
          amount=Decimal('3400.00'),
          due_date=date.today() - timedelta(days=10))),
    ('administrative/licenses', 'License renewal — Acme',
     'closed', 30,
     dict(license_type='enterprise',
          user_count=120,
          expiry_date=date.today() + timedelta(days=180))),
    ('technical/system', 'Slow performance on prod cluster',
     'in_progress', 2,
     dict(operating_system='Ubuntu 22.04 LTS',
          software_version='3.4.1',
          browser='Chrome 138')),
    ('technical/error', 'NullPointer at checkout flow',
     'open', 0,
     dict(error_code='E_NPE_4471',
          error_message='Cannot read property "id" of undefined',
          log='at checkout.js:142\n  at process.tick (node:internal/...)\n  ...')),
    ('technical/reproduction', 'Cannot reproduce search timeout',
     'closed', 20,
     dict(steps_to_reproduce='1. Login as guest\n'
                             '2. Search "test"\n'
                             '3. Wait 30s',
          expected_result='Results within 2s',
          actual_result='Worked fine in QA; not reproducible')),
]


def populate(instance_name='sandboxpg'):
    app = GnrApp(instance_name)
    db = app.db
    tbl = db.table('test.myticket')
    inserted = 0
    for ticket_type, subject, status, days_ago, extra in SAMPLES:
        extra_bag = Bag()
        for k, v in extra.items():
            extra_bag[k] = v
        record = dict(
            subject=subject,
            ticket_type=ticket_type,
            ticket_date=date.today() - timedelta(days=days_ago),
            status=status,
            description=f'Auto-generated sample for {ticket_type}.',
            extra_data=extra_bag,
        )
        tbl.insert(record)
        inserted += 1
    db.commit()
    print(f'Inserted {inserted} sample tickets into test.myticket '
          f'(instance: {instance_name})')


if __name__ == '__main__':
    instance = sys.argv[1] if len(sys.argv) > 1 else 'sandboxpg'
    populate(instance)
