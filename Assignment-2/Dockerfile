# Stage 1: Build stage
FROM mysql:8.0-debian


# Copy the rest of the files
COPY loadbalancer.py /
COPY requirements.txt /
COPY ConsistentHashing.py /
COPY deploy.sh /always-initdb.d/
COPY custom-entry.sh /

RUN apt-get update
RUN apt-get update && apt-get install -y python3 python3-pip

# Install the dependencies from the wheels
RUN pip install --break-system-packages -r requirements.txt

RUN chmod +x ./custom-entry.sh
RUN apt-get -y install sudo


RUN apt-get -y install apt-transport-https ca-certificates curl gnupg2 software-properties-common
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -
RUN add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/debian $(lsb_release -cs) stable"
RUN apt-get update
RUN apt-get -y install docker-ce-cli

ENV USER=theuser
RUN adduser --home /home/$USER --disabled-password --gecos GECOS $USER \
  && echo "$USER ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/$USER \
  && chmod 0440 /etc/sudoers.d/$USER \
  && groupadd docker \
  && usermod -aG docker $USER \
  && chsh -s /bin/zsh $USER
USER $USER
ENV HOME=/home/$USER
ENV MYSQL_ROOT_PASSWORD="root"
EXPOSE 5000

ENTRYPOINT ["./custom-entry.sh"]
CMD ["mysqld"]

# Run the application
#CMD ["uvicorn", "loadbalancer:app", "--port", "5000", "--host", "0.0.0.0"]

#RUN sudo service mysql start
#RUN mysql -u root -p -e "CREATE USER 'lb'@'localhost' identified WITH mysql_native_password BY 'root'; flush privileges;"
