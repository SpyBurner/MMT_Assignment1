import threading


#TODO Implement sending requests to the tracker.
#TODO Request format is defined in the project description.
class ClientUploader(threading.Thread):
    def __init__(self, filePath, trackerURL):
        threading.Thread.__init__(self)
        self.filePath = None
        self.trackerURL = None

    def run(self):
        #TODO Generate metainfo from the file.
        #TODO Put the metainfo in the metainfo folder.
        #TODO Start a ServerRegularAnouncer thread for the file
        #TODO Send a request to the tracker with the metainfo.

        print("Implement uploading logic here.")

class ClientDownloader(threading.Thread):
    def __init__(self, metainfo):
        threading.Thread.__init__(self)
        self.metainfo = None

    def start(self):
        print("Implement downloading logic here.")

class ClientLister(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        print("Implement listing logic here.")


#! Create the right type of thread and start it.
def Upload(filePath, trackerURL):
    print("Uploading file: ", filePath, " to tracker: ", trackerURL)
    uploader = ClientUploader(filePath, trackerURL)
    uploader.start()

def Download(metainfo):
    print("Downloading file with metainfo: ", metainfo)
    downloader = ClientDownloader(metainfo)
    downloader.start()
    
def ListFiles():
    print("Listing files.")
    lister = ClientLister()
    lister.start()
