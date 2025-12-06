import { PageContainer, ProTable, ActionType } from '@ant-design/pro-components';
import { Button, Tag } from 'antd';
import { useRef } from 'react';
import { PlusOutlined } from '@ant-design/icons';
import { history, useIntl } from '@umijs/max';
import { getWorkflows } from '@/services/workflow/api';

export default () => {
  const actionRef = useRef<ActionType>();
  const intl = useIntl();

  const columns: any[] = [
    {
      title: intl.formatMessage({ id: 'workflow.field.id' }),
      dataIndex: 'id',
      width: 60,
      search: false,
    },
    {
      title: intl.formatMessage({ id: 'workflow.field.name' }),
      dataIndex: 'name',
      copyable: true,
    },
    {
      title: intl.formatMessage({ id: 'workflow.field.description' }),
      dataIndex: 'description',
      search: false,
      ellipsis: true,
    },
    {
      title: intl.formatMessage({ id: 'workflow.field.status' }),
      dataIndex: 'status',
      valueEnum: {
        pending: { text: intl.formatMessage({ id: 'workflow.status.pending' }), status: 'Default' },
        running: { text: intl.formatMessage({ id: 'workflow.status.running' }), status: 'Processing' },
        completed: { text: intl.formatMessage({ id: 'workflow.status.completed' }), status: 'Success' },
        failed: { text: intl.formatMessage({ id: 'workflow.status.failed' }), status: 'Error' },
        paused: { text: intl.formatMessage({ id: 'workflow.status.paused' }), status: 'Warning' },
      },
    },
    {
      title: intl.formatMessage({ id: 'workflow.field.currentStage' }),
      dataIndex: 'current_stage',
      search: false,
      render: (_: any, record: any) => <Tag color="blue">{record.current_stage}</Tag>
    },
    {
      title: intl.formatMessage({ id: 'workflow.field.createdAt' }),
      dataIndex: 'created_at',
      valueType: 'dateTime',
      search: false,
    },
    {
      title: intl.formatMessage({ id: 'workflow.field.updatedAt' }),
      dataIndex: 'updated_at',
      valueType: 'dateTime',
      search: false,
    },
    {
      title: intl.formatMessage({ id: 'pages.searchTable.titleOption' }),
      valueType: 'option',
      render: (_: any, record: any) => [
        <a
          key="detail"
          onClick={() => {
            history.push(`/workflow/execute/detail/${record.id}`);
          }}
        >
          {intl.formatMessage({ id: 'workflow.action.detail' })}
        </a>,
      ],
    },
  ];

  return (
    <PageContainer>
      <ProTable
        headerTitle={intl.formatMessage({ id: 'workflow.title.execute' })}
        actionRef={actionRef}
        rowKey="id"
        search={{
          labelWidth: 120,
        }}
        polling={3000} // Auto refresh every 3s for monitoring
        toolBarRender={() => [
          <Button
            type="primary"
            key="primary"
            onClick={() => {
              history.push('/workflow/execute/create');
            }}
          >
            <PlusOutlined /> {intl.formatMessage({ id: 'workflow.title.create' })}
          </Button>,
        ]}
        request={async (params) => {
          const data = await getWorkflows(params);
          return {
            data: data,
            success: true,
          };
        }}
        columns={columns}
      />
    </PageContainer>
  );
};
