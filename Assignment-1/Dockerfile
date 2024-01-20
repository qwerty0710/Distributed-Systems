
FROM docker:dind
COPY loadbalancer.py /
COPY requirements.txt /
COPY ConsistentHashing.py /
RUN apk add --no-cache su-exec
RUN set -ex && apk --no-cache add sudo
ENV PYTHONUNBUFFERED=1
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN apk add --update --no-cache py3-pip
RUN python3 -m pip install --break-system-packages --no-cache-dir -r requirements.txt
EXPOSE 5000
CMD ["python3","loadbalancer.py"]



