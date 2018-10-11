"""
Interactive editors for tasks and others
"""
from collections import namedtuple

import click

from odoohelper.tasks import Task

Action = namedtuple('Action', ['key', 'description', 'action_func'])
Reaction = namedtuple('Reaction', ['cont', 'index'])

def open_in_browser(client, task):
    click.launch(task.url())
    return Reaction(True, None)

def change_deadline(client, task):
    return Reaction(True, None)

def change_startdate(client, task):
    return Reaction(True, None)

def mark_as_done(client, task):
    return Reaction(True, None)

def next_task(client, task):
    # Return from task view and advance index by 1
    return Reaction(False, 1)

def previous_task(client, task):
    # Return from task view and rollback index by 1
    return Reaction(False, -1)

def exit_tasks(client, task):
    exit(0)

def print_data(title, data, warning=False):
    data_color = 'red' if warning else 'white'
    click.echo(
        click.style(f'{title}:\t', fg='blue') +
        click.style(data, fg=data_color)
    )

def print_task(task):
    """
    Print task information
    """

    print_data('Task title', task.name)
    print_data('Priority', str(task.priority))
    if not task.deadline:
        print_data('Deadline', 'MISSING!', True)
    else:
        print_data('Deadline', str(task.deadline)) # Timezone conversion missing

def as_interactive(client: any, task: Task, task_count: int, current_index: int):
    """
    Handle interactive task here
    """
    actions = [
        Action(('1',), 'Open in browser', open_in_browser),
        Action(('2',), 'Change deadline', change_deadline),
        Action(('3',), 'Change start date', change_startdate),
        Action(('0',), 'Mark as done', mark_as_done),
        Action(('n', '\r'), 'Next task', next_task),
        Action(('p',), 'Previous task', previous_task),
        Action(('e',), 'Exit', exit_tasks)
    ]

    action_str = ''
    for action in actions:
        action_str += f'[{action.key[0]}] {action.description} '

    # Loop around one task until ctrl+c or enter is given
    while True:
        # Reload task here.
        task.reload(client)
        click.clear()
        print_data('Current queue', f'{current_index+1}/{task_count}')
        print_task(task)
        print_data('Actions', action_str)

        action_key = click.getchar()
        try:
            act = next(act for act in actions if action_key in act.key)
        except StopIteration:
            continue
        # Action func should return false if this task is done
        reaction = act.action_func(client, task)
        if not reaction.cont:
            return reaction.index
