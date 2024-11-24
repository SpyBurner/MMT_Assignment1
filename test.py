import os

absolute_path = 'D:/Documents/HCMUT/HK241/MMT/BTL1/MMT_Assignment1/BTL_MMT'

data = b''
for root, _, files in os.walk(absolute_path):
    for file in files:
        file_path = os.path.join(root, file)
        print(file_path)
        with open(file_path, 'rb') as f:
            data += f.read()

# print(data)

