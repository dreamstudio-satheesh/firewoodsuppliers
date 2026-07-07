#!/bin/bash
# One-time setup: creates a desktop launcher for Firewood Billing
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cat > "$HOME/Desktop/Firewood Billing.desktop" << EOF
[Desktop Entry]
Name=Firewood Billing
Comment=Firewood Seller Billing Software
Exec=$SCRIPT_DIR/run.sh
Path=$SCRIPT_DIR
Terminal=false
Type=Application
Categories=Office;Finance;
EOF
chmod +x "$HOME/Desktop/Firewood Billing.desktop"
echo "✅ Done! Double-click 'Firewood Billing' on your Desktop to launch."
