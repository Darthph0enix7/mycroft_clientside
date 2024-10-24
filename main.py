import platform
import subprocess

def run_script(script_name):
    try:
        subprocess.run(['python', script_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to run {script_name}: {e}")

def main():
    current_os = platform.system().lower()
    current_arch = platform.machine().lower()
    
    if current_os == 'windows':
        run_script('windows_script.py')
        print('Would run: windows_script.py')
    elif current_os == 'linux':
        if 'arm' in current_arch or 'aarch' in current_arch:
            run_script('linux_arm_script.py')
            print('Would run: linux_arm_script.py')
        elif 'x86_64' in current_arch:
            run_script('linux_x64_script.py')
            print('Would run: linux_x64_script.py')
        else:
            print(f"Unsupported Linux architecture: {current_arch}")
    else:
        print(f"Unsupported OS or architecture: {current_os} {current_arch}")

if __name__ == "__main__":
    main()