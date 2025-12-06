declare namespace AnsibleAPI {
  interface Host {
    id: number;
    comment: string;
    address: string;
    username: string;
    port: number;
    password?: string;
    status?: 'checking' | 'success' | 'unreachable' | 'failed' | null;
    is_password_encrypted?: boolean;
    auth_method?: 'password' | 'key';
    group_name?: string;
  }

  interface AccessLog {
    id: number;
    access_time: string;
    ip_address: string;
    path: string;
    status_code: number;
  }

  interface PlaybookResult {
    success: boolean;
    return_code: number;
    logs: string[];
    summary: {
      success: string[];
      failed: string[];
      unreachable: string[];
    };
  }

  interface PlaybookParams {
    playbook: string;
    host_ids: number[] | 'all';
  }

  interface BatchHostParams {
    hosts: Host[];
  }

  interface BatchHostResult {
    success: boolean;
    count: number;
    message?: string;
  }

  interface FileUploadParams {
    file: File;
    target_path: string;
    host_ids: number[] | 'all';
  }

  interface FileUploadResult {
    success: boolean;
    message: string;
    details?: any;
  }

  interface Template {
    id: number;
    name: string;
    description?: string;
    content: string;
    created_at: string;
    updated_at: string;
  }

  interface Task {
    id: number;
    type: string;
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    target_hosts: number[];
    params: any;
    result?: PlaybookResult;
    logs?: string[];
    created_at: string;
    updated_at: string;
    completed_at?: string;
  }
}
