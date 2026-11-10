FROM python:3.13-alpine@sha256:1e1f6334529d1fb26a2ef619d7cffb30a7c7d7cc1cc7338ebee283a58d1aeaca
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip uninstall -y pip
COPY src /app/src
USER 65532:65532
EXPOSE 8080
CMD ["python", "-m", "src.server"]
