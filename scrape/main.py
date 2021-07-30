from .alibaba.scraper import main as alibaba_scraper
from .snapp_trip.scraper import main as snapp_trip_scraper
from .compare_rooms import main as comapre_runner

from dotenv import load_dotenv, find_dotenv
import os

env_path = find_dotenv(raise_error_if_not_found=True)
load_dotenv(dotenv_path=env_path, verbose=True, override=True)

sleep_time = int(os.environ.get("SCRAPPER_SLEEP_TIME", "1"))
proxy_file = os.environ.get("SCRAPPER_PROXY_FILE")

if os.environ.get("SCRAPE_ALIBABA"):
    alibaba_scraper(sleep_time=sleep_time, proxy_file=proxy_file)

if os.environ.get("SCRAPE_SNAPPTRIP"):
    snapp_trip_scraper(sleep_time=sleep_time, proxy_file=proxy_file)

if os.environ.get("COMPARE_SCRAPES"):
    comapre_runner()
