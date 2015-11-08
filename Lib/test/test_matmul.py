import unittest


class TestMatMul(unittest.TestCase):

    def test_matmul(self):
        class MOldStyle:
            def __matmul__(self, o):
                return 4
            def __imatmul__(self, o):
                self.other = o
                return self

        class MNewStyle(MOldStyle, object):
            pass

        for M in [MOldStyle, MNewStyle]:
            m = M()
            self.assertEqual(m @ m, 4)
            m @= 42
            self.assertEqual(m.other, 42)

if __name__ == "__main__":
    unittest.main()
