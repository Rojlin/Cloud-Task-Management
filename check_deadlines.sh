#!/bin/bash

# Script to run deadline checks with optional frequency parameter

# Parse command-line arguments
DAYS=3
INTERVAL=21600  # 6 hours in seconds

while [[ $# -gt 0 ]]; do
  case $1 in
    --days=*)
      DAYS="${1#*=}"
      shift
      ;;
    --interval=*)
      INTERVAL="${1#*=}"
      shift
      ;;
    --once)
      RUN_ONCE=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Function to check deadlines
check_deadlines() {
    echo "$(date): Checking for tasks with approaching deadlines (${DAYS} days threshold)..."
    python manage.py check_deadlines --days=${DAYS}
    echo "$(date): Deadline check completed."
}

# Run the check once if --once is specified, otherwise run in a loop
if [ "${RUN_ONCE}" = "true" ]; then
    check_deadlines
else
    echo "Starting deadline checking service with ${DAYS} days threshold, running every ${INTERVAL} seconds."
    
    # Run immediately on start
    check_deadlines
    
    # Then run at specified intervals
    while true; do
        echo "Waiting ${INTERVAL} seconds until next deadline check..."
        sleep ${INTERVAL}
        check_deadlines
    done
fi