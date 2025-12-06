declare namespace TencentAPI {
  type Config = {
    secret_id: string;
    region: string;
    is_configured?: boolean;
    masked_secret_key?: string;
    secret_key?: string; // For create
  };

  type Instance = {
    InstanceId: string;
    InstanceName: string;
    InstanceState: string;
    PublicIpAddresses: string[];
    PrivateIpAddresses: string[];
    CPU: number;
    Memory: number;
    CreatedTime: string;
    ExpiredTime: string;
    OsName: string;
  };

  type InstanceCreate = {
    InstanceName: string;
    ImageId: string;
    InstanceType: string;
    Zone: string;
    Password: string;
    DryRun?: boolean;
  };

  type AccountInfo = {
    Balance: number;
    Currency: string;
  };
}
