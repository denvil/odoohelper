"""
All utils functions.
"""
import os
import datetime
import click
import keyring

from odoohelper.settings import Settings

def validate_odoo_date(ctx, param, value):
    if not value:
        # Empty date is fine
        return None
    try:
        date = datetime.datetime.strptime(value, '%Y-%m-%d')
        return date
    except ValueError:
        raise click.BadParameter(f'date needs to be in format YYYY-MM-DD')

def get_pass():
    """
    Get password from external source or return None for user prompt
    """
    import keyring
    pass_key = os.environ.get('ODOO_KEYRING_NAME', 'Odoo helper password')
    password = keyring.get_password("odoo-helper", pass_key)
    return password

def check_config():
    """
    Check that config is completed for required parts
    """
    required_keys = [
        'username',
        'host',
        'database'
    ]

    with Settings() as config:
        if all(key in config for key in required_keys):
            return True
        click.echo(click.style('Required configs missing. Please fill them now', fg='red'))
        host = input('Host: ')
        database = input('Database: ')
        username = input('Username: ')
        config['host'] = host
        config['database'] = database
        config['username'] = username
        config.save()
