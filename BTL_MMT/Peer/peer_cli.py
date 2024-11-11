import Server
import Client
import argparse

def main():   
    parser = argparse.ArgumentParser(
                        prog='Peer_cli',
                        description='Interface to perform all Peer-to-Peer Transmission tasks',)
    parser.add_argument('-o', type=str, choices=['start','upload', 'download', 'list'], required=True)
    
    # Upload task
    parser.add_argument('--filePath', type=str)
    parser.add_argument('--trackerIP', type=str, nargs='+')
    parser.add_argument('--trackerPort', type=str, nargs='+')
    
    # Download task
    parser.add_argument('--metainfo', type=str)
    
    args = parser.parse_args()
    operation = args.o
    
    filePath = args.filePath
    trackerIP = args.trackerIP
    trackerPort = args.trackerPort
    

    metainfo = args.metainfo

    
    if operation == 'start':
        #* STARTING PEER SERVER
        Server.Start()
    elif operation == 'upload':
        #* UPLOADING
        if filePath and trackerIP:
            Client.Upload(filePath, trackerIP, trackerPort)
        else:
            print("Filepath and trackerURL are required for upload operation.")
    elif operation == 'download':
        #* DOWNLOADING
        if metainfo:
            Client.Download(metainfo)
        else:
            print("Metainfo is required for download operation.")
    elif operation == 'list':
        #* LISTING FILES IN TRACKER
        Client.ListFiles()
    else:
        print("Invalid operation. Please use --help to see the available operations.")

if __name__ == "__main__":
    main()