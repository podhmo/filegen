# -*- coding:utf-8 -*-
import sys
import contextlib
import os.path
import shutil
if int(sys.version[0]) >= 3:
    from io import StringIO as IO
else:
    from io import BytesIO as IO
from collections import namedtuple
from prestring.python import PythonModule
import logging
logger = logging.getLogger(__name__)


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
        writer = IO()
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
        if not os.path.exists(str(d.path)):
            logger.info('[d] create: %s', d.path)
            os.mkdir(str(d.path))

    def branch_directory(self, d):
        self.emit_directory(d)
        for f in d.files:
            if isinstance(f, Directory):
                self.branch_directory(f)
            else:
                self.emit_file(f)

    def emit_file(self, f):
        logger.info('[f] create: %s', f.path)
        with open(str(f.path), "w") as wf:
            f.io.seek(0)
            shutil.copyfileobj(f.io, wf)

    def emit(self, fg):
        self.branch_directory(fg.frame[0])


class PythonModuleMaker(DirectoryMaker):
    def emit_directory(self, d):
        super(PythonModuleMaker, self).emit_directory(d)
        initfile = os.path.join(str(d.path), "__init__.py")
        logger.info('[f] create: %s', initfile)
        if not os.path.exists(initfile):
            with open(initfile, "w"):
                pass


class CodeGenerator(object):
    def __init__(self, fg, varname="rootpath", m=None):
        self.fg = fg
        self.rootpath = str(fg.frame[0].path)
        self.varname = varname
        self.m = m or PythonModule(import_unique=True)

    def virtualpath(self, f):
        self.m.from_("os.path", "join")
        return "join({}, '{}')".format(self.varname, str(f.path).replace(self.rootpath, "").lstrip("/"))

    def emit(self, io=sys.stdout):
        m = self.m
        m.import_("sys")
        m.import_("logging")
        m.stmt("logger = logging.getLogger(__name__)")
        m.sep()

        with m.def_("gen", self.varname):
            self.branch_directory(fg.frame[0])
        with m.main():
            m.stmt("logging.basicConfig(level=logging.INFO)")
            m.stmt("gen(sys.argv[1])")
        return io.write(str(m))

    def branch_directory(self, d):
        self.emit_directory(d)
        for f in d.files:
            if isinstance(f, Directory):
                self.branch_directory(f)
            else:
                self.emit_file(f)

    def emit_directory(self, d):
        m = self.m
        m.from_("os.path", "exists")
        m.from_("os", "mkdir")
        with m.unless("exists({})".format(self.virtualpath(d))):
            m.stmt("logger.info('[d] create: %s', {})".format(self.virtualpath(d)))
            m.stmt("mkdir({})".format(self.virtualpath(d)))

    def emit_file(self, f):
        m = self.m
        m.stmt("logger.info('[f] create: %s', {})".format(self.virtualpath(f)))
        with m.with_("open({}, 'w')".format(self.virtualpath(f)), as_="wf"):
            f.io.seek(0)
            m.stmt("wf.write('{}')".format(f.io.read()))


class FilegenApplication(object):
    def parse(self, argv):
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--action", choices=["file", "python", "string", "code", "default"], default="default")
        parser.add_argument("root", nargs="?", default=".")
        return parser.parse_args(argv)

    def run(self, fg, *args, **kwargs):
        import sys
        args = self.parse(sys.argv[1:])
        fg.change(args.root)
        if args.action == "python":
            return PythonModuleMaker().emit(fg)
        elif args.action == "file":
            return DirectoryMaker().emit(fg)
        elif args.action == "code":
            return CodeGenerator(fg).emit()
        else:
            return Writer().emit(fg)

if __name__ == "__main__":
    fg = Filegen()
    with fg.dir("foo"):
        with fg.file("bar.py") as wf:
            wf.write("# this is comment file")
        with fg.file("readme.txt") as wf:
            wf.write(u"いろはにほへと　ちりぬるを わかよたれそ　つねならむ うゐのおくやま　けふこえて あさきゆめみし　ゑひもせす")
    FilegenApplication().run(fg)
