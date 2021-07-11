
from flask import Flask, request
from .db_util import get_db_connection, custom, select

en_cities = {
    'تهران':
    'tehran',
    'شیراز':
    'shiraz',
    'مشهد':
    'mashhad',
    'تبریز':
    'tabriz',
    'اصفهان':
    'isfahan',
    'کیش':
    'kish',
    'یزد':
    'yazd',
    'قشم':
    'qeshm',
    'بندرعباس':
    'bandarAbbas',
    'اهواز':
    'ahvaz',
    'قزوین':
    'qazvin',
    'ساری':
    'sari',
    'سرعین':
    'sarein',
    'گرگان':
    'gorgan',
    'رشت':
    'rasht',
    'بوشهر':
    'bushehr',
    'کرمان':
    'kerman',
    'ارومیه':
    'urmia',
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
        query = "select htlName, htlCity, htlUUID from tblHotels where htlCity LIKE ? "
        data = [city_UUID]

    elif list_type == "rooms":
        query = """
            select romName, htlCity, htlUUID, romUUID from tblRooms
            INNER JOIN  tblHotels on rom_htlUUID = htlUUID
            where htlCity LIKE ? AND hotel_UUID LIKE ?
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
                    "name": hotel["htlName"],
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
                    "uid": room["romUUID"]
                }
            )

    return result_data, 200


@app.route('/alerts')
def alerts_view():
    token = request.args.get("token")
    date_from = request.args.get("DATE_FROM")  # YYYY-MM-DD format
    date_to = request.args.get("DATE_TO")  # YYYY-MM-DD format
    
    alert_type = request.args.get("TYPE", "%") # reservation/price/options/discount
    alert_type_abrv = alert_type[0]
    
    city_UUID = request.args.get("CITY_UID", "%")
    hotel_UUID = request.args.get("HOTEL_UID", "%")
    room_UUID = request.args.get("ROOM_UID", "%")

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

    query = """select alrRoomUUID, alrType, alrOnDate, alrA_romID, alS_romID, alrInfo from tblAlert 
        where alrOnDate between ? and ? 
        AND alrType LIKE ? AND city_UUID LIKE ? 
        AND hotel_UUID LIKE ? AND room_UUID LIKE ?
    """ 

    data = [date_from, date_to, alert_type_abrv, city_UUID, hotel_UUID, room_UUID]

    if not alert_type in ["reservation", "price", "options", "discount", "%"]:
        return "Invalid type", 400

    with get_db_connection() as conn:
        database_result = custom(query_string=query, data=data, conn=conn)
    
        
        for alert in database_result:
            alibaba_room_id = alert['alrA_romID']
            snapptrip_room_id = alert['alS_romID']

            alert_data =  {
                "uid": alert['alrRoomUUID'],
                "type": type_abrv_to_complete[alert['alrType']],
                "date": alert['alrOnDate']
            }
            
            if alert['alrType'] == "R":
                reserved_room_site = "alibaba" if alert['alrInfo'].keys[0] == snapptrip_room_id else "snapptrip"
                alert_info = "reserved on " + reserved_room_site
            else:
                alibab_info = alert['alrInfo'][alibaba_room_id]
                snapptrip_info = alert['alrInfo'][snapptrip_room_id]
                alert_info = {"alibaba": alibab_info, "snapptrip": snapptrip_info}

            alert_data['info'] = alert_info
            result_data.append(alert_data)
        
    return result_data, 200


@app.route('/userOpinion')
def userOpinion_view():
    token = request.args.get("token")
    room_UUID = request.args.get("ROOM_UID")

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

    return opinions_result, 200


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
    
    if token_data['tokSatatus'] == "A":
        return True
    return False

if __name__ == '__main__':
    app.run(debug=True)
