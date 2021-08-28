from time import sleep
from rq import get_current_job


def example(user_id, seconds):
    """
    This function implements a simple example for the purpose of testing Redis 
    RQ.
    """

    job = get_current_job()
    print("Starting a new task for user = {}".format(user_id))

    for i in range(seconds):
        job.meta['progress'] = i * 100.0 / seconds
        job.save_meta()
        print(i)
        sleep(1)

    job.meta['progress'] = 100.0
    job.save_meta()
    print("Task completed.")
        