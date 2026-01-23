#!/bin/sh
set -e
: "${API_BASE_URL:=http://localhost:8080}"
cat > /usr/share/nginx/html/config.js <<EOF
window.API_BASE_URL = "${API_BASE_URL}";
EOF
exec "$@"