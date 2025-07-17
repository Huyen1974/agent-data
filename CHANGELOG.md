# Changelog

All notable changes to this project will be documented in this file.

## Phase 1 Changes

### Security Improvements
- Switched to bullseye base image for security (from buster EOL)
- Fixed CVE vulnerabilities via package upgrades
- Implemented hashed dependency locking with requirements.lock
- Added Trivy vulnerability scanning with permissive settings for stabilization
- Established baseline test collection (141 test files) for CI consistency

### CI/CD Enhancements
- Added dynamic CI/test badges with shields.io JSON endpoints
- Implemented baseline test artifact generation and SHA verification
- Added TEST_COUNT environment variable for dynamic badge updates
- Configured Workload Identity Federation for secure GCP integration

### Documentation
- Added comprehensive CI status and security badges
- Created TODO issue (#27) for stricter Trivy settings post-Phase 1
- Established consistent test baseline from CI container environment
