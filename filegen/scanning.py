# -*- coding:utf-8 -*-
import re
import os.path
import logging
import ast
from mako.lexer import Lexer
from mako.parsetree import Expression
logger = logging.getLogger(__name__)


class Scanner(object):
    def __init__(self):
        self.context = ScannerContext()
        self.file_scanner = MakoTemplateScanner(self.context)
        self.name_scanner = NameScanner(self.context, re.compile("\+([^\+]+)\+"))

    def is_target_file(self, f):
        return f.endswith(".tmpl")

    def scan(self, root):
        for r, ds, fs in os.walk(root):
            self.name_scanner.scan(r)
            for d in ds:
                self.name_scanner.scan(d)
            for f in fs:
                self.name_scanner.scan(f)
                if self.is_target_file(f):
                    with open(os.path.join(r, f)) as rf:
                        self.file_scanner.scan(rf.read())


class NameScanner(object):
    def __init__(self, context, rx):
        self.context = context
        self.rx = rx

    def scan(self, name):
        for m in self.rx.findall(name):
            self.context.varnameset.add(m)


class ScannerContext(object):
    def __init__(self):
        self.codelist = []
        self.varnameset = set()


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
        self._traverse(Lexer(text, input_encoding="utf-8").parse(), r)
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
