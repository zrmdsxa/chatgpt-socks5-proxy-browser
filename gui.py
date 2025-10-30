import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import time
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ---------------- Global Variables ---------------- #
browsers = []
proxies = []
proxy_index = 0
lock = threading.Lock()
running = True
proxy_file_path = None

# ---------------- Logging ---------------- #
def log_message(msg):
    log_box.config(state="normal")
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)
    log_box.config(state="disabled")

# ---------------- Proxy Handling ---------------- #
def load_proxies():
    global proxies
    if not proxy_file_path:
        log_message("⚠️ Please select a proxy file.")
        return
    with open(proxy_file_path, "r") as f:
        proxies = [line.strip() for line in f if line.strip()]
    log_message(f"📂 Loaded {len(proxies)} proxies from file.")

def get_next_proxy():
    global proxy_index
    with lock:
        if not proxies:
            return None
        proxy = proxies[proxy_index % len(proxies)]
        proxy_index += 1
        return proxy

# ---------------- Browser Management ---------------- #
def create_instance(url):
    proxy = get_next_proxy()
    if not proxy:
        log_message("⚠️ No proxies loaded.")
        return

    # Yellow square immediately
    square = tk.Button(grid_frame, bg="yellow", width=4, height=2)
    entry = {"driver": None, "square": square, "loading": True}
    browsers.append(entry)
    refresh_squares()

    # Allow canceling yellow square
    def cancel_launch():
        if entry in browsers:
            browsers.remove(entry)
        try:
            square.destroy()
        except:
            pass
        refresh_squares()
        log_message("🟡 Browser launch cancelled.")

    square.configure(command=cancel_launch)

    # Launch browser in background thread
    def launch_browser():
        try:
            seleniumwire_options = {
                "proxy": {
                    "http": f"socks5://{proxy}",
                    "https": f"socks5://{proxy}",
                    "no_proxy": "localhost,127.0.0.1"
                },
                "request_storage": "memory",
                "request_storage_max_size": 50
            }

            chrome_options = Options()
            if headless_var.get():
                chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--log-level=3")

            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options,
                seleniumwire_options=seleniumwire_options
            )

            entry["driver"] = driver
            entry["loading"] = False

            # Change square to green and update click handler
            square.configure(bg="green")

            def close_browser():
                threading.Thread(target=_close_browser_thread, args=(entry,), daemon=True).start()

            square.configure(command=close_browser)

            driver.get(url if url.strip() else "about:blank")
            log_message(f"🟢 Browser launched with proxy {proxy}")

            # Monitor driver
            while running:
                try:
                    _ = driver.title
                    time.sleep(1)
                except:
                    break
        except Exception as e:
            log_message(f"❌ Failed to launch with proxy {proxy}: {e}")
            with lock:
                if entry in browsers:
                    browsers.remove(entry)
            try:
                square.destroy()
            except:
                pass
            refresh_squares()

    threading.Thread(target=launch_browser, daemon=True).start()

def _close_browser_thread(entry):
    driver = entry.get("driver")
    if driver:
        try:
            driver.quit()
        except:
            pass
    with lock:
        if entry in browsers:
            browsers.remove(entry)
    try:
        entry["square"].destroy()
    except:
        pass
    refresh_squares()
    log_message("🟥 Browser closed.")

def refresh_squares():
    for i, b in enumerate(browsers):
        b["square"].grid(row=i // 10, column=i % 10, padx=4, pady=4)

def close_all_browsers():
    global running
    running = False
    log_message("🔻 Closing all browsers...")
    for b in browsers[:]:
        _close_browser_thread(b)
    log_message("✅ All browsers closed.")

# ---------------- GUI ---------------- #
root = tk.Tk()
root.title("Socks5 Proxy Launcher")
root.geometry("540x520")
root.minsize(540, 520)
root.protocol("WM_DELETE_WINDOW", lambda: (close_all_browsers(), root.destroy()))

# --- Browser Settings Frame --- #
settings_frame = ttk.LabelFrame(root, text="Browser Settings", padding=10)
settings_frame.pack(fill="x", padx=10, pady=10)

tk.Label(settings_frame, text="Target URL:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
url_entry = tk.Entry(settings_frame, width=40)
url_entry.grid(row=0, column=1, padx=5, pady=5)
url_entry.insert(0, "")

tk.Label(settings_frame, text="Instances:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
num_entry = tk.Entry(settings_frame, width=10)
num_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
num_entry.insert(0, "1")

headless_var = tk.BooleanVar()
tk.Checkbutton(settings_frame, text="Headless mode", variable=headless_var).grid(row=2, column=1, sticky="w", padx=5, pady=5)

tk.Label(settings_frame, text="Proxy file:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
proxy_label = tk.Label(settings_frame, text="(none selected)", fg="gray")
proxy_label.grid(row=4, column=1, sticky="w", padx=5)

def select_proxy_file():
    global proxy_file_path
    file_path = filedialog.askopenfilename(
        title="Select Proxy File",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if file_path:
        proxy_file_path = file_path
        proxy_label.config(text=file_path.split("/")[-1])
        load_proxies()

proxy_btn = ttk.Button(settings_frame, text="Browse...", command=select_proxy_file)
proxy_btn.grid(row=3, column=1, sticky="w", padx=5, pady=5)

def start_launch():
    url = url_entry.get().strip()
    try:
        num_instances = int(num_entry.get())
    except ValueError:
        log_message("⚠️ Invalid number of browsers.")
        return

    for _ in range(num_instances):
        create_instance(url)
        time.sleep(0.2)

launch_btn = ttk.Button(settings_frame, text="Launch Browsers", command=lambda: threading.Thread(target=start_launch, daemon=True).start())
launch_btn.grid(row=5, column=1, columnspan=2, sticky="w", pady=10)

# --- Active Browsers Frame --- #
grid_frame = ttk.LabelFrame(root, text="Active Browsers", padding=10)
grid_frame.pack(fill="both", expand=True, padx=10, pady=5)

# --- Log Window --- #
log_box = scrolledtext.ScrolledText(root, width=60, height=8, state="disabled", wrap="word")
log_box.pack(fill="both", padx=10, pady=10, expand=True)

root.mainloop()
