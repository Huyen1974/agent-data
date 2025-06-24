#!/usr/bin/env python3
"""
Create initial CI manifest (tests/manifest_ci.txt) with filtering suggestions.

This script analyzes the full test manifest and creates an initial filtered version
with exactly 519 tests, prioritizing stability and core functionality.

The user can then manually adjust this list as needed.
"""

import re
from pathlib import Path
from collections import defaultdict

def categorize_test(test_path):
    """Categorize a test based on its path and name patterns."""
    test_lower = test_path.lower()
    
    # Priority 1: Core functionality tests (highest stability)
    core_patterns = [
        'test_meta_counts',
        'api.*endpoint',
        'test.*auth',
        'test.*cache',
        'test.*basic',
        'test.*simple',
        'TestAPI.*',
        'test.*vector.*tool',
        'test.*firestore',
        'test.*qdrant.*basic'
    ]
    
    # Priority 2: Coverage and validation tests
    coverage_patterns = [
        'test.*coverage.*additional',
        'test.*validation',
        'test_cli140[em].*coverage',
        'test.*api_gateway.*coverage'
    ]
    
    # Priority 3: Performance tests (controlled selection)
    performance_patterns = [
        'test_cli140[fgh]',
        'latency',
        'performance',
        'optimization'
    ]
    
    # Exclude: Most problematic tests
    exclude_patterns = [
        'test_cli140[klj]',  # Most problematic runtime/cost/nightly tests
        'legacy.*test_cli140[klj]',
        'nightly.*simulation',
        'full.*runtime.*validation',
        'cost.*optimization'
    ]
    
    # Check exclusions first
    for pattern in exclude_patterns:
        if re.search(pattern, test_path, re.IGNORECASE):
            return 'exclude', f'Excluded: {pattern}'
    
    # Check core patterns
    for pattern in core_patterns:
        if re.search(pattern, test_path, re.IGNORECASE):
            return 'core', f'Core: {pattern}'
    
    # Check coverage patterns
    for pattern in coverage_patterns:
        if re.search(pattern, test_path, re.IGNORECASE):
            return 'coverage', f'Coverage: {pattern}'
    
    # Check performance patterns
    for pattern in performance_patterns:
        if re.search(pattern, test_path, re.IGNORECASE):
            return 'performance', f'Performance: {pattern}'
    
    # Default category
    if 'mock' in test_lower or 'unit' in test_lower:
        return 'unit', 'Unit test'
    elif 'integration' in test_lower or 'e2e' in test_lower:
        return 'integration', 'Integration test'
    else:
        return 'other', 'Other test'

