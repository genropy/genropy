# Users and shipping

(help-page-test-test_manual_help)=
## This page

The page shows how a manual section reaches the "?" of fields, cards, blocks
and table views. Its own "?" is the one of the page.

(help-field-adm-user-username)=
## Username

The name used to log in. It is unique and has no spaces: write it **lower case**,
for example `m.rossi`.

(help-field-adm-user-email)=
## Email

The address that receives the notifications and the password reset links.

| Kind | Example |
| --- | --- |
| Personal | `mario.rossi@example.org` |
| Shared mailbox | `office@example.org` |

(help-grouplet-test-card_profile)=
## Shipping address card

Street, city and province of the delivery. The province decides the delivery
zone; the courier comes from the profile.

(help-page-test-test_manual_help-shipping)=
## Shipping block

A block of the page with its own "?": `roundedGroup(title=..., helpcode='shipping')`.

(help-table-adm-user)=
## The users table

Every person who logs in. Double click a row to open the user; the group decides
the menu and the manual the user sees.

(help-grouplet-test-demo_customer)=
## Customer card

Name and VAT number of the customer. Both are required: while one is empty the
band of the card stays red, folded or not, and the form cannot be saved.

