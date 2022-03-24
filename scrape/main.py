from .alibaba.scraper import main as alibaba_scraper
from .snapp_trip.scraper import main as snapp_trip_scraper
from .compare_rooms import main as comapre_runner
from .together_scrape import main as together_scrape

import os


if os.environ.get("SCRAPE_ALIBABA") == "1":
    alibaba_scraper()

if os.environ.get("SCRAPE_TOGETHER") == "1":
    together_scrape()

if os.environ.get("SCRAPE_SNAPPTRIP") == "1":
    snapp_trip_scraper()

if os.environ.get("COMPARE_SCRAPES") == "1":
    comapre_runner()

if os.environ.get("FIX_ABRV") == "1":
    comapre_runner()

print("DONE")
