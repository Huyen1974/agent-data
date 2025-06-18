#!/usr/bin/env python3
"""
Test timeout fake for CLI140m.47 verification
This test is designed to timeout and demonstrate timeout logging
"""

import time
import pytest


class TestTimeoutFake:
    """Test class with intentional timeout for verification"""
    
    def test_timeout_fake(self):
        """Test that will timeout after 10 seconds to demonstrate timeout logging"""
        # Sleep for 10 seconds to force timeout (batch timeout is 24s but test timeout demo is 10s)
        time.sleep(10)
        assert True, "This should timeout before reaching this assertion"
    
    def test_timeout_fake_short(self):
        """Shorter timeout test for verification"""
        time.sleep(5)
        assert True, "This might also timeout in verification mode" 