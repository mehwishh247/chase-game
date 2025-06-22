import vlc
import pygame

class VideoPlayer:
    def __init__(self, screen):
        self.screen = screen
        # Add arguments to help with embedding and avoid conflicts
        args = [
            '--no-xlib',          # Disable X11 error handling by VLC
            '--vout=xcb_x11',     # Force a specific video output module
            '--avcodec-hw=none',  # Disable hardware decoding
        ]
        self.vlc_instance = vlc.Instance(args)
        self.media_player = self.vlc_instance.media_player_new()
        
        try:
            info = pygame.display.get_wm_info()
            window_id = info['window']
            self.media_player.set_hwnd(window_id)
        except (KeyError, pygame.error):
            print("Could not set window handle for VLC. Video may not be embedded.")

        self.current_video_path = None
        self.loop = False

    def play(self, video_path, loop=False):
        self.current_video_path = str(video_path)
        self.loop = loop
        
        media = self.vlc_instance.media_new(self.current_video_path)
        if self.loop:
            media.add_option('input-repeat=65535') # VLC's way of looping
            
        self.media_player.set_media(media)
        self.media_player.play()

    def stop(self):
        self.media_player.stop()
        self.current_video_path = None

    def is_playing(self):
        return self.media_player.is_playing() 