
import numpy as np
import os
import logging

logger = logging.getLogger(os.path.basename(__file__))

DBA_TIMESENSORS = ['m_present_time',
    'sci_m_present_time',
    'sci_ctd41cp_timestamp']
    
def dba_to_stream(dbd, timesensor=None):
    """Parse a Slocum glider ascii dba file and return a dictionary containing 
    the dbd file metadata and the data stream.  The
    data stream is an array in which each element is a dictionary mapping the 
    sensor name to the sensor value for each row contained in the dbd file.
    """
    
    dbd_data = {'meta' : {}, 'stream' : []}
    if not os.path.isfile(dbd):
        logger.error('File does not exist {:s}'.format(dbd))
        return
        
    with open(dbd, 'r') as fid:
        
        skiprows = 0
        header = {}
        for line in fid:
            
            tokens = line.strip().split(': ')
            if len(tokens) == 1:
                break
                
            if tokens[0] == 'num_ascii_tags' or tokens[0] == 'num_label_lines':
                skiprows += int(tokens[1])
                
            header[tokens[0]] = tokens[1]
        
        # First line after the for break is the list of sensors
        sensor_names = line.split()
        # Next line is the units
        sensor_units = fid.next().split()
        # Next line is number of bytes
        sensor_bytes = fid.next().split()
        
    # If no timesensor specified, find the first one in DBA_TIMESENSORS
    if not timesensor:
        for s in DBA_TIMESENSORS:
            if s in sensor_names:
                timesensor = s
                break
        
    # Load the data into a numpy array
    data = np.loadtxt(dbd, skiprows=skiprows)
    if not len(data):
        logger.warning('No data rows found {:s}'.format(dbd))
        return
        
    stream = []
    col_range = range(len(sensor_names))
    for d in data:
        
        row = {sensor_names[c]:d[c] for c in col_range}
        row['timestamp'] = row[timesensor]
        
        dbd_data['stream'].append(row)
        
    # Make sure timesensor is in sensor_names
    if not timesensor:
        logger.error('No master time sensor name found {:s}'.format(dbd))
        return
    elif timesensor not in sensor_names:
        logger.error('Master time sensor {:s} not found {:s}'.format(dbd, timesensor))
        return
        
    # Add the file metadata
    dbd_data['meta']['header'] = header
    dbd_data['meta']['sensor_names'] = sensor_names
    dbd_data['meta']['sensor_units'] = sensor_units
    dbd_data['meta']['sensor_bytes'] = sensor_bytes
    
    return dbd_data
    
