# -*- coding: utf-8 -*-
#
# This file is part of INGInious. See the LICENSE and the COPYRIGHTS files for
# more information about the licensing of this file.

import json
from collections import OrderedDict

from inginious.frontend.task_dispensers.util import check_toc, SectionsList, SectionConfigItem
from inginious.frontend.task_dispensers import TaskDispenser


class TableOfContents(TaskDispenser):

    def __init__(self, task_list_func, dispenser_data, database, course_id):
        self._task_list_func = task_list_func
        self._toc = SectionsList(dispenser_data)
        self._database = database
        self._course_id = course_id

    @classmethod
    def get_id(cls):
        """ Returns the task dispenser id """
        return "toc"

    @classmethod
    def get_name(cls, language):
        """ Returns the localized task dispenser name """
        return _("Table of contents")

    def get_course_grade(self, username, course, user_task_list):
        tasks = course.get_tasks()
        tasks_data = {taskid: {"succeeded": False, "grade": 0.0} for taskid in user_task_list}
        user_tasks = self._database.user_tasks.find({"username": username, "courseid": course.get_id(), "taskid": {"$in": user_task_list}})
        tasks_score = [0.0, 0.0]

        for taskid in user_task_list:
            tasks_score[1] += tasks[taskid].get_grading_weight()

        for user_task in user_tasks:
            tasks_data[user_task["taskid"]]["succeeded"] = user_task["succeeded"]
            tasks_data[user_task["taskid"]]["grade"] = user_task["grade"]

            weighted_score = user_task["grade"]*tasks[user_task["taskid"]].get_grading_weight()
            tasks_score[0] += weighted_score

        course_grade = round(tasks_score[0]/tasks_score[1]) if tasks_score[1] > 0 else 0
        return course_grade

    def get_weight(self, taskid):
        """ Returns the weight of taskid """
        try:
            struct = self._toc.to_structure()
            for elem in struct:
                weight = self._toc.get_value_rec(taskid,elem,"weights")
                if weight is not None:
                    return weight
            return 1
        except:
            return 1

    def get_stored_submissions(self,taskid):
        try:
            struct = self._toc.to_structure()
            for elem in struct:
                store_submission = self._toc.get_value_rec(taskid,elem,"store_submission")
                if store_submission is not None:
                    return store_submission
            return 0
        except:
            return 0

    def get_course_grade(self, username):
        """ Returns the grade of a user for the current course"""
        task_list = self.get_user_task_list([username])[username]
        user_tasks = self._database.user_tasks.find({"username": username, "courseid": self._course_id, "taskid": {"$in": task_list}})
        return self._toc.get_course_grade_weighted_sum(user_tasks, task_list, self.get_weight)

    def get_dispenser_data(self):
        """ Returns the task dispenser data structure """
        return self._toc

    def render_edit(self, template_helper, course, task_data):
        """ Returns the formatted task list edition form """
        config_fields = {
            "closed": SectionConfigItem(_("Closed by default"), "checkbox", False)
        }
        return template_helper.render("course_admin/task_dispensers/toc.html", course=course,
                                      course_structure=self._toc, tasks=task_data, config_fields=config_fields)

    def render(self, template_helper, course, tasks_data, tag_list):
        """ Returns the formatted task list"""
        return template_helper.render("task_dispensers/toc.html", course=course, tasks=self._task_list_func(),
                                      tasks_data=tasks_data, tag_filter_list=tag_list, sections=self._toc)

    @classmethod
    def check_dispenser_data(cls, dispenser_data):
        """ Checks the dispenser data as formatted by the form from render_edit function """
        new_toc = json.loads(dispenser_data)
        valid, errors = check_toc(new_toc)
        return new_toc if valid else None, errors


    def get_user_task_list(self, usernames):
        """ Returns a dictionary with username as key and the user task list as value """
        tasks = self._task_list_func()
        task_list = [taskid for taskid in self._toc.get_tasks() if
                     taskid in tasks and tasks[taskid].get_accessible_time().after_start()]
        return {username: task_list for username in usernames}

    def get_ordered_tasks(self):
        """ Returns a serialized version of the tasks structure as an OrderedDict"""
        tasks = self._task_list_func()
        return OrderedDict([(taskid, tasks[taskid]) for taskid in self._toc.get_tasks() if taskid in tasks])

    def get_task_order(self, taskid):
        """ Get the position of this task in the course """
        tasks_id = self._toc.get_tasks()
        if taskid in tasks_id:
            return tasks_id.index(taskid)
        else:
            return len(tasks_id)