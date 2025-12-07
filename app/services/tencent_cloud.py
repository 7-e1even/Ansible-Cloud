from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.cvm.v20170312 import cvm_client, models as cvm_models
from tencentcloud.billing.v20180709 import billing_client, models as billing_models
from app.core.config import settings
from typing import Dict, Any, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

class TencentCloudService:
    def __init__(self, secret_id: Optional[str] = None, secret_key: Optional[str] = None):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self._billing_client = None
        
        if not self.secret_id or not self.secret_key:
             self._load_credentials()

    def _load_credentials(self):
        # Try DB
        try:
            from app.core.database import Database
            db = Database()
            creds = db.get_cloud_credentials(provider='tencent')
            # Find default
            default_cred = next((c for c in creds if c.get('is_default')), None)
            
            # If no default marked, use the first one available
            if not default_cred and creds:
                 default_cred = creds[0]
            
            if default_cred:
                 full_cred = db.get_cloud_credential(default_cred['id'], decrypt=True)
                 if full_cred:
                     self.secret_id = full_cred['access_key']
                     self.secret_key = full_cred['secret_key']
        except Exception as e:
            logger.error(f"Failed to load credentials from DB: {e}")

    def _check_config(self):
        if not self.secret_id or not self.secret_key:
             raise Exception("Tencent Cloud credentials not configured")

    def _get_client(self, region: str):
        if not self.secret_id or not self.secret_key:
             return None
        
        if not region:
             region = "ap-guangzhou"

        try:
            cred = credential.Credential(self.secret_id, self.secret_key)
            httpProfile = HttpProfile()
            httpProfile.endpoint = "cvm.tencentcloudapi.com"

            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile
            client = cvm_client.CvmClient(cred, region, clientProfile)
            return client
        except Exception as e:
            logger.error(f"Failed to init Tencent Cloud client for region {region}: {e}")
            return None

    def get_account_balance(self):
        self._check_config()
        try:
            cred = credential.Credential(self.secret_id, self.secret_key)
            httpProfile = HttpProfile()
            httpProfile.endpoint = "billing.tencentcloudapi.com"
            clientProfile = ClientProfile()
            clientProfile.httpProfile = httpProfile
            client = billing_client.BillingClient(cred, "", clientProfile)
            
            req = billing_models.DescribeAccountBalanceRequest()
            resp = client.DescribeAccountBalance(req)
            return {
                "Balance": resp.Balance / 100.0,
                "Currency": "CNY"
            }
        except Exception as e:
            logger.error(f"Billing error: {e}")
            return {"Balance": 0.0, "Currency": "CNY"}

    def describe_regions(self):
        """Get available regions"""
        self._check_config()
        client = self._get_client("ap-guangzhou")
        try:
            req = cvm_models.DescribeRegionsRequest()
            resp = client.DescribeRegions(req)
            regions = []
            for region in resp.RegionSet:
                if region.RegionState == "AVAILABLE":
                    regions.append({
                        "label": region.RegionName,
                        "value": region.Region
                    })
            return regions
        except TencentCloudSDKException as err:
            raise Exception(f"Tencent Cloud SDK Error: {err.message}")

    def describe_zones(self, region: str):
        """Get available zones"""
        self._check_config()
        client = self._get_client(region)
        if not client:
             raise Exception(f"Failed to initialize Tencent Cloud client for region {region}")
        
        try:
            req = cvm_models.DescribeZonesRequest()
            resp = client.DescribeZones(req)
            zones = []
            for zone in resp.ZoneSet:
                if zone.ZoneState == "AVAILABLE":
                    zones.append({
                        "label": zone.ZoneName,
                        "value": zone.Zone
                    })
            return zones
        except TencentCloudSDKException as err:
            logger.error(f"Tencent Cloud SDK Error in describe_zones: {err}")
            raise Exception(f"Tencent Cloud SDK Error: {err.message}")
        except Exception as err:
            logger.error(f"Unexpected error in describe_zones: {err}", exc_info=True)
            raise

    def describe_images(self, architecture: str = "x86_64", os_name: str = "CentOS", region: str = None):
        """Get available images"""
        self._check_config()
        client = self._get_client(region)
        if not client:
             raise Exception(f"Failed to initialize Tencent Cloud client for region {region}")

        try:
            req = cvm_models.DescribeImagesRequest()
            
            filters = []
            
            f_type = cvm_models.Filter()
            f_type.Name = "image-type"
            f_type.Values = ["PUBLIC_IMAGE"]
            filters.append(f_type)
            
            if os_name:
                f_os = cvm_models.Filter()
                f_os.Name = "platform"
                f_os.Values = [os_name]
                filters.append(f_os)
                
            req.Filters = filters
            req.Limit = 100 
            
            resp = client.DescribeImages(req)
            images = []
            for img in resp.ImageSet:
                if img.Architecture != architecture:
                    continue
                    
                images.append({
                    "label": f"{img.OsName} ({img.ImageId})",
                    "value": img.ImageId,
                    "os_name": img.OsName,
                    "architecture": img.Architecture
                })
            return images
        except TencentCloudSDKException as err:
            logger.error(f"Tencent Cloud SDK Error in describe_images: {err}")
            raise Exception(f"Tencent Cloud SDK Error: {err.message}")
        except Exception as err:
            logger.error(f"Unexpected error in describe_images: {err}", exc_info=True)
            raise

    def describe_instance_types(self, zone: str, region: str):
        """Get instance types for a zone with detailed info"""
        self._check_config()
        client = self._get_client(region)
        if not client:
             raise Exception(f"Failed to initialize Tencent Cloud client for region {region}")

        try:
            # Get available instance types (quotas) which contains config info
            req = cvm_models.DescribeZoneInstanceConfigInfosRequest()
            
            filters = []
            f_zone = cvm_models.Filter()
            f_zone.Name = "zone"
            f_zone.Values = [zone]
            filters.append(f_zone)
            req.Filters = filters
            
            resp = client.DescribeZoneInstanceConfigInfos(req)
            
            # Use a dictionary to deduplicate by InstanceType (value)
            instance_types_map = {}
            
            for config in resp.InstanceTypeQuotaSet:
                 if config.Status == "SELL":
                     # If duplicate InstanceType found, we can skip or overwrite.
                     # Usually identical InstanceType means same spec.
                     if config.InstanceType not in instance_types_map:
                         instance_types_map[config.InstanceType] = {
                             "value": config.InstanceType,
                             "cpu": config.Cpu,
                             "memory": config.Memory,
                             "family": config.InstanceFamily,
                             "typeName": config.InstanceFamily # Use Family as TypeName fallback
                         }
            
            instance_types = list(instance_types_map.values())
            
            # Sort by CPU then Memory
            instance_types.sort(key=lambda x: (x['cpu'], x['memory']))
            
            return instance_types

        except TencentCloudSDKException as err:
            logger.error(f"Tencent Cloud SDK Error in describe_instance_types: {err}")
            raise Exception(f"Tencent Cloud SDK Error: {err.message}")
        except Exception as err:
            logger.error(f"Unexpected error in describe_instance_types: {err}", exc_info=True)
            raise

    def describe_instances(self, region: str):
        """List Tencent Cloud instances"""
        self._check_config()
        client = self._get_client(region)
        if not client:
             raise Exception(f"Failed to initialize Tencent Cloud client for region {region}")

        try:
            req = cvm_models.DescribeInstancesRequest()
            req.Limit = 100
            
            resp = client.DescribeInstances(req)
            instances = []
            for inst in resp.InstanceSet:
                instances.append({
                    "InstanceId": inst.InstanceId,
                    "InstanceName": inst.InstanceName,
                    "InstanceState": inst.InstanceState,
                    "PublicIpAddresses": inst.PublicIpAddresses,
                    "PrivateIpAddresses": inst.PrivateIpAddresses,
                    "CPU": inst.CPU,
                    "Memory": inst.Memory,
                    "CreatedTime": inst.CreatedTime,
                    "ExpiredTime": inst.ExpiredTime,
                    "OsName": inst.OsName,
                    "Zone": inst.Placement.Zone,
                    "InstanceType": inst.InstanceType,
                    "InstanceChargeType": inst.InstanceChargeType,
                    "InternetAccessible": {
                        "InternetMaxBandwidthOut": inst.InternetAccessible.InternetMaxBandwidthOut if inst.InternetAccessible else 0
                    }
                })
            return instances
        except TencentCloudSDKException as err:
            raise Exception(f"Tencent Cloud SDK Error: {err.message}")

    def create_instance(self, params: Dict[str, Any]):
        """Create Tencent Cloud CVM instance"""
        self._check_config()
        region = params.get('Region')
        client = self._get_client(region)
        if not client:
             raise Exception(f"Failed to initialize Tencent Cloud client for region {region}")

        try:
            req = cvm_models.RunInstancesRequest()
            
            placement = cvm_models.Placement()
            placement.Zone = params['Zone']
            req.Placement = placement
            
            req.ImageId = params['ImageId']
            req.InstanceType = params['InstanceType']
            req.InstanceChargeType = params.get('InstanceChargeType', 'POSTPAID_BY_HOUR')
            req.InstanceName = params['InstanceName']
            
            system_disk = cvm_models.SystemDisk()
            system_disk.DiskType = params.get('SystemDiskType', 'CLOUD_PREMIUM')
            system_disk.DiskSize = params.get('SystemDiskSize', 50)
            req.SystemDisk = system_disk
            
            login_settings = cvm_models.LoginSettings()
            login_settings.Password = params['Password']
            req.LoginSettings = login_settings
            
            if params.get('InternetAccessible'):
                internet_accessible = cvm_models.InternetAccessible()
                internet_accessible.InternetChargeType = params.get('InternetChargeType', "TRAFFIC_POSTPAID_BY_HOUR")
                internet_accessible.InternetMaxBandwidthOut = params.get('InternetMaxBandwidthOut', 1)
                internet_accessible.PublicIpAssigned = True
                req.InternetAccessible = internet_accessible

            if params.get('VpcId') and params.get('SubnetId'):
                vpc = cvm_models.VirtualPrivateCloud()
                vpc.VpcId = params['VpcId']
                vpc.SubnetId = params['SubnetId']
                req.VirtualPrivateCloud = vpc
            
            # Handle Security Groups
            if params.get('SecurityGroupIds'):
                req.SecurityGroupIds = params['SecurityGroupIds']

            # Handle Data Disks
            if params.get('DataDisks'):
                data_disks = []
                for disk_data in params['DataDisks']:
                    data_disk = cvm_models.DataDisk()
                    data_disk.DiskType = disk_data.get('DiskType', 'CLOUD_PREMIUM')
                    data_disk.DiskSize = disk_data.get('DiskSize', 50)
                    data_disks.append(data_disk)
                req.DataDisks = data_disks

            req.InstanceCount = params.get('InstanceCount', 1)
            
            # Handle Prepaid
            if req.InstanceChargeType == 'PREPAID':
                prepaid = cvm_models.InstanceChargePrepaid()
                prepaid.Period = int(params.get('Period', 1))
                prepaid.RenewFlag = params.get('RenewFlag', 'NOTIFY_AND_AUTO_RENEW')
                req.InstanceChargePrepaid = prepaid
            
            if params.get('DryRun'):
                req.DryRun = True

            resp = client.RunInstances(req)
            return json.loads(resp.to_json_string())
            
        except TencentCloudSDKException as err:
            logger.error(f"Tencent Cloud SDK Error: {err}")
            raise Exception(f"Tencent Cloud SDK Error: {err.message}")
        except Exception as err:
            logger.error(f"Unexpected Error creating instance: {err}")
            raise Exception(f"Unexpected Error: {str(err)}")

    def terminate_instances(self, instance_ids: List[str], region: Optional[str] = None):
        """Terminate instances"""
        self._check_config()
        client = self._get_client(region)
        if not client:
             raise Exception(f"Failed to initialize Tencent Cloud client for region {region}")

        try:
            req = cvm_models.TerminateInstancesRequest()
            req.InstanceIds = instance_ids
            
            resp = client.TerminateInstances(req)
            return json.loads(resp.to_json_string())
        except TencentCloudSDKException as err:
            logger.error(f"Tencent Cloud SDK Error in terminate_instances: {err}")
            raise Exception(f"Tencent Cloud SDK Error: {err.message}")
        except Exception as err:
            logger.error(f"Unexpected error in terminate_instances: {err}", exc_info=True)
            raise

    def get_instance_details(self, instance_id: str, region: str):
        """Get full details of a specific instance"""
        self._check_config()
        client = self._get_client(region)
        if not client:
             raise Exception(f"Failed to initialize Tencent Cloud client for region {region}")

        try:
            req = cvm_models.DescribeInstancesRequest()
            req.InstanceIds = [instance_id]
            
            resp = client.DescribeInstances(req)
            if resp.TotalCount == 0:
                raise Exception(f"Instance {instance_id} not found")
                
            return resp.InstanceSet[0]
        except TencentCloudSDKException as err:
            raise Exception(f"Tencent Cloud SDK Error: {err.message}")

    def extract_template_from_instance(self, instance_id: str, region: str) -> Dict[str, Any]:
        """Extract configuration from an instance to create a template"""
        instance = self.get_instance_details(instance_id, region)
        
        # Map instance properties to template format
        template = {
            "Region": region,
            "ImageId": instance.ImageId,
            "InstanceType": instance.InstanceType,
            "Zone": instance.Placement.Zone,
            "InstanceChargeType": instance.InstanceChargeType,
            "SystemDiskSize": instance.SystemDisk.DiskSize,
            "SystemDiskType": instance.SystemDisk.DiskType,
            "InstanceName": f"{instance.InstanceName}-template",
            "InternetAccessible": False,
            "InternetMaxBandwidthOut": 0
        }

        # Network
        if instance.VirtualPrivateCloud:
            template["VpcId"] = instance.VirtualPrivateCloud.VpcId
            template["SubnetId"] = instance.VirtualPrivateCloud.SubnetId

        # Internet Access
        if instance.InternetAccessible:
            template["InternetAccessible"] = True
            template["InternetMaxBandwidthOut"] = instance.InternetAccessible.InternetMaxBandwidthOut
            template["InternetChargeType"] = instance.InternetAccessible.InternetChargeType

        # Data Disks
        if instance.DataDisks:
            data_disks = []
            for disk in instance.DataDisks:
                data_disks.append({
                    "DiskSize": disk.DiskSize,
                    "DiskType": disk.DiskType,
                    # SnapshotId can be added if needed, but for generic template usually not
                })
            template["DataDisks"] = data_disks

        # Security Groups
        if instance.SecurityGroupIds:
            template["SecurityGroupIds"] = instance.SecurityGroupIds

        return template
