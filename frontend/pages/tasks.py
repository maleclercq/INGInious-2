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
""" Task page """
import base64
import json
import mimetypes
import urllib

import web

from common.tasks_code_boxes import FileBox
from common.tasks_problems import MultipleChoiceProblem, BasicCodeProblem
from frontend.base import renderer
from frontend.custom.courses import FrontendCourse
import frontend.submission_manager as submission_manager
import frontend.user as User


class TaskPage(object):

    """ Display a task (and allow to reload old submission/file uploaded during a submission) """

    def GET(self, courseid, taskid):
        """ GET request """
        if User.is_logged_in():
            try:
                course = FrontendCourse(courseid)
                if not course.is_open() and User.get_username() not in course.get_admins():
                    return renderer.course_unavailable()

                task = course.get_task(taskid)
                if not task.is_open() and User.get_username() not in course.get_admins():
                    return renderer.task_unavailable()

                User.get_data().view_task(courseid, taskid)

                userinput = web.input()
                if "submissionid" in userinput and "questionid" in userinput:
                    # Download a previously submitted file
                    submission = submission_manager.get_submission(userinput["submissionid"], True)
                    if submission is None:
                        raise web.notfound()
                    sinput = submission_manager.get_input_from_submission(submission, True)
                    if userinput["questionid"] not in sinput:
                        raise web.notfound()

                    if isinstance(sinput[userinput["questionid"]], dict):
                        # File uploaded previously
                        mimetypes.init()
                        mime_type = mimetypes.guess_type(urllib.pathname2url(sinput[userinput["questionid"]]['filename']))
                        web.header('Content-Type', mime_type)
                        return base64.b64decode(sinput[userinput["questionid"]]['value'])
                    else:
                        # Other file, download it as text
                        web.header('Content-Type', 'text/plain')
                        return sinput[userinput["questionid"]]
                else:
                    # Display the task itself
                    return renderer.task(course, task, submission_manager.get_user_submissions(task))
            except:
                if web.config.debug:
                    raise
                else:
                    raise web.notfound()
        else:
            return renderer.index(False)

    def POST(self, courseid, taskid):
        """ POST a new submission """
        if User.is_logged_in():
            try:
                course = FrontendCourse(courseid)
                if not course.is_open() and User.get_username() not in course.get_admins():
                    return renderer.course_unavailable()

                task = course.get_task(taskid)
                if not task.is_open() and User.get_username() not in course.get_admins():
                    return renderer.task_unavailable()

                User.get_data().view_task(courseid, taskid)
                userinput = web.input()
                if "@action" in userinput and userinput["@action"] == "submit":
                    # Reparse user input with array for multiple choices
                    init_var = self.list_multiple_multiple_choices_and_files(task)
                    userinput = task.adapt_input_for_backend(web.input(**init_var))

                    if not task.input_is_consistent(userinput):
                        web.header('Content-Type', 'application/json')
                        return json.dumps({"status": "error", "text": "Please answer to all the questions. Your responses were not tested."})
                    del userinput['@action']

                    # Get debug info if the current user is an admin
                    debug = User.get_username() in course.get_admins()

                    # Start the submission
                    submissionid = submission_manager.add_job(task, userinput, debug)

                    web.header('Content-Type', 'application/json')
                    return json.dumps({"status": "ok", "submissionid": str(submissionid)})
                elif "@action" in userinput and userinput["@action"] == "check" and "submissionid" in userinput:
                    if submission_manager.is_done(userinput['submissionid']):
                        web.header('Content-Type', 'application/json')
                        result = submission_manager.get_submission(userinput['submissionid'])
                        result = submission_manager.get_input_from_submission(result)
                        return self.submission_to_json(result, User.get_username() in course.get_admins())
                    else:
                        web.header('Content-Type', 'application/json')
                        return json.dumps({'status': "waiting"})
                elif "@action" in userinput and userinput["@action"] == "load_submission_input" and "submissionid" in userinput:
                    submission = submission_manager.get_submission(userinput["submissionid"])
                    submission = submission_manager.get_input_from_submission(submission)
                    if not submission:
                        raise web.notfound()
                    web.header('Content-Type', 'application/json')
                    return self.submission_to_json(submission, (User.get_username() in course.get_admins()), True)
                else:
                    raise web.notfound()
            except:
                if web.config.debug:
                    raise
                else:
                    raise web.notfound()
        else:
            return renderer.index(False)

    def submission_to_json(self, data, debug, reloading=False):
        """ Converts a submission to json (keeps only needed fields) """
        tojson = {'status': data['status'], 'result': data.get('result', 'crash'), 'id': str(data["_id"]), 'submitted_on': str(data['submitted_on'])}

        if reloading:
            # Set status='ok' because we are reloading an old submission.
            tojson["status"] = 'ok'
            # And also include input
            tojson["input"] = data.get('input', {})

        if "text" in data:
            tojson["text"] = data["text"]
        if "problems" in data:
            tojson["problems"] = data["problems"]

        if debug:
            tojson["debug"] = data
        return json.dumps(tojson, default=str)

    def list_multiple_multiple_choices_and_files(self, task):
        """ List problems in task that expect and array as input """
        output = {}
        for problem in task.get_problems():
            if isinstance(problem, MultipleChoiceProblem) and problem.allow_multiple():
                output[problem.get_id()] = []
            elif isinstance(problem, BasicCodeProblem):
                for box in problem.get_boxes():
                    if isinstance(box, FileBox):
                        output[box.get_complete_id()] = {}
        return output
