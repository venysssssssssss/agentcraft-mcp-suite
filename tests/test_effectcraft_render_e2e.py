"""Pure tests of the manual render example; no external ArtCraft binary required."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'effectcraft_render_e2e.py'
spec = importlib.util.spec_from_file_location('effectcraft_render_e2e', EXAMPLE)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


class FakeMCP:
    invocations = []
    output = None
    should_fail = False

    def __init__(self, command, timeout):
        self.start_command, self.timeout = command, timeout

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def list_paginated(self, method, field):
        return [{'name': 'command_run'}]

    def request(self, method, params):
        assert method == 'tools/call'
        cmd = params['arguments']['id']
        self.invocations.append((cmd, params['arguments']['params']))
        if self.should_fail and cmd == 'renderQueue.render':
            return {'isError': True, 'content': [{'type':'text', 'text':'encoder failed'}]}
        if cmd == 'renderQueue.render':
            self.output.write_bytes(b'fake-mp4-contents')
        return {'isError': False, 'content': [{'type':'text','text':'{}'}]}


class TestEffectCraftRenderE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.project = root / 'existing.ecproj'
        self.project.write_text('test project')
        self.binary = root / 'effectcraft-cli'
        self.binary.write_text('fake binary')
        self.output = root / 'render.mp4'
        FakeMCP.invocations = []
        FakeMCP.output = self.output
        FakeMCP.should_fail = False
        self.argv = ['--project', str(self.project), '--binary', str(self.binary), '--output', str(self.output), '--seconds','1']

    def test_render_and_verify(self):
        ffprobe = SimpleNamespace(returncode=0, stderr='', stdout=json.dumps({
            'format': {'duration': '1.0', 'size': '17'},
            'streams': [{'index': 0,'codec_type':'video','codec_name':'h264','width':1920,'height':1080}]
        }))
        with patch.object(module, 'MCPProcess', FakeMCP), patch.object(module.shutil, 'which', return_value='/usr/bin/ffprobe'),patch.object(module.subprocess, 'run',return_value=ffprobe):
            self.assertEqual(module.main(self.argv),0)
        self.assertEqual([x[0] for x in FakeMCP.invocations],
                         ['comp.open','renderQueue.add','renderQueue.list','renderQueue.render','renderQueue.list'])
        self.assertEqual(FakeMCP.invocations[1][1]['format'], 'h264')
        self.assertEqual(FakeMCP.invocations[1][1]['timeSpan'], 'custom')
        self.assertEqual(FakeMCP.invocations[1][1]['end'], 1.0)

    def test_render_error_is_not_reported_as_success(self):
        FakeMCP.should_fail = True
        with patch.object(module, 'MCPProcess', FakeMCP),patch.object(module.shutil, 'which', return_value='/usr/bin/ffprobe'):
            self.assertEqual(module.main(self.argv),1)
        self.assertFalse(self.output.exists())

    def test_prevents_accidental_overwrite(self):
        self.output.write_bytes(b'original')
        with self.assertRaises(SystemExit) as err:
            module.main(self.argv)
        self.assertEqual(err.exception.code,2)
        self.assertEqual(self.output.read_bytes(),b'original')

    def test_verify_media_refuses_non_h264(self):
        self.output.write_bytes(b'example')
        info = SimpleNamespace(returncode=0,stderr='',stdout=json.dumps({'format':{'duration':'1'}, 'streams':[{'codec_type':'video','codec_name':'vp9'}]}))
        with patch.object(module.subprocess, 'run', return_value=info):
            with self.assertRaisesRegex(RuntimeError,'Expected H.264'):
                module.verify_media(self.output,'ffprobe')


if __name__ == '__main__':
    unittest.main()
