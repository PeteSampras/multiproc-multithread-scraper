#!/usr/bin/env python

import sys
import requests
from bs4 import BeautifulSoup
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
from multiprocessing import Process, Queue, current_process, Manager
import multiprocessing
import numpy as np


NUM_WORKERS = 4#multiprocessing.cpu_count()

# global variables
process_queue = Queue()
found_queue = Queue()
manager = Manager()
master_dict = manager.dict()


class MultiThreadScraper: # class does all processing

   def __init__(self, base_url,masterdict):
       self.base_url = base_url
       self.root_url = '{}://{}'.format(urlparse(self.base_url).scheme, urlparse(self.base_url).netloc)
       self.pool = ThreadPoolExecutor(max_workers=500) # was 50
       self.scraped_pages = set([])
       self.to_crawl = Queue()
       self.to_crawl.put(base_url)
       self.dict = masterdict

   def parse_links(self,html):
       soup = BeautifulSoup(html, 'html.parser')
       links = soup.find_all('a', href=True)
       for link in links:
           url = link['href']
           if url.startswith('//'):
               continue
           if url.startswith('/') or url.startswith(self.root_url):
               url = urljoin(self.root_url, url)
               if url not in self.scraped_pages:
                   self.to_crawl.put(url)
                   #print(url)
                   #found_queue.put(url)
                   self.dict.append(url)

   def scrape_info(self, html):
       return

   def post_scrape_callback(self, res):
       result = res.result()
       if result and result.status_code == 200:
           self.parse_links(result.text)
           self.scrape_info(result.text)

   def scrape_page(self, url):
       try:
           res = requests.get(url, timeout=(3, 10)) # was 30
           return res
       except requests.RequestException:
           return

   def run_scraper(self):
       while True:
           try:
               target_url = self.to_crawl.get(timeout=3) # was 60
               if target_url not in self.scraped_pages:
                   print("Scraping URL: {}".format(target_url))
                   self.scraped_pages.add(target_url)
                   job = self.pool.submit(self.scrape_page, target_url)
                   job.add_done_callback(self.post_scrape_callback)
           except Empty:
               return
           except Exception as e:
               print(e)
               continue

def get_listing(url):
    # headers = {
    #     'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36'}
    html = None
    links = url
    if url.startswith('/'):
        url = website+url
    r = requests.get(url, timeout=3)   # was 10      
    if r.status_code == 200:
        html = r.text
        soup = BeautifulSoup(html, 'html.parser')
        listing_section = soup.findAll('a', href=True)
        links = [link['href'].strip() for link in listing_section]
        return links

def parse(links,master):
    for link in links:
        if link == "''":
            pass
        if link.startswith('//'):
            pass
        if link.startswith('mailto:'):
            pass
        if not link.startswith('//'):
            if link != '/' and not link.startswith('#') and '/' in link:
                if website in link:
                    master.append(link)
                if 'http' in link.lower() or 'www' in link.lower():
                    pass
                else:
                    master.append(link)
            else:
                pass
        pass
    return master

def chunks(n, page_list):
    """Splits the list into n chunks"""
    return np.array_split(page_list,n)

def threader(urls,master):
    for url in urls:
        s = MultiThreadScraper(url,master)
        s.run_scraper()

if __name__ == '__main__':
    # set up first dict
    master_dict[0] = manager.list()

    # fake a website since this isnt a normal function yet
    website='https://www.facebook.com'


    #url_list = get_listing(website) # this would be useful if targeting a repository of links
    url_list=[]
    url_list.append(website)
    url_list = list(set(url_list))
    clean_url_list = parse(url_list,master_dict[0])

    # split urls up into chunks if more than one
    chunk = chunks(NUM_WORKERS,clean_url_list)
    procs = []

    # adjust actual size of processes if smaller to conserve cpu for threading
    size = NUM_WORKERS
    if len(clean_url_list) < NUM_WORKERS:
        size = len(clean_url_list)

    # create all processes
    for i in range(size):
        master_dict[i]=manager.list()
        print(chunk[i])
        p = Process(target=threader, args=(chunk[i],master_dict[i]))
        procs.append(p)
        p.start()

    # join all created processes    
    for p in procs:
        p.join()

    # 
    for i in range(size):
        master_dict[i]=list(set(master_dict[i]))
        print(len(master_dict[i]))
        for domain in master_dict[i]:
            print('Found: '+domain)
