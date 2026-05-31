#!/bin/bash
# Deploy inputs-page fix to PDU. Run from your PC (NOT from inside SSH to the PDU).
#
# Usage:
#   ./deploy-to-pdu.sh
#   ./deploy-to-pdu.sh root@192.168.1.66

set -e

PDU="${1:-ne@192.168.1.66}"
NE="$(cd "$(dirname "$0")" && pwd)"

echo "Deploying from: $NE"
echo "Deploying to:   $PDU"
echo ""

echo ">> Copying files to /tmp on PDU..."
scp "$NE/app/helpers.py"            "$PDU:/tmp/helpers.py"
scp "$NE/app/views.py"              "$PDU:/tmp/views.py"
scp "$NE/ne/urls.py"                "$PDU:/tmp/urls.py"
scp "$NE/static/js/app/live_inputs.js" "$PDU:/tmp/live_inputs.js"
scp "$NE/templates/inputs.html"     "$PDU:/tmp/inputs.html"

echo ""
echo ">> Files copied to /tmp. Now run ON THE PDU as root:"
echo ""
cat <<'EOF'
su root
cp /tmp/helpers.py      /opt/ne/app/helpers.py
cp /tmp/views.py        /opt/ne/app/views.py
cp /tmp/urls.py         /opt/ne/ne/urls.py
cp /tmp/inputs.html     /opt/ne/templates/inputs.html
cp /tmp/live_inputs.js  /opt/ne/static/js/app/live_inputs.js
kill $(pgrep -f "manage.py runserver") 2>/dev/null || true
cd /opt/ne && python3 manage.py runserver 0.0.0.0:8000 &
EOF

echo ""
echo "Then hard-refresh the browser: http://192.168.1.66/en/inputs/"
