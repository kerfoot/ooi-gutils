
class Args(object):
    
    def __init__(self, base_url=None, debug=False, instruments=['CTDGVM000'], loglevel='info', root=None, status='active', timeout=30):
        """Class used to simulate an args object resulting from the argparse:parse_args method
        Used for debugging __main__ scripts written using argparse"""
        
        self._base_url = base_url
        self._loglevel = loglevel
        self._status = status
        self._debug = debug
        self._timeout = 30
        self._root = root
        self._instruments = instruments
        self._response_file = None
        self._glider_config_path = None
        self._user = 'rutgers'
        self._password = '1ioo$man9'
        self._host = 'data.ioos.us'
        self._deployment_nc_path = None
        self._timestamping = True
        
    @property
    def timestamping(self):
        return self._timestamping
    @timestamping.setter
    def timestamping(self, bool):
        if type(bool) != bool:
           return
        self._timestamps = bool
        
    @property
    def deployment_nc_path(self):
        return self._deployment_nc_path
    @deployment_nc_path.setter
    def deployment_nc_path(self, path):
        self._deployment_nc_path = path
        
    @property
    def glider_deployment_path(self):
        return self._glider_config_path
    @glider_deployment_path.setter
    def glider_deployment_path(self, path):
        self._glider_config_path = path
         
    @property
    def user(self):
        return self._user
    @user.setter
    def user(self, user):
        self._user = user
        
    @property
    def password(self):
        return self._password
    @password.setter
    def password(self, pw):
        self._password = pw
        
    @property
    def host(self):
        return self._host
    @host.setter
    def host(self, host):
        self._host = host
        
    @property
    def glider_config_path(self):
        return self._glider_config_path
    @glider_config_path.setter
    def glider_config_path(self, glider_config_path):
        self._glider_config_path = glider_config_path

    @property
    def response_file(self):
        return self._response_file
        
    @response_file.setter
    def response_file(self, response_file):
        self._response_file = response_file
        
    @property
    def instruments(self):
        return self._instruments
    @instruments.setter
    def instruments(self, instruments):
        if type(instruments) == str:
            self._instruments = [instruments]
        elif type(instruments) == list:
            self._instruments = instruments

    @property
    def root(self):
        return self._root
    @root.setter
    def root(self, directory):
        self._root = directory

    @property
    def base_url(self):
        return self._base_url
    @base_url.setter
    def base_url(self, base_url):
        self._base_url = base_url
        
    @property
    def loglevel(self):
        return self._loglevel
    @loglevel.setter
    def loglevel(self, loglevel):
        self._loglevel = loglevel
        
    @property
    def status(self):
        return self._status
    @status.setter
    def status(self, status):
        self._status = status
        
    @property
    def debug(self):
        return self._debug
    @debug.setter
    def debug(self, debug):
        self._debug = debug
        
    @property
    def timeout(self):
        return self._timeout
    @timeout.setter
    def timeout(self, timeout):
        self._timeout = timeout
    
        
    def __repr__(self):
        return '<argparse:args dummy instance>'
