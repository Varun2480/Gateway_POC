#!/bin/sh
# Replace the {{API_URL}} placeholder in nginx.conf with the value of the API_URL environment variable
echo "Replacing API_URL in nginx.conf"
sed -i "s|{{API_URL}}|$API_URL|g" /etc/nginx/nginx.conf

# Replace the {{API_URL}} placeholder in index.html (if required)
sed -i "s|{{API_URL}}|$API_URL|g" /usr/share/nginx/html/index.html

# Start nginx
nginx -g 'daemon off;'
