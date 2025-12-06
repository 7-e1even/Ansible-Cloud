import paramiko
import os
import stat
from werkzeug.utils import secure_filename
from typing import List, Dict, Any, BinaryIO
from app.core.database import Database

class SFTPService:
    def __init__(self, db: Database):
        self.db = db

    def _get_ssh_client(self, host_id: int):
        host = self.db.get_host(host_id)
        if not host:
            raise ValueError("Host not found")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        connect_args = {
            'hostname': host['address'],
            'port': host['port'],
            'username': host['username']
        }
        if host['auth_method'] == 'password':
            connect_args['password'] = host['password']
            
        ssh.connect(**connect_args)
        return ssh

    def list_files(self, host_id: int, path: str) -> List[Dict[str, Any]]:
        with self._get_ssh_client(host_id) as ssh:
            with ssh.open_sftp() as sftp:
                file_list = []
                for entry in sftp.listdir_attr(path):
                    file_list.append({
                        'name': entry.filename,
                        'type': 'directory' if stat.S_ISDIR(entry.st_mode) else 'file',
                        'size': entry.st_size,
                        'mtime': entry.st_mtime
                    })
                return file_list

    def mkdir(self, host_id: int, path: str) -> None:
        with self._get_ssh_client(host_id) as ssh:
            with ssh.open_sftp() as sftp:
                try:
                    sftp.stat(path)
                    raise ValueError("Directory already exists")
                except IOError:
                    sftp.mkdir(path)

    def upload(self, host_id: int, remote_path: str, files: List[Any]) -> None:
        with self._get_ssh_client(host_id) as ssh:
            with ssh.open_sftp() as sftp:
                for file in files:
                    if file.filename:
                        filename = secure_filename(file.filename)
                        final_remote_path = os.path.join(remote_path, filename).replace('\\', '/')
                        
                        temp_path = os.path.join('/tmp', filename)
                        # Ensure /tmp exists or use a better temp dir
                        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                        
                        try:
                            # In FastAPI, UploadFile has a .file attribute which is a file-like object
                            # or we can read it. Here assuming 'file' is UploadFile or similar wrapper
                            with open(temp_path, "wb") as buffer:
                                buffer.write(file.file.read())
                            
                            sftp.put(temp_path, final_remote_path)
                        finally:
                            if os.path.exists(temp_path):
                                os.remove(temp_path)

    def rename(self, host_id: int, old_path: str, new_path: str) -> None:
        with self._get_ssh_client(host_id) as ssh:
            with ssh.open_sftp() as sftp:
                try:
                    sftp.stat(new_path)
                    raise ValueError("Destination already exists")
                except IOError:
                    sftp.rename(old_path, new_path)

    def touch(self, host_id: int, path: str) -> None:
        with self._get_ssh_client(host_id) as ssh:
            with ssh.open_sftp() as sftp:
                try:
                    sftp.stat(path)
                    raise ValueError("File already exists")
                except IOError:
                    with sftp.file(path, 'w') as f:
                        f.write('')

    def read_file(self, host_id: int, path: str) -> str:
        with self._get_ssh_client(host_id) as ssh:
            with ssh.open_sftp() as sftp:
                with sftp.file(path, 'r') as f:
                    return f.read().decode('utf-8', errors='replace')

    def write_file(self, host_id: int, path: str, content: str) -> None:
        with self._get_ssh_client(host_id) as ssh:
            with ssh.open_sftp() as sftp:
                with sftp.file(path, 'w') as f:
                    f.write(content)

    def delete(self, host_id: int, path: str, is_directory: bool) -> None:
        with self._get_ssh_client(host_id) as ssh:
            with ssh.open_sftp() as sftp:
                if is_directory:
                    if sftp.listdir(path):
                        raise ValueError("Directory is not empty")
                    sftp.rmdir(path)
                else:
                    sftp.remove(path)

    def download(self, host_id: int, path: str) -> str:
        """Downloads file to a temp path and returns the path"""
        with self._get_ssh_client(host_id) as ssh:
            with ssh.open_sftp() as sftp:
                file_attr = sftp.stat(path)
                if stat.S_ISDIR(file_attr.st_mode):
                    raise ValueError("Cannot download a directory")
                
                filename = os.path.basename(path)
                temp_path = os.path.join('/tmp', secure_filename(filename))
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                
                sftp.get(path, temp_path)
                return temp_path
