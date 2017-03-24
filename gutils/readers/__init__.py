
import numpy as np
import logging

logger = logging.getLogger(__file__)

def stream_to_yo(stream, depthsensor, timesensor='timestamp'):
    """Create an Nx2 depth/pressure time series from the specified stream.  The
    depth/pressure sensor name (z_sensor) must be specified.  The default
    timestamp sensor name (t_sensor) is timestmap.
    """
     
    sensor_names = stream[0].keys()
    if depthsensor not in sensor_names:
        logger.error('z_sensor {:s} not found in stream rows'.format(depthsensor))
        return
        
    if timesensor not in sensor_names:
        logger.error('t_sensor {:s} not found in stream rows'.format(timesensor))
        return
        
    return np.asarray([[r[timesensor],r[depthsensor]] for r in stream])
    
def stream_to_profiles(timestamps, profile_times):
    
    profile_streams = []

    p_counter = 0
    for pt in profile_times:
        
        p0 = pt[0]
        p1 = pt[1]
        
        profile_inds = np.flatnonzero(np.logical_and(timestamps >= p0, timestamps <= p1))
        
        profile_stream = np.full((len(profile_inds),3), np.nan)
        
        profile_stream[:,0] = timestamps[profile_inds]
        profile_stream[:,2] = p_counter
        
        profile_streams.append(profile_stream)
        
        p_counter += 1
        
    return profile_streams
        