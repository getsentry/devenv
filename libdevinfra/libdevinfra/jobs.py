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
from enum import Enum


JobStatus = Enum(
    "JobStatus", ("SUCCESS", "FAIL", "RUNNING", "PENDING")
)

TaskStatus = Enum(
    "TaskStatus", ("SUCCESS", "FAIL", "RUNNING", "PENDING")
)


@dataclass
class Job:
    """foo"""

    name: str
    tasks: list  # not sure how to type Task here
    status: JobStatus = JobStatus.PENDING


@dataclass
class Task:
    """foo"""

    name: str
    func: Callable
    timeout: int = None
    spawn_jobs: tuple[Job] = ()
    log: str = ""
    status: TaskStatus = TaskStatus.PENDING

    def __repr__(self):
        return self.name

# a task is responsible for collecting its stdout/err and saving it

import queue

q = queue.SimpleQueue()


def _run_job(job, tpe):
    job.status = JobStatus.RUNNING

    i = 0
    n_tasks = len(job.tasks)
    for task in job.tasks:
        i += 1
        print(f"job {job.name} running task {task.name} ({i}/{n_tasks})...")
        task_future = tpe.submit(task.func)
        task.status = TaskStatus.RUNNING
        try:
            # we ask that task functions capture their output and
            # return it in a str
            task.log = task_future.result(timeout=task.timeout)
            # TODO: Task timed out
            task.status = TaskStatus.SUCCESS
        except Exception:
            # we ask that task functions should raise an Exception
            # to denote a failure, and print output that's useful
            task.status = TaskStatus.FAIL

        if task.status != TaskStatus.SUCCESS:
            job.status = JobStatus.FAIL
            return job

        # spawn any jobs only if the task finishes successfully
        for task_spawned_job in task.spawn_jobs:
            q.put(tpe.submit(_run_job, task_spawned_job, tpe))

    job.status = JobStatus.SUCCESS
    return job


def run_jobs(jobs, tpe):
    # TODO: tasks can reference a new job(s) to kick off
    # but the executor should verify beforehand that it's a DAG

    for job in jobs:
        # all Jobs are immediately scheduled for execution
        q.put(tpe.submit(_run_job, job, tpe))

    while True:
        futures = []
        while not q.empty():
            futures.append(q.get())

        for f in concurrent.futures.as_completed(futures):
            job = f.result()
            if job.status == JobStatus.FAIL:
                print(f"job {job.name} failed!!!")
                for task in job.tasks:
                    print(f"job {job.name} task {task.name} status {task.status}, log:\n{task.log}\n")
            elif job.status == JobStatus.SUCCESS:
                print(f"job {job.name} succeeded")
            else:
                print(f"job {job.name} unexpected status: {job.status}")

        # at this point there is a possibility that tasks had spawned more jobs
        if q.empty():
            break
