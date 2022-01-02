import json
import logging
import time
from scrape.db_util import custom, get_db_connection, insert_select_id
from scrape.common_utils import mgroupby
from datetime import datetime, timedelta

logger = logging.getLogger("main_logger")


def main(crawl_date_start=None, crawl_date_end=None):
    rooms_data = []

    single_rooms = []

    get_romUUIDs_query = """
        SELECT htlFrom, romID, romUUID
        FROM tblRooms
        INNER JOIN tblHotels on htlID = rom_htlID
    ;
    """

    with get_db_connection() as conn:
        result = custom(query_string=get_romUUIDs_query, conn=conn)

    romUUID_romIDs = make_romUUID_romIDs(result)

    rooms_data_query = """
            SELECT romUUID, avlInsertionDate, avlDate, romID, avlBasePrice,
                avlDiscountPrice, romName, rom_htlID, htlFrom, romMealPlan, romAdditives
            FROM tblRooms
            INNER JOIN tblAvailabilityInfo ON romID = avl_romID
            INNER JOIN tblHotels ON htlID = rom_htlID 
            WHERE NOT romUUID IS NULL
                AND  (ISNULL(%s) OR avlCrawlTime >= %s)
                AND  (ISNULL(%s) OR avlCrawlTime <= %s)
            ;
        """

    with get_db_connection() as conn:
        rooms_data = custom(
            query_string=rooms_data_query,
            data=[
                crawl_date_start, crawl_date_start,
                crawl_date_end, crawl_date_end
            ],
            conn=conn
        )

    rom_identifier_groups = mgroupby(
        rooms_data,
        lambda room: "{}_{}".format(room['romID'], room['avlDate']),
        sort_key=lambda room: room['avlInsertionDate'], reverse=True
    )

    last_inserted_rooms = {k: v[0] for k, v in rom_identifier_groups.items()}

    room_UUID_groups = mgroupby(
        last_inserted_rooms.values(),
        # lambda room:room['romUUID']
        lambda room: "{}_{}".format(room['romUUID'], room['avlDate'])
    )

    count_roomUUID = len(room_UUID_groups.items())
    for i, (roomUUID, rooms_group) in enumerate(room_UUID_groups.items()):

        htlFrom_groups = mgroupby(
            rooms_group,
            lambda room: room['htlFrom'],
            sort_key=lambda room: room['romMealPlan']
        )

        if len(htlFrom_groups.keys()) == 1:
            single_room = list(htlFrom_groups.values())[0][0]
            single_rooms.append(single_room)
            logger.info(
                f"{i}/{count_roomUUID} - single - {single_room['romUUID']} - {single_room['avlDate']} - {single_room['avlInsertionDate']}")

        elif len(htlFrom_groups.keys()) == 2:
            crawl_start_datetime = htlFrom_groups['S'][0]['avlInsertionDate'].strftime(
                "%Y-%m-%d %H:00:00")

            while True:
                with get_db_connection() as conn:
                    err_check = compare_rooms(
                        alibaba_room=htlFrom_groups['A'][0],
                        snapptrip_room=htlFrom_groups['S'][0],
                        conn=conn,
                        crawl_start_time=crawl_start_datetime,
                        insertion_datetime=htlFrom_groups['S'][0]['avlInsertionDate']
                    )
                if not err_check == -1:
                    break
                time.sleep(2)

            logger.info(f"{i}/{count_roomUUID} - dual")

        else:
            logger.critical(
                "Non handled condition, {}".format(str(htlFrom_groups)))

    with get_db_connection() as conn:
        add_single_available_rooms(
            rooms=single_rooms,
            romUUID_romIDs=romUUID_romIDs,
            conn=conn,
        )


def make_romUUID_romIDs(rooms):
    romUUID_romIDs = {}

    for room in rooms:
        htlFrom = room['htlFrom']
        romID = room['romID']
        romUUID = room['romUUID']

        past = romUUID_romIDs.get(romUUID, {})
        past[htlFrom] = romID
        romUUID_romIDs[romUUID] = past

    return romUUID_romIDs


def compare_rooms(alibaba_room, snapptrip_room, conn, crawl_start_time=None, insertion_datetime=None):
    prices_alrInfo = {
        'base_price': {
            alibaba_room['romID']: alibaba_room['avlBasePrice'],
            snapptrip_room['romID']: snapptrip_room['avlBasePrice']
        },
        'discount_price': {
            alibaba_room['romID']: alibaba_room['avlDiscountPrice'],
            snapptrip_room['romID']: snapptrip_room['avlDiscountPrice'],
        }
    }
    romUUID = alibaba_room['romUUID']
    room_alert = {
        "alrRoomUUID": romUUID,
        "alrOnDate": alibaba_room['avlDate'],
        "alrCrawlTime": crawl_start_time,
        "alrA_romID": alibaba_room['romID'],
        "alrS_romID": snapptrip_room['romID'],
    }

    if not alibaba_room['avlBasePrice'] == snapptrip_room['avlBasePrice']:

        err_check = save_price_alert(
            conn, insertion_datetime, prices_alrInfo, room_alert)

        if err_check == -1:
            return -1

    if not alibaba_room['avlDiscountPrice'] == snapptrip_room['avlDiscountPrice']:
        err_check = save_discount_alert(
            conn, insertion_datetime, prices_alrInfo, room_alert)

        if err_check == -1:
            return -1

    set_a = set(json.loads(alibaba_room['romAdditives']))
    set_b = set(json.loads(snapptrip_room['romAdditives']))

    diff_a = set_a-set_b
    diff_b = set_b-set_a

    if diff_a or diff_b:
        err_check = save_option_alert(alibaba_room, snapptrip_room, conn,
                                      insertion_datetime, prices_alrInfo, room_alert, diff_a, diff_b)

        if err_check == -1:
            return -1


