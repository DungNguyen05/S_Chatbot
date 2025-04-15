import scrapy
from .fetch_article_links import fetch_article_links
import datetime

class ArticleSpider(scrapy.Spider):
    name = 'coin68_content'

    custom_settings = {
        'LOG_ENABLED': False,  # Disable logging
        'FEEDS': {  
            'articles.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 4,
                'overwrite': True
            },
        },
    }

    def __init__(self, target_count=30, driver=None, *args, **kwargs):
        self.target_count = target_count
        self.driver = driver
        self.article_count = 0
        self.failed_count = 0
        super(ArticleSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        links = fetch_article_links(self.driver, self.target_count) 

        for link in links:
            yield scrapy.Request(url=link, callback=self.parse, errback=self.errback)

    def parse(self, response):
        try:
            title = response.css('h1::text').get()
            paragraphs = response.xpath('//div[@id="content"]//text()').getall()
            content = ' '.join([text.strip() for text in paragraphs if text.strip()]).strip()
            source = 'coin68.com'

            published_at = response.xpath('//span[contains(@class, "css-1sdkvdj")]/text()').get()
            day, month, year = published_at.split("/")
            formatted_date = f"{year}-{month}-{day} 00:00:00"
            published_at = formatted_date

            self.article_count += 1
            print(f"✅ Processed article {self.article_count}/{self.target_count}", end="\r", flush=True)

            # Yield article data, Scrapy will automatically save it to articles.json
            yield {
                'title': title,
                'url': response.url,
                'source': source,
                'published_at': published_at,
                'currencies': None,
                'content': content,
            }
        except Exception as e:
            self.failed_count += 1
            print(f"⏩ Skipping article: {response.url} - {str(e)}")

    def errback(self, failure):
        self.failed_count += 1
        request = failure.request
        print(f"⏩ Failed to fetch article: {request.url}")

    def closed(self, reason):
        print(f"✅ {self.article_count} articles content fetched, {self.failed_count} failed")