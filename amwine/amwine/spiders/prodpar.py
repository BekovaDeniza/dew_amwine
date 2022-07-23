import scrapy
import json
from time import time
from amwine.items import Product


class ProdparSpider(scrapy.Spider):
    name = 'prodpar'
    allowed_domains = ['amwine.ru']
    start_urls = ['https://amwine.ru/catalog/krepkie_napitki/']

    headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/103.0.0.0 Safari/537.36'}

    section_ids = ['29', '38']  # vino-16, viski-28, konyak-18, vodka-29, krepkie_napitki-185, pivo-38
    api = 'https://amwine.ru/local/components/adinadin/catalog.section.json/ajax_call.php'

    def parse(self, response):
        for i in self.section_ids:
            yield scrapy.Request(self.api, headers=self.headers,
                                 body=f'json=y&params%5BIBLOCK_TYPE%5D=catalog&params%5BIBLOCK_ID%5D=2&params%5B'
                                      f'SECTION_ID%5D={i}&params%5BPRICE_CODE%5D=CFO&params%5BFILTER_NAME%5D=arrF'
                                      f'ilterCatalog&params%5BSORT_ORDER%5D=ASC&params%5BSORT_FIELD%5D=SORT',
                                 callback=self.parse_page, method='POST', meta={'section_id': i})

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
                                  f'D={section_id}&params%5BPRICE_CODE%5D=CFO&params%5BPAGE_ELEMENT_COUNT%5D='
                                  f'{page_element_count}&params%5BFILTER_NAME%5D=arrFilterCatalog&params%5BSORT_ORDER'
                                  f'%5D=ASC&params%5BSORT_FIELD%5D=SORT',
                             method='POST',
                             callback=self.parse_links
                             )

    def parse_links(self, response):
        """
        Получаем все ссылки на продуты и парсим из api имеющуюся информацию.
        """
        result = json.loads(response.body)
        for product in result['products']:
            print(product['name'])
            temp_data = {'available': product['available'], 'id': product['id'], 'name': product['name'],
                         'article': product['props']['article'], 'image': product['preview_picture'],
                         'price': {
                             'current': product['props']['middle_price_77'],
                             'original': product['props']['old_price_77'],
                             'sale': product['sale']
                         }
                         }
            url = response.urljoin(product['link'])
            yield scrapy.Request(url, callback=self.parse_product, meta={'temp_data': temp_data})

    def parse_product(self, response):
        """
        Парсим страницу товара.
        """
        item = Product()
        item['timestamp'] = time()
        item['RPC'] = response.meta['temp_data']['id']
        item['url'] = response.url
        item['title'] = response.meta['temp_data']['name']
        item['marketing_tags'] = []
        item['brand'] = ''
        item['section'] = [x.strip() for x in response.css('div.breadcrumbs a::text').getall()]
        item['variants'] = 1
        item['assets'] = {
            "main_image": 'https://amwine.ru' + response.meta['temp_data']['image'],
            "set_images": [],
            "view360": [],
            "video": []
        }
        item['price_data'] = {
            'current': float(response.meta['temp_data']['price']['current']),
            'original': float(response.meta['temp_data']['price']['original']),
            'sale_tag': ''
        }
        sale = response.meta['temp_data']['price']['sale']
        if sale: item['price_data']['sale_tag'] = 'Скидка ' + sale.replace('-', '')
        item['stock'] = {
            'in_stock': response.meta['temp_data']['available'],
            'count': 0
        }
        item['metadata'] = {
            '__description': '',
            'Страна': '',
            'Объем': '',
            'Производитель': '',
            'Крепость': '',
            'Выдержка': '',
            'Артикул': str(response.meta['temp_data']['article'])
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
        for i in range(0, len(description), 2):
            if description[i] == 'Описание':
                item['metadata']['__description'] = description[i+1]
        yield item