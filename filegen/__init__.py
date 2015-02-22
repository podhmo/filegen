# -*- coding:utf-8 -*-
import sys
import contextlib
import os.path
import shutil
from io import StringIO
from collections import namedtuple

Directory = namedtuple("Directory", "name path files")
File = namedtuple("File", "name path io")


class LazyPath(object):
    def __init__(self, values):
        self.values = values

    def __str__(self):
        return os.path.join(*[str(x) for x in self.values])


class LazyString(object):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def change(self, value):
        self.value = value


class Filegen(object):
    def __init__(self, curdir="."):
        self.curdir = LazyString(curdir)
        self.scope = [self.curdir]
        self.frame = [Directory(name=self.curdir, path=self.curdir, files=[])]

    def fullpath(self):
        return LazyPath(self.scope[:])

    @contextlib.contextmanager
    def dir(self, name):
        self.scope.append(name)
        self.frame.append(Directory(name=name, path=self.fullpath(), files=[]))
        yield
        d = self.frame.pop()
        self.frame[-1].files.append(d)
        self.scope.pop()

    @contextlib.contextmanager
    def file(self, name):
        self.scope.append(name)
        writer = StringIO()
        yield writer
        self.frame[-1].files.append(File(name=name, path=self.fullpath(), io=writer))
        self.scope.pop()

    def to_string(self, curdir=None, limit=80):
        if curdir is not None:
            self.change(curdir)
        return Writer(limit).emit(self)

    def to_python_module(self, curdir=None, overwrite=True):
        if curdir is not None:
            self.change(curdir)
        return PythonModuleMaker(overwrite).emit(self)

    def to_directory(self, curdir=None, overwrite=True):
        if curdir is not None:
            self.change(curdir)
        return DirectoryMaker(overwrite).emit(self)

    def change(self, curdir):
        self.curdir.change(curdir)


class Writer(object):
    def __init__(self, limit=80):
        self.limit = limit

    def output(self, content):
        sys.stdout.write(content)
        sys.stdout.write("\n")

    def emit_directory(self, d, indent):
        self.output("{}d:{}".format(" " * indent, d.path))
        for f in d.files:
            if isinstance(f, Directory):
                self.emit_directory(f, indent + 1)
            else:
                self.emit_file(f, indent + 1)

    def emit_file(self, f, indent):
        padding = " " * indent
        content_padding = "  " + padding
        self.output("{}f:{}".format(padding, f.path))
        self.output(content_padding + ("\n" + content_padding).join(f.io.getvalue()[:self.limit].split("\n")))

    def emit(self, fg):
        self.emit_directory(fg.frame[0], 0)


class DirectoryMaker(object):
    def __init__(self, overwrite=True):
        self.overwrite = overwrite

    def output(self, content):
        sys.stdout.write(content)
        sys.stdout.write("\n")

    def emit_directory(self, d):
        if not os.path.exists(str(str(d.path))):
            os.mkdir(str(str(d.path)))

    def branch_directory(self, d):
        self.emit_directory(d)
        for f in d.files:
            if isinstance(f, Directory):
                self.branch_directory(f)
            else:
                self.emit_file(f)

    def emit_file(self, f):
        with open(str(f.path), "w") as wf:
            f.io.seek(0)
            shutil.copyfileobj(f.io, wf)

    def emit(self, fg):
        self.branch_directory(fg.frame[0])


class PythonModuleMaker(DirectoryMaker):
    def emit_directory(self, d):
        super(PythonModuleMaker, self).emit_directory(d)
        initfile = os.path.join(str(d.path), "__init__.py")
        if not os.path.exists(initfile):
            with open(initfile, "w"):
                pass


class FilegenApplication(object):
    def run(self, method, *args, **kwargs):
        import sys
        try:
            curdir = sys.argv[1]
        except IndexError:
            curdir = os.getcwd()
        method(curdir=curdir, **kwargs)

if __name__ == "__main__":
    fg = Filegen()
    with fg.dir("foo"):
        with fg.file("bar.py") as wf:
            wf.write("# this is comment file")
        with fg.file("readme.txt") as wf:
            wf.write("# foo")
    FilegenApplication().run(fg.to_string)
