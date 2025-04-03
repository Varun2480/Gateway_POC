# Stage 1: Build the Angular app
FROM node:18-alpine as builder

WORKDIR /app

# Copy package.json and package-lock.json first for efficient caching
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the source code
COPY . .

# Copy nginx.conf and entrypoint.sh
COPY nginx.conf entrypoint.sh ./

# Build the application
RUN npm run build -- --configuration production

# Stage 2: Serve the app with Nginx
FROM nginx:alpine

WORKDIR /app

# Copy the built Angular app
# COPY --from=builder /app/dist/* /usr/share/nginx/html
COPY --from=builder /app/dist/restaurant-app/browser/* /usr/share/nginx/html

# Copy the custom Nginx config
COPY --from=builder /app/nginx.conf /etc/nginx/nginx.conf

# Copy the entrypoint script
COPY --from=builder /app/entrypoint.sh /entrypoint.sh

# Make entrypoint script executable
RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Expose port 80 for the app
EXPOSE 80
