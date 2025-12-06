import { request } from '@umijs/max';
import { authStorage } from '@/utils/auth';

const getHeaders = () => {
  const token = authStorage.getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export async function getInstances(region?: string) {
  return request<TencentAPI.Instance[]>('/api/tencent/instances', {
    method: 'GET',
    headers: getHeaders(),
    params: { region },
  });
}

export async function createInstance(data: TencentAPI.InstanceCreate) {
  return request<any>('/api/tencent/instances', {
    method: 'POST',
    headers: getHeaders(),
    data,
  });
}

export async function instanceAction(instanceId: string, action: string, password?: string) {
  return request<any>(`/api/tencent/instances/${instanceId}/${action}`, {
    method: 'POST',
    headers: getHeaders(),
    data: password ? { password } : {},
  });
}

export async function deleteInstance(instanceId: string, region: string) {
    return request<any>(`/api/tencent/instances/${instanceId}`, {
      method: 'DELETE',
      headers: getHeaders(),
      params: { region },
    });
  }

export async function batchDeleteInstances(instanceIds: string[], region: string) {
  return request<any>('/api/tencent/instances/batch-delete', {
    method: 'POST',
    headers: getHeaders(),
    data: { InstanceIds: instanceIds, Region: region },
  });
}

export async function getAccountInfo() {
  return request<TencentAPI.AccountInfo>('/api/tencent/account', {
    method: 'GET',
    headers: getHeaders(),
  });
}

export async function getRegions() {
  return request<any[]>('/api/tencent/regions', {
    method: 'GET',
    headers: getHeaders(),
  });
}

export async function getZones(region?: string) {
  return request<any[]>('/api/tencent/zones', {
    method: 'GET',
    headers: getHeaders(),
    params: { region },
  });
}

export async function getInstanceTypes(zone?: string, region?: string) {
  return request<any[]>('/api/tencent/instance-types', {
    method: 'GET',
    headers: getHeaders(),
    params: { zone, region },
  });
}

export async function getImages(architecture?: string, osName?: string, region?: string) {
  return request<any[]>('/api/tencent/images', {
    method: 'GET',
    headers: getHeaders(),
    params: { architecture, os_name: osName, region },
  });
}

export async function syncInstances(data: { Region: string; Instances: { InstanceId: string; Password: string }[] }) {
  return request<{ message: string }>('/api/tencent/instances/sync', {
    method: 'POST',
    headers: getHeaders(),
    data,
  });
}
