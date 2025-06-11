FROM prom/pushgateway:latest

# Expose port 8080 for Cloud Run compatibility
EXPOSE 8080

# Configure Pushgateway to listen on port 8080
CMD ["--web.listen-address=:8080"]
