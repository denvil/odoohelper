import os
import sys
import tempfile
import datetime
from subprocess import call

import click

import textile
from odoohelper.client import Client
from odoohelper.settings import Settings
from odoohelper.utils import check_config, get_pass, validate_odoo_date

from .interactive import as_interactive
from .tasks import Task


def create_message():
    """ Open editor """
    EDITOR = os.environ.get('EDITOR', 'vim')
    template = """Tehtävän kuvaus:

Tilaaja:

Mahdollinen muu tieto:
"""
    message = template
    with tempfile.NamedTemporaryFile(suffix='.tmp') as tf:
        tf.write(template.encode('utf-8'))
        tf.flush()
        call([EDITOR, tf.name])

        tf.seek(0)
        message = tf.read()
    
    html = textile.textile(message.decode('utf-8'))
    return html

@click.group()
def tasks_group():
    # Temp task group
    pass

@tasks_group.command()
@click.password_option(prompt=True if get_pass() is None else False, confirmation_prompt=False)
def instant(password):
    """ Start clocking on new task """
    if password is None:
        password = get_pass()
    check_config()
    with Settings() as config:
        client = Client(username=config['username'], password=password, database=config['database'], host=config['host'])
    client.connect()

    task = Task()
    # Inbox project 1555
    task.project_id = 1555
    task.name = f'Task started on {datetime.datetime.now()}'
    task.description = "Fill this later"
    task.user_id = client.user.id
    ids = task.create(client)
    client.start_tracking([ids])


@tasks_group.command()
@click.password_option(prompt=True if get_pass() is None else False, confirmation_prompt=False)
def stop(password):
    """ Stop clocking on previous task.
    If this is instance task then ask for more information """
    if password is None:
        password = get_pass()
    check_config()
    with Settings() as config:
        client = Client(username=config['username'], password=password, database=config['database'], host=config['host'])
    client.connect()
    filters = [
        ('user_id', '=', client.user.id),
    ]
    employee = client.search_read('hr.employee', filters)

    if not employee[0]['current_task']:
        click.echo('Nothing to show. Exiting..')
        return
    ids = employee[0]['current_task'][0]
    client.terminate_tracking([ids])
    task = Task()
    task.id = ids
    click.launch(task.url())
    input('Press Enter to continue...')


@tasks_group.command()
@click.password_option(prompt=True if get_pass() is None else False, confirmation_prompt=False)
@click.option('-t', '--title', metavar='<title>', help='Task title', prompt=True)
def create(password, title):
    """ Create new task """
    if password is None:
        password = get_pass()
    check_config()
    with Settings() as config:
        client = Client(username=config['username'], password=password, database=config['database'], host=config['host'])

    client.connect()
    message = create_message()

    selected_project = None
    while not selected_project:
        project = click.prompt('Project')
        filters = []
        filters.append(('is_subtask_project', '=', False))
        filters.append(('name', 'ilike', project))
        projects = client.search_read('project.project', filters)
        for index, project_data in enumerate(projects):
            click.echo(f'[{index}] {project_data["display_name"]}')
        click.echo(f'[s] Search again')
        if len(projects) == 1:
            selection = click.prompt('Select project', default=0)
        else:
            selection = click.prompt('Select project')
        try: 
            selected = int(selection)
            selected_project = projects[selected]
        except:
            pass
    task = Task()
    task.name = title
    task.description = message
    task.project_id = selected_project['id']

    selected_user = None
    while not selected_user:
        user = click.prompt('User')
        filters = []
    
        filters.append(('name', 'ilike', user))
        users = client.search_read('res.users', filters)
        for index, user_data in enumerate(users):
            click.echo(f'[{index}] {user_data["name"]}')
        click.echo(f'[s] Search again')
        if len(users) == 1:
            selection = click.prompt('Select user', default=0)
        else:
            selection = click.prompt('Select user')
        try: 
            selected = int(selection)
            selected_user = users[selected]
        except:
            pass
            
    
    task.user_id = selected_user['id']

    task.create(client)
    click.echo(task.url())
    input('Press Enter to continue...')


@tasks_group.command()
@click.password_option(prompt=True if get_pass() is None else False, confirmation_prompt=False)
@click.argument('search-term', required=False)
def search(password, search_term):
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
    if not search_term:
        search_term = click.prompt('Search')

    tasks = Task.search(client, search_term)
    if len(tasks) != 0:
        for task in tasks:
            click.echo(task.as_formatted('terminal'))
    else:
        click.echo('No tasks found')
    input('Press Enter to continue...')



@tasks_group.command()
@click.password_option(prompt=True if get_pass() is None else False, confirmation_prompt=False)
@click.option('-u','--user', metavar='<user full name>', help="User display name in Odoo")
@click.option('-i','--interactive', help="Ask what you want to do on each task", is_flag=True)
@click.option('-l','--list-tasks', help="List tasks", is_flag=True)
@click.option('-f', '--print-format', metavar='<format>', help='format return data as csv or md (markdown) (not interactive)', default='csv')
@click.option('--start', metavar='<start date>', callback=validate_odoo_date, help="Show active tasks from date")
@click.option('--end', metavar='<end date>', callback=validate_odoo_date, help="Show active tasks up to date")
def tasks(password, user, interactive, list_tasks, print_format, start=None, end=None):
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
    else:
        selected_user = None
        while not selected_user:
            filters = []
        
            filters.append(('name', 'ilike', user))
            users = client.search_read('res.users', filters)

            if len(users) == 1:
                selection = 0
            else:
                for index, user_data in enumerate(users):
                    click.echo(f'[{index}] {user_data["name"]}')
                click.echo(f'[s] Search again')
                selection = click.prompt('Select user')
            try: 
                selected = int(selection)
                selected_user = users[selected]
            except:
                user = click.prompt('User')
        user_id = selected_user['id']
    filters = [
        ('user_id', '=', user_id),
        ('stage_id', '!=', 8),  # This is done stage. Should be in config?
    ]

    if start:
        filters.append(('date_start', "<=", end.strftime('%Y-%m-%d 00:00:00')))
    if end:
        filters.append(('date_deadline', "<=", end.strftime('%Y-%m-%d 23:59:00')))

    all_tasks = Task.fetch_tasks(client, filters)
    all_sorted = sorted(all_tasks, key=lambda x: x.priority, reverse=True)
    if not interactive:
        click.echo(Task.print_topic(print_format))
        for task in all_sorted:
            click.echo(task.as_formatted(print_format))
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
