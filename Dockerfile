FROM python:3.11-slim
WORKDIR /app
RUN pip install fastapi uvicorn httpx pydantic --no-cache-dir
COPY onepass_v0.py main.py
RUN mkdir -p static
EXPOSE 7000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7000"]
