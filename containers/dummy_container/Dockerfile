FROM python:3.10-slim

WORKDIR /app

COPY ../../functions/dummy_function/main.py .
COPY ../../functions/dummy_function/requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 8080

CMD ["python", "main.py"]
