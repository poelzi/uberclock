import datetime

def time_to_next_datetime(time, dt=None):
    """
    Returns the next valid datetime object for a given
    datetime.time object
    """
    if not dt:
        dt = datetime.datetime.now()
    
    res = datetime.datetime.combine(dt.date(), time)
    if res < datetime.datetime.now():
        res = res + datetime.timedelta(days=1)
    return res

