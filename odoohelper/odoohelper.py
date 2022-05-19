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
    from datetime import datetime, timedelta
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
    filters_leave = [
        ('employee_id.user_id.id', '=', user_id),
        ('holiday_type', '=', 'employee')
    ]

    # Add end cutoff for checkout if there is one
    if end:
        filters.append(('check_out', '<', end.strftime('%Y-%m-%d 00:00:00')))

    # Get start and end times
    if start:
        # No need to calculate start or end
        pass
    elif period == 'month':
        # Calculate month
        start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
        if start.month < 12:
            end = start.replace(month=start.month + 1, day=1) - \
                timedelta(days=1)
        else:
            end = start.replace(day=31)
    elif period == 'year':
        # Calculate year
        start = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0)
        end = start.replace(month=start.month, day=31)

    # Add start filters
    filters.append(
        ('check_in', '>=', start.strftime('%Y-%m-%d 00:00:00')))
    filters_leave.append(
        ('date_from', '>=', start.strftime('%Y-%m-%d 00:00:00')))

    # Always set end to end of today if not set
    if not end:
        end = datetime.now().replace(hour=23, minute=59, second=59)

    # Add end cutoff for leaves
    filters_leave.append(
        ('date_to', '<', end.strftime('%Y-%m-%d 00:00:00')))

    attendance_ids = client.search('hr.attendance', filters)
    attendances = client.read('hr.attendance', attendance_ids)

    leave_ids = client.search('hr.holidays', filters_leave)
    leaves = client.read('hr.holidays', leave_ids)

    def daterange(start_date, end_date):
        # Always emit at least one day
        for n in range(int((end_date - start_date).days) + 1):
            yield start_date + timedelta(n)

    # Pre-process the weeks and days
    weeks = {}
    # @TODO Assumes user is in Finland
    local_holidays = holidays.FI()

    # Faux data to test holidays
    # attendances.append({
    #     'check_in': '2018-01-01 00:00:00',
    #     'check_out': '2018-01-01 02:00:00',
    #     'worked_hours': 2
    # })

    # Process attendances
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
                'overtime': False,
                'overtime_reason': None
            }

        # Sum the attendance
        weeks[week_key][day_key]['worked_hours'] += attendance['worked_hours']

    for date in daterange(start, end):
        # Get the day and week index keys (Key = %Y-%m-%d)
        day_key = date.strftime('%Y-%m-%d')
        # Counts weeks from first Monday of the year
        week_key = date.strftime('%W')
        if day_key not in weeks.get(week_key, {}):
            # We don't care, no attendances for this day
            continue

        if day_key in local_holidays:
            # This day is a holiday, no allocated hours
            weeks[week_key][day_key]['overtime'] = True
            weeks[week_key][day_key]['overtime_reason'] = local_holidays.get(
                day_key)
            weeks[week_key][day_key]['allocated_hours'] = 0

        if date.isoweekday() >= 6:
            # Weekend, assume everything is overtime
            weeks[week_key][day_key]['overtime'] = True
            weeks[week_key][day_key]['overtime_reason'] = 'Weekend'
            weeks[week_key][day_key]['allocated_hours'] = 0

    # Process any leaves
    for leave in leaves:
        leave_start = pytz.timezone('Europe/Helsinki').localize(
            datetime.strptime(leave['date_from'], '%Y-%m-%d %H:%M:%S'))
        leave_end = pytz.timezone('Europe/Helsinki').localize(
            datetime.strptime(leave['date_to'], '%Y-%m-%d %H:%M:%S'))
        for date in daterange(leave_start, leave_end):
            # Get the day and week index keys (Key = %Y-%m-%d)
            day_key = date.strftime('%Y-%m-%d')
            # Counts weeks from first Monday of the year
            week_key = date.strftime('%W')
            if day_key not in weeks.get(week_key, {}):
                # We don't care, no attendances for this day
                continue
            weeks[week_key][day_key]['overtime'] = True
            weeks[week_key][day_key]['overtime_reason'] = f'Leave: {leave["name"]}'
            weeks[week_key][day_key]['allocated_hours'] = 0

    total_diff = 0
    total_hours = 0
    day_diff = 0
    click.echo(click.style(f'Balance as of {(datetime.today().isoformat(timespec="seconds"))} (system time)', fg='blue'))
    click.echo(click.style('Day\t\tWorked\tDifference', fg='blue'))
    for week_number, week in sorted(weeks.items()):
        for key, day in sorted(week.items()):
            if day['worked_hours'] == 0.0:
                continue
            diff = day['worked_hours'] - day['allocated_hours']
            colored_diff(f'{key}\t{(day["worked_hours"]):.2f}',
                         f'{diff:+.2f}', day.get('overtime_reason', None))

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
