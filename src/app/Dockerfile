FROM python:3.13.5-slim

WORKDIR /src

COPY src ./src

RUN pip install --no-cache-dir -r src/app/requirements.txt

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8080"]