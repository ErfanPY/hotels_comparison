# syntax=docker/dockerfile:1

FROM python:3.8-alpine

WORKDIR /scrapper

COPY requirements.txt requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

COPY ./scrape ./scrape

CMD [ "python3", "-m" , "scrape.main"]
