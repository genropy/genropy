import os, os.path


class ProjectMaker(object):
    """Handle the autocreation of a package.

    To autocreate a package, please type in your console::

        gnrmkpackage packagename

    where ``packagename`` is the name of your ``package`` folder."""

    def __init__(self, project_name, base_path=None):
        self.project_name = project_name
        self.base_path = base_path or "."

    def do(self):
        """Create the project path with its subfolders paths: the path of the ``packages`` folder,
        the path of the ``sites`` folder, the path of the ``instances`` folder and the path of the
        ``resources`` folder."""
        self.project_path = os.path.join(self.base_path, self.project_name)
        self.packages_path = os.path.join(self.project_path, "packages")
        self.instances_path = os.path.join(self.project_path, "instances")
        for path in (self.project_path, self.packages_path, self.instances_path):
            if not os.path.isdir(path):
                os.makedirs(path, exist_ok=True)
