FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    pandas \
    pymongo \
    pyarrow \
    boto3 \
    kfp \
    kfp-kubernetes

COPY src/ /app/src/

ENV PYTHONPATH="/app"