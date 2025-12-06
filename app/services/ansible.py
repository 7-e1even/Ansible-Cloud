import os
import tempfile
import json
import subprocess
import threading
import re
import shutil
from app.utils.crypto import CryptoUtils
from app.core.database import Database
import logging
import sys
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import Ansible modules
try:
    import ansible.constants as C
    from ansible.parsing.dataloader import DataLoader
    from ansible.inventory.manager import InventoryManager
    from ansible.vars.manager import VariableManager
    from ansible.playbook.play import Play
    from ansible.executor.task_queue_manager import TaskQueueManager
    from ansible.plugins.callback import CallbackBase
    from ansible import context
    from ansible.module_utils.common.collections import ImmutableDict
    ANSIBLE_AVAILABLE = True
except ImportError:
    ANSIBLE_AVAILABLE = False
    logger.warning("Ansible package not found. Ansible features will be disabled.")
    # Define dummy classes to avoid NameError during class definition
    class CallbackBase:
        pass
    class TaskQueueManager:
        pass
    class ImmutableDict(dict):
        pass

if ANSIBLE_AVAILABLE:
    class ResultCallback(CallbackBase):
        """Custom callback to handle task results"""
        def __init__(self):
            super().__init__()
            self.host_ok = {}
            self.host_unreachable = {}
            self.host_failed = {}

        def v2_runner_on_ok(self, result):
            self.host_ok[result._host.get_name()] = result

        def v2_runner_on_failed(self, result, ignore_errors=False):
            self.host_failed[result._host.get_name()] = result

        def v2_runner_on_unreachable(self, result):
            self.host_unreachable[result._host.get_name()] = result
else:
    class ResultCallback:
        pass

