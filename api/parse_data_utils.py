from datetime import datetime
from collections import defaultdict
import json


def normalize_crawl_time(crawl_time:datetime):
    date_part = str(crawl_time).split()[0]
    am_start = datetime.strptime(f"{date_part} 00:00:00", "%Y-%m-%d %H:%M:%S")
    am_end = datetime.strptime(f"{date_part} 12:00:00", "%Y-%m-%d %H:%M:%S")

    stat = "AM" if am_start <= crawl_time < am_end else "PM"
    
    return f"{date_part}-{stat}"


def group_alerts(database_result, verbose):
    result_data = []
    dc_indexs = {}
    nested_dict = lambda: defaultdict(nested_dict)

    for alert in database_result:
        alrCrawlTime = normalize_crawl_time(alert['alrCrawlTime'])
        alert['alrInfo'] = json.loads(alert['alrInfo'])
        alert_data = alert_to_dict(alert, verbose=verbose)

        dc_key = f"{alert['alrDateTime'].date()}/{alrCrawlTime}"
        dc_i = dc_indexs.get(dc_key)
        if dc_i is None:
            dc_indexs[dc_key] = len(result_data)

            if verbose:
                result_data.append({
                    "date": str(alert['alrDateTime'].date()),
                    "crawlStartTime": str(alrCrawlTime),
                    "alerts": nested_dict()
                })
                result_data[-1]['alerts'][alert['htlCity']][alert['htlUUID']][alert['alrRoomUUID']] = [alert_data[alert['alrRoomUUID']]]
                # result_data[dc_i]['alerts']["CITY_UID_n"]["HOTEL_UID_n"][alert['alrRoomUUID']] = [alert_data[alert['alrRoomUUID']]]
            else:
                result_data.append({
                    "date": str(alert['alrDateTime'].date()),
                    "crawlStartTime": str(alrCrawlTime),
                    "alerts": [alert_data]
                })
        else:
            if verbose:
                same_uuid_rooms = result_data[dc_i]['alerts'][alert['htlCity']][alert['htlUUID']].get(alert['alrRoomUUID'])
                if same_uuid_rooms is None:
                    result_data[dc_i]['alerts'][alert['htlCity']][alert['htlUUID']][alert['alrRoomUUID']] = [alert_data[alert['alrRoomUUID']]]
                else:
                    result_data[dc_i]['alerts'][alert['htlCity']][alert['htlUUID']][alert['alrRoomUUID']].append(alert_data[alert['alrRoomUUID']])
            else:
                result_data[dc_i]['alerts'].append(alert_data)

    return result_data


def alert_to_dict(alert, verbose=False):
    type_letter = alert['alrType'][0].lower()
    if type_letter == "p":
        alert_type = "price"
    elif type_letter == "d":
        alert_type = "discount"
    elif type_letter == "r":
        alert_type = "reserve"
    else:
        print("No alert type "+alert['alrType'])
    
    bese_price = alert['alrInfo']['base_price']
    discount_price = alert['alrInfo']['discount_price']

    alibaba_id = str(alert['alrA_romID'])
    snapptrip_id = str(alert['alrS_romID'])

    res = {
        alert['alrRoomUUID']: {
            "type": alert_type,
            "detected-at": str(alert['alrDateTime']),
            "alibaba": {
                "base_price": bese_price.get(alibaba_id),
                "discount_amount": discount_price.get(alibaba_id),
                "name": alert['aName'],
            },
            "snapptrip": {
                "base_price": bese_price.get(snapptrip_id),
                "discount_amount": discount_price.get(snapptrip_id),
                "name": alert['sName'],

            }
        }
    }
    if verbose:
        res[alert['alrRoomUUID']]["alibaba"]['hotel'] = {
                    "fa": alert["ahtlFaName"],
                    "en": alert["ahtlEnName"]
                }
        res[alert['alrRoomUUID']]["snapptrip"]['hotel'] = {
                    "fa": alert["shtlFaName"],
                    "en": alert["shtlEnName"]
                }

    return res


def group_infos(infos):
    groups = []
    dc_index = {} # dc = date_crawlDate
    nested_dict = lambda: defaultdict(nested_dict)
    
    hotel_rooms = defaultdict(set)
    for info in infos:
        hotel_name = info['htlEnName'] or info['htlFaName']
        site = "alibaba" if info['htlFrom'][0].lower() == "a" else "snapptrip"
        hotel_rooms[f"{info['htlCity']}//{hotel_name}//{site}"].add(info['romID'])
        
    for info in infos:
        avlCrawlTime = normalize_crawl_time(info['avlCrawlTime'])
        hotel_name = info['htlEnName'] or info['htlFaName']
        site = "alibaba" if info['htlFrom'][0].lower() == "a" else "snapptrip"

        dc_key = f'{info["avlDate"]} {avlCrawlTime}'
        i = dc_index.get(dc_key)

        if i is None:
            i = len(groups)
            dc_index[dc_key] = i
            groups.append(nested_dict())
            groups[i]["date"] = str(info["avlDate"])
            groups[i]["crawlStartTime"] = str(avlCrawlTime)
            groups[i][info['htlCity']][hotel_name][site] = info_to_site(info, hotel_rooms)
            
        else:
            prev_hotel = groups[i][info['htlCity']][hotel_name].get(site)
            if prev_hotel is None or not "lowest-price" in prev_hotel.keys():
                groups[i][info['htlCity']][hotel_name][site] = info_to_site(info, hotel_rooms)
            else:
                low_p = groups[i][info['htlCity']][hotel_name][site]['lowest-price']['amount']
                room_count = groups[i][info['htlCity']][hotel_name][site]['room-count']
                if info['avlDiscountPrice'] < low_p:
                    groups[i][info['htlCity']][hotel_name][site] = info_to_site(info, hotel_rooms)
        
        groups[i][info['htlCity']][hotel_name]["hotel-uid"] = info['htlUUID']

    return groups


def info_to_site(info, hotel_rooms):
    hotel_name = info['htlEnName'] or info['htlFaName']
    site = "alibaba" if info['htlFrom'][0].lower() == "a" else "snapptrip"
    rooms_count = len(hotel_rooms[f"{info['htlCity']}//{hotel_name}//{site}"])

    return { 
        "lowest-price": {
            "amount": info['avlDiscountPrice'],
            "room-name": info['romName'],
            "room-uid": info["romUUID"]
        },
        "room-count": rooms_count,
        "hotel": {
            "fa": info["htlFaName"],
            "en": info["htlEnName"]
        }
    }
