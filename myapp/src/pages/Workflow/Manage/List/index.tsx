import React, { useRef, useState } from 'react';
import { PageContainer, ProTable, ActionType, ProColumns } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Tag } from 'antd';
import { PlusOutlined, RocketOutlined } from '@ant-design/icons';
import { getTemplates, deleteTemplate } from '@/services/ansible/api';
import TemplateModal from '../components/TemplateModal';
import { useIntl, history } from '@umijs/max';

const TemplateList: React.FC = () => {
  const intl = useIntl();
  const actionRef = useRef<ActionType>();
  const [modalVisible, setModalVisible] = useState<boolean>(false);
  const [currentRow, setCurrentRow] = useState<any>(undefined);

  const handleDelete = async (id: number) => {
    try {
      await deleteTemplate(id, 'workflow');
      message.success(intl.formatMessage({ id: 'workflow.message.deleteSuccess' }));
      actionRef.current?.reload();
    } catch (error) {
      message.error('Delete failed');
    }
  };

  const columns: ProColumns<any>[] = [
    {
      title: intl.formatMessage({ id: 'workflow.field.id' }),
      dataIndex: 'id',
      width: 60,
      search: false,
    },
    {
      title: intl.formatMessage({ id: 'workflow.field.name' }),
      dataIndex: 'name',
    },
    {
        title: intl.formatMessage({ id: 'workflow.field.version' }),
        dataIndex: 'version',
        width: 80,
        render: (text) => <Tag>{text || '1.0'}</Tag>
    },
    {
      title: intl.formatMessage({ id: 'workflow.field.description' }),
      dataIndex: 'description',
      search: false,
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
      title: intl.formatMessage({ id: 'pages.searchTable.titleOption' }), // 'Option'
      valueType: 'option',
      render: (_, record) => [
        <a
          key="deploy"
          onClick={() => {
            history.push(`/workflow/execute/create?template_id=${record.id}`);
          }}
        >
          <RocketOutlined /> {intl.formatMessage({ id: 'workflow.action.deploy' })}
        </a>,
        <a
          key="edit"
          onClick={() => {
            setCurrentRow(record);
            setModalVisible(true);
          }}
        >
          {intl.formatMessage({ id: 'workflow.action.edit' })}
        </a>,
        <Popconfirm
          key="delete"
          title={intl.formatMessage({ id: 'workflow.message.deleteConfirm' })}
          onConfirm={() => handleDelete(record.id)}
        >
          <a style={{ color: 'red' }}>{intl.formatMessage({ id: 'workflow.action.delete' })}</a>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <PageContainer>
      <ProTable<any>
        headerTitle={intl.formatMessage({ id: 'workflow.title.manage' })}
        actionRef={actionRef}
        rowKey="id"
        search={false}
        toolBarRender={() => [
          <Button
            type="primary"
            key="primary"
            onClick={() => {
              setCurrentRow(undefined);
              setModalVisible(true);
            }}
          >
            <PlusOutlined /> {intl.formatMessage({ id: 'workflow.action.create' })}
          </Button>,
        ]}
        request={async () => {
          const data = await getTemplates('workflow');
          return {
            data: data,
            success: true,
          };
        }}
        columns={columns}
      />
      <TemplateModal
        visible={modalVisible}
        onVisibleChange={setModalVisible}
        current={currentRow}
        onFinish={() => actionRef.current?.reload()}
      />
    </PageContainer>
  );
};

export default TemplateList;
