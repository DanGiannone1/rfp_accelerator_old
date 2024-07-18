from threading import Lock
import threading 

# Global Variables
test_counter = 0
test_counter_lock = Lock()
status_updates = []
status_lock = Lock()
stop_event = threading.Event()
# RDC 
thread = None

#New function to clear status updates
def clear_status_updates():
    global status_updates
    with status_lock:
        status_updates.clear()

def add_status_update(message):
    global status_updates
    with status_lock:
        status_updates.append(message)
