filegen
========================================

.. code-block:: python

  fg = Filegen()
  with fg.dir("foo"):
      with fg.file("hello.txt") as wf:
          wf.write("hello")

      with fg.dir("bar"):
          with fg.file("x") as wf:
              wf.write("x")

      with fg.file("bye.txt") as wf:
          wf.write("bye")

  fg.to_python_module()


generated files ::

  foo/
  ├── __init__.py
  ├── bar
  │   ├── __init__.py
  │   └── x
  ├── bye.txt
  └── hello.txt

making file-structure generating application
----------------------------------------

Using `FilegenApplication` for creating file structure generating command.
Writing a script file such as below.

.. code-block:: python

  # myscript.py
  if __name__ == "__main__":
      from filegen import Filegen, FilegenApplication

      fg = Filegen()
      with fg.dir("foo"):
          with fg.file("bar.py") as wf:
              wf.write("# this is comment file")
          with fg.file("readme.txt") as wf:
              wf.write("# foo")
      FilegenApplication().run(fg)

then.

.. code-block:: shell

  $ python myscript.py --action=string /tmp
  d:/tmp
   d:/tmp/foo
    f:/tmp/foo/bar.py
      # this is comment file
   d:/tmp/foo
    f:/tmp/foo/readme.txt
      # foo

  $ python myscript.py --action=string /foo/bar
  d:/foo/bar
   d:/foo/bar/foo
    f:/foo/bar/foo/bar.py
      # this is comment file
   d:/foo/bar/foo
    f:/foo/bar/foo/readme.txt
      # foo

