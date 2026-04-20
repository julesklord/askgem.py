import datetime

def get_current_time():
    """Extrae y retorna la hora actual de la máquina."""
    now = datetime.datetime.now()
    return now.strftime("%H:%M:%S")

if __name__ == "__main__":
    current_time = get_current_time()
    print(f"La hora actual es: {current_time}")