# -*- coding: utf-8 -*-

# Scrapy settings for whoscored project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'Stanislav'

SPIDER_MODULES = ['squawka.spiders']
NEWSPIDER_MODULE = 'squawka.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36' #FAKE USER AGENT

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 1 #FAKE USER AGENT
#DOWNLOAD_TIMEOUT = 30

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY = 30 #FAKE USER AGENT
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 15 #FAKE USER AGENT
#CONCURRENT_REQUESTS_PER_IP = 16
#REDIRECT_MAX_TIMES = 5

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'whoscored.middlewares.WhoscoredSpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    'whoscored.middlewares.MyCustomDownloaderMiddleware': 543,
#}

SPIDER_MIDDLEWARES = {
    'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
}

SPLASH_URL = 'http://localhost:8050' #'http://192.168.59.103:8050'

DUPEFILTER_CLASS = 'scrapy_splash.SplashAwareDupeFilter'

HTTPCACHE_STORAGE = 'scrapy_splash.SplashAwareFSCacheStorage'

#fake user agent
DOWNLOADER_MIDDLEWARES = {
    #'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    #'scrapy_fake_useragent.middleware.RandomUserAgentMiddleware': 400,
    'scrapy_splash.SplashCookiesMiddleware': 723,
    'scrapy_splash.SplashMiddleware': 725,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,    
}

#DEFAULT_REQUEST_HEADERS = {
    #'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    #'accept-encoding': 'gzip, deflate',
    #'accept-language': 'uk-UA,uk;q=0.8,ru;q=0.6,en-US;q=0.4,en;q=0.2',
    #'cache-control': 'max-age=0',
    #'connection': 'keep-alive',
    #'host': 'epl.squawka.com',
    #'cookie': '__cfduid=d521671991c9d91d6d7d98a8d345fc0c11509256135; __qca=P0-1261407897-1509256137174; mcStep2=true; sqhome_competition=819; sqhome_competitionteam=0; PHPSESSID=kq2qtjrrt199f9qnr8hlk6eb10; _ga=GA1.2.662426480.1509256135; _gid=GA1.2.714579889.1509847494; sqhome_competitionidinfeed=8; sqhome_seasonid=2017; __asc=f48c6e4415f8ee703057492a287; __auc=afc5b74e15f66ad2849b14b11a4; __utmt=1; __utma=259859080.662426480.1509256135.1509920408.1509931025.14; __utmb=259859080.1.10.1509931025; __utmc=259859080; __utmz=259859080.1509256145.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)',
    #'upgrade-insecure-requests': '1',
    #'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
#}

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    'whoscored.pipelines.WhoscoredPipeline': 300,
#}

# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
