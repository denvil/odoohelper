"""
Odoo tasks
"""
import math
from datetime import datetime, timedelta
from odoohelper.settings import Settings

class Task():
    """
    Wrapper for Odoo task
    """
    def __init__(self, task_data):
        self.id = task_data['id']
        self.setup(task_data)

    def setup(self, task_data):
        """
        Setup values from raw json task.
        """
        self.name = task_data['name']
        self.stage = task_data['stage_id']
        self.project = task_data.get('full_project_name', 'Not assigned to project')
        # All dates and times should be in UTC. Only print and input with local time
        self.deadline = self.date_or_bool(task_data['date_deadline'], '%Y-%m-%d')
        # Padd deadline to 12:00:00 for clarity
        if self.deadline:
            self.deadline += timedelta(hours=12)
        self.start_date = self.date_or_bool(task_data['date_start'], '%Y-%m-%d %H:%M:%S')
        self.end_date = self.date_or_bool(task_data['date_end'], '%Y-%m-%d %H:%M:%S')
        self.newest_message_date = max(
            datetime.strptime(
                d['date'], '%Y-%m-%d %H:%M:%S'
            ) for d in task_data['partial_messages']
        )
        self.blocked = task_data['kanban_state'] == 'blocked'
        self.planned_hours = task_data['planned_hours']
        self.marked_priority = task_data['priority'] == '1'
        self.priority = self.calculate_priority()

    @classmethod
    def print_topic(cls):
        return 'priority\tstage\tdeadline\tname'

    def __str__(self):
        """ Print as tab separated line"""
        return f'{self.priority}\t{self.stage[1]}\t{self.deadline}\t{self.name}'

    @classmethod
    def date_or_bool(cls, datestr, dateformat):
        try:
            return datetime.strptime(datestr, dateformat)
        except TypeError:
            return False

    def get_current_time(self):
        """
        Wrap datetime.now for easier mocking in tests
        """
        return datetime.now()

    def calculate_priority(self):
        """
        Calculate priority for task
        """
        weight_table = [
            ('Marked with star', self.priority_check_star),
            ('Deadline passed', self.priority_check_deadline_pass),
            ('Check for blocking', self.priority_check_blocked),
            # ('Check that planned hours is set', self.priority_planned_hours_set),
            # ('Check that gantt is set', self.priority_gantt_set)
        ]
        total_weight = 0
        for check in weight_table:
            total_weight += check[1]()
        return total_weight

    def priority_check_deadline_pass(self):
        """
        If deadline is missing or it has passed
        """
        if not self.deadline:
            return 1000
        if self.deadline <= self.get_current_time():
            return 300
        # Calculate each day to deadline.
        diff = self.deadline - self.get_current_time()
        diff = diff.days
        if diff > 100:
            diff = 100

        return int(math.pow(0.5, diff)*300)

    def priority_check_star(self):
        return 40 if self.marked_priority else 0

    def priority_check_blocked(self):
        """
        This will check how many days have gone since last message in blocked task.
        """
        if not self.blocked:
            return 0
        # Each day since blocked will increase weight by 5
        diff = self.get_current_time() - self.newest_message_date
        return 5 * diff.days

    def priority_planned_hours_set(task):
        """
        Each task should have something planned.
        """
        tasks = client['project.task']
        data = tasks.read(task.id, ['planned_hours'])
        if data['planned_hours'] > 0:
            return 0
        else:
            return 50

    def priority_gantt_set(task):
        """
        Each task should have start and end set
        """
        tasks = client['project.task']
        full_data = tasks.read(task.id)
        if not full_data['date_start'] or not full_data['date_end']:
            return 50
        return 0

    def url(self):
        """Return task url in host"""
        with Settings() as settings:
            return f'https://{settings["host"]}/web#id={self.id}&view_type=form&model=project.task&menu_id=93&action=143'

    def reload(self, client):
        """Reload task infromation."""
        task_data = client.read('project.task', self.id)
        task_data['partial_messages'] = client.read('mail.message', task_data['message_ids'], ['date', 'description'])
        self.setup(task_data)

    def update(self, client, field, value):
        client.write('project.task', self.id, {field: value})

    @staticmethod
    def fetch_tasks(client, filters):
        """
        Fetch tasks using client and filters.
        Each task will also find messages for it self for
        futher analytics. This can be slow process so it should be saved
        to some cache after fetching.
        """
        task_ids = client.search('project.task', filters)
        # Fetch data for task_ids
        tasks_data = client.read('project.task', task_ids)
        final_task_list = []
        for task in tasks_data:
            # Read only partial data to messages. For now only create date, description
            task['partial_messages'] = client.read('mail.message', task['message_ids'], ['date', 'description'])
            final_task_list.append(Task(task))
        return final_task_list

