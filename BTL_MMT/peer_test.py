import shutil
import os
import time

# Define the source and destination directories
source_dir = './Peer'
destination_dir = './Peer_test' + str(time.time())

# Copy the Peer folder into Peer_test (overwrite)
if os.path.exists(destination_dir):
    shutil.rmtree(destination_dir)
shutil.copytree(source_dir, destination_dir)

os.chdir(destination_dir)

try: 
    # Run the Server
    os.system('python main.py')
except (Exception , KeyboardInterrupt) as e:
    print('Error: ', e)

os.chdir('..')
shutil.rmtree(destination_dir)