class AnsibleService:
    def __init__(self, db: Database):
        self.db = db
        self.crypto = CryptoUtils()
        
        if ANSIBLE_AVAILABLE:
            # Initialize context.CLIARGS only once effectively, though it's global
            # We set it here to ensure it's set when service is used
            context.CLIARGS = ImmutableDict(
                connection='smart',
                module_path=None,
                forks=50,
                become=None,
                become_method=None,
                become_user=None,
                check=False,
                diff=False,
                verbosity=0
            )
        else:
            logger.warning("AnsibleService initialized but Ansible is not available.")
        
        self.TEMP_DIR = os.path.join(os.getcwd(), 'ansible_temp')
        if not os.path.exists(self.TEMP_DIR):
            os.makedirs(self.TEMP_DIR)

    def generate_inventory(self, hosts):
        """Generate temporary inventory file"""
        groups = {}
        
        # Group hosts
        for host in hosts:
            group = host.get('group_name', 'managed_hosts')
            if group not in groups:
                groups[group] = []
            groups[group].append(host)
            
        inventory_content = []
        
        for group_name, group_hosts in groups.items():
            inventory_content.append(f"[{group_name}]")
            for host in group_hosts:
                line = f"{host['address']} ansible_user={host['username']} ansible_port={host['port']} "
                
                if host['auth_method'] == 'key':
                    # Use private key
                    line += "ansible_ssh_private_key_file=/root/.ssh/id_ed25519 "
                elif host['auth_method'] == 'password':
                    # Use password
                    password = host.get('password')
                    # Note: The password here should be decrypted because get_hosts() decrypts it.
                    if password:
                        line += f"ansible_ssh_pass={password} "

                line += "ansible_ssh_common_args='-o StrictHostKeyChecking=no -o ControlMaster=auto -o ControlPersist=60s'"
                inventory_content.append(line)
            inventory_content.append("")

        # Create temp file
        fd, inventory_path = tempfile.mkstemp(prefix='ansible_inventory_', dir=self.TEMP_DIR)
        with os.fdopen(fd, 'w') as f:
            f.write('\n'.join(inventory_content))
            
        return inventory_path

    def execute_command(self, command, target_hosts=None):
        """Execute Ansible command"""
        if not ANSIBLE_AVAILABLE:
            raise Exception("Ansible is not available on this system.")

        if target_hosts is None:
            target_hosts = self.db.get_hosts()

        inventory_path = self.generate_inventory(target_hosts)
        
        try:
            loader = DataLoader()
            inventory = InventoryManager(loader=loader, sources=inventory_path)
            variable_manager = VariableManager(loader=loader, inventory=inventory)
            
            play_source = dict(
                name="Ansible Ad-Hoc",
                hosts='all',
                gather_facts='no',
                tasks=[dict(action=dict(module='shell', args=command))]
            )

            play = Play().load(play_source, variable_manager=variable_manager, loader=loader)
            results_callback = ResultCallback()

            tqm = None
            try:
                tqm = TaskQueueManager(
                    inventory=inventory,
                    variable_manager=variable_manager,
                    loader=loader,
                    passwords=dict(),
                    stdout_callback=results_callback
                )
                tqm.run(play)
            finally:
                if tqm is not None:
                    tqm.cleanup()

            results = {
                'success': {},
                'failed': {},
                'unreachable': {}
            }

            for host, result in results_callback.host_ok.items():
                results['success'][host] = {
                    'stdout': result._result.get('stdout', ''),
                    'stderr': result._result.get('stderr', ''),
                    'rc': result._result.get('rc', 0)
                }
                host_id = next((h['id'] for h in target_hosts if h['address'] == host), None)
                if host_id:
                    self.db.log_command(
                        host_id,
                        command,
                        json.dumps(results['success'][host]),
                        'success'
                    )

            for host, result in results_callback.host_failed.items():
                results['failed'][host] = {
                    'msg': result._result.get('msg', ''),
                    'rc': result._result.get('rc', 1)
                }
                host_id = next((h['id'] for h in target_hosts if h['address'] == host), None)
                if host_id:
                    self.db.log_command(
                        host_id,
                        command,
                        json.dumps(results['failed'][host]),
                        'failed'
                    )

            for host, result in results_callback.host_unreachable.items():
                results['unreachable'][host] = {
                    'msg': result._result.get('msg', '')
                }
                host_id = next((h['id'] for h in target_hosts if h['address'] == host), None)
                if host_id:
                    self.db.log_command(
                        host_id,
                        command,
                        json.dumps(results['unreachable'][host]),
                        'unreachable'
                    )

            return results

        finally:
            if os.path.exists(inventory_path):
                os.remove(inventory_path)

    def check_host_connectivity(self, target_hosts=None):
        """Check connectivity for hosts using ansible ping"""
        if not ANSIBLE_AVAILABLE:
             raise Exception("Ansible is not available on this system.")

        if target_hosts is None:
            target_hosts = self.db.get_hosts()
        
        if not target_hosts:
             return {}

        results = self.execute_ping(target_hosts)
        
        # Update status in DB
        status_map = {}
        
        for host in target_hosts:
            address = host['address']
            status = 'failed'
            if address in results['success']:
                status = 'success'
            elif address in results['unreachable']:
                status = 'unreachable'
            elif address in results['failed']:
                status = 'failed'
            
            self.db.update_host_status(host['id'], status)
            status_map[host['id']] = status
            
        return status_map

    def execute_ping(self, target_hosts=None):
        """Execute Ansible ping module"""
        if not ANSIBLE_AVAILABLE:
            raise Exception("Ansible is not available on this system.")

        if target_hosts is None:
            target_hosts = self.db.get_hosts()

        inventory_path = self.generate_inventory(target_hosts)
        
        try:
            loader = DataLoader()
            inventory = InventoryManager(loader=loader, sources=inventory_path)
            variable_manager = VariableManager(loader=loader, inventory=inventory)
            
            play_source = dict(
                name="Ansible Ping",
                hosts='all',
                gather_facts='no',
                tasks=[dict(action=dict(module='ping'))]
            )

            play = Play().load(play_source, variable_manager=variable_manager, loader=loader)
            results_callback = ResultCallback()

            tqm = None
            try:
                tqm = TaskQueueManager(
                    inventory=inventory,
                    variable_manager=variable_manager,
                    loader=loader,
                    passwords=dict(),
                    stdout_callback=results_callback
                )
                tqm.run(play)
            finally:
                if tqm is not None:
                    tqm.cleanup()

            results = {
                'success': {},
                'failed': {},
                'unreachable': {}
            }

            for host, result in results_callback.host_ok.items():
                results['success'][host] = result._result
                host_id = next((h['id'] for h in target_hosts if h['address'] == host), None)
                if host_id:
                    self.db.log_command(host_id, 'ping', json.dumps(result._result), 'success')

            for host, result in results_callback.host_failed.items():
                results['failed'][host] = result._result
                host_id = next((h['id'] for h in target_hosts if h['address'] == host), None)
                if host_id:
                    self.db.log_command(host_id, 'ping', json.dumps(result._result), 'failed')

            for host, result in results_callback.host_unreachable.items():
                results['unreachable'][host] = result._result
                host_id = next((h['id'] for h in target_hosts if h['address'] == host), None)
                if host_id:
                    self.db.log_command(host_id, 'ping', json.dumps(result._result), 'unreachable')

            return results

        finally:
            if os.path.exists(inventory_path):
                os.remove(inventory_path)

    def get_host_facts(self, host_id):
        """Get host facts"""
        host = self.db.get_host(host_id)
        if not host:
            return None

        results = self.execute_command('ansible_facts', [host])
        if host['address'] in results['success']:
            return results['success'][host['address']]
        return None

    def run_playbook(self, play, target_hosts=None):
        """Run playbook"""
        if not ANSIBLE_AVAILABLE:
            raise Exception("Ansible is not available on this system.")

        if target_hosts:
            inventory_path = self.generate_inventory(target_hosts)
        else:
            inventory_path = self.generate_inventory(self.db.get_hosts())

        try:
            loader = DataLoader()
            inventory = InventoryManager(loader=loader, sources=inventory_path)
            variable_manager = VariableManager(loader=loader, inventory=inventory)
            
            results_callback = ResultCallback()
            tqm = None
            try:
                tqm = TaskQueueManager(
                    inventory=inventory,
                    variable_manager=variable_manager,
                    loader=loader,
                    passwords=dict(),
                    stdout_callback=results_callback
                )
                for play_item in play:
                    play_obj = Play().load(play_item, variable_manager=variable_manager, loader=loader)
                    tqm.run(play_obj)
            finally:
                if tqm is not None:
                    tqm.cleanup()

            return {
                'success': results_callback.host_ok,
                'failed': results_callback.host_failed,
                'unreachable': results_callback.host_unreachable
            }
        except Exception as e:
            raise Exception(f"Run playbook failed: {str(e)}")
        finally:
            if os.path.exists(inventory_path):
                os.remove(inventory_path)

    def copy_file_to_hosts(self, src, dest, hosts):
        """Copy file to selected hosts"""
        if not isinstance(hosts, list):
            hosts = [hosts]
        
        selected_hosts_data = []
        all_hosts = self.db.get_hosts()
        for host in all_hosts:
            host_id_str = str(host['id'])
            if host_id_str in [str(h) for h in hosts]:
                selected_hosts_data.append(host)
        
        if not selected_hosts_data:
            raise Exception("No selected hosts found")
        
        hosts_str = ','.join([h['address'] for h in selected_hosts_data])
        
        play = [{
            'name': 'Copy file to selected hosts',
            'hosts': hosts_str,
            'gather_facts': 'no',
            'tasks': [{
                'name': 'Ensure destination directory exists',
                'file': {
                    'path': os.path.dirname(dest),
                    'state': 'directory',
                    'mode': '0755'
                }
            }, {
                'name': 'Copy file to remote hosts',
                'copy': {
                    'src': src,
                    'dest': dest,
                    'mode': '0644'
                }
            }]
        }]
        
        return self.run_playbook(play, target_hosts=selected_hosts_data)

    def copy_file_to_all(self, src, dest):
        """Copy file to all hosts"""
        all_hosts = self.db.get_hosts()
        play = [{
            'name': 'Copy file to all hosts',
            'hosts': 'all',
            'gather_facts': 'no',
            'tasks': [{
                'name': 'Ensure destination directory exists',
                'file': {
                    'path': os.path.dirname(dest),
                    'state': 'directory',
                    'mode': '0755'
                }
            }, {
                'name': 'Copy file to remote hosts',
                'copy': {
                    'src': src,
                    'dest': dest,
                    'mode': '0644'
                }
            }]
        }]
        
        return self.run_playbook(play, target_hosts=all_hosts)

    def execute_custom_playbook(self, playbook_content, target_hosts=None, timeout=None):
        """Execute custom playbook
        
        Args:
            playbook_content (str): Playbook content
            target_hosts (list): List of target hosts
            timeout (int, optional): Timeout in seconds
        """
        if not ANSIBLE_AVAILABLE:
             raise Exception("Ansible is not available on this system.")
        
        if not shutil.which('ansible-playbook') and not (sys.platform == 'win32' and shutil.which('wsl')):
            raise Exception("Executable 'ansible-playbook' not found. Please ensure Ansible is installed and in your PATH.")

        fd, playbook_path = tempfile.mkstemp(prefix='ansible_playbook_', suffix='.yml', dir=self.TEMP_DIR)
        with os.fdopen(fd, 'w') as f:
            f.write(playbook_content)
        
        inventory_path = None
        try:
            inventory_option = []
            
            if target_hosts:
                inventory_path = self.generate_inventory(target_hosts)
                inventory_option = ['-i', inventory_path]
            
            cmd = ['ansible-playbook', playbook_path] + inventory_option + ['-v']

            if sys.platform == 'win32':
                 # Use relative paths for WSL
                playbook_rel = os.path.relpath(playbook_path).replace('\\', '/')
                cmd[1] = playbook_rel
                
                if inventory_option:
                    inventory_rel = os.path.relpath(inventory_path).replace('\\', '/')
                    cmd[3] = inventory_rel
                
                # Prepend wsl if we are on Windows and likely using WSL ansible
                cmd.insert(0, 'wsl')

            logs = []
            log_lock = threading.Lock()
            
            def process_output(process):
                for line in iter(process.stdout.readline, b''):
                    decoded_line = line.decode('utf-8').rstrip()
                    with log_lock:
                        logs.append(decoded_line)
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=False
            )
            
            output_thread = threading.Thread(target=process_output, args=(process,))
            output_thread.daemon = True
            output_thread.start()
            
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                with log_lock:
                    logs.append("Execution timed out.")
            
            output_thread.join(timeout=1)
            
            result = {
                'success': process.returncode == 0,
                'return_code': process.returncode,
                'logs': logs,
                'summary': self._parse_playbook_result(logs)
            }
            
            return result
        
        finally:
            if os.path.exists(playbook_path):
                os.remove(playbook_path)
            if inventory_path and os.path.exists(inventory_path):
                os.remove(inventory_path)
    
    def execute_playbook_async(self, task_id: int, playbook_content: str, target_hosts=None, timeout=None):
        """Execute playbook asynchronously"""
        def run_task():
            if not ANSIBLE_AVAILABLE:
                self.db.update_task(task_id, {
                    'status': 'failed',
                    'logs': json.dumps(["Error: Ansible is not available on this system."]),
                    'result': json.dumps({'success': False, 'return_code': -1})
                })
                return

            if not shutil.which('ansible-playbook') and not (sys.platform == 'win32' and shutil.which('wsl')):
                self.db.update_task(task_id, {
                    'status': 'failed',
                    'logs': json.dumps(["Error: Executable 'ansible-playbook' not found. Please ensure Ansible is installed and in your PATH."]),
                    'result': json.dumps({'success': False, 'return_code': -1})
                })
                return

            self.db.update_task(task_id, {'status': 'running'})
            
            fd, playbook_path = tempfile.mkstemp(prefix='ansible_playbook_', suffix='.yml', dir=self.TEMP_DIR)
            with os.fdopen(fd, 'w') as f:
                f.write(playbook_content)
            
            inventory_path = None
            logs = []
            try:
                inventory_option = []
                
                if target_hosts:
                    inventory_path = self.generate_inventory(target_hosts)
                    inventory_option = ['-i', inventory_path]
                
                cmd = ['ansible-playbook', playbook_path] + inventory_option + ['-v']
                
                if sys.platform == 'win32':
                     # Use relative paths for WSL
                    playbook_rel = os.path.relpath(playbook_path).replace('\\', '/')
                    cmd[1] = playbook_rel
                    
                    if inventory_option:
                        inventory_rel = os.path.relpath(inventory_path).replace('\\', '/')
                        cmd[3] = inventory_rel
                    
                    # Prepend wsl if we are on Windows and likely using WSL ansible
                    cmd.insert(0, 'wsl')
                
                # Update logs periodically or use a callback?
                # For simplicity, we'll collect all logs and update at the end, 
                # or update periodically if needed. 
                # Updating DB for every line is too heavy.
                
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=False
                )
                
                for line in iter(process.stdout.readline, b''):
                    decoded_line = line.decode('utf-8').rstrip()
                    logs.append(decoded_line)
                    # Optional: Update logs in DB every N lines or seconds to show progress
                    # For now, let's just append to memory.
                
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    logs.append("Execution timed out.")
                
                result = {
                    'success': process.returncode == 0,
                    'return_code': process.returncode,
                    'summary': self._parse_playbook_result(logs)
                }
                
                self.db.update_task(task_id, {
                    'status': 'completed' if process.returncode == 0 else 'failed',
                    'result': json.dumps(result),
                    'logs': json.dumps(logs),
                    'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                # Also log command history for each host if needed
                # (Reusing logic from execute_custom_playbook)
                if target_hosts:
                    for host in target_hosts:
                        host_status = 'success'
                        if host['address'] in result['summary']['failed']:
                            host_status = 'failed'
                        elif host['address'] in result['summary']['unreachable']:
                            host_status = 'unreachable'
                        
                        self.db.log_command(
                            host['id'],
                            'Batch Playbook Execution',
                            json.dumps({'task_id': task_id}),
                            host_status
                        )

            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                self.db.update_task(task_id, {
                    'status': 'failed',
                    'logs': json.dumps(logs + [f"Error: {str(e)}"]),
                    'result': json.dumps({'success': False, 'return_code': -1})
                })
            finally:
                if os.path.exists(playbook_path):
                    os.remove(playbook_path)
                if inventory_path and os.path.exists(inventory_path):
                    os.remove(inventory_path)

        thread = threading.Thread(target=run_task)
        thread.start()

    def _parse_playbook_result(self, logs):
        """Parse playbook execution logs"""
        summary = {
            'success': [],
            'failed': [],
            'unreachable': []
        }
        
        success_pattern = re.compile(r'([\w\.-]+)\s+:\s+ok=\d+')
        failed_pattern = re.compile(r'([\w\.-]+)\s+:\s+.*failed=([1-9]\d*)')
        unreachable_pattern = re.compile(r'([\w\.-]+)\s+:\s+.*unreachable=([1-9]\d*)')
        
        for line in logs:
            success_match = success_pattern.search(line)
            if success_match and not failed_pattern.search(line) and not unreachable_pattern.search(line):
                host = success_match.group(1)
                if host not in summary['success']:
                    summary['success'].append(host)
            
            failed_match = failed_pattern.search(line)
            if failed_match:
                host = failed_match.group(1)
                if host not in summary['failed']:
                    summary['failed'].append(host)
            
            unreachable_match = unreachable_pattern.search(line)
            if unreachable_match:
                host = unreachable_match.group(1)
                if host not in summary['unreachable']:
                    summary['unreachable'].append(host)
        
        return summary

from fastapi import Depends
from app.core.database import get_db

def get_ansible_service(db: Database = Depends(get_db)) -> AnsibleService:
    return AnsibleService(db)
