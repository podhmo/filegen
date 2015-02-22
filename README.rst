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
