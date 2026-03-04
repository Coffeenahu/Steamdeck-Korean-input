#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KoreanInput - 스팀덱 데스크탑용 한글 입력기
- Ctrl+Space 로 팝업 열기/닫기
- 한영키로 한글/영어 모드 전환
- 트레이 아이콘 우클릭으로 자동실행 켜고 끄기
"""

import tkinter as tk
import threading
import subprocess
import os
import sys
import json

try:
    from pynput import keyboard as pynput_keyboard
    HAS_PYNPUT = True
except ImportError:
    HAS_PYNPUT = False

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

# ─────────────────────────────────────────
# 1. 설정 파일 (한영키 코드 저장)
# ─────────────────────────────────────────
CONFIG_PATH = os.path.expanduser('~/.config/korean-input/config.json')

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {'hangul_key_vk': None}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f)

config = load_config()

# ─────────────────────────────────────────
# 2. 두벌식 변환 엔진
# ─────────────────────────────────────────
CHOSUNG_IDX = {
    'ㄱ':0,'ㄲ':1,'ㄴ':2,'ㄷ':3,'ㄸ':4,'ㄹ':5,
    'ㅁ':6,'ㅂ':7,'ㅃ':8,'ㅅ':9,'ㅆ':10,'ㅇ':11,
    'ㅈ':12,'ㅉ':13,'ㅊ':14,'ㅋ':15,'ㅌ':16,'ㅍ':17,'ㅎ':18
}
JUNGSUNG_IDX = {
    'ㅏ':0,'ㅐ':1,'ㅑ':2,'ㅒ':3,'ㅓ':4,'ㅔ':5,
    'ㅕ':6,'ㅖ':7,'ㅗ':8,'ㅘ':9,'ㅙ':10,'ㅚ':11,
    'ㅛ':12,'ㅜ':13,'ㅝ':14,'ㅞ':15,'ㅟ':16,'ㅠ':17,
    'ㅡ':18,'ㅢ':19,'ㅣ':20
}
JONGSUNG_IDX = {
    'ㄱ':1,'ㄲ':2,'ㄳ':3,'ㄴ':4,'ㄵ':5,'ㄶ':6,
    'ㄷ':7,'ㄹ':8,'ㄺ':9,'ㄻ':10,'ㄼ':11,'ㄽ':12,
    'ㄾ':13,'ㄿ':14,'ㅀ':15,'ㅁ':16,'ㅂ':17,'ㅄ':18,
    'ㅅ':19,'ㅆ':20,'ㅇ':21,'ㅈ':22,'ㅊ':23,'ㅋ':24,
    'ㅌ':25,'ㅍ':26,'ㅎ':27
}
KEY_TO_JAMO = {
    'r':'ㄱ','s':'ㄴ','e':'ㄷ','f':'ㄹ','a':'ㅁ','q':'ㅂ',
    't':'ㅅ','d':'ㅇ','w':'ㅈ','c':'ㅊ','z':'ㅋ','x':'ㅌ',
    'v':'ㅍ','g':'ㅎ',
    'R':'ㄲ','E':'ㄸ','Q':'ㅃ','T':'ㅆ','W':'ㅉ',
    'k':'ㅏ','o':'ㅐ','i':'ㅑ','O':'ㅒ','j':'ㅓ','p':'ㅔ',
    'u':'ㅕ','P':'ㅖ','h':'ㅗ','y':'ㅛ','n':'ㅜ','b':'ㅠ',
    'm':'ㅡ','l':'ㅣ',
}
VOWELS = set(JUNGSUNG_IDX.keys())
COMPOUND_VOWEL = {
    'ㅗ': {'ㅏ':'ㅘ','ㅐ':'ㅙ','ㅣ':'ㅚ'},
    'ㅜ': {'ㅓ':'ㅝ','ㅔ':'ㅞ','ㅣ':'ㅟ'},
    'ㅡ': {'ㅣ':'ㅢ'},
}
COMPOUND_CONSONANT = {
    'ㄱ': {'ㅅ':'ㄳ'},
    'ㄴ': {'ㅈ':'ㄵ','ㅎ':'ㄶ'},
    'ㄹ': {'ㄱ':'ㄺ','ㅁ':'ㄻ','ㅂ':'ㄼ','ㅅ':'ㄽ','ㅌ':'ㄾ','ㅍ':'ㄿ','ㅎ':'ㅀ'},
    'ㅂ': {'ㅅ':'ㅄ'},
}
SPLIT_CONSONANT = {
    'ㄳ':('ㄱ','ㅅ'),'ㄵ':('ㄴ','ㅈ'),'ㄶ':('ㄴ','ㅎ'),
    'ㄺ':('ㄹ','ㄱ'),'ㄻ':('ㄹ','ㅁ'),'ㄼ':('ㄹ','ㅂ'),
    'ㄽ':('ㄹ','ㅅ'),'ㄾ':('ㄹ','ㅌ'),'ㄿ':('ㄹ','ㅍ'),
    'ㅀ':('ㄹ','ㅎ'),'ㅄ':('ㅂ','ㅅ'),
}

def combine_hangul(cho, jung, jong=None):
    code = (CHOSUNG_IDX[cho] * 21 * 28
            + JUNGSUNG_IDX[jung] * 28
            + (JONGSUNG_IDX[jong] if jong else 0)
            + 0xAC00)
    return chr(code)

def convert_to_korean(text):
    jamos = []
    for ch in text:
        if ch == ' ':
            jamos.append(' ')
        else:
            j = KEY_TO_JAMO.get(ch)
            jamos.append(j if j else ch)

    result = ''
    cho = jung = jong = None

    def flush():
        nonlocal cho, jung, jong, result
        if cho:
            result += combine_hangul(cho, jung, jong) if jung else cho
        elif jung:
            result += jung
        cho = jung = jong = None

    for jamo in jamos:
        is_vowel = jamo in VOWELS
        is_jamo  = is_vowel or jamo in CHOSUNG_IDX or jamo in JONGSUNG_IDX

        if not is_jamo:
            flush(); result += jamo
        elif not is_vowel:
            if not cho and not jung:   cho = jamo
            elif cho and not jung:     flush(); cho = jamo
            elif cho and jung and not jong: jong = jamo
            elif cho and jung and jong:
                c = COMPOUND_CONSONANT.get(jong, {})
                if jamo in c: jong = c[jamo]
                else: flush(); cho = jamo
            else: flush(); cho = jamo
        else:
            if not cho and not jung:   jung = jamo
            elif cho and not jung:     jung = jamo
            elif cho and jung and not jong:
                c = COMPOUND_VOWEL.get(jung, {})
                if jamo in c: jung = c[jamo]
                else: flush(); jung = jamo
            elif cho and jung and jong:
                split = SPLIT_CONSONANT.get(jong)
                if split: jong = split[0]; next_cho = split[1]
                else: next_cho = jong; jong = None
                flush(); cho = next_cho; jung = jamo
            else: flush(); jung = jamo
    flush()
    return result

# ─────────────────────────────────────────
# 3. 클립보드
# ─────────────────────────────────────────
def copy_to_clipboard(text, root):
    for cmd in [['xclip', '-selection', 'clipboard'],
                ['xsel', '--clipboard', '--input']]:
        try:
            subprocess.run(cmd, input=text.encode(), check=True,
                           stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass
    try:
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        return True
    except Exception:
        pass
    return False

# ─────────────────────────────────────────
# 4. 자동실행 관리
# ─────────────────────────────────────────
AUTOSTART_PATH = os.path.expanduser('~/.config/autostart/korean-input.desktop')
SCRIPT_PATH    = os.path.expanduser('~/.local/bin/korean_input.py')
VENV_PYTHON    = os.path.expanduser('~/korean-env/bin/python3')

def is_autostart_enabled():
    return os.path.exists(AUTOSTART_PATH)

def enable_autostart():
    os.makedirs(os.path.dirname(AUTOSTART_PATH), exist_ok=True)
    with open(AUTOSTART_PATH, 'w') as f:
        f.write(f"""[Desktop Entry]
