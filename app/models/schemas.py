from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any, Union, Dict

# --- Auth Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    success: bool
    message: str
    token: str
    # Ant Design Pro compatibility
    status: str = "ok"
    type: str = "account"
    currentAuthority: str = "admin"
    redirect_url: str = "/"  # Default redirect URL

class CurrentUser(BaseModel):
    name: str = "Admin"
    avatar: str = "https://gw.alipayobjects.com/zos/antfincdn/XAosXuNZyF/BiazfanxmamNRoxxVxka.png"
    userid: str = "00000001"
    email: str = "admin@example.com"
    signature: str = "Be tolerant to diversity, tolerance is a virtue"
    title: str = "Administrator"
    group: str = "IT Department"
    notifyCount: int = 12
    unreadCount: int = 11
    country: str = "China"
    access: str = "admin"
    address: str = "Hangzhou, China"
    phone: str = "0752-268888888"

# --- Host Schemas ---
class HostBase(BaseModel):
    comment: Optional[str] = ""
    address: str
    username: str
    port: int = 22
    auth_method: str = "password"  # 'password' or 'key'
    group_name: Union[str, List[str]] = "all"

    @validator('group_name', pre=True)
    def parse_group_name(cls, v):
        if isinstance(v, list):
            # If multiple groups are selected, take the last one or join them?
            # Current DB design supports single group.
            # Taking the last one is common for "move to group" behavior in single-select-masked-as-multi
            # Or taking the first one.
            # Let's assume single group logic for now.
            return v[-1] if v else "all"
        return v

class HostCreate(HostBase):
    password: Optional[str] = None

class HostUpdate(HostBase):
    password: Optional[str] = None

class HostResponse(HostBase):
    id: int
    created_at: str
    is_password_encrypted: bool = False
    password: str = "********"  # Masked
    status: Optional[str] = None

# --- Command Execution Schemas ---
class ExecuteRequest(BaseModel):
    command: str
    hosts: Union[List[int], str]  # List of host IDs or "all"

# --- SFTP Schemas ---
class SFTPMkdirRequest(BaseModel):
    path: str

class SFTPRenameRequest(BaseModel):
    old_path: str
    new_path: str

class SFTPTouchRequest(BaseModel):
    path: str

class SFTPWriteRequest(BaseModel):
    path: str
    content: str

class SFTPDeleteRequest(BaseModel):
    path: str
    is_directory: bool = False

# --- Logs Schemas ---
class AccessLog(BaseModel):
    id: int
    ip_address: str
    path: str
    status: str
    status_code: int
    access_time: str

class CommandLog(BaseModel):
    id: int
    host_id: Optional[int]
    command: str
    output: Optional[str]
    status: str
    executed_at: str
    comment: Optional[str] = None
    address: Optional[str] = None

# --- Template Schemas ---
class TemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    content: str
    type: str = "ansible"  # "ansible" or "workflow"

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(TemplateBase):
    pass

class TemplateResponse(TemplateBase):
    id: int
    created_at: str
    updated_at: str

# --- Tencent Cloud Schemas ---
class TencentInstance(BaseModel):
    InstanceId: str
    InstanceName: Optional[str] = None
    InstanceState: Optional[str] = None
    PublicIpAddresses: Optional[List[str]] = []
    PrivateIpAddresses: Optional[List[str]] = []
    CPU: Optional[int] = None
    Memory: Optional[int] = None
    CreatedTime: Optional[str] = None
    ExpiredTime: Optional[str] = None
    OsName: Optional[str] = None
    Zone: Optional[str] = None
    InstanceType: Optional[str] = None
    InstanceChargeType: Optional[str] = None
    InternetAccessible: Optional[Dict[str, Any]] = None

class TencentInstanceCreate(BaseModel):
    Region: str = Field(..., description="Region, e.g. ap-guangzhou")
    InstanceName: str = Field(..., min_length=1, max_length=60, description="Instance name, 1-60 characters")
    ImageId: str = Field(..., description="Image ID")
    InstanceType: str = Field(..., description="Instance type, e.g. S2.SMALL1")
    Zone: str = Field(..., description="Availability Zone")
    Password: str = Field(..., min_length=8, max_length=30, description="Password, 8-30 characters. Must contain uppercase, lowercase, and numbers.")
    # LoginUsername: str = Field("root", description="Login username for the instance (used for local sync only)")
    InstanceChargeType: str = Field("POSTPAID_BY_HOUR", description="Instance charge type")
    InstanceCount: int = Field(1, ge=1, le=100, description="Number of instances to create")
    InternetAccessible: bool = Field(True, description="Whether to allocate public IP")
    InternetMaxBandwidthOut: int = Field(1, ge=0, le=100, description="Max bandwidth out in Mbps")
    SystemDiskSize: int = Field(50, ge=50, le=1000, description="System disk size in GB")
    SystemDiskType: str = Field("CLOUD_PREMIUM", description="System disk type")
    VpcId: Optional[str] = Field(None, description="VPC ID")
    SubnetId: Optional[str] = Field(None, description="Subnet ID")
    DryRun: bool = False

class TencentBatchDeleteRequest(BaseModel):
    InstanceIds: List[str]
    Region: str

class TencentAccountInfo(BaseModel):
    Balance: float
    Currency: str

class TencentSyncInstanceItem(BaseModel):
    InstanceId: str
    Password: str

class TencentSyncRequest(BaseModel):
    Region: str
    Instances: List[TencentSyncInstanceItem]

# --- Workflow Schemas ---
class WorkflowCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    template_id: int
    ansible_template_id: Optional[int] = None
    params: Dict[str, Any] = {}

class WorkflowBatchCreateRequest(BaseModel):
    template_id: int
    ansible_template_id: Optional[int] = None
    instances: List[Dict[str, Any]] # List of params for each instance

class WorkflowResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    status: str
    current_stage: Optional[str] = None
    context: Optional[str] = None # JSON string
    logs: Optional[str] = None
    created_at: str
    updated_at: str

class WorkflowLogResponse(BaseModel):
    id: int
    workflow_id: int
    stage: str
    status: str
    message: Optional[str] = None
    detail: Optional[str] = None
    timestamp: str

class WorkflowLogSummary(BaseModel):
    id: int
    workflow_id: int
    stage: str
    status: str
    message: Optional[str] = None
    has_detail: bool = False
    timestamp: str

class ExtractTemplateRequest(BaseModel):
    instance_id: str
    region: str

# --- Cloud Credentials Schemas ---
class CloudCredentialBase(BaseModel):
    name: str
    provider: str = Field(..., description="Provider name, e.g., tencent")
    is_default: bool = False

class CloudCredentialCreate(CloudCredentialBase):
    access_key: str
    secret_key: str

class CloudCredentialUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    is_default: Optional[bool] = None

class CloudCredentialResponse(CloudCredentialBase):
    id: int
    access_key: str  # Masked
    created_at: str
    updated_at: str

class CloudCredentialTestRequest(BaseModel):
    provider: str
    access_key: str
    secret_key: str

