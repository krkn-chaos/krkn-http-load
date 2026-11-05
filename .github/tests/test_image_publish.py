import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / 'workflows' / 'build.yaml'


def step(name):
    return WORKFLOW.read_text().split(f'      - name: {name}\n', 1)[1].split('\n      - name:', 1)[0]


def enabled_for_event(name, event, ref):
    match = re.search(r'^        if: (.+)$', step(name), re.MULTILINE)
    if not match:
        return True
    condition = match.group(1)
    pattern = r"github.event_name == '([^']+)' && startsWith\(github.ref, '([^']+)'\)"
    parsed = re.fullmatch(pattern, condition)
    if not parsed:
        raise AssertionError(f'Unexpected condition: {condition}')
    return event == parsed.group(1) and ref.startswith(parsed.group(2))


class ImagePublishTest(unittest.TestCase):
    def test_pr_builds_but_only_tag_pushes_publish(self):
        self.assertTrue(enabled_for_event('Build Docker image', 'pull_request', 'refs/pull/1/merge'))
        for name in ['Login in quay', 'Push Docker image']:
            with self.subTest(step=name):
                self.assertFalse(enabled_for_event(name, 'pull_request', 'refs/pull/1/merge'))
                self.assertFalse(enabled_for_event(name, 'push', 'refs/heads/main'))
                self.assertTrue(enabled_for_event(name, 'push', 'refs/tags/v1.2.3'))

    def test_registry_password_is_sent_on_stdin(self):
        source = step('Login in quay')
        run = re.search(r'^        run: (.*)$', source, re.MULTILINE).group(1)
        script = textwrap.dedent(source.split('        run: |\n', 1)[1].split('\n        env:', 1)[0]) if run == '|' else run
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docker = root / 'docker'
            docker.write_text('#!/usr/bin/env python3\nimport json,os,sys\n'
                              'json.dump({"args":sys.argv[1:],"stdin":sys.stdin.read()},'
                              'open(os.environ["DOCKER_CAPTURE"],"w"))\n')
            docker.chmod(0o755)
            capture = root / 'capture.json'
            env = {**os.environ, 'PATH': f'{directory}:{os.environ["PATH"]}',
                   'DOCKER_CAPTURE': str(capture), 'QUAY_USER': 'test-user', 'QUAY_TOKEN': 'test-token'}
            result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script],
                                    env=env, input='', capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            invocation = json.loads(capture.read_text())
            self.assertNotIn('test-token', invocation['args'])
            self.assertIn('--password-stdin', invocation['args'])
            self.assertEqual(invocation['stdin'], 'test-token')


if __name__ == '__main__':
    unittest.main()
