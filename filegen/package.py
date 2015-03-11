# -*- coding:utf-8 -*-
import os.path
from filegen import Filegen
from prestring.python import PythonModule
from filegen.asking import AskString


def gen():
    package_name = str(AskString("package", description="package name", default="foo-bar"))
    module_name = package_name.replace("-", "_")
    version = str(AskString("version", description="version", default="0.0.0"))
    test_module_name = "{}.tests".format(module_name)

    fg = Filegen()
    with fg.dir(package_name):
        with fg.file(".gitignore") as wf:
            with open(os.path.join(os.path.dirname(__file__), "gitignore.txt")) as rf:
                wf.write(rf.read())
        with fg.file("README.rst") as wf:
            wf.write(package_name)
            wf.write("========================================")
        with fg.file("CHANGES.rst") as wf:
            pass
        with fg.dir(module_name):
            with fg.file("__init__.py"):
                pass
            with fg.dir("tests"):
                with fg.file("__init__.py"):
                    pass
        with fg.file("setup.py") as wf:
            m = PythonModule()
            m.import_("os")
            m.from_("setuptools", "setup")
            m.from_("setuptools", "find_packages")
            m.stmt("here = os.path.abspath(os.path.dirname(__file__))")
            m.sep()
            with m.try_():
                with m.with_("open(os.path.join(here, 'README.rst')) as f"):
                    m.stmt("README = f.read()")
                with m.with_("open(os.path.join(here, 'CHANGES.rst')) as f"):
                    m.stmt("CHANGES = f.read()")
            with m.except_("IOError"):
                m.stmt("README = CHANGES = ''")
            m.sep()
            m.stmt("install_requires = []")
            m.stmt("docs_extras = []")
            m.stmt("tests_requires = []")
            m.stmt("testing_extras = tests_requires + []")
            m.sep()
            with m.hugecall("setup") as r:
                r.add(name=repr(package_name))
                r.add(version=repr(version))
                r.add(classifiers=[
                    "Programming Language :: Python",
                    "Programming Language :: Python :: Implementation :: CPython",
                ])
                r.add(keywords=repr(""))
                r.add(author=repr(""))
                r.add(author_email=repr(""))
                r.add(url=repr(""))
                r.add(packages="find_packages(exclude=['{}'])".format(test_module_name))
                r.add(include_package_data=True)
                r.add(zip_safe=False)
                r.add(install_requires="install_requires")
                r.add(extras_require="""\
{
   'testing': testing_extras,
   'docs': docs_extras}""")
                r.add(tests_require="tests_requires")
                r.add(test_suite=repr(test_module_name))
                r.add(entry_points=repr(""))
            wf.write(str(m))
    return fg


if __name__ == "__main__":
    from filegen import FilegenApplication
    FilegenApplication().run(gen)
