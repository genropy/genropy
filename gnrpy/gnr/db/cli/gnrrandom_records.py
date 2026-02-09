#!/usr/bin/env python
# encoding: utf-8

import json

from gnr.core.cli import GnrCliArgParse
from gnr.app.cli.gnrdbsetup import get_app
from gnr.sql.gnrsql_random import load_config_file, parse_typed_value

description = "generate random records for a given table"

DTYPE_LABELS = {
    'T': 'Text', 'A': 'Text (long)', 'I': 'Integer', 'L': 'Long',
    'N': 'Numeric', 'B': 'Boolean', 'D': 'Date', 'H': 'Time',
    'DH': 'DateTime', 'X': 'Blob',
}

DTYPE_PROMPTS = {
    'I': [('min_value', 'Min value', int), ('max_value', 'Max value', int)],
    'L': [('min_value', 'Min value', int), ('max_value', 'Max value', int)],
    'N': [('min_value', 'Min value', float), ('max_value', 'Max value', float)],
    'B': [('true_value', 'True percentage (0-100)', int)],
    'T': [('default_value', 'Default value (use #P=prefix, #N=counter)', str),
           ('random_value', 'Generate random text? (y/n)', str)],
    'A': [('default_value', 'Default value (use #P=prefix, #N=counter)', str),
           ('random_value', 'Generate random text? (y/n)', str)],
    'D': [('min_value', 'Min date (YYYY-MM-DD)', str),
           ('max_value', 'Max date (YYYY-MM-DD)', str)],
    'H': [('min_value', 'Min time (HH:MM)', str),
           ('max_value', 'Max time (HH:MM)', str)],
    'DH': [('min_value', 'Min datetime (YYYY-MM-DD HH:MM)', str),
            ('max_value', 'Max datetime (YYYY-MM-DD HH:MM)', str)],
}


def interactive_config(tblobj):
    config = dict()
    print(f"\nInteractive configuration for: {tblobj.fullname}")
    print("For each column enter values or press Enter to skip.\n")
    for col_name, col in list(tblobj.columns.items()):
        attr = col.attributes
        dtype = attr.get('dtype', 'T')
        if attr.get('_sysfield') or dtype == 'X':
            continue
        related = col.relatedTable()
        dtype_label = DTYPE_LABELS.get(dtype, dtype)
        size_info = f" size={attr['size']}" if attr.get('size') else ''
        if related:
            print(f"  {col_name} -> FK to {related.fullname}")
        else:
            print(f"  {col_name} ({dtype_label}{size_info})")
        skip = input("    Configure? [y/N] ").strip().lower()
        if skip not in ('y', 'yes'):
            continue
        if related:
            condition = input("    WHERE condition (empty=all): ").strip()
            if condition:
                config[col_name] = {'condition': condition}
            continue
        prompts = DTYPE_PROMPTS.get(dtype, [])
        field_config = dict()
        for param_name, prompt_text, converter in prompts:
            raw = input(f"    {prompt_text}: ").strip()
            value = parse_typed_value(raw, dtype, converter)
            if value is not None:
                field_config[param_name] = value
        if field_config:
            config[col_name] = field_config
    if config:
        print(f"\nConfiguration: {json.dumps(config, indent=2, default=str)}")
        confirm = input("Proceed? [Y/n] ").strip().lower()
        if confirm in ('n', 'no'):
            print("Aborted.")
            return None
    return config


def main():
    parser = GnrCliArgParse(description=description)

    parser.add_argument('table',
                        help="Table name (pkg.tablename)")

    parser.add_argument('-i', '--instance',
                        dest='instance',
                        help="Instance name")

    parser.add_argument('-D', '--directory',
                        dest='directory',
                        help="Instance directory path")

    parser.add_argument('-n', '--how_many',
                        dest='how_many',
                        type=int,
                        default=10,
                        help="Number of records to generate (default: 10)")

    parser.add_argument('--seed',
                        dest='seed',
                        type=int,
                        default=None,
                        help="Random seed for reproducibility")

    parser.add_argument('--batch_prefix',
                        dest='batch_prefix',
                        default='RND',
                        help="Prefix for generated text fields (default: RND)")

    parser.add_argument('-I', '--interactive',
                        dest='interactive',
                        action='store_true',
                        help="Interactive mode: configure fields one by one")

    parser.add_argument('--config',
                        dest='config_file',
                        default=None,
                        help="YAML/JSON config file with field parameters")

    options = parser.parse_args()
    app, storename = get_app(options)
    if storename:
        app.db.use_store(storename)

    config = None
    if options.config_file:
        config = load_config_file(options.config_file)
    if options.interactive:
        tblobj = app.db.table(options.table)
        config = interactive_config(tblobj)
        if config is None:
            return

    kwargs = dict(how_many=options.how_many,
                  seed=options.seed,
                  batch_prefix=options.batch_prefix)
    if config:
        kwargs['config'] = config
    app.db.createRandomRecords(options.table, **kwargs)
    print(f"{options.how_many} random records created for {options.table}")


if __name__ == '__main__':
    main()
