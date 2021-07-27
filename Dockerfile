# syntax=docker/dockerfile:1

FROM python:3.8-alpine

WORKDIR /scrapper

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY ./scrape ./scrape
COPY ./logs ./logs
COPY __init__.py __init__.py

CMD [ "python3", "-m" , "scrape.main"]
