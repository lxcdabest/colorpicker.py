from tkinter import Tk, Label, Canvas, Button, Entry, StringVar, Toplevel, Frame, messagebox
import mss
import numpy as np
import pyautogui
import keyboard

SAMPLE_INTERVAL_MS = 33
TRANSPARENT_COLOR = '#ff00ff'
SAMPLE_N = 11
MAG_SCALE = 8


class ColorPickingApp:
    def __init__(self):
        self.root = Tk()
        self.root.title('Color Picker')
        self.root.geometry('420x240')
        self.root.resizable(False, False)

        self.running = False
        self.ov = None
        self.sct = mss.mss()
        self.sample_after_id = None
        self.frozen_frame = None

        center_frame = Frame(self.root)
        center_frame.pack(expand=True)

        self.start_btn = Button(center_frame, text='Start (F1)', width=20, command=self.toggle)
        self.start_btn.pack(pady=6)

        btn_row = Frame(center_frame)
        btn_row.pack(pady=4)

        self.mag_enabled = True
        self.mag_btn = Button(btn_row, text='Magnifier: On', width=12, command=self.toggle_magnifier)
        self.mag_btn.pack(side='left', padx=6)

        self.mag_side = 'left'
        self.mag_side_btn = Button(btn_row, text='Mag Side: Left', width=12, command=self.toggle_mag_side)
        self.mag_side_btn.pack(side='left', padx=6)

        color_row = Frame(center_frame)
        color_row.pack(pady=8)

        self.color_var = StringVar(value='None')
        Label(color_row, textvariable=self.color_var, relief='sunken').pack(side='left', padx=8)

        self.swatch = Label(color_row, text='      ', bg='#000000')
        self.swatch.pack(side='left', padx=8)

        self.hex_var = StringVar()
        hex_row = Frame(center_frame)
        hex_row.pack()

        Entry(hex_row, textvariable=self.hex_var, width=9, justify='center').pack(side='left', padx=6)
        Button(hex_row, text='Apply Hex', command=self.apply_hex).pack(side='left')

        self.status_var = StringVar()
        Label(self.root, textvariable=self.status_var, relief='sunken').pack(side='bottom', fill='x')

        keyboard.add_hotkey('f1', self.toggle)
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    def toggle(self):
        self.stop_overlay() if self.running else self.start_overlay()

    def start_overlay(self):
        self.running = True
        self.start_btn.config(text='Stop (F1)')

        mon = self.sct.monitors[0]
        self._vleft, self._vtop = mon['left'], mon['top']
        self._vwidth, self._vheight = mon['width'], mon['height']

        # 🔒 FREEZE SCREEN
        self.frozen_frame = np.array(self.sct.grab(mon))

        self.ov = Toplevel(self.root)
        self.ov.geometry(f"{self._vwidth}x{self._vheight}+{self._vleft}+{self._vtop}")
        self.ov.overrideredirect(True)
        self.ov.attributes('-topmost', True)
        self.ov.config(bg=TRANSPARENT_COLOR)
        self.ov.attributes('-transparentcolor', TRANSPARENT_COLOR)

        self.canvas = Canvas(self.ov, bg=TRANSPARENT_COLOR, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True)

        self.hline = self.canvas.create_line(0, 0, 0, 0, fill='red')
        self.vline = self.canvas.create_line(0, 0, 0, 0, fill='red')

        self.info_bg = self.canvas.create_rectangle(0, 0, 0, 0, outline='#fff')
        self.info_text = self.canvas.create_text(0, 0, anchor='nw', fill='#fff')

        self.mag_bg = self.canvas.create_rectangle(0, 0, 0, 0, fill='#000', outline='#888')
        self.mag_pixels = [
            self.canvas.create_rectangle(0, 0, 0, 0, outline='#222')
            for _ in range(SAMPLE_N * SAMPLE_N)
        ]
        self.mag_center = self.canvas.create_rectangle(0, 0, 0, 0, outline='#fff', width=2)

        self.canvas.bind('<Button-1>', self._on_click)
        self._sample_loop()

    def stop_overlay(self):
        self.running = False
        self.start_btn.config(text='Start (F1)')
        if self.sample_after_id and self.ov:
            self.ov.after_cancel(self.sample_after_id)
        if self.ov:
            self.ov.destroy()
        self.ov = None
        self.frozen_frame = None

    def _sample_loop(self):
        if not self.running:
            return

        x, y = pyautogui.position()
        N = SAMPLE_N
        cx, cy = x - self._vleft, y - self._vtop

        left = np.clip(cx - N // 2, 0, self._vwidth - N)
        top = np.clip(cy - N // 2, 0, self._vheight - N)

        arr = self.frozen_frame[top:top + N, left:left + N]

        center = N // 2
        b, g, r = arr[center, center][:3]
        hexcol = f'#{r:02x}{g:02x}{b:02x}'

        self.color_var.set(hexcol)
        self.hex_var.set(hexcol)
        self.swatch.config(bg=hexcol)

        self.canvas.coords(self.hline, 0, cy, self._vwidth, cy)
        self.canvas.coords(self.vline, cx, 0, cx, self._vheight)

        self.canvas.coords(self.info_bg, cx + 10, cy + 10, cx + 120, cy + 34)
        self.canvas.coords(self.info_text, cx + 14, cy + 14)
        self.canvas.itemconfig(self.info_bg, fill=hexcol)
        self.canvas.itemconfig(self.info_text, text=hexcol)

        if self.mag_enabled:
            size = N * MAG_SCALE
            offset = -size - 20 if self.mag_side == 'left' else 20
            mx, my = cx + offset, cy - size // 2

            self.canvas.coords(self.mag_bg, mx - 2, my - 2, mx + size + 2, my + size + 2)

            i = 0
            for j in range(N):
                for k in range(N):
                    b, g, r = arr[j, k][:3]
                    color = f'#{r:02x}{g:02x}{b:02x}'
                    px = mx + k * MAG_SCALE
                    py = my + j * MAG_SCALE
                    self.canvas.coords(self.mag_pixels[i], px, py, px + MAG_SCALE, py + MAG_SCALE)
                    self.canvas.itemconfig(self.mag_pixels[i], fill=color)
                    i += 1

            cpx = mx + center * MAG_SCALE
            cpy = my + center * MAG_SCALE
            self.canvas.coords(self.mag_center, cpx, cpy, cpx + MAG_SCALE, cpy + MAG_SCALE)

        self.sample_after_id = self.ov.after(SAMPLE_INTERVAL_MS, self._sample_loop)

    def toggle_magnifier(self):
        self.mag_enabled = not self.mag_enabled
        self.mag_btn.config(text=f'Magnifier: {"On" if self.mag_enabled else "Off"}')

    def toggle_mag_side(self):
        self.mag_side = 'right' if self.mag_side == 'left' else 'left'
        self.mag_side_btn.config(text=f'Mag Side: {self.mag_side.capitalize()}')

    def _on_click(self, _):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.hex_var.get())
        self.status_var.set('Copied')
        self.root.after(1500, lambda: self.status_var.set(''))
        self.stop_overlay()

    def apply_hex(self):
        try:
            s = self.hex_var.get().lstrip('#')
            int(s, 16)
            self.swatch.config(bg=f'#{s}')
        except:
            messagebox.showerror('Invalid', 'Invalid hex')

    def _on_close(self):
        keyboard.remove_hotkey('f1')
        self.sct.close()
        self.stop_overlay()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    ColorPickingApp().run()
