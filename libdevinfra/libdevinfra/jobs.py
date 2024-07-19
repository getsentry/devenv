# job executor framework preferably for i/o bound things
# a job is a sequential execution of tasks
# a task is a python function
# tasks can spawn jobs upon successful completion
# tasks early fail the respective job
# should take a function f
# essentially we're just a scheduling layer on top of python's TPE
# and we define the structure of a Job and Task
# devenv should be in charge of passing devenv.lib.proc.runs to this
from __future__ import annotations

import concurrent.futures
from collections.abc import Callable
from dataclasses import dataclass


# TODO: some kind of status structure (task 2/4 success, running, success, fail)
@dataclass
class Job:
    """foo"""

    name: str
    tasks: list  # not sure how to type Task here


@dataclass
class Task:
    """foo"""

    name: str
    func: Callable
    spawn_jobs: tuple[Job] = ()
    log: str = ""
    logfile: str = ""


# a task is responsible for collecting its stdout/err and saving it


def _run_job(job, tpe):
    for task in job.tasks:
        print(f"job {job.name} schedules task {task.name}")
        # schedule task.func
        # save to log
        # spawn any jobs asynchronously
        for task_spawned_job in task.spawn_jobs:
            print(f"task {task.name} schedules {task_spawned_job.name}")
            future = tpe.submit(_run_job, task_spawned_job, tpe)


def run_jobs(jobs, tpe):
    # TODO: tasks can reference a new job(s) to kick off, but the executor should precheck this for safety

    futures = (
        # all Jobs are immediately scheduled for execution
        tpe.submit(_run_job, job, tpe)
        for job in jobs
    )
    for f in concurrent.futures.as_completed(futures):
        # we need a global futures iterable
        print(f)
