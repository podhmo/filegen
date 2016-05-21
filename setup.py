# -*- coding:utf-8 -*-

import os


from setuptools import setup, find_packages
here = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(here, 'README.rst')) as f:
        README = f.read()
    with open(os.path.join(here, 'CHANGES.txt')) as f:
        CHANGES = f.read()
except IOError:
    README = CHANGES = ''


install_requires = [
    'prestring'
]


docs_extras = [
]

tests_require = [
]

testing_extras = tests_require + [
]

codegen_extras = [
    'prestring',
]

setup(name='filegen',
      version='0.2.1',
      description='file structure generator with onefile script',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
          "Programming Language :: Python",
          "Programming Language :: Python :: Implementation :: CPython",
      ],
      keywords='filegen, file generation, scaffold',
      author="podhmo",
      author_email="",
      url="https://github.com/podhmo/filegen",
      license="mit",
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      extras_require={
          'testing': testing_extras,
          'docs': docs_extras,
          'codegen': codegen_extras
      },
      tests_require=tests_require,
      test_suite="filegen.tests",
      entry_points="""
""")
