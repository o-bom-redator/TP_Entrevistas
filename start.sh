#!/bin/zsh
# Starts the server (if needed) and opens the teleprompter as a small window with no
# address bar, centered at the top of the screen, right under the webcam (macOS).
# Usage: ./start.sh [width] [height]
cd "$(dirname "$0")"

W=${1:-560}
H=${2:-260}
URL="http://localhost:${PORT:-8765}/?compact=1"

if ! curl -s -o /dev/null "$URL"; then
  python3 server.py &
  sleep 1
fi

if [[ -d "/Applications/Google Chrome.app" ]]; then
  SW=$(osascript -e 'tell application "Finder" to get item 3 of (get bounds of window of desktop)')
  X=$(( (SW - W) / 2 ))
  # A separate profile forces a new Chrome process, so the size/position flags are honored.
  open -na "Google Chrome" --args --user-data-dir="$HOME/.ai-teleprompter-chrome" --no-first-run \
    --app="$URL" --window-size=$W,$H --window-position=$X,0
else
  open "$URL"
fi

wait
