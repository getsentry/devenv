from devenv.lib.proc import run_jobs

run_jobs(
    (
        (
            "job1",
            (
                # kwargs for proc.run
                {"cmd": ("echo", "job 1 $foo"), "env": {"foo": "bar"}},
                {"cmd": ("echo", "$foo"), "env": {"foo": "baz"}},
            ),
        ),
        (
            "job2",
            (
                {"cmd": ("echo", "job 2 $foo"), "env": {"foo": "bar"}},
                {"cmd": ("false",), "env": {"foo": "baz"}},
            ),
        ),
    )
)
