import { request } from '@umijs/max';

export namespace CloudAPI {
  export type Credential = {
    id: number;
    name: string;
    provider: string;
    access_key: string;
    is_default: boolean;
    created_at: string;
    updated_at: string;
  };

  export type CreateCredentialParams = {
    name: string;
    provider: string;
    access_key: string;
    secret_key: string;
    is_default?: boolean;
  };

  export type UpdateCredentialParams = {
    name?: string;
    provider?: string;
    access_key?: string;
    secret_key?: string;
    is_default?: boolean;
  };
  
  export type TestCredentialParams = {
      provider: string;
      access_key: string;
      secret_key: string;
  }
}

export async function getCredentials(params?: { provider?: string }) {
  return request<CloudAPI.Credential[]>('/api/cloud-credentials', {
    method: 'GET',
    params,
  });
}

export async function createCredential(data: CloudAPI.CreateCredentialParams) {
  return request<CloudAPI.Credential>('/api/cloud-credentials', {
    method: 'POST',
    data,
  });
}

export async function updateCredential(id: number, data: CloudAPI.UpdateCredentialParams) {
  return request<CloudAPI.Credential>(`/api/cloud-credentials/${id}`, {
    method: 'PUT',
    data,
  });
}

export async function deleteCredential(id: number) {
  return request<{ success: boolean }>(`/api/cloud-credentials/${id}`, {
    method: 'DELETE',
  });
}

export async function testCredential(data: CloudAPI.TestCredentialParams) {
    return request<{ success: boolean; message: string }>('/api/cloud-credentials/test', {
        method: 'POST',
        data,
    });
}
