## run 

python -m scrape.main

-a --alibaba 
Scrape alibabas hotels.

-s --snapp 
Scrape snapptrips hotels.

-c --compare 
Compare scraped hotels data.

--all 
Scrape both site hotels and Compare them.

--sleep 
Sleep time should sleep between scrape intervals (default 1 second).

--proxy-host 

--proxy-port

--log 
log file path


## env
### Configure database connection
MYSQL_HOST=127.0.0.1  
MYSQL_USER=user  
MYSQL_PASSWORD=password  
MYSQL_DATABASE=databse  

### Configure Email logging server
EMAIL_HOST=smtp.example.com  
EMAIL_USER_ADDR=mail@example.com  
EMAIL_PASSWORD=password  
\# EMAIL_TO_ADDR is comma seprated list  
EMAIL_TO_ADDR=admin@gmail.com,admin@example.com  
DONT_SEND_EMAIL=1  

### Debug
SCRAPPER_DEBUG=0  
DEBUG_HOTEL_NAME=  

### Limit the scrapers
ALIBABA_TO_SCRAPE_CITIES=  
ALIBABA_SCRAPPER_SLEEP_TIME=4  
ALIBABA_START_DAY=0  
SNAPPTRIP_TO_SCRAPE_CITIES=bushehr,kerman  
SNAPPTRIP_SCRAPPER_SLEEP_TIME=5  

### Which scrapers whill run  
SCRAPE_TOGETHER=1  
SCRAPE_ALIBABA=0  
SCRAPE_SNAPPTRIP=0  
COMPARE_SCRAPES=0  
