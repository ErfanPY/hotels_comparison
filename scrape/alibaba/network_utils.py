import json
from datetime import datetime, timedelta
import logging
import time

import requests
from scrape.critical_log import log_critical_error

logger = logging.getLogger("main_logger")


def get_search_session_id(city_id, offset):
    today_date = datetime.now() + timedelta(days=offset)
    tomorrow_date = today_date + timedelta(days=1)

    start_date = today_date.strftime("%Y-%m-%d")
    end_date = tomorrow_date.strftime("%Y-%m-%d")

    data = '{"checkIn":"'+start_date+'","checkOut":"'+end_date + \
        '","rooms":[{"adults":[30],"children":[]}],"destination":{"type":"City","id":"'+city_id+'"}}'

    url = "https://ws.alibaba.ir/api/v1/hotel/search"

    sleep_time = 1
    while True:
        if sleep_time >= 120:
            log_critical_error(
                "Alibaba nonhandleable network error. (session id endpoint)")
            return -1, -1

        try:
            response = requests.post(url, data=data, timeout=1000)
            response.raise_for_status()
            if response.status_code == 429:
                logger.error("Alibaba - session - Too many request")
                continue
            elif response.status_code == 403:
                logger.error("Alibaba - session - Forbidden")
                continue

        except Exception as e:
            logger.error(
                "Alibaba - network error - err:{} - sleep_time:{}".format(e, sleep_time))
            continue

        try:
            response_data = json.loads(response.content)
            return response_data["result"]["sessionId"], start_date

        except Exception as e:
            logger.error(
                "Alibaba - Couldn't load json - err:{} - sleep_time:{}".format(e, sleep_time))

        time.sleep(sleep_time)
        sleep_time *= 2


def get_search_data(session_id):

    data = '{"sessionId":"'+session_id + \
        '","limit":100,"skip":0,"sort":{"field":"score","order":-1},"filter":[]}'
    url = "https://ws.alibaba.ir/api/v1/hotel/result"

    sleep_time = 1
    while True:
        if sleep_time >= 120:
            log_critical_error(
                "Alibaba nonhandleable network error. (search endpoint)")
            return -1

        try:
            response = requests.post(url, data=data, timeout=100)
            if response.status_code == 429:
                logger.error("Alibaba - search - Too many request")
            else:
                response_data = json.loads(response.content)

                return response_data

        except Exception as e:
            logger.error(
                "Alibaba - get_search_data - err:{} - sleep_time:{}".format(e, sleep_time))

        time.sleep(sleep_time)
        sleep_time *= 2


def get_hotel_rooms_data(session_id, hotel_id):
    url = "https://ws.alibaba.ir/api/v1/hotel/rate/room"

    data = '{"sessionId":"'+session_id+'","hotelId":"'+hotel_id+'"}'

    sleep_time = 1
    while True:
        if sleep_time >= 120:
            log_critical_error(
                "Alibaba nonhandleable network error. (rooms endpoint)")
            return -1

        try:
            response = requests.post(url, data=data, timeout=100)
            if response.status_code == 429:
                logger.error("Alibaba - hotels - Too many request")
            else:
                response_data = json.loads(response.content)

                return response_data

        except Exception as e:
            logger.error(
                "Alibaba - rooms_data network error - err:{} - sleep_time:{}\n - url: {}\n - data: {}".format(e, sleep_time, url, data))

        time.sleep(sleep_time)
        sleep_time *= 2
