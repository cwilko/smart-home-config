#!/usr/bin/python3
import sys
import re
import subprocess
import os
import signal
import time
import atexit

# --- Pre-fetch Configuration ---
SQUID_PROXY_HOST = '127.0.0.1'
SQUID_PROXY_PORT = '3128'
LOG_LEVEL = os.environ.get('SQUID_STORE_ID_LOG_LEVEL', 'INFO')  # Options: 'DEBUG', 'INFO', 'WARNING', 'ERROR'
LOG_FILE = '/var/log/squid/store_id_debug.log'
LOG_TO_STDERR = os.environ.get('SQUID_STORE_ID_LOG_TO_STDERR', 'False').lower() in ('true', '1', 'yes', 'on')
PREFETCH_ENABLED = os.environ.get('SQUID_STORE_ID_PREFETCH_ENABLED', 'True').lower() in ('true', '1', 'yes', 'on')
PREFETCH_HEAD_START_DELAY = float(os.environ.get('SQUID_PREFETCH_DELAY', '3.0'))  # Seconds for pre-fetch head start

# --- Signal Handler for Zombie Process Cleanup ---
def sigchld_handler(signum, frame):
    """Clean up zombie child processes when they terminate"""
    try:
        while True:
            # Non-blocking wait for any child process
            pid, status = os.waitpid(-1, os.WNOHANG)
            if pid == 0:
                # No more child processes to clean up
                break
            log_message('DEBUG', f'Cleaned up child process {pid} with status {status}')
    except OSError:
        # No child processes exist
        pass

# Register the signal handler
signal.signal(signal.SIGCHLD, sigchld_handler)

# File-based coordination for multiple instances
PREFETCH_LOCK_FILE = "/var/log/squid/squid_prefetch.lock"
PREFETCH_PID_FILE = "/var/log/squid/squid_prefetch.pid"

LOG_MAPPING = {
    'DEBUG': 1,
    'INFO': 2,
    'WARNING': 3,
    'ERROR': 4
}
CURRENT_LOG_LEVEL = LOG_MAPPING.get(LOG_LEVEL.upper(), 2)

def log_message(level, message):
    """Log message to dedicated file and optionally to stderr"""
    if LOG_MAPPING.get(level.upper(), 0) >= CURRENT_LOG_LEVEL:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        formatted_msg = f"[{timestamp}] STORE_ID {level.upper()}: {message}\n"
        
        # Always log to file
        try:
            with open(LOG_FILE, 'a') as f:
                f.write(formatted_msg)
                f.flush()
        except Exception:
            pass  # Don't let logging errors break the script
        
        # Optionally log to stdout pipe for k8s pod logs
        if LOG_TO_STDERR:
            try:
                with open('/var/log/squid/stdout_pipe', 'w') as f:
                    f.write(formatted_msg)
                    f.flush()
            except Exception:
                pass

def start_prefetch(url, store_id):
    """Start pre-fetch with atomic coordination"""
    
    # Check for existing pre-fetch of same content first (optimization)
    existing_match = is_same_content_prefetching(store_id)
    log_message('DEBUG', f"Pre-fetch exists check for {store_id}: {existing_match}")
    if existing_match:
        log_message('DEBUG', f"Pre-fetch already active for store ID: {store_id}")
        return "exists"  # Same content already prefetching, no wait needed
    
    # Atomically acquire lock (handles termination if needed)
    lock_result = acquire_prefetch_lock(store_id)
    log_message('DEBUG', f"acquire_prefetch_lock for {store_id} returned: {lock_result}")
    if lock_result:
        # We got the lock - start the actual pre-fetch process
        log_message('DEBUG', f"Starting actual pre-fetch for {store_id}")
        actual_start_prefetch(url, store_id)
        return True  # We successfully started the pre-fetch
    else:
        log_message('DEBUG', f"Failed to acquire pre-fetch lock for {store_id}")
        return False  # Another instance started it (race condition)

