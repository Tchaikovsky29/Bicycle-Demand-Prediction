#!/bin/bash
set -e

echo "📦 Creating dvc remote..."
awslocal s3 mb s3://ml-pipeline-dvc-cache

echo "✅ Buckets created"