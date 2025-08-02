"""
Configuration for TSI device IDs.
"""

def get_tsi_devices():
    """
    Returns a list of production TSI device IDs.
    
    Update this list with the actual device_id values from your TSI account.
    If the list is empty, the script will fetch data for all devices in the account.
    """
    # TODO: Replace placeholder IDs with your actual TSI device IDs
    # Example:
    # return [
    #     "aBcDeFgHiJkLmNoPqRsTuV",
    #     "zYxWvUtSrQpOnMlKjIhGfEd",
    # ]
    device_ids = [
        # "placeholder_device_1", # Replace with real ID
        # "placeholder_device_2", # Replace with real ID
    ]
    
    # If no specific devices are listed, the script will process all devices found.
    # To avoid processing all devices, ensure at least one ID is in the list.
    if not device_ids:
        print("✅ No specific TSI devices configured. The script will attempt to process all devices found in the account.")
    
    return device_ids
