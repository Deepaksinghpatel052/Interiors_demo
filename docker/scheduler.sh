#!/bin/sh
# Daily jobs inside Docker, so the server needs no cron entries. Times are Indian time (TZ=Asia/Kolkata).
#   AUTOMATIONS_AT  daily reminders and follow-ups (run_automations)         default 08:00
#   RESET_AT        nightly demo reset (only when DEMO_MODE=True and
#                   RESET_DEMO_NIGHTLY=True; never on a client's live site)    default 03:30
AUTOMATIONS_AT="${AUTOMATIONS_AT:-08:00}"
RESET_AT="${RESET_AT:-03:30}"
echo "Scheduler started ($(date '+%d-%m-%Y %H:%M %Z')): automations at $AUTOMATIONS_AT, demo reset at $RESET_AT"

last_auto=""
last_reset=""
while true; do
    now=$(date +%H:%M)
    today=$(date +%F)
    if [ "$now" = "$AUTOMATIONS_AT" ] && [ "$last_auto" != "$today" ]; then
        last_auto="$today"
        echo "$(date '+%F %T') run_automations"
        python manage.py run_automations || echo "run_automations failed"
    fi
    if [ "$now" = "$RESET_AT" ] && [ "$last_reset" != "$today" ] \
       && [ "$DEMO_MODE" = "True" ] && [ "${RESET_DEMO_NIGHTLY:-True}" = "True" ]; then
        last_reset="$today"
        echo "$(date '+%F %T') reset_demo"
        python manage.py reset_demo --offline || echo "reset_demo failed"
    fi
    sleep 20
done
