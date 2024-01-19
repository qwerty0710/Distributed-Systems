FROM python:3.9
COPY ConsistentHashing.py /
COPY loadbalancer.py /
COPY requirements.txt /
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python3","loadbalancer.py"]
