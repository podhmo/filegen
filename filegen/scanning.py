# -*- coding:utf-8 -*-
import re
import os.path
import logging
import ast
from mako.lexer import Lexer
from mako.parsetree import Expression
from collections import namedtuple
from prestring import INDENT, UNINDENT
logger = logging.getLogger(__name__)
_File = namedtuple("_File", "name content is_template")
_Directory = namedtuple("_Directory", "name files")


def parse(template, encoding="utf-8"):
    return Lexer(template, input_encoding=encoding).parse()


class Scanner(object):
    def __init__(self):
        self.context = ScannerContext()
        self.file_scanner = MakoTemplateScanner(self.context)
        self.name_scanner = NameScanner(self.context, re.compile("\+([^\+]+)\+"))

    def is_target_file(self, f):
        return f.endswith(".tmpl")

    def scan(self, root):
        d = self.branch_directory("", root)
        self.context.roots.append(d)
        return d

    def branch_directory(self, prefix, dirname):
        d = self.scan_directory(prefix, dirname)
        fullpath = os.path.join(prefix, dirname)
        for f in os.listdir(fullpath):
            if f == "." or f == "..":
                break
            if os.path.isdir(os.path.join(fullpath, f)):
                d.files.append(self.branch_directory(fullpath, f))
            else:
                d.files.append(self.scan_file(fullpath, f))
        return d

    def scan_directory(self, prefix, dirname):
        container = _Directory(dirname, [])
        self.name_scanner.scan(dirname)
        return container

    def scan_file(self, prefix, filename):
        self.name_scanner.scan(filename)
        fullpath = os.path.join(prefix, filename)
        with open(fullpath) as rf:
            try:
                f = _File(filename, rf.read(), self.is_target_file(fullpath))
                if self.is_target_file(fullpath):
                    self.file_scanner.scan(f.content)
                return f
            except:
                pass


class NameScanner(object):
    def __init__(self, context, rx):
        self.context = context
        self.rx = rx

    def scan(self, name):
        varnames = self.rx.findall(name)
        for m in varnames:
            self.context.varnameset.add(m)
        self.context.name_to_vars_map[name] = varnames


class ScannerContext(object):
    def __init__(self):
        self.codelist = []
        self.varnameset = set()
        self.name_to_vars_map = {}
        self.content_to_vars_map = {}
        self.roots = []


class MakoTemplateScanner(object):
    def __init__(self, context):
        self.varname_collector = VarNameCollector()
        self.context = context

    def _traverse(self, node, r):
        if hasattr(node, "nodes"):
            for n in node.nodes:
                self._traverse(n, r)
        if isinstance(node, Expression):
            r.append(node)

    def scan(self, text, name=None):  # todo: handle name
        r = []
        self._traverse(parse(text), r)
        astlist = [expr.code.code for expr in r]
        self.varname_collector.collectall(astlist, self.context.varnameset)
        self.context.codelist.extend(astlist)
        return self.context.varnameset


class VarNameCollector(object):
    def collectall(self, expressions, s):
        for expr in expressions:
            self.collect(expr, s)
        return list(s)

    def collect(self, expr, s):
        m = ast.parse(expr)
        for line in m.body:
            self.traverse(line.value, s)
        return s

    def traverse(self, v, s):
        if isinstance(v, ast.Name):
            s.add(v.id)
        elif isinstance(v, ast.BinOp):
            self.traverse(v.left, s)
            self.traverse(v.right, s)
        elif isinstance(v, ast.UnaryOp):
            self.traverse(v.operand, s)
        elif isinstance(v, ast.Attribute):
            self.traverse(v.value, s)
        elif isinstance(v, ast.Call):
            for e in v.args:
                self.traverse(e, s)


