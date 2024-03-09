
FROM python:3.9
FROM docker:dind 
COPY server_2.py /
WORKDIR /app
COPY . /app

RUN apk add --no-cache su-exec
RUN set -ex && apk --no-cache add sudo
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN apk add --update --no-cache py3-pip
RUN python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt
EXPOSE 5000
ENV EXAMPLE_VAR="example_value"
CMD ["python3","server_2.py"]



