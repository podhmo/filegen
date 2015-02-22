# -*- coding:utf-8 -*-
import sys
import contextlib
import os.path
import shutil
from io import StringIO
from collections import namedtuple

Directory = namedtuple("Directory", "name path files")
File = namedtuple("File", "name path io")


class Filegen(object):
    def __init__(self, curdir="."):
        self.scope = [curdir]
        self.frame = [Directory(name=curdir, path=curdir, files=[])]

    def fullpath(self):
        return os.path.join(*self.scope)

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

    def write(self, limit=80):
        return Writer(limit).emit(self)

    def to_python_module(self, overwrite=True):
        return PythonModuleMaker(overwrite).emit(self)

    def to_directory(self, overwrite=True):
        return DirectoryMaker(overwrite).emit(self)


class Writer(object):
    def __init__(self, limit=80):
        self.limit = limit

    def output(self, content):
        sys.stdout.write(content)
        sys.stdout.write("\n")

    def emit_directory(self, d, indent):
        for f in d.files:
            self.output("{}d:{}".format(" " * indent, d.path))
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
        if not os.path.exists(d.path):
            os.mkdir(d.path)

    def branch_directory(self, d):
        self.emit_directory(d)
        for f in d.files:
            if isinstance(f, Directory):
                self.branch_directory(f)
            else:
                self.emit_file(f)

    def emit_file(self, f):
        with open(f.path, "w") as wf:
            shutil.copyfileobj(f.io, wf)

    def emit(self, fg):
        self.branch_directory(fg.frame[0])


class PythonModuleMaker(DirectoryMaker):
    def emit_directory(self, d):
        super(PythonModuleMaker, self).emit_directory(d)
        initfile = os.path.join(d.path, "__init__.py")
        if not os.path.exists(initfile):
            with open(initfile, "w"):
                pass
