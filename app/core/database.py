import sqlite3
import os
from contextlib import contextmanager
from typing import List, Optional, Dict, Any, Generator
from app.core.config import settings
from app.utils.crypto import CryptoUtils

class Database:
    def __init__(self, db_path: str = settings.DB_PATH):
        self.db_path = db_path
        self.crypto = CryptoUtils()
        self.init_database()

    def init_database(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hosts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    comment TEXT NOT NULL,
                    address TEXT NOT NULL,
                    username TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    password TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    auth_method TEXT NOT NULL DEFAULT 'password',
                    status TEXT DEFAULT NULL,
                    group_name TEXT DEFAULT 'all'
                )
            """)
            
            # Check if status column exists (for migration)
            try:
                conn.execute("SELECT status FROM hosts LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE hosts ADD COLUMN status TEXT DEFAULT NULL")

            # Check if group_name column exists (for migration)
            try:
                conn.execute("SELECT group_name FROM hosts LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE hosts ADD COLUMN group_name TEXT DEFAULT 'all'")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    host_id INTEGER,
                    command TEXT NOT NULL,
                    output TEXT,
                    status TEXT NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (host_id) REFERENCES hosts (id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT NOT NULL,
                    path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    access_time TIMESTAMP DEFAULT (datetime('now', '+8 hours'))
                )
            """)

            # New: Ansible Templates Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ansible_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # New: Workflow Templates Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    content TEXT NOT NULL,
                    version TEXT DEFAULT '1.0',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # New: Cloud Credentials Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cloud_credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    access_key TEXT NOT NULL,
                    secret_key TEXT NOT NULL,
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Migration: Split templates into ansible_templates and workflow_templates
            try:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='templates'")
                if cursor.fetchone():
                    # Check if data exists in templates to migrate
                    count = conn.execute("SELECT count(*) FROM templates").fetchone()[0]
                    if count > 0:
                        print("Migrating templates...")
                        # Migrate Workflow Templates
                        conn.execute("""
                            INSERT INTO workflow_templates (name, description, content, version, created_at, updated_at)
                            SELECT name, description, content, version, created_at, updated_at
                            FROM templates WHERE type = 'workflow'
                        """)
                        
                        # Migrate Ansible Templates
                        conn.execute("""
                            INSERT INTO ansible_templates (name, description, content, created_at, updated_at)
                            SELECT name, description, content, created_at, updated_at
                            FROM templates WHERE type = 'ansible' OR type IS NULL
                        """)
                    
                    # Drop old table (rename for safety? No, user wants separation)
                    conn.execute("DROP TABLE templates")
                    print("Migrated templates to ansible_templates and workflow_templates")
            except Exception as e:
                print(f"Migration warning: {e}")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS tencent_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    secret_id TEXT NOT NULL,
                    secret_key TEXT NOT NULL,
                    region TEXT DEFAULT 'ap-guangzhou',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    target_hosts TEXT,
                    params TEXT,
                    result TEXT,
                    logs TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    current_stage TEXT,
                    context TEXT,
                    logs TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workflow_id) REFERENCES workflows (id)
                )
            """)
            
            # Check if detail column exists (for migration)
            try:
                conn.execute("SELECT detail FROM workflow_logs LIMIT 1")
            except sqlite3.OperationalError:
                conn.execute("ALTER TABLE workflow_logs ADD COLUMN detail TEXT")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def add_host(self, host_data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            encrypted_password = None
            auth_method = host_data.get('auth_method', 'password')
            
            if auth_method == 'password' and host_data.get('password'):
                encrypted_password = self.crypto.encrypt(host_data['password'])

            cursor = conn.execute("""
                INSERT INTO hosts (comment, address, username, port, password, auth_method, group_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                host_data['comment'],
                host_data['address'],
                host_data['username'],
                host_data['port'],
                encrypted_password,
                auth_method,
                host_data.get('group_name', 'all')
            ))
            return cursor.lastrowid

    def add_hosts_batch(self, hosts_data: List[Dict[str, Any]]) -> int:
        with self.get_connection() as conn:
            processed_hosts = []
            for host in hosts_data:
                encrypted_password = None
                auth_method = host.get('auth_method', 'password')
                
                if auth_method == 'password' and host.get('password'):
                    encrypted_password = self.crypto.encrypt(host['password'])
                
                processed_hosts.append((
                    host['comment'],
                    host['address'],
                    host['username'],
                    host['port'],
                    encrypted_password,
                    auth_method,
                    host.get('group_name', 'all')
                ))
                
            cursor = conn.executemany("""
                INSERT INTO hosts (comment, address, username, port, password, auth_method, group_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, processed_hosts)
            return cursor.rowcount

    def get_hosts(self, group_name: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            query = "SELECT * FROM hosts"
            params = []
            if group_name:
                query += " WHERE group_name = ?"
                params.append(group_name)
            query += " ORDER BY created_at DESC"
            
            cursor = conn.execute(query, params)
            hosts = [dict(row) for row in cursor.fetchall()]
            
            for host in hosts:
                host['encrypted_password'] = host['password']
                if host['auth_method'] == 'password' and host['password']:
                    host['password'] = self.crypto.decrypt(host['password'])
                else:
                    host['password'] = None
            return hosts

    def get_groups(self) -> List[str]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT DISTINCT group_name FROM hosts ORDER BY group_name")
            return [row['group_name'] for row in cursor.fetchall() if row['group_name']]

    def get_host(self, host_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM hosts WHERE id = ?", (host_id,))
            row = cursor.fetchone()
            if row:
                host = dict(row)
                host['encrypted_password'] = host['password']
                if host['auth_method'] == 'password' and host['password']:
                    host['password'] = self.crypto.decrypt(host['password'])
                else:
                    host['password'] = None
                return host
            return None

    def update_host(self, host_id: int, host_data: Dict[str, Any]) -> None:
        with self.get_connection() as conn:
            auth_method = host_data.get('auth_method', 'password')
            encrypted_password = None

            if auth_method == 'password' and host_data.get('password'):
                encrypted_password = self.crypto.encrypt(host_data['password'])
            
            # Note: This logic might be slightly flawed if password is NOT updated but passed as empty/None in update.
            # The original Flask app handled this in the route logic. We will handle it in the service.
            # But here we assume `host_data` contains the correct values to write.
            
            # To support partial updates properly, dynamic SQL generation is better, 
            # but adhering to original structure:
            conn.execute("""
                UPDATE hosts 
                SET comment = ?, address = ?, username = ?, port = ?, password = ?, auth_method = ?, group_name = ?
                WHERE id = ?
            """, (
                host_data['comment'],
                host_data['address'],
                host_data['username'],
                host_data['port'],
                encrypted_password,
                auth_method,
                host_data.get('group_name', 'all'),
                host_id
            ))

    def update_host_status(self, host_id: int, status: str) -> None:
        with self.get_connection() as conn:
            conn.execute("UPDATE hosts SET status = ? WHERE id = ?", (status, host_id))

    def delete_host(self, host_id: int) -> None:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM command_logs WHERE host_id = ?", (host_id,))
            conn.execute("DELETE FROM hosts WHERE id = ?", (host_id,))

    def log_command(self, host_id: int, command: str, output: str, status: str) -> None:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO command_logs (host_id, command, output, status)
                VALUES (?, ?, ?, ?)
            """, (host_id, command, output, status))

    def get_command_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT cl.*, h.comment, h.address 
                FROM command_logs cl
                LEFT JOIN hosts h ON cl.host_id = h.id
                ORDER BY cl.executed_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def add_access_log(self, ip_address: str, path: str, status: str, status_code: int) -> None:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO access_logs (ip_address, path, status, status_code)
                VALUES (?, ?, ?, ?)
            """, (ip_address, path, status, status_code))

    def get_access_logs(self, limit: int = 100, ip: Optional[str] = None, path: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            query = "SELECT * FROM access_logs"
            params = []
            conditions = []
            
            if ip:
                conditions.append("ip_address LIKE ?")
                params.append(f"%{ip}%")
            
            if path:
                conditions.append("path LIKE ?")
                params.append(f"%{path}%")
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
                
            query += " ORDER BY access_time DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_logs(self) -> None:
        with self.get_connection() as conn:
            conn.execute("""
                DELETE FROM access_logs 
                WHERE access_time < datetime('now', '+8 hours', '-7 days')
            """)

    # --- Template Methods ---
    def add_template(self, template_data: Dict[str, Any]) -> int:
        template_type = template_data.get('type', 'workflow')
        table = 'workflow_templates' if template_type == 'workflow' else 'ansible_templates'
        
        with self.get_connection() as conn:
            if template_type == 'workflow':
                cursor = conn.execute(f"""
                    INSERT INTO {table} (name, description, content, version)
                    VALUES (?, ?, ?, ?)
                """, (
                    template_data['name'],
                    template_data.get('description'),
                    template_data['content'],
                    template_data.get('version', '1.0')
                ))
            else:
                cursor = conn.execute(f"""
                    INSERT INTO {table} (name, description, content)
                    VALUES (?, ?, ?)
                """, (
                    template_data['name'],
                    template_data.get('description'),
                    template_data['content']
                ))
            return cursor.lastrowid

    def get_templates(self, type: str = 'ansible') -> List[Dict[str, Any]]:
        # Default to ansible if type is not provided, though API should provide it
        if not type:
            type = 'ansible'
            
        table = 'workflow_templates' if type == 'workflow' else 'ansible_templates'
        
        with self.get_connection() as conn:
            # We return 'type' field artificially to keep compatibility with schemas if needed
            query = f"SELECT *, '{type}' as type FROM {table} ORDER BY created_at DESC"
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def get_template(self, template_id: int, type: str = 'ansible') -> Optional[Dict[str, Any]]:
        if not type:
            type = 'ansible'
            
        table = 'workflow_templates' if type == 'workflow' else 'ansible_templates'
        with self.get_connection() as conn:
            cursor = conn.execute(f"SELECT *, '{type}' as type FROM {table} WHERE id = ?", (template_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def update_template(self, template_id: int, template_data: Dict[str, Any]) -> None:
        template_type = template_data.get('type', 'ansible')
        table = 'workflow_templates' if template_type == 'workflow' else 'ansible_templates'
        
        with self.get_connection() as conn:
            if template_type == 'workflow':
                conn.execute(f"""
                    UPDATE {table} 
                    SET name = ?, description = ?, content = ?, version = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    template_data['name'],
                    template_data.get('description'),
                    template_data['content'],
                    template_data.get('version', '1.0'),
                    template_id
                ))
            else:
                conn.execute(f"""
                    UPDATE {table} 
                    SET name = ?, description = ?, content = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    template_data['name'],
                    template_data.get('description'),
                    template_data['content'],
                    template_id
                ))

    def delete_template(self, template_id: int, type: str = 'ansible') -> None:
        if not type:
            type = 'ansible'
            
        table = 'workflow_templates' if type == 'workflow' else 'ansible_templates'
        with self.get_connection() as conn:
            conn.execute(f"DELETE FROM {table} WHERE id = ?", (template_id,))

    # --- Tencent Cloud Methods ---
    def save_tencent_config(self, config_data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            # Check if config exists, if so update, else insert
            cursor = conn.execute("SELECT id FROM tencent_config LIMIT 1")
            row = cursor.fetchone()
            
            encrypted_secret_key = self.crypto.encrypt(config_data['secret_key'])
            
            if row:
                conn.execute("""
                    UPDATE tencent_config 
                    SET secret_id = ?, secret_key = ?, region = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    config_data['secret_id'],
                    encrypted_secret_key,
                    config_data.get('region', 'ap-guangzhou'),
                    row['id']
                ))
                return row['id']
            else:
                cursor = conn.execute("""
                    INSERT INTO tencent_config (secret_id, secret_key, region)
                    VALUES (?, ?, ?)
                """, (
                    config_data['secret_id'],
                    encrypted_secret_key,
                    config_data.get('region', 'ap-guangzhou')
                ))
                return cursor.lastrowid

    # --- Task Methods ---
    def add_task(self, task_data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO tasks (type, name, status, target_hosts, params, result, logs)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data['type'],
                task_data['name'],
                task_data['status'],
                task_data.get('target_hosts'),
                task_data.get('params'),
                task_data.get('result'),
                task_data.get('logs')
            ))
            return cursor.lastrowid

    def update_task(self, task_id: int, task_data: Dict[str, Any]) -> None:
        with self.get_connection() as conn:
            fields = []
            values = []
            for key, value in task_data.items():
                fields.append(f"{key} = ?")
                values.append(value)
            
            if not fields:
                return

            values.append(task_id)
            conn.execute(f"""
                UPDATE tasks 
                SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)

    def get_task(self, task_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM tasks 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_tencent_config(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tencent_config LIMIT 1")
            row = cursor.fetchone()
            if row:
                config = dict(row)
                try:
                    config['secret_key'] = self.crypto.decrypt(config['secret_key'])
                except Exception:
                    # Fallback if decryption fails (e.g. if key changed or invalid data)
                    config['secret_key'] = ""
                return config
            return None

    # --- Workflow Methods ---
    def create_workflow(self, workflow_data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO workflows (name, description, status, current_stage, context, logs)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                workflow_data['name'],
                workflow_data.get('description'),
                workflow_data.get('status', 'pending'),
                workflow_data.get('current_stage'),
                workflow_data.get('context', '{}'),
                workflow_data.get('logs')
            ))
            return cursor.lastrowid

    def get_workflow(self, workflow_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM workflows WHERE id = ?", (workflow_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_workflows(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM workflows 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def update_workflow(self, workflow_id: int, workflow_data: Dict[str, Any]) -> None:
        with self.get_connection() as conn:
            fields = []
            values = []
            for key, value in workflow_data.items():
                fields.append(f"{key} = ?")
                values.append(value)
            
            if not fields:
                return

            values.append(workflow_id)
            conn.execute(f"""
                UPDATE workflows 
                SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)

    def add_workflow_log(self, log_data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO workflow_logs (workflow_id, stage, status, message, detail)
                VALUES (?, ?, ?, ?, ?)
            """, (
                log_data['workflow_id'],
                log_data['stage'],
                log_data['status'],
                log_data.get('message'),
                log_data.get('detail')
            ))
            return cursor.lastrowid

    def get_workflow_logs(self, workflow_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            # Only select necessary fields for list view
            cursor = conn.execute("""
                SELECT id, workflow_id, stage, status, message, timestamp, 
                       CASE WHEN detail IS NOT NULL AND detail != '' THEN 1 ELSE 0 END as has_detail
                FROM workflow_logs 
                WHERE workflow_id = ?
                ORDER BY timestamp DESC
            """, (workflow_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_workflow_log_detail(self, log_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM workflow_logs WHERE id = ?", (log_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # --- Cloud Credential Methods ---
    def add_cloud_credential(self, cred_data: Dict[str, Any]) -> int:
        with self.get_connection() as conn:
            encrypted_sk = self.crypto.encrypt(cred_data['secret_key'])
            
            # If default, unset other defaults
            if cred_data.get('is_default'):
                conn.execute("UPDATE cloud_credentials SET is_default = 0 WHERE provider = ?", (cred_data['provider'],))
            
            cursor = conn.execute("""
                INSERT INTO cloud_credentials (name, provider, access_key, secret_key, is_default)
                VALUES (?, ?, ?, ?, ?)
            """, (
                cred_data['name'],
                cred_data['provider'],
                cred_data['access_key'],
                encrypted_sk,
                cred_data.get('is_default', False)
            ))
            return cursor.lastrowid

    def get_cloud_credentials(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            query = "SELECT * FROM cloud_credentials"
            params = []
            if provider:
                query += " WHERE provider = ?"
                params.append(provider)
            query += " ORDER BY created_at DESC"
            
            cursor = conn.execute(query, params)
            creds = [dict(row) for row in cursor.fetchall()]
            
            for cred in creds:
                # Mask Access Key partially
                ak = cred['access_key']
                if len(ak) > 8:
                    cred['access_key'] = ak[:4] + '*' * (len(ak) - 8) + ak[-4:]
                # Never return SK in list
                cred['secret_key'] = "********" 
            return creds

    def get_cloud_credential(self, cred_id: int, decrypt: bool = False) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM cloud_credentials WHERE id = ?", (cred_id,))
            row = cursor.fetchone()
            if row:
                cred = dict(row)
                if decrypt:
                    try:
                        cred['secret_key'] = self.crypto.decrypt(cred['secret_key'])
                    except:
                        cred['secret_key'] = ""
                else:
                    cred['secret_key'] = "********"
                return cred
            return None

    def update_cloud_credential(self, cred_id: int, cred_data: Dict[str, Any]) -> None:
        with self.get_connection() as conn:
            fields = []
            values = []
            
            if 'name' in cred_data:
                fields.append("name = ?")
                values.append(cred_data['name'])
            
            if 'provider' in cred_data:
                fields.append("provider = ?")
                values.append(cred_data['provider'])
                
            if 'access_key' in cred_data and cred_data['access_key']:
                fields.append("access_key = ?")
                values.append(cred_data['access_key'])
                
            if 'secret_key' in cred_data and cred_data['secret_key']:
                encrypted_sk = self.crypto.encrypt(cred_data['secret_key'])
                fields.append("secret_key = ?")
                values.append(encrypted_sk)
                
            if 'is_default' in cred_data:
                fields.append("is_default = ?")
                values.append(cred_data['is_default'])
                # If setting to default, unset others
                if cred_data['is_default']:
                     # We need provider. If not in data, fetch from DB.
                     provider = cred_data.get('provider')
                     if not provider:
                         curr = conn.execute("SELECT provider FROM cloud_credentials WHERE id = ?", (cred_id,)).fetchone()
                         if curr:
                             provider = curr[0]
                     if provider:
                        conn.execute("UPDATE cloud_credentials SET is_default = 0 WHERE provider = ? AND id != ?", (provider, cred_id))

            if not fields:
                return

            values.append(cred_id)
            conn.execute(f"""
                UPDATE cloud_credentials 
                SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)

    def delete_cloud_credential(self, cred_id: int) -> None:
        with self.get_connection() as conn:
            conn.execute("DELETE FROM cloud_credentials WHERE id = ?", (cred_id,))

# Dependency
def get_db() -> Database:
    return Database()
