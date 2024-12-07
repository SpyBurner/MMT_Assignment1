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

    def set_info_hash(self, info_hash):
        self.info_hash = info_hash
        return self
    
    def set_peer_id(self, peer_id):
        self.peer_id = peer_id
        return self
    
    def set_port(self, port):
        self.port = port
        return self
    
    # used
    def set_uploaded(self, uploaded):
        self.uploaded = uploaded
        return self
    
    # unused
    def set_downloaded(self, downloaded):
        self.downloaded = downloaded
        return self
    
    # unused
    def set_left(self, left):
        self.left = left
        return self
    
    def set_event(self, event):
        self.event = event
        return self
    
    def set_tracker_id(self, tracker_id):
        self.tracker_id = tracker_id
        return self
    
    def build(self):
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
    
    def set_failure_reason(self, failure_reason):
        self.failure_reason = failure_reason
        return self
    
    # unused
    def set_warning_message(self, warning_message):
        self.warning_message = warning_message
        return self

    def set_tracker_id(self, tracker_id):
        self.tracker_id = tracker_id
        return self
    
    def set_peers(self, peers):
        self.peers = peers
        return self
    
    def build(self):
        # return {
        #     "failure reason": self.failure_reason,
        #     "warning message": self.warning_message,
        #     "tracker id": self.tracker_id,
        #     "peers": self.peers
        # }
        return {key: value for key, value in self.__dict__.items() if value is not None}