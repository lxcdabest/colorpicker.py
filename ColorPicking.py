from tkinter import Tk, Label, Canvas, Button, Entry, StringVar, Toplevel, Frame, messagebox
import mss
import numpy as np
import pyautogui
import keyboard

SAMPLE_INTERVAL_MS = 33  # ~30 Hz
TRANSPARENT_COLOR = '#ff00ff'  # transparent background color (Windows)
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
        self.color_label = Label(color_row, textvariable=self.color_var, relief='sunken')
        self.color_label.pack(side='left', padx=8)

        self.swatch = Label(color_row, text='      ', bg='#000000')
        self.swatch.pack(side='left', padx=8)

        self.hex_var = StringVar(value='')
        hex_row = Frame(center_frame)
        hex_row.pack(pady=(4, 4))
        self.hex_entry = Entry(hex_row, textvariable=self.hex_var, font=('Courier', 12, 'bold'),
                               width=9, justify='center')
        self.hex_entry.pack(side='left', padx=(0, 6))
        self.hex_entry.bind('<Return>', lambda e: self.apply_hex())
        Button(hex_row, text='Apply Hex', width=10, command=self.apply_hex).pack(side='left')

        self.status_var = StringVar(value='')
        self.status_label = Label(self.root, textvariable=self.status_var, relief='sunken',
                                  anchor='center', justify='center')
        self.status_label.pack(side='bottom', fill='x', pady=(4, 0))

        try:
            keyboard.add_hotkey('f1', self.toggle)
        except Exception:
            pass

        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    def toggle(self, *args):
        if self.running:
            self.stop_overlay()
        else:
            self.start_overlay()

    def start_overlay(self):
        if self.running:
            return
        self.running = True
        self.start_btn.config(text='Stop (F1)')

        try:
            self.ov = Toplevel(self.root)
            mon = self.sct.monitors[0]
            vleft, vtop = int(mon['left']), int(mon['top'])
            vwidth, vheight = int(mon['width']), int(mon['height'])
            self._vleft, self._vtop, self._vwidth, self._vheight = vleft, vtop, vwidth, vheight

            self.ov.geometry(f"{vwidth}x{vheight}+{vleft}+{vtop}")
            self.ov.overrideredirect(True)
            self.ov.attributes('-topmost', True)
            self.ov.config(bg=TRANSPARENT_COLOR)
            try:
                self.ov.attributes('-transparentcolor', TRANSPARENT_COLOR)
            except Exception:
                pass

            self.canvas = Canvas(self.ov, bg=TRANSPARENT_COLOR, highlightthickness=0)
            self.canvas.pack(fill='both', expand=True)
            self.hline = self.canvas.create_line(0, 0, 0, 0, fill='red', width=1)
            self.vline = self.canvas.create_line(0, 0, 0, 0, fill='red', width=1)
            self.info_bg = self.canvas.create_rectangle(10, 10, 170, 36, fill='#000000', outline='#ffffff')
            self.info_text = self.canvas.create_text(16, 18, anchor='nw', text='', fill='#ffffff', font=('Arial', 10))

            self.mag_pixel_rects = []
            self.mag_size = SAMPLE_N * MAG_SCALE
            self.mag_bg = self.canvas.create_rectangle(0, 0, 0, 0, fill='#000000', outline='#888888')
            for _ in range(SAMPLE_N * SAMPLE_N):
                rect = self.canvas.create_rectangle(0, 0, 0, 0, outline='#222222', fill='#000000')
                self.mag_pixel_rects.append(rect)
            self.mag_center_border = self.canvas.create_rectangle(0, 0, 0, 0, outline='#ffffff', width=2)

            self.canvas.bind('<Button-1>', self._on_click)
            self.ov.bind('<Escape>', lambda e: self.stop_overlay())

        except Exception as e:
            print('Failed to create overlay:', e)
            self.running = False
            self.start_btn.config(text='Start (F1)')
            return

        self._sample_loop()

    def stop_overlay(self):
        if not self.running:
            return
        self.running = False
        self.start_btn.config(text='Start (F1)')
        if self.sample_after_id and self.ov:
            try:
                self.ov.after_cancel(self.sample_after_id)
            except Exception:
                pass
        try:
            if hasattr(self, 'ov'):
                self.ov.destroy()
        except Exception:
            pass
        self.ov = None

    def _sample_loop(self):
        if not self.running:
            return
        try:
            x, y = pyautogui.position()
            N = SAMPLE_N
            vleft, vtop, vwidth, vheight = self._vleft, self._vtop, self._vwidth, self._vheight
            left = int(np.clip(x - N // 2, vleft, vleft + vwidth - N))
            top = int(np.clip(y - N // 2, vtop, vtop + vheight - N))
            region = {'left': left, 'top': top, 'width': N, 'height': N}

            img = self.sct.grab(region)
            arr = np.array(img)
            center = N // 2
            mask = (np.indices((N, N))[0] == center) | (np.indices((N, N))[1] == center)
            r, g, b = [int(np.median(arr[..., i][~mask])) for i in [2, 1, 0]]
            hexcol = '#%02x%02x%02x' % (r, g, b)
            combined = f'RGB({r},{g},{b}) {hexcol}'

            self.color_var.set(f'RGB({r},{g},{b})')
            self.hex_var.set(hexcol)
            self.swatch.config(bg=hexcol)

            rx = x - self.ov.winfo_rootx()
            ry = y - self.ov.winfo_rooty()
            w = self.ov.winfo_width()
            h = self.ov.winfo_height()
            self.canvas.coords(self.hline, 0, ry, w, ry)
            self.canvas.coords(self.vline, rx, 0, rx, h)

            self.canvas.coords(self.info_bg, rx+12, ry+12, rx+172, ry+36)
            self.canvas.coords(self.info_text, rx+18, ry+16)
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            fg = '#000' if luminance > 128 else '#fff'
            self.canvas.itemconfig(self.info_text, text=combined, fill=fg)
            self.canvas.itemconfig(self.info_bg, fill=hexcol)

        except Exception as e:
            print('Error:', e)

        self.sample_after_id = self.ov.after(SAMPLE_INTERVAL_MS, self._sample_loop)

    def toggle_magnifier(self):
        self.mag_enabled = not self.mag_enabled
        self.mag_btn.config(text=f"Magnifier: {'On' if self.mag_enabled else 'Off'}")

    def toggle_mag_side(self):
        self.mag_side = 'right' if self.mag_side == 'left' else 'left'
        self.mag_side_btn.config(text=f"Mag Side: {'Left' if self.mag_side=='left' else 'Right'}")

    def _on_click(self, event):
        x, y = pyautogui.position()
        N = 11
        sw, sh = pyautogui.size()
        left, top = max(0, x - N // 2), max(0, y - N // 2)
        reg = {'left': left, 'top': top, 'width': N, 'height': N}
        arr = np.array(self.sct.grab(reg))
        center = N // 2
        mask = (np.indices((N, N))[0] == center) | (np.indices((N, N))[1] == center)
        r, g, b = [int(np.median(arr[..., i][~mask])) for i in [2, 1, 0]]
        hexcol = '#%02x%02x%02x' % (r, g, b)
        txt = f'RGB({r},{g},{b}) {hexcol}'

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self.status_var.set('Copied to clipboard')
            self.root.after(2000, lambda: self.status_var.set(''))
        except Exception as e:
            print('Clipboard error:', e)

        self.root.after(200, self.stop_overlay)

    def apply_hex(self):
        try:
            s = self.hex_var.get().strip().lstrip('#')
            if len(s) != 6 or any(c not in '0123456789abcdefABCDEF' for c in s):
                messagebox.showerror('Invalid hex', 'Enter hex as RRGGBB or #RRGGBB')
                return
            r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
            hexcol = f'#{s.lower()}'
            self.color_var.set(f'RGB({r},{g},{b})')
            self.swatch.config(bg=hexcol)

            txt = f'RGB({r},{g},{b}) {hexcol}'
            self.root.clipboard_clear()
            self.root.clipboard_append(txt)
            self.status_var.set('Hex applied and copied')
            self.root.after(2000, lambda: self.status_var.set(''))
        except Exception as e:
            messagebox.showerror('Error', f'Failed to apply hex: {e}')

    def _on_close(self):
        try:
            keyboard.remove_hotkey('f1')
        except Exception:
            pass
        try:
            self.sct.close()
        except Exception:
            pass
        try:
            self.stop_overlay()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    ColorPickingApp().run()