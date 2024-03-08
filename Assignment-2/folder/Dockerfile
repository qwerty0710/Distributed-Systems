FROM mysql:8.0-debian

COPY deploy.sh /always-initdb.d/
COPY custom-entry.sh /
COPY server.py /
COPY requirements.txt /

RUN apt-get update
RUN apt-get install -y python3 python3-pip
RUN python3 -m pip install --upgrade pip --break-system-packages
RUN python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt
RUN chmod +x /custom-entry.sh

ENV MYSQL_ROOT_PASSWORD="abc"

EXPOSE 5000

ENTRYPOINT ["/custom-entry.sh"]
CMD ["mysqld"]
