import os


class AppPaths:
    def __init__(self, root_path):
        self._root_path = root_path

    def get_local_path(self, *args):
        path = str(self._root_path)
        for arg in args:
            path = os.path.join(path, arg)
        return path