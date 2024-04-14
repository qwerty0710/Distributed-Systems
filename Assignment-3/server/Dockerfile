FROM python:3.9
COPY server.py /
COPY helper.py /
COPY requirements.txt /
COPY logFile.py /
RUN pip install -r requirements.txt
EXPOSE 5001
CMD ["python3","server.py"]
