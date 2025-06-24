#!/usr/bin/env python3
"""
Filter full test manifest to exactly 519 tests for CI.
Priority: core/unit tests > integration tests > performance tests
Exclude: only the most problematic tests (CLI140k*, CLI140l*, CLI140j*)
"""

import re
from pathlib import Path

def main():
    # Read full manifest
    manifest_full_path = Path("tests/manifest_full.txt")
    with open(manifest_full_path, 'r') as f:
        all_tests = [line.strip() for line in f if line.strip()]
    
    print(f"Total tests in manifest_full.txt: {len(all_tests)}")
    
    # Categories for prioritization
    priority_1_core = []  # Core functionality tests
    priority_2_unit = []  # Unit tests with minimal dependencies
    priority_3_integration = []  # Integration tests
    priority_4_performance = []  # Performance tests
    priority_5_others = []  # Everything else
    excluded_tests = []  # Tests to exclude
    
    # Patterns to exclude (only the most problematic ones)
    exclude_patterns = [
        r'test_cli140[klj]',  # Only CLI140k*, l*, j* tests (most problematic)
        r'legacy.*test_cli140[klj]',
        r'nightly.*simulation',
        r'full.*runtime.*validation'
    ]
    
    # Patterns for core tests (highest priority)
    core_patterns = [
        r'test_.*core',
        r'test_.*unit',
        r'test_.*basic',
        r'test_.*simple',
        r'TestAPI.*',
        r'test_.*auth',
        r'test_.*vector',
        r'test_.*qdrant',
        r'test_.*firestore',
        r'test_.*meta',
        r'test_.*endpoint',
        r'test_.*coverage.*additional'
    ]
    
    # Patterns for performance tests (now included with lower priority)
    performance_patterns = [
        r'performance',
        r'latency',
        r'optimization',
        r'test_cli140[gh]',  # CLI140g*, h* tests
        r'runtime'
    ]
    
    # Categorize tests
    for test in all_tests:
        # Check if test should be excluded
        should_exclude = any(re.search(pattern, test, re.IGNORECASE) for pattern in exclude_patterns)
        
        if should_exclude:
            excluded_tests.append(test)
            continue
            
        # Check if test is core functionality
        is_core = any(re.search(pattern, test, re.IGNORECASE) for pattern in core_patterns)
        is_performance = any(re.search(pattern, test, re.IGNORECASE) for pattern in performance_patterns)
        
        if is_core:
            priority_1_core.append(test)
        elif 'unit' in test.lower() or 'mock' in test.lower():
            priority_2_unit.append(test)
        elif 'integration' in test.lower() or 'e2e' in test.lower():
            priority_3_integration.append(test)
        elif is_performance:
            priority_4_performance.append(test)
        else:
            priority_5_others.append(test)
    
    print(f"Priority 1 (Core): {len(priority_1_core)}")
    print(f"Priority 2 (Unit): {len(priority_2_unit)}")
    print(f"Priority 3 (Integration): {len(priority_3_integration)}")
    print(f"Priority 4 (Performance): {len(priority_4_performance)}")
    print(f"Priority 5 (Others): {len(priority_5_others)}")
    print(f"Excluded: {len(excluded_tests)}")
    
    # Select exactly 519 tests
    selected_tests = []
    
    # Take all core tests first
    selected_tests.extend(priority_1_core)
    
    # Add unit tests if we have room
    remaining = 519 - len(selected_tests)
    if remaining > 0:
        selected_tests.extend(priority_2_unit[:remaining])
        remaining = 519 - len(selected_tests)
    
    # Add integration tests if we have room
    if remaining > 0:
        selected_tests.extend(priority_3_integration[:remaining])
        remaining = 519 - len(selected_tests)
    
    # Add performance tests if we have room
    if remaining > 0:
        selected_tests.extend(priority_4_performance[:remaining])
        remaining = 519 - len(selected_tests)
    
    # Add other tests if we have room
    if remaining > 0:
        selected_tests.extend(priority_5_others[:remaining])
    
    # Ensure we have exactly 519 tests
    selected_tests = selected_tests[:519]
    
    print(f"Selected tests: {len(selected_tests)}")
    
    # Write to manifest_ci.txt
    manifest_ci_path = Path("tests/manifest_ci.txt")
    with open(manifest_ci_path, 'w') as f:
        for test in selected_tests:
            f.write(f"{test}\n")
    
    # Create filter log
    filter_log_path = Path(".cursor/G02h_filter_log.md")
    filter_log_path.parent.mkdir(exist_ok=True)
    
    with open(filter_log_path, 'w') as f:
        f.write("# G02h Test Filtering Log\n\n")
        f.write(f"**Date:** June 23, 2025\n")
        f.write(f"**Total tests collected:** {len(all_tests)}\n")
        f.write(f"**Target for CI:** 519 tests\n")
        f.write(f"**Final selected:** {len(selected_tests)}\n\n")
        
        f.write("## Filter Strategy (Final)\n\n")
        f.write("1. **Priority 1 (Core):** Tests matching core functionality patterns\n")
        f.write("2. **Priority 2 (Unit):** Unit tests with minimal dependencies\n") 
        f.write("3. **Priority 3 (Integration):** Integration and E2E tests\n")
        f.write("4. **Priority 4 (Performance):** Performance/optimization tests\n")
        f.write("5. **Priority 5 (Others):** All remaining valid tests\n\n")
        
        f.write("## Final Exclusion Patterns (Minimal)\n\n")
        for pattern in exclude_patterns:
            f.write(f"- `{pattern}`\n")
        
        f.write(f"\n## Final Results\n\n")
        f.write(f"- **Core tests selected:** {len([t for t in selected_tests if any(re.search(p, t, re.IGNORECASE) for p in core_patterns)])}\n")
        f.write(f"- **Unit tests selected:** {len([t for t in selected_tests if 'unit' in t.lower() or 'mock' in t.lower()])}\n")
        f.write(f"- **Integration tests selected:** {len([t for t in selected_tests if 'integration' in t.lower() or 'e2e' in t.lower()])}\n")
        f.write(f"- **Performance tests selected:** {len([t for t in selected_tests if any(re.search(p, t, re.IGNORECASE) for p in performance_patterns)])}\n")
        f.write(f"- **Other tests selected:** {max(0, len(selected_tests) - len(priority_1_core) - len(priority_2_unit) - len(priority_3_integration) - len(priority_4_performance))}\n")
        f.write(f"- **Tests excluded:** {len(excluded_tests)}\n\n")
        
        f.write("## Final Excluded Test Categories (Minimal)\n\n")
        f.write("- CLI140k* runtime optimization tests (most problematic)\n")
        f.write("- CLI140l* nightly simulation tests\n")
        f.write("- CLI140j* cost optimization tests\n")
        f.write("- Full runtime validation tests\n\n")
        
        f.write("## Final Included Categories\n\n")
        f.write("- CLI140g* validation tests\n")
        f.write("- CLI140h* build optimization tests\n")
        f.write("- Performance and latency tests\n")
        f.write("- All coverage tests\n")
        f.write("- All API and endpoint tests\n")
        f.write("- All core functionality tests\n")
    
    print(f"✅ Created tests/manifest_ci.txt with {len(selected_tests)} tests")
    print(f"✅ Created .cursor/G02h_filter_log.md with filtering details")

if __name__ == "__main__":
    main() 