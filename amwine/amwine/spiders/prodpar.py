import scrapy


class ProdparSpider(scrapy.Spider):
    name = 'prodpar'
    allowed_domains = ['amwine.ru']
    start_urls = ['https://amwine.ru/catalog/krepkie_napitki/viski/']

    def parse(self, response):
        pass