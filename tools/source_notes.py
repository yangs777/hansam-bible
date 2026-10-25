"""Narrow allowance for individually reviewed plain notes; never merge readings."""
import hashlib,json,pathlib
R=pathlib.Path(__file__).resolve().parents[1]
DECISIONS=json.loads((R/'data/source-note-decisions.json').read_text(encoding='utf-8'))

def reviewed_plain_note(reference, element, source_hash):
    decision=DECISIONS.get(reference)
    return bool(decision and element.tag.rsplit('}',1)[-1]=='note' and not list(element)
        and element.get('n')==decision['note_n'] and source_hash==decision['source_file_sha256']
        and hashlib.sha256((element.text or '').encode('utf-8')).hexdigest()==decision['text_sha256'])
