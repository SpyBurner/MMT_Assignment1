import socket
import time
import argparse
import bcoding

from threading import Thread

def new_connection(tid, host, port):
    print('Thread ID {:d} connecting to {}:{:d}'.format(tid, host, port))

    client_socket = socket.socket()
    client_socket.connect((host, port))
    
    #request = fhasdlkjfhalsdfj.Build()
    #request_encode = bcoding.bencode(request)
    
    sample_dict = {
        'info': {
            'piece length': 256,
            'pieces': b'1234567890abcdef',
            'name': 'sample.txt',
            'length': 1024
        },
        'announce_list': [
            {'ip': ' ', 'port': 22236}
        ]
    }
    
    request_encode = bcoding.bencode(sample_dict)        
    client_socket.send(request_encode)


def connect_server(threadnum, host, port):

    # Create "threadnum" of Thread to parallelly connnect
    threads = [Thread(target=new_connection, args=(i, host, port)) for i in range(0,threadnum)]
    [t.start() for t in threads]

    # TODO: wait for all threads to finish
    [t.join() for t in threads]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                        prog='Client',
                        description='Connect to pre-declard server',
                        epilog='!!!It requires the server is running and listening!!!')
    parser.add_argument('--server-ip')
    parser.add_argument('--server-port', type=int)
    parser.add_argument('--client-num', type=int)
    args = parser.parse_args()
    host = args.server_ip
    port = args.server_port
    cnum = args.client_num
    connect_server(cnum, host, port)
