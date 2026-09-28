# Opening a table page with a query in its query editor

A page that opens a table page (a `thpage` with the extended query) can send
it conditions to load in the query editor, and optionally a view of its grid
and a grouped view: the page opens the query editor with them, the user
reviews and runs them, or they are run at once.

The table page subscribes to the topic `th_external_query`
(`TableHandlerMain`, `resources/common/public.py`) and loads the message with
`QueryManager.applyExternalQuery` (`resources/common/th/th_querytool.js`) once
its query manager is ready.

From the index, the message travels with `openKw`, which the index posts to
the page iframe when it starts and when it is selected:

```javascript
kw.openKw = {topic: 'th_external_query',
             query_id: 'q_' + new Date().getTime(),   // optional
             table: 'invc.invoice',                  // ignored by other tables
             title: 'Invoices 2022 above 10,000',
             where_xml: where.toXml(),               // the query editor where bag
             orderby_xml: order.toXml(),             // optional custom order bag
             limit: 100,                             // optional
             run: false,                             // run after loading
             view: {code: 'q_view', caption: 'Invoices by customer',
                    struct_xml: struct.toXml()},     // optional grid view
             groupby: {code: 'q_grp', caption: 'Total by month',
                       struct_xml: grpstruct.toXml(),
                       mode: 'flatview'}};           // optional grouped view
genro.publish('selectIframePage', kw);
```

`where_xml` is the `where` bag as the query editor writes it: nodes `c_0`,
`c_1`... with the attributes `column`, `column_caption`, `column_dtype`, `op`,
`op_caption`, `jc`, `not`, `value_caption`, and a bag value for a group. A
condition whose `value_caption` starts with `?` is asked when the query runs.
The custom order bag has rows with `fieldpath` and `sorting` (true ascending).
Bags are serialized because the message crosses the iframe boundary.

`view` and `groupby` carry grid structs (`view_0.rows_0` with a cell per
column: `field`, `name`, `dtype`, `width`...). They are added to the views of
the grid and of the Group By grid as temporary views, the views the grid
configurator creates with *New view*: the views menu lists them and the user
can save them. A grouped view makes the page show the Group By tools and run
the query, since it totalizes the records of the main view. In its struct a
cell without `group_aggr` breaks the groups, a date cell breaks them with a
`to_char` pattern in `group_aggr` (`YYYY-MM`, with `dtype` `T` and
`original_dtype` `D`), a numeric cell is aggregated with `group_aggr` `sum`,
`avg`, `min` or `max`, and the `_grp_count` cell counts the records.
Conditions are optional when a view or a grouped view is sent.

A message with a `query_id` is applied once: the page confirms it to its
parent window with the topic `th_external_query_applied` and `query_id`, so
that the sender can drop it from the `openKw` of the index tab and other pages
opened later from the same tab do not receive it again.
