# Use official PostGIS image based on PostgreSQL 16 Alpine for small footprint
FROM postgis/postgis:16-3.4-alpine

# Set default timezone to Indian Standard Time (IST)
ENV TZ=Asia/Kolkata
RUN apk add --no-cache tzdata && \
    cp /usr/share/zoneinfo/Asia/Kolkata /etc/localtime && \
    echo "Asia/Kolkata" > /etc/timezone

# Copy database initialization SQL scripts into the container
COPY init-scripts/ /docker-entrypoint-initdb.d/

# Expose standard PostgreSQL port
EXPOSE 5433