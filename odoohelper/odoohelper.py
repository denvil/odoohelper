#!/usr/bin/env python3
"""
CLI for ODOO. This will automate some tasks and jobs that
are too time consuming to workout in ODOO.
"""
import os
import sys
import json
import click
from pyfiglet import figlet_format

from odoohelper.client import Client
from odoohelper.tasks import Task
from odoohelper.interactive import as_interactive
try:
    with open(os.environ.get('ODOO_CONFIG', 'config.json'), 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    # Set default configs
    config = {

    }



try:
    from termcolor import colored
except ImportError:
    def colored(string, _):
        return string


def log(string: str, color: str, font="slant", figlet=False, output=True):
    """
    Log using colors and figlet if needed.
    Output True equalst stdout and False if stderr
    """
    if not output:
        out = sys.stderr
    else:
        out = sys.stdout
    if not figlet:
        print(colored(string, color), file=out)
    else:
        print(colored(figlet_format(string, font), color), file=out)

def check_config():
    """
    Check that config is completed for required parts
    """
    required_keys = [
        'username',
        'host',
        'database'
    ]
    if all(key in config for key in required_keys):
        return True
    log('Required configs missing. Please fill them now', 'red')
    host = input('Host: ')
    database = input('Database: ')
    username = input('Username: ')
    config['host'] = host
    config['database'] = database
    config['username'] = username

    # Save new values
    with open(os.environ.get('ODOO_CONFIG', 'config.json'), 'w') as f:
        json.dump(config, f)

def get_pass():
    """
    Get password from external source or return '' for user prompt
    """
    return ''

@click.group()
def main():
    """
    ODOO CLI helper for common tasks.
    """
    pass

@main.command()
@click.password_option(default=get_pass(), confirmation_prompt=False)
@click.option('-u','--user', metavar='<user full name>', help="User display name in Odoo")
@click.option('-i','--interactive', help="Ask what you want to do on each task", is_flag=True)
def tasks(password, user, interactive):
    """Return tasks in priority order.

    Default is to find your tasks. This can also be used
    to fetch tasks by user.
    """
    check_config()
    client = Client(username=config['username'], password=password, database=config['database'], host=config['host'])
    client.connect()
    log('Fetching tasks from ODOO... This may take a while.', 'blue')
    if not user:
        user_id = client.user.id
    filters = [
        ('user_id', '=', user_id),
        ('stage_id', '!=', 8)  # This is done stage. Should be in config?
    ]
    all_tasks = Task.fetch_tasks(client, filters)
    all_sorted = sorted(all_tasks, key=lambda x: x.priority, reverse=True)
    if not interactive:
        log(Task.print_topic(), 'blue')
    for task in all_sorted:
        if not interactive:
            log(task, 'yellow')
        else:
            as_interactive(client, task)



if __name__ == '__main__':
    main()