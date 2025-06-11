#!/bin/bash

# Qdrant Snapshot Scheduler Script
# This script is designed to be run by cron every 6 hours
# It activates the virtual environment and runs the snapshot script with proper logging

# Set script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Paths
VENV_PATH="$PROJECT_ROOT/venv"
SNAPSHOT_SCRIPT="$PROJECT_ROOT/scripts/qdrant_snapshot.py"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/snapshot.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Function to log with timestamp
log_with_timestamp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Start logging
log_with_timestamp "=== Starting Qdrant snapshot process ==="
log_with_timestamp "Script directory: $SCRIPT_DIR"
log_with_timestamp "Project root: $PROJECT_ROOT"
log_with_timestamp "Virtual environment: $VENV_PATH"
log_with_timestamp "Snapshot script: $SNAPSHOT_SCRIPT"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    log_with_timestamp "ERROR: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Check if snapshot script exists
if [ ! -f "$SNAPSHOT_SCRIPT" ]; then
    log_with_timestamp "ERROR: Snapshot script not found at $SNAPSHOT_SCRIPT"
    exit 1
fi

# Activate virtual environment and run snapshot script
log_with_timestamp "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

if [ $? -ne 0 ]; then
    log_with_timestamp "ERROR: Failed to activate virtual environment"
    exit 1
fi

log_with_timestamp "Virtual environment activated successfully"
log_with_timestamp "Python path: $(which python)"
log_with_timestamp "Running snapshot script..."

# Run the snapshot script and capture both stdout and stderr
python "$SNAPSHOT_SCRIPT" >> "$LOG_FILE" 2>&1
SNAPSHOT_EXIT_CODE=$?

# Log the result
if [ $SNAPSHOT_EXIT_CODE -eq 0 ]; then
    log_with_timestamp "Snapshot process completed successfully"
else
    log_with_timestamp "Snapshot process failed with exit code: $SNAPSHOT_EXIT_CODE"
fi

log_with_timestamp "=== Qdrant snapshot process finished ==="
log_with_timestamp ""

# Exit with the same code as the snapshot script
exit $SNAPSHOT_EXIT_CODE
