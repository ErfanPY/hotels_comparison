
from flask import Flask, json, request, abort

from .db_util import custom, get_db_connection, select, select_all
from .parse_data_utils import *

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

QUERY_RESULT_LIMIT = 1000


@app.route('/list')
def list_view():
    list_type = request.args.get("type")  # cities/hotels/rooms
    city_UUID = request.args.get("city")
    hotel_UUID = request.args.get("hotel")
    site_from = request.args.get("site")
    hotel_name = request.args.get("hotel-name")

    token = request.args.get("token")
    page = int(request.args.get("page", "1"))
    encoded = request.args.get("encoded", "false").lower()
    compact = request.args.get("compact", "true").lower()
    verbose = request.args.get("verbose", "false").lower() == "true"

    page = max(page, 1) - 1

    do_compressed = None if compact == "true" else 4
    do_ensure_ascii = encoded == "true"

    result_data = []

    token_validity = is_token_valid(token)
    if not token_validity:
        return "Invalid token", 401

    if list_type == "cities":
        query = "select htlCity from tblHotels Group BY htlCity"
        data = []

    elif list_type == "hotels":
        query = """
            select htlEnName, htlFaName, htlCity, htlUUID, htlFrom
            from tblHotels
            WHERE (ISNULL(%s) OR htlCity = %s) AND (ISNULL(%s) OR htlFrom = %s)
        """
        data = [city_UUID, city_UUID, site_from, site_from]

    elif list_type == "rooms":
        query = """
            select romName, htlCity, htlUUID, htlFaName, romUUID, htlFrom from tblRooms
            JOIN  tblHotels on rom_htlID = htlID
            WHERE  (ISNULL(%s) OR htlCity = %s)  
            AND  (ISNULL(%s) OR htlUUID = %s)
            AND  (ISNULL(%s) OR htlFrom = %s)
            AND  (ISNULL(%s) OR htlFaName = %s OR htlEnName = %s)
            LIMIT %s OFFSET %s 
        """
        data = [
            city_UUID, city_UUID,
            hotel_UUID, hotel_UUID,
            site_from, site_from,
            hotel_name, hotel_name, hotel_name,
            QUERY_RESULT_LIMIT, QUERY_RESULT_LIMIT*page
        ]

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
            # "city-name": "HOTEL_CITY_NAME_n (just when verbose argument is set)",
            hotel_data = {
                "name": {
                    "en": hotel["htlEnName"],
                    "fa": hotel["htlFaName"]
                },
                "city": hotel['htlCity'],
                "uid": hotel["htlUUID"],
                "site": "snapptrip" if hotel['htlFrom'] == "S" else "alibaba" 
            }
            if verbose:
                hotel_data["city-name"] = cities_UUID_name[hotel['htlCity']]
            result_data.append(hotel_data)

    elif list_type == "rooms":
        for room in database_result:
            room_data = {
                "site": "snapptrip" if room['htlFrom'] == "S" else "alibaba",
                "name": room["romName"],
                "hotel": room["htlUUID"],
                "uid": room["romUUID"],
                "city": room['htlCity'],
            }

            if verbose:
                room_data["hotel-info"] = {
                    "fa": room["htlFaName"],
                    "en": room["htlEnName"],
                }
                room_data["city-name"] = cities_UUID_name[room['htlCity']]

            result_data.append(room_data)

        
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
    city_UUID = request.args.get("city")
    site_from = request.args.get("site")
    hotel_UUID = request.args.get("hotel")
    hotel_name = request.args.get("hotel-name")
    room_uuid = request.args.get("room")
    alert_type = request.args.get("type") # price/ reservation
    date_from = request.args.get("from")  # YYYY-MM-DD format
    date_to = request.args.get("to")  # YYYY-MM-DD format
    crawl = request.args.get("crawl")  # Date+Time (YYYY-MM-DD-[AM|PM])

    token = request.args.get("token")
    page = int(request.args.get("page", "1")) - 1
    encoded = request.args.get("encoded", "false").lower()
    compact = request.args.get("compact", "true").lower()
    verbose = request.args.get("verbose", "false").lower() == "true"
    
    
    if not token:
        return "token is required", 400
    token_validity = is_token_valid(token)
    if not token_validity:
        return abort(401, "Invalid token")
    if not alert_type in ["reservation", "price"]:
        abort(400, "Type should be one of ( reservation / price)")
    if not city_UUID and not hotel_UUID:
        abort(400, "One of the city or hotel filters must be set.")

    do_compressed = None if compact == "true" else 4
    do_ensure_ascii = encoded == "true"

    alert_type_abrv = alert_type[0].upper()
    
    crawl_date = crawl[:-3]
    crawl_clock = crawl[-2:]
    
    type_abrv_to_complete = {
        'R': 'reservation',
        'P': 'price',
        'O': 'options',
        'D': 'discount',
    }

    query = """
        SELECT 
            alrRoomUUID,
            alrType,
            alrOnDate,
            alrCrawlTime,
            alrDateTime,
            alrA_romID,
            alrS_romID,
            alrInfo,
            A.romName as `aName`,
            S.romName as `sName`,
            htlFaName,
            htlEnName,
            htlCity,
            htlUUID
        FROM tblAlert 
        LEFT JOIN tblRooms A 
        ON A.romID = alrA_romID
        LEFT JOIN tblRooms S
        ON S.romID = alrS_romID
        
        JOIN tblHotels ON htlID = IFNULL(A.rom_htlID, S.rom_htlID)
        WHERE  (ISNULL(%s) OR alrType = %s)
            AND  (ISNULL(%s) OR htlFrom = %s)
            AND  (ISNULL(%s) OR htlCity = %s) 
            AND  (ISNULL(%s) OR htlUUID = %s)
            AND  (ISNULL(%s) OR htlFaName = %s OR htlEnName = %s)
            AND  (ISNULL(%s) OR romUUID = %s)
            AND  (ISNULL(%s) OR alrCrawlClock = %s)
            AND  (ISNULL(%s) OR DATE(alrDateTime) = %s)
            AND  alrOnDate >= IFNULL(%s, DATE_SUB(NOW(), INTERVAL 7 DAY)) 
            AND  alrOnDate <= IFNULL(%s,DATE_ADD(IFNULL(%s, NOW()), INTERVAL 7 DAY))
        ORDER BY alrOnDate
        LIMIT %s OFFSET %s
    """ 

    data = [
        alert_type_abrv, alert_type_abrv,
        site_from, site_from,
        city_UUID, city_UUID,
        hotel_UUID, hotel_UUID,
        hotel_name, hotel_name, hotel_name,
        room_uuid, room_uuid,
        crawl_clock, crawl_clock,
        crawl_date, crawl_date,
        date_from, date_to, date_from,
        QUERY_RESULT_LIMIT, QUERY_RESULT_LIMIT*page
    ]
 

    with get_db_connection() as conn:
        database_result = custom(query_string=query, data=data, conn=conn)
    
    result_data = group_alerts(database_result, verbose=verbose)
        
    response = app.response_class(
        response=json.dumps(
            result_data,
            ensure_ascii=do_ensure_ascii,
            indent=do_compressed,
        ),
        status=200,
        mimetype='application/json',
    )
    return response


