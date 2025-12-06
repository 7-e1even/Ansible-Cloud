import { PageContainer, ProCard, ProDescriptions } from '@ant-design/pro-components';
import { Steps, Timeline, Tag, Spin, Result, Button } from 'antd';
import { useState, useEffect } from 'react';
import { useParams, history, useIntl } from '@umijs/max';
import { getWorkflow, getWorkflowLogs } from '@/services/workflow/api';

export default () => {
  const params = useParams();
  const id = Number(params.id);
  const [workflow, setWorkflow] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const intl = useIntl();

  const fetchData = async () => {
    try {
      const w = await getWorkflow(id);
      const l = await getWorkflowLogs(id);
      setWorkflow(w);
      setLogs(l);
      setLoading(false);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000); // Poll every 3 seconds
    return () => clearInterval(interval);
  }, [id]);

  if (loading && !workflow) {
      return <PageContainer><Spin /></PageContainer>;
  }

  if (!workflow) {
      return (
          <PageContainer>
              <Result
                status="404"
                title="Workflow Not Found"
                subTitle="Sorry, the workflow you visited does not exist."
                extra={<Button type="primary" onClick={() => history.push('/workflow/execute')}>{intl.formatMessage({ id: 'workflow.title.execute' })}</Button>}
              />
          </PageContainer>
      );
  }

  const getStepStatus = (stepStage: string, currentStage: string, workflowStatus: string) => {
      const stages = ['validation', 'resource_creation', 'wait_for_ready', 'ansible_deployment', 'completed'];
      const currentIndex = stages.indexOf(currentStage);
      const stepIndex = stages.indexOf(stepStage);

      if (workflowStatus === 'failed' && currentStage === stepStage) return 'error';
      if (stepIndex < currentIndex) return 'finish';
      if (stepIndex === currentIndex) {
          return workflowStatus === 'running' ? 'process' : (workflowStatus === 'completed' ? 'finish' : 'wait');
      }
      return 'wait';
  };

  return (
    <PageContainer
        header={{
            title: `${intl.formatMessage({ id: 'workflow.field.name' })}: ${workflow.name}`,
            subTitle: <Tag color={workflow.status === 'completed' ? 'green' : (workflow.status === 'failed' ? 'red' : 'blue')}>{workflow.status}</Tag>,
            extra: [
                <Button key="back" onClick={() => history.push('/workflow/execute')}>{intl.formatMessage({ id: 'workflow.title.execute' })}</Button>
            ]
        }}
    >
      <ProCard direction="column" ghost gutter={[0, 16]}>
        <ProCard title={intl.formatMessage({ id: 'workflow.section.progress' })}>
          <Steps
            current={['validation', 'resource_creation', 'wait_for_ready', 'ansible_deployment', 'completed'].indexOf(workflow.current_stage)}
            items={[
                { title: intl.formatMessage({ id: 'workflow.step.validation' }), status: getStepStatus('validation', workflow.current_stage, workflow.status) },
                { title: intl.formatMessage({ id: 'workflow.step.resource_creation' }), status: getStepStatus('resource_creation', workflow.current_stage, workflow.status) },
                { title: intl.formatMessage({ id: 'workflow.step.wait_for_ready' }), status: getStepStatus('wait_for_ready', workflow.current_stage, workflow.status) },
                { title: intl.formatMessage({ id: 'workflow.step.ansible_deployment' }), status: getStepStatus('ansible_deployment', workflow.current_stage, workflow.status) },
                { title: intl.formatMessage({ id: 'workflow.step.completed' }), status: getStepStatus('completed', workflow.current_stage, workflow.status) },
            ]}
          />
        </ProCard>

        <ProCard gutter={16} ghost>
            <ProCard title={intl.formatMessage({ id: 'workflow.section.basicInfo' })} colSpan={12}>
                <ProDescriptions column={1} dataSource={workflow}>
                    <ProDescriptions.Item label={intl.formatMessage({ id: 'workflow.field.id' })} dataIndex="id" />
                    <ProDescriptions.Item label={intl.formatMessage({ id: 'workflow.field.name' })} dataIndex="name" />
                    <ProDescriptions.Item label={intl.formatMessage({ id: 'workflow.field.description' })} dataIndex="description" />
                    <ProDescriptions.Item label={intl.formatMessage({ id: 'workflow.field.createdAt' })} dataIndex="created_at" valueType="dateTime" />
                    <ProDescriptions.Item label={intl.formatMessage({ id: 'workflow.field.updatedAt' })} dataIndex="updated_at" valueType="dateTime" />
                </ProDescriptions>
            </ProCard>
            <ProCard title={intl.formatMessage({ id: 'workflow.section.context' })} colSpan={12}>
                <pre style={{ maxHeight: 300, overflow: 'auto', background: '#f5f5f5', padding: 10, borderRadius: 4 }}>
                    {JSON.stringify(JSON.parse(workflow.context || '{}'), null, 2)}
                </pre>
            </ProCard>
        </ProCard>

        <ProCard title={intl.formatMessage({ id: 'workflow.section.logs' })}>
            <Timeline mode="left">
                {logs.map(log => (
                    <Timeline.Item 
                        key={log.id} 
                        color={log.status === 'success' ? 'green' : (log.status === 'failed' ? 'red' : 'blue')}
                        label={log.timestamp}
                    >
                        <p><strong>{log.stage}</strong>: {log.message}</p>
                    </Timeline.Item>
                ))}
            </Timeline>
        </ProCard>
      </ProCard>
    </PageContainer>
  );
};
