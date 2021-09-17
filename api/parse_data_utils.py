from collections import defaultdict
import json


def group_alerts(database_result, verbose):
    result_data = []
    if verbose:
        result_data = verbose_alerts_to_dict(database_result)        
    else:
        dc_indexs = {}
        for alert in database_result:
            alert['alrInfo'] = json.loads(alert['alrInfo'])
            alert_data = alert_to_dict(alert)

            dc_key = f"{alert['alrDateTime']}-{alert['alrCrawlTime']}"
            dc_i = dc_indexs.get(dc_key)
            if dc_i is None:
                dc_indexs[dc_key] = len(result_data)
                result_data.append({
                    "date": str(alert['alrDateTime'].date()),
                    "crawlStartTime": str(alert['alrCrawlTime']),
                    "alerts": alert_data
                })
            else:
                result_data[dc_i]['alerts'].update(alert_data)

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
                    "fa": alert["htlEnName"],
                    "en": alert["htlFaName"]
                }
        res[alert['alrRoomUUID']]["snapptrip"]['hotel'] = {
                    "fa": alert["htlEnName"],
                    "en": alert["htlFaName"]
                }

    return res


def verbose_alerts_to_dict(alerts):
    result = []
    nested_dict = lambda: defaultdict(nested_dict)

    city_index = {}
    for alert in alerts:
        alert['alrInfo'] = json.loads(alert['alrInfo'])

        i = city_index.get(alert['htlCity'])
        if i is None:
            i = len(result)
            result.append({
                alert['htlCity']: nested_dict()
            })
            city_index[alert['htlCity']] = i

        result[i][alert['htlCity']][alert['htlEnName']].update(alert_to_dict(alert))

    return result
            

def group_infos(infos):
    groups = []
    dc_index = {} # dc = date_crawlDate
    nested_dict = lambda: defaultdict(nested_dict)
  
    for info in infos:
        dc_key = f'{info["avlDate"]} {info["avlCrawlTime"]}'
        i = dc_index.get(dc_key)
        site = "alibaba" if info['htlFrom'][0].lower() == "a" else "snapptrip"
        
        if i is None:
            i = len(groups)
            dc_index[dc_key] = i
            groups.append(nested_dict())
            groups[i]["date"] = str(info["avlDate"])
            groups[i]["crawlStartTime"] = str(info["avlCrawlTime"])
            groups[i][info['htlCity']][info['htlEnName']]["hotel-uid"] = info['htlUUID']
            groups[i][info['htlCity']][info['htlEnName']][site] = info_to_site(info)
            
        else:
            prev_hotel = groups[i][info['htlCity']][info['htlEnName']].get(site)
            if prev_hotel is None or not "lowest-price" in prev_hotel.keys():
                groups[i][info['htlCity']][info['htlEnName']][site] = info_to_site(info)
            else:
                low_p = groups[i][info['htlCity']][info['htlEnName']][site]['lowest-price']['amount']
                room_count = groups[i][info['htlCity']][info['htlEnName']][site]['room-count']
                if info['avlDiscountPrice'] < low_p:
                    groups[i][info['htlCity']][info['htlEnName']][site] = info_to_site(info, room_count)
                else:
                    groups[i][info['htlCity']][info['htlEnName']][site]['room-count'] = room_count+1
    return groups


def info_to_site(info, room_count=0):
    return { 
        "lowest-price": {
            "amount": info['avlDiscountPrice'],
            "room-name": info['romName'],
            "room-uid": info["romUUID"]
        },
        "room-count": room_count+1,
        "hotel": {
            "fa": info["htlFaName"],
            "en": info["htlEnName"]
        }
    }
