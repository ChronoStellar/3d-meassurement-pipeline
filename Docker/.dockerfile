
FROM python:3.12.12

WORKDIR /3D-meassurement-pipeline/Docker

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts/prepare_data.sh .
RUN chmod +x prepare_data.sh