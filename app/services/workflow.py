import json
import logging
import time
import threading
import paramiko
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.core.database import Database
from app.services.tencent_cloud import TencentCloudService
from app.services.ansible import AnsibleService

logger = logging.getLogger(__name__)

class WorkflowService:
    def __init__(self, db: Database):
        self.db = db
        self.tencent_service = TencentCloudService()
        self.ansible_service = AnsibleService(db)

    def _check_ssh(self, ip: str, port: int, username: str, password: str, timeout: int = 3) -> bool:
        """Check if SSH connection can be established"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(ip, port=port, username=username, password=password, timeout=timeout, banner_timeout=timeout)
            return True
        except Exception:
            return False
        finally:
            client.close()

    def create_workflow(self, name: str, description: str, template_content: Dict[str, Any], params: Dict[str, Any]) -> int:
        """Create a new workflow instance"""
        # Merge params into template
        context = template_content.copy()
        context.update(params)
        
        workflow_data = {
            "name": name,
            "description": description,
            "status": "pending",
            "current_stage": "init",
            "context": json.dumps(context),
            "logs": json.dumps([])
        }
        return self.db.create_workflow(workflow_data)

    def start_workflow(self, workflow_id: int):
        """Start workflow execution in background"""
        thread = threading.Thread(target=self._process_workflow, args=(workflow_id,))
        thread.daemon = True
        thread.start()

    def _process_workflow(self, workflow_id: int):
        """Main workflow execution loop"""
        try:
            workflow = self.db.get_workflow(workflow_id)
            if not workflow:
                logger.error(f"Workflow {workflow_id} not found")
                return

            self._update_status(workflow_id, "running", "validation")
            
            # Stage 1: Validation
            if not self._stage_validation(workflow_id):
                return

            # Stage 2: Create Resources
            self._update_status(workflow_id, "running", "resource_creation")
            if not self._stage_resource_creation(workflow_id):
                return

            # Stage 3: Wait for Ready
            self._update_status(workflow_id, "running", "wait_for_ready")
            if not self._stage_wait_for_ready(workflow_id):
                return

            # Stage 4: Post-Create Configuration (Ansible)
            self._update_status(workflow_id, "running", "ansible_deployment")
            if not self._stage_ansible_deployment(workflow_id):
                return

            # Stage 5: Completion
            self._update_status(workflow_id, "completed", "completed")
            self._log_stage(workflow_id, "completed", "success", "Workflow completed successfully")

        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}", exc_info=True)
            self._update_status(workflow_id, "failed", workflow['current_stage'])
            self._log_stage(workflow_id, workflow['current_stage'], "failed", str(e))

    def _update_status(self, workflow_id: int, status: str, stage: str):
        self.db.update_workflow(workflow_id, {
            "status": status,
            "current_stage": stage
        })

    def _log_stage(self, workflow_id: int, stage: str, status: str, message: str, detail: Optional[str] = None):
        self.db.add_workflow_log({
            "workflow_id": workflow_id,
            "stage": stage,
            "status": status,
            "message": message,
            "detail": detail
        })

    def _get_context(self, workflow_id: int) -> Dict[str, Any]:
        workflow = self.db.get_workflow(workflow_id)
        return json.loads(workflow['context'])

    def _save_context(self, workflow_id: int, context: Dict[str, Any]):
        self.db.update_workflow(workflow_id, {
            "context": json.dumps(context)
        })

    # --- Stages ---

    def _stage_validation(self, workflow_id: int) -> bool:
        self._log_stage(workflow_id, "validation", "running", "Validating parameters...")
        try:
            context = self._get_context(workflow_id)
            
            # Check mandatory fields
            required_fields = ["Region", "Zone", "ImageId", "InstanceType", "Password"]
            for field in required_fields:
                if field not in context or not context[field]:
                    raise Exception(f"Missing required field: {field}")

            # Check quota (optional, skipping for now as it requires complex SDK calls)
            
            self._log_stage(workflow_id, "validation", "success", "Validation passed")
            return True
        except Exception as e:
            self._log_stage(workflow_id, "validation", "failed", str(e))
            self._update_status(workflow_id, "failed", "validation")
            return False

    def _stage_resource_creation(self, workflow_id: int) -> bool:
        self._log_stage(workflow_id, "resource_creation", "running", "Creating instance...")
        try:
            context = self._get_context(workflow_id)
            
            # Call Tencent Cloud API
            # Filter out context fields that are not for create_instance
            create_params = {k: v for k, v in context.items() if k in [
                "Region", "Zone", "ImageId", "InstanceType", "InstanceName", 
                "Password", "InstanceChargeType", "SystemDiskSize", "SystemDiskType",
                "VpcId", "SubnetId", "InternetAccessible", "InternetMaxBandwidthOut",
                "InstanceCount", "DryRun"
            ]}
            
            # Ensure DryRun is false for actual creation
            create_params["DryRun"] = False

            result = self.tencent_service.create_instance(create_params)
            
            instance_id_set = result.get("InstanceIdSet", [])
            if not instance_id_set:
                raise Exception("No instance ID returned from API")
            
            instance_id = instance_id_set[0]
            context["InstanceId"] = instance_id
            self._save_context(workflow_id, context)
            
            self._log_stage(workflow_id, "resource_creation", "success", f"Instance created: {instance_id}")
            return True
        except Exception as e:
            self._log_stage(workflow_id, "resource_creation", "failed", str(e))
            self._update_status(workflow_id, "failed", "resource_creation")
            return False

    def _stage_wait_for_ready(self, workflow_id: int) -> bool:
        self._log_stage(workflow_id, "wait_for_ready", "running", "Waiting for instance to be RUNNING...")
        try:
            context = self._get_context(workflow_id)
            instance_id = context.get("InstanceId")
            region = context.get("Region")
            
            max_retries = 60 # 5 minutes
            retry_interval = 5
            
            for i in range(max_retries):
                details = self.tencent_service.get_instance_details(instance_id, region)
                state = details.InstanceState
                
                if state == "RUNNING":
                    # Capture IPs
                    public_ips = details.PublicIpAddresses
                    private_ips = details.PrivateIpAddresses
                    
                    context["PublicIp"] = public_ips[0] if public_ips else None
                    context["PrivateIp"] = private_ips[0] if private_ips else None
                    self._save_context(workflow_id, context)
                    
                    self._log_stage(workflow_id, "wait_for_ready", "success", f"Instance is RUNNING. IP: {context.get('PublicIp') or context.get('PrivateIp')}")
                    return True
                
                if state in ["TERMINATED", "CREATION_FAILED"]:
                     raise Exception(f"Instance entered failed state: {state}")
                
                time.sleep(retry_interval)
            
            raise Exception("Timeout waiting for instance to be ready")
            
        except Exception as e:
            self._log_stage(workflow_id, "wait_for_ready", "failed", str(e))
            self._update_status(workflow_id, "failed", "wait_for_ready")
            return False

    def _rollback_deployment(self, workflow_id: int, context: Dict[str, Any], host_id: Optional[int]):
        """Rollback resources on failure"""
        # Rollback: Release instance
        instance_id = context.get("InstanceId")
        region = context.get("Region")
        if instance_id and region:
            try:
                self._log_stage(workflow_id, "ansible_deployment", "warning", f"Rolling back: Terminating instance {instance_id}...")
                self.tencent_service.terminate_instances([instance_id], region)
                self._log_stage(workflow_id, "ansible_deployment", "warning", f"Instance {instance_id} terminated.")
            except Exception as e:
                self._log_stage(workflow_id, "ansible_deployment", "failed", f"Rollback failed: {str(e)}")

        # Rollback: Delete host
        if host_id:
            try:
                self.db.delete_host(host_id)
                self._log_stage(workflow_id, "ansible_deployment", "warning", f"Host {host_id} removed from inventory.")
            except Exception as e:
                logger.error(f"Failed to delete host {host_id}: {e}")

    def _stage_ansible_deployment(self, workflow_id: int) -> bool:
        self._log_stage(workflow_id, "ansible_deployment", "running", "Registering to Ansible Inventory...")
        host_id = None
        context = {}
        try:
            context = self._get_context(workflow_id)
            
            ip_address = context.get("PublicIp") or context.get("PrivateIp")
            if not ip_address:
                raise Exception("No IP address available for Ansible connection")
            
            password = context.get("Password")
            username = "root" # Default for Linux
            
            # Attempt to detect username via SSH with retry
            self._log_stage(workflow_id, "ansible_deployment", "running", f"Checking SSH on {ip_address}...")
            
            detected_username = None
            candidate_usernames = ['root', 'ubuntu', 'lighthouse']
            
            # Retry loop for SSH connection (up to 300 seconds)
            max_ssh_retries = 60
            ssh_retry_interval = 5
            
            for i in range(max_ssh_retries):
                for user in candidate_usernames:
                    if self._check_ssh(ip_address, 22, user, password):
                        detected_username = user
                        self._log_stage(workflow_id, "ansible_deployment", "running", f"SSH connection confirmed ({detected_username})")
                        break
                
                if detected_username:
                    username = detected_username
                    break
                
                if i % 5 == 0: # Log every 25 seconds
                    self._log_stage(workflow_id, "ansible_deployment", "running", f"Waiting for SSH service... ({i * ssh_retry_interval}s)")
                
                time.sleep(ssh_retry_interval)
            
            if not detected_username:
                 self._log_stage(workflow_id, "ansible_deployment", "warning", "SSH connection timeout, defaulting to 'root'")
                 # Proceed with 'root' as fallback, similar to tencent sync task

            # Add to local DB hosts table
            host_data = {
                "comment": f"Auto-created from Workflow {workflow_id}",
                "address": ip_address,
                "username": username, 
                "port": 22,
                "password": password,
                "auth_method": "password",
                "group_name": "workflow_created"
            }
            
            # Check if host exists (by IP)
            existing_hosts = self.db.get_hosts()
            existing_host = next((h for h in existing_hosts if h['address'] == ip_address), None)
            
            if existing_host:
                self.db.update_host(existing_host['id'], host_data)
                host_id = existing_host['id']
                self._log_stage(workflow_id, "ansible_deployment", "success", f"Updated existing host {host_id} in inventory")
            else:
                host_id = self.db.add_host(host_data)
                self._log_stage(workflow_id, "ansible_deployment", "success", f"Host added to inventory with ID {host_id}")
            
            # Optional: Run a setup playbook if specified in template
            playbook_content = context.get("PlaybookContent")
            if playbook_content:
                self._log_stage(workflow_id, "ansible_deployment", "running", "Executing post-creation playbook...")
                
                # We need to run this synchronously here or spawn another task.
                # Since we are already in a background thread, synchronous is fine.
                
                # However, AnsibleService.execute_custom_playbook spawns a process.
                # We can use it.
                
                target_hosts = [self.db.get_host(host_id)]
                
                # Wait a bit for SSH to be truly ready
                time.sleep(10)
                
                # Simple ping check first
                ping_res = self.ansible_service.check_host_connectivity(target_hosts)
                if ping_res.get(host_id) != 'success':
                    # Retry ping a few times
                    for _ in range(5):
                        time.sleep(5)
                        ping_res = self.ansible_service.check_host_connectivity(target_hosts)
                        if ping_res.get(host_id) == 'success':
                            break
                
                result = self.ansible_service.execute_custom_playbook(playbook_content, target_hosts=target_hosts, timeout=300)
                
                ansible_logs = result.get('logs', [])
                log_output = "\n".join(ansible_logs) if ansible_logs else "No output"
                
                if result['success']:
                    self._log_stage(workflow_id, "ansible_deployment", "success", "Playbook executed successfully", detail=log_output)
                else:
                    self._log_stage(workflow_id, "ansible_deployment", "failed", "Playbook execution failed", detail=log_output)
                    self._update_status(workflow_id, "failed", "ansible_deployment")
                    self._rollback_deployment(workflow_id, context, host_id)
                    return False

            return True
        except Exception as e:
            self._log_stage(workflow_id, "ansible_deployment", "failed", str(e))
            self._update_status(workflow_id, "failed", "ansible_deployment")
            self._rollback_deployment(workflow_id, context, host_id)
            return False

from fastapi import Depends
from app.core.database import get_db

def get_workflow_service(db: Database = Depends(get_db)) -> WorkflowService:
    return WorkflowService(db)
