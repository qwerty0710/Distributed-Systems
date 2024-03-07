FROM docker:dind

# Install essential tools
RUN apk add --no-cache su-exec curl

# Install and configure `sudo` for safe environment modifications
RUN set -ex && apk add --no-cache sudo

# Set environment variable for unbuffered output
ENV PYTHONUNBUFFERED=1

# Install Python 3 and set symbolic link
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python

# Install `pip` for Python package management
RUN apk add --update --no-cache py3-pip

# Copy application files
COPY loadbalancer.py /
COPY requirements.txt /
COPY ConsistentHashing.py /

# Install MySQL and set up connection credentials
RUN set -ex && \
    apk add --update --no-cache --virtual .mysql-deps \
        mysql-client \
        && \
    echo "mysql:root:root" > /root/.my.cnf \
    && \
    chmod 600 /root/.my.cnf \
    && \
    apk del --no-cache .mysql-deps

# Install application dependencies
RUN python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt

# Expose port for communication
EXPOSE 5000

# Run the application
CMD ["python3", "loadbalancer.py"]
