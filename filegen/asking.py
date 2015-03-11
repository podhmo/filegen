import sys


class AskStringCache(object):
    prompt = "{varname} ({description})[{default!r}]:"

    def __init__(self, inp=sys.stdin, err=sys.stderr):
        self.description_map = {}
        self.default_map = {}
        self.cache = {}
        self.inp = inp
        self.err = err
        self.hooks = []

    def __getitem__(self, name):
        try:
            return self.cache[name]
        except KeyError:
            return self.load(name)

    def load(self, name):
        description = self.description_map.get(name, "")
        default = self.default_map.get(name)
        self.err.write(self.prompt.format(varname=name, description=description, default=default))
        self.err.flush()
        value = self.inp.readline().rstrip() or self.default_map.get(name, "")
        self.cache[name] = value
        return value

    def add_description(self, name, description):
        self.description_map[name] = description

    def add_default(self, name, default):
        self.default_map[name] = default


_ask_string_cache = AskStringCache()


def get_ask_string_cache():
    global _ask_string_cache
    return _ask_string_cache


def set_ask_string_cache(cache):
    global _ask_string_cache
    _ask_string_cache = cache


class AskString(object):
    def __init__(self, name, description=None, default=None, cache=None):
        self.cache = cache or get_ask_string_cache()
        self.name = name
        if description is not None:
            self.cache.add_description(name, description)
        if default is not None:
            self.cache.add_default(name, default)

    def __str__(self):
        return self.cache[self.name]
