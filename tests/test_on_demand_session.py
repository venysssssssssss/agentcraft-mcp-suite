"""Session daemon integration tests against the synthetic native MCP server."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import stat
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agentcraft.session import main as session_main

ROOT=Path(__file__).resolve().parents[1]


class OnDemandSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)
        bin_dir=self.path/'bin'
        bin_dir.mkdir()
        self.binary=bin_dir/'effectcraft-cli'
        shutil.copy2(ROOT/'tests/mock_server.py',self.binary)
        self.binary.chmod(self.binary.stat().st_mode|stat.S_IXUSR)
        self.session_dir=self.path/'private-sessions'
        patcher=patch.dict(os.environ,{'AGENTCRAFT_SESSION_DIR':str(self.session_dir)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.sid=None
        self.addCleanup(self.stop_session)

    def invoke(self,*args):
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            code=session_main(list(args))
        result=output.getvalue().strip()
        return code,json.loads(result) if result.startswith(('{','[')) else result

    def stop_session(self):
        if self.sid and (self.session_dir/(self.sid+'.json')).exists():
            self.invoke('stop',self.sid)
            for _ in range(30):
                if not (self.session_dir/(self.sid+'.json')).exists():
                    break
                time.sleep(0.1)

    def test_lazy_lifecycle_stateful_calls_and_stop(self):
        self.assertEqual(list(self.session_dir.glob('*.json')) if self.session_dir.exists() else [],[])
        code,info=self.invoke('start','effectcraft','--bin-dir',str(self.binary.parent),'--idle-seconds','45')
        self.assertEqual(code,0)
        self.sid=info['session']
        self.assertEqual(info['app'],'effectcraft')
        self.assertTrue((self.session_dir/(self.sid+'.json')).exists())
        if os.name!='nt':
            self.assertEqual((self.session_dir/(self.sid+'.json')).stat().st_mode & 0o077,0)
        code,tools=self.invoke('tools',self.sid,'--details')
        self.assertEqual(code,0)
        self.assertEqual({x['name'] for x in tools},{'doc_inspect','command_list'})
        code,a=self.invoke('call',self.sid,'command_list','--arguments','{}')
        self.assertEqual(code,0)
        self.assertIn('layer.add',a['content'][0]['text'])
        code,ping=self.invoke('status',self.sid)
        self.assertEqual(code,0)
        self.assertEqual(ping['pid'],info['pid'])
        code,b=self.invoke('call',self.sid,'doc_inspect','--arguments','{}')
        self.assertEqual(code,0)
        self.assertIn('content',b)
        code,stopped=self.invoke('stop',self.sid)
        self.assertEqual(code,0)
        self.assertTrue(stopped['stopping'])
        for _ in range(30):
            if not (self.session_dir/(self.sid+'.json')).exists():
                break
            time.sleep(0.1)
        self.assertFalse((self.session_dir/(self.sid+'.json')).exists())
        self.sid=None

    def test_invalid_session_token_and_malformed_id(self):
        from agentcraft.session import metadata_path
        with self.assertRaises(ValueError):
            metadata_path('../../invalid')
