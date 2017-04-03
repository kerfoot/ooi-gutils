
import os
import json
import logging
import glob
import datetime
from netCDF4 import Dataset
from dateutil import parser
import numpy as np

logger = logging.getLogger(os.path.basename(__file__))

GLIDER_INSTRUMENT_TYPES = ['CTDGVM000',
    'DOSTAM000',
    'NUTNRM000',
    'PARADM000']
    
GLIDER_TELEMETRY_TYPES = {'active' : 'telemetered',
    'inactive' : 'recovered_host'}
    
GLIDER_INSTRUMENT_STREAMS = {
    u'active' : {
        u'CTDGVM000': {
            u'method': u'telemetered',
            u'stream': u'ctdgv_m_glider_instrument'},
        u'DOSTAM000': {
            u'method': u'telemetered',
            u'stream': u'dosta_abcdjm_glider_instrument'},
        u'FLORTM000': {
            u'method': u'telemetered',
            u'stream': u'flort_m_glider_instrument'},
        u'PARADM000': {
            u'method': u'telemetered',
            u'stream': u'parad_m_glider_instrument'}
    },
    u'inactive' : {
        u'CTDGVM000': {
            u'method': u'recovered_host',
            u'stream': u'ctdgv_m_glider_instrument_recovered'},
        u'DOSTAM000': {
            u'method': u'recovered_host',
            u'stream': u'dosta_abcdjm_glider_recovered'},
        u'FLORTM000': {
            u'method': u'recovered_host',
            u'stream': u'flort_m_glider_recovered'},
        u'PARADM000': {
            u'method': u'recovered_host',
            u'stream': u'parad_m_glider_recovered'}
    }
}

    
def build_trajectory_name(json_file):

    if not os.path.isfile(json_file):
        logger.error('Deployment JSON file does not exist {:s}'.format(json_file))
        return

    try:
        with open(json_file, 'r') as fid:
            deployment_info = json.load(fid)
    except (OSError, ValueError) as e:
        logger.error('Error opening {:s} ({:s})'.format(json_file, e))
        return

    if 'glider' not in deployment_info:
        logger.warning('glider missing from deployment info {:s}'.format(json_file))
        return
    elif 'trajectory_date' not in deployment_info:
        logger.warning('trajectory_date missing from deployment info {:s}'.format(json_file))
        return

    try:
        dt = parser.parse(deployment_info['trajectory_date'])
    except ValueError as e:
        logger.error('Error creating trajectory {:s}'.format(json_file))
        return

    return '{:s}-{:s}'.format(deployment_info['glider'], dt.strftime('%Y%m%dT%H%M'))

def write_dataset_status_file(deployment_path, clobber=False,destination=None):
    
    if not os.path.isdir(deployment_path):
        logger.error('Invalid deployment path {:s}'.format(deployment_path))
        return
        
    status_path = destination or os.path.join(deployment_path, 'status')
    if not os.path.isdir(status_path):
        logger.error('Invalid deployment status path {:s}'.format(status_path))
        return
        
    cfg_path = os.path.join(deployment_path, 'cfg')
    if not os.path.isdir(cfg_path):
        logger.error('Invalid deployment configuration path {:s}'.format(cfg_path))
        return
        
    # Read in the deployment.json file
    deployment_cfg = os.path.join(cfg_path, 'deployment.json')
    if not os.path.isfile(deployment_cfg):
        logger.error('Deployment configuration does not exit {:s}'.format(deployment_cfg))
        return
        
    try:
        with open(deployment_cfg, 'r') as fid:
            cfg = json.load(fid)
    except OSError as e:
        logger.error('Error reading deployment configuration {:s} ({:s})'.format(deployment_cfg, e))
        return
        
    trajectory = build_trajectory_name(deployment_cfg)
    if not trajectory:
        return
        
    # Name of profile status file
    profile_status_file = os.path.join(status_path, '{:s}-profiles.json'.format(trajectory))
    profile_status = []
    if not clobber and os.path.isfile(profile_status_file):
        try:
            with open(profile_status_file, 'r') as fid:
                profile_status = json.load(fid)
        except IOError as e:
            logger.error('Erroring reading profile status file {:s}'.format(profile_status_file))
            return
    seen_nc_files = [os.path.basename(s['filename']) for s in profile_status]
        
    # NetCDF directories
    nc_queue_dir = os.path.join(deployment_path, trajectory)
    nc_archive_dir = os.path.join(deployment_path, 'nc-archive')
    if not os.path.isdir(nc_archive_dir):
        logger.error('NetCDF archive directory does not exist {:s}'.format(nc_archive_dir))
        return
        
    nc_files = glob.glob(os.path.join(nc_archive_dir, '*.nc'))
    if os.path.isdir(nc_queue_dir):
        nc_files = nc_files + glob.glob(os.path.join(nc_queue_dir, '*.nc'))
        
    
    # Add new files
    for nc_file in nc_files:
        
        if not os.path.isfile(nc_file):
            logger.warning('NetCDF file does not exist {:s}'.format(nc_file))
            continue
        if os.path.basename(nc_file) in seen_nc_files:
            continue
            
        try:
            with Dataset(nc_file, 'r') as nci:
                profile_time = np.asscalar(nci.variables['profile_time'][-1])
                try:
                    profile_time_dt = datetime.datetime.utcfromtimestamp(profile_time)
                except ValueError as e:
                    logging.error(e)
                    continue
                profile_max_time = np.asscalar(np.max(nci.variables['time']))
                try:
                    profile_max_time_dt = datetime.datetime.utcfromtimestamp(profile_max_time)
                except ValueError as e:
                    logging.error(e)
                    continue
                    
                # Create the depth time-series, store the min depth, max depth and
                # number of non-Nan records
                yo = np.column_stack((nci.variables['time'], nci.variables['depth']))
                yo = yo[np.all(~np.isnan(yo),axis=1)]
                num_records = len(yo)
                if num_records == 0:
                    logger.warning('Profile has 0 non-NaN time/depth records {:s}'.format(nc_file))
                    min_depth = None
                    max_depth = None
                else:
                    min_depth = np.min(yo[:,1])
                    max_depth = np.max(yo[:,1])
                    
                profile = {'profile_id' : np.asscalar(nci.variables['profile_id'][-1]),
                    'profile_time' : profile_time,
                    'profile_time_str' : profile_time_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                    'profile_max_time' : profile_max_time,
                    'profile_max_time_str' : profile_max_time_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                    'filename' : nc_file,
                    'min_depth' : min_depth,
                    'max_depth' : max_depth,
                    'num_records' : num_records}
                profile_status.append(profile)
        except IOError as e:
            logger.error('Erroring reading {:s} ({:s})'.format(nc_file, e))
            continue
            
    with open(profile_status_file, 'w') as fid:
        json.dump(profile_status, fid, indent=4)
        
    return profile_status_file
        
    
        
    