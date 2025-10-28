import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import gen_svg

PROFILE = {
    "name": "Aditya Verma",
    "location": "San Francisco",
    "tagline": "agents & devtools <3",
    "stack": ["rust", "swift"],
    "now": [{"name": "thing", "desc": "a thing"}],
}


class RenderTest(unittest.TestCase):
    def test_output_is_valid_xml(self):
        root = ET.fromstring(gen_svg.render(PROFILE))
        self.assertTrue(root.tag.endswith("svg"))

    def test_special_chars_survive_round_trip(self):
        root = ET.fromstring(gen_svg.render(PROFILE))
        texts = [t.text for t in root.iter("{http://www.w3.org/2000/svg}text")]
        self.assertIn("San Francisco · agents & devtools <3", texts)


if __name__ == "__main__":
    unittest.main()
