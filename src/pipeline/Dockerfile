FROM python:3.10-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    kserve \
    scikit-learn \
    numpy \
    pandas \
    boto3 \
    mlflow

COPY inference_transformer.py /app/inference_transformer.py

ENV PYTHONPATH="/app"

ENTRYPOINT ["python", "inference_transformer.py"]