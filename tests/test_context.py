import unittest
import xml.etree.ElementTree as ET

import drawsvg as draw


class InvertedPathTest(unittest.TestCase):
    def test_scientific_notation(self):
        context = draw.Context(invert_y=True)
        for value in ('1e-5', '1E-5', '1e+5', '-1e-5', '1.5e-5'):
            with self.subTest(value=value):
                result = context.override_args({'d': f'M1,{value} L2,3'})['d']
                first, second = result.split()
                self.assertEqual(float(first.split(',')[1]), -float(value))
                self.assertEqual(second, 'L2,-3')

    def test_generated_path_with_small_float(self):
        drawing = draw.Drawing(100, 100, context=draw.Context(invert_y=True))
        drawing.append(draw.Path().M(1, 1e-5).L(2, 3))
        root = ET.fromstring(drawing.as_svg())
        path = root.find('{http://www.w3.org/2000/svg}path')
        self.assertEqual(path.attrib['d'], 'M1,-1e-05 L2,-3')

    def test_integer_formatting_and_default_context_unchanged(self):
        self.assertEqual(draw.Context(invert_y=True).override_args(
            {'d': 'M1,2 L3,4'})['d'], 'M1,-2 L3,-4')
        self.assertEqual(draw.Context().override_args(
            {'d': 'M1,1e-5 L2,3'})['d'], 'M1,1e-5 L2,3')


if __name__ == '__main__':
    unittest.main()
