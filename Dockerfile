# syntax=docker/dockerfile:1

FROM python:3.8-alpine

WORKDIR /scrapper

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "-m" , "scrape.main", "-a"]
# CMD [ "python3", "doc_test.py"]
# ENTRYPOINT ["tail", "-f", "/dev/null"]

RUN tail /dev/null