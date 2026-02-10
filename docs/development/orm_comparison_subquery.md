# Genropy vs Django vs SQLAlchemy: Subquery e Colonne Virtuali

## Caso d'uso: Dashboard prodotti con analisi clienti

Per ogni prodotto vogliamo mostrare:
1. Il fatturato totale del prodotto
2. Il nome del miglior cliente (chi ha comprato di più quel prodotto)
3. Il fatturato totale del miglior cliente (su tutti i prodotti, non solo questo)
4. La percentuale che il prodotto rappresenta nel fatturato di quel cliente

Schema relazionale: `prodotto ← fattura_riga → fattura → cliente`

---

## Genropy

### Definizione nel modello (una volta sola)

```python
# prodotto.py
tbl.formulaColumn('totale_fatturato', select=dict(
    table='fatt.fattura_riga',
    columns='SUM($prezzo_totale)',
    where='$prodotto_id=#THIS.id'),
    dtype='N', name_long='Tot.Fatturato')

tbl.formulaColumn('top_cliente_id', select=dict(
    table='fatt.fattura_riga',
    columns='@fattura_id.cliente_id',
    where='$prodotto_id=#THIS.id',
    group_by='@fattura_id.cliente_id',
    order_by='SUM($prezzo_totale) DESC',
    limit=1),
    dtype='T', name_long='Top Cliente'
    ).relation('cliente.id', relation_name='top_prodotti')

# cliente.py
tbl.formulaColumn('tot_fatturato', select=dict(
    table='fatt.fattura',
    columns='SUM($totale_fattura)',
    where='$cliente_id=#THIS.id'),
    dtype='N', name_long='Tot.Fatturato')
```

### Query

```python
tbl.query(columns="""$descrizione,
                      $totale_fatturato,
                      @top_cliente_id.ragione_sociale,
                      @top_cliente_id.tot_fatturato""",
          order_by='$descrizione')
```

Quattro colonne, una riga. La navigazione `@top_cliente_id.tot_fatturato` attraversa una
relazione logica (non fisica) e accede a una colonna virtuale (non fisica) definita su un'altra
tabella. Due livelli di astrazione che si compongono trasparentemente.

Con `enable_sq_join=True` le subquery aggregazione vengono automaticamente convertite in
LEFT JOIN pre-aggregati, e le subquery con `limit` vengono wrappate con ROW_NUMBER()
OVER (PARTITION BY ...) — tutto senza cambiare il codice applicativo.

---

## Django ORM

### Definizione

Django non ha il concetto di colonne virtuali riusabili nel modello.
Ogni query deve ricostruire le annotazioni da zero.

```python
from django.db.models import Subquery, OuterRef, Sum, F, CharField
from django.db.models.functions import Coalesce

# Step 1: subquery per il top cliente di ogni prodotto
top_cliente_per_prodotto = (
    FatturaRiga.objects
    .filter(prodotto_id=OuterRef('pk'))
    .values('fattura__cliente_id')
    .annotate(tot=Sum('prezzo_totale'))
    .order_by('-tot')
    .values('fattura__cliente_id')[:1]
)

# Step 2: subquery per il nome del top cliente
nome_top_cliente = (
    Cliente.objects
    .filter(id=Subquery(top_cliente_per_prodotto))
    .values('ragione_sociale')[:1]
)

# Step 3: subquery per il fatturato totale del top cliente
fatturato_top_cliente = (
    Fattura.objects
    .filter(cliente_id=Subquery(top_cliente_per_prodotto))
    .values('cliente_id')
    .annotate(tot=Sum('totale_fattura'))
    .values('tot')[:1]
)

# Step 4: subquery per il fatturato del prodotto
fatturato_prodotto = (
    FatturaRiga.objects
    .filter(prodotto_id=OuterRef('pk'))
    .values('prodotto_id')
    .annotate(tot=Sum('prezzo_totale'))
    .values('tot')
)

# Query finale
Prodotto.objects.annotate(
    totale_fatturato=Subquery(fatturato_prodotto),
    top_cliente_nome=Subquery(nome_top_cliente, output_field=CharField()),
    top_cliente_fatturato=Subquery(fatturato_top_cliente),
)
```

Ogni "livello" richiede una Subquery esplicita annidata. La subquery del fatturato
del top cliente (`fatturato_top_cliente`) non può riusare una definizione sul modello
Cliente — va riscritta ogni volta che serve in un contesto diverso.

