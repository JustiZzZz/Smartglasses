import asyncio
from bleak import BleakClient, BleakScanner
import logging

class BLEAudioHandler:
    def __init__(self, config):
        self.config = config
        self.client = None
        self.characteristic = None
        self.connected = False

    async def connect(self):
        try:
            logging.info("search Bluetooth devices...")
            devices = await BleakScanner.discover()
            for d in devices:
                logging.info(f"yes device: {d.name} ({d.address})")
            
            logging.info(f"search device: {self.config['bluetooth']['device_name']}")
            device = await BleakScanner.find_device_by_name(self.config['bluetooth']['device_name'])
            
            if not device:
                raise Exception("no device")
                
            logging.info(f"Try to connect...")
            self.client = BleakClient(device)
            await self.client.connect()
            self.connected = True
            self.characteristic = self.config['bluetooth']['characteristic_uuid']
            logging.info("BLE yes")
        except Exception as e:
            logging.error(f"Error BLE: {e}")
            self.connected = False

    async def disconnect(self):
        if self.client:
            try:
                await self.client.disconnect()
                self.connected = False
                logging.info("BLE NO")
            except Exception as e:
                logging.error(f"Error unload BLE: {e}")

    async def send_audio(self, audio_data):
        if not self.connected:
            await self.connect()
        try:
            await self.client.write_gatt_char(self.characteristic, audio_data)
        except Exception as e:
            logging.error(f"Error audio: {e}")
            self.connected = False