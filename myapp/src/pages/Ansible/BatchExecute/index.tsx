import React, { useState, useEffect, useRef } from 'react';
import { PageContainer, ProCard } from '@ant-design/pro-components';
import { 
  Card, 
  Tabs, 
  Form, 
  Select, 
  Input, 
  Button, 
  Radio, 
  Transfer, 
  message, 
  Space, 
  Tag, 
  Modal,
  List,
  Progress,
  Alert,
  Typography,
  Row,
  Col
} from 'antd';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { ProTable } from '@ant-design/pro-components';
import { 
  getTemplates, 
  getHosts, 
  getGroups, 
  executePlaybookTask, 
  getTasks, 
  getTask 
} from '@/services/ansible/api';
import { 
  CheckCircleOutlined, 
  CloseCircleOutlined, 
  WarningOutlined, 
  ClockCircleOutlined, 
  SyncOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { useIntl, FormattedMessage } from '@umijs/max';

const { TextArea } = Input;
const { Text, Paragraph } = Typography;

const BatchExecute: React.FC = () => {
  const intl = useIntl();
  const [activeTab, setActiveTab] = useState('new');
  const actionRef = useRef<ActionType>();

  // Form states
  const [form] = Form.useForm();
  const [templates, setTemplates] = useState<AnsibleAPI.Template[]>([]);
  const [hosts, setHosts] = useState<AnsibleAPI.Host[]>([]);
  const [groups, setGroups] = useState<string[]>([]);
  const [targetType, setTargetType] = useState<'hosts' | 'group'>('hosts');
  const [selectedHosts, setSelectedHosts] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);

  // Task Detail Modal
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [currentTask, setCurrentTask] = useState<AnsibleAPI.Task | null>(null);
  const [pollingTimer, setPollingTimer] = useState<NodeJS.Timer | null>(null);

  useEffect(() => {
    loadData();
    return () => {
      if (pollingTimer) clearInterval(pollingTimer);
    };
  }, []);

  const loadData = async () => {
    try {
      const [tpls, hsts, grps] = await Promise.all([
        getTemplates(),
        getHosts(),
        getGroups()
      ]);
      setTemplates(tpls);
      setHosts(hsts);
      setGroups(grps);
    } catch (error) {
      message.error(intl.formatMessage({ id: 'ansible.batch.load_failed', defaultMessage: '加载基础数据失败' }));
    }
  };

  const handleTemplateChange = (value: number) => {
    const template = templates.find(t => t.id === value);
    if (template) {
      form.setFieldsValue({
        playbook: template.content,
        name: `Execute: ${template.name}`
      });
    }
  };

  const handleSubmit = async (values: any) => {
    if (!values.playbook) {
      message.error(intl.formatMessage({ id: 'ansible.batch.playbook_required', defaultMessage: 'Playbook内容不能为空' }));
      return;
    }

    if (targetType === 'hosts' && selectedHosts.length === 0) {
      message.error(intl.formatMessage({ id: 'ansible.batch.select_host_required', defaultMessage: '请选择至少一个主机' }));
      return;
    }

    setSubmitting(true);
    try {
      const payload: any = {
        playbook: values.playbook,
        name: values.name || 'Batch Execution',
      };

      if (targetType === 'hosts') {
        payload.host_ids = selectedHosts.map(id => parseInt(id));
      } else {
        payload.group_name = values.group;
      }

      const res = await executePlaybookTask(payload);
      message.success(intl.formatMessage({ id: 'ansible.batch.submit_success', defaultMessage: '任务已提交' }));
      form.resetFields();
      setSelectedHosts([]);
      setActiveTab('history');
      actionRef.current?.reload();
      
      // Open detail modal to track progress
      fetchTaskDetail(res.task_id);
      setDetailModalOpen(true);
      
    } catch (error: any) {
      message.error(error.message || intl.formatMessage({ id: 'ansible.batch.submit_failed', defaultMessage: '提交失败' }));
    } finally {
      setSubmitting(false);
    }
  };

  const fetchTaskDetail = async (taskId: number) => {
    try {
      const task = await getTask(taskId);
      setCurrentTask(task);
      
      if (task.status === 'running' || task.status === 'pending') {
        // Start polling if not already polling or if polling different task
        // Ideally we should manage polling better, but simple setInterval works for now
      }
    } catch (error) {
      console.error('Fetch task failed', error);
    }
  };

  // Poll for current task updates
  useEffect(() => {
    if (detailModalOpen && currentTask && (currentTask.status === 'pending' || currentTask.status === 'running')) {
      const timer = setInterval(() => {
        fetchTaskDetail(currentTask.id);
      }, 2000);
      return () => clearInterval(timer);
    }
  }, [detailModalOpen, currentTask?.status, currentTask?.id]);

  const columns: ProColumns<AnsibleAPI.Task>[] = [
    {
      title: intl.formatMessage({ id: 'ansible.batch.id', defaultMessage: 'ID' }),
      dataIndex: 'id',
      width: 80,
      search: false,
    },
    {
      title: intl.formatMessage({ id: 'ansible.batch.task_name', defaultMessage: '任务名称' }),
      dataIndex: 'name',
      copyable: true,
    },
    {
      title: intl.formatMessage({ id: 'ansible.batch.status', defaultMessage: '状态' }),
      dataIndex: 'status',
      valueEnum: {
        pending: { text: intl.formatMessage({ id: 'ansible.batch.status.pending', defaultMessage: '等待中' }), status: 'Default' },
        running: { text: intl.formatMessage({ id: 'ansible.batch.status.running', defaultMessage: '执行中' }), status: 'Processing' },
        completed: { text: intl.formatMessage({ id: 'ansible.batch.status.completed', defaultMessage: '已完成' }), status: 'Success' },
        failed: { text: intl.formatMessage({ id: 'ansible.batch.status.failed', defaultMessage: '失败' }), status: 'Error' },
      },
    },
    {
      title: intl.formatMessage({ id: 'ansible.batch.created_at', defaultMessage: '创建时间' }),
      dataIndex: 'created_at',
      valueType: 'dateTime',
      sorter: true,
      search: false,
    },
    {
      title: intl.formatMessage({ id: 'ansible.batch.actions', defaultMessage: '操作' }),
      valueType: 'option',
      render: (_, record) => [
        <a key="view" onClick={() => {
          fetchTaskDetail(record.id);
          setDetailModalOpen(true);
        }}>
          {intl.formatMessage({ id: 'ansible.batch.view_details', defaultMessage: '查看详情' })}
        </a>,
      ],
    },
  ];

  const renderTaskDetail = () => {
    if (!currentTask) return null;

    const result = currentTask.result;
    
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <Card size="small" title={intl.formatMessage({ id: 'ansible.batch.task_status', defaultMessage: '任务状态' })}>
           <Space size="large">
             <Tag color={
               currentTask.status === 'completed' ? 'success' :
               currentTask.status === 'failed' ? 'error' :
               currentTask.status === 'running' ? 'processing' : 'default'
             }>
               {currentTask.status.toUpperCase()}
             </Tag>
             <span>{intl.formatMessage({ id: 'ansible.batch.created_at', defaultMessage: '创建时间' })}: {currentTask.created_at}</span>
             {currentTask.completed_at && <span>{intl.formatMessage({ id: 'ansible.batch.completed_at', defaultMessage: '完成时间' })}: {currentTask.completed_at}</span>}
           </Space>
        </Card>

        {result && result.summary && (
          <Row gutter={16}>
             <Col span={8}>
               <Card size="small" bodyStyle={{ backgroundColor: '#f6ffed', textAlign: 'center' }}>
                 <CheckCircleOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                 <div style={{ fontSize: 20, fontWeight: 'bold' }}>{result.summary.success.length}</div>
                 <div>{intl.formatMessage({ id: 'ansible.batch.success', defaultMessage: '成功' })}</div>
               </Card>
             </Col>
             <Col span={8}>
               <Card size="small" bodyStyle={{ backgroundColor: '#fff1f0', textAlign: 'center' }}>
                 <CloseCircleOutlined style={{ fontSize: 24, color: '#ff4d4f' }} />
                 <div style={{ fontSize: 20, fontWeight: 'bold' }}>{result.summary.failed.length}</div>
                 <div>{intl.formatMessage({ id: 'ansible.batch.failed', defaultMessage: '失败' })}</div>
               </Card>
             </Col>
             <Col span={8}>
               <Card size="small" bodyStyle={{ backgroundColor: '#fffbe6', textAlign: 'center' }}>
                 <WarningOutlined style={{ fontSize: 24, color: '#faad14' }} />
                 <div style={{ fontSize: 20, fontWeight: 'bold' }}>{result.summary.unreachable.length}</div>
                 <div>{intl.formatMessage({ id: 'ansible.batch.unreachable', defaultMessage: '不可达' })}</div>
               </Card>
             </Col>
          </Row>
        )}

        {currentTask.logs && (
          <div>
            <Text strong>{intl.formatMessage({ id: 'ansible.batch.logs', defaultMessage: '执行日志' })}</Text>
            <div style={{ 
              backgroundColor: '#1e1e1e', 
              color: '#d4d4d4', 
              padding: '12px', 
              borderRadius: '4px', 
              fontFamily: 'monospace', 
              fontSize: '12px',
              height: '400px', 
              overflowY: 'auto',
              marginTop: '8px',
              whiteSpace: 'pre-wrap'
            }}>
              {currentTask.logs.join('\n')}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <PageContainer>
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <Tabs.TabPane tab={intl.formatMessage({ id: 'ansible.batch.new_task', defaultMessage: '新建任务' })} key="new">
            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
              initialValues={{ target_type: 'hosts' }}
            >
              <ProCard ghost gutter={24}>
                <ProCard colSpan={14} title="任务配置" bordered headerBordered>
                  <Form.Item name="name" label={intl.formatMessage({ id: 'ansible.batch.task_name', defaultMessage: '任务名称' })}>
                    <Input placeholder={intl.formatMessage({ id: 'ansible.batch.task_name_placeholder', defaultMessage: '请输入任务名称（可选）' })} />
                  </Form.Item>

                  <Form.Item label={intl.formatMessage({ id: 'ansible.batch.select_template', defaultMessage: '选择模板' })} name="template">
                    <Select 
                      placeholder={intl.formatMessage({ id: 'ansible.batch.select_template_placeholder', defaultMessage: '选择Playbook模板（可选）' })}
                      onChange={handleTemplateChange}
                      allowClear
                    >
                      {templates.map(t => (
                        <Select.Option key={t.id} value={t.id}>{t.name}</Select.Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Form.Item 
                    name="playbook" 
                    label={intl.formatMessage({ id: 'ansible.batch.playbook_content', defaultMessage: 'Playbook 内容' })}
                    rules={[{ required: true, message: intl.formatMessage({ id: 'ansible.batch.playbook_required', defaultMessage: 'Playbook内容不能为空' }) }]}
                  >
                    <TextArea rows={15} style={{ fontFamily: 'monospace' }} />
                  </Form.Item>
                </ProCard>

                <ProCard colSpan={10} title="执行目标" bordered headerBordered>
                  <Form.Item label={intl.formatMessage({ id: 'ansible.batch.target', defaultMessage: '执行目标' })}>
                    <Radio.Group 
                      value={targetType} 
                      onChange={e => setTargetType(e.target.value)}
                      style={{ marginBottom: 16 }}
                    >
                      <Radio.Button value="hosts">{intl.formatMessage({ id: 'ansible.batch.specific_hosts', defaultMessage: '指定主机' })}</Radio.Button>
                      <Radio.Button value="group">{intl.formatMessage({ id: 'ansible.batch.host_group', defaultMessage: '主机分组' })}</Radio.Button>
                    </Radio.Group>

                    {targetType === 'hosts' ? (
                      <Transfer
                        dataSource={hosts.map(h => ({
                          key: h.id.toString(),
                          title: `${h.address} (${h.comment})`,
                          description: h.username
                        }))}
                        titles={[
                          intl.formatMessage({ id: 'ansible.batch.available_hosts', defaultMessage: '可选' }),
                          intl.formatMessage({ id: 'ansible.batch.selected_hosts', defaultMessage: '已选' })
                        ]}
                        targetKeys={selectedHosts}
                        onChange={setSelectedHosts}
                        render={item => item.title}
                        listStyle={{ width: '45%', height: 400 }}
                      />
                    ) : (
                      <Form.Item name="group" rules={[{ required: true, message: intl.formatMessage({ id: 'ansible.batch.select_group_required', defaultMessage: '请选择主机分组' }) }]}>
                        <Select placeholder={intl.formatMessage({ id: 'ansible.batch.select_group_placeholder', defaultMessage: '选择主机分组' })}>
                          {groups.map(g => (
                            <Select.Option key={g} value={g}>{g}</Select.Option>
                          ))}
                        </Select>
                      </Form.Item>
                    )}
                  </Form.Item>

                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={submitting} size="large" block>
                      {intl.formatMessage({ id: 'ansible.batch.start_execution', defaultMessage: '开始执行' })}
                    </Button>
                  </Form.Item>
                </ProCard>
              </ProCard>
            </Form>
          </Tabs.TabPane>
          
          <Tabs.TabPane tab={intl.formatMessage({ id: 'ansible.batch.history', defaultMessage: '执行历史' })} key="history">
            <ProTable<AnsibleAPI.Task>
              actionRef={actionRef}
              columns={columns}
              size="small"
              scroll={{ x: 'max-content', y: 'calc(100vh - 400px)' }}
              request={async (params) => {
                const res = await getTasks({ limit: params.pageSize });
                return {
                  data: res,
                  success: true,
                  total: res.length // Note: Pagination is client-side for now based on limit
                };
              }}
              rowKey="id"
              pagination={{
                showQuickJumper: true,
              }}
              search={false}
              dateFormatter="string"
              headerTitle={intl.formatMessage({ id: 'ansible.batch.task_list', defaultMessage: '任务列表' })}
              toolBarRender={() => [
                <Button key="reload" icon={<ReloadOutlined />} onClick={() => actionRef.current?.reload()}>
                  {intl.formatMessage({ id: 'ansible.batch.reload', defaultMessage: '刷新' })}
                </Button>
              ]}
            />
          </Tabs.TabPane>
        </Tabs>
      </Card>

      <Modal
        title={`${intl.formatMessage({ id: 'ansible.batch.task_details', defaultMessage: '任务详情' })} #${currentTask?.id} - ${currentTask?.name}`}
        open={detailModalOpen}
        onCancel={() => setDetailModalOpen(false)}
        width={1000}
        footer={[
          <Button key="close" onClick={() => setDetailModalOpen(false)}>
            {intl.formatMessage({ id: 'ansible.batch.close', defaultMessage: '关闭' })}
          </Button>
        ]}
      >
        {renderTaskDetail()}
      </Modal>
    </PageContainer>
  );
};

export default BatchExecute;
