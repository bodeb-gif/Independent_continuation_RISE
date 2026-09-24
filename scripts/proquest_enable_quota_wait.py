"""Enable daily-quota waiting in the existing ProQuest VM corpus runner.

Copy this file to election_arm on the VM, then run:
    "$PY" proquest_enable_quota_wait.py
No API requests are made by this installer. Existing outputs are untouched.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import tempfile


MARKER = '# PROQUEST_DAILY_QUOTA_WAIT_V1'
WAIT_FUNCTION = r'''
# PROQUEST_DAILY_QUOTA_WAIT_V1
# Both LLM stages exit 2 only for the daily quota. Keep this runner alive and
# resume the same stage/year after waiting; the stages skip saved pages.
run_with_quota_wait() {
    local rc wait_seconds="${QUOTA_RETRY_SECONDS:-3600}"
    if [[ ! "$wait_seconds" =~ ^[0-9]+$ ]] || [ "$wait_seconds" -lt 60 ]; then
        echo "QUOTA_RETRY_SECONDS must be a whole number of seconds >= 60." >&2
        return 1
    fi
    while true; do
        "$@"
        rc=$?
        if [ "$rc" -ne 2 ]; then
            return "$rc"
        fi
        echo "$(date -u '+%Y-%m-%d %H:%M:%S UTC'): daily quota exhausted."
        echo "Saved progress is retained; waiting ${wait_seconds}s before retrying."
        sleep "$wait_seconds" || return 130
    done
}
'''


def patched_text(text):
    replacements = [
        ('STOPPED=0\n', 'STOPPED=0\n' + WAIT_FUNCTION + '\n'),
        ('        $PY extract_gpt.py --source proquest --window "$y"',
         '        run_with_quota_wait "$PY" extract_gpt.py --source proquest --window "$y"'),
        ('        $PY verify_gpt.py \\\n',
         '        run_with_quota_wait "$PY" verify_gpt.py \\\n'),
    ]
    if MARKER in text:
        if WAIT_FUNCTION not in text or any(new not in text for _, new in replacements[1:]):
            raise ValueError('An incomplete or modified quota-wait patch exists; inspect the runner first.')
        return text
    for old, _ in replacements:
        if text.count(old) != 1:
            raise ValueError('Runner layout differs from the inspected version; no changes made.')
    for old, new in replacements:
        text = text.replace(old, new, 1)
    return text


def install(runner):
    runner = Path(runner)
    original = runner.read_text()
    updated = patched_text(original)
    if updated == original:
        print('Quota waiting is already enabled.')
        return
    # Syntax validation precedes any modification to the original runner.
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh') as candidate:
        candidate.write(updated)
        candidate.flush()
        subprocess.run(['bash', '-n', candidate.name], check=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = runner.with_name(runner.name + '.before-quota-wait-' + stamp)
    shutil.copy2(runner, backup)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', dir=runner.parent, delete=False) as candidate:
            staged = Path(candidate.name)
            candidate.write(updated)
        shutil.copymode(runner, staged)
        staged.replace(runner)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
    print(f'Enabled hourly quota retries in {runner}. Backup: {backup}')
    print('Restart the runner to use this change; an already-running job is unchanged.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner', type=Path, default=Path('run_corpus_economy.sh'))
    args = parser.parse_args()
    try:
        install(args.runner)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')
