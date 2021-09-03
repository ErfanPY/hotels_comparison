
from collections import defaultdict

from flask import Flask, json, request

from .db_util import custom, get_db_connection, select, select_all

en_cities = {
    'تهران': 'tehran',
    'شیراز': 'shiraz',
    'مشهد': 'mashhad',
    'تبریز': 'tabriz',
    'اصفهان': 'isfahan',
    'کیش': 'kish',
    'یزد': 'yazd',
    'قشم': 'qeshm',
    'بندر-عباس': 'bandarAbbas',
    'اهواز': 'ahvaz',
    'قزوین': 'qazvin',
    'ساری': 'sari',
    'سرعین': 'sarein',
    'گرگان': 'gorgan',
    'رشت': 'rasht',
    'بوشهر': 'bushehr',
    'کرمان': 'kerman',
    'ارومیه': 'urmia',
}

cities_UUID_name = {city_UUID: city_name for city_name,
                    city_UUID in en_cities.items()}

app = Flask(__name__)

@app.route('/list')
def list_view():
    token = request.args.get("token")
    list_type = request.args.get("type")  # cities/hotels/rooms
    hotel_UUID = request.args.get("hotel", "%")
    city_UUID = request.args.get("city", "%")

    encoded = request.args.get("encoded", "false").lower()
    compressed = request.args.get("compressed", "true").lower()
    
    do_compressed = None if compressed == "true" else 4
    do_ensure_ascii = encoded == "true"

    result_data = []

    token_validity = is_token_valid(token)
    if not token_validity:
        return "Invalid token", 401

    if list_type == "cities":
        query = "select htlCity from tblHotels Group BY htlCity"
        data = []

    elif list_type == "hotels":
        query = "select htlEnName, htlFaName, htlCity, htlUUID from tblHotels where IFNULL(htlCity, '') LIKE %s "
        data = [city_UUID]

    elif list_type == "rooms":
        query = """
            select romName, htlCity, htlUUID, htlFaName, romUUID from tblRooms
            INNER JOIN  tblHotels on rom_htlID = htlID
            WHERE IFNULL(htlCity, '') LIKE %s AND IFNULL(htlUUID, '') LIKE %s
        """
        data = [city_UUID, hotel_UUID]

    else:
        return "Invalid type", 400

    with get_db_connection() as conn:
        database_result = custom(query_string=query, data=data, conn=conn)

    if list_type == "cities":
        for city in database_result:
            result_data.append(
                {
                    "name": cities_UUID_name[city["htlCity"]],
                    "uid": city["htlCity"]
                }
            )

    elif list_type == "hotels":
        for hotel in database_result:
            result_data.append(
                {
                    "name": hotel["htlEnName"] or hotel["htlFaName"],
                    "city": hotel['htlCity'],
                    "uid": hotel["htlUUID"]
                }
            )

    elif list_type == "rooms":
        for room in database_result:
            result_data.append(
                {
                    "name": room["romName"],
                    "city": room['htlCity'],
                    "hotel": room["htlUUID"],
                    "hotel_name": room["htlFaName"],
                    "uid": room["romUUID"]
                }
            )

        
    response = app.response_class(
        response=json.dumps(
            result_data,
            ensure_ascii=do_ensure_ascii,
            indent=do_compressed
        ),
        status=200,
        mimetype='application/json',
    )
    return response

def mgroupby(iterator, key, key_name, items_key_name, sort_key=None, reverse=False):
    date_key_index = {}
    city_key_index = {}
    hotel_key_index = {}
    site_key_index = {}

    groups = []
    try:
        for item in iterator:
            key_date = str(item['avlInsertionDate'])
            key_city = item['htlCity']+"_/_"+key_date
            key_hotel = item['htlFaName']+"_/_"+key_city
            key_site = item['htlFrom']+"_/_"+key_hotel

            index_date = date_key_index.get(key_date)
            index_city = city_key_index.get(key_city)
            index_hotel = hotel_key_index.get(key_hotel)
            index_site = site_key_index.get(key_site)

            if index_date is None:
                groups.append({
                    'date': key_date,
                    'cities': []
                })
                
                index_date = len(groups)-1
                date_key_index[key_date] = index_date

            if index_city is None:
                groups[index_date]['cities'].append({
                    "city": key_city.split('_/_')[0],
                    'hotels': []
                })

                index_city = len(groups[index_date]['cities'])-1
                city_key_index[key_city] = index_city

            if index_hotel is None:
                groups[index_date]['cities'][index_city]['hotels'].append({
                    "hotel": key_hotel.split('_/_')[0],
                    'sites': []
                })
                
                index_hotel = len(groups[index_date]['cities'][index_city]['hotels'])-1
                hotel_key_index[key_hotel] = index_hotel
        
            if index_site is None:
                groups[index_date]['cities'][index_city]['hotels'][index_hotel]['sites'].append({
                    "site": "alibaba" if key_site[0]=="A" else "snapptrip",
                    'rooms': []
                })
                
                index_site = len(groups[index_date]['cities'][index_city]['hotels'][index_hotel]['sites'])-1
                site_key_index[key_site] = index_site


            groups[index_date]['cities'][index_city]['hotels'][index_hotel]['sites'][index_site]['rooms'].append(
                {
                    "additives":item['romMealPlan'],
                    "base_price":item['avlBasePrice'],
                    "discount_price":item['avlDiscountPrice'],
                    "name":item['romName'],
                }
            )
    except Exception as e:
        a=3
    if not sort_key is None:
        for group, items in groups.items():
            groups[group] = sorted(items, key=sort_key, reverse=reverse)

    return groups


