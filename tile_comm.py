import serial
import serial.tools.list_ports
import time
import threading
from typing import Optional, Tuple, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArduinoTileController:
    """Controller for Arduino tile communication via serial port."""
    
    def __init__(self, baud_rate: int = 9600, timeout: float = 1.0, auto_reconnect: bool = True):
        """
        Initialize the Arduino tile controller.
        
        Args:
            baud_rate: Serial communication baud rate (default: 9600)
            timeout: Serial timeout in seconds (default: 1.0)
            auto_reconnect: Whether to automatically reconnect on connection loss (default: True)
        """
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.auto_reconnect = auto_reconnect
        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
        self.reconnect_thread: Optional[threading.Thread] = None
        self.should_stop = False
        
        # Latest pressed tile data
        self.latest_pressed_tile: Optional[Tuple[int, int]] = None
        self.tile_lock = threading.Lock()
        
    def find_arduino_port(self) -> Optional[str]:
        """
        Find the Arduino port automatically.
        
        Returns:
            Port name if found, None otherwise
        """
        ports = serial.tools.list_ports.comports()
        for port in ports:
            # Common Arduino identifiers
            if any(identifier in port.description.lower() for identifier in 
                   ['arduino', 'usb serial', 'ch340', 'cp210x', 'ftdi']):
                logger.info(f"Found Arduino on port: {port.device}")
                return port.device
        return None
    
    def connect(self, port: Optional[str] = None) -> bool:
        """
        Connect to the Arduino.
        
        Args:
            port: Serial port name. If None, will try to auto-detect.
            
        Returns:
            True if connection successful, False otherwise
        """
        if self.is_connected:
            logger.warning("Already connected to Arduino")
            return True
            
        if port is None:
            port = self.find_arduino_port()
            if port is None:
                logger.error("No Arduino port found")
                return False
        
        try:
            self.serial_connection = serial.Serial(
                port=port,
                baudrate=self.baud_rate,
                timeout=self.timeout
            )
            
            # Wait a moment for Arduino to reset
            time.sleep(2)
            
            if self.serial_connection.is_open:
                self.is_connected = True
                logger.info(f"Successfully connected to Arduino on {port}")
                
                # Start listening thread
                self.start_listening()
                return True
            else:
                logger.error("Failed to open serial connection")
                return False
                
        except serial.SerialException as e:
            logger.error(f"Serial connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the Arduino."""
        self.should_stop = True
        self.is_connected = False
        
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            self.reconnect_thread.join(timeout=2.0)
        
        if self.serial_connection and self.serial_connection.is_open:
            try:
                self.serial_connection.close()
                logger.info("Disconnected from Arduino")
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
    
    def start_listening(self):
        """Start the listening thread for incoming messages."""
        self.reconnect_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.reconnect_thread.start()
    
    def _listen_loop(self):
        """Main listening loop for Arduino messages."""
        while not self.should_stop:
            if not self.is_connected or not self.serial_connection:
                if self.auto_reconnect:
                    logger.info("Attempting to reconnect...")
                    time.sleep(2)
                    self.connect()
                else:
                    break
                continue
            
            try:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8').strip()
                    if line:
                        self._process_message(line)
                        
            except serial.SerialException as e:
                logger.error(f"Serial error in listening loop: {e}")
                self.is_connected = False
                if not self.auto_reconnect:
                    break
            except Exception as e:
                logger.error(f"Unexpected error in listening loop: {e}")
                time.sleep(0.1)
    
    def _process_message(self, message: str):
        """
        Process incoming messages from Arduino.
        
        Args:
            message: Raw message string from Arduino
        """
        try:
            parts = message.split()
            if len(parts) >= 3 and parts[0].lower() == "pressed":
                row = int(parts[1])
                col = int(parts[2])
                
                with self.tile_lock:
                    self.latest_pressed_tile = (row, col)
                
                logger.debug(f"Tile pressed: ({row}, {col})")
                
        except (ValueError, IndexError) as e:
            logger.warning(f"Invalid message format: {message} - {e}")
        except Exception as e:
            logger.error(f"Error processing message '{message}': {e}")
    
    def get_pressed_tile(self) -> Optional[Tuple[int, int]]:
        """
        Get the latest pressed tile coordinates.
        
        Returns:
            Tuple of (row, col) if a tile was pressed, None otherwise
        """
        with self.tile_lock:
            if self.latest_pressed_tile:
                result = self.latest_pressed_tile
                self.latest_pressed_tile = None  # Clear after reading
                return result
            return None
    
    def light_tile(self, row: int, col: int, brightness: int) -> bool:
        """
        Send command to light up a specific tile with brightness.
        
        Args:
            row: Row coordinate (0-based)
            col: Column coordinate (0-based)
            brightness: Brightness value (0-255)
            
        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.is_connected or not self.serial_connection:
            logger.error("Not connected to Arduino")
            return False
        
        try:
            index = row * 5 + col
            command = f"light {index} {brightness}\n"
            self.serial_connection.write(command.encode('utf-8'))
            self.serial_connection.flush()
            logger.debug(f"Sent command: {command.strip()}")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Serial error sending command: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False
    
    def light_all_tiles(self, color: str) -> bool:
        """
        Light up all tiles with the same color.
        
        Args:
            color: Color name for all tiles
            
        Returns:
            True if command sent successfully, False otherwise
        """
        if not self.is_connected or not self.serial_connection:
            logger.error("Not connected to Arduino")
            return False
        
        try:
            command = f"light_all {color.lower()}\n"
            self.serial_connection.write(command.encode('utf-8'))
            self.serial_connection.flush()
            logger.debug(f"Sent command: {command.strip()}")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Serial error sending command: {e}")
            self.is_connected = False
            return False
        except Exception as e:
            logger.error(f"Error sending command: {e}")
            return False
    
    def turn_off_all_tiles(self) -> bool:
        """
        Turn off all tiles.
        
        Returns:
            True if command sent successfully, False otherwise
        """
        return self.light_all_tiles("off")
    
    def is_arduino_connected(self) -> bool:
        """
        Check if Arduino is currently connected.
        
        Returns:
            True if connected, False otherwise
        """
        return bool(self.is_connected and self.serial_connection and self.serial_connection.is_open)

# Global instance for easy access
_arduino_controller: Optional[ArduinoTileController] = None

def initialize_arduino(port: Optional[str] = None, baud_rate: int = 9600) -> bool:
    """
    Initialize the Arduino connection.
    
    Args:
        port: Serial port name (None for auto-detect)
        baud_rate: Serial baud rate
        
    Returns:
        True if initialization successful, False otherwise
    """
    global _arduino_controller
    
    if _arduino_controller is None:
        _arduino_controller = ArduinoTileController(baud_rate=baud_rate)
    
    return _arduino_controller.connect(port)

def get_pressed_tile() -> Optional[Tuple[int, int]]:
    """
    Get the latest pressed tile coordinates.
    
    Returns:
        Tuple of (row, col) if a tile was pressed, None otherwise
    """
    global _arduino_controller
    
    if _arduino_controller is None:
        logger.error("Arduino not initialized. Call initialize_arduino() first.")
        return None
    
    return _arduino_controller.get_pressed_tile()

def light_tile(row: int, col: int, brightness: int) -> bool:
    """
    Light up a specific tile with brightness.
    
    Args:
        row: Row coordinate (0-based)
        col: Column coordinate (0-based)
        brightness: Brightness value (0-255)
        
    Returns:
        True if command sent successfully, False otherwise
    """
    global _arduino_controller
    
    if _arduino_controller is None:
        logger.error("Arduino not initialized. Call initialize_arduino() first.")
        return False
    
    return _arduino_controller.light_tile(row, col, brightness)

def cleanup():
    """Clean up Arduino connection."""
    global _arduino_controller
    
    if _arduino_controller:
        _arduino_controller.disconnect()
        _arduino_controller = None

def turn_off_all_tiles() -> bool:
    """
    Global wrapper for turning off all tiles.
    """
    global _arduino_controller
    
    if _arduino_controller is None:
        logger.error("Arduino not initialized. Call initialize_arduino() first.")
        return False
    
    return _arduino_controller.turn_off_all_tiles()


# Example usage and testing
if __name__ == "__main__":
    try:
        # Initialize Arduino connection
        if initialize_arduino():
            print("Arduino connected successfully!")
            
            # Test lighting some tiles
            light_tile(0, 0, 255)
            light_tile(1, 1, 128)
            light_tile(2, 2, 64)
            
            # Monitor for pressed tiles
            print("Monitoring for pressed tiles... (Press Ctrl+C to stop)")
            while True:
                pressed = get_pressed_tile()
                if pressed:
                    row, col = pressed
                    print(f"Tile pressed at ({row}, {col})")
                    # Light up the pressed tile
                    light_tile(row, col, 255)
                time.sleep(0.1)
                
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        cleanup()
        print("Cleanup complete.")
