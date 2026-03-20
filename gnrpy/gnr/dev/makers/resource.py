import os, os.path
import ast
from pathlib import Path
from collections import defaultdict

from gnr.core.gnrbag import Bag
from gnr.web.gnrmenu import MenuStruct
from gnr.dev import logger


class ResourceMaker(object):
    """Handle the creation of the ``resources`` folder"""

    def __init__(self, resource_name, base_path=None):
        self.resource_name = resource_name
        self.base_path = base_path or "."

    def do(self):
        """TODO"""
        self.resource_path = os.path.join(self.base_path, self.resource_name)
        for path in (self.resource_path,):
            if not os.path.isdir(path):
                os.makedirs(path, exist_ok=True)


class ThPackageResourceMaker(object):
    def __init__(
        self,
        application,
        package=None,
        tables=None,
        force=False,
        menu=False,
        columns=2,
        guess_size=False,
        indent=4,
        bag_columns=None,
        filename=None,
        output=None,
    ):
        self.option_force = force
        self.option_menu = menu
        self.option_output = filename or output
        self.option_columns = columns
        self.option_guess_size = guess_size
        if self.option_guess_size:
            logger.debug("Guessing column width by data size: ACTIVE")
        self.option_indent = indent
        self.pkg_tables = defaultdict(list)
        self.pkg_menus = dict()
        self.app = application
        self.package = package
        self.bag_columns = bag_columns or dict(view=False, form=False)
        self.tables = (
            tables if tables else list(self.app.db.packages[self.package].tables.keys())
        )
        if not self.app.packages(package):
            raise ModuleNotFoundError(f"Package {package} was not found")

        self.packageFolder = self.app.packages(package).packageFolder
        self.has_lookups = False

    def makeResources(self):
        for table in self.tables:
            table_full_name = f"{self.package}.{table}"
            logger.debug("Processing table %s", table_full_name)
            if "lookup" in self.app.db.table(table_full_name).attributes:
                logger.debug("Skipping lookup table %s", table_full_name)
                self.has_lookups = True
                continue
            self.createResourceFile(table)

        if self.option_menu:
            self.makeMenu()

    def makeMenu(self):
        menu_xml_path = os.path.join(self.packageFolder, "menu.xml")
        self.pkg_menus[self.package] = (
            Bag(menu_xml_path) if os.path.exists(menu_xml_path) else Bag()
        )

        if self.has_lookups:
            self.pkg_menus[self.package].setItem(
                "auto.lookups",
                None,
                label="!!Lookup tables",
                pkg=self.package,
                tag="lookupBranch",
            )

        menupath = Path(self.packageFolder) / "menu.py"

        if menupath.exists():
            logger.info("Menu file %s exists, appending", menupath)
            source = menupath.read_text(encoding="utf-8")
            tree = ast.parse(source)
            lines = source.splitlines(keepends=True)

            class Finder(ast.NodeVisitor):
                """
                Simple AST visitor to search for the root branch assignment
                and add a new page to such branch
                """

                def __init__(self):
                    self.config_func = None
                    self.branch_var = None

                def visit_ClassDef(self, node):
                    if node.name != "Menu":
                        return
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == "config":
                            self.config_func = item
                            self._find_branch_assignment(item)
                            return

                def _find_branch_assignment(self, func):
                    for stmt in func.body:
                        if not isinstance(stmt, ast.Assign):
                            continue
                        if len(stmt.targets) != 1:
                            continue
                        target = stmt.targets[0]
                        if not isinstance(target, ast.Name):
                            continue
                        value = stmt.value
                        if not isinstance(value, ast.Call):
                            continue
                        func_attr = value.func
                        if (
                            isinstance(func_attr, ast.Attribute)
                            and isinstance(func_attr.value, ast.Name)
                            and func_attr.value.id == "root"
                            and func_attr.attr == "branch"
                        ):
                            self.branch_var = target.id
                            return

            finder = Finder()
            finder.visit(tree)
            if not finder.config_func:
                raise RuntimeError("Menu.config not found")
            if finder.branch_var is None:
                raise RuntimeError("Root branch not found")
            insert_at = finder.config_func.end_lineno
            for item in self.pkg_menus[self.package]["auto"] or []:
                new_line = f"\n        {finder.branch_var}.thpage(u'{item.attr['label']}', table='{item.attr['table']}')"
                lines.insert(insert_at, new_line)
                insert_at += 1

            menupath.write_text("".join(lines), encoding="utf-8")

        else:
            logger.info("Menu file %s does not exist, creating", menupath)
            m = MenuStruct()
            for t in self.tables:
                tblobj = self.app.db.table("%s.%s" % (self.package, t))
                if tblobj.attributes.get("lookup"):
                    self.has_lookups = True
                else:
                    m.thpage(
                        tblobj.name_plural or tblobj.name_long, table=tblobj.fullname
                    )
            if self.has_lookups:
                m.lookupBranch("Lookup tables", pkg=self.package)
            m.toPython(menupath)
        if os.path.exists(menu_xml_path):
            os.remove(menu_xml_path)

    def write(self, line=None, indent=0):
        line = line or ""
        self.out_file.write("%s%s\n" % (self.option_indent * indent * " ", line))

    def writeHeaders(self):
        self.write("#!/usr/bin/python3")
        self.write("# -*- coding: utf-8 -*-")
        self.write()

    def writeImports(self):
        self.write("from gnr.web.gnrbaseclasses import BaseComponent")
        self.write()

    def writeViewClass(self, tblobj, column_groups):
        self.write("class View(BaseComponent):")
        self.write()
        self.write("def th_struct(self,struct):", indent=1)
        self.write("r = struct.view().rows()", indent=2)
        for group, columns in column_groups.items():
            if group:
                self.write(
                    f"{group[0]}_col_group = r.columnset('{group[0]}', name='{group[1]}')",
                    indent=2,
                )
                for column, size in columns:
                    if self.option_guess_size:
                        self.write(
                            "%s_col_group.fieldcell('%s', width='%iem')"
                            % (group[0], column, size),
                            indent=2,
                        )
                    else:
                        self.write(
                            "%s_col_group.fieldcell('%s')" % (group[0], column),
                            indent=2,
                        )
            else:
                for column, size in columns:
                    if self.option_guess_size:
                        self.write(
                            "r.fieldcell('%s', width='%iem')" % (column, size), indent=2
                        )
                    else:
                        self.write("r.fieldcell('%s')" % column, indent=2)
        self.write()
        self.write("def th_order(self):", indent=1)
        self.write("return '%s'" % columns[0][0], indent=2)
        self.write()
        self.write("def th_query(self):", indent=1)
        searchcol = tblobj.attributes.get("caption_field")

        if not searchcol:
            l = [
                c
                for c in list(tblobj.columns.values())
                if c.attributes.get("dtype") in ("A", "T", "C")
                and not c.attributes.get("_sysfield")
            ]
            if l:
                searchcol = l[0].name
        self.write(
            "return dict(column='%s', op='contains', val='')" % searchcol, indent=2
        )
        self.write()
        self.write()
        self.write()

    def writeFormClass(self, tblobj, columns):
        children = self.getChildrenRelations(tblobj)
        self.write("class Form(BaseComponent):")
        self.write()
        self.write("def th_form(self, form):", indent=1)
        if children:
            self.write("bc = form.center.borderContainer()", indent=2)
            self.write(
                "top = bc.contentPane(region='top',datapath='.record')", indent=2
            )
            self.write(
                "fb = top.formbuilder(cols=%i, border_spacing='4px')"
                % self.option_columns,
                indent=2,
            )
            for column, size, dtype in columns:
                self.write("fb.field('%s')" % column, indent=2)
            if len(children) > 1:
                self.write(
                    "tc = bc.tabContainer(region='center',margin='2px')", indent=2
                )
                for c, mode in children:
                    self.write(
                        "tab_%s = tc.contentPane(title='%s')"
                        % (
                            c.replace("@", ""),
                            (tblobj.name_plural or tblobj.name_long),
                        ),
                        indent=2,
                    )
                    self.write(
                        "tab_%s.%sTableHandler(relation='%s')"
                        % (c.replace("@", ""), mode, c),
                        indent=2,
                    )
            else:
                c, mode = children[0]
                self.write("center = bc.contentPane(region='center')", indent=2)
                self.write("center.%sTableHandler(relation='%s')" % (mode, c), indent=2)
        else:
            self.write("pane = form.record", indent=2)
            self.write(
                "fb = pane.formbuilder(cols=%i, border_spacing='4px')"
                % self.option_columns,
                indent=2,
            )
            for column, size, dtype in columns:
                tag = ""
                if dtype == "X":
                    if isinstance(self.bag_columns["form"], str):
                        tag = ", tag='%s'" % self.bag_columns["form"]
                self.write("fb.field('%s' %s)" % (column, tag), indent=2)

        self.write()
        self.write()
        self.write("def th_options(self):", indent=1)
        hierarchical = tblobj.column("hierarchical_pkey") is not None
        hierarchical_chunk = ""
        if hierarchical:
            hierarchical_chunk = ", hierarchical=True"
        self.write(
            "return dict(dialog_height='400px', dialog_width='600px' %s)"
            % hierarchical_chunk,
            indent=2,
        )

    def getChildrenRelations(self, tblobj):
        result = []
        for relation, j in tblobj.relations.digest("#k,#a.joiner"):
            if j and j["mode"] == "M" and j.get("thmode"):
                result.append((relation, j.get("thmode")))
        return result

    def columnWidthEstimate(self, column):
        """
        Estimates the width of a column based on its data type (dtype) and specified size attributes.

        Description
        -----------
        For text columns ('A' or 'T'), it uses a conversion map
        to determine the appropriate width. For date ('D') and datetime ('DH') columns, it returns
        fixed widths. If the data type is not recognized, it returns a default width.

        Parameters
        ----------
        column : Column
            The column object containing attributes such as dtype and size.

        Returns
        -------
        int
            The calculated width of the column.
        """
        # TODO: Review the LUT and evaluate the use of a formula.
        # Note that the commented formulae seems to be less accurate than the LUT

        MAX_SIZE = 50
        DEFAULT_WIDTH = 7

        sizeWidthMap = {
            1: 2,
            2: 2,
            3: 3,
            4: 4,
            5: 4,
            6: 5,
            7: 5,
            8: 6,
            9: 6,
            10: 6,
            11: 6,
            12: 7,
            13: 7,
            14: 8,
            15: 8,
            16: 9,
            17: 9,
            18: 10,
            19: 10,
            20: 10,
            21: 11,
            22: 11,
            23: 11,
            24: 12,
            25: 12,
            26: 12,
            27: 13,
            28: 13,
            29: 14,
            30: 14,
            31: 15,
            32: 15,
            33: 15,
            34: 16,
            35: 17,
            36: 17,
            37: 18,
            38: 18,
            39: 18,
            40: 19,
            41: 19,
            42: 20,
            43: 20,
            44: 21,
            45: 21,
            46: 22,
            47: 22,
            48: 23,
            49: 23,
            50: 24,
        }

        def handleTextColumn(column):
            try:
                sizeTxt = column.attributes.get("size", "")
            except Exception as e:
                logger.warning(
                    f"Unable to get size attribute for column {column.name}: {e}. Using default width."
                )
                return DEFAULT_WIDTH

            if not sizeTxt:
                logger.warning(
                    f"No size attribute found for column {column.name}. Using default width."
                )
                return DEFAULT_WIDTH

            if ":" in sizeTxt:
                size = int(sizeTxt.split(":")[1])
            else:
                size = int(sizeTxt)

            if size > max(sizeWidthMap):
                logger.info(
                    f"Column {column.name} has a size greater than the maximum. Topping to max handled value."
                )
                return sizeWidthMap[MAX_SIZE]
            # LUT conversion
            return sizeWidthMap[size]

            # ChatGPT 4o conversion
            # return round(0.429 * size + 1.709)

            # ChatGPT o3-mini-high conversion
            # return round(0.45 * size + 1.55)

            # Deepseek conversion
            # return round(0.44 * size + 1.56)

            # Claude conversion
            # return floor(2.8 * size^0.45)

        typesHandler = {
            "A": handleTextColumn,  # Varchar
            "T": handleTextColumn,  # Text
            "C": handleTextColumn,  # Chars
            "D": 6,  # Date
            "H": 4,  # Time
            "DH": 9,  # DateTime
            "DHZ": 12,  # DateTime + TimeZone
            "B": 3,  # Boolean
            "N": 7,  # Numeric
            "L": 7,  # Numeric (long)
            "I": 7,  # Numeric (int)
            "R": 7,  # Numeric (float)
            "X": 10,  # Bag
        }
        handler = typesHandler.get(column.dtype, 7)
        if callable(handler):
            return handler(column)
        return handler

    def createResourceFile(self, table):
        resourceFolder = os.path.join(self.packageFolder, "resources", "tables", table)
        if not os.path.exists(resourceFolder):
            os.makedirs(resourceFolder, exist_ok=True)
        name = "th_%s.py" % table
        path = (
            os.path.join(resourceFolder, name)
            if not self.option_output
            else self.option_output
        )
        if os.path.exists(path) and not self.option_force:
            logger.warning(
                "%s exist: will be skipped, use -f/--force to force replace", name
            )
            return

        column_groups = defaultdict(list)
        columns = []
        tbl_obj = self.app.db.table("%s.%s" % (self.package, table))

        for col_name, column in tbl_obj.columns.items():

            # Skip id and internal columns
            if (
                col_name == "id"
                or column.attributes.get("_sysfield")
                or col_name.startswith("__")
                or column.dtype == "O"
            ):
                continue

            logger.debug(f"Processing column {column.name}")
            if self.option_guess_size:
                width = self.columnWidthEstimate(column)
                logger.debug(f"Estimated width for column {column.name}: {width}em")
            else:
                width = 7

            col_group_label = column.attributes.get("colgroup_label", None)

            if col_group_label is None:
                col_group = ""
            else:
                col_group = (
                    col_group_label,
                    column.attributes.get("colgroup_name_long"),
                )

            column_groups[col_group].append((column.name, width))
            columns.append((column.name, width))

        if not columns:
            logger.error("Table %s does not contain any valid column", table)
            return

        try:
            with open(path, "w") as out_file:
                self.out_file = out_file
                self.writeHeaders()
                self.writeImports()
                self.writeViewClass(tbl_obj, column_groups)
                self.writeFormClass(tbl_obj, columns)
                logger.info("%s created", name)
        except Exception as e:
            logger.exception(f"Error creating output file: {path}. Error: {e}")
