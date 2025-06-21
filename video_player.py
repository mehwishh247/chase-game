import vlc
import time
import os
from typing import Optional



class VideoPlayer:
    """A video player that plays videos in the background without GUI."""
    
    def __init__(self):
        """Initialize the video player with VLC instance."""
        # Create VLC instance with no GUI
        self.vlc_instance = vlc.Instance('--no-xlib', '--quiet')
        self.media_player = None
        
    def play_video(self, file_path: str, duration_in_sec: Optional[float] = None) -> bool:
        """
        Play a video file for a specified duration without showing any window.
        
        Args:
            file_path: Path to the video file (mp4, webm, etc.)
            duration_in_sec: Duration to play in seconds. If None, plays until end.
            
        Returns:
            bool: True if video played successfully, False otherwise.
        """
        if not os.path.exists(file_path):
            print(f"Error: Video file '{file_path}' not found.")
            return False
            
        if not self.vlc_instance:
            print("Error: VLC instance not initialized.")
            return False
            
        try:
            # Create media from file
            media = self.vlc_instance.media_new(file_path)
            
            # Create media player
            self.media_player = self.vlc_instance.media_player_new()
            if self.media_player:
                self.media_player.set_media(media)
                
                # Start playing
                self.media_player.play()
                
                # Wait a moment for playback to start
                time.sleep(0.5)
                
                # Wait for specified duration or until video ends
                if duration_in_sec is not None:
                    time.sleep(duration_in_sec)
                else:
                    # Wait until video ends
                    while self.media_player.is_playing():
                        time.sleep(0.1)
                
                # Stop playback
                self.stop()
                return True
            else:
                print("Error: Failed to create media player.")
                return False
            
        except Exception as e:
            print(f"Error playing video: {e}")
            return False
    
    def stop(self):
        """Stop video playback."""
        if self.media_player:
            self.media_player.stop()
            self.media_player = None
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        self.stop()


def play_video(file_path: str, duration_in_sec: Optional[float] = None) -> bool:
    """
    Convenience function to play a video file.
    
    Args:
        file_path: Path to the video file
        duration_in_sec: Duration to play in seconds. If None, plays until end.
        
    Returns:
        bool: True if video played successfully, False otherwise.
    """
    player = VideoPlayer()
    return player.play_video(file_path, duration_in_sec)


def play_fullscreen_video(path: str, duration: float) -> bool:
    """
    Play a video file in fullscreen mode for a specified duration.
    
    Args:
        path: Path to the video file (mp4, webm, etc.)
        duration: Duration to play in seconds
        
    Returns:
        bool: True if video played successfully, False otherwise.
    """
    if not os.path.exists(path):
        print(f"Error: Video file '{path}' not found.")
        return False
    
    # Create VLC instance with minimal GUI suppression
    vlc_instance = vlc.Instance('--no-xlib', '--quiet', '--no-video-title-show')
    media_player = None
    
    try:
        # Create media from file
        media = vlc_instance.media_new(path)
        
        # Create media player
        media_player = vlc_instance.media_player_new()
        media_player.set_media(media)
        
        # Set fullscreen mode
        media_player.fullscreen = True
        
        # Start playing
        media_player.play()
        
        # Wait a moment for playback to start
        time.sleep(0.5)
        
        # Wait for specified duration
        time.sleep(duration)
        
        # Stop playback and release resources
        media_player.stop()
        media_player.release()
        vlc_instance.release()
        
        return True
        
    except Exception as e:
        print(f"Error playing fullscreen video: {e}")
        # Cleanup on error
        if media_player:
            try:
                media_player.stop()
                media_player.release()
            except:
                pass
        try:
            vlc_instance.release()
        except:
            pass
        return False


# Example usage
if __name__ == "__main__":
    # Example: Play a video for 5 seconds
    # play_video("path/to/your/video.mp4", 5.0)
    
    # Example: Play entire video
    # play_video("path/to/your/video.webm")
    
    print("Video player module loaded. Use play_video(file_path, duration) to play videos in the background.")
