# syntax=docker/dockerfile:1


FROM python:3.8-alpine

WORKDIR /my_dir

COPY requirements.txt my_dir/api/requirements.txt
COPY app.py my_dir/api/app.py
COPY db_util.py my_dir/api/db_util.py

# RUN pip3 install -r my_dir/api/requirements.txt