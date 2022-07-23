BOT_NAME = 'amwine'

SPIDER_MODULES = ['amwine.spiders']
NEWSPIDER_MODULE = 'amwine.spiders'


FEED_EXPORT_ENCODING = 'utf-8'
FEED_EXPORT_FIELDS = ['timestamp', 'RPC', 'url',
                      'title', 'marketing_tags', 'brand',
                      'section', 'price_data', 'stock',
                      'assets', 'metadata', 'variants']
FEED_FORMAT = "json"
FEED_URI = "amwine.json"
ROBOTSTXT_OBEY = False

CONCURRENT_REQUESTS = 16

DOWNLOAD_DELAY = 1
