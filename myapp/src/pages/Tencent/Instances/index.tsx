import { PageContainer, ProTable, ActionType, ProCard } from '@ant-design/pro-components';
import { Button, message as antdMessage, Popconfirm, Modal, Form, Input, Card, Statistic, Row, Col, Tag, Space, Typography, Dropdown, App } from 'antd';
import { useRef, useState, useEffect } from 'react';
import { getInstances, instanceAction, getAccountInfo, deleteInstance, getRegions, batchDeleteInstances } from '@/services/tencent/api';
import { extractTemplate } from '@/services/workflow/api';
import { PlusOutlined, ReloadOutlined, EllipsisOutlined, PoweroffOutlined, CaretRightOutlined, DeleteOutlined, SyncOutlined, CopyOutlined } from '@ant-design/icons';
import { history } from '@umijs/max';

const { Text } = Typography;

const Instances: React.FC = () => {
  const { message, modal } = App.useApp();
  const actionRef = useRef<ActionType>();
  const errorShownRef = useRef(false);
  const [passwordModalVisible, setPasswordModalVisible] = useState(false);
  const [currentInstance, setCurrentInstance] = useState<string>();
  const [balance, setBalance] = useState<TencentAPI.AccountInfo>();
  const [currentRegion, setCurrentRegion] = useState<string>('ap-nanjing');
  const [form] = Form.useForm();

  const handleError = (e: any) => {
    if (errorShownRef.current) return;
    
    const errorMsg = e?.response?.data?.detail || e.message || 'Unknown error';
    // Check for specific error message regarding missing credentials
    if (e?.response?.status === 400 && (errorMsg.includes("configure Tencent Cloud Access Key") || errorMsg.includes("credentials not configured"))) {
        errorShownRef.current = true;
        modal.warning({
            title: '需要配置腾讯云密钥',
            content: '检测到您尚未配置腾讯云 AccessKey/SecretKey，请前往设置页面进行配置。',
            okText: '前往配置',
            onOk: () => {
                errorShownRef.current = false;
                history.push('/cloud/keys');
            },
            onCancel: () => {
                errorShownRef.current = false;
            },
            closable: true,
        });
    } else {
         message.error(`获取数据失败: ${errorMsg}`);
    }
  };
  
  useEffect(() => {
    getAccountInfo().then(setBalance).catch((e) => {
        // Also check error here
        handleError(e);
    });
  }, []);

  const handleAction = async (id: string, action: string) => {
    try {
      await instanceAction(id, action);
      message.success(`操作 ${action} 已触发`);
      actionRef.current?.reload();
    } catch (e: any) {
      message.error(`触发 ${action} 失败: ${e.message}`);
    }
  };

  const handleDelete = async (id: string) => {
      try {
          await deleteInstance(id, currentRegion);
          message.success('删除/销毁实例操作已触发');
          actionRef.current?.reload();
      } catch (e: any) {
          message.error(`删除失败: ${e.message}`);
      }
  };

  const handleBatchDelete = async (selectedRowKeys: React.Key[]) => {
    try {
      await batchDeleteInstances(selectedRowKeys as string[], currentRegion);
      message.success('批量销毁/退还实例操作已触发');
      actionRef.current?.reload();
      actionRef.current?.clearSelected();
    } catch (e: any) {
      message.error(`批量删除失败: ${e.message}`);
    }
  };

  const handleResetPassword = async () => {
    try {
        const values = await form.validateFields();
        if (currentInstance) {
            await instanceAction(currentInstance, 'reset_password', values.password);
            message.success('重置密码已触发');
            setPasswordModalVisible(false);
            form.resetFields();
        }
    } catch (e) {
        // Validation failed
    }
  };

  const handleExtractTemplate = async (instanceId: string) => {
    try {
      const hide = message.loading('正在提取模板...', 0);
      await extractTemplate({ instance_id: instanceId, region: currentRegion });
      hide();
      message.success('模板提取成功，已保存到模板列表');
    } catch (e: any) {
      message.error(`模板提取失败: ${e.message}`);
    }
  };

  const columns: any[] = [
    {
      title: '地域',
      dataIndex: 'Region',
      hideInTable: true,
      valueType: 'select',
      request: async () => {
          try {
              const regions = await getRegions();
              return regions;
          } catch (e) {
              handleError(e);
              return [];
          }
      },
      formItemProps: {
          rules: [{ required: true, message: '请选择地域' }],
      },
      initialValue: 'ap-nanjing',
    },
    {
      title: '实例信息',
      dataIndex: 'InstanceName',
      width: 250,
      render: (dom: any, entity: any) => (
          <Space direction="vertical" size={0}>
              <Text strong>{entity.InstanceName}</Text>
              <Text type="secondary" copyable={{text: entity.InstanceId}} style={{fontSize: '12px'}}>{entity.InstanceId}</Text>
              <Space size={4} style={{marginTop: 4}}>
                  <Tag>{entity.Zone}</Tag>
                  <Tag>{entity.InstanceType}</Tag>
              </Space>
          </Space>
      )
    },
    {
      title: '状态',
      dataIndex: 'InstanceState',
      width: 100,
      valueEnum: {
        RUNNING: { text: '运行中', status: 'Success' },
        STOPPED: { text: '已关机', status: 'Default' },
        STARTING: { text: '启动中', status: 'Processing' },
        STOPPING: { text: '关机中', status: 'Processing' },
        REBOOTING: { text: '重启中', status: 'Processing' },
      },
      filters: true,
      onFilter: true,
    },
    {
      title: '网络信息',
      dataIndex: 'PublicIpAddresses',
      width: 200,
      search: false,
      render: (_: any, record: TencentAPI.Instance) => (
          <Space direction="vertical" size={0}>
              <div><Tag color="blue">公</Tag> {record.PublicIpAddresses?.join(', ') || '-'}</div>
              <div><Tag color="cyan">内</Tag> {record.PrivateIpAddresses?.join(', ') || '-'}</div>
          </Space>
      ),
    },
    {
      title: '配置详情',
      search: false,
      width: 150,
      render: (_: any, record: TencentAPI.Instance) => (
          <Space direction="vertical" size={0} style={{fontSize: '13px'}}>
              <div>CPU: {record.CPU} 核</div>
              <div>内存: {record.Memory} GB</div>
              <div>带宽: {record.InternetAccessible?.InternetMaxBandwidthOut || 0} Mbps</div>
          </Space>
      ),
    },
    {
      title: '计费模式',
      dataIndex: 'InstanceChargeType',
      width: 100,
      search: false,
      valueEnum: {
          'POSTPAID_BY_HOUR': { text: '按量计费', status: 'Warning' },
          'PREPAID': { text: '包年包月', status: 'Success' },
      },
      render: (dom: any, entity: any) => <Tag color={entity.InstanceChargeType === 'PREPAID' ? 'green' : 'orange'}>{entity.InstanceChargeType === 'PREPAID' ? '包年包月' : '按量计费'}</Tag>
    },
    {
      title: '创建时间',
      dataIndex: 'CreatedTime',
      valueType: 'dateTime',
      width: 160,
      search: false,
    },
    {
      title: '操作',
      valueType: 'option',
      width: 200,
      fixed: 'right',
      render: (_: any, record: TencentAPI.Instance) => {
          const isRunning = record.InstanceState === 'RUNNING';
          const isStopped = record.InstanceState === 'STOPPED';
          
          return (
            <Space>
                {isStopped && (
                    <a key="start" onClick={() => handleAction(record.InstanceId, 'start')}>
                        <CaretRightOutlined /> 开机
                    </a>
                )}
                {isRunning && (
                    <Popconfirm title="确定要关机吗?" okText="是" cancelText="否" onConfirm={() => handleAction(record.InstanceId, 'stop')}>
                        <a key="stop" style={{ color: 'orange' }}>
                            <PoweroffOutlined /> 关机
                        </a>
                    </Popconfirm>
                )}
                <Dropdown
                    menu={{
                        items: [
                            {
                                key: 'extract_template',
                                label: '提取为模板',
                                icon: <CopyOutlined />,
                                onClick: () => handleExtractTemplate(record.InstanceId)
                            },
                            {
                                key: 'reboot',
                                label: '重启实例',
                                disabled: !isRunning,
                                onClick: () => {
                                    modal.confirm({
                                        title: '确定要重启吗?',
                                        content: '重启过程中实例将无法访问。',
                                        onOk: () => handleAction(record.InstanceId, 'reboot')
                                    });
                                }
                            },
                            {
                                key: 'reset_pwd',
                                label: '重置密码',
                                onClick: () => {
                                    setCurrentInstance(record.InstanceId);
                                    setPasswordModalVisible(true);
                                }
                            },
                            {
                                key: 'delete',
                                label: '销毁/退还',
                                danger: true,
                                onClick: () => {
                                    modal.confirm({
                                        title: '确定要销毁/退还实例吗?',
                                        content: '此操作不可恢复，实例数据将丢失！',
                                        okType: 'danger',
                                        onOk: () => handleDelete(record.InstanceId)
                                    });
                                }
                            }
                        ]
                    }}
                >
                    <a onClick={e => e.preventDefault()}>
                        更多 <EllipsisOutlined />
                    </a>
                </Dropdown>
            </Space>
          );
      },
    },
  ];

  return (
    <PageContainer>
      {balance && (
        <ProCard gutter={16} ghost style={{ marginBottom: 16 }}>
            <ProCard colSpan={6} layout="center" bordered>
                <Statistic 
                    title="账户余额" 
                    value={balance.Balance} 
                    precision={2} 
                    suffix={balance.Currency} 
                    valueStyle={{ color: balance.Balance > 0 ? '#3f8600' : '#cf1322' }}
                />
            </ProCard>
            <ProCard colSpan={18} bordered>
                <div style={{display: 'flex', alignItems: 'center', height: '100%', color: '#666'}}>
                    <Space split="|">
                        <span>当前区域: {currentRegion}</span>
                        <span>实例总数: {actionRef.current?.pageInfo?.total || '-'}</span>
                    </Space>
                </div>
            </ProCard>
        </ProCard>
      )}

      <ProTable<TencentAPI.Instance>
        headerTitle="腾讯云 CVM 实例"
        actionRef={actionRef}
        rowKey="InstanceId"
        size="small"
        scroll={{ x: 1300, y: 'calc(100vh - 450px)' }}
        search={{
          labelWidth: 120,
        }}
        toolBarRender={() => [
          <Button
            type="primary"
            key="primary"
            onClick={() => {
              history.push('/tencent/create');
            }}
          >
            <PlusOutlined /> 新建实例
          </Button>,
        ]}
        request={async (params) => {
          if (!params.Region) return { data: [], success: true };
          setCurrentRegion(params.Region);
          try {
            const data = await getInstances(params.Region);
            return {
                data: data,
                success: true,
            };
          } catch (e) {
            handleError(e);
            return {
                data: [],
                success: false,
            };
          }
        }}
        columns={columns}
        pagination={{
            defaultPageSize: 20,
            showSizeChanger: true,
        }}
        rowSelection={{}}
        tableAlertOptionRender={({ selectedRowKeys, onCleanSelected, selectedRows }) => (
          <Space>
            <a
              onClick={() => {
                modal.confirm({
                  title: '确定要批量销毁/退还实例吗?',
                  content: `即将销毁 ${selectedRowKeys.length} 个实例，操作不可恢复！`,
                  okType: 'danger',
                  onOk: () => handleBatchDelete(selectedRowKeys),
                });
              }}
            >
              批量销毁
            </a>
            <a onClick={onCleanSelected}>取消选择</a>
          </Space>
        )}
      />

      <Modal
        title="重置实例密码"
        open={passwordModalVisible}
        onOk={handleResetPassword}
        onCancel={() => {
            setPasswordModalVisible(false);
            form.resetFields();
        }}
      >
        <Form form={form} layout="vertical">
            <Form.Item
                name="password"
                label="新密码"
                rules={[{ required: true, message: '请输入新密码' }, { min: 8, message: '密码至少8位' }]}
            >
                <Input.Password placeholder="请输入新密码" />
            </Form.Item>
        </Form>
      </Modal>
    </PageContainer>
  );
};

export default () => (
    <App>
        <Instances />
    </App>
);
