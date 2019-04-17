"""
Odoo client using Openerp proxy
"""
# https://pypi.org/project/openerp_proxy/
from openerp_proxy import Client as erpClient

class Client():
    """
    Odoo client
    """
    def __init__(self, username:str, password:str = '', database:str = '', host:str = '', port:int = 443, protocol:str = 'json-rpcs'):
        """
        Initialize parameters here
        """
        if len(username) == 0:
            raise ValueError('Missing username argument')
        self.username = username
        self.password = password
        self.database = database
        self.host = host
        self.port = port
        self.protocol = protocol
        self.client = None  # Set this in connect or enter
        self.user = None

    def connect(self):
        """
        Connect to Odoo
        """
        self.client = erpClient(
            host=self.host,
            dbname=self.database,
            user=self.username,
            pwd=self.password,
            protocol=self.protocol,
            port=self.port)
        # Check connection by fetching user name
        self.user = self.client.user


    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        pass

    def search(self, db_name, filters):
        """
        Search ids for db_name using filters
        """
        return self.client[db_name].search(filters)

    def search_read(self, db_name, filters):
        """
        Search data for db_name using filters
        """
        return self.client[db_name].search_read(filters)

    def read(self, db_name, ids, fields=None):
        """
        Read data using ids list or int. Fields is optional
        """
        return self.client[db_name].read(ids, fields)

    def write(self, db_name, ids, field):
        """
        Write data to db_name with id
        """
        return self.client[db_name].write(ids, field)
    
    def create(self, db_name, fields):
        return self.client[db_name].create(fields)