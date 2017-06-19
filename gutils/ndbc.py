
def check_gts_bin_count(max_depth, bin_count):
    """Returns True if the profile bin_count meets the NDBC minimum required
    number of records.  These values are based on the maximum profile depth
    """
    
    if max_depth <= 15:
        if bin_count < 5:
            return False
    elif max_depth <= 50:
        if bin_count < 10:
            return False
    elif max_depth <= 100:
        if bin_count < 10:
            return False
    elif max_depth <= 200:
        if bin_count < 20:
            return False
    elif bin_count < 25:
        return False
        
    return True
    
def calculate_profile_resolution(min_depth, max_depth, num_records):
    
    return (max_depth - min_depth)/num_records
    