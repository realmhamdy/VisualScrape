'''
Created on May 26, 2014
@author: Mohammed Hamdy
'''
from scrapy.contrib.spiders import CrawlSpider
from scrapy.http import Request, FormRequest
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import Selector
from scrapy import signals
from multiprocessing import Process
import urlparse
from visualscrape.lib.path import URL, Form
from visualscrape.config import settings
from visualscrape.lib.item import InterestItem, FaviconItem
from visualscrape.lib.selector import FieldSelector, ImageSelector
from visualscrape.lib.signal import SpiderStarted, SpiderClosed
from visualscrape.lib.event_handler import EventConfigurator

class ScrapyCrawler(CrawlSpider, EventConfigurator):
  """
  This spider now doesn't support multiple urls per path, something 
  like start_urls=[url1, more than 1 url...]
  """
  name = "ScrapyCrawler"
  def __init__(self, spiderInfo, spiderID, name="ScrapyCrawler", *args, **kwargs):
    EventConfigurator.__init__(self, spiderInfo, spiderID, name, *args, **kwargs)
    self._spider_info = spiderInfo
    # prevent the handler from being pickled into the spider process. It's not needed anymore after EventConfigurator.__init__
    self._spider_info.handler = None 
    self.name = spiderInfo.spider_name
    self.request_delay = kwargs.get("requestDelay", 1) #scrapy uses something between .5 and 1.5
    self.path = spiderInfo.spider_path
    self.id = spiderID # this is a public property
    self.path_index = 0
    self.favicon_required = kwargs.get("downloadFavicon", True) #the favicon for the scraped site will be added to the first item
    self.item_loader = kwargs.get("itemLoader")
    self.favicon_item = None
  
  def start_requests(self):
    #this might not work as per docs if it returns items. see Spiders page
    if self.event_handler: self.event_handler.emit(SpiderStarted(self.id))
    start_path = self.path[0]
    if self.favicon_required: #the first item contains only the favicon
      #obtain the favicon url
      start_url = start_path if isinstance(start_path, URL) else start_path.url
      url_components = urlparse.urlparse(start_url)
      favicon_url = urlparse.urljoin(url_components.scheme + "://" + url_components.netloc, "favicon.ico")
      favicon_item = FaviconItem()
      favicon_item["image_urls"] =  [favicon_url]
      favicon_item["id"] =  self.id
      self.favicon_item = favicon_item #assign it to be returned later. can't return here
    return self._take_step()
  
  def parse_intermediate(self, response):
    """This should continue until there's only one item in self.path which is
       MainPage object"""
    return self._take_step()
    
  def parse_item_pages(self, response):
    """Gets the pages of items from a MainPage"""
    main_page = self.path[-1]
    similar_pages_selector = main_page.similar_pages_selector
    similar_pages_restrict = main_page.similar_pages_restrict
    # i think yield from syntax would've helped me refactor the next section. But it's only in 3.3
    if similar_pages_selector:
      similar_nav = self._links_from_selector(response, similar_pages_selector, similar_pages_restrict)
      for nav in similar_nav: yield Request(nav, dont_filter=False, callback=self.parse_item_pages) # the extracted links can well have their crawled friends
      
    item_page_selector = self.path[-1].item_page_selector
    item_pages = self._links_from_selector(response, item_page_selector, restrict=None)
    for request in [Request(page, callback=self.parse_items) for page in item_pages]:
      yield request
    
  def parse_items(self, response):
    if self.favicon_item:
      yield self.favicon_item
      self.favicon_item = None
    item_selector = self.path[-1].item_selector
    item_info = {"keys":[], "values":[], "types":[]}
    # fill an item loader
    for key_value_selector in item_selector:
      # keys can be either strings or selectors
      key_selector = key_value_selector.key_selector
      if isinstance(key_selector, FieldSelector):
        sel = Selector(response)
        if key_selector.type == FieldSelector.XPATH:
          key = sel.xpath(key_selector).extract()
        elif key_selector.type == FieldSelector.CSS:
          key = sel.css(key_selector).extract()
        if key: key = key[0]
        else: key = "Invalid_Key_Selector" #this may pack in all values with invalid keys with this key.
      else: #key_selector is a FieldSelector, use it to get the key from the response
        key = key_selector
      item_info["keys"].append(key)
      value_selector = key_value_selector.value_selector
      item_info["values"].append(value_selector)
    # dynamically create the item from collected keys. The item must be created before the item loader
    item = InterestItem(item_info["keys"])
    item_loader = self.item_loader(item, response=response, response_ctx=response) #pass the response to i/o processors
    for (key, value_selector) in zip(item_info["keys"], item_info["values"]):
      if value_selector.type == FieldSelector.CSS:
        if isinstance(value_selector, ImageSelector):
          item_loader.add_css("image_urls", value_selector)
        else:
          item_loader.add_css(key, value_selector)
      elif value_selector.type == FieldSelector.XPATH:
        if isinstance(value_selector, ImageSelector):
          item_loader.add_xpath("image_urls", value_selector)
        else:
          item_loader.add_xpath(key, value_selector)
    item_loader.add_value("id", self.id)
    item = item_loader.load_item()
    yield item
    
  def _take_step(self):
    step = self.path.pop(0)
    next_step = self.path[0]
    callback = self.parse_intermediate if isinstance(next_step, (URL, Form)) \
       else self.parse_item_pages
    if isinstance(step, URL):
      next_url = step
      request = Request(next_url, callback=callback)
    elif isinstance(step, Form):
      next_url = step.url
      form_data = {elem.name:elem.value for elem in step.data}
      request = FormRequest(next_url, form_data, 
                          callback=callback)
      
    return [request]
  
  def _links_from_selector(self, response, selector, restrict=None):
    if selector.type == FieldSelector.REGEX:
      # use rules to do manual link extraction, since scrapy seems not to do it unless the rules are a class attribute
      similar_extractor = SgmlLinkExtractor(allow=(selector,),
                         restrict_xpaths=(restrict,) if restrict else ())
      links = [link.url for link in similar_extractor.extract_links(response)]
    else:
      sel = Selector(response)
      if selector.type == FieldSelector.CSS:
        if not "::href" in selector: selector = selector + "::attr(href)"
        links = sel.css(selector).extract()
      elif selector.type == FieldSelector.XPATH:
        if not "@href" in selector: selector = selector + "/@href"
        links = sel.xpath(selector).extract()
      # canonicalize ...
      links = [URL(link).canonicalize(response.url) for link in links]
    return links
  
  
  @staticmethod      
  def get_manager():
    return ScrapyManager

