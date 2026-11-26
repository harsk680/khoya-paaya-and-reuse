
from multiprocessing import Process
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import threading

from database import SessionLocal

from models import (
    Job,
    Item,
    LostReport,
    FoundReport,
    Match,
    Notification
)

from ai.matching import calculate_match_score


# Synchronization lock for match creation
match_lock = threading.Lock()


def process_job(job_id, job_type, reference_id, found_reference_id):

    db = SessionLocal()

    try:

        print(
            f"Thread {threading.current_thread().name} "
            f"is processing Job {job_id}"
        )

        # =================================
        # AI MATCHING
        # =================================

        if job_type == "AI_MATCH":

            lost_report = (
                db.query(LostReport)
                .filter(
                    LostReport.lost_id == reference_id
                )
                .first()
            )

            if not lost_report:
                raise ValueError("Lost report not found")

            found_report = (
                db.query(FoundReport)
                .filter(
                    FoundReport.found_id == found_reference_id
                )
                .first()
            )

            if not found_report:
                raise ValueError("Found report not found")

            lost_item = (
                db.query(Item)
                .filter(
                    Item.item_id == lost_report.item_id
                )
                .first()
            )

            found_item = (
                db.query(Item)
                .filter(
                    Item.item_id == found_report.item_id
                )
                .first()
            )

            if not lost_item or not found_item:
                raise ValueError("Item record not found")

            # AI similarity calculation
            score = calculate_match_score(
                lost_item,
                found_item
            )

            print(f"AI Match Score: {score}")

            if score >= 50:

                # Synchronize duplicate match checking
                with match_lock:

                    existing_match = (
                        db.query(Match)
                        .filter(
                            Match.lost_id == reference_id,
                            Match.found_id == found_reference_id
                        )
                        .first()
                    )

                    if existing_match:

                        existing_match.match_score = score

                    else:

                        new_match = Match(
                            lost_id=reference_id,
                            found_id=found_reference_id,
                            match_score=score,
                            status="possible"
                        )

                        db.add(new_match)
                        db.flush()

                        notification = Notification(
                            user_id=lost_report.user_id,
                            match_id=new_match.match_id,
                            message=(
                                "Possible match found for your lost item: "
                                f"{lost_item.title}"
                            )
                        )

                        db.add(notification)

                    db.commit()

            else:

                print(
                    "Similarity score below threshold. "
                    "No match created."
                )

        # =================================
        # TEST JOB
        # =================================

        elif job_type == "TEST":
            print(f"Test job started by {threading.current_thread().name}")

            print("Test job processed successfully")

        else:

            raise ValueError(
                f"Unsupported job type: {job_type}"
            )

        # =================================
        # MARK JOB COMPLETED
        # =================================

        job = (
            db.query(Job)
            .filter(Job.job_id == job_id)
            .first()
        )

        if job:
            job.status = "completed"
            job.completed_at = datetime.now()
            db.commit()

        print(f"Job {job_id} completed successfully")

    except Exception as e:

        db.rollback()

        print(f"Job {job_id} failed: {e}")

        try:

            failed_job = (
                db.query(Job)
                .filter(Job.job_id == job_id)
                .first()
            )

            if failed_job:
                failed_job.status = "failed"
                db.commit()

        except Exception:
            db.rollback()

    finally:

        db.close()


def worker_process(job_queue):

    print("Worker process started...")

    # Two threads inside one worker process
    with ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="AIWorker"
    ) as executor:

        while True:

            # Wait for queue signal
            queue_signal = job_queue.get()

            print(f"Worker received queue signal: {queue_signal}")

            db = SessionLocal()

            try:

                # Priority Scheduling + FCFS
                job = (
                    db.query(Job)
                    .filter(Job.status == "waiting")
                    .order_by(
                        Job.priority.asc(),
                        Job.created_at.asc(),
                        Job.job_id.asc()
                    )
                    .first()
                )

                if not job:
                    print("No waiting jobs found")
                    continue

                job_id = job.job_id
                job_type = job.job_type
                reference_id = job.reference_id
                found_reference_id = job.found_reference_id

                # Mark job as processing before dispatching
                job.status = "processing"
                job.started_at = datetime.now()

                db.commit()

                print(
                    f"Dispatching Job {job_id} | "
                    f"Priority: {job.priority} | "
                    f"Type: {job_type}"
                )

                # Submit work to a separate thread
                executor.submit(
                    process_job,
                    job_id,
                    job_type,
                    reference_id,
                    found_reference_id
                )

            except Exception as e:

                db.rollback()
                print(f"Worker dispatch error: {e}")

            finally:

                db.close()


def start_worker(job_queue):

    process = Process(
        target=worker_process,
        args=(job_queue,)
    )

    process.start()

    print(
        f"Worker process started with PID: {process.pid}"
    )

    return process
