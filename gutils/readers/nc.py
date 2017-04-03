
import logging
import os
import numpy as np
from seawater.eos80 import dpth
from netCDF4 import Dataset, num2date, date2num

logger = logging.getLogger(os.path.basename(__file__))

#M2M_REQUIRED_PARAMETERS = [u'sci_water_cond',
#    u'deployment',
#    u'sci_water_pracsal',
#    u'driver_timestamp',
#    u'sci_water_pressure_dbar',
#    u'lon',
#    u'internal_timestamp',
#    u'm_present_secs_into_mission',
#    u'm_present_time',
#    u'ingestion_timestamp',
#    u'port_timestamp',
#    u'sci_water_pressure',
#    u'sci_seawater_density',
#    u'sci_m_present_time',
#    u'lat',
#    u'sci_ctd41cp_timestamp',
#    u'sci_m_present_secs_into_mission',
#    u'sci_water_temp',
#    u'time']
M2M_REQUIRED_PARAMETERS = [u'sci_water_cond',
    u'deployment',
    u'practical_salinity',
    u'sci_water_pressure_dbar',
    u'lon',
    u'sci_water_pressure',
    u'sci_seawater_density',
    u'lat',
    u'sci_water_temp',
    u'time']

def m2m_nc_to_gutils_stream(nc_file):
    """Parse a NetCDF file created via a UFrame m2m asynchronous request and
    return a dictionary containing sensor metadata and the data stream.  The
    data stream is an array in which each element is a dictionary mapping the 
    sensor name to the sensor value for each observation contained in the NetCDF
    file.
    """
    
    dataset = {'meta' : {}, 'stream' : []}
    
    nci = Dataset(nc_file, 'r')
    
    num_obs = nci.dimensions['obs'].size
    
    # Get NetCDF variables that have only obs as the dimension
    obs_vars = [k for k in nci.variables.keys() if len(nci.variables[k].dimensions) == 1 and nci.variables[k].dimensions[0] == 'obs']
        
    if not obs_vars:
        return
        
    # Get the units for each of obs_vars
    obs_units = []
    for v in obs_vars:
        if 'units' not in nci.variables[v].ncattrs():
            obs_units.append(None)
            continue
        obs_units.append(nci.variables[v].getncattr('units'))
        
    # Make sure all required parameters are present
    has_required = True
    for v in M2M_REQUIRED_PARAMETERS:
        if v not in obs_vars:
            logger.warning('Missing required parameter {:s} - {:s}'.format(v, nc_file))
            has_required = False
            
    if not has_required:
        return
        
    for r in range(num_obs):
        
        # Create the dict
        row = {k:np.asscalar(nci.variables[k][r]) for k in obs_vars}
        # Add dummy current values
        row['time_uv'] = None
        row['lat_uv'] = None
        row['lon_uv'] = None
        row['m_water_vx'] = None
        row['m_water_vy'] = None
        
        # Convert time from native units (seconds since 1900-01-01) to unix time
        dt = num2date(row['time'], units=nci.variables['time'].units, calendar=nci.variables['time'].calendar)
        row[u'timestamp'] = date2num(dt, units='seconds since 1970-01-01 00:00:00', calendar='gregorian')
        #row['lat'] = np.asscalar(row['lat'])
        #row['lon'] = np.asscalar(row['lon'])
        # Calculate depth from pressure and latitude
        row[u'eos80_depth'] = dpth(row['sci_water_pressure_dbar'], row['lat'])
        
        dataset['stream'].append(row)
        
    # Add derived sensors
    obs_vars.append(u'timestamp')
    obs_vars.append(u'eos80_depth')
    # Add derived sensor units
    obs_units.append(u'seconds since 1970-01-01 00:00:00Z')
    obs_units.append(u'meters')
    
    dataset['meta']['sensor_names'] = obs_vars
    dataset['meta']['sensor_units'] = obs_units
        
    return dataset
    
def erddap_nc_to_gutils_stream(nc_file):
    
    dataset = []
    
    return dataset
