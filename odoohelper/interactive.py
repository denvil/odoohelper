"""
Interactive editors for tasks and others
"""
import click
from odoohelper.tasks import Task

def open_in_browser(client, task):
    pass

def change_deadline(client, task):
    pass

def change_startdate(client, task):
    pass

def mark_as_done(client, task):
    pass

def print_data(title, data, warning=False):
    data_color = 'red' if warning else 'white'
    click.echo(
        click.style(f'{title}:\t', fg='blue') +
        click.style(data, fg='white')
    )

def as_interactive(client, task):
    """
    Handle interactive task here
    """
    actions = [
        ('Open in browser', open_in_browser),
        ('Change deadline', change_deadline),
        ('Change start date', change_startdate),
        ('Mark as done', mark_as_done)
    ]
    print_data('Task title', task.name)
    print_data('Priority', str(task.priority))
    if not task.deadline:
        print_data('Deadline', 'MISSING!', True)
    else:
        print_data('Deadline', str(task.deadline)) # Timezone conversion missing
    action_str = ''
    for action in actions:
        action_str += f'[{actions.index(action)}] {action[0]} '
    action_str += '<empty> continue to next task'
    print(action_str)