# ------------------------------------------------------------------------- #
#two modules brought together to solve a circular import

from twisted.internet import reactor
import os
from scrapy.crawler import Crawler
from scrapy import log
from scrapy.utils.project import get_project_settings


class ScrapyManager(object):
  """Takes the spider information and handles launching and 
     termination of the spider(s)"""
  def __init__(self, spidersInfo=[]):
    # set the settings directory. Use scrapy settings manager
    os.environ["SCRAPY_SETTINGS_MODULE"] = "visualscrape.settings"
    self.spiders_info = spidersInfo
    self.closed_spiders = 0
    self.crawlers = []
    self._crawl_process = Process(target=self.run_spiders, args=())
    
  def start_all(self):
    #self._crawl_process.start()
    self.run_spiders()
    
  def run_spiders(self):
    """Currently, all the spiders are run within the same process"""
    log.start(loglevel=log.DEBUG)
    for (id, sp_info) in enumerate(self.spiders_info):
      spider = ScrapyCrawler(sp_info, id, 
                             downloadFavicon=settings.DOWNLOAD_FAVICON.value(),
                             itemLoader=settings.get_item_loader_for(sp_info.spider_path[0]),
                             requestDelay=settings.SITE_PARAMS.by(sp_info.spider_path[0]).get("REQUEST_DELAY", 1))
      proj_settings = get_project_settings()
      crawler = Crawler(proj_settings)
      self.crawlers.append(crawler)
      # connect each spider's closed signal to self. When all spiders done, stop the reactor
      crawler.signals.connect(self.spider_closed, signal=signals.spider_closed) # i do not really now if that is appended or overwritten
      crawler.configure()
      crawler.crawl(spider)
      crawler.start()
    reactor.run()
    
  def stop_spider(self, spiderID):
    # can I stop a scrapy spider without stopping them all?
    # it seems scrapy spiders can't be stopped without stopping them all
    pass
  
  def spider_closed(self, spider):
    self.closed_spiders += 1
    if spider.event_handler: spider.event_handler.emit(SpiderClosed(spider.id))
    if self.closed_spiders == len(self.spiders_info):
      reactor.stop()