@app.route('/info')
def availability_view():
    city_UUID = request.args.get("city")
    site_from = request.args.get("site")
    hotel_UUID = request.args.get("hotel")
    hotel_name = request.args.get("hotel-name")
    date_from = request.args.get("from")  # YYYY-MM-DD format
    date_to = request.args.get("to")  # YYYY-MM-DD format
    crawl = request.args.get("crawl")  # Date+Time (YYYY-MM-DD-[AM|PM])
    
    token = request.args.get("token")
    page = int(request.args.get("page", "1"))
    encoded = request.args.get("encoded", "false").lower()
    compact = request.args.get("compact", "true").lower()

    token_validity = is_token_valid(token)
    if not token_validity:
        abort(401, "Invalid token")

    page = max(page, 1) - 1
    
    do_compressed = None if compact == "true" else 4
    do_ensure_ascii = encoded == "true"
    
    crawl_date = crawl[:-3]
    crawl_clock = crawl[-2:]
    
    query = """
        select
            avlInsertionDate, 
            avlBasePrice, 
            avlDiscountPrice, 
            avlDate,
            avlCrawlTime,
            htlFaName, htlEnName, htlCity, htlFrom, htlUUID,
            romName, romMealPlan
        FROM tblAvailabilityInfo
        JOIN  tblRooms on avl_romID = romID
        JOIN  tblHotels on rom_htlID = htlID
        WHERE  (ISNULL(%s) OR htlUUID = %s)
            AND  (ISNULL(%s) OR htlFrom = %s)
            AND  (ISNULL(%s) OR htlEnName = %s OR htlFaName = %s)  
            AND  (ISNULL(%s) OR htlCity =%s)  
            AND  (ISNULL(%s) OR alrCrawlClock = %s)
            AND  (ISNULL(%s) OR DATE(alrDateTime) = %s)
            AND  avlDate >= IFNULL(%s, DATE_SUB(NOW(), INTERVAL 7 DAY)) 
            AND  avlDate <= IFNULL(%s,DATE_ADD(IFNULL(%s, NOW()), INTERVAL 7 DAY))
        ORDER BY avlDate
        LIMIT %s OFFSET %s
    """
    data = [
        hotel_UUID, hotel_UUID, hotel_UUID,
        site_from, site_from,
        hotel_name, hotel_name, hotel_name,
        city_UUID, city_UUID,
        crawl_clock, crawl_clock,
        crawl_date, crawl_date,
        date_from, date_to, date_from,
        QUERY_RESULT_LIMIT, QUERY_RESULT_LIMIT*page
    ]

    with get_db_connection() as conn:
        database_result = custom(query_string=query+";", data=data, conn=conn)

    result_data = group_infos(database_result)

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
    room_UUID = request.args.get("room", "%")

    token = request.args.get("token")
    encoded = request.args.get("encoded", "false").lower()
    compact = request.args.get("compact", "true").lower()
    
    do_compressed = None if compact == "true" else 4
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
                "site": "snapptrip",
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


@app.route('/health_check')
def health_check():
    return "OK"


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
