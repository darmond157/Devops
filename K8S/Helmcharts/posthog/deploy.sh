#!/usr/bin/env bash

set -e

export DEBIAN_FRONTEND="noninteractive"
export RESTART_MODE="l"
export POSTHOG_APP_TAG="latest"
export POSTHOG_SECRET="aa0f2e2af8e7d702bbac762d63123e64afe3663fabff73beca5b2773"
export ENCRYPTION_SALT_KEYS="04b10b15868b5ceefdfbc461a8def71c"
export DOMAIN="temp.ir"
export REGISTRY_URL="posthog/posthog"
export TLS_BLOCK="acme_ca https://acme-staging-v02.api.letsencrypt.org/directory"

git clone --filter=blob:none https://github.com/PostHog/posthog.git &> /dev/null || true

# Write .env file
cat > .env <<EOF
POSTHOG_SECRET=$POSTHOG_SECRET
ENCRYPTION_SALT_KEYS=$ENCRYPTION_SALT_KEYS
DOMAIN=$DOMAIN
TLS_BLOCK=$TLS_BLOCK
REGISTRY_URL=$REGISTRY_URL
CADDY_TLS_BLOCK=$TLS_BLOCK
CADDY_HOST="$DOMAIN, http://, https://"
POSTHOG_APP_TAG=$POSTHOG_APP_TAG
EOF

# Download GeoLite2-City.mmdb GeoIP database file if it doesn't exist
sudo apt-get install -y --no-install-recommends curl ca-certificates brotli
mkdir -p ./share
curl -L 'https://mmdbcdn.posthog.net/' --http1.1 | brotli --decompress --output=./share/GeoLite2-City.mmdb &&
echo '{\"date\": \"'"$(date +%Y-%m-%d)"'\"}' > ./share/GeoLite2-City.json;
chmod 644 ./share/GeoLite2-City.mmdb &&
chmod 644 ./share/GeoLite2-City.json

# start up the stack
echo "Configuring Docker Compose...."
rm -f docker-compose.yml
cp posthog/docker-compose.base.yml docker-compose.base.yml
cp posthog/docker-compose.hobby.yml docker-compose.yml

sudo -E docker-compose -f docker-compose.yml up -d --no-build --pull always; then
