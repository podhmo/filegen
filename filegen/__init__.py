# -*- coding:utf-8 -*-
import sys
import contextlib
import os.path
if int(sys.version[0]) >= 3:
    from io import StringIO as IO
else:
    from io import BytesIO as IO
from collections import namedtuple
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
            if hasattr(f, "io"):
                self.emit_file(f, indent + 1)
            else:
                self.emit_directory(f, indent + 1)

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
            os.makedirs(str(d.path))

    def branch_directory(self, d):
        self.emit_directory(d)
        for f in d.files:
            if hasattr(f, "io"):
                self.emit_file(f)
            else:
                self.branch_directory(f)

    def emit_file(self, f):
        logger.info('[f] create: %s', f.path)
        with open(str(f.path), "w") as wf:
            f.io.seek(0)
            wf.write(f.io.read())

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


class FilegenApplication(object):
    default_action = "default"

    def parse(self):
        import argparse
        parser = argparse.ArgumentParser()
        choices = ["file", "python", "string", "code", "default"]
        parser.add_argument("--action", choices=choices, default=self.default_action)
        parser.add_argument("root", nargs="?", default=".")
        return parser.parse_args()

    def run(self, fg, *args, **kwargs):
        logging.basicConfig(level=logging.INFO)
        args = self.parse()

        if args.action == "python":
            if callable(fg):
                fg = fg()
            fg.change(args.root)
            return PythonModuleMaker().emit(fg)
        elif args.action == "file" or args.action == "default":
            if callable(fg):
                fg = fg()
            fg.change(args.root)
            return DirectoryMaker().emit(fg)
        elif args.action == "code":
            from filegen.codegen import CodeGenerator
            return CodeGenerator(fg, args.root).emit()
        else:
            if callable(fg):
                fg = fg()
            fg.change(args.root)
            return Writer().emit(fg)


if __name__ == "__main__":
    def closure():
        from filegen.asking import AskString
        fg = Filegen()
        with fg.dir("foo"):
            with fg.file(AskString("comment-file-name", default="comment.txt")) as wf:
                wf.write("# {} is wrote\n\n".format(AskString("yourname", description="what is your name?", default="foo")))
                wf.write("# this is comment file")
            with fg.file("readme.txt") as wf:
                wf.write("{} is wrote\n\n".format(AskString("yourname", description="hmm", default="foo")))
                wf.write(u"いろはにほへと　ちりぬるを わかよたれそ　つねならむ うゐのおくやま　けふこえて あさきゆめみし　ゑひもせす")
        return fg
    FilegenApplication().run(closure)