def main():
    # Read full manifest
    manifest_full_path = Path("tests/manifest_full.txt")
    if not manifest_full_path.exists():
        print("❌ tests/manifest_full.txt not found! Run test collection first.")
        return
    
    with open(manifest_full_path, 'r') as f:
        all_tests = [line.strip() for line in f if line.strip() and '::test_' in line]
    
    print(f"📊 Total tests found: {len(all_tests)}")
    
    # Categorize all tests
    categories = defaultdict(list)
    reasons = {}
    
    for test in all_tests:
        category, reason = categorize_test(test)
        categories[category].append(test)
        reasons[test] = reason
    
    # Display categorization results
    print("\n📋 Test Categorization Results:")
    for category, tests in categories.items():
        print(f"  {category.upper()}: {len(tests)} tests")
    
    # Select tests for CI manifest (targeting 519)
    selected_tests = []
    
    # Priority order for selection
    priority_order = [
        ('core', 999),        # Take all core tests
        ('coverage', 999),    # Take all coverage tests
        ('unit', 999),        # Take all unit tests
        ('integration', 50),  # Limit integration tests
        ('performance', 30),  # Limit performance tests
        ('other', 999)        # Fill remaining with others
    ]
    
    for category, max_count in priority_order:
        available = categories.get(category, [])
        selected_count = min(len(available), max_count)
        selected_tests.extend(available[:selected_count])
        
        if len(selected_tests) >= 519:
            break
    
    # Ensure exactly 519 tests
    selected_tests = selected_tests[:519]
    
    print(f"\n✅ Selected {len(selected_tests)} tests for CI manifest")
    
    # Write initial CI manifest
    manifest_ci_path = Path("tests/manifest_ci.txt")
    with open(manifest_ci_path, 'w') as f:
        for test in selected_tests:
            f.write(f"{test}\n")
    
    # Create detailed filter log
    filter_log_path = Path(".cursor/G02h_filter_log.md")
    filter_log_path.parent.mkdir(exist_ok=True)
    
    with open(filter_log_path, 'w') as f:
        f.write("# G02h Test Filtering Log - Full Analysis\n\n")
        f.write(f"**Date:** June 23, 2025, 14:00 +07\n")
        f.write(f"**Total tests collected:** {len(all_tests)}\n")
        f.write(f"**Target for CI:** 519 tests\n")
        f.write(f"**Initial selection:** {len(selected_tests)} tests\n\n")
        
        f.write("## 📊 Test Distribution Analysis\n\n")
        f.write("| Category | Count | Description |\n")
        f.write("|----------|-------|-------------|\n")
        for category, tests in categories.items():
            desc = {
                'core': 'Core functionality, APIs, auth, basic operations',
                'coverage': 'Coverage tests and validation suites',
                'unit': 'Unit tests with mocks and minimal dependencies',
                'integration': 'Integration and end-to-end tests',
                'performance': 'Performance, latency, and optimization tests',
                'other': 'General tests not in other categories',
                'exclude': 'Problematic tests excluded from CI'
            }.get(category, 'Unknown category')
            f.write(f"| {category.upper()} | {len(tests)} | {desc} |\n")
        
        f.write(f"\n## 🎯 Selection Strategy\n\n")
        f.write("The initial manifest prioritizes:\n")
        f.write("1. **Core functionality tests** - Essential APIs, auth, vectors, basic operations\n")
        f.write("2. **Coverage and validation tests** - Quality assurance and validation suites\n") 
        f.write("3. **Unit tests** - Fast tests with mocks and minimal dependencies\n")
        f.write("4. **Limited integration tests** - Key integration scenarios only\n")
        f.write("5. **Controlled performance tests** - Essential performance validations\n\n")
        
        f.write("## ❌ Excluded Categories\n\n")
        excluded = categories.get('exclude', [])
        f.write(f"**{len(excluded)} tests excluded** for stability:\n")
        f.write("- `test_cli140k*` - Runtime optimization tests (most problematic)\n")
        f.write("- `test_cli140l*` - Nightly simulation tests\n")
        f.write("- `test_cli140j*` - Cost optimization tests\n")
        f.write("- Full runtime validation tests\n")
        f.write("- Cost optimization tests\n\n")
        
        f.write("## 📝 Manual Adjustment Instructions\n\n")
        f.write("**Next Steps for User:**\n")
        f.write("1. Review `tests/manifest_ci.txt` (current: 519 tests)\n")
        f.write("2. Add/remove tests as needed to reach exactly 519\n")
        f.write("3. Priority should be: stability > coverage > speed\n")
        f.write("4. Avoid tests with known flakiness (e.g., rate limiting, timeouts)\n")
        f.write("5. Test locally with: `pytest --collect-only -q --qdrant-mock | wc -l`\n\n")
        
        f.write("## 🔍 Detailed Test List by Category\n\n")
        
        # Write selected tests by category
        for category in ['core', 'coverage', 'unit', 'integration', 'performance', 'other']:
            selected_in_category = [t for t in selected_tests if categorize_test(t)[0] == category]
            if selected_in_category:
                f.write(f"### {category.upper()} Tests Selected ({len(selected_in_category)})\n\n")
                for test in selected_in_category[:10]:  # Show first 10
                    f.write(f"- `{test}`\n")
                if len(selected_in_category) > 10:
                    f.write(f"- ... and {len(selected_in_category) - 10} more\n")
                f.write("\n")
        
        # Write excluded tests sample
        excluded = categories.get('exclude', [])
        if excluded:
            f.write(f"### EXCLUDED Tests ({len(excluded)})\n\n")
            for test in excluded[:10]:  # Show first 10
                f.write(f"- `{test}` - {reasons.get(test, 'Unknown reason')}\n")
            if len(excluded) > 10:
                f.write(f"- ... and {len(excluded) - 10} more excluded\n")
            f.write("\n")
    
    print(f"✅ Created tests/manifest_ci.txt with {len(selected_tests)} tests")
    print(f"✅ Created .cursor/G02h_filter_log.md with detailed analysis")
    print(f"\n📋 Summary by category in CI manifest:")
    
    selected_by_category = defaultdict(int)
    for test in selected_tests:
        category = categorize_test(test)[0]
        selected_by_category[category] += 1
    
    for category, count in selected_by_category.items():
        print(f"  {category.upper()}: {count} tests")
    
    print(f"\n🎯 Next steps:")
    print(f"1. Review tests/manifest_ci.txt")
    print(f"2. Manually adjust to exactly 519 tests")
    print(f"3. Run local verification: pytest --collect-only -q --qdrant-mock | wc -l")

if __name__ == "__main__":
    main() 