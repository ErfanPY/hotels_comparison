import os

import mysql.connector
import logging
from dotenv import load_dotenv, find_dotenv

from scrape.alibaba.scraper import city_ids
import re

logger = logging.getLogger(__name__)

env_path = find_dotenv(raise_error_if_not_found=True)
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

DO_WARN_NO_RESULT = True
DO_WARN_MANY_RESULTS = False

def get_db_connection(host=None, user=None, password=None, port=None, database=None):
    cnx = mysql.connector.connect(
        host     = host      or os.environ.get("MYSQL_HOST"),
        user     = user      or os.environ.get("MYSQL_USER"),
        password = password  or os.environ.get("MYSQL_PASSWORD"),
        # port     = port      or os.environ.get("MYSQL_PORT"),
        database = database  or os.environ.get("MYSQL_DATABASE")
    )

    return cnx

def custom(query_string:str, data:list=[], conn=None, res=True):
    curs = conn.cursor(buffered=True, dictionary=True)

    curs.execute(query_string, data)

    if res:
        result = curs.fetchall()
        
        return result


for city_name in city_ids.keys():
    query_templ = """
    SELECT htlID, htlEnName, htlFaName FROM tblHotels
    WHERE htlCity = "{}" AND htlFrom = "{}" AND htlUUID is NULL
    """
    
    alibaba_query = query_templ.format(city_name, "A")
    
    with get_db_connection() as conn:
        alibaba_hotels = custom(
            query_string=alibaba_query,
            conn=conn)

        for alibaba_hotel in alibaba_hotels:
            alibaba_hotel_name = re.sub(" ", "-", alibaba_hotel['htlFaName'].strip())
            snapp_query = query_templ+" AND htlFaName like '%{}%'"
            snapp_query = snapp_query.format(
                city_name,
                "S",
                alibaba_hotel_name
            )
            
            snapp_hotels = custom(
                query_string=snapp_query,
                conn=conn
            )

            # logger.error("Matchs: {}".format(len(snapp_hotels)))
            if len(snapp_hotels) == 0 and DO_WARN_NO_RESULT:
                with open("hotels_UUID.txt", 'w') as f:
                    f.write("Zero result\n"+alibaba_hotel_name+'\n')
                    f.write(str(alibaba_hotel))
                    
                edited_hotel = alibaba_hotel
                edited_hotel['htlFaName'] = input("search? ")
                if not edited_hotel['htlFaName'] == "" and not edited_hotel['htlFaName'] == " " and edited_hotel['htlFaName']:
                    alibaba_hotels.append(edited_hotel)

            if len(snapp_hotels) > 1 and DO_WARN_MANY_RESULTS:

                with open("hotels_UUID.txt", 'w') as f:
                    f.write("Many results\n")
                    many_hotels_name = [str(h['htlFaName']) for h in snapp_hotels]
                    
                    f.write("\n".join(many_hotels_name))

            for snapp_hotel in snapp_hotels:
                match_string = "\nA: \n\tEN: {}\n\tFA: {}\nS:\n\tFA: {}\n".format(
                    alibaba_hotel['htlEnName'],
                    alibaba_hotel['htlFaName'],
                    snapp_hotel['htlFaName'],
                    )
                with open("hotels_UUID.txt", 'a') as f:
                    f.write(match_string)

                if len(snapp_hotels) == 1:
                    mathc_check = "y"
                elif DO_WARN_MANY_RESULTS:
                    mathc_check = input("y/n? [Press any key for y]: ")

                if mathc_check.lower() == "y":
                    update_query = "UPDATE `Alibaba`.`tblHotels` SET `htlUUID`='{}', `htlEnName`='{}' WHERE  `htlID`={} or `htlID`={};".format(
                        alibaba_hotel['htlEnName'],
                        alibaba_hotel['htlEnName'],
                        alibaba_hotel['htlID'],
                        snapp_hotel['htlID'],
                    )
                    custom(update_query, conn=conn, res=False)
                    conn.commit()