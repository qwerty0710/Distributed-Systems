FROM python:3.9
COPY server.py /
COPY ../requirements.txt /
RUN pip install -r requirements.txt
CMD ["uvicorn", "server:app", "--port", "5000", "--host", "0.0.0.0"]