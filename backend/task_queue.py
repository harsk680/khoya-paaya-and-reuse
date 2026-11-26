
from multiprocessing import Queue

# Queue sends a wake-up signal to the worker.
# MySQL will decide which job should run next.
job_queue = Queue()


def add_job_to_queue(job_id):
    job_queue.put(job_id)
    print(f"Job {job_id} added to queue")


def get_job_from_queue():
    job_id = job_queue.get()
    print(f"Worker received queue signal for job {job_id}")
    return job_id
