#!/usr/bin/env python

import logging
import argparse
import os
import shutil
import sys
import json
from m2m.UFrameClient import UFrameClient
from ooidac import GLIDER_TELEMETRY_TYPES

def main(args):
    """Initialize new OOI glider deployments for creation of U.S. IOOS Glider Data
    Assembly Center NetCDF file creation by querying OOI UFrame asset management."""
    
    exit_status = 0
    
    # Configure logging
    log_level = getattr(logging, args.loglevel.upper())
    log_format = '%(module)s:[line %(lineno)d]:%(levelname)s:%(message)s'
    logging.basicConfig(format=log_format, level=log_level)
    
    # Deployments home directory
    deployments_root = args.root or os.getenv('OOI_GLIDER_DAC_HOME')
    logging.info('Deployments root {:s}'.format(deployments_root))
    if not deployments_root:
        logging.error('No deployments root specified (OOI_GLIDER_DAC_HOME not set?)')
        return 1
    if not os.path.isdir(deployments_root):
        logging.error('Invalid deployments root {:s}'.format(deployments_root))
        return 1
    # Master configuration directory
    script_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    master_cfg_dir = os.path.join(script_dir, 'resources', 'deployment-master')
    logging.info('Master configuration dir {:s}'.format(master_cfg_dir))
    if not os.path.isdir(master_cfg_dir):
        logging.error('Invalid master configuration directory {:s}'.format(master_cfg_dir))
        return 1
    # Deployment directories home
    deployments_home = os.path.join(deployments_root, 'deployments')
    logging.info('Deployments home {:s}'.format(deployments_home))
    if not os.path.isdir(deployments_home):
        logging.error('Invalid deployments home {:s}'.format(deployments_home))
        return 1
    # Array specific attributes directory
    array_attrs_dir = os.path.join(script_dir, 'resources', 'arrays')
    logging.info('Array-specific attributes dir {:s}'.format(array_attrs_dir))
        
    # UFrame instance
    uframe_base_url = args.base_url or os.getenv('UFRAME_BASE_URL')
    if not uframe_base_url:
        logging.error('No base_url set/found')
        return 1

    # Create the m2m UFrame client instance
    client = UFrameClient(uframe_base_url, timeout=args.timeout, m2m=True)
    
    # Fetch all MOAS instruments
    instruments = client.search_instruments('MOAS')
    if not instruments:
        logging.warning('No MOAS instruments found {:s}'.format(client.base_url))
        return 1
    gliders = list(set('-'.join(i.split('-')[:2]) for i in instruments))
    gliders.sort()
        
    seen_deployments = []
    for glider in gliders:
        
        # First 2 letters are the OOI array identifier
        array = glider[:2]
        # Check for the array-specific global attributes json file
        global_attrs_file = os.path.join(array_attrs_dir, '{:s}-global_attributes.json'.format(array))
            
        # Fetch all deployments of this instrument
        logging.debug('Finding {:s} {:s} deployments'.format(glider, args.status))
        instrument_deployments = client.fetch_instrument_deployments(glider)
        if not instrument_deployments:
            logging.debug('No deployments found for {:s}'.format(glider))
            continue
        # Filter deployments by status type
        status_deployments = client.filter_deployments_by_status(instrument_deployments, status=args.status)
        if not status_deployments:
            logging.debug('No {:s} deployments for {:s}'.format(args.status, glider))
            continue
    
        for deployment in status_deployments:
            
            glider = '-'.join(deployment['referenceDesignator'].split('-')[:2])
            deployment_dir = '{:s}-deployment{:04.0f}-{:s}'.format(glider, deployment['deploymentNumber'], GLIDER_TELEMETRY_TYPES[args.status])
            logging.debug('Checking deployment {:s}'.format(deployment_dir))
            deployment_path = os.path.join(deployments_home, deployment_dir)
            
            if deployment_dir in seen_deployments:
                continue
            seen_deployments.append(deployment_dir)
            if os.path.isdir(deployment_path):
                continue
                
            logging.info('New deployment {:s}'.format(deployment_dir))
            if not os.path.isfile(global_attrs_file):
                logging.warning('Skipping configuration {:s} (Missing array global attributes file {:s})'.format(glider, global_attrs_file))
                continue
            
            if args.debug:
                continue
                
            logging.info('Configuring new deployment {:s}'.format(deployment_path))
            try:
                # Copy the deployment-master template folder
                shutil.copytree(master_cfg_dir, deployment_path)
                # Copy the global_attrs_file to the deployment/cfg directory
                dest_path = os.path.join(deployment_path, 'cfg', 'global_attributes.json.new')
                shutil.copyfile(global_attrs_file, dest_path)
                # Write the deployment events to a json file
                deployment_events = [d for d in status_deployments if d['referenceDesignator'].startswith(glider)]
                events_json_file = os.path.join(deployment_path, '{:s}.json'.format(deployment_dir))
                try:
                    with open(events_json_file, 'w') as fid:
                        json.dump(deployment_events, fid, indent=4)
                except OSError as e:
                    logging.error('Failed to write deployment json {:s}'.format(events_json_file))
                    continue
                    
            except OSError as e:
                logging.error('Error creating directory {:s} ({:s})'.format(deployment_path, e))
                exit_status = 1
                continue
        
    return exit_status
    
if __name__ == '__main__':

    arg_parser = argparse.ArgumentParser(description=main.__doc__)
    arg_parser.add_argument('-r', '--root',
        help='Root directory containing the OOI glider deployment folders and master configurations.  Taken from OOI_GLIDER_DAC_HOME if not specified')
    arg_parser.add_argument('-s', '--status',
        dest='status',
        type=str,
        default='active',
        choices=['active', 'inactive'],
        help='Specify the status of the deployment <Default=active>')
    arg_parser.add_argument('-b', '--baseurl',
        dest='base_url',
        type=str,
        help='UFrame m2m base url beginning with https.  Taken from UFRAME_BASE_URL if not specified')
    arg_parser.add_argument('-l', '--loglevel',
        help='Verbosity level <Default=info>',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default='info')
    arg_parser.add_argument('-x', '--debug',
        help='Print new deployments but do not perform any intitialization',
        action='store_true')
    arg_parser.add_argument('-t', '--timeout',
        type=int,
        default=30,
        help='Request timeout, in seconds <Default=30>')

    parsed_args = arg_parser.parse_args()

    sys.exit(main(parsed_args))
