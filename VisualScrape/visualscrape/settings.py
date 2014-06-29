'''
Created on May 26, 2014
@author: Mohammed Hamdy
'''
"""Warning: setting names should not begin with underscores, since these are used internally"""

from visualscrape.lib.types import SpiderTypes as _spidertypes

BOT_NAME = 'ScrapyCrawler'

SPIDER_MODULES = ['visualscrape.lib.scrapylib.scrapy_crawl']
NEWSPIDER_MODULE = 'NefsakLaptops.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'NefsakLaptops (+http://www.yourdomain.com)'
ITEM_PIPELINES = {"visualscrape.lib.scrapylib.pipeline.ItemPostProcessor": 1,
                  'scrapy.contrib.pipeline.images.ImagesPipeline': 2,
                  "visualscrape.lib.scrapylib.pipeline.CanonicalizeImagePathPipeline": 101,
                  "visualscrape.lib.scrapylib.pipeline.FilterFieldsPipeline": 100,
                  "visualscrape.lib.scrapylib.pipeline.PushToHandlerPipeline": 1000}
                  #"carscraper.pipeline.CorrectMotoFieldNamesPipeline":102}

IMAGES_STORE = "D:/scraped_images" #relative to the project directory?
_CONFIG_PATH = "D:/scraped_images/config" # this is a path used for spider configuration, like current progress
SCRAPER_CLASSES = {"visualscrape.lib.scrapylib.ScrapyCrawler" : _spidertypes.TYPE_SCRAPY,
                   "visualscrape.lib.seleniumlib.selenium_crawl.SeleniumCrawler" : _spidertypes.TYPE_SELENIUM}

ITEM_LOADER = "visualscrape.lib.scrapylib.itemloader.DefaultItemLoader"

DOWNLOAD_FAVICON = False

FEED_FORMAT = "json"
FEED_URI = "file:///C:/Users/Tickler/Desktop/example.json"

USER_AGENT = "Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0"

SITE_PARAMS = {"http://www.machinerytrader.com/":{"REQUEST_DELAY":3, 
              #The cookies enabled settings applies actually per-start-url, not per-site
                                                  "COOKIES_ENABLED": True,
                                                  "PREFERRED_SCRAPER": _spidertypes.TYPE_SELENIUM, # Uses indexes from SCRAPER_CLASSES
                                                  "ITEM_LOADER": "carscraper.itemloader.CarItemLoader",
                                                  },
               "http://www.cycletrader.com":{"PREFERRED_SCRAPER":_spidertypes.TYPE_SELENIUM,
                                             "REQUEST_DELAY": 1,
                                             "ITEM_LOADER": "carscraper.itemloader.CarItemLoader"}, # use the car item loader because it overrider takefirst on output
               
               "http://www.ebay.com/":{"PREFERRED_SCRAPER": _spidertypes.TYPE_SELENIUM,
                                       "REQUEST_DELAY": 1,
                                       "ITEM_LOADER": "carscraper.itemloader.CarItemLoader"},
               
               "http://www.cars.com":{"PREFERRED_SCRAPER":_spidertypes.TYPE_SELENIUM, # runs quite well with 1
                                      "REQUEST_DELAY": 1, 
                                      "ITEM_LOADER": "carscraper.itemloader.CarItemLoader"},
               
               "http://www.autotrader.com":{"PREFERRED_SCRAPER":_spidertypes.TYPE_SELENIUM, # requires click pagination
                                            "REQUEST_DELAY":1,
                                            "ITEM_LOADER": "carscraper.itemloader.CarItemLoader"}}