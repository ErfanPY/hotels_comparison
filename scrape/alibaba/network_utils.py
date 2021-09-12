import json
from datetime import datetime, timedelta
import logging
import time

import requests

logger = logging.getLogger(__name__)

def get_search_session_id(city_id, offset):
    today_date = datetime.now() + timedelta(days=offset)
    tomorrow_date = today_date + timedelta(days=1)

    start_date = today_date.strftime("%Y-%m-%d")
    end_date = tomorrow_date.strftime("%Y-%m-%d")
    
    data = '{"checkIn":"'+start_date+'","checkOut":"'+end_date+'","rooms":[{"adults":[30],"children":[]}],"destination":{"type":"City","id":"'+city_id+'"}}'

    url = "https://ws.alibaba.ir/api/v1/hotel/search"
    sleep_time = 0
    while True:
        try:
            response = requests.post(url, data=data)
            if response.status_code == 429:
                logger.error("Alibaba - session - Too many request")
            else:
                break

        except Exception as e:
            logger.error("Alibaba - network error - err:{} - sleep_time:{}".format(e, sleep_time))

            if sleep_time >= 10 :
                return -1, -1

            sleep_time += 1
            time.sleep(sleep_time)
        

    while True:
        try:
            response_data = json.loads(response.content)
            return response_data["result"]["sessionId"], start_date

        except Exception as e:
            logger.error("Alibaba - Couldn't load json - err:{} - sleep_time:{}".format(e, sleep_time))
          
            if sleep_time >= 10 :
                return -1, -1

            sleep_time += 1
            time.sleep(sleep_time)


def get_search_data(session_id):

    data = '{"sessionId":"'+session_id+'","limit":100,"skip":0,"sort":{"field":"score","order":-1},"filter":[]}'
    url = "https://ws.alibaba.ir/api/v1/hotel/result"
    sleep_time = 0
    
    while True:
        try:
            response = requests.post(url, data=data)
            if response.status_code == 429:
                logger.error("Alibaba - search - Too many request")
            else:
                response_data = json.loads(response.content)
        
                return response_data

        except Exception as e:
            logger.error("Alibaba - get_search_data - err:{} - sleep_time:{}".format(e, sleep_time))
           
            if sleep_time >= 10 :
                return {
                    'error': True
                }
           
            sleep_time += 1
            time.sleep(sleep_time)


def get_hotel_rooms_data(session_id, hotel_id):
    url = "https://ws.alibaba.ir/api/v1/hotel/rate/room"

    
    data = '{"sessionId":"'+session_id+'","hotelId":"'+hotel_id+'"}'
    sleep_time = 0
   
    while True:
        try:
            response = requests.post(url, data=data)
            if response.status_code == 429:
                logger.error("Alibaba - hotels - Too many request")
            else:
                response_data = json.loads(response.content)
            
                return response_data

        except Exception as e:
            logger.error("Alibaba - rooms_data network error - err:{} - sleep_time:{}".format(e, sleep_time))
            response_data = {'result':{'finalResult':True, "rooms":[]}}

            if sleep_time >= 10 :
                return -1

            sleep_time += 1
            time.sleep(sleep_time)
