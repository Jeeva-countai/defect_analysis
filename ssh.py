import subprocess, time


class SSHManager:
    def __init__(self, username, password):
        self.username = username
        self.password = password

    def run_command(self, hostname, command, max_attempts=10, delay=10):
        try:
            for attempt in range(max_attempts):
                try:
                    # SSH command with options
                    ssh_command = f'ssh -o StrictHostKeyChecking=no {self.username}@{hostname} "echo \'{self.password}\' | sudo -S bash -c \'{command}\'"'
                    print(ssh_command)

                    # Execute SSH command using subprocess
                    print(f"Executing SSH command on {hostname}: {command}")
                    result = subprocess.run(ssh_command, shell=True, check=True, capture_output=True, text=True)
                    print("RESULT",result)
                    # Print command output
                    print(f"Command output:")
                    print(result.stdout)

                    return True,result.stdout.strip()  # Return command output

                except subprocess.CalledProcessError as e:
                    print(f"Attempt {attempt+1} failed. Error executing command on {hostname}: {e}")
                    time.sleep(delay)  # Retry delay

            print(f"Max attempts reached. Skipping command '{command}' for {hostname}.")
            return False,None  # Return None if max attempts reached

        except Exception as e:
            print(f"Error executing SSH command on {hostname}: {e}")
            return False,None  # Return None on other exceptions