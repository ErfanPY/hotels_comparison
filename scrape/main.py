import argparse

from .alibaba.scraper import main as alibaba_scraper
from .snapp_trip.scraper import main as snapp_trip_scraper
from .compare_rooms import main as comapre_runner
parser = argparse.ArgumentParser(
        description='Scrape Alibaba & Snapptrip hotels price then compare them.')

parser.add_argument(
    '-a', '--alibaba', action='store_true',
    help="Scrape alibaba's hotels.")
parser.add_argument(
    '-s', '--snapp', action='store_true',
    help="Scrape snapptrip's hotels.")
parser.add_argument(
    '-c', '--compare', action='store_true',
    help='Compare scraped hotels data.')
parser.add_argument(
    '--all', action='store_true',
    help='Scrape both site hotels and Compare them.')
parser.add_argument(
    '--sleep', type=int, default=1,
    help='Sleep time should sleep between scrape intervals (default 1 second).')
parser.add_argument(
    '--proxy-host', type=str,
    help='Proxy host')
parser.add_argument(
    '--proxy-port', type=int,
    help='Ptoxy port')
parser.add_argument(
    '--log', type=str,
    help='log file path')

args = parser.parse_args()

if args.alibaba or args.all:
    alibaba_scraper(sleep_time=args.sleep, proxy_host=args.proxy_host, proxy_port=args.proxy_port)

if args.snap or args.all:
    snapp_trip_scraper(sleep_time=args.sleep, proxy_host=args.proxy_host, proxy_port=args.proxy_port)

if args.compare or args.all:
    comapre_runner()

print(args)
