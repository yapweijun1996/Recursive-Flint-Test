"""Build the static benchmark report from recorded, scored evidence. No API calls."""

import argparse
import html
import json
import pathlib
import re
import shutil
import statistics
import subprocess
from urllib.parse import urljoin

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'site'
OUTPUT = ROOT / 'dist'
REPO = 'https://github.com/yapweijun1996/Recursive-Flint-Test'
PROFILES = {'luna-high': 'Luna · high', 'luna-medium': 'Luna · medium', 'flint': 'Flint'}


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8-sig'))


def prepare_data():
    expanded = read('benchmarks/expanded-20261026/results.json')
    cross = read('benchmarks/luna-vs-flint-20261026/results.scored.json')
    initial = read('benchmarks/flint-20261026/results.json')
    effort = read('benchmarks/flint-20261026/comparison.json')
    retries = read('benchmarks/flint-20261026/read-tool-retry-20261026-011420.json')
    records = expanded['results']
    if len(records) != expanded['metadata']['expected_calls'] or not expanded['metadata'].get('finished_utc'):
        raise ValueError('Expanded benchmark is incomplete')
    if len({(r['suite'], r['task'], r['trial'], r['profile']) for r in records}) != len(records):
        raise ValueError('Duplicate expanded benchmark observations')
    suites = {}
    for suite in ['A', 'B', 'C']:
        groups = []
        for profile, label in PROFILES.items():
            rows = [r for r in records if r['suite'] == suite and r['profile'] == profile]
            if rows:
                groups.append({'id': profile, 'label': label, 'runs': len(rows),
                               'passed': sum(r['passed'] for r in rows),
                               'total': round(sum(r['wall_seconds'] for r in rows), 3),
                               'median': round(statistics.median(r['wall_seconds'] for r in rows), 3),
                               'cost': sum(r.get('reported_cost_usd', 0) for r in rows)})
        suites[suite] = groups
    baseline = expanded['baseline']
    if not all(not result['buggy']['passed'] and result['reference']['passed'] for result in baseline.values()):
        raise ValueError('Repair baseline/reference checks are invalid')
    revision = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, text=True).strip()
    return {'date': '2026-10-26', 'piVersion': expanded['metadata']['pi_version'], 'revision': revision,
            'calls': len(records), 'passed': sum(r['passed'] for r in records),
            'repairChecks': sum(r['reference']['checks'] for r in baseline.values()),
            'repairCalls': sum(r['suite'] == 'A' for r in records),
            'readCalls': sum(r['suite'] == 'B' for r in records),
            'effortCalls': sum(r['suite'] == 'C' for r in records),
            'checks': {task: item['reference']['checks'] for task, item in baseline.items()},
            'suites': suites, 'cross': cross['summary'],
            'initial': initial['summary'], 'effort': effort['summary']['groups'],
            'readRetries': {'passed': retries['passed'], 'trials': retries['trials']},
            'sourceRepository': REPO}


def build():
    data = prepare_data()
    if OUTPUT.is_symlink():
        raise ValueError('Build destination must not be a symbolic link')
    OUTPUT.mkdir(exist_ok=True)
    template = (SOURCE / 'index.html').read_text(encoding='utf-8')
    replacements = {'DATA': json.dumps(data, separators=(',', ':')).replace('<', '\\u003c'),
                    'CALLS': str(data['calls']), 'PASSED': str(data['passed']),
                    'CHECKS': str(data['repairChecks']), 'PI_VERSION': html.escape(data['piVersion']),
                    'REPAIR_CALLS': str(data['repairCalls']), 'READ_CALLS': str(data['readCalls']),
                    'EFFORT_CALLS': str(data['effortCalls']), 'REVISION': html.escape(data['revision'])}
    for task, count in data['checks'].items():
        replacements[task.upper() + '_CHECKS'] = str(count)
    for token, value in replacements.items():
        template = template.replace('{{' + token + '}}', value)
    if re.search(r'\{\{[A-Z_]+\}\}', template):
        raise ValueError('Unresolved report template token')
    (OUTPUT / 'index.html').write_text(template, encoding='utf-8')
    for name in ['styles.css', 'app.js', 'favicon.svg']:
        shutil.copyfile(SOURCE / name, OUTPUT / name)
    downloads = OUTPUT / 'downloads'
    downloads.mkdir(exist_ok=True)
    brief = (ROOT / 'benchmarks/FLINT_TESTING_KNOWLEDGE.md').read_text(encoding='utf-8')
    brief = re.sub(r'\]\((?!https?://)([^)]+)\)',
                   lambda match: '](' + urljoin(REPO + '/blob/main/benchmarks/', match.group(1)) + ')', brief)
    (downloads / 'FLINT_TESTING_KNOWLEDGE.md').write_text(brief, encoding='utf-8')
    (downloads / 'benchmark-summary.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    (OUTPUT / '.nojekyll').touch()
    validate(template)
    print(f'Built {OUTPUT}: {data["passed"]}/{data["calls"]} expanded calls; source {data["revision"]}.')


def validate(document):
    ids = re.findall(r'\bid="([^"]+)"', document)
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate HTML IDs')
    for href in re.findall(r'(?:href|src)="([^"]+)"', document):
        if href.startswith('#'):
            if href[1:] not in ids:
                raise ValueError('Missing section: ' + href)
        elif not href.startswith(('https://', 'http://', 'data:')):
            if not (OUTPUT / href).is_file():
                raise ValueError('Missing local asset: ' + href)
    if '.pi/' in document:
        raise ValueError('Local configuration must not be included in the report')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Build and validate all local assets and links.')
    parser.parse_args()
    build()
