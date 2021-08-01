
from flask import Flask, json, request, jsonify
from .db_util import get_db_connection, custom, select

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

    result_data = []

    token_validity = is_token_valid(token)
    if not token_validity:
        return "Invalid token", 401

    if list_type == "cities":
        query = "select htlCity from tblHotels Group by htlCity"
        data = []

    elif list_type == "hotels":
        query = "select htlEnName, htlFaName, htlCity, htlUUID from tblHotels where IFNULL(htlCity, '') LIKE %s "
        data = [city_UUID]

    elif list_type == "rooms":
        query = """
            select romName, htlCity, htlUUID, htlFaName, romUUID from tblRooms
            INNER JOIN  tblHotels on rom_htlID = htlID
            where IFNULL(htlCity, '') LIKE %s AND IFNULL(htlUUID, '') LIKE %s;
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

    return jsonify(result_data), 200


@app.route('/alerts')
def alerts_view():
    token = request.args.get("token")
    date_from = request.args.get("from")  # YYYY-MM-DD format
    date_to = request.args.get("to")  # YYYY-MM-DD format
    
    if not token:
        return "token is required", 400
    

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
        AND IFNULL(htlUUID, '') LIKE %s AND IFNULL(romUUID, '') LIKE %s;
    """ 

    data = [alert_type_abrv, city_UUID, hotel_UUID, room_UUID]

    if date_from:
        query += " AND alrOnDate >= %s"
        data.append(date_from)

    if date_to:
        query += " AND alrOnDate <= %s"
        data.append(date_to)
        
    if not alert_type in ["reservation", "price", "options", "discount", "%"]:
        return "Invalid type", 400

    with get_db_connection() as conn:
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
            reserved_room_site = "alibaba" if snapptrip_room_id in alrInfo.keys() else "snapptrip"
            alert_info = "reserved on " + reserved_room_site
        else:
            alibab_info = alrInfo[str(alibaba_room_id)]
            snapptrip_info = alrInfo[str(snapptrip_room_id)]
            alert_info = {"alibaba": alibab_info, "snapptrip": snapptrip_info}

        alert_data['info'] = alert_info
        result_data.append(alert_data)
        
    return jsonify(result_data), 200


@app.route('/userOpinion')
def userOpinion_view():
    token = request.args.get("token")
    room_UUID = request.args.get("room", "%")

    opinions_result = []

    token_validity = is_token_valid(token)
    if not token_validity:
        return "Invalid token", 401

    with get_db_connection() as conn:
        opinions_database = select(
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

    return jsonify(opinions_result), 200


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
    app.run(debug=True)
