(help-page-test-test_page_doc)=
# How the documentation works in GenroPy

Every element a user meets on a page — a field, a grouplet card, a table, a part
of the page — has a documentation **address**. The ⓘ next to the element shows
what documents that address, taken from two sources: the **published manual**
of the application and the **notes** written on the page itself by the
customer's documenters. The ⓘ of a field, a card or a block opens a popup at
the icon; the ⓘ of the page and of a table opens the help panel on the right.

(help-page-test-test_page_doc-addresses)=
## Addresses

An address is `<kind>:<target>:<name>`, the context-sensitive help ID of the
element:

| Kind | Address | Written by |
| --- | --- | --- |
| Field | `field:adm.user:email` | `fb.field('email')` in any form of the table |
| Table | `table:adm.user:` | the views and forms of a table handler |
| Grouplet | `grouplet:test:card_profile` | a grouplet resource, or `doc=` on a card |
| Page | `page:test/test_page_doc:` | the page itself |
| Part of a page | `page:test/test_page_doc:sources` | `helpcode='sources'` |

The same address is the same doc wherever the element appears: the email of the
users table is documented once and shows in every form that holds it.

(help-page-test-test_page_doc-sources)=
## Two sources

**The manual** is a Sphinx site written in MyST Markdown. A section documents an
address by carrying its label: `help-` followed by the address with `:`, `.`
and `/` turned into `-`, lower case — `(help-field-adm-user-email)=` above the
heading. `adm.helpdoc` links the manual pages to the user groups: a user reads
the pages of the user's own group first, then the pages linked to no group. A
label ending in `--<variant>` (`help-field-adm-user-email--operator`) is a
variant of the same address, read only from the pages of the user's own group.

**The notes** are Markdown files the customer writes on the page, in place,
without building anything. They show under the manual's section, or alone where
the manual says nothing.

(help-page-test-test_page_doc-visibility)=
## Who sees what

- The ⓘ shows only where the manual or a note documents the address: a user
  never meets an empty one.
- **Documentation mode** (`gnr.docModeVisible`) shows to a documenter the
  addresses nobody documented yet, with a red ⓘ: the list of what is missing.
- A **documenter** is a user with the tag `_DOC_`, or `doc_<package>` for the
  addresses of one package.
- Nothing answers a guest: the docs are read through `sys/ep_doc`, from the
  connection of a logged user.

(help-page-test-test_page_doc-editing)=
## Writing a note

- A click on a red ⓘ opens the editor, Markdown or WYSIWYG; on a documented
  address, *Add a note* or *Edit the note* in the popup.
- An image pasted in the editor is stored next to the note (png, jpg, gif or
  webp, up to 5 MB).
- The note of a grouplet may hold the values of the row it documents: the
  editor lists them as variables (`$city`, `$province`), and `doc_kw` adds more.
- One file per language: a note in another language is the starting point of a
  translation, saved as a new file.
- A note saved meanwhile by somebody else asks before being overwritten.
- A note saved empty is removed.

(help-page-test-test_page_doc-storage)=
## Where the notes live

The notes are files in the `inlinedoc` storage, one folder per address:

    adm/user/fields/email/it.md
    test/_grouplets/card_profile/en.md
    test/_pages/test_page_doc/_page/it.md
    test/_pages/test_page_doc/sources/it.md

Each opens with a YAML front matter (`id`, `title`, `type`, `updated`,
`author`), so the same files build a Sphinx reference through myst-parser. The
storage is private: no url serves it, only `sys/ep_doc`. It is a folder of the
instance unless a storage service named `inlinedoc` is configured — an S3
bucket, for example.

The whole feature sits behind an experimental flag of the instanceconfig:

    <experimental><gui inlinedoc="true"/></experimental>

Without it no ⓘ is drawn and `sys/ep_doc` answers nothing.

(help-page-test-test_page_doc-code)=
## In the code

```python
fb.field('email')                                    # field:<pkg.table>:email
fb.textbox(value='^.notes', lbl='Notes', helpcode='notes')   # page:<pkg>/<page>:notes
pane.roundedGroup(title='Shipping', helpcode='shipping')     # a part of the page
pane.groupletCard(datapath='.shipping', resource='card_profile')   # grouplet:<pkg>:card_profile
pane.groupletCard(handler=self.fields, doc='grouplet:test:notes', doc_kw=dict(when='daily'))
pane.docHelpButton('table:adm.user:', title='Users', tooltip=True)
```

A grouplet resource declares its card doc in `__info__`:
`card=dict(tools='collapse,title,doc,menu', doc=..., doc_kw=...)`.