class Walker(object):
    def __init__(self, m, filename, wf="wf"):
        self.top = m.submodule()
        self.bottom = m.submodule()
        self.filename = filename
        self.wf = wf
        self.in_expression = False
        self.in_toplevel = False

    @property
    def m(self):
        if self.in_toplevel:
            return self.top
        else:
            return self.bottom

    def walk(self, node):
        method = getattr(self, "walk_{}".format(node.__class__.__name__.lower()))
        return method(node)

    def walk_templatenode(self, node):
        for sub in node.nodes:
            self.walk(sub)

    def walk_text(self, node):
        self.m.stmt("{}.write('''{}''')".format(self.wf, node.content))

    def walk_expression(self, node):
        self.in_expression = True
        self.walk(node.code)
        self.in_expression = False

    def walk_pythoncode(self, node):
        if self.in_expression:
            code = node.code
            if code.strip() == "caller.body()":
                self.m.stmt("yield")
            else:
                for e in node.undeclared_identifiers:
                    code = code.replace(e, "''' + str(AskString('{}')) + '''".format(e))
                code = "{}.write('''{}''')".format(self.wf, code)
                code = code.replace("'''''' + ", "").replace(" + ''''''", "")
                self.m.stmt(code)
        else:
            for line in node.code.split("\n"):
                self.m.stmt(line)

    def walk_code(self, node):
        self.walk(node.code)

    def walk_controlline(self, node):
        if node.is_primary:
            if not node.isend:
                self.m.stmt(node.text)
                self.m.append(INDENT)
            else:
                self.m.append(UNINDENT)
        else:
            self.m.append(UNINDENT)
            self.m.stmt(node.text)
            self.m.append(INDENT)

    def walk_deftag(self, node):
        self.in_toplevel = True
        if node.decorator:
            self.m.stmt("@{}".format(node.decorator))
        self.m.from_("contextlib", "contextmaager")
        self.m.stmt("@contextmanager")
        self.m.stmt("def {}:".format(node.attributes["name"]))
        with self.m.scope():
            for sub in node.nodes:
                self.walk(sub)
        self.m.sep()
        self.in_toplevel = False

    def walk_comment(self, node):
        for line in node.text.split("\n"):
            self.m.stmt("wf.write('# {}\n')".format(line))

    def walk_callnamespacetag(self, node):
        with self.m.with_("{}()".format(node.keyword.replace("self:", ""))):
            for sub in node.nodes:
                self.walk(sub)


from prestring.python import PythonModule
import inspect
from filegen import asking


if __name__ == "__main__":
    import sys
    #root = sys.argv[1]
    scanner = Scanner()
    d = scanner.scan("/tmp/moo")
    m = PythonModule()

    # with open(inspect.getsourcefile(asking)) as rf:
    #     m.stmt(rf.read())

    def replace(name):
        varname_list = scanner.context.name_to_vars_map[name]
        if name.endswith(".tmpl"):
            name = name[:-5]
        if not varname_list:
            return "'{}'".format(name)
        else:
            for vname in varname_list:
                name = vname.replace(vname, "' + str({}) + '".format(vname))
            return "'{}'".format(name)

    def walk(m, d):
        if isinstance(d, _File):
            if d.is_template:
                with m.with_("fg.file({})".format(replace(d.name)), as_="wf"):
                    walker = Walker(m, "wf")
                    walker.walk(parse(d.content))
            else:
                with m.with_("fg.file({})".format(replace(d.name)), as_="wf"):
                    m.stmt("wf.write('''{}''')".format(d.content))
        else:
            with m.with_("fg.dir({})".format(replace(d.name))):
                for f in d.files:
                    if f is None:
                        continue
                    walk(m, f)
                else:
                    m.pass_()

    with m.def_("gen"):
        m.submodule().from_("filegen.asking", "AskString")
        for name in scanner.context.varnameset:
            m.stmt("{name} = AskString('{name}')".format(name=name))
        m.sep()

        m.from_("filegen", "Filegen")
        m.stmt("fg = Filegen()")
        for f in d.files:
            walk(m, f)
        m.return_("fg")

    with m.main():
        m.submodule().from_("filegen", "FilegenApplication")
        m.stmt("FilegenApplication().run(gen)")

    print(m)
