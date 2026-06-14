# Create empty __init__.py files for cloud-core packages
import os

files = [
    "/c/Users/SKV/Desktop/projects/AMOS/cloud-core/ingestion-service/app/__init__.py",
    "/c/Users/SKV/Desktop/projects/AMOS/cloud-core/tsdb-service/app/__init__.py",
    "/c/Users/SKV/Desktop/projects/AMOS/cloud-core/alert-service/app/__init__.py",
    "/c/Users/SKV/Desktop/projects/AMOS/cloud-core/mlops-service/app/__init__.py",
]

for f in files:
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, 'w') as fp:
        pass  # empty file

print("Created __init__.py files")