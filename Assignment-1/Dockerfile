FROM python:3.9
COPY ConsistentHashing.py /
COPY loadbalancer.py /
COPY requirements.txt /
RUN pip install -r requirements.txt
CMD ["python3","loadbalancer.py"]
