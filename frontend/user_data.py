# -*- coding: utf-8 -*-
#
# Copyright (c) 2014 Université Catholique de Louvain.
#
# This file is part of INGInious.
#
# INGInious is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# INGInious is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with INGInious.  If not, see <http://www.gnu.org/licenses/>.
""" Contains the UserData class that helps to manage saved data of a user """
from frontend.base import get_database, add_to_template_globals


class UserData(object):

    """ Allow to get and to modify _data stored in database for a particular user
            userdata
            {
                "_id":             "gderval",
                "realname":        "Guillaume Derval",
                "email":           "guillaume.derval@student.uclouvain.be",
                "task_tried":      0,
                "task_succeeded":  0,
                "total_tries":     0,
            }

            user_course
            {
                "username":        "gderval",
                "courseid":        "idCourse1",
                "task_tried":      0,
                "task_succeeded":  0,
                "total_tries":     0
            }

            user_task
            {
                "username":        "gderval",
                "courseid":        "idCourse1",
                "taskid":          "idTask1",
                "tried":           0,
                "succeeded":       False
            }
    """

    def __init__(self, username):
        self.username = username
        self._data = None
        self._update_cache()

    def _update_cache(self):
        """ Update internal cache of this object """
        self._data = get_database().users.find_and_modify({"_id": self.username},
                                                          {"$setOnInsert": {"realname": "",
                                                                            "email": "",
                                                                            "task_tried": 0,
                                                                            "task_succeeded": 0,
                                                                            "total_tries": 0}},
                                                          upsert=True,
                                                          new=True)

    def update_basic_informations(self, realname, email):
        """ Update basic informations in the database """
        get_database().users.update({"_id": self.username}, {"$set": {"realname": realname, "email": email}})
        self._update_cache()

    def get_data(self):
        """ Returns data of this user """
        return self._data

    def get_course_data(self, courseid):
        """ Returns data of this user for a specific course """
        return get_database().user_courses.find_one({"username": self.username, "courseid": courseid})

    def get_task_data(self, courseid, taskid):
        """ Returns data of this user for a specific task """
        return get_database().user_tasks.find_one({"username": self.username, "courseid": courseid, "taskid": taskid})

    def view_task(self, courseid, taskid):
        """ Set in the database that the user has viewed this task """
        # Insert a new entry if no one exists
        self.view_course(courseid)
        get_database().user_tasks.update(
            {"username": self.username, "courseid": courseid, "taskid": taskid},
            {"$setOnInsert": {"username": self.username, "courseid": courseid, "taskid": taskid, "tried": 0, "succeeded": False}},
            upsert=True)

    def view_course(self, courseid):
        """ Set in the database that the user has viewed this course """
        get_database().user_courses.update(
            {"username": self.username, "courseid": courseid},
            {"$setOnInsert": {"username": self.username, "courseid": courseid, "task_tried": 0, "task_succeeded": 0, "total_tries": 0}},
            upsert=True)

    def update_stats(self, submission, job):
        """ Update stats with a new submission """
        # Tasks
        # Insert a new entry if no one exists
        obj = get_database().user_tasks.find_and_modify(
            {"username": self.username, "courseid": submission["courseid"], "taskid": submission["taskid"]},
            {"$setOnInsert": {"username": self.username, "courseid": submission["courseid"], "taskid": submission["taskid"], "tried": 0, "succeeded": False}},
            upsert=True)
        new_try = obj is None or obj["tried"] == 0

        # Update inc counter
        get_database().user_tasks.update({"username": self.username, "courseid": submission["courseid"], "taskid": submission["taskid"]}, {"$inc": {"tried": 1}})

        # Set to succeeded if not succeeded yet
        new_succeed = False
        if job["result"] == "success":
            obj = get_database().user_tasks.find_and_modify({"username": self.username,
                                                             "courseid": submission["courseid"],
                                                             "taskid": submission["taskid"],
                                                             "succeeded": False},
                                                            {"$set": {"succeeded": True}})
            new_succeed = obj is not None and obj["succeeded"] == False

        # Courses
        # Insert a new entry if no one exists
        get_database().user_courses.update(
            {"username": self.username, "courseid": submission["courseid"]},
            {"$setOnInsert": {"username": self.username, "courseid": submission["courseid"], "task_tried": 0, "task_succeeded": 0, "total_tries": 0}},
            upsert=True)

        # Update counters
        get_database().user_courses.update(
            {"username": self.username, "courseid": submission["courseid"]},
            {"$inc": {"total_tries": 1, "task_tried": (1 if new_try else 0), "task_succeeded": (1 if new_succeed else 0)}})

        # User
        get_database().users.update(
            {"_id": self.username},
            {"$inc": {"total_tries": 1, "task_tried": (1 if new_try else 0), "task_succeeded": (1 if new_succeed else 0)}})

        self._update_cache()

add_to_template_globals("UserData", UserData)
