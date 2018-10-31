from datetime import datetime, timedelta
import unittest
from unittest.mock import Mock
from odoohelper.tasks import Task

class TaskPriorityTestSuite(unittest.TestCase):
    """Basic test cases."""
    def setUp(self):
        self.task = Task({
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

    def test_deadline_missing(self):
        """Priority should be 1000 if deadline is missing"""
        self.task.deadline = False
        self.assertEqual(self.task.priority_check_deadline_pass(), 1000, 'Wrong priority')

    def test_deadline_passed(self):
        """Priority should be 300 if deadline has passed"""
        self.task.get_current_time = Mock(
            return_value=datetime.strptime('2018-11-02 00:00:00', '%Y-%m-%d %H:%M:%S'))
        self.assertEqual(self.task.priority_check_deadline_pass(), 300, 'Wrong priority')

    def test_deadline_over_100days(self):
        """Priority should be 0 if deadline is over 100 days away"""
        mock_now = Mock(
            return_value=datetime.strptime('2018-11-02 00:00:00', '%Y-%m-%d %H:%M:%S'))
        new_dl = mock_now() + timedelta(days=100)
        self.task.end_date = new_dl
        self.task.get_current_time = mock_now
        self.assertEqual(self.task.priority_check_deadline_pass(), 300, 'Wrong priority')

    def test_deadline_inside_100days(self):
        """Priority should lower from 300 to 0"""
        current_dl = self.task.deadline
        self.task.get_current_time = Mock(return_value=current_dl)
        for days in range(101):
            new_dl = current_dl + timedelta(days=days)
            self.task.deadline = new_dl
            priority = self.task.priority_check_deadline_pass()
            if days == 0:
                self.assertEqual(priority, 300)
            if days == 4:
                self.assertEqual(priority, 18)
            if days == 9:
                self.assertEqual(priority, 0)
    
    def test_planned_hours(self):
        """Planned hours should influence priority"""
        task_planned = Task({
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
        self.assertEqual(task_planned.priority_planned_hours_set(), 0)
        task_not_planned = Task({
            'name': 'test',
            'id': 1,
            'stage_id' : [1, 'name'],
            'date_deadline': '2018-10-31',
            'date_start': '2018-10-20 00:00:00',
            'date_end': '2018-10-31 23:59:00',
            'partial_messages': [{'date':'2018-10-21 12:00:00'}],
            'kanban_state': 'blocked',
            'planned_hours': 0,
            'priority': '1'
        })
        self.assertEqual(task_not_planned.priority_planned_hours_set(), 50)

    def test_gantt_hours(self):
        """Gantt should be set"""
        task_planned = Task({
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
        self.assertEqual(task_planned.priority_planned_hours_set(), 0)
        task_not_planned_start = Task({
            'name': 'test',
            'id': 1,
            'stage_id' : [1, 'name'],
            'date_deadline': '2018-10-31',
            'date_start': False,
            'date_end': '2018-10-31 23:59:00',
            'partial_messages': [{'date':'2018-10-21 12:00:00'}],
            'kanban_state': 'blocked',
            'planned_hours': 0,
            'priority': '1'
        })
        self.assertEqual(task_not_planned_start.priority_planned_hours_set(), 50)
        task_not_planned_end = Task({
            'name': 'test',
            'id': 1,
            'stage_id' : [1, 'name'],
            'date_deadline': '2018-10-31',
            'date_start': '2018-10-20 00:00:00',
            'date_end': False,
            'partial_messages': [{'date':'2018-10-21 12:00:00'}],
            'kanban_state': 'blocked',
            'planned_hours': 0,
            'priority': '1'
        })
        self.assertEqual(task_not_planned_end.priority_planned_hours_set(), 50)

if __name__ == '__main__':
    unittest.main()