import unittest,xml.etree.ElementTree as ET
from source_notes import reviewed_plain_note

class SourceNoteTests(unittest.TestCase):
    def test_only_reviewed_reference_note_and_source_hash_are_accepted(self):
        note=ET.Element('note',n='1');note.text='BHS has been faithful to the Leningrad Codex where there might be a question of the validity of the form and we keep the same form as BHS. '
        digest='0526e5c9a5fb4d907847645f954ed3d1268fa69decbd872056cedd2668d86449'
        self.assertTrue(reviewed_plain_note('Gen.2.18',note,digest))
        self.assertFalse(reviewed_plain_note('Gen.2.19',note,digest))
        self.assertFalse(reviewed_plain_note('Gen.2.18',note,'changed source'))
        note.text+='Changed'
        self.assertFalse(reviewed_plain_note('Gen.2.18',note,digest))

    def test_nested_variant_content_is_never_accepted(self):
        note=ET.Element('note',n='1');ET.SubElement(note,'reading').text='variant'
        self.assertFalse(reviewed_plain_note('Gen.2.18',note,'0526e5c9a5fb4d907847645f954ed3d1268fa69decbd872056cedd2668d86449'))

if __name__=='__main__':unittest.main()
