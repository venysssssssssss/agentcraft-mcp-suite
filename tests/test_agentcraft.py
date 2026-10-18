import json
import os
import shutil
import stat
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

from agentcraft.cli import main
from agentcraft.mcp import MCPProcess, discover_engine_commands
from agentcraft.registry import APPS

ROOT=Path(__file__).resolve().parents[1]

class RegistryTests(unittest.TestCase):
    def test_thirteen_unique_apps(self):
        self.assertEqual(len(APPS),13)
        self.assertTrue(all(a.binary == a.name+'-cli' for a in APPS.values()))
        self.assertEqual(APPS['vectorcraft'].args(), ['mcp','--headless'])
        self.assertEqual(APPS['effectcraft'].args('desktop'), ['mcp','--bridge','9877'])
        self.assertEqual(APPS['figcraft'].args('desktop'), ['mcp','--attach','7979'])
        with self.assertRaises(ValueError):
            APPS['pdfcraft'].args('desktop')

class MCPTests(unittest.TestCase):
    def test_protocol_pagination_and_missing_resource_templates(self):
        with MCPProcess([sys.executable,str(ROOT/'tests/mock_server.py')],timeout=4) as mcp:
            snap=mcp.snapshot()
            self.assertEqual([t['name'] for t in snap['tools']], ['doc_inspect','command_list'])
            self.assertEqual(len(snap['resources']),1)
            self.assertEqual(snap['resourceTemplates'],[])
            self.assertEqual(discover_engine_commands(mcp,snap['tools'])['catalog'][0]['id'],'layer.add')

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.bin=self.base/'bin';self.bin.mkdir()
        target=self.bin/'effectcraft-cli'
        shutil.copy2(ROOT/'tests/mock_server.py',target)
        target.chmod(target.stat().st_mode|stat.S_IXUSR)

    def test_install_unregistered_and_idempotent_for_all_clients(self):
        project=self.base/'project';project.mkdir()
        # Seed the exact old (eager) registrations created by AgentCraft 0.1.1
        cli=str(self.bin/'effectcraft-cli')
        (project/'opencode.json').write_text(json.dumps({'model':'keep-me','mcp':{
            'effectcraft':{'type':'local','command':[cli,'mcp'],'enabled':True,'timeout':30000},
            'thirdparty':{'type':'local','command':['other-cli'],'enabled':True}}}))
        (project/'.mcp.json').write_text(json.dumps({'mcpServers':{
            'effectcraft':{'command':cli,'args':['mcp']},'thirdparty':{'command':'other-cli','args':[]}}}))
        (project/'.codex').mkdir()
        (project/'.codex/config.toml').write_text('model = "keep-me"\n\n# AgentCraft MCP servers (generated; review before use)\n\n[mcp_servers.effectcraft]\ncommand = '+json.dumps(cli)+'\nargs = ["mcp"]\nstartup_timeout_sec = 30\ntool_timeout_sec = 120\n')
        for _ in range(2):
            self.assertEqual(main(['install','--target',str(project),'--apps','effectcraft','--bin-dir',str(self.bin)]),0)
        for p in ('.agents/skills/agentcraft-effectcraft/SKILL.md',
                  '.claude/skills/agentcraft-effectcraft/SKILL.md',
                  '.opencode/skills/agentcraft-effectcraft/SKILL.md',
                  '.claude/commands/agentcraft-effectcraft.md',
                  '.opencode/commands/agentcraft-effectcraft.md'):
            self.assertTrue((project/p).exists(), p)
        cfg=json.loads((project/'opencode.json').read_text())
        self.assertEqual(cfg['model'],'keep-me')
        self.assertNotIn('effectcraft',cfg['mcp'])
        self.assertIn('thirdparty',cfg['mcp'])
        claude=json.loads((project/'.mcp.json').read_text())
        self.assertNotIn('effectcraft',claude['mcpServers'])
        self.assertIn('thirdparty',claude['mcpServers'])
        codex=(project/'.codex/config.toml').read_text()
        self.assertIn('model = "keep-me"',codex)
        self.assertNotIn('effectcraft',codex)

    def test_migrate_generated_opencode_legacy_schema(self):
        project=self.base/'legacy';project.mkdir()
        (project/'opencode.json').write_text(json.dumps({'mcp':{'servers':{
            'effectcraft':{'type':'local', 'command':['effectcraft-cli','mcp'],
                           'timeout':{'startup':30000,'catalog':30000,'execution':600000}}
        }}}))
        self.assertEqual(main(['install','--client','opencode','--target',str(project),
                               '--apps','effectcraft','--bin-dir',str(self.bin)]),0)
        config=json.loads((project/'opencode.json').read_text())
        self.assertNotIn('mcp',config)

    def test_unknown_registration_fails_closed(self):
        project=self.base/'unsafe';project.mkdir()
        (project/'opencode.json').write_text(json.dumps({'mcp':{
            'effectcraft':{'type':'local','command':['custom-wrapper','mcp'],'enabled':True}
        }}))
        self.assertEqual(main(['install','--client','opencode','--target',str(project),'--apps','effectcraft']),2)
        self.assertTrue(json.loads((project/'opencode.json').read_text())['mcp']['effectcraft']['enabled'])

    def test_doctor_and_catalog(self):
        self.assertEqual(main(['doctor','--apps','effectcraft','--bin-dir',str(self.bin)]),0)
        out=self.base/'generated'
        self.assertEqual(main(['catalog','--apps','effectcraft','--engine','--bin-dir',str(self.bin),'--out',str(out)]),0)
        data=json.loads((out/'effectcraft.json').read_text())
        self.assertEqual(len(data['tools']),2)
        self.assertEqual(data['engineCommands']['catalog'][0]['id'],'layer.add')
        text=(out/'effectcraft.md').read_text()
        self.assertIn('doc_inspect',text)
        self.assertIn('## Engine command catalog',text)

    def test_failed_availability_is_visible(self):
        self.assertEqual(main(['doctor','--apps','photocraft','--bin-dir',str(self.bin)]),1)
        self.assertEqual(main(['install','--apps','photocraft','--bin-dir',str(self.bin),
                  '--target',str(self.base/'other'),'--strict']),2)

    def test_unsafe_tool_name_rejected(self):
        self.assertEqual(main(['call','effectcraft','not_a_tool','--bin-dir',str(self.bin)]),2)

if __name__=='__main__':
    unittest.main()

class SkillTests(unittest.TestCase):
    def test_all_fourteen_skill_manifests(self):
        skills=list((ROOT/'skills').glob('*/SKILL.md'))
        self.assertEqual(len(skills),14)
        for p in skills:
            data=p.read_text(encoding='utf-8')
            self.assertTrue(data.startswith('---\nname: '),p)
            self.assertIn('description: ',data)
            self.assertIn('opencode/slash:',data)
            self.assertIn('session start',data)
        self.assertEqual(len(list((ROOT/'commands').glob('*.md'))),14)
