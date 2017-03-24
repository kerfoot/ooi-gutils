
import json
import re
import requests
import logging
import os
import sys
import argparse
import tempfile
# Disables SSL warnings
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

# Create a session
async_session = requests.session()
    
def parse_response_nc_urls(response, timeout=30):
    
    nc_urls = []
    
    # Create the NetCDF filename template
    try:
        nc_template = 'deployment{:04.0f}_{:s}-{:s}-{:s}.*\.nc'.format(
            response['deployment_number'],
            response['instrument'],
            response['method'],
            response['stream'])
    except KeyError as e:
        logging.error('Invalid response')
        return nc_urls
        
    if 'response' not in response:
        logging.error('Invalid response')
        return nc_urls
        
    if 'allURLs' not in response['response']:
        logging.error('Invalid response')
        return nc_urls
        
    async_urls = [u for u in response['response']['allURLs'] if u.find('async_results') > -1]
    if len(async_urls) == 0:
        logging.warning('No async URL found')
        return nc_urls
    elif len(async_urls) != 1:
        logging.warning('Multiple async URLs found')
        return nc_urls
        
    async_url = async_urls[0]
    r = async_session.get(async_url)
    if not r.ok:
        logging.warning('Failed to retrieve async url {:s} ({:s})'.format(async_url, r.reason))
        return nc_urls
        
    # Create the regex
    url_regex = re.compile('href=\"({:s})\"'.format(nc_template))
    # Find matching urls
    urls = url_regex.findall(r.text)
    if not urls:
        logging.warning('No product NetCDF urls found in response')
        return nc_urls
        
    for url in urls:
        nc_urls.append('{:s}/{:s}'.format(async_url, url))
            
    return nc_urls
    
def download_nc(url, download_path=None, timeout=30):
    
    if not download_path:
        download_path = os.path.realpath(os.curdir)
    if not os.path.isdir(download_path):
        logging.error('Invalid download path specified {:s}'.format(download_path))
        return
        
    # Create the downloaded NetCDF file name
    url_tokens = url.split('/')
    nc_file = url_tokens[-1]
    if not nc_file.endswith('.nc'):
        logging.error('Invalid NetCDF name {:s} (Does not end with .nc)'.format(nc_file))
        return
        
    nc_path = os.path.join(download_path, nc_file)
    
    try:
        r = async_session.get(url, stream=True)
    except requests.exceptions.RequestException as e:
        logging.error('Request failed {:s} ({:s})'.format(url, e))
        return
        
    if not r.ok:
        logging.error('Request failed {:s} ({:s})'.format(url, e))
        return
        
    try:    
        with open(nc_path, 'wb') as fid:
            for chunk in r.iter_content(chunk_size=1024):
                fid.write(chunk)
                fid.flush()
    except IOError as e:
        sys.stderr.write('{:s} (Query produced no matching rows?)\n'.format(e))
        r.close()
        return
        
    return nc_path
    
#def download_ascii_file(url, download_path=None):
#    
#    if not download_path:
#        download_path = os.path.realpath(os.path.curdir)
        
    
    