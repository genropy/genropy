from gnr.app import pkglog as logger

def main(db):
    logger.info("Ensure GLBL data is loaded")
    if not db.table("glbl.nazione").query().count():
        logger.info("Loading GLBL data")
        db.package("glbl").loadStartupData()
    