---

## SQLAlchemy

### Definizione

```python
from sqlalchemy import func, select, and_
from sqlalchemy.orm import aliased

# Step 1: subquery per il fatturato per prodotto-cliente
fatt_per_cliente = (
    select(
        FatturaRiga.prodotto_id,
        Fattura.cliente_id,
        func.sum(FatturaRiga.prezzo_totale).label('tot')
    )
    .join(Fattura, FatturaRiga.fattura_id == Fattura.id)
    .group_by(FatturaRiga.prodotto_id, Fattura.cliente_id)
    .subquery()
)

# Step 2: subquery per il top cliente per prodotto (richiede DISTINCT ON o ROW_NUMBER)
from sqlalchemy import over
ranked = (
    select(
        fatt_per_cliente.c.prodotto_id,
        fatt_per_cliente.c.cliente_id,
        fatt_per_cliente.c.tot,
        func.row_number().over(
            partition_by=fatt_per_cliente.c.prodotto_id,
            order_by=fatt_per_cliente.c.tot.desc()
        ).label('rn')
    )
    .subquery()
)
top_cliente = (
    select(ranked.c.prodotto_id, ranked.c.cliente_id)
    .where(ranked.c.rn == 1)
    .subquery()
)

# Step 3: join per il nome
ClienteAlias = aliased(Cliente)

# Step 4: subquery per il fatturato totale del top cliente
fatt_totale_cliente = (
    select(func.sum(Fattura.totale_fattura))
    .where(Fattura.cliente_id == top_cliente.c.cliente_id)
    .correlate(top_cliente)
    .scalar_subquery()
)

# Step 5: query finale
query = (
    select(
        Prodotto.descrizione,
        func.sum(FatturaRiga.prezzo_totale).label('totale_fatturato'),
        ClienteAlias.ragione_sociale,
        fatt_totale_cliente.label('fatt_top_cliente')
    )
    .outerjoin(top_cliente, Prodotto.id == top_cliente.c.prodotto_id)
    .outerjoin(ClienteAlias, ClienteAlias.id == top_cliente.c.cliente_id)
    .outerjoin(FatturaRiga, FatturaRiga.prodotto_id == Prodotto.id)
    .group_by(Prodotto.id, Prodotto.descrizione,
              ClienteAlias.ragione_sociale, top_cliente.c.cliente_id)
)
```

SQLAlchemy è il più verboso: ogni join va esplicitato, il ROW_NUMBER va costruito
manualmente, e non esiste alcun meccanismo di composizione tra definizioni su modelli diversi.

---

## Confronto sintetico

| Aspetto | Genropy | Django | SQLAlchemy |
|---|---|---|---|
| **Colonne virtuali riusabili** | `formulaColumn` nel modello, usata ovunque con `$nome` | Non esiste, annotazioni ogni volta | Non esiste |
| **Navigazione relazioni** | `@fattura_id.@cliente_id.ragione_sociale` | Join/Subquery esplicite | Join espliciti con alias |
| **Relazione su colonna calcolata** | `.relation('cliente.id')` → navigabile con `@` | Non esiste | Non esiste |
| **Composizione trasparente** | Colonna virtuale che naviga altra colonna virtuale | Subquery dentro subquery, manuale | Subquery dentro subquery, manuale |
| **Ottimizzazione subquery→JOIN** | `enable_sq_join=True`, automatico | Manuale | Manuale |
| **ROW_NUMBER per limit+JOIN** | Automatico (wrapping trasparente) | Manuale o raw SQL | Manuale |
| **Righe di codice (questo caso)** | ~15 (modello) + 1 (query) | ~35 (ogni query) | ~45 (ogni query) |
| **Riuso cross-tabella** | `@top_cliente_id.tot_fatturato` riusa la definizione di `cliente` | Impossibile senza riscrivere | Impossibile senza riscrivere |

## Il punto chiave

La differenza fondamentale non è solo la brevità sintattica. È che in Genropy le colonne
virtuali e le relazioni logiche **si compongono**: una volta definite nel modello, sono
disponibili ovunque come se fossero colonne fisiche. In Django e SQLAlchemy ogni query
deve ricostruire la logica da zero, rendendo il codice fragile (la stessa formula in N posti)
e difficile da mantenere.

Il pattern `formulaColumn` + `relation` + navigazione `@` crea un livello di astrazione
che gli altri ORM semplicemente non hanno.
