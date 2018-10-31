import sys
import click
from odoohelper.settings import Settings
from odoohelper.client import Client
from odoohelper.utils import get_pass, check_config
from .tasks import Task
from .interactive import as_interactive

@click.group()
def tasks_group():
    # Temp task group
    pass

@tasks_group.command()
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
