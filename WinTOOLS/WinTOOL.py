import os
import sys
import subprocess
import winreg
import ctypes
import threading
import time
import wmi
import psutil
import webbrowser
import re
import random
from pynput import mouse
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

# ================== ADMIN ==================
def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def run(cmd, timeout=3600):
    try:
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, startupinfo=info)
        return r.stdout + r.stderr
    except Exception as e: return f"[ERR] {e}"

# ================== ЛОГИ ==================
logs = []
logs_lock = threading.Lock()

def add_log(msg):
    timestamp = time.strftime("%H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    with logs_lock:
        logs.append(formatted)
        if len(logs) > 200: logs.pop(0)

def get_logs():
    with logs_lock:
        return "\n".join(logs)

# ================== ОПТИМИЗАЦИЯ ==================
def clean_temp():
    add_log("Начата очистка Temp...")
    for p in [os.environ.get("TEMP"), os.environ.get("TMP"), r"C:\Windows\Temp", r"C:\Windows\Prefetch"]:
        if p: run(f'del /q /s /f "{p}\\*" >nul 2>&1')
    add_log("Temp/Prefetch очищены.")

def clean_shaders_dns():
    add_log("Очистка кэша шейдеров и DNS...")
    run("ipconfig /flushdns")
    for path in [r"%LOCALAPPDATA%\D3DSCache", r"%LOCALAPPDATA%\NVIDIA\DXCache", r"%LOCALAPPDATA%\AMD\DxCache"]:
        p = os.path.expandvars(path)
        if os.path.exists(p): run(f'del /q /s /f "{p}\\*" >nul 2>&1')
    add_log("Кэш шейдеров и DNS очищены.")

def disable_services():
    add_log("Отключение телеметрии и лишних служб...")
    svcs = ["DiagTrack", "dmwappushservice", "SysMain", "WSearch", "MapsBroker", "RetailDemo", "XblAuthManager", "XblGameSave", "XboxNetApiSvc", "Spooler", "Fax"]
    for s in svcs:
        run(f'sc config "{s}" start= disabled')
        run(f'sc stop "{s}"')
    add_log("Телеметрия и службы (Spooler, Xbox) отключены.")

def power_tweaks():
    add_log("Настройка схемы питания...")
    run("powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c")
    run("powercfg -setacvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0")
    run("powercfg -setactive SCHEME_CURRENT")
    add_log("Схема питания MAX применена.")

def disable_hibernate():
    add_log("Отключение гибернации...")
    run("powercfg -h off")
    add_log("Гибернация отключена.")

def disable_uac_delay():
    add_log("Отключение задержки UAC...")
    try:
        k = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, "DelayedDesktopSwitchTimeout", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(k)
        add_log("Задержка UAC убрана.")
    except: add_log("Ошибка UAC.")

def reset_network():
    add_log("Сброс сети (Winsock/IP)...")
    run("ipconfig /release"); run("ipconfig /renew")
    run("netsh winsock reset"); run("netsh int ip reset")
    add_log("Сеть сброшена (нужна перезагрузка).")

def disable_ads():
    add_log("Отключение рекламы Windows...")
    try:
        k = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\CloudContent", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, "DisableWindowsConsumerFeatures", 0, winreg.REG_DWORD, 1)
        winreg.CloseKey(k)
        add_log("Реклама Windows отключена.")
    except: pass

def registry_tweaks():
    add_log("Твики реестра (GameDVR, Приоритет)...")
    def setreg(path, name, val):
        try:
            k = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, val)
            winreg.CloseKey(k)
        except: pass
    setreg(r"SOFTWARE\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", 0)
    setreg(r"System\GameConfigStore", "GameDVR_Enabled", 0)
    setreg(r"SYSTEM\CurrentControlSet\Control\PriorityControl", "Win32PrioritySeparation", 0x26)
    setreg(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "GPU Priority", 8)
    setreg(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Priority", 6)
    setreg(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Scheduling Category", "High")
    add_log("Реестр игр настроен.")

def disable_onedrive():
    add_log("Удаление OneDrive...")
    run("taskkill /f /im OneDrive.exe")
    run(r"C:\Windows\System32\OneDriveSetup.exe /uninstall")
    add_log("OneDrive отключен.")

def disable_cortana():
    add_log("Отключение Cortana...")
    run('reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search" /v AllowCortana /t REG_DWORD /d 0 /f')
    add_log("Cortana отключена.")

def disable_windows_update():
    add_log("Отключение Windows Update...")
    run('sc config wuauserv start= disabled')
    run('sc stop wuauserv')
    run('reg add "HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU" /v NoAutoUpdate /t REG_DWORD /d 1 /f')
    add_log("Windows Update отключен.")

def clean_winsxs():
    add_log("Очистка WinSxS (глубокая очистка системы)...")
    run("dism.exe /Online /Cleanup-Image /StartComponentCleanup /ResetBase")
    add_log("WinSxS очищен.")

def optimize_hdd_with_progress(progress_bar, root, log_func):
    log_func("Дефрагментация диска C: начата...")
    try:
        process = subprocess.Popen('defrag C: /O /V', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='cp866', startupinfo=subprocess.STARTUPINFO())
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                log_func(f"[DEFRAG] {line}")
                match = re.search(r'(\d+)%', line)
                if match:
                    progress_bar['value'] = int(match.group(1))
                    root.update_idletasks()
        process.stdout.close(); process.wait()
        progress_bar['value'] = 100
        log_func("Дефрагментация завершена.")
    except Exception as e:
        log_func(f"Ошибка дефрагментации: {e}")

def disable_indexing():
    add_log("Отключение индексации файлов...")
    run('sc config WSearch start= disabled'); run('sc stop WSearch')
    add_log("Служба индексации отключена.")

def disable_network_throttling():
    add_log("Отключение сетевого троттлинга...")
    try:
        k = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(k, "NetworkThrottlingIndex", 0, winreg.REG_DWORD, 0xffffffff)
        winreg.CloseKey(k)
        add_log("Сетевой троттлинг отключен.")
    except: pass

def disable_superfetch():
    add_log("Отключение Superfetch/SysMain...")
    run('sc config SysMain start= disabled'); run('sc stop SysMain')
    add_log("Superfetch отключен.")

def set_pagefile(size_mb):
    add_log(f"Настройка файла подкачки ({size_mb} МБ)...")
    try:
        run(f'wmic computersystem set AutomaticManagedPagefile=False')
        cmd = f'wmic pagefileset where name="C:\\\\pagefile.sys" set InitialSize={size_mb},MaximumSize={size_mb}'
        run(cmd)
        add_log(f"Файл подкачки установлен на {size_mb} МБ.")
    except Exception as e: add_log(f"Ошибка подкачки: {e}")

# ================== FPS ТЕСТ (ПОЛНОЭКРАННЫЙ) ==================
def start_fps_test(objects_count, log_func):
    test_win = tk.Toplevel()
    test_win.title("FPS Benchmark")
    test_win.attributes('-fullscreen', True) # На весь экран
    test_win.configure(bg="black")
    test_win.resizable(False, False)

    canvas = tk.Canvas(test_win, bg="black", highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    fps_list = []
    running = True
    frame_count = 0
    last_time = time.time()
    
    screen_w = test_win.winfo_screenwidth()
    screen_h = test_win.winfo_screenheight()

    shapes = []
    for _ in range(objects_count):
        x = random.randint(10, screen_w - 20)
        y = random.randint(10, screen_h - 20)
        size = random.randint(5, 25)
        vx = random.choice([-6, -5, -4, 4, 5, 6])
        vy = random.choice([-6, -5, -4, 4, 5, 6])
        color = random.choice(["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF", "#FFFFFF"])
        rect = canvas.create_rectangle(x, y, x+size, y+size, fill=color, outline="")
        shapes.append({"id": rect, "x": x, "y": y, "vx": vx, "vy": vy, "size": size})

    fps_text = canvas.create_text(30, 30, text="FPS: 0", fill="lime", font=("Consolas", 30, "bold"), anchor="nw")
    
    def stop_test(event=None):
        nonlocal running
        running = False
        test_win.destroy()
        if fps_list:
            avg_fps = sum(fps_list) / len(fps_list)
            max_fps = max(fps_list)
            min_fps = min(fps_list)
            result = f"=== РЕЗУЛЬТАТ БЕНЧМАРКА ===\nСредний FPS: {avg_fps:.1f}\nМаксимальный: {max_fps:.1f}\nМинимальный: {min_fps:.1f}"
            log_func(result)
            messagebox.showinfo("Результат FPS", result)
        else:
            log_func("FPS Тест: не удалось собрать данные.")
            messagebox.showwarning("FPS Тест", "Тест был слишком коротким. Попробуйте еще раз.")

    # Огромная кнопка СТОП внизу экрана
    btn_rect = canvas.create_rectangle(
        screen_w//2 - 200, screen_h - 90, 
        screen_w//2 + 200, screen_h - 20, 
        fill="#d83b3b", outline="white", width=3
    )
    btn_text = canvas.create_text(
        screen_w//2, screen_h - 55, 
        text="⏹ СТОП И ПОКАЗАТЬ РЕЗУЛЬТАТ", 
        fill="white", font=("Tahoma", 18, "bold")
    )
    
    canvas.tag_bind(btn_rect, "<Button-1>", stop_test)
    canvas.tag_bind(btn_text, "<Button-1>", stop_test)
    test_win.bind("<Escape>", stop_test)

    def update():
        nonlocal running, frame_count, last_time
        if not running:
            return

        for s in shapes:
            s["x"] += s["vx"]
            s["y"] += s["vy"]
            if s["x"] <= 0 or s["x"] + s["size"] >= screen_w:
                s["vx"] *= -1
                s["x"] = max(0, min(screen_w - s["size"], s["x"]))
            if s["y"] <= 0 or s["y"] + s["size"] >= screen_h:
                s["vy"] *= -1
                s["y"] = max(0, min(screen_h - s["size"], s["y"]))
            canvas.coords(s["id"], s["x"], s["y"], s["x"]+s["size"], s["y"]+s["size"])

        frame_count += 1
        now = time.time()
        if now - last_time >= 1.0:
            fps = frame_count / (now - last_time)
            fps_list.append(fps)
            frame_count = 0
            last_time = now
            canvas.itemconfig(fps_text, text=f"FPS: {fps:.1f}")

        test_win.after(1, update)

    update()

# ================== АНТИСРЫВ ==================
antishake_active = False
last_x, last_y = 0, 0
last_time = 0

def on_move(x, y):
    global antishake_active, last_x, last_y, last_time
    if not antishake_active: return
    current_time = time.time()
    dist = ((x - last_x)**2 + (y - last_y)**2)**0.5
    dt = current_time - last_time
    if dt > 0:
        speed = dist / dt
        if speed > 8000: return False
    last_x, last_y = x, y
    last_time = current_time

def toggle_antishake(enable):
    global antishake_active
    antishake_active = enable
    if enable:
        add_log("Антисрыв ВКЛ.")
        listener = mouse.Listener(on_move=on_move)
        listener.start()
    else: add_log("Антисрыв ВЫКЛ.")

# ================== CS2 ==================
def find_cs2_paths():
    paths = []
    drives = [f"{d}:\\" for d in "CDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
    for drive in drives:
        steam_paths = [
            os.path.join(drive, "Steam", "steamapps", "common", "Counter-Strike Global Offensive", "game", "csgo", "cfg"),
            os.path.join(drive, "Program Files (x86)", "Steam", "steamapps", "common", "Counter-Strike Global Offensive", "game", "csgo", "cfg"),
            os.path.join(drive, "Games", "Steam", "steamapps", "common", "Counter-Strike Global Offensive", "game", "csgo", "cfg")
        ]
        for p in steam_paths:
            if os.path.exists(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(p))))):
                paths.append(p)
    return paths

# ================== СКАНЕР И ЧИСТКА ==================
def get_processes():
    procs = []
    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'exe']):
        try:
            procs.append({
                'pid': p.info['pid'],
                'name': p.info['name'],
                'cpu': p.info['cpu_percent'],
                'ram': p.info['memory_info'].rss / (1024 * 1024),
                'exe': p.info['exe'] or "Недоступно"
            })
        except: pass
    return sorted(procs, key=lambda x: x['cpu'], reverse=True)