@app.route('/availability')
def availability_view():
    token = request.args.get("token")
    hotel_UUID = request.args.get("hotel", "%")
    city_UUID = request.args.get("city", "%")
    
    date_from = request.args.get("from")  # YYYY-MM-DD format
    date_to = request.args.get("to")  # YYYY-MM-DD format
    
    encoded = request.args.get("encoded", "false").lower()
    compressed = request.args.get("compressed", "true").lower()
    
    do_compressed = None if compressed == "true" else 4
    do_ensure_ascii = encoded == "true"

    token_validity = is_token_valid(token)
    if not token_validity:
        return "Invalid token", 401

    query = """
        select
            avlInsertionDate, avlBasePrice, avlDiscountPrice, 
            htlFaName, htlCity, htlFrom,
            romName, romMealPlan
        FROM tblAvailabilityInfo
        INNER JOIN  tblRooms on avl_romID = romID
        INNER JOIN  tblHotels on rom_htlID = htlID
        where IFNULL(htlCity, '') LIKE %s AND IFNULL(htlUUID, '') LIKE %s
    """
    data = [city_UUID, hotel_UUID]
    
    if date_from:
        query += " AND avlDate >= '{}'".format(date_from)

    if date_to:
        query += " AND avlDate <= '{}'".format(date_to)

    with get_db_connection() as conn:
        database_result = custom(query_string=query+";", data=data, conn=conn)


    nested_dict = lambda: defaultdict(nested_dict)
    result_data = nested_dict()
    aaaaaa = mgroupby(database_result, lambda x:x['avlInsertionDate'], 'date', 'cities')

    for room in database_result:
        hotel_site = "alibaba" if room['htlFrom'] == "A" else "snapptrip"
       
        room_data = {
            "name": room["romName"],
            "additives": room["romMealPlan"],
            "base_price": room["avlBasePrice"],
            "discount_price": room["avlDiscountPrice"],
        }

        if type(result_data[str(room["avlInsertionDate"])][room['htlCity']][room["htlFaName"]][hotel_site]) == list:
            result_data[str(room["avlInsertionDate"])][room['htlCity']][room["htlFaName"]][hotel_site].append(room_data)
        else:
            result_data[str(room["avlInsertionDate"])][room['htlCity']][room["htlFaName"]][hotel_site] = [room_data, ]
        a = 3
        # result_data.append(
        #     {
        #         "name": room["romName"],
        #         "city": room['htlCity'],
        #         "hotel_site": hotel_site,
        #         "hotel": room["htlFaName"],
        #         "additives": room["romMealPlan"],
        #         "on_date": room["avlInsertionDate"],
        #         "base_price": room["avlBasePrice"],
        #         "discount_price": room["avlDiscountPrice"],
        #     }
        # )

    response = app.response_class(
        response=json.dumps(
            result_data,
            ensure_ascii=do_ensure_ascii,
            indent=do_compressed
        ),
        status=200,
        mimetype='application/json',
    )
    return response