def is_same_content_prefetching(store_id):
    """Check if same content is already being pre-fetched"""
    try:
        log_message('DEBUG', f"Checking lock file: {PREFETCH_LOCK_FILE}")
        if os.path.exists(PREFETCH_LOCK_FILE):
            log_message('DEBUG', f"Lock file exists")
            with open(PREFETCH_LOCK_FILE, 'r') as f:
                lock_content = f.read().strip()
                log_message('DEBUG', f"Lock file content: '{lock_content}'")
                # Parse lock content: PID:FILENAME:TIMESTAMP (without rd-cache:// prefix)
                lock_data = lock_content.split(':', 2)
                log_message('DEBUG', f"Lock data parts: {lock_data}, length: {len(lock_data)}")
                if len(lock_data) >= 2:
                    existing_filename = lock_data[1]
                    # Compare with store_id after removing rd-cache:// prefix
                    store_filename = store_id.replace('rd-cache://', '')
                    log_message('DEBUG', f"Existing filename: '{existing_filename}', checking against: '{store_filename}'")
                    match = existing_filename == store_filename
                    log_message('DEBUG', f"Filenames match: {match}")
                    return match
                else:
                    log_message('DEBUG', f"Lock data has insufficient parts: {len(lock_data)}")
        else:
            log_message('DEBUG', f"Lock file does not exist")
    except (OSError, IndexError) as e:
        log_message('DEBUG', f"Exception in is_same_content_prefetching: {e}")
        pass
    log_message('DEBUG', f"Returning False from is_same_content_prefetching")
    return False

def atomic_replace_lock(old_store_id_pid, old_store_id, new_store_id):
    """Atomically replace existing lock with new one"""
    try:
        log_message('DEBUG', f"Starting atomic_replace_lock: old_store_id_pid={old_store_id_pid}, old_store_id={old_store_id}, new_store_id={new_store_id}")
        
        # Get the actual wget PID from the PID file, not the store_id script PID
        wget_pid = None
        try:
            if os.path.exists(PREFETCH_PID_FILE):
                with open(PREFETCH_PID_FILE, 'r') as f:
                    wget_pid = int(f.read().strip())
                    log_message('DEBUG', f"Found wget PID {wget_pid} in PID file")
            else:
                log_message('DEBUG', f"PID file {PREFETCH_PID_FILE} does not exist")
        except (OSError, ValueError) as e:
            log_message('DEBUG', f"Failed to read wget PID from file: {e}")
        
        # Terminate old wget process if we found it
        if wget_pid:
            try:
                # First check if process exists
                os.kill(wget_pid, 0)  # Signal 0 just checks if process exists
                log_message('DEBUG', f"Wget process {wget_pid} exists, attempting to terminate")
                
                # Now actually terminate it
                os.kill(wget_pid, signal.SIGTERM)
                log_message('INFO', f"Terminated wget PID {wget_pid} for {old_store_id}")
            except (ProcessLookupError, OSError) as e:
                log_message('DEBUG', f"Wget process {wget_pid} already gone or not found: {e}")
        else:
            log_message('DEBUG', f"No wget PID found to terminate")
        
        # Atomic lock replacement using rename
        temp_lock = f"{PREFETCH_LOCK_FILE}.{os.getpid()}.tmp"
        log_message('DEBUG', f"Creating temp lock file: {temp_lock}")
        try:
            with open(temp_lock, 'w') as f:
                # Store filename without rd-cache:// prefix
                filename = new_store_id.replace('rd-cache://', '')
                lock_data = f"{os.getpid()}:{filename}:{time.time()}"
                f.write(lock_data)
            log_message('DEBUG', f"Wrote temp lock data: {lock_data}")
            
            # Atomic rename to replace old lock
            os.rename(temp_lock, PREFETCH_LOCK_FILE)
            log_message('DEBUG', f"Successfully replaced lock file with new data")
            return True
            
        except OSError as e:
            log_message('ERROR', f"Failed to create/rename lock file: {e}")
            # Cleanup temp file and fail
            try:
                os.remove(temp_lock)
            except OSError:
                pass
            return False
            
    except Exception as e:
        log_message('ERROR', f"Unexpected error in atomic_replace_lock: {e}")
        return False

def acquire_prefetch_lock(store_id):
    """Atomically acquire lock, terminating different content if needed"""
    try:
        cleanup_stale_locks()
        
        # Try to acquire lock - handles both new and termination cases atomically
        while True:
            try:
                # Attempt atomic lock creation
                with open(PREFETCH_LOCK_FILE, 'x') as f:
                    # Store filename without rd-cache:// prefix
                    filename = store_id.replace('rd-cache://', '')
                    lock_data = f"{os.getpid()}:{filename}:{time.time()}"
                    f.write(lock_data)
                log_message('DEBUG', f"Acquired new pre-fetch lock for {store_id}")
                return True  # Successfully acquired new lock
                
            except FileExistsError:
                # Lock exists - check if it's same or different content
                try:
                    with open(PREFETCH_LOCK_FILE, 'r') as f:
                        lock_content = f.read().strip()
                        # Parse lock content: PID:FILENAME:TIMESTAMP (without rd-cache:// prefix)
                        lock_data = lock_content.split(':', 2)
                        if len(lock_data) >= 2:
                            existing_pid = int(lock_data[0])
                            existing_filename = lock_data[1]
                            # Compare filenames (both without rd-cache:// prefix)
                            store_filename = store_id.replace('rd-cache://', '')
                            
                            if existing_filename == store_filename:
                                # Same content already being pre-fetched
                                log_message('DEBUG', f"Pre-fetch lock already exists for same content: {store_id}")
                                return False
                            else:
                                # Different content - terminate and try atomic replacement
                                existing_store_id = f"rd-cache://{existing_filename}"
                                log_message('INFO', f"Switching from {existing_store_id} to {store_id}")
                                result = atomic_replace_lock(existing_pid, existing_store_id, store_id)
                                log_message('DEBUG', f"atomic_replace_lock returned: {result}")
                                return result
                        else:
                            continue  # Invalid format, retry
                                
                except (OSError, ValueError, IndexError):
                    # Corrupted lock file - remove and retry
                    try:
                        os.remove(PREFETCH_LOCK_FILE)
                        log_message('DEBUG', "Removed corrupted lock file, retrying")
                        continue  # Retry lock acquisition
                    except OSError:
                        return False
                        
    except Exception as e:
        log_message('WARNING', f"Failed to acquire lock: {e}")
        return False

