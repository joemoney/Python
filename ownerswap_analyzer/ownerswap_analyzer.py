import os
import re
import csv

#define constant states of owner swap sequence
STATE_WAITING_FOR_OWNER_PAIRING = 0
STATE_OWNER_PAIRING_STARTED = 1
STATE_OWNER_PAIRING_COMPLETED = 2
STATE_OWNER_SWAP_INITIATED = 3
STATE_OLD_OWNER_DISCONNECTED = 4
STATE_OWNER_SWAP_COMPLETED = 5
STATE_BOND_DELETED_STILL_CONNECTED = 6
STATE_NEW_OWNER_DISCONNECTED_BOND_STILL_EXIST = 7
STATE_OWNER_SWAP_SUCCESS = 8

#define state machine events
EVENT_OWNER_PAIRING_STARTED = 0
EVENT_OWNER_PAIRING_COMPLETED = 1
EVENT_OLD_OWNER_DISCONNECTED = 2
EVENT_BOND_DELETION = 3
EVENT_BOND_DELETION_FAILED = 4
EVENT_NEW_OWNER_DISCONNECTED = 5


# search for all .log files in the current directory and its subdirectories
def find_log_files(directory: str):
    log_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.log'):
                log_files.append(os.path.join(root, file))
    return log_files

# process analyze state machine for owner swap sequence based on events
def owner_swap_state_machine(events: int, current_state: int):
    """Returns (new_state, status_message)"""
    
    if current_state == STATE_WAITING_FOR_OWNER_PAIRING:
        if events == EVENT_OWNER_PAIRING_STARTED:
            return (STATE_OWNER_PAIRING_STARTED, "OK")
        else:
            return (current_state, "Owner Pairing was not started")
    
    elif current_state == STATE_OWNER_PAIRING_STARTED:
        if events == EVENT_OWNER_PAIRING_COMPLETED:
            return (STATE_OWNER_PAIRING_COMPLETED, "OK")
        else:
            return (current_state, "Owner Pairing was not completed")
    
    elif current_state == STATE_OWNER_PAIRING_COMPLETED:
        if events == EVENT_OWNER_PAIRING_STARTED:
            return (STATE_OWNER_SWAP_INITIATED, "OK")
        else:
            return (current_state, "Owner Swap was not initiated")
    
    elif current_state == STATE_OWNER_SWAP_INITIATED:
        if events == EVENT_OLD_OWNER_DISCONNECTED:
            return (STATE_OLD_OWNER_DISCONNECTED, "OK")
        else:
            return (current_state, "Old Owner did not disconnect")
    
    elif current_state == STATE_OLD_OWNER_DISCONNECTED:
        if events == EVENT_OWNER_PAIRING_COMPLETED:
            return (STATE_OWNER_SWAP_COMPLETED, "OK")
        else:
            return (current_state, "Owner Swap was not completed")
    
    elif current_state == STATE_OWNER_SWAP_COMPLETED:
        if events == EVENT_BOND_DELETION:
            return (STATE_BOND_DELETED_STILL_CONNECTED, "OK")
        elif events == EVENT_BOND_DELETION_FAILED:
            return (current_state, "Bond Deletion failed")
        elif events == EVENT_NEW_OWNER_DISCONNECTED:
            return (STATE_NEW_OWNER_DISCONNECTED_BOND_STILL_EXIST, "OK")
        else:
            return (current_state, "Bond Deletion did not occur before disconnecting")
    
    elif current_state == STATE_BOND_DELETED_STILL_CONNECTED:
        if events == EVENT_NEW_OWNER_DISCONNECTED:
            return (STATE_OWNER_SWAP_SUCCESS, "OK")
        elif events == EVENT_OLD_OWNER_DISCONNECTED:
            return (current_state, "OK")
        else:
            return (current_state, "New Owner did not disconnect")
    
    elif current_state == STATE_NEW_OWNER_DISCONNECTED_BOND_STILL_EXIST:
        if events == EVENT_BOND_DELETION:
            return (STATE_OWNER_SWAP_SUCCESS, "OK")
        elif events == EVENT_BOND_DELETION_FAILED:
            return (current_state, "Bond Deletion failed")
        elif events == EVENT_OLD_OWNER_DISCONNECTED:
            return (current_state, "OK")
        else:
            return  (current_state, "Bond Deletion did no occur after disconnecting")
        
    elif current_state == STATE_OWNER_SWAP_SUCCESS:
        return (current_state, "OK")
    
    else:
        return (current_state, f"Unknown state: {current_state}")