def get_startup():
    startup = []
    keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")
    ]
    for hive, key_path in keys:
        try:
            key = winreg.OpenKey(hive, key_path)
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    startup.append({"name": name, "path": value, "hive": "HKCU" if hive == winreg.HKEY_CURRENT_USER else "HKLM"})
                    i += 1
                except OSError: break
            winreg.CloseKey(key)
        except: pass
    return startup

# ================== GUI ==================
def launch_gui():
    root = tk.Tk()
    root.title("🚀 WinTools (Windows 95 Edition)")
    root.geometry("1000x800")
    root.configure(bg="#c0c0c0")
    root.option_add("*Font", "Tahoma 9")

    style = ttk.Style(root)
    style.theme_use("classic")

    top_frame = tk.Frame(root, bg="#c0c0c0", relief="raised", bd=2)
    top_frame.pack(fill="x", padx=2, pady=2)
    tk.Label(top_frame, text="Файл   Правка   Вид   Справка", bg="#c0c0c0", font=("Tahoma", 8)).pack(anchor="w")

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=5, pady=5)

    # --- Вкладка 1: Оптимизация ---
    tab1 = ttk.Frame(nb)
    nb.add(tab1, text="⚡ Оптимизация")
    
    canvas = tk.Canvas(tab1, bg="#c0c0c0", highlightthickness=0)
    scrollbar = ttk.Scrollbar(tab1, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg="#c0c0c0")
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    vars = {}
    opts = [
        ("clean_temp", "Очистка Temp/Prefetch"),
        ("clean_shaders", "Очистка кэша шейдеров + DNS"),
        ("services", "Отключить телеметрию и Xbox"),
        ("power", "Схема питания MAX"),
        ("hibernate", "Отключить гибернацию"),
        ("uac", "Отключить задержку UAC"),
        ("network", "Сброс сети (winsock)"),
        ("ads", "Отключить рекламу Windows"),
        ("reg", "Твики реестра игр"),
        ("onedrive", "Удалить OneDrive"),
        ("cortana", "Отключить Cortana"),
        ("winupdate", "🚫 Отключить Windows Update"),
        ("winsxs", "🧹 Глубокая очистка WinSxS"),
        ("indexing", "🚫 Отключить индексацию"),
        ("throttling", "🚫 Отключить троттлинг"),
        ("superfetch", "🚫 Отключить Superfetch")
    ]
    for i, (k, label) in enumerate(opts):
        v = tk.BooleanVar(value=True)
        vars[k] = v
        cb = tk.Checkbutton(scroll_frame, text=label, variable=v, bg="#c0c0c0", anchor="w", activebackground="#c0c0c0")
        cb.pack(fill="x", padx=5, pady=1)

    progress = ttk.Progressbar(tab1, orient="horizontal", length=100, mode="determinate")
    progress.pack(fill="x", padx=5, pady=5)

    log_box = tk.Text(tab1, bg="black", fg="lime", font=("Consolas", 9), height=10, relief="sunken", bd=2)
    log_box.pack(fill="both", expand=True, padx=5, pady=5)

    def update_logs_auto():
        current_text = log_box.get("1.0", tk.END).strip()
        new_text = get_logs().strip()
        if current_text != new_text:
            log_box.delete(1.0, tk.END)
            log_box.insert(tk.END, new_text)
            log_box.see(tk.END)
        root.after(1500, update_logs_auto)

    def run_opt():
        log_box.delete(1.0, tk.END)
        add_log("=== ЗАПУСК ОПТИМИЗАЦИИ ===")
        opts_checked = [k for k, v in vars.items() if v.get()]
        progress['value'] = 0
        def task():
            total_steps = len(opts_checked); current_step = 0
            if "clean_temp" in opts_checked: clean_temp(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "clean_shaders" in opts_checked: clean_shaders_dns(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "services" in opts_checked: disable_services(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "power" in opts_checked: power_tweaks(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "hibernate" in opts_checked: disable_hibernate(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "uac" in opts_checked: disable_uac_delay(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "network" in opts_checked: reset_network(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "ads" in opts_checked: disable_ads(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "reg" in opts_checked: registry_tweaks(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "onedrive" in opts_checked: disable_onedrive(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "cortana" in opts_checked: disable_cortana(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "winupdate" in opts_checked: disable_windows_update(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "winsxs" in opts_checked: clean_winsxs(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "indexing" in opts_checked: disable_indexing(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "throttling" in opts_checked: disable_network_throttling(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            if "superfetch" in opts_checked: disable_superfetch(); current_step += 1; progress['value'] = (current_step/total_steps)*100; root.update_idletasks()
            progress['value'] = 100; add_log("=== ОПТИМИЗАЦИЯ ЗАВЕРШЕНА ===")
        threading.Thread(target=task, daemon=True).start()

    btn_frame = tk.Frame(tab1, bg="#c0c0c0")
    btn_frame.pack(fill="x", pady=5)
    tk.Button(btn_frame, text="▶ ЗАПУСТИТЬ ОПТИМИЗАЦИЮ", bg="#c0c0c0", relief="raised", bd=2, command=run_opt).pack(side="left", padx=5)
    tk.Button(btn_frame, text="🔄 Обновить логи", bg="#c0c0c0", relief="raised", bd=2, command=lambda: (log_box.delete(1.0, tk.END), log_box.insert(tk.END, get_logs()))).pack(side="left", padx=5)

    def run_defrag():
        add_log("=== ЗАПУСК ДЕФРАГМЕНТАЦИИ ===")
        progress['value'] = 0
        threading.Thread(target=lambda: optimize_hdd_with_progress(progress, root, add_log), daemon=True).start()

    tk.Button(btn_frame, text="💾 ДЕФРАГМЕНТАЦИЯ (HDD)", bg="#c0c0c0", fg="blue", relief="raised", bd=2, command=run_defrag).pack(side="left", padx=5)

    root.after(1500, update_logs_auto)

    # --- Вкладка 2: FPS Тест ---
    tab2 = ttk.Frame(nb)
    nb.add(tab2, text="🎮 FPS Тест")
    
    tk.Label(tab2, text="Нагрузочный бенчмарк FPS", font=("Tahoma", 14, "bold"), bg="#c0c0c0").pack(pady=15)
    tk.Label(tab2, text="Настройте количество фигур и запустите тест.\nЧерез 10-15 секунд нажмите огромную кнопку СТОП на экране.", bg="#c0c0c0", justify="center").pack(pady=5)

    frame_slider = tk.Frame(tab2, bg="#c0c0c0")
    frame_slider.pack(pady=20)
    tk.Label(frame_slider, text="Количество фигур:", bg="#c0c0c0").pack(side="left", padx=5)
    slider_var = tk.IntVar(value=500)
    slider = tk.Scale(frame_slider, from_=100, to=2000, orient="horizontal", variable=slider_var, bg="#c0c0c0", length=400)
    slider.pack(side="left", padx=5)

    def start_test():
        count = slider_var.get()
        add_log(f"Запуск FPS-теста с {count} объектами...")
        start_fps_test(count, add_log)

    tk.Button(tab2, text="▶ ЗАПУСТИТЬ БЕНЧМАРК", bg="#c0c0c0", fg="green", font=("Tahoma", 12, "bold"), relief="raised", bd=3, command=start_test).pack(pady=30)

    # --- Вкладка 3: Конфиги ---
    tab3 = ttk.Frame(nb)
    nb.add(tab3, text="🎮 Конфиги")
    tk.Label(tab3, text="Настройки графики:", bg="#c0c0c0").pack(anchor="w", padx=5)
    cfg_txt = tk.Text(tab3, height=10, bg="white", font=("Consolas", 9), relief="sunken", bd=2)
    cfg_txt.pack(fill="x", padx=5, pady=2)
    cfg_txt.insert("1.0", "fps_max 0\nfps_max_ui 120\ncl_forcepreload 1\nrate 786432\ncl_updaterate 128\ncl_cmdrate 128\ncl_interp 0\ncl_interp_ratio 1\ncl_predict 1\ncl_lagcompensation 1\nr_dynamic 0\nmat_queue_mode 2\nr_lod 2\ncl_ragdoll_physics_enable 0\ncl_disablefreezecam 1\nsnd_mixahead 0.05\nsensitivity 2.0\nm_rawinput 1")
    
    tk.Label(tab3, text="Бинды (Клавиши):", bg="#c0c0c0").pack(anchor="w", padx=5)
    keys_txt = tk.Text(tab3, height=10, bg="white", font=("Consolas", 9), relief="sunken", bd=2)
    keys_txt.pack(fill="x", padx=5, pady=2)
    keys_txt.insert("1.0", 'bind "w" "+forward"\nbind "s" "+back"\nbind "a" "+moveleft"\nbind "d" "+moveright"\nbind "space" "+jump"\nbind "ctrl" "+duck"\nbind "shift" "+speed"\nbind "mouse1" "+attack"\nbind "mouse2" "+attack2"\nbind "r" "+reload"\nbind "e" "+use"\nbind "q" "lastinv"\nbind "1" "slot1"\nbind "2" "slot2"\nbind "3" "slot3"\nbind "4" "slot4"\nbind "5" "slot5"')
    
    def save_cfg():
        paths = find_cs2_paths()
        if paths:
            with open(os.path.join(paths[0], "autoexec.cfg"), "w") as f:
                f.write(cfg_txt.get("1.0", "end") + "\n\n// BINDS\n" + keys_txt.get("1.0", "end"))
            add_log("Конфиг сохранен."); messagebox.showinfo("Успех", "Сохранено!")
        else: messagebox.showerror("Ошибка", "Папка CS2 не найдена")
    
    tk.Button(tab3, text="💾 Сохранить в autoexec.cfg", bg="#c0c0c0", relief="raised", bd=2, command=save_cfg).pack(pady=5)

    # --- Вкладка 4: Антисрыв ---
    tab4 = ttk.Frame(nb)
    nb.add(tab4, text="🖱️ Антисрыв")
    def toggle_as():
        toggle_antishake(var_as.get())
        messagebox.showinfo("Статус", f"Антисрыв: {'ВКЛ' if var_as.get() else 'ВЫКЛ'}")
    var_as = tk.BooleanVar()
    tk.Checkbutton(tab4, text="Включить антисрыв мыши", variable=var_as, bg="#c0c0c0", command=toggle_as).pack(pady=20)

    # --- Вкладка 5: Вирт. память ---
    tab5 = ttk.Frame(nb)
    nb.add(tab5, text="🧠 Вирт. память")
    tk.Label(tab5, text="Размер файла подкачки (МБ):", bg="#c0c0c0").pack(pady=10)
    pf_entry = tk.Entry(tab5, relief="sunken", bd=2); pf_entry.insert(0, "8192"); pf_entry.pack()
    tk.Button(tab5, text="Применить", bg="#c0c0c0", relief="raised", bd=2, command=lambda: threading.Thread(target=lambda: set_pagefile(int(pf_entry.get()))).start()).pack(pady=5)

    # --- Вкладка 6: Сканер ---
    tab6 = ttk.Frame(nb)
    nb.add(tab6, text="🛡️ Сканер и Чистка")
    
    tk.Label(tab6, text="Нагрузка на систему (Топ процессов):", bg="#c0c0c0", font=("Tahoma", 9, "bold")).pack(anchor="w", padx=5, pady=5)
    
    cols = ("PID", "Имя", "CPU %", "RAM (MB)", "Путь")
    tree_proc = ttk.Treeview(tab6, columns=cols, show="headings", height=8)
    for c in cols: tree_proc.heading(c, text=c); tree_proc.column(c, width=100 if c != "Путь" else 300)
    tree_proc.pack(fill="x", padx=5)

    def refresh_procs():
        for i in tree_proc.get_children(): tree_proc.delete(i)
        for p in get_processes()[:20]:
            tree_proc.insert("", "end", values=(p['pid'], p['name'], f"{p['cpu']:.1f}", f"{p['ram']:.1f}", p['exe']))

    def kill_proc():
        sel = tree_proc.selection()
        if not sel: return
        item = tree_proc.item(sel[0])['values']
        pid, name = item[0], item[1]
        if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите завершить процесс {name} (PID: {pid})?"):
            try:
                psutil.Process(int(pid)).terminate()
                add_log(f"Процесс {name} завершен.")
                refresh_procs()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось завершить: {e}")

    btn_p_frame = tk.Frame(tab6, bg="#c0c0c0")
    btn_p_frame.pack(fill="x", padx=5, pady=5)
    tk.Button(btn_p_frame, text="🔄 Обновить процессы", bg="#c0c0c0", relief="raised", bd=2, command=refresh_procs).pack(side="left", padx=5)
    tk.Button(btn_p_frame, text="❌ Завершить процесс", bg="#c0c0c0", fg="red", relief="raised", bd=2, command=kill_proc).pack(side="left", padx=5)

    tk.Label(tab6, text="Автозагрузка (что стартует с Windows):", bg="#c0c0c0", font=("Tahoma", 9, "bold")).pack(anchor="w", padx=5, pady=5)
    
    cols_start = ("Имя", "Путь", "Реестр")
    tree_start = ttk.Treeview(tab6, columns=cols_start, show="headings", height=6)
    for c in cols_start: tree_start.heading(c, text=c); tree_start.column(c, width=150 if c != "Путь" else 400)
    tree_start.pack(fill="x", padx=5)

    def refresh_startup():
        for i in tree_start.get_children(): tree_start.delete(i)
        for s in get_startup():
            tree_start.insert("", "end", values=(s['name'], s['path'], s['hive']))

    def delete_startup():
        sel = tree_start.selection()
        if not sel: return
        item = tree_start.item(sel[0])['values']
        name, path, hive = item[0], item[1], item[2]
        if messagebox.askyesno("Подтверждение", f"Удалить '{name}' из автозагрузки?"):
            try:
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                hive_key = winreg.HKEY_CURRENT_USER if hive == "HKCU" else winreg.HKEY_LOCAL_MACHINE
                key = winreg.OpenKey(hive_key, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, name)
                winreg.CloseKey(key)
                add_log(f"Удалено из автозагрузки: {name}")
                refresh_startup()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить: {e}")

    btn_s_frame = tk.Frame(tab6, bg="#c0c0c0")
    btn_s_frame.pack(fill="x", padx=5, pady=5)
    tk.Button(btn_s_frame, text="🔄 Обновить автозагрузку", bg="#c0c0c0", relief="raised", bd=2, command=refresh_startup).pack(side="left", padx=5)
    tk.Button(btn_s_frame, text="❌ Удалить из автозагрузки", bg="#c0c0c0", fg="red", relief="raised", bd=2, command=delete_startup).pack(side="left", padx=5)

    def delete_file_manual():
        filepath = filedialog.askopenfilename(title="Выберите файл для удаления")
        if filepath:
            if messagebox.askyesno("Подтверждение", f"Вы уверены, что хотите УДАЛИТЬ этот файл?\n\n{filepath}"):
                try:
                    os.remove(filepath)
                    add_log(f"Файл удален: {filepath}")
                    messagebox.showinfo("Успех", "Файл удален!")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось удалить: {e}")

    tk.Button(tab6, text="🗑️ Удалить файл вручную (с подтверждением)", bg="#c0c0c0", fg="red", relief="raised", bd=2, command=delete_file_manual).pack(pady=10)

    # --- Вкладка 7: О программе ---
    tab7 = ttk.Frame(nb)
    nb.add(tab7, text="❤️ О программе")
    tk.Label(tab7, text="🚀 WinTools - Бесплатный оптимизатор Windows", font=("Tahoma", 12, "bold"), bg="#c0c0c0").pack(pady=10)
    tk.Label(tab7, text="Программа полностью бесплатная.\nПодписывайся на канал и смотри новые видео!", bg="#c0c0c0", justify="center").pack(pady=5)

    def open_tg(): webbrowser.open("https://t.me/qrt111y")
    def open_yt(): webbrowser.open("https://www.youtube.com/@qrt11y")

    btn_link_frame = tk.Frame(tab7, bg="#c0c0c0"); btn_link_frame.pack(pady=15)
    tk.Button(btn_link_frame, text="✈️ Телеграм-канал (qrt111y)", bg="#c0c0c0", fg="blue", relief="raised", bd=2, width=30, command=open_tg).pack(pady=5)
    tk.Button(btn_link_frame, text="▶️ YouTube (qrt11y)", bg="#c0c0c0", fg="red", relief="raised", bd=2, width=30, command=open_yt).pack(pady=5)

    root.mainloop()

# ================== ЗАПУСК ==================
if __name__ == "__main__":
    if not is_admin():
        try: ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{__file__}"', None, 1)
        except: pass
        sys.exit(0)
    
    launch_gui()