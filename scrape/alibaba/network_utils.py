import json
from datetime import datetime, timedelta

import requests

def get_search_session_id(city_id, offset):
    today_date = datetime.now() + timedelta(days=offset)
    tomorrow_date = today_date + timedelta(days=1)

    start_date = today_date.strftime("%Y-%m-%d")
    end_date = tomorrow_date.strftime("%Y-%m-%d")
    
    data = '{"checkIn":"'+start_date+'","checkOut":"'+end_date+'","rooms":[{"adults":[30],"children":[]}],"destination":{"type":"City","id":"'+city_id+'"}}'

    url = "https://ws.alibaba.ir/api/v1/hotel/search"

    response = requests.post(url, data=data)
    response_data = json.loads(response.content)

    return response_data["result"]["sessionId"], start_date


def get_search_data(session_id):

    data = '{"sessionId":"'+session_id+'","limit":100,"skip":0,"sort":{"field":"score","order":-1},"filter":[]}'
    url = "https://ws.alibaba.ir/api/v1/hotel/result"

    response = requests.post(url, data=data)
    response_data = json.loads(response.content)

    return response_data


def get_hotel_rooms_data(session_id, hotel_id):
    url = "https://ws.alibaba.ir/api/v1/hotel/rate/room"

    
    data = '{"sessionId":"'+session_id+'","hotelId":"'+hotel_id+'"}'
    try:
        response = requests.post(url, data=data)
        response_data = json.loads(response.content)
    except:
        response_data = {'result':{'finalResult':True, "rooms":[]}}

    return response_data