@app.route('/alerts')
def alerts_view():
    token = request.args.get("token")
    date_from = request.args.get("from")  # YYYY-MM-DD format
    date_to = request.args.get("to")  # YYYY-MM-DD format

    if not token:
        return "token is required", 400
    
    encoded = request.args.get("encoded", "false").lower()
    compressed = request.args.get("compressed", "true").lower()
    
    do_compressed = None if compressed == "true" else 4
    do_ensure_ascii = encoded == "true"

    alert_type = request.args.get("type", "%") # reservation/price/options/discount
    alert_type_abrv = alert_type[0]
    
    city_UUID = request.args.get("city", "%")
    hotel_UUID = request.args.get("hotel", "%")
    room_UUID = request.args.get("room", "%")

    type_abrv_to_complete = {
        'R': 'reservation',
        'P': 'price',
        'O': 'options',
        'D': 'discount',
    }
    result_data = []

    token_validity = is_token_valid(token)
    if not token_validity:
        return "Invalid token", 401

    query = """
        SELECT alrRoomUUID, alrType, alrOnDate, alrA_romID, alrS_romID, alrInfo
        FROM tblAlert 
        INNER JOIN tblRooms ON romUUID = alrRoomUUID
        INNER JOIN tblHotels ON rom_htlID = htlID
        WHERE IFNULL(alrType, '') LIKE %s AND IFNULL(htlCity, '') LIKE %s
        AND IFNULL(htlUUID, '') LIKE %s AND IFNULL(romUUID, '') LIKE %s
    """ 

    data = [alert_type_abrv, city_UUID, hotel_UUID, room_UUID]

    if date_from:
        query += " AND alrOnDate >= '{}'".format(date_from)
        # data.append(date_from)

    if date_to:
        query += " AND alrOnDate <= '{}'".format(date_to)
        # data.append(date_to)
        
    if not alert_type in ["reservation", "price", "options", "discount", "%"]:
        return "Invalid type", 400

    with get_db_connection() as conn:
        query += "GROUP BY romUUID;"
        database_result = custom(query_string=query, data=data, conn=conn)
    
        
    for alert in database_result:
        alibaba_room_id = alert['alrA_romID']
        snapptrip_room_id = alert['alrS_romID']

        alert_data =  {
            "uid": alert['alrRoomUUID'],
            "type": type_abrv_to_complete[alert['alrType']],
            "date": alert['alrOnDate']
        }
        
        alrInfo = json.loads(alert['alrInfo'])

        if alert['alrType'] == "R":
            reserved_room_site = "alibaba" if str(snapptrip_room_id) in alrInfo.keys() else "snapptrip"
            alert_info = "reserved on " + reserved_room_site
        elif alert['alrType'] in ["P", "D"]:
            alibaba_base_price = alrInfo['base_price'][str(alibaba_room_id)]
            snapptrip_base_price = alrInfo['base_price'][str(snapptrip_room_id)]
            base_price_diff = abs(alibaba_base_price - snapptrip_base_price)

            if alert['alrType'] == "P" and base_price_diff < (alibaba_base_price / 50):
                continue
            
            alibaba_discount_price = alrInfo['discount_price'][str(alibaba_room_id)]
            snapptrip_discount_price = alrInfo['discount_price'][str(snapptrip_room_id)]
            discount_price_diff = abs(alibaba_discount_price - snapptrip_discount_price)

            if alert['alrType'] == "D" and discount_price_diff < (alibaba_discount_price / 50):
                continue

            alert_info = {
                "alibaba":{
                    "base_price":alibaba_base_price,
                    "discount_price":alibaba_discount_price,
                    "discount_amount":alibaba_base_price-alibaba_discount_price,
                },
                "snapptrip":{
                    "base_price":snapptrip_base_price,
                    "discount_price":snapptrip_discount_price,
                    "discount_amount":snapptrip_base_price-snapptrip_discount_price,
                },
            }
        else:
            alibab_info = alrInfo[str(alibaba_room_id)]
            snapptrip_info = alrInfo[str(snapptrip_room_id)]
            alert_info = {"alibaba": alibab_info, "snapptrip": snapptrip_info}
        
        alert_data['info'] = alert_info
        result_data.append(alert_data)
        
    response = app.response_class(
        response=json.dumps(
            result_data,
            ensure_ascii=do_ensure_ascii,
            indent=do_compressed
        ),
        status=200,
        mimetype='application/json',
    )
    return response


@app.route('/userOpinion')
def userOpinion_view():
    token = request.args.get("token")
    room_UUID = request.args.get("room", "%")

    encoded = request.args.get("encoded", "false").lower()
    compressed = request.args.get("compressed", "true").lower()
    
    do_compressed = None if compressed == "true" else 4
    do_ensure_ascii = encoded == "true"

    opinions_result = []

    token_validity = is_token_valid(token)
    if not token_validity:
        return "Invalid token", 401

    with get_db_connection() as conn:
        opinions_database = select_all(
            table="tblRoomsOpinions",
            select_columns=["ropUserName", "ropDate",
                            "ropStrengths", "ropWeakness", "ropText"],
            and_conditions={"rop_romID": room_UUID},
            conn=conn
        )

    for opinion in opinions_database:
        opinions_result.append(
            {
                "from": "snapptrip",
                "name": opinion['ropUserName'],
                "date": opinion["ropDate"],
                "strengths": opinion["ropStrengths"],
                "weaknesses": opinion["ropWeakness"],
                "opinion": opinion["ropText"]
            }
        )

        
    response = app.response_class(
        response=json.dumps(
            opinions_result,
            ensure_ascii=do_ensure_ascii,
            indent=do_compressed
        ),
        status=200,
        mimetype='application/json',
    )
    return response


def is_token_valid(token):
    if not token or not type(token) == str:
        return False
        
    with get_db_connection() as conn:
        token_data = select(
            table="tblTokens",
            select_columns=["tokSatatus"],
            and_conditions={'tokUUID': token},
            conn=conn
        )
    
    if token_data and token_data['tokSatatus'] == "A":
        return True
    return False

if __name__ == '__main__':
    app.run(host="0.0.0.0")
