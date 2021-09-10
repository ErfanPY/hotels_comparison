from .alibaba.scraper import main as alibaba_scraper
from .snapp_trip.scraper import main as snapp_trip_scraper
from .compare_rooms import main as comapre_runner
from .together_scrape import main as together_scrape

# from dotenv import load_dotenv, find_dotenv
import os

# env_path = find_dotenv(raise_error_if_not_found=True)
# # load_dotenv(dotenv_path=env_path, verbose=True, override=True)
# load_dotenv(dotenv_path=env_path, verbose=True)

proxy_host = os.environ.get("SCRAPPER_PROXY_HOST")
proxy_port = os.environ.get("SCRAPPER_PROXY_PORT")

if os.environ.get("SCRAPE_ALIBABA") == "1":
    alibaba_scraper(proxy_host=proxy_host, proxy_port=proxy_port)

if os.environ.get("SCRAPE_TOGETHER") == "1":
    together_scrape()

if os.environ.get("SCRAPE_SNAPPTRIP") == "1":
    snapp_trip_scraper(proxy_host=proxy_host, proxy_port=proxy_port)

if os.environ.get("COMPARE_SCRAPES") == "1":
    comapre_runner()

if os.environ.get("FIX_ABRV") == "1":
    comapre_runner()

print("NO env variable")