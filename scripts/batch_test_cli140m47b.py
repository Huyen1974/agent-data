#!/usr/bin/env python3
"""
CLI140m.47c Batch Test Script - Comprehensive Test Logging
Created: June 18, 2025, 15:21 +07
Purpose: Log ALL tests (Pass, F, S, Skipped, Timeout) with M1 safety
"""

import subprocess
import sys
import time
import csv
import re
from datetime import datetime
from pathlib import Path

class BatchTestRunner:
    def __init__(self):
        self.batch_size = 3  # ≤3 for M1 safety
        self.timeout_per_test = 8  # 8s per test
        self.batch_timeout = 24  # 3×8s
        self.sleep_between_batches = 0.5
        self.results = []
        self.log_file = "logs/test_fixes.log"
        self.csv_file = "test_summary_cli140m47.txt"
        
    def log_action(self, message):
        """Log action with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"{timestamp}: {message}"
        print(log_msg)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"{log_msg}\n")
    
    def collect_tests(self):
        """Collect all tests using pytest --collect-only"""
        self.log_action("Collecting all tests with pytest --collect-only")
        
        try:
            result = subprocess.run([
                'python', '-m', 'pytest', '--collect-only', '-q'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.log_action(f"Test collection failed: {result.stderr}")
                return []
            
            # Parse test collection output
            tests = []
            for line in result.stdout.split('\n'):
                # Look for test method patterns
                if '::test_' in line and not line.startswith(' '):
                    # Extract test file and method
                    parts = line.strip().split('::')
                    if len(parts) >= 2:
                        test_file = parts[0]
                        test_method = parts[1]
                        tests.append((test_file, test_method))
            
            self.log_action(f"Collected {len(tests)} total tests")
            return tests
            
        except subprocess.TimeoutExpired:
            self.log_action("Test collection timed out")
            return []
        except Exception as e:
            self.log_action(f"Test collection error: {e}")
            return []
    
    def run_test_batch(self, batch_tests):
        """Run a batch of tests with comprehensive logging"""
        test_methods = [test[1] for test in batch_tests]
        test_selector = " or ".join(test_methods)
        
        cmd = [
            'python', '-m', 'pytest',
            '-k', test_selector,
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
        """Parse pytest output to extract individual test results"""
        lines = output.split('\n')
        
        # Track which tests we've seen results for
        seen_tests = set()
        
        for line in lines:
            # Look for test result patterns
            if '::test_' in line:
                # PASSED pattern
                if ' PASSED ' in line:
                    test_info = self.extract_test_info(line)
                    if test_info:
                        test_method = test_info['method']
                        seen_tests.add(test_method)
                        self.results.append({
                            'name': test_method,
                            'file': test_info['file'],
                            'status': 'PASSED',
                            'error_runtime_reason': f'{test_info.get("runtime", "N/A")}',
                            'log_line': line.strip()
                        })
                
                # FAILED pattern
                elif ' FAILED ' in line:
                    test_info = self.extract_test_info(line)
                    if test_info:
                        test_method = test_info['method']
                        seen_tests.add(test_method)
                        self.results.append({
                            'name': test_method,
                            'file': test_info['file'],
                            'status': 'FAILED',
                            'error_runtime_reason': self.extract_failure_reason(lines, line),
                            'log_line': line.strip()
                        })
                
                # SKIPPED pattern
                elif ' SKIPPED ' in line:
                    test_info = self.extract_test_info(line)
                    if test_info:
                        test_method = test_info['method']
                        seen_tests.add(test_method)
                        self.results.append({
                            'name': test_method,
                            'file': test_info['file'],
                            'status': 'SKIPPED',
                            'error_runtime_reason': self.extract_skip_reason(line),
                            'log_line': line.strip()
                        })
        
        # Check for tests that took >8s (SLOW)
        avg_runtime = batch_runtime / len(batch_tests)
        if avg_runtime > 8:
            for test_file, test_method in batch_tests:
                if test_method in seen_tests:
                    # Update existing result to mark as SLOW
                    for result in self.results:
                        if result['name'] == test_method and result['file'] == test_file:
                            if result['status'] == 'PASSED':
                                result['status'] = 'SLOW'
                                result['error_runtime_reason'] = f'>{avg_runtime:.2f}s (>8s threshold)'
        
        # Mark any unseen tests as missing/unknown
        for test_file, test_method in batch_tests:
            if test_method not in seen_tests:
                self.results.append({
                    'name': test_method,
                    'file': test_file,
                    'status': 'UNKNOWN',
                    'error_runtime_reason': 'No result found in output',
                    'log_line': f'UNKNOWN: {test_method} in {test_file}'
                })
    
    def extract_test_info(self, line):
        """Extract test file and method from pytest output line"""
        # Pattern: tests/test_file.py::test_method PASSED/FAILED/SKIPPED
        match = re.search(r'([^:]+)::([^:\s]+)', line)
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
        self.log_action("Starting CLI140m.47c batch test execution")
        
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
        
        # Run each batch
        successful_batches = 0
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
    """Main entry point"""
    runner = BatchTestRunner()
    success = runner.run_all_tests()
    
    if success:
        print(f"\nBatch testing completed. Results saved to {runner.csv_file}")
        print("Check logs/test_fixes.log for detailed execution log")
    else:
        print("Batch testing failed. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 