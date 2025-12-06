import { request } from '@umijs/max';
import { authStorage } from '@/utils/auth';

const getHeaders = () => {
  const token = authStorage.getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

/** 登录 */
export async function login(body: { username: string; password: string }) {
  return request<{ success: boolean; token: string; message?: string }>('/api/login', {
    method: 'POST',
    data: body,
  });
}

/** 获取主机列表 */
export async function getHosts(params?: { group_name?: string }) {
  return request<AnsibleAPI.Host[]>('/api/hosts', {
    method: 'GET',
    headers: getHeaders(),
    params,
  });
}

/** 获取主机分组列表 */
export async function getGroups() {
  return request<string[]>('/api/hosts/groups', {
    method: 'GET',
    headers: getHeaders(),
  });
}

/** 批量添加主机 */
export async function addHostsBatch(data: any[]) {
  return request<AnsibleAPI.BatchHostResult>('/api/hosts/batch', {
    method: 'POST',
    headers: getHeaders(),
    data,
  });
}

/** 添加单个主机 */
export async function addHost(data: any) {
  return request<{ message: string; host_id: number }>('/api/hosts', {
    method: 'POST',
    headers: getHeaders(),
    data,
  });
}

/** 更新主机 */
export async function updateHost(hostId: number, data: Partial<AnsibleAPI.Host>) {
  return request<{ message: string }>('/api/hosts/' + hostId, {
    method: 'PUT',
    headers: getHeaders(),
    data,
  });
}

/** 删除主机 */
export async function deleteHost(hostId: number) {
  return request<{ message: string }>('/api/hosts/' + hostId, {
    method: 'DELETE',
    headers: getHeaders(),
  });
}

/** 检查所有主机状态 */
export async function checkAllHostsStatus() {
  return request<{ message: string; results: Record<number, string> }>('/api/hosts/check-status', {
    method: 'POST',
    headers: getHeaders(),
  });
}

/** 检查单个主机状态 */
export async function checkHostStatus(hostId: number) {
  return request<{ message: string; status: string }>('/api/hosts/' + hostId + '/check-status', {
    method: 'POST',
    headers: getHeaders(),
  });
}

/** 获取访问日志 */
export async function getAccessLogs(params: { ip?: string; path?: string }) {
  return request<AnsibleAPI.AccessLog[]>('/api/access-logs', {
    method: 'GET',
    headers: getHeaders(),
    params,
  });
}

/** 执行 Playbook */
export async function executePlaybook(data: AnsibleAPI.PlaybookParams) {
  return request<AnsibleAPI.PlaybookResult>('/api/playbook/execute', {
    method: 'POST',
    headers: getHeaders(),
    data,
  });
}

/** 上传文件 */
export async function uploadFile(formData: FormData) {
  return request<AnsibleAPI.FileUploadResult>('/api/files/upload', {
    method: 'POST',
    headers: getHeaders(),
    data: formData,
    // request 会自动处理 FormData 的 Content-Type
  });
}

/** 获取模板列表 */
export async function getTemplates(type?: string) {
  return request<AnsibleAPI.Template[]>('/api/templates', {
    method: 'GET',
    headers: getHeaders(),
    params: { type },
  });
}

/** 获取单个模板 */
export async function getTemplate(templateId: number, type?: string) {
  return request<AnsibleAPI.Template>('/api/templates/' + templateId, {
    method: 'GET',
    headers: getHeaders(),
    params: { type },
  });
}

/** 添加模板 */
export async function addTemplate(data: Partial<AnsibleAPI.Template>) {
  return request<{ message: string; template_id: number }>('/api/templates', {
    method: 'POST',
    headers: getHeaders(),
    data,
  });
}

/** 更新模板 */
export async function updateTemplate(templateId: number, data: Partial<AnsibleAPI.Template>) {
  return request<{ message: string }>('/api/templates/' + templateId, {
    method: 'PUT',
    headers: getHeaders(),
    data,
  });
}

/** 删除模板 */
export async function deleteTemplate(templateId: number, type?: string) {
  return request<{ message: string }>('/api/templates/' + templateId, {
    method: 'DELETE',
    headers: getHeaders(),
    params: { type },
  });
}

/** 获取WebSocket Token */
export async function getWsToken(hostId: number) {
  return request<{ token: string }>(`/api/ws-token/${hostId}`, {
    method: 'GET',
    headers: getHeaders(),
  });
}

/** 启动 Playbook 任务 */
export async function executePlaybookTask(data: { playbook: string; host_ids?: number[] | 'all'; group_name?: string; name?: string }) {
  return request<{ task_id: number; message: string }>('/api/tasks/execute', {
    method: 'POST',
    headers: getHeaders(),
    data,
  });
}

/** 获取任务列表 */
export async function getTasks(params?: { limit?: number }) {
  return request<AnsibleAPI.Task[]>('/api/tasks', {
    method: 'GET',
    headers: getHeaders(),
    params,
  });
}

/** 获取任务详情 */
export async function getTask(taskId: number) {
  return request<AnsibleAPI.Task>(`/api/tasks/${taskId}`, {
    method: 'GET',
    headers: getHeaders(),
  });
}
