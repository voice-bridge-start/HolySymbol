import threading
import time
import cv2
import numpy as np
import pygetwindow as gw
import mss
from PIL import Image
from tkinter import messagebox


class Detector:
    def __init__(self, ui):
        self.ui = ui
        self.is_running = False
        self.detection_thread = None
        self.current_state = "WAITING"
        self.timer_start_time = 0
        self.alarm_played_for_this_buff = False
        self.active_detection_area = None

        self.active_threshold = 0.9
        self.active_start_time = 59
        self.active_target_number = 5
        self.active_volume = 1.0

    def start(self, detection_area):
        self.is_running = True
        self.current_state = "WAITING"
        self.alarm_played_for_this_buff = False
        self.active_detection_area = detection_area
        self.detection_thread = threading.Thread(target=self.detection_loop, daemon=True)
        self.detection_thread.start()

    def stop(self):
        self.is_running = False

    def detection_loop(self):
        try:
            trigger_image_raw = cv2.imdecode(np.fromfile(self.ui.trigger_image_path, dtype=np.uint8),
                                             cv2.IMREAD_UNCHANGED)
            if trigger_image_raw is None:
                raise ValueError("이미지 로딩 실패")

            if len(trigger_image_raw.shape) == 3 and trigger_image_raw.shape[2] == 4:
                _, _, _, mask = cv2.split(trigger_image_raw)
                trigger_image = cv2.cvtColor(trigger_image_raw, cv2.COLOR_BGRA2BGR)
            else:
                trigger_image, mask = trigger_image_raw, None
        except Exception as e:
            self.ui.root.after(0, lambda: messagebox.showerror("오류", f"이미지 로딩 실패: {e}"))
            self.ui.root.after(0, self.stop)
            return

        with mss.mss() as sct:
            while self.is_running:
                try:
                    win = self.find_target_window()
                    if not win:
                        if self.current_state == "COUNTING":
                            self.reset_to_waiting_state()
                        time.sleep(1)
                        continue

                    max_val = self.capture_and_match(sct, win, trigger_image, mask)
                    self.ui.root.after(0, self.ui.update_match_rate, max_val)
                    self.process_state(max_val)
                    time.sleep(0.1)
                except Exception as e:
                    print(f"탐지 루프 오류: {e}")
                    time.sleep(1)

    def find_target_window(self):
        try:
            win_title = self.ui.selected_window_title.get()
            target_windows = gw.getWindowsWithTitle(win_title)
            if target_windows and not target_windows[0].isMinimized:
                return target_windows[0]
        except Exception as e:
            print(f"창 찾기 오류: {e}")
        return None

    def capture_and_match(self, sct, win, trigger_image, mask):
        if self.active_detection_area:
            monitor = {
                "top": win.top + self.active_detection_area["top"],
                "left": win.left + self.active_detection_area["left"],
                "width": self.active_detection_area["width"],
                "height": self.active_detection_area["height"]
            }
        else:
            monitor = {"top": win.top, "left": win.left, "width": win.width, "height": win.height}

        sct_img = sct.grab(monitor)
        screen_image = np.array(Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX"))
        result = cv2.matchTemplate(screen_image, trigger_image, cv2.TM_CCOEFF_NORMED, mask=mask)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        return max_val

    def process_state(self, max_val):
        is_image_found = max_val >= self.active_threshold

        if self.current_state == "WAITING":
            if is_image_found:
                print("시작 이미지 발견. 카운트다운을 시작합니다.")
                self.current_state = "COUNTING"
                self.timer_start_time = time.time()
                self.alarm_played_for_this_buff = False
        elif self.current_state == "COUNTING":
            elapsed_time = time.time() - self.timer_start_time
            current_timer_value = self.active_start_time - int(elapsed_time)
            self.ui.root.after(0, self.ui.update_status, f"상태: 카운트다운 중... {current_timer_value}초", "green")

            if current_timer_value <= self.active_target_number and not self.alarm_played_for_this_buff:
                print(f"{self.active_target_number}초 알람을 울립니다.")
                self.ui.root.after(0, self.ui.sound_manager.play, self.active_volume)
                self.alarm_played_for_this_buff = True
                self.reset_to_waiting_state()
                time.sleep(1)

            if elapsed_time > self.active_start_time + 3:
                print("타이머 시간 초과. 상태를 초기화합니다.")
                self.reset_to_waiting_state()

    def reset_to_waiting_state(self):
        self.current_state = "WAITING"
        self.ui.root.after(0, self.ui.update_status, "상태: 시작 이미지 대기 중...", "orange")
