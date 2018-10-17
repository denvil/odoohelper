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


@main.command()
@click.password_option(prompt=True if get_pass() is None else False, confirmation_prompt=False)
@click.option('-u','--user', metavar='<user full name>', help="User display name in Odoo")
def attendance(password, user):
    """
    Retrieves timesheet and totals it for the current month.
    """
    from datetime import datetime
    import pytz

    def colored_diff(title, diff, invert=False):
        color = 'magenta' if diff[0] == '-' and not invert else 'green'
        click.echo(
            click.style(f'{title}\t', fg='blue') +
            click.style(diff, fg=color)
        )

    if password is None:
        password = get_pass()
    check_config()
    with Settings() as config:
        client = Client(username=config['username'], password=password, database=config['database'], host=config['host'])
    client.connect()
    if not user:
        user_id = client.user.id
    filters = [
        ('employee_id.user_id.id', '=', user_id),
        ('check_in', '>=', datetime.now().strftime('%Y-%m-01 00:00:00'))
    ]
    attendance_ids = client.search('hr.attendance', filters)
    attendances = client.read('hr.attendance', attendance_ids)

    days = {}

    for attendance in attendances:
        date = pytz.timezone('Europe/Helsinki').localize(
            datetime.strptime(attendance['check_in'], '%Y-%m-%d %H:%M:%S'))
        now = pytz.timezone('Europe/Helsinki').localize(
            datetime.utcnow())
        if attendance['check_out'] == False:
            attendance['worked_hours'] = (now - date).seconds / 3600
        # Key = %Y-%m-%d
        key = date.strftime('%Y-%m-%d')
        try:
            days[key]['worked_hours'] += attendance['worked_hours']
        except KeyError:
            if date.weekday() in [5, 6]:  # Sat, Sun off
                allocated_hours = 0.0
            else:
                allocated_hours = 7.5
            days[key] = {
                'worked_hours': 0,
                'allocated_hours': allocated_hours
            }
            days[key]['worked_hours'] += attendance['worked_hours']
    
    total_diff = 0
    total_hours = 0
    day_diff = 0
    click.echo(click.style(f'Balance as of {(datetime.today().isoformat(timespec="seconds"))} (system time)', fg='blue'))
    click.echo(click.style('Day\t\tWorked\tDifference', fg='blue'))
    for key, day in sorted(days.items()):
        diff = day['worked_hours'] - day['allocated_hours']
        colored_diff(f'{key}\t{(day["worked_hours"]):.2f}', f'{diff:+.2f}')

        if key == datetime.today().strftime('%Y-%m-%d'):
            day_diff += day['worked_hours'] - day['allocated_hours']
        else:
            total_diff += day['worked_hours'] - day['allocated_hours']
        total_hours += day['worked_hours']

    today = datetime.now().strftime('%Y-%m-%d')
    hours_today = 0
    allocated_today = 0
    if today in days:
        hours_today = days[today]['worked_hours']
        allocated_today = days[today]['allocated_hours']

    click.echo(click.style('---\t\t------\t-----', fg='blue'))
    colored_diff(f'Totals:\t\t{total_hours:.2f}', f'{(total_diff + day_diff):+.2f}')
    print()
    colored_diff('Balance yesterday:', f'{total_diff:+.2f}')
    colored_diff('Balance now:\t', f'{(total_diff + day_diff):+.2f}')
    colored_diff(
        'Allocated hours today:', f'{(allocated_today - hours_today):+.2f}', invert=True)

if __name__ == '__main__':
    main()
