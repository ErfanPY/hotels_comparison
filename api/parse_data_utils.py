from collections import defaultdict


def group_alerts(database_result, verbose):
    result_data = []
    if verbose:
        result_data = verbose_alerts_to_dict(database_result)        
    else:
        dc_indexs = {}
        for alert in database_result:
            alert_data = alert_to_dict(alert)

            dc_key = alert['alrDateTime']+alert['alrCrawlTime']
            dc_i = dc_indexs.get(dc_key)
            if dc_i is None:
                dc_indexs[dc_key] = len(result_data)
                result_data.append({
                    "date": alert['alrDateTime'],
                    "crawlStartTime": alert['alrCrawlTime'],
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

    alibaba_id = alert['alrA_romID']
    snapptrip_id = alert['alrS_romID']

    res = {
        alert['alrRoomUUID']: {
            "type": alert_type,
            "detected-at": alert['alrDateTime'],
            "alibaba": {
                "base_price": bese_price.get(alibaba_id),
                "discount_amount": discount_price.get(alibaba_id),
                "name": alert['aName'],
            },
            "snapptrip": {
                "base_price": bese_price.get(snapptrip_id),
                "discount_amount": discount_price.get(snapptrip_id),
                "name": alert['bName'],

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
        i = city_index.get(alert['htlCity'])
        if i is None:
            result.append({
                alert['htlCity']: nested_dict()
            })
            i = len(result)
            city_index[alert['htlCity']] = i

        result[i][alert['htlCity']][alert['htlUUID']].update(alert_to_dict(alert))

    return result
            

def group_infos(infos):
    groups = []
    dc_index = {} # dc = date_crawlDate
  
    for info in infos:
        dc_key = info["avlDate"]+info["avlCrawlTime"]
        i = dc_index.get(dc_key)
        site = "alibaba" if info['htlFrom'][0].lower() == "a" else "snapptrip"

        if i is None:
            i = len(groups)
            dc_index[dc_key] = i
            groups.append({
                "date": info["avlDate"],
                "crawlStartTime": info["avlCrawlTime"],
                info['htlCity']: {
                    site: { # TODO:
                        "lowest-price": {
                            "amount": 1111,
                            "room-name": "ROOM_NAME_ALIBABA_n",
                            "room-uid": "ROOM_UID_n"
                        },
                        "room-count": 10,
                        "hotel": {
                            "fa": "HOTEL_NAME_ALIBABA_FA_n",
                            "en": "HOTEL_NAME_ALIBABA_EN_n"
                        }
                    }
                },
            })
        else:
            # TODO:
            groups[i][info['htlCity']][info['htlUUID']]
    return groups

# avlInsertionDate, 
# avlBasePrice, 
# avlDiscountPrice, 
# avlDate,
# htlFaName, htlEnName, htlCity, htlFrom, htlUUID
# romName, romMealPlan