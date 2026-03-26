FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    pandas \
    dill \
    pymongo \
    pyarrow \
    boto3 \
    kfp \
    kfp-kubernetes \
    scikit-learn \
    mlflow \ 
    dagshub

COPY src/ /app/src/
COPY config/ /app/config/

ENV PYTHONPATH="/app"