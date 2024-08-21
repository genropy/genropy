from gnr.core.gnrbag import Bag

def main(db):
    documentation_contents = db.table('docu.documentation').query(columns='$id,$docbag', bagFields=True).fetch()
    for doc in documentation_contents:
        docbag = Bag(doc['docbag'])
        for lang,content in list(docbag.items()):
            if not content['title']:
                continue
            new_cont = db.table('docu.content').newrecord(title=content['title'], text=content['rst'])
            db.table('docu.content').insert(new_cont)
            new_doccont = db.table('docu.documentation_content').newrecord(content_id=new_cont['id'], documentation_id=doc['id'], language_code=lang)
            db.table('docu.documentation_content').insert(new_doccont)

    db.commit()