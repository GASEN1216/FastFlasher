import os
import glob
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports
import subprocess

CONFIG_FILE = "config.ini"

class FastFlasherApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("FastFlasher")
        self.geometry("560x500")
        self.resizable(False, False)

        self.logo_label = ttk.Label(self, text="FastFlasher", font=("Helvetica", 18, "bold"))
        self.logo_label.pack(pady=10)

        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.create_widgets()
        self.scan_ports()
        self.scan_mcuboot()
        self.load_config()

    def create_widgets(self):
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill="x", pady=5)

        ttk.Label(control_frame, text="串口选择:").grid(row=0, column=0, sticky="w")
        self.port_cb = ttk.Combobox(control_frame, state="readonly")
        self.port_cb.grid(row=0, column=1, sticky="ew")
        self.port_cb.bind("<<ComboboxSelected>>", lambda e: self.save_config())

        ttk.Label(control_frame, text="波特率:").grid(row=1, column=0, sticky="w")
        self.baud_cb = ttk.Combobox(control_frame, state="readonly", values=["9600", "115200", "230400"])
        self.baud_cb.grid(row=1, column=1, sticky="ew")
        self.baud_cb.bind("<<ComboboxSelected>>", lambda e: self.save_config())

        ttk.Label(control_frame, text="MCUBoot工具:").grid(row=2, column=0, sticky="w")
        self.mcuboot_cb = ttk.Combobox(control_frame, state="readonly")
        self.mcuboot_cb.grid(row=2, column=1, sticky="ew")
        self.mcuboot_cb.bind("<<ComboboxSelected>>", lambda e: self.save_config())

        ttk.Label(control_frame, text="固件:").grid(row=3, column=0, sticky="w")
        self.target_label = ttk.Label(control_frame, text="hyp60.exe")
        self.target_label.grid(row=3, column=1, sticky="w")

        for i in range(2):
            control_frame.columnconfigure(i, weight=1)

        self.output_text = tk.Text(self.main_frame, height=15, state='disabled', bg="#f5f5f5")
        self.output_text.pack(fill="both", pady=10)

        self.start_btn = ttk.Button(self, text="开始烧录", command=self.start_flashing)
        self.start_btn.pack(pady=10)

        self.status_label = ttk.Label(self, text="", foreground="blue")
        self.status_label.pack()

    def append_output(self, text):
        self.output_text.config(state='normal')
        self.output_text.insert('end', text)
        self.output_text.see('end')
        self.output_text.config(state='disabled')

    def scan_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_cb['values'] = ports
        if ports:
            self.port_cb.current(0)

    def scan_mcuboot(self):
        mcuboots = glob.glob("*-mcuboot.exe")
        if mcuboots:
            self.mcuboot_cb['values'] = mcuboots
            self.mcuboot_cb.current(0)
        else:
            messagebox.showerror("错误", "当前目录未找到mcuboot工具！")

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            f.write(f"COM_PORT={self.port_cb.get()}\n")
            f.write(f"BAUD_RATE={self.baud_cb.get()}\n")
            f.write(f"mcuboot={self.mcuboot_cb.get()}\n")

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            config = {}
            with open(CONFIG_FILE, "r") as f:
                for line in f:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        config[key.strip()] = value.strip()
            # 加载配置
            if "BAUD_RATE" in config:
                self.baud_cb.set(config["BAUD_RATE"])
            if "mcuboot" in config:
                self.mcuboot_cb.set(config["mcuboot"])
            if "COM_PORT" in config:
                self.port_cb.set(config["COM_PORT"])

    def start_flashing(self):
        threading.Thread(target=self.flash_process, daemon=True).start()

    def flash_process(self):
        com_port = self.port_cb.get()
        baud = self.baud_cb.get()
        mcuboot = self.mcuboot_cb.get()
        target = "xxx.exe"

        if not all([com_port, baud, mcuboot]):
            messagebox.showerror("错误", "请确保所有选项都已选择！")
            return

        if not os.path.exists(mcuboot) or not os.path.exists(target):
            messagebox.showerror("错误", "缺少必要的文件！请确保hyp60.exe和mcuboot*.exe在当前目录！")
            return

        self.status_label.config(text="烧录中...请稍候...")
        self.start_btn.config(state="disabled")

        try:
            self.append_output(f"\n>> 运行 {mcuboot}\n")
            proc1 = subprocess.Popen([mcuboot], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc1.stdout:
                self.append_output(line)
            proc1.wait()

            if proc1.returncode != 0:
                raise subprocess.CalledProcessError(proc1.returncode, mcuboot)

            self.append_output(f"\n>> MCUboot执行成功，开始执行 {target}\n")

            proc2 = subprocess.Popen([target], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in proc2.stdout:
                self.append_output(line)
            proc2.wait()

            if proc2.returncode != 0:
                raise subprocess.CalledProcessError(proc2.returncode, target)

            self.status_label.config(text="执行成功！请检查输出窗口是否成功烧录")
            messagebox.showinfo("完成", "执行成功！")
            self.save_config()
        except subprocess.CalledProcessError as e:
            self.status_label.config(text="执行失败！")
            messagebox.showerror("错误", f"烧录过程中发生错误！\n{e}")
        except FileNotFoundError as e:
            self.status_label.config(text="找不到文件！")
            messagebox.showerror("错误", f"找不到文件！\n{e}")
        finally:
            self.start_btn.config(state="normal")

if __name__ == "__main__":
    app = FastFlasherApp()
    app.mainloop()
