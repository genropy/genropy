#!/usr/bin/env python
# encoding: utf-8

import datetime
import sys
import os
import zipfile
import json

from gnr.db import logger
from gnr.core.gnrconfig import getGnrConfig
from gnr.core.cli import GnrCliArgParse
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp
from gnr.app.pathresolver import PathResolver
from gnr.sql.gnrsqlmigration import SqlMigrator
from gnr.sql import AdapterCapabilities
from gnr.db.cli import _migrator_bridge

description = "create/update/check database models in Genro framework NG"


def _external_scope(app, options):
    """Return the external CLI path when this run is in scope, else None.

    Scope (A): only plain check/apply on a direct PostgreSQL connection —
    inspect/import/extensions/rebuild and non-direct connections stay on the
    legacy path.
    """
    if options.inspect or options.import_file or options.extensions \
            or options.rebuild_relations or options.remove_relations_only:
        return None
    cmd = _migrator_bridge.external_cmd()
    if not cmd or not _migrator_bridge.is_direct_connection(app.db):
        return None
    return cmd


def _try_external_migrate(app, options):
    """Delegate a standard migrate/check to the external genro-sqlmigrate CLI.

    Used only in ``--newmode``: the external engine becomes the one that
    applies. Returns True if it handled the run, False to fall back to the
    in-process legacy engine.
    """
    cmd = _external_scope(app, options)
    if not cmd:
        return False

    extensions = app.db.application.config['db?extensions']
    engine_options = {'force': options.force, 'backup': options.backup}
    job = _migrator_bridge.build_job(app.db, extensions=extensions,
                                     options=engine_options)
    subcommand = 'check' if options.check else 'migrate'
    apply = not options.check
    result = _migrator_bridge.run_external(cmd, subcommand, job, apply=apply)
    if result.stderr:
        logger.error(result.stderr.rstrip())
    sql = result.stdout.strip()
    if subcommand == 'check':
        logger.info('STRUCTURE NEEDS CHANGES' if result.returncode == 1
                    else 'STRUCTURE OK')
        if sql and options.verbose:
            logger.info('*CHANGES:\n%s' % sql)
    else:
        if sql:
            logger.info('CHANGES APPLIED TO DATABASE' if apply
                        else 'STRUCTURE NEEDS CHANGES')
            if options.verbose:
                logger.info('*CHANGES:\n%s' % sql)
        else:
            logger.info('STRUCTURE OK')
    return True


def _shadow_compare(app, options, legacy_sql):
    """Compute the external SQL (without applying) and compare it to legacy.

    Runs in the default mode alongside the trusted legacy engine: the external
    ``migrate`` prints the SQL but does not touch the DB. Silent when the two
    agree; logs a warning only on a substantial divergence.

    The comparison is purely observational: any failure of the external path is
    logged and swallowed, so it can never interrupt the real (legacy) migrate.
    """
    cmd = _external_scope(app, options)
    if not cmd:
        return
    try:
        extensions = app.db.application.config['db?extensions']
        engine_options = {'force': options.force, 'backup': options.backup}
        job = _migrator_bridge.build_job(app.db, extensions=extensions,
                                         options=engine_options)
        result = _migrator_bridge.run_external(cmd, 'migrate', job, apply=False)
        if result.stderr:
            logger.error(result.stderr.rstrip())
        report = _migrator_bridge.compare_sql(legacy_sql, result.stdout)
    except Exception as err:
        logger.error('SHADOW COMPARE skipped: %s' % err)
        return
    if report['verdict'] != 'DIVERGENT':
        return
    lines = ['SHADOW COMPARE DIVERGENT: legacy and external SQL differ']
    if report['only_legacy']:
        lines.append('  only legacy:\n    %s'
                     % '\n    '.join(report['only_legacy']))
    if report['only_external']:
        lines.append('  only external:\n    %s'
                     % '\n    '.join(report['only_external']))
    logger.warning('\n'.join(lines))


