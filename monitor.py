#!/usr/bin/env python3
"""
Worker process monitor script for the Python backend server.
This script checks if the Gunicorn workers are running properly and restarts them if needed.
"""

import os
import sys
import time
import subprocess
import logging
import signal
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("worker_monitor")

GUNICORN_MASTER_PROCESS_NAME = "gunicorn: master"
CHECK_INTERVAL = 30  # seconds
RESTART_DELAY = 5  # seconds
MAX_MEMORY_PERCENT = 80  # Restart if memory usage exceeds this percentage
MAX_RESTARTS = 5  # Maximum number of restarts before giving up

class WorkerMonitor:
    def __init__(self):
        self.server_start_time = time.time()
        self.restart_count = 0
        self.last_restart_time = 0
        
    def find_gunicorn_processes(self):
        """Find all gunicorn processes"""
        master_pid = None
        worker_pids = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Check for the master process
                if "gunicorn: master" in " ".join(proc.info['cmdline'] or []):
                    master_pid = proc.info['pid']
                # Check for worker processes
                elif "gunicorn: worker" in " ".join(proc.info['cmdline'] or []):
                    worker_pids.append(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        return master_pid, worker_pids
    
    def check_worker_health(self):
        """Check if workers are healthy"""
        try:
            master_pid, worker_pids = self.find_gunicorn_processes()
            
            if not master_pid:
                logger.warning("Gunicorn master process not found!")
                return False
                
            if not worker_pids:
                logger.warning("No gunicorn worker processes found!")
                return False
                
            logger.info(f"Found gunicorn master (PID: {master_pid}) and {len(worker_pids)} workers")
            
            # Check memory usage of workers
            for pid in worker_pids:
                try:
                    worker = psutil.Process(pid)
                    memory_percent = worker.memory_percent()
                    
                    if memory_percent > MAX_MEMORY_PERCENT:
                        logger.warning(f"Worker (PID: {pid}) using excessive memory: {memory_percent:.1f}%")
                        return False
                        
                    # Check if the worker is responding (simplified check - just see if it's running)
                    if worker.status() in ['zombie', 'dead']:
                        logger.warning(f"Worker (PID: {pid}) is in a bad state: {worker.status()}")
                        return False
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    logger.warning(f"Worker (PID: {pid}) no longer accessible")
                    return False
            
            # All checks passed
            return True
            
        except Exception as e:
            logger.error(f"Error checking worker health: {str(e)}")
            return False
    
    def restart_server(self):
        """Restart the server gracefully"""
        if self.restart_count >= MAX_RESTARTS:
            logger.error(f"Maximum restart count ({MAX_RESTARTS}) reached. Giving up.")
            return False
            
        # Check if we've restarted recently (within 5 minutes)
        if time.time() - self.last_restart_time < 300:
            self.restart_count += 1
            logger.warning(f"Restarting frequently - attempt {self.restart_count} of {MAX_RESTARTS}")
        else:
            # Reset restart count if it's been a while
            self.restart_count = 1
            
        self.last_restart_time = time.time()
        
        # Find the current server process
        master_pid, _ = self.find_gunicorn_processes()
        
        if master_pid:
            try:
                # Send SIGTERM to master process (graceful shutdown)
                logger.info(f"Sending SIGTERM to master process {master_pid}")
                os.kill(master_pid, signal.SIGTERM)
                
                # Wait for processes to terminate
                logger.info("Waiting for processes to terminate...")
                time.sleep(RESTART_DELAY)
                
            except ProcessLookupError:
                logger.warning(f"Process {master_pid} not found when attempting to terminate")
        
        # Start a new server instance
        logger.info("Starting new server instance...")
        try:
            script_path = "/app/start_server.sh"
            if not os.path.exists(script_path):
                script_path = "./start_server.sh"
                
            # Run the server in the background
            subprocess.Popen(script_path, shell=True)
            logger.info("New server instance started")
            
            # Wait for it to initialize
            time.sleep(10)
            return True
            
        except Exception as e:
            logger.error(f"Failed to start new server instance: {str(e)}")
            return False
    
    def run(self):
        """Main monitoring loop"""
        logger.info("Worker monitor started")
        
        while True:
            try:
                logger.info("Checking worker health...")
                if not self.check_worker_health():
                    logger.warning("Workers not healthy, attempting restart")
                    if not self.restart_server():
                        logger.error("Failed to restart server. Monitoring will continue.")
                
                # Sleep before next check
                logger.info(f"Sleeping for {CHECK_INTERVAL} seconds")
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("Monitor shutting down")
                break
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(CHECK_INTERVAL)  # Sleep even if there's an error

if __name__ == "__main__":
    monitor = WorkerMonitor()
    monitor.run() 