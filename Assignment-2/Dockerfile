# Stage 1: Build stage
FROM mysql:8.0-debian

# Copy the rest of the files
COPY loadbalancer.py /
COPY requirements.txt /
COPY ConsistentHashing.py /
COPY deploy.sh /always-initdb.d/
COPY custom-entry.sh /

RUN chmod +x custom-entry.sh

# Update the package lists and install necessary packages
RUN apt-get update && \
    apt-get install -y python3 python3-pip python3-venv && \
    apt-get install -y apt-transport-https ca-certificates curl gnupg2 software-properties-common && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add - && \
    add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable" && \
    apt-get update && \
    apt-get install -y docker-ce-cli && \
    apt-get install -y sudo && \
    rm -rf /var/lib/apt/lists/*

# Create and activate a virtual environment
RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Install Python dependencies within the virtual environment
RUN pip install --no-cache-dir -r requirements.txt

# Set up user
ENV USER=theuser
RUN adduser --home /home/$USER --disabled-password --gecos GECOS $USER && \
    echo "$USER ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/$USER && \
    chmod 0440 /etc/sudoers.d/$USER && \
    groupadd docker && \
    usermod -aG docker $USER && \
    chsh -s /bin/zsh $USER
USER $USER
ENV HOME=/home/$USER

# Set MySQL root password
ENV MYSQL_ROOT_PASSWORD="root"

# Expose port
EXPOSE 5000

# Set entry point and command
ENTRYPOINT ["./custom-entry.sh"]
CMD ["mysqld"]
