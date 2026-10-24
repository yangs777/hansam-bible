"""Exercise adoption against isolated copies; never change the real edition."""
import contextlib, hashlib, io, json, pathlib, shutil, tempfile, unittest
import adopt

REAL=adopt.R
class RevisionTests(unittest.TestCase):
    def setUp(self):
        (REAL/'private').mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='revision-test-',dir=REAL/'private')
        self.root=pathlib.Path(self.temp.name); adopt.R=self.root
        for name in ('config.json','data/editorial.json','data/decisions.json','dist/data/hansam-bible.json'):
            dest=self.root/name; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(REAL/name,dest)
        self.decisions=adopt.read(self.root/'data/decisions.json')
        self.version=adopt.read(self.root/'config.json')['version']
        parts=list(map(int,self.version.split('.'))); parts[-1]+=1
        self.next_version='.'.join(map(str,parts))
        self.path=self.root/'next.json'
    def tearDown(self):
        adopt.R=REAL; self.temp.cleanup()
    def next_decisions(self):
        self.decisions['version']=self.next_version
        for d in self.decisions['verses']:d['version']=self.next_version
        self.decisions['verses'][0]['translations']['ko']='검증용 새 채택문'
        adopt.save(self.path,self.decisions)
    def test_current_version_cannot_be_overwritten(self):
        before=(self.root/'config.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'NEW version'):
            adopt.adopt(self.root/'data/decisions.json',self.version)
        self.assertEqual(before,(self.root/'config.json').read_bytes())
    def test_new_selection_preserves_previous_text(self):
        previous=adopt.read(self.root/'dist/data/hansam-bible.json')['records']
        self.next_decisions()
        with contextlib.redirect_stdout(io.StringIO()):adopt.adopt(self.path,self.next_version)
        archive=adopt.read(self.root/f'data/releases/v{self.version}.json')
        self.assertEqual(previous,archive['records'])
        target_id=self.decisions['verses'][0]['id']
        selected=next(v for p in adopt.read(self.root/'data/editorial.json')['passages'] for v in p['verses'] if v['id']==target_id)
        self.assertEqual('검증용 새 채택문',selected['ko'])
        old=next(v for v in archive['records'] if v['id']==target_id)
        self.assertNotEqual(selected['ko'],old['translations']['ko'])
    def test_existing_archive_cannot_be_changed(self):
        self.next_decisions(); path=self.root/f'data/releases/v{self.version}.json'
        old=adopt.read(self.root/'dist/data/hansam-bible.json'); old['records'][0]['translations']['ko']='tampered'
        adopt.save(path,old); digest=hashlib.sha256(path.read_bytes()).digest()
        with self.assertRaisesRegex(ValueError,'immutable'):adopt.adopt(self.path,self.next_version)
        self.assertEqual(digest,hashlib.sha256(path.read_bytes()).digest())
        self.assertEqual(self.version,adopt.read(self.root/'config.json')['version'])
    def test_new_passage_preserves_entire_previous_collection(self):
        import copy
        self.next_decisions()
        passage=copy.deepcopy(adopt.read(self.root/'data/editorial.json')['passages'][0])
        passage['id']='TEST.NEW';passage['slug']='test-new';passage['verses']=passage['verses'][:1]
        passage['verses'][0]['id']='TEST.NEW.001'
        decision=copy.deepcopy(self.decisions['verses'][0]);decision['id']='TEST.NEW.001'
        self.decisions['new_passages']=[passage];self.decisions['verses'].append(decision);adopt.save(self.path,self.decisions)
        old=adopt.read(self.root/'dist/data/hansam-bible.json')['records']
        with contextlib.redirect_stdout(io.StringIO()):adopt.adopt(self.path,self.next_version)
        self.assertEqual(old,adopt.read(self.root/f'data/releases/v{self.version}.json')['records'])
        self.assertEqual('TEST.NEW.001',adopt.read(self.root/'data/editorial.json')['passages'][0]['verses'][0]['id'])

    def test_extend_passage_preserves_url_and_previous_collection(self):
        import copy
        self.next_decisions()
        passage=adopt.read(self.root/'data/editorial.json')['passages'][0]
        verse=copy.deepcopy(passage['verses'][-1]);verse['id']='TEST.APPEND.001'
        decision=copy.deepcopy(self.decisions['verses'][0]);decision['id']=verse['id']
        self.decisions['verses'].append(decision)
        self.decisions['passage_updates']=[{'id':passage['id'],'verses':[verse]}]
        adopt.save(self.path,self.decisions)
        old=adopt.read(self.root/'dist/data/hansam-bible.json')['records']
        with contextlib.redirect_stdout(io.StringIO()):adopt.adopt(self.path,self.next_version)
        current=adopt.read(self.root/'data/editorial.json')['passages'][0]
        self.assertEqual(passage['slug'],current['slug'])
        self.assertEqual([v['id'] for v in passage['verses']]+[verse['id']],[v['id'] for v in current['verses']])
        self.assertEqual(old,adopt.read(self.root/f'data/releases/v{self.version}.json')['records'])

    def test_extension_cannot_replace_existing_ids_or_urls(self):
        self.next_decisions()
        passage=adopt.read(self.root/'data/editorial.json')['passages'][0]
        for update,error in [({'id':passage['id'],'slug':'changed'},'stable'),
                             ({'id':passage['id'],'verses':[passage['verses'][0]]},'Duplicate')]:
            self.decisions['passage_updates']=[update];adopt.save(self.path,self.decisions)
            with self.assertRaisesRegex(ValueError,error):adopt.adopt(self.path,self.next_version)
        self.assertEqual(self.version,adopt.read(self.root/'config.json')['version'])

if __name__=='__main__':unittest.main()
