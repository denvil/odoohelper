#!/usr/bin/env python3
"""
CLI for ODOO. This will automate some tasks and jobs that
are too time consuming to workout in ODOO.
"""
import os
import sys
import json
import click
import keyring

from odoohelper.client import Client
from odoohelper.tasks import Task
from odoohelper.interactive import as_interactive
from odoohelper.settings import Settings

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


def get_pass():
    """
    Get password from external source or return None for user prompt
    """
    import keyring
    pass_key = os.environ.get('ODOO_KEYRING_NAME', 'Odoo helper password')
    password = keyring.get_password("odoo-helper", pass_key)
    return password

@click.group()
def main():
    """
    ODOO CLI helper for common tasks.
    """
    pass

@main.command()
@click.password_option(prompt=True if get_pass() is None else False, confirmation_prompt=False)
@click.option('-u','--user', metavar='<user full name>', help="User display name in Odoo")
@click.option('-i','--interactive', help="Ask what you want to do on each task", is_flag=True)
def tasks(password, user, interactive):
    """Return tasks in priority order.

    Default is to find your tasks. This can also be used
    to fetch tasks by user.
    """
    if password is None:
        password = get_pass()
    check_config()
    with Settings() as config:
        client = Client(username=config['username'], password=password, database=config['database'], host=config['host'])

    client.connect()
    click.echo('Fetching tasks from ODOO... This may take a while.', file=sys.stderr)
    if not user:
        user_id = client.user.id
    filters = [
        ('user_id', '=', user_id),
        ('stage_id', '!=', 8)  # This is done stage. Should be in config?
    ]
    all_tasks = Task.fetch_tasks(client, filters)
    all_sorted = sorted(all_tasks, key=lambda x: x.priority, reverse=True)
    if not interactive:
        click.echo(Task.print_topic())
        for task in all_sorted:
            click.echo(task)
    else:
        current_index = 0
        # Loop with index as interactive can go both ways
        while True:
            task = all_sorted[current_index]
            index_mod = as_interactive(
                client=client,
                task=task,
                task_count=len(all_sorted),
                current_index=current_index)
            new_index = current_index + index_mod

            current_index = new_index
            if current_index >= len(all_sorted):
                current_index = 0
            if current_index < 0:
                current_index = len(all_sorted) - 1



if __name__ == '__main__':
    main()