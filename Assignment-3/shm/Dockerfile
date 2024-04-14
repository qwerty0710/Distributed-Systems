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

COPY requirements.txt /

# Install application dependencies
RUN python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt

# Copy application files
COPY shardManager.py /

# Expose port for communication
EXPOSE 5000

# Run the application
CMD ["uvicorn", "shardManager:app", "--port", "5000", "--host", "0.0.0.0"]