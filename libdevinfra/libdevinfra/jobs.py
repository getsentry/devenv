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
    timeout: int = None
    spawn_jobs: tuple[Job] = ()
    log: str = ""
    logfile: str = ""

# a task is responsible for collecting its stdout/err and saving it

import queue

q = queue.SimpleQueue()


def _run_job(job, tpe):
    for task in job.tasks:
        print(f"job {job.name} schedules task {task.name}")
        task_future = tpe.submit(task.func)
        success = True
        try:
            task_future.result(timeout=task.timeout)
            # TODO: save output to log. We'll probably wrap
            # it so that we capture all stdout, and return it
            # as a result or some tempfile.
        except Exception:
            # we ask that task functions should raise an Exception
            # to denote a failure, and print output that's useful
            success = False

        # spawn any jobs only if the task finishes successfully
        if success:
            for task_spawned_job in task.spawn_jobs:
                print(f"task {task.name} schedules {task_spawned_job.name}")
                q.put(tpe.submit(_run_job, task_spawned_job, tpe))

    # TODO status structure (task 2/4 success, running, success, fail)
    return job


def run_jobs(jobs, tpe):
    # TODO: tasks can reference a new job(s) to kick off, but the executor should precheck this for safety

    for job in jobs:
        # all Jobs are immediately scheduled for execution
        q.put(tpe.submit(_run_job, job, tpe))

    all_jobs = []
    while True:
        while not q.empty():
            all_jobs.append(q.get())

        for f in concurrent.futures.as_completed(all_jobs):
            print(f, f.result())
            # todo, print complete status including futures that except

        # at this point there is a possibility that tasks had spawned more jobs
        if q.empty():
            break
