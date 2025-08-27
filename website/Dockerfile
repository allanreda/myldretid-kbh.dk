# docker build -t local-static-site .
# docker run -p 3000:80 local-static-site

FROM nginx:alpine

# Copy static site files to the default Nginx public folder
COPY website/ /usr/share/nginx/html

# Expose port 80
EXPOSE 80
