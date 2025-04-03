#!/bin/sh
# Replace the {{API_URL}} placeholder in nginx.conf with the value of the API_URL environment variable
echo "Replacing API_URL in nginx.conf"
sed -i "s|{{API_URL}}|$API_URL|g" /etc/nginx/nginx.conf

# Start nginx
nginx -g 'daemon off;'
