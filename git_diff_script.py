import subprocess

def get_current_branch():
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).strip().decode("utf-8")
        return branch
    except subprocess.CalledProcessError as e:
        print(f"Error al obtener la rama actual: {e}")
        return None

def show_git_diff():
    current_branch = get_current_branch()
    if not current_branch:
        return

    print(f"Obteniendo los últimos cambios de 'origin'...")
    try:
        subprocess.run(["git", "fetch", "origin"], check=True)
        print("Cambios obtenidos. Generando diff...")
        command = ["git", "diff", f"origin/{current_branch}"]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        if result.stdout:
            print(result.stdout)
        else:
            print(f"No hay diferencias entre la rama local '{current_branch}' y 'origin/{current_branch}'.")
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar el comando git: {e}")
        print(f"Stderr: {e.stderr}")
    except FileNotFoundError:
        print("Error: 'git' no se encontró. Asegúrate de que Git esté instalado y en tu PATH.")

if __name__ == "__main__":
    show_git_diff()
