#!/bin/sh
set -eu

# Generate /app/public/config.js from runtime env vars so the browser bundle
# can read NEXT_PUBLIC_*-style values without rebuilding the image.
# Loaded by app/layout.tsx via <Script src="/config.js" strategy="beforeInteractive" />.

CONFIG_FILE="/app/public/config.js"

API_URL="${MARROW_API_URL:-http://localhost:8000}"
API_KEY="${MARROW_API_KEY:-}"
OIDC_ENABLED="${MARROW_OIDC_ENABLED:-false}"

# Escape backslash, double-quote, and newline for safe JSON-ish embedding.
escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e ':a;N;$!ba;s/\n/\\n/g'
}

cat > "$CONFIG_FILE" <<EOF
window.__MARROW_CONFIG__ = {
  apiUrl: "$(escape "$API_URL")",
  apiKey: "$(escape "$API_KEY")",
  oidcEnabled: $([ "$OIDC_ENABLED" = "true" ] && echo "true" || echo "false")
};
EOF

exec "$@"
