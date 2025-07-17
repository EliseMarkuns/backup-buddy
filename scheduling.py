import json
import os
import time
from datetime import datetime, timedelta

CONFIG_FILE = "schedule_state.json"

# Each job: {"id": str, "source": str, "destination": str, "interval": str, "time": str, "n_days": int|None, "last_run": str|None}

# Load all scheduled backup jobs from the config file
def load_jobs():
    if not os.path.exists(CONFIG_FILE):
        return []
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

# Save the list of jobs to the config file
def save_jobs(jobs):
    with open(CONFIG_FILE, "w") as f:
        json.dump(jobs, f, indent=4)

# Add a new backup job or update an existing one (by name)
def add_job(name, source, destination, interval, time_str, n_days=None):
    jobs = load_jobs()
    job_id = name  # Use name as unique identifier
    job = {
        "id": job_id,  # Unique identifier for the job (name)
        "name": name,  # Job name
        "source": source,  # Source folder path
        "destination": destination,  # Destination folder path
        "interval": interval,  # Schedule interval (Daily, Weekly, Every N Days)
        "time": time_str,  # Time of day to run (HH:MM)
        "n_days": n_days,  # N for 'Every N Days', else None
        "last_run": None  # Last time this job ran
        # No status field persisted
    }
    # Remove any existing job with the same id (name)
    jobs = [j for j in jobs if j["id"] != job_id]
    jobs.append(job)
    save_jobs(jobs)

# Remove a backup job by its id
def remove_job(job_id):
    jobs = load_jobs()
    jobs = [j for j in jobs if j["id"] != job_id]
    save_jobs(jobs)

# Get the list of all jobs
def get_jobs():
    return load_jobs()

# Update the status (idle, running, paused, stopped) of a job (in-memory only)
def update_job_status(job_id, status):
    # This function is now a no-op for persistence; status is managed in-memory in the GUI
    pass

# Update the last_run time of a job to now
def update_job_last_run(job_id):
    jobs = load_jobs()
    for job in jobs:
        if job["id"] == job_id:
            job["last_run"] = datetime.now().isoformat()
    save_jobs(jobs)

# Calculate the next scheduled run time for a job
def get_next_run_time(job):
    """
    Returns the next scheduled run time for a job, based on its interval, time, and last_run.
    If the job has never run, schedule for the next occurrence after now.
    If the job has run, schedule for the next occurrence after last_run.
    """
    interval = job.get("interval")
    time_str = job.get("time")
    n_days = job.get("n_days")
    last_run = job.get("last_run")
    now = datetime.now()
    hour, minute = map(int, time_str.split(":"))
    # Determine the base time to calculate from
    if last_run:
        base = datetime.fromisoformat(last_run)
    else:
        # If never run, check if scheduled time for today is in the past
        today_scheduled = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if today_scheduled <= now:
            return today_scheduled  # Run immediately
        else:
            base = now
    if interval == "Daily":
        next_run = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_run <= base:
            next_run += timedelta(days=1)
    elif interval == "Weekly":
        next_run = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        weekday = next_run.weekday()
        days_ahead = (6 - weekday) % 7
        if days_ahead == 0 and next_run <= base:
            days_ahead = 7
        next_run += timedelta(days=days_ahead)
    elif interval == "Every N Days" and n_days:
        if last_run:
            last_run_dt = datetime.fromisoformat(last_run)
            next_run = last_run_dt + timedelta(days=int(n_days))
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= last_run_dt:
                next_run += timedelta(days=int(n_days))
        else:
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                return next_run  # Run immediately
            else:
                next_run += timedelta(days=int(n_days))
    else:
        return None  # Unknown interval
    return next_run
