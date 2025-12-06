import { request } from '@umijs/max';
import { authStorage } from '@/utils/auth';

const getHeaders = () => {
  const token = authStorage.getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export async function createWorkflow(data: any) {
  return request<any>('/api/workflows/create', {
    method: 'POST',
    headers: getHeaders(),
    data,
  });
}

export async function batchCreateWorkflow(data: { template_id: number; ansible_template_id?: number; instances: any[] }) {
  return request<any>('/api/workflows/batch-create', {
    method: 'POST',
    headers: getHeaders(),
    data,
  });
}

export async function getWorkflows(params?: { limit?: number }) {
  return request<any[]>('/api/workflows', {
    method: 'GET',
    headers: getHeaders(),
    params,
  });
}

export async function getWorkflow(id: number) {
  return request<any>(`/api/workflows/${id}`, {
    method: 'GET',
    headers: getHeaders(),
  });
}

export async function getWorkflowLogs(id: number) {
  return request<any[]>(`/api/workflows/${id}/logs`, {
    method: 'GET',
    headers: getHeaders(),
  });
}

export async function extractTemplate(data: { instance_id: string; region: string }) {
  return request<any>('/api/workflows/template-from-instance', {
    method: 'POST',
    headers: getHeaders(),
    data,
  });
}