# analyze the log file for owner swap sequence

def analyze_log_file(file_path: str, report_file_path: str):
    owner_swap_state = STATE_WAITING_FOR_OWNER_PAIRING
    result = "OK"  # default result in case no events are matched

    try:
        # Use UTF-8 with replacement to avoid crashes on bad encodings
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            for line in file:
                match_found = True

                if re.search(r'Owner Pairing Started', line):
                    owner_swap_state, result = owner_swap_state_machine(EVENT_OWNER_PAIRING_STARTED, owner_swap_state)
                elif re.search(r'Owner Pairing Complete!', line):
                    owner_swap_state, result = owner_swap_state_machine(EVENT_OWNER_PAIRING_COMPLETED, owner_swap_state)
                elif re.search(r'Link Terminated Received, link 0x00', line):
                    owner_swap_state, result = owner_swap_state_machine(EVENT_OLD_OWNER_DISCONNECTED, owner_swap_state)
                elif re.search(r'BLE Cloud Event: Bond Deletion - Deletion Type: 02 \| Status: 00', line):
                    owner_swap_state, result = owner_swap_state_machine(EVENT_BOND_DELETION, owner_swap_state)
                elif re.search(r'BLE Cloud Event: Bond Deletion - Deletion Type: 02 \| Status:', line):
                    owner_swap_state, result = owner_swap_state_machine(EVENT_BOND_DELETION_FAILED, owner_swap_state)
                elif re.search(r'Link Terminated Received, link 0x01', line):
                    owner_swap_state, result = owner_swap_state_machine(EVENT_NEW_OWNER_DISCONNECTED, owner_swap_state)
                else:
                    match_found = False

                if match_found:
                    if result != "OK":
                        # Early stop on failure
                        break
                    else:
                        continue

        # Write result to the central CSV in the cwd
        with open(report_file_path, 'a', newline='', encoding='utf-8') as report_file:
            writer = csv.writer(report_file)
            if owner_swap_state != STATE_OWNER_SWAP_SUCCESS or result != "OK":
                writer.writerow([os.path.basename(file_path), "FAILED", owner_swap_state, result])
            else:
                writer.writerow([os.path.basename(file_path), "PASSED", owner_swap_state, result])

    except Exception as e:
        # In case of crash, still log that this file failed
        with open(report_file_path, 'a', newline='', encoding='utf-8') as report_file:
            writer = csv.writer(report_file)
            writer.writerow([os.path.basename(file_path), "FAILED", "EXCEPTION", str(e)])

        

def main():
    # find all log files in the current directory and its subdirectories
    log_files = find_log_files(os.getcwd())
    
    if not log_files:
        print("No log files found in the current directory and its subdirectories.")
        return

    #if analysis_report.csv exists, delete it
    report_file_path = os.path.join(os.getcwd(), "analysis_report.csv")
    if os.path.exists(report_file_path):
        os.remove(report_file_path)

     # Optional: write CSV header
    with open(report_file_path, 'w', newline='', encoding='utf-8') as report_file:
        writer = csv.writer(report_file)
        writer.writerow(["file", "status", "final_state", "result"])

    # analyze each log file
    for i, log_file in enumerate(log_files, start=1):
        print(f"Analyzing {i}/{len(log_files)}: {os.path.basename(log_file)}")
        analyze_log_file(log_file, report_file_path)


    print("\nOwner Swap Analysis Complete. Check analysis_report.csv for results.")


######################################################################
# run the main function
######################################################################
if __name__ == '__main__':
    main()