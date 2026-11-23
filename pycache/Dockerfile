FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd -m appuser
COPY . .
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app
USER appuser
EXPOSE 5001
CMD ["python","app.py"]
