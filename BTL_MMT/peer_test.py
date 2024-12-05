import shutil
import os

# Define the source and destination directories
source_dir = './Peer'
destination_dir = './Peer_test'

# Copy the Peer folder into Peer_test (overwrite)
if os.path.exists(destination_dir):
    shutil.rmtree(destination_dir)
shutil.copytree(source_dir, destination_dir)

# Run the Server
os.system('python ./Peer_test/main.py')

shutil.rmtree(destination_dir)
