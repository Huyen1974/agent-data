#!/usr/bin/env python3
"""
CLI140m.69 Batch Test Script - Stabilized Test Suite Runner
Created: June 20, 2025, 16:25 +07
Purpose: Achieve 519/0/0/0/6 (tests/failed/timeout/unknown/skipped) with M1 safety
"""

import subprocess
import sys
import time
import csv
import re
import os
import shutil
import pathlib
from datetime import datetime
from pathlib import Path

class BatchTestRunner:
    def __init__(self):
        # CLI140m.69: Setup environment for stability
        self.setup_environment()
        
        self.batch_size = 3  # ≤3 for M1 safety
        self.timeout_per_test = 8  # 8s per test
        self.batch_timeout = 24  # 3×8s
        self.sleep_between_batches = 0.5
        self.results = []
        self.seen_test_ids = set()  # Track unique test IDs to prevent duplication
        self.test_status_dict = {}  # Track test status for better parsing
        self.log_file = "logs/test_fixes.log"
        self.csv_file = "test_summary_cli140m69.txt"  # Updated for CLI140m.69
        
    def setup_environment(self):
        """CLI140m.69: Setup clean environment for stable test runs"""
        # Set environment variables for stability
        os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
        os.environ['RUN_DEFERRED'] = '0'
        os.environ.pop('PYTEST_ADDOPTS', None)
        
        # Clear pytest cache
        cache_dir = pathlib.Path('.pytest_cache')
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        
        # Clear __pycache__ directories
        subprocess.call(['find', '.', '-type', 'd', '-name', '__pycache__', '-exec', 'rm', '-rf', '{}', '+'], 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    def log_action(self, message):
        """Log action with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"{timestamp}: {message}"
        print(log_msg)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{log_msg}\n")
    
    def collect_tests(self):
        """CLI140m.69: Collect all tests with stabilized arguments and verification"""
        self.log_action("CLI140m.69: Collecting all tests with stabilized arguments")
        
        # CLI140m.69: Run collect-only twice to ensure 519 tests
        for attempt in range(1, 3):
            try:
                result = subprocess.run([
                    'python', '-m', 'pytest', '--collect-only', '-q', 
                    '--cache-clear', '-p', 'no:xdist', '-p', 'no:hypothesis', 
                    '--qdrant-mock'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    test_count = result.stdout.count('::test_')
                    self.log_action(f"Collect attempt {attempt}: {test_count} tests found")
                    if test_count == 519:
                        break
                    elif attempt == 2:
                        self.log_action(f"Warning: Expected 519 tests, got {test_count}")
                else:
                    self.log_action(f"Collect attempt {attempt} failed: {result.stderr}")
                    if attempt == 2:
                        return []
                        
            except subprocess.TimeoutExpired:
                self.log_action("Test collection timed out")
                return []
            except Exception as e:
                self.log_action(f"Test collection error: {e}")
                return []
        
        if result.returncode != 0:
            self.log_action(f"Test collection failed: {result.stderr}")
            return []
        
        # Parse test collection output with optimized regex
        tests = []
        unique_tests = set()  # Ensure uniqueness during collection
        
        # Optimized regex to match only test methods in .py files, skip class names
        test_pattern = re.compile(r'([^:\s]+\.py)::(?:[^\s:]+::)?(test_[^\s:]+)')
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            
            # Skip empty lines, headers, and summary lines
            if not line or line.startswith('=') or 'collected' in line.lower() or line.startswith('<'):
                continue
            
            # Use optimized regex pattern
            match = test_pattern.search(line)
            if match:
                test_file = match.group(1).strip()
                test_method = match.group(2).strip()
                
                # Only include actual test methods
                if test_method.startswith('test_'):
                    # Create unique test identifier
                    test_id = f"{test_file}::{test_method}"
                    
                    if test_id not in unique_tests:
                        unique_tests.add(test_id)
                        tests.append((test_file, test_method))
                        # Initialize status tracking
                        self.test_status_dict[test_id] = 'PENDING'
        
        self.log_action(f"CLI140m.69: Collected {len(tests)} unique tests with optimized regex")
        return tests
    
    def run_test_batch(self, batch_tests):
        """Run a batch of tests with comprehensive logging"""
        test_methods = [test[1] for test in batch_tests]
        test_selector = " or ".join(test_methods)
        
        # CLI140m.69: Stabilized command arguments
        cmd = [
            'python', '-m', 'pytest',
            '-k', test_selector,
            '--cache-clear', '-p', 'no:xdist', '-p', 'no:hypothesis',
            '--qdrant-mock',
            '--timeout=8',
            '-v',
            '--tb=short',
            '--junit-xml=test_fixes.xml'
        ]
        
        self.log_action(f"Running batch: {test_methods}")
        
        try:
            start_time = time.time()
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.batch_timeout
            )
            end_time = time.time()
            runtime = end_time - start_time
            
            # Parse pytest output for individual test results
            self.parse_pytest_output(result.stdout, batch_tests, runtime)
            
            self.log_action(f"Batch completed in {runtime:.2f}s")
            return True
            
        except subprocess.TimeoutExpired:
            # Handle timeout - mark all tests as TIMEOUT
            for test_file, test_method in batch_tests:
                test_id = f"{test_file}::{test_method}"
                if test_id not in self.seen_test_ids:
                    self.seen_test_ids.add(test_id)
                    self.test_status_dict[test_id] = 'TIMEOUT'
                    self.results.append({
                        'name': test_method,
                        'file': test_file,
                        'status': 'TIMEOUT',
                        'error_runtime_reason': f'Batch timeout >{self.batch_timeout}s',
                        'log_line': f'TIMEOUT: {test_method} in {test_file}'
                    })
            self.log_action(f"Batch TIMEOUT after {self.batch_timeout}s")
            return False
            
        except Exception as e:
            # Handle other errors - mark tests as ERROR
            for test_file, test_method in batch_tests:
                test_id = f"{test_file}::{test_method}"
                if test_id not in self.seen_test_ids:
                    self.seen_test_ids.add(test_id)
                    self.test_status_dict[test_id] = 'ERROR'
                    self.results.append({
                        'name': test_method,
                        'file': test_file,
                        'status': 'ERROR',
                        'error_runtime_reason': f'Execution error: {e}',
                        'log_line': f'ERROR: {test_method} in {test_file} - {e}'
                    })
            self.log_action(f"Batch ERROR: {e}")
            return False
    
    def parse_pytest_output(self, output, batch_tests, batch_runtime):
        """Parse pytest output to extract individual test results with optimized regex"""
        lines = output.split('\n')
        
        # Track which tests we've seen results for
        seen_tests = set()
        
        for line in lines:
            # Look for test result patterns with optimized regex
            if '::test_' in line:
                # PASSED pattern
                if ' PASSED ' in line:
                    test_info = self.extract_test_info(line)
                    if test_info:
                        test_id = f"{test_info['file']}::{test_info['method']}"
                        if test_id not in self.seen_test_ids:
                            self.seen_test_ids.add(test_id)
                            seen_tests.add(test_info['method'])
                            self.test_status_dict[test_id] = 'PASSED'
                            self.results.append({
                                'name': test_info['method'],
                                'file': test_info['file'],
                                'status': 'PASSED',
                                'error_runtime_reason': f'{test_info.get("runtime", "N/A")}',
                                'log_line': line.strip()
                            })
                
                # FAILED pattern
                elif ' FAILED ' in line:
                    test_info = self.extract_test_info(line)
                    if test_info:
                        test_id = f"{test_info['file']}::{test_info['method']}"
                        if test_id not in self.seen_test_ids:
                            self.seen_test_ids.add(test_id)
                            seen_tests.add(test_info['method'])
                            self.test_status_dict[test_id] = 'FAILED'
                            self.results.append({
                                'name': test_info['method'],
                                'file': test_info['file'],
                                'status': 'FAILED',
                                'error_runtime_reason': self.extract_failure_reason(lines, line),
                                'log_line': line.strip()
                            })
                
                # SKIPPED pattern
                elif ' SKIPPED ' in line:
                    test_info = self.extract_test_info(line)
                    if test_info:
                        test_id = f"{test_info['file']}::{test_info['method']}"
                        if test_id not in self.seen_test_ids:
                            self.seen_test_ids.add(test_id)
                            seen_tests.add(test_info['method'])
                            self.test_status_dict[test_id] = 'SKIPPED'
                            self.results.append({
                                'name': test_info['method'],
                                'file': test_info['file'],
                                'status': 'SKIPPED',
                                'error_runtime_reason': self.extract_skip_reason(line),
                                'log_line': line.strip()
                            })
                
                # CLI140m.69: XFAIL pattern - handle separately to avoid UNKNOWN classification
                elif ' XFAIL ' in line:
                    test_info = self.extract_test_info(line)
                    if test_info:
                        test_id = f"{test_info['file']}::{test_info['method']}"
                        if test_id not in self.seen_test_ids:
                            self.seen_test_ids.add(test_id)
                            seen_tests.add(test_info['method'])
                            self.test_status_dict[test_id] = 'XFAIL'
                            self.results.append({
                                'name': test_info['method'],
                                'file': test_info['file'],
                                'status': 'XFAIL',
                                'error_runtime_reason': 'Expected failure',
                                'log_line': line.strip()
                            })
        
        # Check for tests that took >8s (SLOW)
        avg_runtime = batch_runtime / len(batch_tests)
        if avg_runtime > 8:
            for test_file, test_method in batch_tests:
                test_id = f"{test_file}::{test_method}"
                if test_method in seen_tests:
                    # Update existing result to mark as SLOW
                    for result in self.results:
                        if result['name'] == test_method and result['file'] == test_file:
                            if result['status'] == 'PASSED':
                                result['status'] = 'SLOW'
                                result['error_runtime_reason'] = f'>{avg_runtime:.2f}s (>8s threshold)'
                                self.test_status_dict[test_id] = 'SLOW'
        
        # OPTIMIZED: Only mark tests as UNKNOWN if they're truly missing from output
        # Use test_status_dict to track which tests were actually expected
        for test_file, test_method in batch_tests:
            test_id = f"{test_file}::{test_method}"
            if test_method not in seen_tests and test_id not in self.seen_test_ids:
                # Double-check if this test was actually expected to run
                if test_id in self.test_status_dict and self.test_status_dict[test_id] == 'PENDING':
                    self.seen_test_ids.add(test_id)
                    self.test_status_dict[test_id] = 'UNKNOWN'
                    self.results.append({
                        'name': test_method,
                        'file': test_file,
                        'status': 'UNKNOWN',
                        'error_runtime_reason': 'No result found in output',
                        'log_line': f'UNKNOWN: {test_method} in {test_file}'
                    })
    
    def extract_test_info(self, line):
        """Extract test file and method from pytest output line with optimized regex"""
        # Optimized pattern to handle both formats:
        # tests/file.py::test_method PASSED/FAILED/SKIPPED
        # tests/file.py::TestClass::test_method PASSED/FAILED/SKIPPED
        match = re.search(r'([^:\s]+\.py)::(?:[^\s:]+::)?(test_[^\s:]+)', line)
        if match:
            return {
                'file': match.group(1),
                'method': match.group(2),
                'runtime': self.extract_runtime(line)
            }
        return None
    
    def extract_runtime(self, line):
        """Extract runtime from pytest line if available"""
        # Look for patterns like [0.001s] or (0.001s)
        match = re.search(r'[\[\(](\d+\.\d+)s[\]\)]', line)
        if match:
            return f'{match.group(1)}s'
        return 'N/A'
    
    def extract_failure_reason(self, lines, failed_line):
        """Extract failure reason from pytest output"""
        # Simple approach - look for common failure patterns
        if 'AssertionError' in failed_line:
            return 'AssertionError'
        elif 'TimeoutError' in failed_line:
            return 'TimeoutError'
        elif 'Exception' in failed_line:
            return 'Exception'
        else:
            return 'Test failure'
    
    def extract_skip_reason(self, line):
        """Extract skip reason from pytest output"""
        # Look for skip reason in parentheses or brackets
        match = re.search(r'SKIPPED\s*[\[\(]([^\]\)]+)[\]\)]', line)
        if match:
            return match.group(1)
        return 'Skipped'
    
    def save_results_to_csv(self):
        """Save all results to CSV file"""
        self.log_action(f"Saving {len(self.results)} test results to {self.csv_file}")
        
        with open(self.csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['name', 'file', 'status', 'error_runtime_reason', 'log_line']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in self.results:
                writer.writerow(result)
        
        # Log summary statistics
        status_counts = {}
        for result in self.results:
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        self.log_action(f"Test summary: {status_counts}")
    
    def run_all_tests(self):
        """Main execution method"""
        self.log_action("Starting CLI140m.61 batch test execution with optimized regex parsing")
        
        # Verify pytest-timeout is installed
        try:
            subprocess.run(['python', '-c', 'import pytest_timeout'], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            self.log_action("Installing pytest-timeout")
            subprocess.run(['pip', 'install', 'pytest-timeout'], check=True)
        
        # Clean up previous test data
        self.log_action("Cleaning up previous test data")
        subprocess.run(['rm', '-f', '.testmondata'], capture_output=True)
        
        # Collect all tests
        all_tests = self.collect_tests()
        if not all_tests:
            self.log_action("No tests collected, exiting")
            return False
        
        # Split into batches
        batches = []
        for i in range(0, len(all_tests), self.batch_size):
            batch = all_tests[i:i + self.batch_size]
            batches.append(batch)
        
        self.log_action(f"Created {len(batches)} batches of ≤{self.batch_size} tests")
        
        # Run each batch (with optional max_batches limit)
        successful_batches = 0
        max_batches_to_run = getattr(self, 'max_batches', None)
        if max_batches_to_run:
            batches = batches[:max_batches_to_run]
            self.log_action(f"Limited to {max_batches_to_run} batches for testing")
        
        for i, batch in enumerate(batches, 1):
            self.log_action(f"Running batch {i}/{len(batches)}")
            
            if self.run_test_batch(batch):
                successful_batches += 1
            
            # Sleep between batches for M1 safety
            if i < len(batches):
                time.sleep(self.sleep_between_batches)
        
        # Save results
        self.save_results_to_csv()
        
        self.log_action(f"Completed: {successful_batches}/{len(batches)} batches successful")
        return True

def main():
    """Main entry point with CLI argument support"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CLI140m.61 Batch Test Runner with Optimized Regex Parsing')
    parser.add_argument('--batch-size', type=int, default=3, help='Number of tests per batch (default: 3)')
    parser.add_argument('--max-batches', type=int, default=None, help='Maximum number of batches to run')
    parser.add_argument('--timeout', type=int, default=8, help='Timeout per test in seconds (default: 8)')
    
    args = parser.parse_args()
    
    runner = BatchTestRunner()
    runner.batch_size = args.batch_size
    runner.timeout_per_test = args.timeout
    runner.batch_timeout = args.batch_size * args.timeout
    
    # If max_batches is specified, modify the run_all_tests method
    if args.max_batches:
        runner.max_batches = args.max_batches
    
    success = runner.run_all_tests()
    
    if success:
        print(f"\nBatch testing completed. Results saved to {runner.csv_file}")
        print("Check logs/test_fixes.log for detailed execution log")
    else:
        print("Batch testing failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 