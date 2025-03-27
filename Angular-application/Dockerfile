# Stage 1: Build the Angular app
FROM node:18-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build -- --configuration production

# Stage 2: Serve the app with Nginx
FROM nginx:alpine

# Copy the built Angular app
COPY --from=builder /app/dist/restaurant-app /usr/share/nginx/html

# Copy the custom Nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy the entrypoint script
COPY entrypoint.sh /entrypoint.sh

# Make entrypoint script executable
RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Expose port 80 for the app
EXPOSE 80