Name=한글 입력기
Exec=bash -c "sleep 3 && nohup {VENV_PYTHON} {SCRIPT_PATH} &"
Icon=input-keyboard
Terminal=false
Type=Application
""")

def disable_autostart():
    if os.path.exists(AUTOSTART_PATH):
        os.remove(AUTOSTART_PATH)

def toggle_autostart():
    if is_autostart_enabled():
        disable_autostart(); return False
    else:
        enable_autostart(); return True

# ─────────────────────────────────────────
# 5. 트레이 아이콘
# ─────────────────────────────────────────
def make_tray_image():
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([2, 2, 62, 62], fill='#0077b6')
    d.text((16, 18), '한', fill='white')
    return img

# ─────────────────────────────────────────
# 6. 메인 앱
# ─────────────────────────────────────────
korean_mode   = True
committed_text = ''

class KoreanInputApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("한글 입력기")
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#1a1a2e')

        w, h = 500, 230
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')

        self.detecting_hangul_key = False
        self._build_ui()
        self._setup_global_hotkey()
        self._setup_tray()

        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.bind('<Escape>', lambda e: self.hide())
        self.root.withdraw()

    def _build_ui(self):
        tk.Label(self.root, text="🇰🇷 한글 입력기",
                 bg='#1a1a2e', fg='#00ccff',
                 font=('Arial', 13, 'bold')).pack(pady=(10, 0))

        tk.Label(self.root, text="영문 입력:",
                 bg='#1a1a2e', fg='#aaaaaa',
                 font=('Arial', 9)).pack(anchor='w', padx=16)

        input_row = tk.Frame(self.root, bg='#1a1a2e')
        input_row.pack(fill='x', padx=16)

        self.input_var = tk.StringVar()
        self.input_var.trace_add('write', self._on_input_change)
        self.input_entry = tk.Entry(
            input_row, textvariable=self.input_var,
            font=('Arial', 13), bg='#16213e', fg='white',
            insertbackground='white', relief='flat', bd=6)
        self.input_entry.pack(side='left', fill='x', expand=True)
        self.input_entry.bind('<Return>', lambda e: self._copy_and_close())
        self.input_entry.bind('<Escape>', lambda e: self.hide())

        self.mode_btn = tk.Button(
            input_row, text="한글", width=4,
            command=self._toggle_mode,
            bg='#0077b6', fg='white',
            font=('Arial', 11, 'bold'),
            relief='flat', cursor='hand2')
        self.mode_btn.pack(side='right', padx=(6, 0))

        tk.Label(self.root, text="변환 결과:",
                 bg='#1a1a2e', fg='#aaaaaa',
                 font=('Arial', 9)).pack(anchor='w', padx=16, pady=(6, 0))

        self.output_var = tk.StringVar()
        row = tk.Frame(self.root, bg='#1a1a2e')
        row.pack(fill='x', padx=16)

        tk.Label(row, textvariable=self.output_var,
                 font=('Arial', 13), bg='#0f3460', fg='#00ff99',
                 anchor='w', padx=8, relief='flat'
                 ).pack(side='left', fill='x', expand=True, ipady=4)

        self.copy_btn = tk.Button(
            row, text="복사 & 닫기", command=self._copy_and_close,
            bg='#0077b6', fg='white', font=('Arial', 10, 'bold'),
            relief='flat', padx=10, cursor='hand2')
        self.copy_btn.pack(side='right', padx=(8, 0))

        # 한영키 설정 버튼
        hangul_row = tk.Frame(self.root, bg='#1a1a2e')
        hangul_row.pack(fill='x', padx=16, pady=(8, 0))

        hangul_key_vk = config.get('hangul_key_vk')
        self.hangul_key_label = tk.Label(
            hangul_row,
            text=f"한영키: {'설정됨 ✓' if hangul_key_vk else '미설정'}",
            bg='#1a1a2e', fg='#aaaaaa', font=('Arial', 9))
        self.hangul_key_label.pack(side='left')

        self.detect_btn = tk.Button(
            hangul_row, text="한영키 등록",
            command=self._start_detect_hangul_key,
            bg='#333355', fg='white',
            font=('Arial', 9), relief='flat',
            cursor='hand2', padx=8)
        self.detect_btn.pack(side='right')

        # 하단 버튼 행
        btn_row = tk.Frame(self.root, bg='#1a1a2e')
        btn_row.pack(fill='x', padx=16, pady=(8, 0))

        self.autostart_btn = tk.Button(
            btn_row,
            text="자동실행 ON" if is_autostart_enabled() else "자동실행 OFF",
            command=self._toggle_autostart_btn,
            bg='#006600' if is_autostart_enabled() else '#444444',
            fg='white', font=('Arial', 9), relief='flat',
            cursor='hand2', padx=8)
        self.autostart_btn.pack(side='left')

        tk.Button(
            btn_row, text="종료",
            command=self._quit,
            bg='#660000', fg='white',
            font=('Arial', 9), relief='flat',
            cursor='hand2', padx=8).pack(side='right')

        tk.Label(self.root,
                 text="Ctrl+Space: 열기/닫기  |  한영키: 모드전환  |  Enter: 복사  |  ESC: 닫기",
                 bg='#1a1a2e', fg='#555577', font=('Arial', 8)
                 ).pack(pady=(4, 0))

    def _toggle_autostart_btn(self):
        enabled = toggle_autostart()
        self.autostart_btn.config(
            text="자동실행 ON" if enabled else "자동실행 OFF",
            bg='#006600' if enabled else '#444444')

    def _quit(self):
        try:
            self.tray.stop()
        except Exception:
            pass
        self.root.destroy()

    def _toggle_mode(self):
        global korean_mode, committed_text
        raw = self.input_var.get()
        if raw:
            committed_text += convert_to_korean(raw) if korean_mode else raw
        korean_mode = not korean_mode
        if korean_mode:
            self.mode_btn.config(text="한글", bg='#0077b6')
        else:
            self.mode_btn.config(text="ENG", bg='#444466')
        self.input_var.set('')
        self.output_var.set(committed_text)
        self.input_entry.focus_set()

    def _on_input_change(self, *args):
        raw = self.input_var.get()
        current = convert_to_korean(raw) if korean_mode else raw
        self.output_var.set(committed_text + current)

    def _copy_and_close(self):
        text = self.output_var.get()
        if not text:
            return
        ok = copy_to_clipboard(text, self.root)
        self.copy_btn.config(text='✓ 복사됨!' if ok else '복사 실패')
        self.root.after(700, self.hide)

    def show(self):
        global korean_mode, committed_text
        korean_mode = True
        committed_text = ''
        self.mode_btn.config(text="한글", bg='#0077b6')
        self.input_var.set('')
        self.output_var.set('')
        self.copy_btn.config(text='복사 & 닫기')
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.input_entry.focus_set()

    def hide(self):
        self.root.withdraw()

    def toggle(self):
        if self.root.state() == 'withdrawn':
            self.root.after(0, self.show)
        else:
            self.root.after(0, self.hide)

    # ── 한영키 감지 ──
    def _start_detect_hangul_key(self):
        self.detecting_hangul_key = True
        self.detect_btn.config(text="한영키를 누르세요...", bg='#ff6600')
        self.hangul_key_label.config(text="한영키: 감지 중...")

    def _on_hangul_key_detected(self, vk):
        config['hangul_key_vk'] = vk
        save_config(config)
        self.detecting_hangul_key = False
        self.root.after(0, lambda: self.detect_btn.config(
            text="한영키 등록", bg='#333355'))
        self.root.after(0, lambda: self.hangul_key_label.config(
            text="한영키: 설정됨 ✓"))

    # ── 글로벌 단축키 ──
    def _setup_global_hotkey(self):
        if not HAS_PYNPUT:
            self.root.after(0, self.show)
            return

        def on_press(key):
            try:
                vk = key.vk if hasattr(key, 'vk') else None

                # 한영키 감지 모드
                if self.detecting_hangul_key and vk:
                    self._on_hangul_key_detected(vk)
                    return

                # 한영키로 모드 토글
                hangul_vk = config.get('hangul_key_vk')
                if hangul_vk and vk == hangul_vk:
                    if self.root.state() != 'withdrawn':
                        self.root.after(0, self.mode_btn.invoke)
            except Exception:
                pass

        def run():
            try:
                listener = pynput_keyboard.Listener(on_press=on_press)
                listener.start()
                with pynput_keyboard.GlobalHotKeys({
                    '<ctrl>+<space>': lambda: self.root.after(0, self.toggle)
                }) as h:
                    h.join()
            except Exception as e:
                print(f"단축키 오류: {e}")

        threading.Thread(target=run, daemon=True).start()

    # ── 트레이 ──
    def _setup_tray(self):
        if not HAS_TRAY:
            self.root.after(500, self.show)
            return

        img = make_tray_image()

        def on_click(icon, button, time=None):
            # 클릭하면 창 열기/닫기
            self.root.after(0, self.toggle)

        self.tray = pystray.Icon(
            "KoreanInput", img, "KoreanInput"
        )
        self.tray.on_activate = lambda icon: self.root.after(0, self.toggle)

        threading.Thread(target=self.tray.run, daemon=True).start()

    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = KoreanInputApp()
    app.run()
