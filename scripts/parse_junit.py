#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import sys
import json

def parse_junit(file):
    tree = ET.parse(file)
    root = tree.getroot()
    total = 0
    passed = 0
    failed = 0
    skipped = 0
    deselected = 0
    failures = []
    for testcase in root.iter('testcase'):
        total += 1
        if testcase.find('failure') is not None:
            failed += 1
            failures.append({
                'name': testcase.get('name'),
                'reason': testcase.find('failure').get('message', 'No message')
            })
        elif testcase.get('status') == 'skipped':
            skipped += 1
        else:
            passed += 1
    return {'total': total, 'passed': passed, 'failed': failed, 'skipped': skipped, 'failures': failures}

if __name__ == "__main__":
    results = {}
    for file in sys.argv[1:]:
        run_id = file.split('-')[2].split('.')[0]
        results[run_id] = parse_junit(file)
    with open('summary.json', 'w') as f:
        json.dump(results, f, indent=2) 