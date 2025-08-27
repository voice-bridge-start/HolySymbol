import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pygetwindow as gw
import mss
from PIL import Image, ImageTk
import os
import time
import threading

from src.detector import Detector
from src.sound import SoundManager
from src.utils import resource_path


class AppUI:
    def __init__(self, root):
        self.root = root
        self.root.title("홀심알람")
        self.root.geometry("500x540")
        self.root.resizable(False, False)

        try:
            self.root.iconbitmap(resource_path("resources/icon.ico"))
        except tk.TclError:
            print("아이콘 파일을 찾을 수 없습니다.")

        self.trigger_image_path = ""
        self.sound_file_path = ""
        self.selected_window_title = tk.StringVar()
        self.detection_area = None

        self.timer_start_var = tk.StringVar(value="59")
        self.target_number_var = tk.StringVar(value="35")
        self.detection_threshold_var = tk.IntVar(value=80)
        self.volume_var = tk.IntVar(value=100)
        self.current_match_rate_var = tk.StringVar(value="현재 일치율: 0.00%")

        self.sound_manager = SoundManager()
        self.detector = Detector(self)

        self.create_widgets()
        self.update_window_list()

        # 기본 사운드 파일 설정
        self.set_default_sound()

    def set_default_sound(self):
        try:
            default_sound_path = resource_path("resources/alarm.mp3")
            if os.path.exists(default_sound_path):
                self.sound_file_path = default_sound_path
                self.sound_label.config(text=os.path.basename(self.sound_file_path), foreground="black")
                self.sound_manager.load_sound(self.sound_file_path)
        except Exception as e:
            print(f"기본 사운드 파일을 로드하는 중 오류 발생: {e}")

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._create_window_selection_widgets(main_frame)
        self._create_file_selection_widgets(main_frame)
        self._create_settings_widgets(main_frame)
        self._create_action_widgets(main_frame)

        self.ui_elements_to_disable = [
            self.window_combobox, self.refresh_button, self.image_button, self.sound_button,
            self.preview_button, self.set_area_button, self.timer_start_entry,
            self.target_number_entry, self.threshold_scale, self.volume_scale
        ]

    def _create_window_selection_widgets(self, parent):
        window_frame = ttk.LabelFrame(parent, text="1. 탐색할 창 선택")
        window_frame.pack(fill=tk.X, padx=5, pady=5)
        self.window_combobox = ttk.Combobox(window_frame, textvariable=self.selected_window_title, state="readonly",
                                            width=40)
        self.window_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.refresh_button = ttk.Button(window_frame, text="새로고침", command=self.update_window_list)
        self.refresh_button.pack(side=tk.LEFT, padx=5, pady=5)

    def _create_file_selection_widgets(self, parent):
        file_frame = ttk.LabelFrame(parent, text="2. 파일 선택")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        self.image_button = ttk.Button(file_frame, text="탐지할 시작 이미지 선택", command=self.select_image_file)
        self.image_button.pack(fill=tk.X, padx=5, pady=5)
        self.image_label = ttk.Label(file_frame, text="선택된 이미지 파일 없음", foreground="gray")
        self.image_label.pack(fill=tk.X, padx=5, pady=2)

        sound_selection_frame = ttk.Frame(file_frame)
        sound_selection_frame.pack(fill=tk.X, padx=5, pady=5)
        self.sound_button = ttk.Button(sound_selection_frame, text="알림 소리 변경", command=self.select_sound_file)
        self.sound_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.preview_button = ttk.Button(sound_selection_frame, text="미리 듣기", command=self.toggle_preview_sound)
        self.preview_button.pack(side=tk.LEFT, padx=(5, 0))
        self.sound_label = ttk.Label(file_frame, text="선택된 소리 파일 없음", foreground="gray")
        self.sound_label.pack(fill=tk.X, padx=5, pady=2)

    def _create_settings_widgets(self, parent):
        settings_frame = ttk.LabelFrame(parent, text="3. 설정")
        settings_frame.pack(fill=tk.X, padx=5, pady=5, ipady=5)

        area_frame = ttk.Frame(settings_frame)
        area_frame.pack(fill=tk.X, expand=True, pady=2, padx=5)
        self.set_area_button = ttk.Button(area_frame, text="탐지 영역 설정", command=self.start_area_selection)
        self.set_area_button.pack(side=tk.LEFT, padx=(0, 5))
        self.area_label = ttk.Label(area_frame, text="탐지 영역: 전체 화면")
        self.area_label.pack(side=tk.LEFT)

        self._create_entry_widget(settings_frame, "타이머 시작 숫자:", self.timer_start_var)
        self._create_entry_widget(settings_frame, "알림 울릴 숫자:", self.target_number_var)
        self._create_scale_widget(settings_frame, "이미지 일치율:", self.detection_threshold_var, 70, 100, "%")
        self._create_scale_widget(settings_frame, "소리 크기:", self.volume_var, 0, 100, "%")

    def _create_entry_widget(self, parent, label_text, textvariable):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, expand=True, pady=2, padx=5)
        label = ttk.Label(frame, text=label_text, width=15)
        label.pack(side=tk.LEFT)
        entry = ttk.Entry(frame, textvariable=textvariable, width=10)
        if label_text == "타이머 시작 숫자:":
            self.timer_start_entry = entry
        else:
            self.target_number_entry = entry
        entry.pack(side=tk.LEFT)

    def _create_scale_widget(self, parent, label_text, variable, from_, to, unit):
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, expand=True, pady=2, padx=5)
        label = ttk.Label(frame, text=label_text, width=15)
        label.pack(side=tk.LEFT)
        value_label = ttk.Label(frame, text=f"{variable.get()}{unit}", width=5, anchor="e")
        scale = ttk.Scale(frame, from_=from_, to=to, orient=tk.HORIZONTAL, variable=variable,
                          command=lambda s, label=value_label: label.config(text=f"{int(float(s))}{unit}"))
        if label_text == "이미지 일치율:":
            self.threshold_scale = scale
        else:
            self.volume_scale = scale
        scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        value_label.pack(side=tk.LEFT)

    def _create_action_widgets(self, parent):
        action_frame = ttk.LabelFrame(parent, text="4. 실행 및 상태")
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        self.toggle_button = ttk.Button(action_frame, text="탐지 시작", command=self.toggle_detection)
        self.toggle_button.pack(fill=tk.X, padx=5, pady=10)
        self.status_label = ttk.Label(action_frame, text="상태: 대기 중", font=("Helvetica", 10, "bold"))
        self.status_label.pack(fill=tk.X, padx=5, pady=2)
        self.match_rate_label = ttk.Label(action_frame, textvariable=self.current_match_rate_var, foreground="gray")
        self.match_rate_label.pack(fill=tk.X, padx=5, pady=2)

    def start_area_selection(self):
        win_title = self.selected_window_title.get()
        if not win_title:
            messagebox.showwarning("오류", "먼저 탐색할 창을 선택해주세요.")
            return

        target_windows = gw.getWindowsWithTitle(win_title)
        if not target_windows:
            messagebox.showwarning("오류", f"'{win_title}' 창을 찾을 수 없습니다.")
            return

        win = target_windows[0]
        if win.isMinimized:
            messagebox.showwarning("오류", "창이 최소화되어 있습니다. 창을 복원한 후 다시 시도해주세요.")
            return

        self.root.withdraw()
        time.sleep(0.2)

        try:
            with mss.mss() as sct:
                monitor = {"top": win.top, "left": win.left, "width": win.width, "height": win.height}
                sct_img = sct.grab(monitor)
                screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except Exception as e:
            messagebox.showerror("캡처 오류", f"창을 캡처하는 데 실패했습니다: {e}")
            self.root.deiconify()
            return

        selector_win = tk.Toplevel()
        selector_win.overrideredirect(True)
        selector_win.attributes("-topmost", True)
        selector_win.geometry(f"{win.width}x{win.height}+{win.left}+{win.top}")

        canvas = tk.Canvas(selector_win, width=win.width, height=win.height, cursor="cross")
        canvas.pack(fill=tk.BOTH, expand=True)

        tk_screenshot = ImageTk.PhotoImage(screenshot)
        canvas.create_image(0, 0, image=tk_screenshot, anchor="nw")

        rect = None
        start_x, start_y = 0, 0

        def on_press(event):
            nonlocal start_x, start_y, rect
            start_x, start_y = event.x, event.y
            if rect:
                canvas.delete(rect)
            rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)

        def on_drag(event):
            nonlocal rect
            canvas.coords(rect, start_x, start_y, event.x, event.y)

        def on_release(event):
            end_x, end_y = event.x, event.y
            left, top = min(start_x, end_x), min(start_y, end_y)
            width, height = abs(start_x - end_x), abs(start_y - end_y)

            if width == 0 or height == 0:
                selector_win.destroy()
                self.root.deiconify()
                return

            self.detection_area = {"left": left, "top": top, "width": width, "height": height}
            self.area_label.config(text=f"탐지 영역: {width}x{height} (설정됨)")
            selector_win.destroy()
            self.root.deiconify()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        selector_win.image = tk_screenshot

    def update_window_list(self):
        try:
            window_titles = [win.title for win in gw.getAllWindows() if win.title]
            self.window_combobox['values'] = window_titles

            target_prefix = "MapleStory Worlds"
            found_target = False
            for title in window_titles:
                if title.startswith(target_prefix):
                    self.selected_window_title.set(title)
                    found_target = True
                    break

            if not found_target:
                if window_titles:
                    self.selected_window_title.set(window_titles[0])
                else:
                    self.selected_window_title.set("")
        except Exception as e:
            messagebox.showerror("오류", f"창 목록을 가져오는 데 실패했습니다: {e}")

    def select_image_file(self):
        file_path = filedialog.askopenfilename(title="탐지할 시작 이미지 선택",
                                               filetypes=[("PNG files", "*.png"), ("All files", "*.*")])
        if file_path:
            self.trigger_image_path = file_path
            self.image_label.config(text=os.path.basename(file_path), foreground="black")

    def select_sound_file(self):
        file_path = filedialog.askopenfilename(title="알림 소리 선택",
                                               filetypes=[("Sound files", "*.wav *.mp3"), ("All files", "*.*")])
        if file_path:
            self.sound_file_path = file_path
            self.sound_label.config(text=os.path.basename(file_path), foreground="black")
            self.sound_manager.load_sound(file_path)

    def toggle_preview_sound(self):
        if self.sound_manager.is_playing():
            self.sound_manager.stop()
            self.preview_button.config(text="미리 듣기")
        else:
            volume = self.volume_var.get() / 100.0
            if self.sound_manager.play(volume):
                self.preview_button.config(text="중지")
                self.check_sound_status()

    def check_sound_status(self):
        if not self.sound_manager.is_playing():
            self.preview_button.config(text="미리 듣기")
        else:
            self.root.after(100, self.check_sound_status)

    def toggle_ui_state(self, state):
        for widget in self.ui_elements_to_disable:
            if isinstance(widget, ttk.Combobox):
                widget.config(state='readonly' if state == 'normal' else 'disabled')
            else:
                widget.config(state=state)

    def toggle_detection(self):
        if self.detector.is_running:
            self.detector.stop()
            self.toggle_button.config(text="탐지 시작")
            self.update_status("상태: 중지됨", "red")
            self.toggle_ui_state('normal')
        else:
            if not all([self.trigger_image_path, self.sound_file_path, self.selected_window_title.get(),
                        self.target_number_var.get(), self.timer_start_var.get()]):
                messagebox.showwarning("준비 미흡", "이미지와 소리 파일을 포함한 모든 항목을 설정해야 합니다.")
                return

            try:
                self.detector.active_start_time = int(self.timer_start_var.get())
                self.detector.active_target_number = int(self.target_number_var.get())
                self.detector.active_threshold = self.detection_threshold_var.get() / 100.0
                self.detector.active_volume = self.volume_var.get() / 100.0
            except ValueError:
                messagebox.showerror("입력 오류", "타이머 숫자는 정수여야 합니다.")
                return

            self.toggle_ui_state('disabled')
            self.toggle_button.config(text="탐지 중지")
            self.update_status("상태: 시작 이미지 대기 중...", "orange")
            self.detector.start(self.detection_area)

    def update_status(self, text, color):
        self.status_label.config(text=text, foreground=color)

    def update_match_rate(self, rate):
        self.current_match_rate_var.set(f"현재 일치율: {rate * 100:.2f}%")
