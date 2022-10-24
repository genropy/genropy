# encoding: utf-8

def main(db):
    print('0001 Starting upgrade after S3 configuration')
    upgradeAttachments(db)
    upgradeContents(db)
    upgradePreference(db)
    upgradeHandbooks(db)
    db.commit()
    print('0001 Upgrade ended')

def upgradeAttachments(db):
    doc_atcs = db.table('docu.documentation_atc').query(for_update=True).selection().output('records')
    for atc in doc_atcs:
        atc['filepath'] = atc['filepath'].replace('docu_documentation', 'documentation:attachments')
        atc['filepath'] = atc['filepath'].replace('home:docu_documentation', 'documentation:attachments')
        db.table('docu.documentation_atc').raw_update(atc)
    print('Updated documentation attachments')

def upgradeContents(db):
    docs = db.table('docu.documentation').query(for_update=True).selection().output('records')
    for doc in docs:
        for doc_lang in doc['docbag']:
            if doc_lang.value['rst']:
                doc_lang.value['rst'] = doc_lang.value['rst'].replace('_vol:docu_documentation', 'documentation:attachments')
                doc_lang.value['rst'] = doc_lang.value['rst'].replace('_vol/docu_documentation', 'documentation:attachments')
                doc_lang.value['rst'] = doc_lang.value['rst'].replace('home:docu_documentation', 'documentation:attachments')
        db.table('docu.documentation').raw_update(doc)
    print('Updated documentation content')

def upgradePreference(db):
    for p in ['sphinx_path', 'local_path']:
        path = db.application.getPreference(f'.{p}',pkg='docu') 
        if path and 'site:' in path:
            path = path.replace('site', 'documentation')
            db.package('docu').setPreference(f'.{p}', path) 
    print('Updated preferences')

def upgradeHandbooks(db):
    handbooks = db.table('docu.handbook').query(for_update=True).selection().output('records')
    for book in handbooks:
        if book['ogp_image'] and '/_storage/site/handbooks_images' in book.get('ogp_image'):
            book['ogp_image'] = book['ogp_image'].replace('site', 'documentation')
        db.table('docu.handbook').checkSphinxPath(book)
        db.table('docu.handbook').raw_update(book)
    print('Updated handbooks image and path')