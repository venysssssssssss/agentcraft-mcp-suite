import json
import tempfile
import unittest
from pathlib import Path
from agentcraft.audit import audit

class AuditTests(unittest.TestCase):
    def test_warns_on_other_scope_and_preserves_unrelated(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            project=root/'project';project.mkdir()
            home=root/'home';home.mkdir()
            (home/'.config/opencode').mkdir(parents=True)
            (home/'.config/opencode/opencode.json').write_text(json.dumps({'mcp':{
                'pdfcraft':{'type':'local','command':['pdfcraft-cli','mcp'],'enabled':True},
                'other':{'type':'local','command':['other']}}}))
            result=audit(project,home)
            self.assertFalse(result['ok'])
            self.assertEqual(result['findings'][0]['server'],'pdfcraft')
            (home/'.config/opencode/opencode.json').write_text(json.dumps({'mcp':{
                'pdfcraft':{'type':'local','command':['pdfcraft-cli','mcp'],'enabled':False}}}))
            self.assertTrue(audit(project,home)['ok'])
