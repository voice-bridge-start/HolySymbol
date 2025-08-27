import pygame
from tkinter import messagebox

class SoundManager:
    def __init__(self):
        try:
            pygame.mixer.init()
            self.sound_player = None
        except pygame.error as e:
            messagebox.showerror("Pygame 오류", f"Pygame 믹서를 초기화할 수 없습니다: {e}")

    def load_sound(self, file_path):
        try:
            self.sound_player = pygame.mixer.Sound(file_path)
        except pygame.error as e:
            messagebox.showerror("소리 파일 오류", f"소리 파일을 로드할 수 없습니다: {e}")
            self.sound_player = None

    def play(self, volume):
        if self.sound_player and not pygame.mixer.get_busy():
            self.sound_player.set_volume(volume)
            self.sound_player.play()
            return True
        elif not self.sound_player:
            messagebox.showinfo("알림", "먼저 소리 파일을 선택해주세요.")
        return False

    def stop(self):
        if self.sound_player:
            self.sound_player.stop()

    def is_playing(self):
        return pygame.mixer.get_busy()
