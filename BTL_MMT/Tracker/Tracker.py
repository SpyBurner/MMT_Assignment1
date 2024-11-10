import threading

class TrackerTable():
    def __init__(self):
        pass

class TrackerResponder(threading.Thread):
    def __init__(self, sock, addr):
        threading.Thread.__init__(self, daemon=True)
        self.sock = sock
        self.addr = addr
        
    def run(self):
        #TODO Run when a peer request is received
        
        pass
    

class Tracker():
    def __init__(self):
        pass
    
    def start(self):
        print("Starting Tracker")
        



def Start():
    tracker = Tracker()
    tracker.start()

def Stat(self):
    print("Tracker Stats")
        
def List(self):
    print("List Files in Tracker")