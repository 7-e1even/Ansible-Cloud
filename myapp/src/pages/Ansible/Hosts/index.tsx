import React, { useRef, useState, useEffect } from 'react';
import { PageContainer, ProTable, ActionType, ProColumns, ModalForm, ProFormTextArea, ProFormSwitch, ProFormText, ProFormDigit, ProFormSelect } from '@ant-design/pro-components';
import { Button, message, Space, Popconfirm, Tag, Modal, Form, Input, Switch, Tooltip, Badge } from 'antd';
import { PlusOutlined, UploadOutlined, CodeOutlined, FileTextOutlined, ReloadOutlined, EditOutlined, DeleteOutlined, CheckCircleOutlined, CloseCircleOutlined, SyncOutlined, ExclamationCircleOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { history } from '@umijs/max';
import { getHosts, addHostsBatch, getAccessLogs, updateHost, deleteHost, addHost, checkAllHostsStatus, checkHostStatus, getGroups } from '@/services/ansible/api';
import { prepareHostData } from '@/utils/crypto';
import PlaybookExecutor from '../components/PlaybookExecutor';
import FileUpload from '../components/FileUpload';

const HostsPage: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  
  // Modal states
  const [isPlaybookOpen, setIsPlaybookOpen] = useState(false);
  const [isFileUploadOpen, setIsFileUploadOpen] = useState(false);
  const [isLogsOpen, setIsLogsOpen] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [addModalVisible, setAddModalVisible] = useState(false);
  const [currentHost, setCurrentHost] = useState<AnsibleAPI.Host | null>(null);
  const [playbookTarget, setPlaybookTarget] = useState<'selected' | 'all'>('selected');
  
  // Batch Add State
  const [batchInput, setBatchInput] = useState('');
  const [useKeyAuth, setUseKeyAuth] = useState(false);

  // Access Logs State
  const [logs, setLogs] = useState<AnsibleAPI.AccessLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [checkingStatus, setCheckingStatus] = useState(false);
  const [checkingHostId, setCheckingHostId] = useState<number | null>(null);

  // Handle Delete
  const handleDelete = async (hostId: number) => {
    try {
      await deleteHost(hostId);
      message.success('删除成功');
      actionRef.current?.reload();
    } catch (error) {
      message.error('删除失败');
    }
  };

  // Handle Update
  const handleUpdate = async (values: any) => {
    if (!currentHost) return;
    try {
      await updateHost(currentHost.id, values);
      message.success('更新成功');
      setEditModalVisible(false);
      setCurrentHost(null);
      actionRef.current?.reload();
      return true;
    } catch (error) {
      message.error('更新失败');
      return false;
    }
  };

  // Handle Check All Status
  const handleCheckAllStatus = async () => {
    setCheckingStatus(true);
    try {
      const res = await checkAllHostsStatus();
      message.success(res.message);
      
      // Show summary
      const results = res.results || {};
      const total = Object.keys(results).length;
      const success = Object.values(results).filter(s => s === 'success').length;
      const failed = Object.values(results).filter(s => s === 'failed').length;
      const unreachable = Object.values(results).filter(s => s === 'unreachable').length;
      
      Modal.info({
        title: '状态检查完成',
        content: (
          <div>
            <p>总计检查: {total}</p>
            <p style={{ color: 'green' }}>正常: {success}</p>
            <p style={{ color: 'red' }}>失败: {failed}</p>
            <p style={{ color: 'orange' }}>不可达: {unreachable}</p>
          </div>
        ),
      });
      
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '检查状态失败');
    } finally {
      setCheckingStatus(false);
    }
  };

  // Handle Single Check Status
  const handleCheckHostStatus = async (hostId: number) => {
    setCheckingHostId(hostId);
    try {
      const res = await checkHostStatus(hostId);
      const status = res.status;
      if (status === 'success') {
        message.success('主机连接正常');
      } else if (status === 'unreachable') {
        message.warning('主机不可达');
      } else {
        message.error('连接失败');
      }
      actionRef.current?.reload();
    } catch (error: any) {
      message.error(error.message || '检查状态失败');
    } finally {
      setCheckingHostId(null);
    }
  };

  // Columns for Host Table
  const columns: ProColumns<AnsibleAPI.Host>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 60,
      search: false,
    },
    {
      title: '分组',
      dataIndex: 'group_name',
      valueType: 'select',
      request: async () => {
        const groups = await getGroups();
        return groups.map(g => ({ label: g, value: g }));
      },
      fieldProps: {
        showSearch: true,
      },
      copyable: true,
    },
    {
      title: '备注',
      dataIndex: 'comment',
      copyable: true,
      ellipsis: true,
    },
    {
      title: '地址',
      dataIndex: 'address',
      copyable: true,
      width: 140,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      width: 100,
      ellipsis: true,
    },
    {
      title: '端口',
      dataIndex: 'port',
      width: 80,
      search: false,
    },
    {
      title: '认证方式',
      dataIndex: 'auth_method',
      valueEnum: {
        password: { text: '密码', status: 'Default' },
        key: { text: '密钥', status: 'Success' },
      },
      width: 100,
    },
    {
      title: '状态',
      dataIndex: 'status',
      render: (_, record) => {
        let statusNode = <Tag color="default">未知</Tag>;
        if (record.status === 'success') {
          statusNode = <Tag icon={<CheckCircleOutlined />} color="success">正常</Tag>;
        } else if (record.status === 'failed') {
          statusNode = <Tag icon={<CloseCircleOutlined />} color="error">失败</Tag>;
        } else if (record.status === 'unreachable') {
          statusNode = <Tag icon={<ExclamationCircleOutlined />} color="warning">不可达</Tag>;
        } else if (record.status === 'checking') {
          statusNode = <Tag icon={<SyncOutlined spin />} color="processing">检查中</Tag>;
        }
        
        return (
           <Space>
             {statusNode}
             <a onClick={() => handleCheckHostStatus(record.id)}>
                {checkingHostId === record.id ? <SyncOutlined spin /> : <ReloadOutlined />}
             </a>
           </Space>
        );
      },
    },
    {
      title: '操作',
      valueType: 'option',
      render: (text, record, _, action) => [
        <a key="terminal" onClick={() => history.push(`/ansible/terminal?host_id=${record.id}`)}>
          <CodeOutlined /> 终端
        </a>,
        <a key="edit" onClick={() => {
          setCurrentHost(record);
          setEditModalVisible(true);
        }}>
          <EditOutlined /> 编辑
        </a>,
        <Popconfirm
           key="delete"
           title="确认删除?"
           onConfirm={() => handleDelete(record.id)}
        >
          <a style={{ color: 'red' }}>
            <DeleteOutlined /> 删除
          </a>
        </Popconfirm>,
      ],
    },
  ];

  // Handle Single Add
  const handleSingleAdd = async (values: any) => {
    try {
      await addHost(values);
      message.success('添加成功');
      setAddModalVisible(false);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '添加失败');
      return false;
    }
  };

  // Handle Batch Add
  const handleBatchAdd = async () => {
    if (!batchInput.trim()) {
      message.error('请输入主机信息');
      return false;
    }

    const lines = batchInput.trim().split('\n');
    const hostsData: any[] = [];
    const errors: string[] = [];
    const expectedParts = useKeyAuth ? 4 : 5;
    const formatString = useKeyAuth ? "'备注 地址 用户名 端口'" : "'备注 地址 用户名 端口 密码'";

    lines.forEach((line, index) => {
      if (line.trim() === '') return;
      const parts = line.trim().split(/\s+/);
      if (parts.length !== expectedParts) {
        errors.push(`第${index + 1}行：格式错误，应为 ${formatString}`);
      } else {
        const [comment, address, username, portStr, password] = parts;
        const port = parseInt(portStr, 10);
        if (isNaN(port)) {
          errors.push(`第${index + 1}行：端口号 '${portStr}' 无效`);
        } else {
          hostsData.push({
            comment,
            address,
            username,
            port,
            password: useKeyAuth ? '' : password
          });
        }
      }
    });

    if (errors.length > 0) {
      errors.forEach(err => message.error(err));
      return false;
    }

    try {
      const processedHostsData = hostsData.map(host => prepareHostData(host, undefined, useKeyAuth));
      const response = await addHostsBatch(processedHostsData);
      message.success(response.message || `成功添加 ${response.count} 台主机`);
      actionRef.current?.reload();
      return true;
    } catch (error: any) {
      message.error(error.message || '添加失败');
      return false;
    }
  };

  // Fetch Logs
  const fetchLogs = async () => {
    setLoadingLogs(true);
    try {
      const data = await getAccessLogs({});
      setLogs(data);
      setIsLogsOpen(true);
    } catch (error) {
      message.error('获取日志失败');
    } finally {
      setLoadingLogs(false);
    }
  };

  return (
    <PageContainer>
      <ProTable<AnsibleAPI.Host>
        columns={columns}
        actionRef={actionRef}
        size="small"
        scroll={{ x: 1200, y: 'calc(100vh - 420px)' }}
        pagination={{
          defaultPageSize: 20,
          showSizeChanger: true, 
          pageSizeOptions: ['20', '50', '100']
        }}
        cardBordered
        request={async (params, sort, filter) => {
          const data = await getHosts({ group_name: params.group_name });
          // ProTable expects { data: T[], success: boolean, total: number }
          // But our API returns T[] directly
          return {
            data: data,
            success: true,
            total: data.length,
          };
        }}
        rowKey="id"
        search={{
          labelWidth: 'auto',
        }}
        options={{
          setting: {
            listsHeight: 400,
          },
        }}
        pagination={{
          pageSize: 10,
        }}
        dateFormatter="string"
        headerTitle="主机列表"
        rowSelection={{
          selectedRowKeys,
          onChange: (keys) => setSelectedRowKeys(keys),
        }}
        toolBarRender={() => [
          <Button
             key="check-all"
             icon={checkingStatus ? <SyncOutlined spin /> : <PlayCircleOutlined />}
             onClick={handleCheckAllStatus}
             loading={checkingStatus}
          >
            检查状态
          </Button>,
          <Button
            key="logs"
            icon={<FileTextOutlined />}
            onClick={fetchLogs}
            loading={loadingLogs}
          >
            访问日志
          </Button>,
          <Button
            key="single-add"
            icon={<PlusOutlined />}
            onClick={() => setAddModalVisible(true)}
          >
            单条添加
          </Button>,
          <ModalForm
            key="batch-add"
            title="批量添加主机"
            trigger={
              <Button key="button" icon={<PlusOutlined />} type="primary">
                批量添加
              </Button>
            }
            onFinish={handleBatchAdd}
          >
             <div style={{ marginBottom: 16 }}>
               <Switch 
                 checked={useKeyAuth} 
                 onChange={setUseKeyAuth} 
                 checkedChildren="密钥认证" 
                 unCheckedChildren="密码认证" 
               />
               <span style={{ marginLeft: 8, color: '#888' }}>
                 {useKeyAuth ? '无需输入密码' : '需要输入密码'}
               </span>
             </div>
             <ProFormTextArea
               name="batchInput"
               label="主机信息"
               placeholder={useKeyAuth 
                 ? "每行一台主机，格式：备注 地址 用户名 端口" 
                 : "每行一台主机，格式：备注 地址 用户名 端口 密码"
               }
               fieldProps={{
                 value: batchInput,
                 onChange: (e) => setBatchInput(e.target.value),
                 rows: 10,
                 style: { fontFamily: 'monospace' }
               }}
             />
          </ModalForm>
        ]}
        tableAlertOptionRender={() => {
          return (
            <Space size={16}>
              <a onClick={() => {
                setPlaybookTarget('selected');
                setIsPlaybookOpen(true);
              }}>
                执行Playbook
              </a>
              <a onClick={() => {
                 setIsFileUploadOpen(true);
              }}>
                分发文件
              </a>
            </Space>
          );
        }}
      />

      {/* Playbook Executor Modal */}
      <PlaybookExecutor 
        open={isPlaybookOpen}
        onCancel={() => setIsPlaybookOpen(false)}
        targetHostIds={playbookTarget === 'all' ? 'all' : (selectedRowKeys as number[])}
        onExecutionComplete={() => {
          // Optional: Refresh host status if playbook changes something
        }}
      />

      {/* Edit Host Modal */}
      <ModalForm
        title="编辑主机"
        open={editModalVisible}
        onOpenChange={setEditModalVisible}
        modalProps={{
          destroyOnClose: true,
        }}
        onFinish={handleUpdate}
        initialValues={currentHost || {}}
      >
        <ProFormSelect
          name="group_name"
          label="分组"
          placeholder="请输入或选择分组"
          request={async () => {
            const groups = await getGroups();
            return groups.map(g => ({ label: g, value: g }));
          }}
          fieldProps={{
              mode: 'tags'
          }}
        />
        <ProFormText
          name="comment"
          label="备注"
          placeholder="请输入备注（可选）"
        />
        <ProFormText
          name="address"
          label="地址"
          placeholder="请输入IP地址或主机名"
          rules={[{ required: true, message: '请输入地址' }]}
        />
        <ProFormText
          name="username"
          label="用户名"
          placeholder="请输入用户名"
          rules={[{ required: true, message: '请输入用户名' }]}
        />
        <ProFormDigit
          name="port"
          label="端口"
          placeholder="请输入端口"
          min={1}
          max={65535}
          initialValue={22}
          rules={[{ required: true, message: '请输入端口' }]}
        />
        <ProFormSelect
          name="auth_method"
          label="认证方式"
          valueEnum={{
            password: '密码',
            key: '密钥',
          }}
          initialValue="password"
          rules={[{ required: true, message: '请选择认证方式' }]}
        />
        <ProFormText.Password
          name="password"
          label="密码"
          placeholder="如果不修改密码请留空"
          dependencies={['auth_method']}
          rules={[
             ({ getFieldValue }) => ({
               validator(_, value) {
                 // For edit: empty means no change
                 return Promise.resolve();
               },
             }),
          ]}
        />
      </ModalForm>

      {/* Add Host Modal */}
      <ModalForm
        title="添加主机"
        open={addModalVisible}
        onOpenChange={setAddModalVisible}
        modalProps={{
          destroyOnClose: true,
        }}
        onFinish={handleSingleAdd}
        initialValues={{
          port: 22,
          auth_method: 'password',
          group_name: 'all',
        }}
      >
        <ProFormSelect
          name="group_name"
          label="分组"
          placeholder="请输入或选择分组"
          request={async () => {
            const groups = await getGroups();
            return groups.map(g => ({ label: g, value: g }));
          }}
          fieldProps={{
              mode: 'tags'
          }}
        />
        <ProFormText
          name="comment"
          label="备注"
          placeholder="请输入备注（可选）"
        />
        <ProFormText
          name="address"
          label="地址"
          placeholder="请输入IP地址或主机名"
          rules={[{ required: true, message: '请输入地址' }]}
        />
        <ProFormText
          name="username"
          label="用户名"
          placeholder="请输入用户名"
          rules={[{ required: true, message: '请输入用户名' }]}
        />
        <ProFormDigit
          name="port"
          label="端口"
          placeholder="请输入端口"
          min={1}
          max={65535}
          rules={[{ required: true, message: '请输入端口' }]}
        />
        <ProFormSelect
          name="auth_method"
          label="认证方式"
          valueEnum={{
            password: '密码',
            key: '密钥',
          }}
          rules={[{ required: true, message: '请选择认证方式' }]}
        />
        <ProFormText.Password
          name="password"
          label="密码"
          placeholder="请输入密码"
          dependencies={['auth_method']}
          rules={[
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (getFieldValue('auth_method') === 'password' && !value) {
                  return Promise.reject(new Error('密码认证方式下，密码不能为空'));
                }
                return Promise.resolve();
              },
            }),
          ]}
        />
      </ModalForm>

      {/* File Upload Modal */}
      <FileUpload
        open={isFileUploadOpen}
        onCancel={() => setIsFileUploadOpen(false)}
        targetHostIds={selectedRowKeys as number[]}
        onUploadComplete={() => {
           // Done
        }}
      />

      {/* Access Logs Modal */}
      <Modal
        title="访问日志"
        open={isLogsOpen}
        onCancel={() => setIsLogsOpen(false)}
        width={800}
        footer={null}
      >
        <ProTable<AnsibleAPI.AccessLog>
           dataSource={logs}
           rowKey="id"
           search={false}
           pagination={{ pageSize: 5 }}
           columns={[
             { title: '时间', dataIndex: 'access_time' },
             { title: 'IP', dataIndex: 'ip_address' },
             { title: '路径', dataIndex: 'path' },
             { title: '状态码', dataIndex: 'status_code', 
               render: (val) => <Tag color={val === 200 ? 'green' : 'red'}>{val}</Tag> 
             },
           ]}
        />
      </Modal>
    </PageContainer>
  );
};

export default HostsPage;
