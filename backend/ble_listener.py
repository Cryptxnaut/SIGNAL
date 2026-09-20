HW_AVAILABLE = False
try:
    import bleak
    HW_AVAILABLE = True
except ImportError:
    pass


async def get_hardware_status():
    return {"nrf_connected": False, "nrf_data": None}


async def start_ble_listener():
    pass  # stub


async def get_live_data_queue():
    return None
