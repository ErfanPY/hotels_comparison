from .alibaba.scraper import main as alibaba_scraper
from .snapp_trip.scraper import main as snapp_trip_scraper
from .compare_rooms import main as comapre_runner

from dotenv import load_dotenv
import os

load_dotenv("../.env")

sleep_time = os.environ.get("SCRAPPER_SLEEP_TIME")
proxy_file = os.environ.get("SCRAPPER_PROXY_FILE")

if os.environ.get("SCRAPE_ALIBABA"):
    alibaba_scraper(sleep_time=sleep_time, proxy_file=proxy_file)

if os.environ.get("SCRAPE_SNAPPTRIP"):
    snapp_trip_scraper(sleep_time=sleep_time, proxy_file=proxy_file)

if os.environ.get("COMPARE_SCRAPES"):
    comapre_runner()
