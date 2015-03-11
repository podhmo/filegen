import unittest
from evilunit import test_target


@test_target("filegen.scanning:MakoTemplateScanner")
class Tests(unittest.TestCase):
    def _makeOne(self):
        from filegen.scanning import ScannerContext
        return self._getTarget()(ScannerContext())

    def test_it(self):
        C = self._makeOne()
        template = u"""
        <% two = 1 + 1%>
        ${two}
        ${two + 2}
        ${two + three * 3}
        ${not one}
        ${four("xxx", five)}
        """
        result = C.scan(template)
        self.assertEqual(list(sorted(result)), ["five", "one", "three", "two"])
