import asyncio

def ensure_event_loop():
    try:
        asyncio.get_event_loop()
        print(f"Event loop Already there.")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        print(f"New Event loop Created. {loop}")