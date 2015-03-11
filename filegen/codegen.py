# -*- coding:utf-8 -*-
import sys
import inspect
import contextlib
from prestring.python import PythonModule
from filegen import asking


@contextlib.contextmanager
def snatch_ask_context(cache):
    try:
        default = asking.get_ask_string_cache()
        asking.set_ask_string_cache(cache)
        yield
    finally:
        asking.set_ask_string_cache(default)


class Gensym(object):
    def __init__(self, i=0, prefix="_G"):
        self.prefix = prefix
        self.i = i

    def __call__(self):
        value = "{}{}".format(self.prefix, self.i)
        self.i += 1
        return value


class Wrapper(str):
    def __init__(self, v):
        self.v = v

    def getvalue(self):
        return self.v


class AskStringCacheCodeGeneration(object):
    def __init__(self, m):
        self.description_map = {}
        self.default_map = {}
        self.cache = {}
        self.m = m
        self.is_import_asking = False
        self.toplevel = m.submodule()
        self.variables = m.submodule()
        self.gensym = Gensym(0)
        self.hooks = []

    def __getitem__(self, name):
        try:
            return self.cache[name]
        except KeyError:
            return self.load(name)

    def import_asking_module(self):
        self.is_import_asking = True
        with open(inspect.getsourcefile(asking)) as rf:
            self.toplevel.stmt(rf.read())

    def load(self, name):
        if not self.is_import_asking:
            self.import_asking_module()

        stmt = ["AskString('{}'".format(name)]
        if name in self.description_map:
            stmt.append(", description='{}'".format(self.description_map[name]))
        if name in self.default_map:
            stmt.append(", default={!r}".format(self.default_map[name]))
        stmt.append(")")

        value = self.cache[name] = self.will_replacement(stmt)
        return value

    def will_replacement(self, stmt):
        varname = self.gensym()
        self.variables.stmt("{} = {}".format(varname, "".join(stmt)))
        pattern = "<<{}>>".format(varname)
        self._append_replace(pattern, 'str({})'.format(varname))
        return pattern

    def _append_replace(self, pat, rep):
        self.hooks.append(lambda x: "{}.replace('{}', {})".format(x, pat, rep))

    def add_description(self, name, description):
        self.description_map[name] = description

    def add_default(self, name, default):
        self.default_map[name] = default


class LocalVariablesManager(object):
    def __init__(self, m):
        self.m = m
        self.local_variables = m.submodule()
        self.file_gensym = Gensym(0, prefix="file")
        self.val_gensym = Gensym(0, prefix="val")
        self.cache = {}

    def file(self, k, stmt):
        return self.get(self.file_gensym, k, stmt)

    def val(self, k, stmt):
        return self.get(self.val_gensym, k, stmt)

    def get(self, gensym, k, stmt):
        try:
            return self.cache[(gensym, k)]
        except KeyError:
            return self.load(gensym, k, stmt)

    def load(self, gensym, k, stmt):
        for hook in asking.get_ask_string_cache().hooks:
            stmt = hook(stmt)
        varname = gensym()
        self.local_variables.stmt("{} = {}".format(varname, stmt))
        self.cache[(gensym, k)] = varname
        return varname


class CodeGenerator(object):
    def __init__(self, fg, rootpath, varname="rootpath", m=None):
        self.fg = fg
        self.varname = varname
        if rootpath == ".":
            rootpath = "./"
        self.rootpath = rootpath
        self.m = m or PythonModule(import_unique=True)
        self.toplevel = self.m.submodule()
        self.tmpval_manager = None

    def virtualpath(self, f):
        self.toplevel.from_("os.path", "join")
        value = "join({}, '{}')".format(self.varname, str(f.path).replace(self.rootpath, "").lstrip("/"))
        return self.tmpval_manager.file(value, value)

    def emit(self, io=sys.stdout):
        m = self.m
        with snatch_ask_context(AskStringCacheCodeGeneration(m)):
            if callable(self.fg):
                self.fg = self.fg()
            self.fg.change(self.rootpath)

            self.toplevel.import_("sys")
            self.toplevel.import_("logging")
            m.stmt("logger = logging.getLogger(__name__)")
            m.sep()

            with m.def_("gen", self.varname):
                self.tmpval_manager = LocalVariablesManager(self.m)
                self.branch_directory(self.fg.frame[0])
            with m.main():
                m.stmt("logging.basicConfig(level=logging.INFO)")
                m.stmt("gen(sys.argv[1])")
        return io.write(str(m))

    def branch_directory(self, d):
        self.emit_directory(d)
        for f in d.files:
            if hasattr(f, "io"):
                self.emit_file(f)
            else:
                self.branch_directory(f)

    def emit_directory(self, d):
        m = self.m
        self.toplevel.from_("os.path", "exists")
        self.toplevel.from_("os", "mkdir")
        with m.unless("exists({})".format(self.virtualpath(d))):
            m.stmt("logger.info('[d] create: %s', {})".format(self.virtualpath(d)))
            m.stmt("mkdir({})".format(self.virtualpath(d)))

    def emit_file(self, f):
        m = self.m
        m.stmt("logger.info('[f] create: %s', {})".format(self.virtualpath(f)))
        with m.with_("open({}, 'w')".format(self.virtualpath(f)), as_="wf"):
            f.io.seek(0)
            value = f.io.read()
            stmt = self.tmpval_manager.val(value, "'''{}'''".format(value))
            m.stmt("wf.write({})".format(stmt))
