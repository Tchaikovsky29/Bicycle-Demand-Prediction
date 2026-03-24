#!/bin/bash
set -e

echo "📦 Creating remote..."
awslocal s3 mb s3://bicycle-demand-prediction-bucket

echo "✅ Buckets created"