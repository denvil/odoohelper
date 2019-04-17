import datetime
import sys

import click

from odoohelper.client import Client
from odoohelper.settings import Settings
from odoohelper.tasks import Task
from odoohelper.utils import check_config, get_pass


def print_project_page(client, project, limit=None):
    """ Print project page as markdown """
    if not limit:
        click.echo(f'## {project["display_name"]}')
        click.echo(f'{project["description"]}')
    if len(project['tasks']) == 0:
        click.echo(f'No tasks...')
        return
    
    # Inbox 14
    # Tehty 8
    # Työn alla 7
    # Tilattu 6
    # Read tasks
    filters = [
        '&',
        ('project_id', '=', project['id']),
        '|',
        ('stage_id', '=', 7),
        ('stage_id', '=', 6),
    ]

    active_tasks = Task.fetch_tasks(client, filters)
    active_tasks = sorted(active_tasks, key=lambda x: x.priority, reverse=True)
    filters = [
        '&',
        ('project_id', '=', project['id']),
        ('stage_id', '=', 14),
    ]
    inbox_tasks = Task.fetch_tasks(client, filters)
    inbox_tasks = sorted(inbox_tasks, key=lambda x: x.priority, reverse=True)
    if len(active_tasks) == 0 and len(inbox_tasks) == 0:
        click.echo('No active or inbox tasks')
        return
    # Build gantt
    click.echo('\n### Status')
    # Find start date for this gantt (first task start date or create date)
    oldest_date = datetime.datetime.now()
    for task in active_tasks:
        if task.start_date:
            if task.start_date < oldest_date:
                oldest_date = task.start_date
        else:
            if task.create_date < oldest_date:
                oldest_date = task.create_date
    click.echo('\n### Active tasks')
    click.echo('@startuml\n@startgantt')
    click.echo(f'project starts the {oldest_date.date()}')
    click.echo('saturday are closed\nsunday are closed')
    if not limit:
        limit = len(active_tasks)
    for task in active_tasks[:limit]:
        # click.echo(f'[{task.name.replace("[","").replace("]","")}] lasts {task.days()} days')
        click.echo(f'[{task.name.replace("[","").replace("]","")}] starts on {task.start().date()}')
        click.echo(f'[{task.name.replace("[","").replace("]","")}] ends on {task.end().date()}')
    click.echo('@endgantt\n@enduml')

    click.echo(f'\n{Task.print_topic(print_format="md")}')
    for task in active_tasks[:limit]:
        click.echo(task.as_formatted('md'))

    # Find start date for this gantt (first task start date or create date)
    oldest_date = datetime.datetime.now()
    for task in inbox_tasks[:limit]:
        if task.start_date:
            if task.start_date < oldest_date:
                oldest_date = task.start_date
        else:
            if task.create_date < oldest_date:
                oldest_date = task.create_date

    click.echo('\n### Inbox tasks')
    click.echo('@startuml\n@startgantt')
    click.echo(f'project starts the {oldest_date.date()}')
    click.echo('saturday are closed\nsunday are closed')
    for task in inbox_tasks[:limit]:
        click.echo(f'[{task.name.replace("[","").replace("]","")}] starts on {task.start().date()}')
        click.echo(f'[{task.name.replace("[","").replace("]","")}] ends on {task.end().date()}')
    click.echo('@endgantt\n@enduml')
    
    click.echo(f'\n{Task.print_topic(print_format="md")}')
    for task in inbox_tasks[:limit]:
        click.echo(task.as_formatted('md'))

@click.group()
def project_group():
    pass

@project_group.command()
@click.password_option(prompt=True if get_pass() is None else False, confirmation_prompt=False)
@click.option('-l','--list-projects', help="List projects and their id", is_flag=True)
@click.option('-p','--project', metavar="<project id>", help="Print project information")
@click.option('-s','--summary', metavar="<project id>", help="Print project summary")
@click.option('-t','--sub-tasks', help="Show subtasks in list-projects", is_flag=True, default=False)
def project(password, list_projects, project, summary, sub_tasks):
    """ Return active projects"""
    if not list_projects and (not project and not summary):
        click.echo("Select --list-projects or --project/--summary")
        return
    if password is None:
        password = get_pass()
    check_config()
    with Settings() as config:
        client = Client(username=config['username'], password=password, database=config['database'], host=config['host'])
    client.connect()
    
    filters = []
    if not sub_tasks:
        filters.append(('is_subtask_project', '=', False))

    projects = client.search_read('project.project', filters)
    if list_projects:
        for project in projects:
            click.echo(f'{project["id"]}\t{project["display_name"]}')
        return
    if summary:
        for project in projects:
            # TODO change to single search for one project.
            if project['id'] == int(summary):
                print_project_page(client, project, 10)
        return
    if project:
        for pro in projects:
            # TODO change to single search for one project.
            if pro['id'] == int(project):
                print_project_page(client, pro)