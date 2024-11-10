import argparse

def main():   
    parser = argparse.ArgumentParser(
                        prog='tracker_cli',
                        description='Interface to perform all Tracker tasks',)
    parser.add_argument('-o', type=str, choices=['start','stat', 'list'], required=True)
    
    args = parser.parse_args()
    operation = args.o
    
    if operation == 'start':
        #* STARTING TRACKER
        print("Starting Tracker")
    elif operation == 'stat':
        #* TRACKER STATS
        print("Tracker Stats")
    elif operation == 'list':
        #* LISTING FILES IN TRACKER
        print("List Files in Tracker")
    else:
        print("Invalid operation. Please use --help to see the available operations.")

if __name__ == "__main__":
    main()