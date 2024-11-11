class TrackerRequestEvent:
    STARTED = "started"
    STOPPED = "stopped"
    COMPLETED = "completed"

#? Build and return a dictionary object that represents a tracker get request
#? Can be later bencoded and sent to the tracker
class TrackerRequestBuilder():
    def __init__(self):
        self.info_hash = None
        self.peer_id = None
        self.peer_ip = None
        self.port = None
        self.uploaded = None
        self.downloaded = None
        self.left = None
        self.event = None
        self.tracker_id = None
        
        self.compact = True
        pass

    def SetInfoHash(self, info_hash):
        self.info_hash = info_hash
        return self
    
    def SetPeerId(self, peer_id):
        self.peer_id = peer_id
        return self

    def SetPeerId(self, peer_id):
        self.peer_id = peer_id
        return self
    
    def SetPort(self, port):
        self.port = port
        return self
    
    def SetUploaded(self, uploaded):
        self.uploaded = uploaded
        return self
    
    def SetDownloaded(self, downloaded):
        self.downloaded = downloaded
        return self

    def SetLeft(self, left):
        self.left = left
        return self
    
    def SetEvent(self, event):
        self.event = event
        return self

    def SetTrackerId(self, tracker_id):
        self.tracker_id = tracker_id
        return self
    
    def SetCompact(self, compact):
        self.compact = compact
        return self
    
    def Build(self):
        return {
            "info_hash": self.info_hash,
            "peer_id": self.peer_id,
            "port": self.port,
            "uploaded": self.uploaded,
            "downloaded": self.downloaded,
            "left": self.left,
            "event": self.event,
            "tracker_id": self.tracker_id,
            "compact": self.compact
        }

class TrackerResponseBuilder():
    def __init__(self):
        self.interval = None
        self.peers = None
        self.complete = None
        self.incomplete = None
        self.tracker_id = None
        
        self.compact = True
        pass

    def SetInterval(self, interval):
        self.interval = interval
        return self
    
    def SetPeers(self, peers):
        self.peers = peers
        return self
    
    def SetComplete(self, complete):
        self.complete = complete
        return self
    
    def SetIncomplete(self, incomplete):
        self.incomplete = incomplete
        return self
    
    def SetTrackerId(self, tracker_id):
        self.tracker_id = tracker_id
        return self
    
    def SetCompact(self, compact):
        self.compact = compact
        return self
    
    def Build(self):
        return {
            "interval": self.interval,
            "peers": self.peers,
            "complete": self.complete,
            "incomplete": self.incomplete,
            "tracker_id": self.tracker_id,
            "compact": self.compact
        }