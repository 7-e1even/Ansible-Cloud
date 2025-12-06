import {
  PageContainer,
  StepsForm,
  ProFormText,
  ProFormTextArea,
  ProFormDigit,
  CheckCard,
  ProCard,
  ProFormGroup,
  ProFormSwitch,
  ProFormDependency,
} from '@ant-design/pro-components';
import { Form, message, Alert, Row, Col, Typography, Divider, Space, Tag, Descriptions } from 'antd';
import { useState, useEffect } from 'react';
import { history, useIntl, useSearchParams } from '@umijs/max';
import { getTemplates } from '@/services/ansible/api';
import { createWorkflow, batchCreateWorkflow } from '@/services/workflow/api';
import {
  RocketOutlined,
  CloudServerOutlined,
  DeploymentUnitOutlined,
  SettingOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CodeOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

export default () => {
  const intl = useIntl();
  const [templates, setTemplates] = useState<any[]>([]);
  const [ansibleTemplates, setAnsibleTemplates] = useState<any[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<any>(null);
  const [selectedAnsibleTemplate, setSelectedAnsibleTemplate] = useState<any>(null);
  const [searchParams] = useSearchParams();
  const [current, setCurrent] = useState(0);
  const [form] = Form.useForm();

  useEffect(() => {
    getTemplates('workflow').then((data) => {
      setTemplates(data);
      const templateId = searchParams.get('template_id');
      if (templateId) {
        const t = data.find((item: any) => item.id === Number(templateId));
        if (t) {
          setSelectedTemplate(t);
          setCurrent(1);
        }
      }
    });
    getTemplates('ansible').then((data) => {
        setAnsibleTemplates(data);
    });
  }, []);

  const handleFinish = async (values: any) => {
    try {
      if (!selectedTemplate) {
        message.error(intl.formatMessage({ id: 'workflow.message.selectTemplate' }));
        return false;
      }

      const params = { ...values };
      const count = params.count || 1;
      
      // Clean up top-level fields to isolate parameters
      const name = params.name;
      const description = params.description;
      
      delete params.name;
      delete params.description;
      delete params.count;

      // Parse JSON overrides if provided (if we had that field, currently removed for simplicity but logic kept if needed)
      // For now, params contains the dynamic form fields directly

      const commonParams = {
          ansible_template_id: selectedAnsibleTemplate?.id,
      };

      if (count > 1) {
        const instances = [];
        for (let i = 0; i < count; i++) {
          instances.push({
            ...params,
            name: `${name} - ${i + 1}`,
            description: description,
          });
        }
        await batchCreateWorkflow({
          template_id: selectedTemplate.id,
          ...commonParams,
          instances: instances,
        });
      } else {
        await createWorkflow({
          name: name,
          description: description,
          template_id: selectedTemplate.id,
          ...commonParams,
          params: params,
        });
      }

      message.success(intl.formatMessage({ id: 'workflow.message.createSuccess' }));
      history.push('/workflow/execute');
      return true;
    } catch (e: any) {
      message.error(`Create failed: ${e.message}`);
      return false;
    }
  };

  const parseTemplateContent = (content: string) => {
    try {
      return JSON.parse(content);
    } catch (e) {
      return {};
    }
  };

  const renderTemplateIcon = (type: string) => {
      // 简单的根据名称或描述判断图标，实际可以加到数据库字段
      return <CloudServerOutlined style={{ fontSize: 24, color: '#1890ff' }} />;
  };

  return (
    <PageContainer
      title={
        <Space>
          <RocketOutlined />
          <span>创建部署任务</span>
        </Space>
      }
      content="选择合适的模板，配置必要的参数，快速创建和执行自动化部署任务。"
    >
      <StepsForm
        form={form}
        current={current}
        onCurrentChange={setCurrent}
        onFinish={handleFinish}
        containerStyle={{ width: '100%', maxWidth: '100%' }}
        formProps={{
          validateMessages: {
            required: '${label} 是必填项',
          },
        }}
        submitter={{
          render: (props, dom) => {
            if (props.step === 3) {
              return (
                <div style={{ display: 'flex', justifyContent: 'center', gap: 16, marginTop: 24 }}>
                   {dom}
                </div>
              );
            }
            return dom;
          },
        }}
      >
        {/* 第一步：选择服务器模板 */}
        <StepsForm.StepForm
          name="template"
          title="选择服务器模板"
          icon={<DeploymentUnitOutlined />}
          style={{ width: '100%', maxWidth: '100%' }}
          onFinish={async () => {
            if (!selectedTemplate) {
              message.error('请选择一个服务器模板');
              return false;
            }
            return true;
          }}
        >
          <ProCard
            title="服务器模板"
            subTitle="定义服务器规格、镜像、网络等基础资源"
            headerBordered
            bordered
            style={{ minHeight: '40vh' }}
          >
            {templates.length === 0 ? (
               <div style={{ textAlign: 'center', padding: '40px' }}>
                 <Text type="secondary">暂无可用模板，请先在模板管理中添加。</Text>
               </div>
            ) : (
                <CheckCard.Group
                value={selectedTemplate?.id}
                onChange={(value) => {
                    const t = templates.find((item) => item.id === value);
                    setSelectedTemplate(t);
                }}
                style={{ width: '100%' }}
                >
                <Row gutter={[16, 16]}>
                    {templates.map((t) => (
                    <Col xs={24} sm={12} md={8} lg={6} key={t.id}>
                        <CheckCard
                        title={
                            <Space>
                                {renderTemplateIcon(t.name)}
                                <Text strong>{t.name}</Text>
                            </Space>
                        }
                        description={
                            <div style={{ marginTop: 8 }}>
                                <Paragraph ellipsis={{ rows: 2 }} type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
                                    {t.description || '暂无描述'}
                                </Paragraph>
                            </div>
                        }
                        value={t.id}
                        style={{ width: '100%', height: '100%' }}
                        />
                    </Col>
                    ))}
                </Row>
                </CheckCard.Group>
            )}
          </ProCard>
        </StepsForm.StepForm>

        {/* 第二步：选择脚本模板 */}
        <StepsForm.StepForm
          name="ansible_template"
          title="选择脚本模板"
          icon={<CodeOutlined />}
          style={{ width: '100%', maxWidth: '100%' }}
          onFinish={async () => {
            // 脚本模板是可选的，如果不选则仅创建服务器
            return true;
          }}
        >
          <ProCard
            title="Ansible 脚本模板 (可选)"
            subTitle="选择在服务器创建完成后执行的自动化脚本"
            headerBordered
            bordered
            style={{ minHeight: '40vh' }}
          >
             <Alert 
                message="说明" 
                description="如果选择了脚本模板，系统将在服务器创建成功并确认SSH可连接后，自动执行该Playbook。"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
             />
            {ansibleTemplates.length === 0 ? (
               <div style={{ textAlign: 'center', padding: '40px' }}>
                 <Text type="secondary">暂无可用脚本模板。</Text>
               </div>
            ) : (
                <CheckCard.Group
                value={selectedAnsibleTemplate?.id}
                onChange={(value) => {
                    const t = ansibleTemplates.find((item) => item.id === value);
                    setSelectedAnsibleTemplate(t);
                }}
                style={{ width: '100%' }}
                >
                <Row gutter={[16, 16]}>
                    {ansibleTemplates.map((t) => (
                    <Col xs={24} sm={12} md={8} lg={6} key={t.id}>
                        <CheckCard
                        title={
                            <Space>
                                <CodeOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                                <Text strong>{t.name}</Text>
                            </Space>
                        }
                        description={
                            <div style={{ marginTop: 8 }}>
                                <Paragraph ellipsis={{ rows: 2 }} type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
                                    {t.description || '暂无描述'}
                                </Paragraph>
                            </div>
                        }
                        value={t.id}
                        style={{ width: '100%', height: '100%' }}
                        />
                    </Col>
                    ))}
                </Row>
                </CheckCard.Group>
            )}
          </ProCard>
        </StepsForm.StepForm>

        {/* 第三步：配置参数 */}
        <StepsForm.StepForm 
            name="config" 
            title="配置参数" 
            icon={<SettingOutlined />}
            style={{ width: '100%', maxWidth: '100%' }}
        >
          <Row gutter={24}>
            <Col xs={24} lg={16}>
                <ProCard 
                    title="基础配置" 
                    bordered 
                    headerBordered 
                    style={{ marginBottom: 24 }}
                >
                    <ProFormGroup>
                        <ProFormText
                            name="name"
                            label="任务名称"
                            width="md"
                            placeholder="请输入任务名称"
                            rules={[{ required: true }]}
                            fieldProps={{
                                prefix: <RocketOutlined />
                            }}
                        />
                        <ProFormDigit
                            name="count"
                            label="批量数量"
                            width="xs"
                            min={1}
                            max={50}
                            initialValue={1}
                            tooltip="设置为大于1时将批量创建任务"
                        />
                    </ProFormGroup>
                    <ProFormTextArea
                        name="description"
                        label="任务描述"
                        placeholder="请输入任务描述信息（可选）"
                        fieldProps={{
                            rows: 3
                        }}
                    />
                </ProCard>

                <ProCard 
                    title="实例参数" 
                    tooltip="根据所选服务器模板定义的动态参数"
                    bordered 
                    headerBordered
                >
                    {selectedTemplate ? (() => {
                        const content = parseTemplateContent(selectedTemplate.content);
                        return (
                            <>
                                <Alert 
                                    message="参数说明" 
                                    description="以下参数由模板定义，请根据实际需求进行调整。部分参数可能为只读。" 
                                    type="info" 
                                    showIcon 
                                    style={{ marginBottom: 24 }}
                                />
                                <Row gutter={24}>
                                    <Col span={12}>
                                        <ProFormText
                                            name="InstanceName"
                                            label="实例名称前缀"
                                            initialValue={content.InstanceName}
                                            rules={[{ required: true }]}
                                            tooltip="生成的实例名称将以此为前缀"
                                        />
                                    </Col>
                                    <Col span={12}>
                                        <ProFormText.Password
                                            name="Password"
                                            label="登录密码"
                                            initialValue={content.Password}
                                            rules={[{ required: true, min: 8 }]}
                                            tooltip="云服务器的初始登录密码"
                                        />
                                    </Col>
                                    <Col span={12}>
                                        <ProFormText
                                            name="Region"
                                            label="地域 (Region)"
                                            initialValue={content.Region}
                                            disabled
                                            addonAfter={<Tag color="blue">固定</Tag>}
                                        />
                                    </Col>
                                    <Col span={12}>
                                        <ProFormText
                                            name="Zone"
                                            label="可用区 (Zone)"
                                            initialValue={content.Zone}
                                            disabled
                                            addonAfter={<Tag color="blue">固定</Tag>}
                                        />
                                    </Col>
                                    <Col span={12}>
                                        <ProFormText
                                            name="InstanceType"
                                            label="实例类型"
                                            initialValue={content.InstanceType}
                                            disabled
                                            addonAfter={<Tag color="purple">配置</Tag>}
                                        />
                                    </Col>
                                    <Col span={12}>
                                        <ProFormText
                                            name="ImageId"
                                            label="镜像 ID"
                                            initialValue={content.ImageId}
                                            disabled
                                            addonAfter={<Tag color="cyan">系统</Tag>}
                                        />
                                    </Col>
                                    <Col span={12}>
                                        <ProFormSwitch
                                            name="InternetAccessible"
                                            label="分配公网 IP"
                                            initialValue={content.InternetAccessible}
                                        />
                                    </Col>
                                    <Col span={12}>
                                        <ProFormDependency name={['InternetAccessible']}>
                                            {({ InternetAccessible }) => {
                                                return (
                                                    <ProFormDigit
                                                        name="InternetMaxBandwidthOut"
                                                        label="公网带宽 (Mbps)"
                                                        initialValue={content.InternetMaxBandwidthOut || 1}
                                                        min={1}
                                                        max={100}
                                                        disabled={!InternetAccessible}
                                                    />
                                                );
                                            }}
                                        </ProFormDependency>
                                    </Col>
                                </Row>
                            </>
                        );
                    })() : (
                        <div style={{ padding: 24, textAlign: 'center' }}>
                            <Text type="secondary">请先选择模板</Text>
                        </div>
                    )}
                </ProCard>
            </Col>
            
            <Col xs={24} lg={8}>
                <ProCard title="模板信息" bordered headerBordered>
                     <Descriptions column={1} size="small" title="服务器模板">
                        {selectedTemplate ? (
                            <>
                                <Descriptions.Item label="名称">{selectedTemplate.name}</Descriptions.Item>
                                <Descriptions.Item label="描述">{selectedTemplate.description}</Descriptions.Item>
                            </>
                        ) : (
                            <Descriptions.Item label="状态"><Text type="secondary">未选择</Text></Descriptions.Item>
                        )}
                     </Descriptions>
                     <Divider style={{ margin: '12px 0' }} />
                     <Descriptions column={1} size="small" title="脚本模板">
                        {selectedAnsibleTemplate ? (
                            <>
                                <Descriptions.Item label="名称">{selectedAnsibleTemplate.name}</Descriptions.Item>
                                <Descriptions.Item label="描述">{selectedAnsibleTemplate.description}</Descriptions.Item>
                            </>
                        ) : (
                            <Descriptions.Item label="状态"><Text type="secondary">未选择</Text></Descriptions.Item>
                        )}
                     </Descriptions>
                </ProCard>
            </Col>
          </Row>
        </StepsForm.StepForm>

        {/* 第四步：确认信息 */}
        <StepsForm.StepForm 
            name="confirm" 
            title="确认信息" 
            icon={<CheckCircleOutlined />}
            style={{ width: '100%', maxWidth: '100%' }}
        >
             <ProCard>
                <div style={{ maxWidth: 600, margin: '0 auto' }}>
                    <Alert
                        message="确认提交"
                        description="请仔细核对以下信息，提交后将开始执行部署任务。"
                        type="warning"
                        showIcon
                        style={{ marginBottom: 24 }}
                    />
                    <Descriptions title="任务概览" bordered column={1}>
                        <Descriptions.Item label="任务名称">
                            {form.getFieldValue('name')}
                        </Descriptions.Item>
                        <Descriptions.Item label="服务器模板">
                            {selectedTemplate?.name}
                        </Descriptions.Item>
                         <Descriptions.Item label="脚本模板">
                            {selectedAnsibleTemplate ? (
                                <Tag color="green">{selectedAnsibleTemplate.name}</Tag>
                            ) : (
                                <Text type="secondary">未选择 (仅创建服务器)</Text>
                            )}
                        </Descriptions.Item>
                        <Descriptions.Item label="创建数量">
                             <Tag color="geekblue">{form.getFieldValue('count') || 1} 个</Tag>
                        </Descriptions.Item>
                         <Descriptions.Item label="描述">
                            {form.getFieldValue('description') || '-'}
                        </Descriptions.Item>
                    </Descriptions>
                </div>
            </ProCard>
        </StepsForm.StepForm>
      </StepsForm>
    </PageContainer>
  );
};
