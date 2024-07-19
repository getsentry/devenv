from __future__ import annotations

import concurrent.futures
import functools

from devenv.lib.proc import run
from libdevinfra.jobs import Job
from libdevinfra.jobs import run_jobs
from libdevinfra.jobs import Task


def task(s):
    output = run(("echo", s), stdout=True)
    return output


def task_fail():
    output = "fine\n"
    if True:
        output += "some kinda error\n"
        raise Exception(output)
    return output


# define everything first then fill in references to spawn_jobs later
ta1 = Task(name="a1", func=functools.partial(task, "a1"))
ta2 = Task(name="a2", func=functools.partial(task, "a2"))
ja = Job(name="a", tasks=(ta1, ta2))
tb1 = Task(name="b1", func=functools.partial(task, "b1"))
tb2 = Task(name="b2", func=task_fail)
jb = Job(name="b", tasks=(tb1, tb2))
tc1 = Task(name="c1", func=functools.partial(task, "c1"))
jc = Job(name="c", tasks=(tc1,))
ta2.spawn_jobs = (jc,)

with concurrent.futures.ThreadPoolExecutor() as tpe:
    run_jobs((ja, jb), tpe)
