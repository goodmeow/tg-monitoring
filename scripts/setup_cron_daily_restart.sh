#!/usr/bin/env bash
set -euo pipefail

# Script to set up daily restart for tg-monitoring bot
# This script will add a cron job for daily restarts

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_DIR/logs/daily-restart.log"

echo "Setting up daily restart for tg-monitoring bot..."

# Check if the log directory exists
if [ ! -d "$PROJECT_DIR/logs" ]; then
    echo "Creating logs directory..."
    mkdir -p "$PROJECT_DIR/logs"
fi

# Create the restart script
RESTART_SCRIPT="$PROJECT_DIR/scripts/daily_restart.sh"
cat > "$RESTART_SCRIPT" << EOF
#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$PROJECT_DIR"

# Change to the project directory
cd "\$PROJECT_DIR"

# Log the restart attempt
echo "\$(date): Initiating daily restart of tg-monitoring" >> logs/daily-restart.log

# Perform the restart using the Makefile target
make daily-restart

# Log completion
echo "\$(date): Completed daily restart attempt" >> logs/daily-restart.log
EOF

# Make the script executable
chmod +x "$RESTART_SCRIPT"

echo "Created daily restart script: $RESTART_SCRIPT"

# Instructions for adding to crontab
echo ""
echo "To set up the daily restart, run the following command:"
echo "crontab -e"
echo ""
echo "Then add this line to schedule a daily restart at 2 AM:"
echo "0 2 * * * $RESTART_SCRIPT"
echo ""
echo "Or, if you want to use the Makefile directly:"
echo "0 2 * * * cd $PROJECT_DIR && make daily-restart >> $PROJECT_DIR/logs/cron-restart.log 2>&1"
echo ""

# Check if crontab command exists
if command -v crontab &> /dev/null; then
    echo ""
    echo "Checking for existing tg-monitoring related cron jobs..."
    if crontab -l 2>/dev/null | grep -i tg-monitor; then
        echo "Existing tg-monitor related cron job found."
        echo "If you want to remove it, run: crontab -e and delete the relevant line"
    else
        echo "No existing tg-monitor related cron jobs found."
    fi
    
    echo ""
    echo "To add the cron job now, run:"
    echo "crontab -e"
    echo "# Then add the line as shown above"
else
    echo ""
    echo "Crontab command not found. You may need to install cron."
    echo "On Ubuntu/Debian: sudo apt-get install cron"
fi

echo ""
echo "Setup complete!"
