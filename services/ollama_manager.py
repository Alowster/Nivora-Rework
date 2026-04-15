import subprocess

def ensure_ollama_running():
    result = subprocess.run(["tasklist"], capture_output=True, text=True)
    if "ollama.exe" not in result.stdout:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def kill_ollama():
    subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], capture_output=True)