def cleanup_stale_locks():
    """Clean up locks from dead processes"""
    try:
        if os.path.exists(PREFETCH_LOCK_FILE):
            with open(PREFETCH_LOCK_FILE, 'r') as f:
                lock_content = f.read().strip()
                # Parse lock content: PID:FILENAME:TIMESTAMP (without rd-cache:// prefix)
                lock_data = lock_content.split(':', 2)
                if len(lock_data) >= 3:
                    lock_pid = int(lock_data[0])
                    lock_time = float(lock_data[2])
                else:
                    return  # Invalid format
                
                # Check if process is still running
                try:
                    os.kill(lock_pid, 0)  # Check if process exists
                except ProcessLookupError:
                    # Process is dead, remove stale lock
                    os.remove(PREFETCH_LOCK_FILE)
                    log_message('DEBUG', f"Removed stale lock from dead process {lock_pid}")
                        
    except (OSError, ValueError, IndexError):
        # If we can't read the lock file, remove it
        try:
            os.remove(PREFETCH_LOCK_FILE)
        except OSError:
            pass

def actual_start_prefetch(url, store_id):
    """Actually start the pre-fetch wget process"""
    log_message('INFO', f"Starting pre-fetch for: {url} (store ID: {store_id})")
    
    # Construct wget command (proxy configured via /etc/wgetrc)
    wget_command = [
        'wget',
        '--progress=dot:giga',  # Show progress with dots (1 dot = 1MB)
        '--server-response',   # Show HTTP headers and response codes
        '--no-check-certificate',  # Skip SSL certificate verification
        '-O', '/dev/null',  # Discard output
        url
    ]
    
    log_message('DEBUG', f"Wget command: {' '.join(wget_command)}")
    
    try:
        # Create unique progress log file in squid log directory
        progress_file = f"/var/log/squid/wget_progress_{int(time.time())}_{os.getpid()}.log"
        
        # Open progress file for writing
        progress_log = open(progress_file, 'w')
        
        # Start wget process with stderr redirected to progress file
        prefetch_process = subprocess.Popen(
            wget_command, 
            preexec_fn=os.setsid,
            stdout=subprocess.DEVNULL,
            stderr=progress_log
        )
        
        # Write PID to file for tracking
        with open(PREFETCH_PID_FILE, 'w') as f:
            f.write(str(prefetch_process.pid))
        
        log_message('INFO', f"Pre-fetch started (PID: {prefetch_process.pid}) for {url} (store ID: {store_id})")
        log_message('INFO', f"Monitor progress: tail -f {progress_file}")
        
        # Note: progress_log file handle will remain open for the wget process
        
    except Exception as e:
        log_message('ERROR', f"Failed to start pre-fetch for {url}: {e}")
        # Clean up lock on failure
        try:
            os.remove(PREFETCH_LOCK_FILE)
        except OSError:
            pass

