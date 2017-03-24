
import logging
import requests
import json
import os
from netCDF4 import Dataset

logger = logging.getLogger(os.path.basename(__file__))

def fetch_glider_datasets(erddap_base_url, timeout=30, verify=True):
    """Fetch the ERDDAP metadata records for all glider datasets at the erddap_base_url
    """
    
    query = 'search/advanced.json?page=1&itemsPerPage=1000&searchFor=MOAS&protocol=tabledap&cdm_data_type=trajectory&institution=ocean_observatories_initiative'
    
    url = '{:s}/{:s}'.format(erddap_base_url.strip('/'), query.strip())
    
    try:
        r = requests.get(url, timeout=timeout, verify=verify)
    except requests.exceptions.RequestException as e:
        logger.error('Request failed - {:s}'.format(e))
        return
        
    if not r.ok:
        logger.warning('{:s}'.format(r.message))
        return
        
    try:
        response = r.json()
    except ValueError as e:
        logger.error('{:s}'.format(e))
        return
        
    datasets = []
    
    col_count = range(len(response['table']['columnNames']))   
    # Create a list of dicts containing each dataset
    for row in response['table']['rows']:
        
        dataset = {response['table']['columnNames'][x]: row[x] for x in col_count}
        if dataset['Dataset ID'] == u'allDatasets':
            continue
            
        datasets.append(dataset)
        
    return datasets
    
def fetch_erddap_stream_data(dataset_url, variables=[], start_ts=None, end_ts=None):
    
    return