def get_app(options):
    storename = None
    if options.directory:
        instance_path = options.directory
        if os.path.isdir(instance_path):
            return GnrApp(instance_path, debug=options.debug)
        else:
            raise Exception("No valid instance provided")

    if hasattr(options, 'config_path') and options.config_path:
        config_path = options.config_path
    else:
        config_path = None

    gnr_config = getGnrConfig(config_path=config_path, set_environment=True)

    path_resolver = PathResolver(gnr_config=gnr_config)
    
    instance_name = options.instance

    if instance_name:
        if '.' in instance_name:
            instance_name, storename = instance_name.split('.')
        instance_path = path_resolver.instance_name_to_path(instance_name)
        if os.path.isdir(instance_path):
            return GnrApp(instance_path, debug=options.debug), storename
        else:
            raise Exception("No valid instance provided")

    if options.site:
        site_path = path_resolver.site_name_to_path(options.site)
        if not site_path:
            site_path = os.path.join(gnr_config['gnr.environment_xml.sites?path'] or '',
                                     options.site)
        instance_path = os.path.join(site_path, 'instance')
        if os.path.isfile(os.path.join(instance_path, 'instanceconfig.xml')):
            return GnrApp(instance_path, debug=options.debug), storename
        else:
            raise "No valid instance provided"
    return GnrApp(os.getcwd()), storename


def inspect(migrator, options):
    # dump the information from the migrator, and generates a zip file
    # useful for inspection/debug
    logger.info("Creating migration inspection archive")
    now = datetime.datetime.now().strftime("%Y%m%d%H%M")
    dump_files = []
    orig_db_dump = f"{options.instance}_cur_db_struct_{now}"
    try:
        db_dump = migrator.db.dump(orig_db_dump,
                                   options=Bag(plain_text=True,
                                               schema_only=True)
                                   )
    except RuntimeError as e:
        logger.error("Can't execute database dump: %s", e)
        sys.exit(1)
        
    dump_files.append(db_dump)
        
    to_dump = [
        ("db_struct", migrator.sqlStructure),
        ("orm_struct", migrator.ormStructure),
        ("changes", migrator.getChanges)
    ]

    for dump_item in to_dump:
        filename = f"{options.instance}_{dump_item[0]}_{now}.json"
        with open(filename, "w") as wfp:
            if callable(dump_item[1]):
                wfp.write(json.dumps(dump_item[1]()))
            else:
                wfp.write(json.dumps(dump_item[1]))
        dump_files.append(filename)

    zip_name = f"{options.instance}_migrate_inspection_{now}.zip"
    with zipfile.ZipFile(zip_name, "w") as zipf:
        for filename in dump_files:
            zipf.write(filename)
            logger.info("Added %s to inspection archive", filename)

    # Remove temporary files after successful zip creation
    for filename in dump_files:
        os.remove(filename)
        logger.debug("Removed temp file %s", filename)
    print(f"Inspection archive {zip_name} created.")


def check_db(migrator, options):
    dbname = migrator.db.currentEnv.get('storename')
    dbname = dbname or 'Main'
    logger.info(f'DB {dbname}')
    if options.rebuild_relations or options.remove_relations_only:
        logger.info('Removing all relations')
        migrator.db.model.enableForeignKeys(enable=False)
        logger.info('Removed')
    if options.remove_relations_only:
        return
    changes = migrator.getChanges()
    if changes:
        if options.verbose:
            logger.info('*CHANGES:\n%s' % changes)
        else:
            logger.info('STRUCTURE NEEDS CHANGES')
    else:
        logger.info('STRUCTURE OK')
    return changes


def import_db(filepath, options):
    app = get_app(options)
    app.db.importXmlData(filepath)
    app.db.commit()