def cleanup_prefetch():
    """Cleanup function called on exit - removes lock files and terminates processes"""
    try:
        # Terminate active pre-fetch process if we own it
        if os.path.exists(PREFETCH_PID_FILE):
            try:
                with open(PREFETCH_PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                    
                # Try to terminate the process (kill specific PID, not process group to avoid killing Squid)
                try:
                    os.kill(pid, signal.SIGTERM)
                    log_message('DEBUG', f'Terminated pre-fetch process {pid} on exit')
                except (ProcessLookupError, OSError):
                    pass  # Process already gone
                    
            except (OSError, ValueError):
                pass
                
        # Clean up lock and PID files
        for file_path in [PREFETCH_LOCK_FILE, PREFETCH_PID_FILE]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass
                
    except Exception:
        pass  # Don't let cleanup errors break the script

# Register cleanup function
atexit.register(cleanup_prefetch)

def generate_store_id(url, is_prefetch_request=False):
    """Generate normalized store ID for caching"""
    try:
        # Pattern for Real-Debrid downloads
        # https://XX-X.download.real-debrid.com/d/TOKEN/filename.ext
        rd_pattern = r'https://\d+-\d+\.download\.real-debrid\.com/d/([^/]+)/(.+)'
        log_message('DEBUG', f'Testing URL against pattern: {rd_pattern}')
        
        rd_match = re.match(rd_pattern, url)
        log_message('DEBUG', f'Regex match result: {rd_match}')
        
        if rd_match:
            filename = rd_match.group(2)
            log_message('DEBUG', f'Extracted filename: {filename}')
            
            # Create normalized cache key based on filename first
            # This makes same file cache together regardless of server
            store_id = f"rd-cache://{filename}"
            log_message('DEBUG', f'Generated store_id: {store_id}')
            
            # Handle pre-fetch coordination for Real-Debrid URLs (only for client requests, not pre-fetch requests)
            if PREFETCH_ENABLED and not is_prefetch_request:
                try:
                    # Try to start pre-fetch (handles existing/new/race conditions)
                    prefetch_result = start_prefetch(url, store_id)
                    
                    if prefetch_result == "exists":
                        log_message('INFO', f'Pre-fetch already active for same content, no wait needed')
                    elif prefetch_result:
                        log_message('INFO', f'Pre-fetch started by this instance, waiting {PREFETCH_HEAD_START_DELAY}s for head start')
                        time.sleep(PREFETCH_HEAD_START_DELAY)
                        log_message('DEBUG', 'Pre-fetch head start delay completed')
                    else:
                        log_message('INFO', f'Pre-fetch handled by another instance, waiting {PREFETCH_HEAD_START_DELAY}s for head start')
                        time.sleep(PREFETCH_HEAD_START_DELAY)
                        log_message('DEBUG', 'Pre-fetch head start delay completed')
                        
                except Exception as e:
                    log_message('WARNING', f'Failed in pre-fetch coordination: {e}')
                    # Continue anyway - store ID generation should not fail due to pre-fetch issues
            elif is_prefetch_request:
                log_message('DEBUG', 'Skipping pre-fetch coordination for pre-fetch request itself')
            
            return store_id
        
        log_message('DEBUG', 'No regex match, returning original URL')
        # Return original URL for everything else
        return url
        
    except Exception as e:
        log_message('ERROR', f'Exception in generate_store_id: {e}')
        return url

def main():
    # Simple startup test - write to a basic file to confirm script runs
    try:
        with open('/tmp/store_id_startup.txt', 'w') as f:
            f.write(f"Script started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    except Exception:
        pass
    
    # Test logging function
    log_message('INFO', 'Store ID script started')
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                log_message('DEBUG', 'No more input, breaking')
                break
                
            line = line.strip()
            log_message('DEBUG', f'Received input: "{line}"')
            
            if not line:
                log_message('DEBUG', 'Empty line, returning ERR')
                print("ERR")
                sys.stdout.flush()
                continue
            
            # Input format: URL IP/- username method
            parts = line.split()
            log_message('DEBUG', f'Split into {len(parts)} parts: {parts}')
            
            if len(parts) >= 1:
                url = parts[0]
                # Extract client IP from input format: URL IP/FQDN username method
                client_ip = parts[1].split('/')[0] if len(parts) > 1 else '-'
                
                # Detect if this is a pre-fetch request (from localhost) vs media client
                is_prefetch_request = (client_ip == '127.0.0.1')
                
                log_message('DEBUG', f'Processing URL: {url}, Client IP: {client_ip}, Is prefetch: {is_prefetch_request}')
                store_id = generate_store_id(url, is_prefetch_request)
                log_message('DEBUG', f'Generated store_id: {store_id}')
                
                # Squid expects: "OK store-id=<store_id>" format
                if store_id != url:
                    # We have a custom store ID
                    log_message('INFO', f'Returning custom store_id for {url}: {store_id}')
                    print(f"OK store-id={store_id}")
                else:
                    # Use original URL (no custom store ID)
                    log_message('DEBUG', f'No custom store_id for {url}, returning ERR')
                    print("ERR")
                sys.stdout.flush()
            else:
                log_message('DEBUG', 'Invalid input format, returning ERR')
                print("ERR")
                sys.stdout.flush()
                
        except KeyboardInterrupt:
            break
        except Exception:
            print("ERR")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
