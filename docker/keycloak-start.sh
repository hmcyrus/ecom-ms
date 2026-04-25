#!/bin/sh
# Starts Keycloak in dev mode, then patches both realms to sslRequired=NONE via
# the loopback address (kcadm via localhost bypasses the sslRequired=external check).
# Writes /tmp/keycloak-ready once patching is done so the healthcheck can signal
# service_healthy to dependent containers.

set -e

KC_HOME=/opt/keycloak

# Launch Keycloak in the background so we can run kcadm against it.
"$KC_HOME/bin/kc.sh" start-dev --import-realm &
KC_PID=$!

echo "Waiting for Keycloak to accept admin logins..."
until "$KC_HOME/bin/kcadm.sh" config credentials \
      --server http://localhost:8080 \
      --realm master \
      --user "${KEYCLOAK_ADMIN}" \
      --password "${KEYCLOAK_ADMIN_PASSWORD}" \
      2>/dev/null; do
  sleep 3
done

echo "Patching master realm: sslRequired=NONE"
"$KC_HOME/bin/kcadm.sh" update realms/master -s sslRequired=NONE

echo "Waiting for bookstore realm to be imported..."
until "$KC_HOME/bin/kcadm.sh" get realms/bookstore >/dev/null 2>&1; do
  sleep 3
done

echo "Patching bookstore realm: sslRequired=NONE"
"$KC_HOME/bin/kcadm.sh" update realms/bookstore -s sslRequired=NONE

echo "Keycloak ready."
touch /tmp/keycloak-ready

# Keep the container alive — the main process is the backgrounded kc.sh.
wait $KC_PID
