#!/bin/bash
# Double-click ONCE to make your Mac refresh the predictions by itself every day at 09:00.
# (First time only: right-click > Open > Open.) If the Mac is asleep at 09:00 it runs when it wakes.
# To stop it:  launchctl unload ~/Library/LaunchAgents/com.f1predictor.refresh.plist
#
# Not tested by the author on a real Mac: if it prints an error, copy it to Claude.
cd "$(dirname "$0")"
DIR="$(pwd)"
chmod +x "$DIR/Refresh_Quietly.command"
PLIST="$HOME/Library/LaunchAgents/com.f1predictor.refresh.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PLISTEND
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.f1predictor.refresh</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$DIR/Refresh_Quietly.command</string></array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>WorkingDirectory</key><string>$DIR</string>
</dict>
</plist>
PLISTEND
launchctl unload "$PLIST" 2>/dev/null
if launchctl load "$PLIST"; then
  echo "Done. The predictions will refresh every day at 09:00 (see Predictions/refresh_log.txt)."
else
  echo "Could not load the schedule: copy the message above to Claude."
fi
read -p "Press Enter to close"