def save_price_alert(conn, insertion_datetime, prices_alrInfo, room_alert):
    alrType = 'P'
    alrInfo = prices_alrInfo

    room_alert.update({
        "alrType": alrType,
        "alrInfo": json.dumps(alrInfo)
    })

    identifier_dict = room_alert
    if insertion_datetime:
        room_alert["alrDateTime"] = insertion_datetime

    err_check = insert_select_id(
        table='tblAlert',
        key_value=room_alert,
        conn=conn,
        identifier_condition=identifier_dict
    )

    return err_check


def save_discount_alert(conn, insertion_datetime, prices_alrInfo, room_alert):
    alrType = 'D'
    alrInfo = prices_alrInfo

    room_alert.update({
        "alrType": alrType,
        "alrInfo": json.dumps(alrInfo)
    })

    identifier_dict = room_alert
    if insertion_datetime:
        room_alert["alrDateTime"] = insertion_datetime

    err_check = insert_select_id(
        table='tblAlert',
        key_value=room_alert,
        conn=conn,
        identifier_condition=identifier_dict
    )

    return err_check


def save_option_alert(alibaba_room, snapptrip_room, conn, insertion_datetime, prices_alrInfo, room_alert, diff_a, diff_b):
    alrType = 'O'
    alrInfo = prices_alrInfo
    alrInfo["options"] = {
        alibaba_room['romID']: list(diff_a),
        snapptrip_room['romID']: list(diff_b),
    }

    room_alert.update({
        "alrType": alrType,
        "alrInfo": json.dumps(alrInfo)
    })

    identifier_dict = room_alert
    if insertion_datetime:
        room_alert["alrDateTime"] = insertion_datetime

    err_check = insert_select_id(
        table='tblAlert',
        key_value=room_alert,
        conn=conn,
        identifier_condition=identifier_dict
    )

    return err_check


def add_single_available_rooms(rooms, romUUID_romIDs, conn, crawl_start_time=None):
    len_rooms = len(rooms)
    for i, room in enumerate(rooms):
        if i % 10 == 0:
            print(f"Single: {i}/{len_rooms}")
        insertion_datetime = room['avlInsertionDate']

        if crawl_start_time is None:
            insertion_datetime_temp = insertion_datetime
            if type(insertion_datetime) == str:
                insertion_datetime_temp = datetime.strptime(
                    insertion_datetime, "%Y-%m-%d %H:%M:%S")
            crawl_start_time = insertion_datetime_temp.strftime(
                "%Y-%m-%d %H:00:00")

        romUUID = room['romUUID']

        alrInfo = {
            'base_price': {
                room['romID']: room['avlBasePrice'],
            },
            'discount_price': {
                room['romID']: room['avlDiscountPrice'],
            }
        }

        roomIDs = romUUID_romIDs.get(romUUID)
        if roomIDs is None:
            logger.critical(
                f"Room doesn't exist in no site. romUUID: {romUUID}")
            continue

        alrA_romID = roomIDs.get('A')
        alrS_romID = roomIDs.get('S')
        if alrA_romID is None or alrS_romID is None:
            logger.critical(
                f"Room doesn't exist in other site. romUUID: {romUUID}")
            continue

        room_alert = {
            "alrRoomUUID": romUUID,
            "alrOnDate": room['avlDate'],
            "alrCrawlTime": crawl_start_time,
            "alrType": 'R',
            "alrA_romID": alrA_romID,
            "alrS_romID": alrS_romID,
            "alrInfo": json.dumps(alrInfo)
        }

        identifier_dict = room_alert
        if insertion_datetime:
            room_alert["alrDateTime"] = insertion_datetime
        try:
            insert_select_id(
                table='tblAlert',
                key_value=room_alert,
                conn=conn,
                identifier_condition=identifier_dict
            )
        except Exception as e:
            print("duplication, ", ", ".join(
                [f"{k}: {v}" for k, v in identifier_dict.items()]))


if __name__ == "__main__":
    date = datetime.today().strftime("%Y-%m-%d")
    for st, en in [
        (f'{date} 00:00:00', f'{date} 12:00:00'),
        (f'{date} 12:00:00', f'{date} 24:00:00')
    ]:
        print(f"{st} // {en}")
        main(crawl_date_start=st, crawl_date_end=en)
