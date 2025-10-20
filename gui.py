import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
from seleniumwire import webdriver
import threading
import requests
import os

# ---------------- Proxy + Browser Management ---------------- #
browsers = []
grid_positions = {}
MAX_COLS = 10
proxy_index = 0
lock = threading.Lock()
proxy_file_path = None

def log_message(msg):
    log_box.config(state="normal")
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)
    log_box.config(state="disabled")

def load_proxies():
    """Read proxy lines from selected file."""
    global proxy_file_path
    if not proxy_file_path or not os.path.exists(proxy_file_path):
        log_message("⚠️ Please select a valid proxy file first.")
        return []
    with open(proxy_file_path, "r") as f:
        return [line.strip() for line in f if line.strip()]

def test_proxy(proxy_line):
    """Quickly check if a proxy works before using it."""
    try:
        username, password_host = proxy_line.split(":", 1)
        password, host_port = password_host.split("@", 1)
        host, port = host_port.split(":")
        proxy_dict = {
            "http": f"socks5://{username}:{password}@{host}:{port}",
            "https": f"socks5://{username}:{password}@{host}:{port}",
        }
        requests.get("https://www.google.com", proxies=proxy_dict, timeout=5)
        return True
    except Exception:
        return False

def get_next_proxy(proxies):
    global proxy_index
    with lock:
        if not proxies:
            return None
        proxy = proxies[proxy_index % len(proxies)]
        proxy_index += 1
        return proxy

def launch_browser(proxy_line, url, headless):
    try:
        username, password_host = proxy_line.split(":", 1)
        password, host_port = password_host.split("@", 1)
        host, port = host_port.split(":")
        options = {
            'proxy': {
                'http': f'socks5://{username}:{password}@{host}:{port}',
                'https': f'socks5://{username}:{password}@{host}:{port}',
                'no_proxy': 'localhost,127.0.0.1'
            },
            'request_storage': 'memory',
            'request_storage_max_size': 50
        }

        chrome_options = webdriver.ChromeOptions()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(seleniumwire_options=options, options=chrome_options)
        driver.get(url)
        log_message(f"✅ Browser launched with proxy: {host}:{port}")
        return driver
    except Exception as e:
        log_message(f"⚠️ Proxy failed: {proxy_line} -> {e}")
        return None

def close_all_browsers():
    for b in browsers[:]:
        try:
            b['driver'].quit()
        except:
            pass
        browsers.remove(b)
    log_message("🛑 All browser instances closed.")


# ---------------- Grid Management ---------------- #
def get_next_grid_position():
    for i in range(1000):
        row, col = divmod(i, MAX_COLS)
        if (row, col) not in grid_positions:
            return row, col
    return 0, 0

def reserve_grid_position(row, col, square):
    grid_positions[(row, col)] = square

def release_grid_position(square):
    for pos, sq in list(grid_positions.items()):
        if sq == square:
            del grid_positions[pos]
            break


# ---------------- GUI Logic ---------------- #
def start_launch():
    url = url_entry.get().strip()
    if not url:
        log_message("⚠️ Please enter a URL.")
        return

    proxies = load_proxies()
    if not proxies:
        log_message("⚠️ No proxies loaded.")
        return

    try:
        num_instances = int(num_entry.get())
    except ValueError:
        log_message("⚠️ Invalid number of browsers.")
        return

    headless = headless_var.get()

    def create_instance():
        proxy_line = get_next_proxy(proxies)
        if not proxy_line:
            log_message("⚠️ No proxies available.")
            return

        if not test_proxy(proxy_line):
            log_message(f"⚠️ Proxy failed test: {proxy_line}")
            return

        driver = launch_browser(proxy_line, url, headless)
        if driver is None:
            return

        row, col = get_next_grid_position()
        square = tk.Button(grid_frame, bg="green", width=4, height=2)
        square.grid(row=row, column=col, padx=4, pady=4)
        reserve_grid_position(row, col, square)

        browsers.append({'driver': driver, 'square': square})

        def on_click():
            try:
                driver.quit()
            except:
                pass
            square.destroy()
            release_grid_position(square)
            browsers[:] = [b for b in browsers if b['square'] != square]
            log_message("🟡 Browser closed.")

        square.configure(command=on_click)

    for _ in range(num_instances):
        threading.Thread(target=create_instance, daemon=True).start()


# ---------------- File Selector ---------------- #
def select_proxy_file():
    global proxy_file_path
    file_path = filedialog.askopenfilename(
        title="Select Proxy File",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if file_path:
        proxy_file_path = file_path
        proxy_label.config(text=os.path.basename(file_path))
        log_message(f"📂 Loaded proxy file: {file_path}")


# ---------------- Main GUI ---------------- #
root = tk.Tk()
root.title("Socks5 Proxy Launcher")
root.geometry("540x520")
root.resizable(False, False)
root.protocol("WM_DELETE_WINDOW", lambda: (close_all_browsers(), root.destroy()))

# --- Top Controls --- #
controls = ttk.LabelFrame(root, text="Browser Settings", padding=10)
controls.pack(fill="x", padx=10, pady=10)

tk.Label(controls, text="URL:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
url_entry = tk.Entry(controls, width=40)
url_entry.grid(row=0, column=1, padx=5, pady=5)
url_entry.insert(0, "")

tk.Label(controls, text="Instances:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
num_entry = tk.Entry(controls, width=10)
num_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
num_entry.insert(0, "1")

headless_var = tk.BooleanVar()
tk.Checkbutton(controls, text="Headless mode", variable=headless_var).grid(row=2, column=1, sticky="w", padx=5, pady=5)

# --- Proxy File Selection --- #
tk.Label(controls, text="Proxy file:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
proxy_btn = ttk.Button(controls, text="Browse...", command=select_proxy_file)
proxy_btn.grid(row=3, column=1, sticky="w", padx=5)
proxy_label = tk.Label(controls, text="(none selected)", fg="gray")
proxy_label.grid(row=4, column=1, sticky="w", padx=5)

launch_btn = ttk.Button(controls, text="Launch Browsers", command=start_launch)
launch_btn.grid(row=5, column=1, sticky="w", pady=5)

# --- Grid Area --- #
grid_frame = ttk.LabelFrame(root, text="Active Browsers", padding=10)
grid_frame.pack(fill="both", expand=True, padx=10, pady=5)

# --- Log Window --- #
log_box = scrolledtext.ScrolledText(root, width=60, height=8, state="disabled", wrap="word")
log_box.pack(fill="both", padx=10, pady=10)

root.mainloop()