def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument('-c', '--check',
                        dest='check',
                        action='store_true',
                        help="Check only, don't apply changes")
    parser.add_argument('-u', '--upgrade',
                        dest='upgrade',
                        action='store_true',
                        help="Execute upgrade")
    parser.add_argument('-U', '--upgrade_only',
                        dest='upgrade_only',
                        action='store_true',
                        help="Execute only upgrade")
    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='store_true',
                        help="Verbose mode")
    parser.add_argument('-r', '--rebuild_relations',
                        dest='rebuild_relations',
                        action='store_true',
                        help="Rebuild relations")
    parser.add_argument('-x', '--remove_relations_only',
                        dest='remove_relations_only',
                        action='store_true',
                        help="Remove relations")
    parser.add_argument('-n', '--newmode',
                        dest='newmode',
                        action='store_true',
                        help="Use the new external migration engine to apply changes")
    parser.add_argument('--inspect',
                        dest='inspect',
                        action='store_true',
                        help='Create a dump file for inspection')
    parser.add_argument('-f', '--force',
                        dest='force',
                        action='store_true',
                        help='Force type conversions (non-matching values become NULL)')
    parser.add_argument('-b', '--backup',
                        dest='backup',
                        action='store_true',
                        help='Create backup columns before type conversions (implies --force)')
    parser.add_argument('-i', '--instance',
                        dest='instance',
                        help="Use command on instance")
    parser.add_argument("instance")
    parser.add_argument('-e', '--extensions',
                        dest='extensions',
                        choices=['txt','json','sql'],
                        help="List the needed extension in the provided format")
    parser.add_argument('-D', '--directory',
                        dest='directory',
                        help="Use command on supplied directory")
    parser.add_argument('-s', '--site',
                        dest='site',
                        help="Use command on supplied site")
    parser.add_argument('-I', '--import',
                        dest='import_file',
                        help="Import specified XML file")
    parser.add_argument('--config',
                        dest='config_path',
                        help="gnrserve file path")

    parser.set_defaults(loglevel="info")
    options = parser.parse_args()
    app, storename = get_app(options)
    if not app.db.adapter.has_capability(AdapterCapabilities.MIGRATIONS):
        logger.error(f"Instance '{options.instance}' adapter doesn't support migrations")
        sys.exit(1)

    errordb = []
    if storename == '*':
        stores = [None] + sorted(app.db.dbstores.keys())
    else:
        stores = [storename]
    for storename in stores:
        app.db.use_store(storename)
        if options.upgrade_only:
            logger.info(f'#### UPGRADE SCRIPTS IN STORE {storename} ####')
            app.pkgBroadcast('onDbUpgrade,onDbUpgrade_*')
            app.db.table('sys.upgrade').runUpgrades()
            app.db.commit()
            app.db.closeConnection()
            continue
        if options.newmode and _try_external_migrate(app, options):
            app.pkgBroadcast('onDbSetup,onDbSetup_*')
            if options.upgrade:
                app.pkgBroadcast('onDbUpgrade,onDbUpgrade_*')
                app.db.table('sys.upgrade').runUpgrades()
                app.db.commit()
            app.db.closeConnection()
            continue

        extensions = app.db.application.config['db?extensions']
        migrator = SqlMigrator(app.db, extensions=extensions,
                               ignore_constraint_name=True,
                               excludeReadOnly=True,
                               removeDisabled=True,
                               force=options.force,
                               backup=options.backup)
        migrator.prepareMigrationCommands()

        if options.extensions:
            # we only need the needed extensions
            # as defined in the application.
            needed_extensions = migrator.ormExtractor.get_json_struct().get('root', {}).get('extensions', {})
            if options.extensions == 'json':
                print(json.dumps(needed_extensions))
            if options.extensions == 'sql':
                print("\n".join([f"CREATE EXTENSION IF NOT EXISTS {x};" for x in needed_extensions]))
            if options.extensions == 'txt':
                print(",".join(needed_extensions))
            sys.exit(1)
            
        if options.check:
            changes = check_db(migrator, options)
            _shadow_compare(app, options, changes)
        elif options.import_file:
            import_db(options.import_file, options)
        elif options.inspect:
            inspect(migrator, options)
        else:
            changes = check_db(migrator, options)
            _shadow_compare(app, options, changes)
            if changes:
                logger.info('APPLYING CHANGES TO DATABASE...')
                migrator.applyChanges()
                logger.info('CHANGES APPLIED TO DATABASE')
        app.pkgBroadcast('onDbSetup,onDbSetup_*')
        if options.upgrade:
            app.pkgBroadcast('onDbUpgrade,onDbUpgrade_*')
            app.db.table('sys.upgrade').runUpgrades()
            app.db.commit()
        app.db.closeConnection()
    if errordb:
        logger.error(f'db: {errordb}')


if __name__ == '__main__':
    main()
