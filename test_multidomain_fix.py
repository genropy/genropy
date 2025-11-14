#!/usr/bin/env python3
"""
Test per verificare il fix del problema catchall su _main_

Test cases:
1. Richiesta a /_main_/ → OK (200)
2. Richiesta a /workspace_valido/ → OK (dipende se workspace esiste)
3. Richiesta a /dominio_invalido/ → 404 HTTPNotFound (NO accumulo su _main_)
"""

import sys
import os

# Test simulato - da eseguire manualmente contro istanza reale

test_urls = [
    ('/_main_/', 'Should work - admin interface'),
    ('/workspace1/', 'Should work if workspace1 exists'),
    ('/invalid_domain/', 'Should return 404 - NO accumulation on _main_'),
    ('/wp-admin/', 'Should return 404 - bot scanning blocked'),
    ('/phpmyadmin/', 'Should return 404 - security scan blocked'),
]

print("=" * 70)
print("MULTIDOMAIN CATCHALL FIX - TEST CASES")
print("=" * 70)
print()
print("Quick Fix implementato in: gnrpy/gnr/web/gnrwsgisite.py:867-871")
print()
print("Test da eseguire manualmente:")
print()

for url, description in test_urls:
    print(f"✓ Test: curl -I http://localhost:8081{url}")
    print(f"  Descrizione: {description}")
    print()

print("=" * 70)
print("VERIFICA FIX")
print("=" * 70)
print()
print("PRIMA del fix:")
print("  - Richieste invalide finivano su _main_")
print("  - Register _main_ accumulava entries")
print("  - Dopo giorni → 400 Bad Request")
print()
print("DOPO il fix:")
print("  - Richieste invalide → 404 immediato")
print("  - Register _main_ rimane pulito")
print("  - NO accumulo, NO errori 400")
print()
print("Per verificare in produzione:")
print()
print("# Before fix - register _main_ grows")
print(">>> len(site.domains['_main_'].register.pages)")
print("50000+  # PROBLEMA!")
print()
print("# After fix - register _main_ stays clean")
print(">>> len(site.domains['_main_'].register.pages)")
print("~100  # Solo richieste legittime a /_main_/")
print()
print("=" * 70)
