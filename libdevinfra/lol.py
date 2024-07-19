from __future__ import annotations

import concurrent.futures
import functools

from libdevinfra.jobs import Job
from libdevinfra.jobs import run_jobs
from libdevinfra.jobs import Task


def task_print(s):
    print(s)

def task_fail():
    raise Exception("lol")


# define everything first then fill in references to spawn_jobs later
ta1 = Task(name="a1", func=functools.partial(task_print, "a1"))
ta2 = Task(name="a2", func=functools.partial(task_print, "a2"))
ja = Job(name="a", tasks=(ta1, ta2))
tb1 = Task(name="b1", func=functools.partial(task_print, "b1"))
tb2 = Task(name="b2", func=task_fail)
jb = Job(name="b", tasks=(tb1, tb2))
tc1 = Task(name="c1", func=functools.partial(task_print, "c1"))
jc = Job(name="c", tasks=(tc1,))
ta2.spawn_jobs = (jc,)

with concurrent.futures.ThreadPoolExecutor() as tpe:
    run_jobs((ja, jb), tpe)
