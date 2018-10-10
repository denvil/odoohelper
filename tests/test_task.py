import unittest
from odoohelper.tasks import Task

class TaskTestSuite(unittest.TestCase):
    """Task creation tests"""
    def test_full_task(self):
        """This should create task without problems"""
        task = Task({
            'name': 'test',
            'id': 1,
            'stage_id' : [1, 'name'],
            'date_deadline': '2018-10-31',
            'date_start': '2018-10-20 00:00:00',
            'date_end': '2018-10-31 23:59:00',
            'partial_messages': [{'date':'2018-10-21 12:00:00'}],
            'kanban_state': 'blocked',
            'planned_hours': 100,
            'priority': '1'
        })
        self.assertIsNotNone(task)

    def test_missing_dates(self):
        """Dates as False should not kill task creation"""
        task = Task({
            'name': 'test',
            'id': 1,
            'stage_id' : [1, 'name'],
            'date_deadline': False,
            'date_start': False,
            'date_end': False,
            'partial_messages': [{'date':'2018-10-21 12:00:00'}],
            'kanban_state': 'blocked',
            'planned_hours': 100,
            'priority': '1'
        })
        self.assertIsNotNone(task)

