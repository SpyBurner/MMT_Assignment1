class RequestEvent:
    STARTED = "started"
    STOPPED = "stopped"
    COMPLETED = "completed"

#? Build and return a dictionary object that represents a tracker get request
#? Can be later bencoded and sent to the tracker
class TrackerRequestBuilder():
    def __init__(self):
        self.info_hash = None
        self.peer_id = None
        self.port = None
        self.uploaded = None
        self.downloaded = None
        self.left = None
        self.event = None
        self.tracker_id = None

    def SetInfoHash(self, info_hash):
        self.info_hash = info_hash
        return self
    
    def SetPeerID(self, peer_id):
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
    
    def SetTrackerID(self, tracker_id):
        self.tracker_id = tracker_id
        return self
    
    def Build(self):
        # return {
        #     "info_hash": self.info_hash,
        #     "peer_id": self.peer_id,
        #     "port": self.port,
        #     "uploaded": self.uploaded,
        #     "downloaded": self.downloaded,
        #     "left": self.left,
        #     "event": self.event,
        #     "tracker_id": self.tracker_id,
        #     "compact": self.compact
        # }
        return {key: value for key, value in self.__dict__.items() if value is not None}

class TrackerResponseBuilder():
    def __init__(self):
        self.failure_reason = None
        self.warning_message = None
        self.tracker_id = None
        self.peers = None
    
    def SetFailureReason(self, failure_reason):
        self.failure_reason = failure_reason
        return self
    
    def SetWarningMessage(self, warning_message):
        self.warning_message = warning_message
        return self

    def SetTrackerId(self, tracker_id):
        self.tracker_id = tracker_id
        return self
    
    def SetPeers(self, peers):
        self.peers = peers
        return self
    
    def Build(self):
        # return {
        #     "failure reason": self.failure_reason,
        #     "warning message": self.warning_message,
        #     "tracker id": self.tracker_id,
        #     "peers": self.peers
        # }
        return {key: value for key, value in self.__dict__.items() if value is not None}