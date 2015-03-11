# -*- coding:utf-8 -*-
from filegen import Filegen
from filegen.asking import AskString


def gen():
    fg = Filegen()
    yourname = str(AskString("yourname", description="what is your name", default="foo"))
    YOURNAME = yourname.upper()

    with fg.dir("greeting"):
        with fg.file("hello.txt") as wf:
            wf.write("{}: hello.".format(yourname))
        with fg.file("bye.txt") as wf:
            wf.write("{}: bye.".format(yourname))
        with fg.file("is_angry.txt") as wf:
            wf.write("{}: HEY!".format(YOURNAME))
    return fg

if __name__ == "__main__":
    from filegen import FilegenApplication
    FilegenApplication().run(gen)
