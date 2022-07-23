import scrapy
import json
from time import time
from amwine.items import Product


class ProdparSpider(scrapy.Spider):
    name = 'prodpar'
    allowed_domains = ['amwine.ru']
    start_urls = ['https://amwine.ru/catalog/krepkie_napitki/']

    headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}

    section_ids = ['29', '38']  # vino-16, viski-28, konyak-18, vodka-29, krepkie_napitki-185, pivo-38
    api = 'https://amwine.ru/local/components/adinadin/catalog.section.json/ajax_call.php'

    def parse(self, response):
        for i in self.section_ids:
            yield scrapy.Request(self.api, headers=self.headers,
                body=f'json=y&params%5BIBLOCK_TYPE%5D=catalog&params%5BIBLOCK_ID%5D=2&params%5BSECTION_ID%5D={i}'
                     f'&params%5BPRICE_CODE%5D=CFO&params%5BPAGE_ELEMENT_COUNT%5D=18',
                callback=self.parse_page, meta={'section_id': i})

    def parse_page(self, response):
        """
        Делаем повторный запрос, с количеством всех товаров.
        """
        data = json.loads(response.body)
        page_element_count = data["productsTotalCount"]
        section_id = response.meta['section_id']
        yield scrapy.Request(self.api,
                             headers=self.headers,
                             body=f'json=y&params%5BIBLOCK_TYPE%5D=catalog&params%5BIBLOCK_ID%5D=2&params%5BSECTION_ID%5'
                                  f'D={section_id}&params%5BPRICE_CODE%5D=CFO&params%5BPAGE_ELEMENT_COUNT%5'
                                  f'D={page_element_count}',
                             method='POST',
                             callback=self.parse_links
                             )

    def parse_links(self, response):
        """
        Получаем все ссылки товаров.
        """
        result = json.loads(response.body)
        for product in result['products']:
            url = response.urljoin(product['link'])
            available = False
            if product['available']:
                available = True

            yield scrapy.Request(url, callback=self.parse_product, meta={'available': available})

    def parse_product(self, response):
        """
        Парсим страницу товара.
        """
        item = Product()
        item['timestamp'] = time()
        item['url'] = response.url
        item['title'] = response.css('div.catalog-element-info__title h1::text').get().strip()
        item['marketing_tags'] = []
        item['brand'] = ''
        item['section'] = [x.strip() for x in response.css('div.breadcrumbs a::text').getall()]
        item['variants'] = 1
        try:
            image = 'https://amwine.ru' + response.css('div.catalog-element-info__picture img::attr(src)').get()
        except:
            image = ''
        try:
            item['RPC'] = response.css('div.catalog-element-info__article span::text').get().split()[-1]
        except:
            item['RPC'] = ''
        item['assets'] = {
            "main_image": image,
            "set_images": [],
            "view360": [],
            "video": []
        }
        item['price_data'] = {
            'current': 0.0,
            'original': 0.0,
            'sale_tag': ''
        }
        item['stock'] = {
            'in_stock': response.meta['available'],
            'count': 0
        }
        item['metadata'] = {
            '__description': '',
            'Страна': '',
            'Объем': '',
            'Производитель': '',
            'Крепость': '',
            'Выдержка': '',
        }
        wine_params = [x.replace('\n', '').replace(' ', '') for x in
                       response.css('div.about-wine__param *::text').getall()]
        wine_params = [x for x in wine_params if x]
        for i in range(0, len(wine_params), 2):
            if wine_params[i] in item['metadata']:
                item['metadata'][wine_params[i]] = wine_params[i + 1]
            elif wine_params[i] == 'Бренд':
                item['brand'] = wine_params[i + 1]
        description = [x.replace('\n', '') for x in response.css('div.about-wine__block.col-md-4 *::text').getall()]
        description = [x for x in description if x.replace(' ', '')]
        item['metadata']['__description'] = ': '.join(description)
        price = response.css(
            'div.catalog-element-info__price.catalog-element-info__price_detail.mobile-show *::text').getall()
        price = [float(x.replace(' ', '')) for x in price if x.replace(' ', '').replace('.', '').isdigit()]
        if len(price) == 1:
            item['price_data'] = {
                'current': price[0],
                'original': price[0],
                'sale_tag': ''
            }
        elif len(price) == 2:
            item['price_data'] = {
                'current': price[0],
                'original': price[1],
                'sale_tag': 'Скидка ' + str(int((price[1] - price[0]) // (price[1] / 100))) + '%'
            }
        yield item
