import psutil
import time
from database import DatabaseManager

def monitor_system():
    while True:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        print(f"CPU: {cpu_percent}%")
        print(f"Memory: {memory.percent}%")
        print(f"Disk: {disk.percent}%")
        
        if cpu_percent > 80:
            print("High CPU usage!")
        
        if memory.percent > 85:
            print("High memory usage!")
        
        time.sleep(60)

if __name__ == '__main__':
    monitor_system()
