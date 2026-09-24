"""Exercise real shell retry/resume behavior without API requests or waits."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from proquest_enable_quota_wait import WAIT_FUNCTION, install, patched_text


class QuotaWaitTests(unittest.TestCase):
    def run_shell(self, body):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sleep = root / 'sleep'
            sleep.write_text('#!/bin/sh\nprintf "%s\\n" "$1" >> waits\n')
            sleep.chmod(0o755)
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'], QUOTA_RETRY_SECONDS='3600')
            result = subprocess.run(['bash', '-c', WAIT_FUNCTION + '\n' + body],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=5)
            waits = (root/'waits').read_text().splitlines() if (root/'waits').exists() else []
            return result, waits

    def test_daily_quota_resumes_each_stage_and_preserves_arguments(self):
        result, waits = self.run_shell(r'''
stage() {
    local phase="$1" year="$2"
    if [ ! -f "$phase" ]; then touch "$phase"; return 2; fi
    echo "completed $phase $year"
}
run_with_quota_wait stage extract 2011 || exit "$?"
run_with_quota_wait stage verify 2011 || exit "$?"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(waits, ['3600', '3600'])
        self.assertIn('completed extract 2011', result.stdout)
        self.assertIn('completed verify 2011', result.stdout)

    def test_repeated_daily_limits_keep_waiting(self):
        result, waits = self.run_shell(r'''
stage() {
    local n=0
    [ -f attempts ] && read -r n < attempts
    n=$((n+1)); echo "$n" > attempts
    [ "$n" -ge 4 ]
    if [ "$n" -lt 4 ]; then return 2; fi
}
run_with_quota_wait stage
''')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(waits, ['3600'] * 3)

    def test_other_errors_return_without_daily_wait(self):
        result, waits = self.run_shell('stage() { return 7; }; run_with_quota_wait stage')
        self.assertEqual(result.returncode, 7)
        self.assertEqual(waits, [])

    def test_installer_preserves_backup_and_is_idempotent(self):
        original = '''#!/bin/bash
STOPPED=0
        $PY extract_gpt.py --source proquest --window "$y"
        $PY verify_gpt.py \\
            --claims "$claims"
'''
        with tempfile.TemporaryDirectory() as directory:
            runner = Path(directory)/'run_corpus_economy.sh'
            runner.write_text(original); runner.chmod(0o755)
            install(runner)
            updated = runner.read_text()
            backups = list(runner.parent.glob('*.before-quota-wait-*'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), original)
            self.assertEqual(runner.stat().st_mode & 0o777, 0o755)
            install(runner)
            self.assertEqual(runner.read_text(), updated)
            self.assertEqual(len(list(runner.parent.glob('*.before-quota-wait-*'))), 1)

    def test_unknown_runner_rejected_before_modification(self):
        with self.assertRaises(ValueError):
            patched_text('#!/bin/bash\necho unexpected runner\n')


if __name__ == '__main__':
    unittest.main()
