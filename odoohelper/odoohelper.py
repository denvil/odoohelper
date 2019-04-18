#!/usr/bin/env python3
"""
CLI for ODOO. This will automate some tasks and jobs that
are too time consuming to workout in ODOO.
"""
import datetime
import json
import os
import sys

import click
import keyring

from odoohelper.client import Client
from odoohelper.projects import project_group
from odoohelper.settings import Settings
from odoohelper.tasks import Task, tasks_group
from odoohelper.utils import (check_config, get_pass, set_pass,
                              validate_odoo_date)


@click.group()
def settings_group():
    pass

@settings_group.command()
@click.password_option(prompt=True, confirmation_prompt=True)
def set_password(password):
    """ Set password to keyring """
    set_pass(password)
    click.echo('Password set')

@click.group()
def attendance_group():
    # Collection for attendance commands
    pass

@attendance_group.command()
@click.password_option(prompt=True if get_pass() is None else False, confirmation_prompt=False)
@click.option('-u','--user', metavar='<user full name>', help="User display name in Odoo")
@click.option('--month', 'period', flag_value='month', default=True, help="Show records since start of current month")
@click.option('--year', 'period', flag_value='year', help="Show records since start of current year")
@click.option('--start', metavar='<start date>', callback=validate_odoo_date, help="Show records since date")
@click.option('--end', metavar='<end date>', callback=validate_odoo_date, help="Show records up to date")
def attendance(password, user, period, start=None, end=None):
    """
    Retrieves timesheet and totals it for the current month.
    """
    from datetime import datetime
    import pytz
    import holidays

    def colored_diff(title, diff, notes=None,  invert=False):
        positive_color = 'green'
        negative_color = 'magenta'
        if invert:
            positive_color = 'magenta'
            negative_color = 'green'

        if not notes:
            notes = ''
        else:
            notes = f' ! {notes}'

        color = negative_color if diff[0] == '-' else positive_color
        click.echo(
            click.style(f'{title}\t', fg='blue') +
            click.style(diff, fg=color) +
            click.style(notes, fg='magenta')
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
        ('employee_id.user_id.id', '=', user_id)
    ]

    # Add the start filter
    if start:
        filters.append(('check_in', '>=', start.strftime('%Y-%m-%d 00:00:00')))
    elif period == 'month':
        filters.append(('check_in', '>=', datetime.now().strftime('%Y-%m-01 00:00:00')))
    elif period == 'year':
        filters.append(('check_in', '>=', datetime.now().strftime('%Y-01-01 00:00:00')))

    # Add optional end filter
    if end:
        filters.append(('check_out', '<', end.strftime('%Y-%m-%d 00:00:00')))

    attendance_ids = client.search('hr.attendance', filters)
    attendances = client.read('hr.attendance', attendance_ids)

    weeks = {}
    # @TODO Assumes user is in Finland
    local_holidays = holidays.FI()

    # Faux data to test holidays
    # attendances.append({
    #     'check_in': '2018-01-01 00:00:00',
    #     'check_out': '2018-01-01 02:00:00',
    #     'worked_hours': 2
    # })

    for attendance in attendances:
        # Get a localized datetime object
        # @TODO This assumes the server returns times as EU/Helsinki
        date = pytz.timezone('Europe/Helsinki').localize(
            datetime.strptime(attendance['check_in'], '%Y-%m-%d %H:%M:%S'))

        # If there is no checkout time, sum to now
        if attendance['check_out'] == False:
            # @TODO Same as above
            now = pytz.timezone('Europe/Helsinki').localize(
                datetime.utcnow())
            attendance['worked_hours'] = (now - date).seconds / 3600

        # Get the day and week index keys (Key = %Y-%m-%d)
        day_key = date.strftime('%Y-%m-%d')
        # Counts weeks from first Monday of the year
        week_key = date.strftime('%W')

        if week_key not in weeks:
            weeks[week_key] = {}
        
        if day_key not in weeks[week_key]:
            # @TODO Assumes 7.5 hours per day
            weeks[week_key][day_key] = {
                'allocated_hours': 7.5,
                'worked_hours': 0,
                'holiday': None
            }

        if day_key in local_holidays:
            # This day is a holiday, no allocated hours
            weeks[week_key][day_key]['holiday'] = local_holidays.get(day_key)
            weeks[week_key][day_key]['allocated_hours'] = 0
            
        # Sum the attendance
        weeks[week_key][day_key]['worked_hours'] += attendance['worked_hours']
    
    total_diff = 0
    total_hours = 0
    day_diff = 0
    click.echo(click.style(f'Balance as of {(datetime.today().isoformat(timespec="seconds"))} (system time)', fg='blue'))
    click.echo(click.style('Day\t\tWorked\tDifference', fg='blue'))
    for week_number, week in sorted(weeks.items()):
        for key, day in sorted(week.items()):
            diff = day['worked_hours'] - day['allocated_hours']
            colored_diff(f'{key}\t{(day["worked_hours"]):.2f}', f'{diff:+.2f}', day['holiday'])

            if key == datetime.today().strftime('%Y-%m-%d'):
                day_diff += day['worked_hours'] - day['allocated_hours']
            else:
                total_diff += day['worked_hours'] - day['allocated_hours']
            total_hours += day['worked_hours']

    today = datetime.now().strftime('%Y-%m-%d')
    this_week = datetime.now().strftime('%W')
    hours_today = 0
    allocated_today = 0
    if today in weeks.get(this_week, {}): 
        hours_today = weeks[this_week][today]['worked_hours']
        allocated_today = weeks[this_week][today]['allocated_hours']

    click.echo(click.style('---\t\t------\t-----', fg='blue'))
    colored_diff(f'Totals:\t\t{total_hours:.2f}', f'{(total_diff + day_diff):+.2f}')
    print()
    colored_diff('Balance yesterday:', f'{total_diff:+.2f}')
    colored_diff('Balance now:\t', f'{(total_diff + day_diff):+.2f}')
    colored_diff(
        'Allocated hours today:', f'{(allocated_today - hours_today):+.2f}', invert=True)


cli = click.CommandCollection(sources=[
    attendance_group,
    tasks_group,
    project_group,
    settings_group
])
    
def main():
    cli()

if __name__ == '__main__':
    main()
