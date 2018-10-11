"""
Wrapper for JSON settings
"""
import os
import json
import click

APP_NAME = 'Odoo Helper'

class Settings():
    """
    Settings wrapper
    """

    def __init__(self):
        self.config = {}

    def __enter__(self):
        try:
            config_file = os.environ.get(
                'ODOO_CONFIG',
                os.path.join(click.get_app_dir(APP_NAME), 'config.json')
            )
            with open(config_file, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:

            # Set default configs
            self.config = {

            }
        return self

    def __exit__(self, type, value, traceback):
        """ No save yet """
        pass

    def __getitem__(self, key):
        return self.config[key]

    def __setitem__(self, key, item):
        self.config[key] = item

    def __contains__(self, item):
        return item in self.config

    def save(self):
        """ Save new json """
                # Save new values
        config_file = os.environ.get(
            'ODOO_CONFIG',
            os.path.join(click.get_app_dir(APP_NAME), 'config.json')
        )
        # Try making dir if it does not exists
        os.makedirs(click.get_app_dir(APP_NAME), exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(self.config, f)

