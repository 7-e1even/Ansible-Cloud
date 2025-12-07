import React, { useRef, useState } from 'react';
import { PageContainer, ProTable, ActionType, ProColumns, ModalForm, ProFormText, ProFormSelect, ProFormRadio, ProFormInstance } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Tag, Space } from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined, ApiOutlined } from '@ant-design/icons';
import { getCredentials, createCredential, updateCredential, deleteCredential, testCredential, CloudAPI } from '@/services/cloud/api';

const CloudKeys: React.FC = () => {
  const actionRef = useRef<ActionType>();
  const formRef = useRef<ProFormInstance>();
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [updateModalVisible, setUpdateModalVisible] = useState(false);
  const [currentRow, setCurrentRow] = useState<CloudAPI.Credential>();
  const [testing, setTesting] = useState(false);

  const handleTestConnection = async () => {
      const values = formRef.current?.getFieldsValue();
      if (!values.provider || !values.access_key || !values.secret_key) {
          message.error("Please fill in Provider, Access Key and Secret Key to test.");
          return;
      }
      
      setTesting(true);
      try {
          const res = await testCredential({
              provider: values.provider,
              access_key: values.access_key,
              secret_key: values.secret_key
          });
          if (res.success) {
              message.success(res.message);
          } else {
              message.error(res.message);
          }
      } catch (e) {
          message.error("Test failed");
      } finally {
          setTesting(false);
      }
  };

  const columns: ProColumns<CloudAPI.Credential>[] = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 48,
      hideInForm: true,
      search: false,
    },
    {
      title: 'Config Name',
      dataIndex: 'name',
    },
    {
      title: 'Provider',
      dataIndex: 'provider',
      valueEnum: {
        tencent: { text: 'Tencent Cloud', status: 'Success' },
        aliyun: { text: 'Aliyun', status: 'Processing' },
        aws: { text: 'AWS', status: 'Warning' },
      },
    },
    {
      title: 'Access Key',
      dataIndex: 'access_key',
      copyable: true,
    },
    {
      title: 'Default',
      dataIndex: 'is_default',
      render: (_, record) => (
        record.is_default ? <Tag color="green">Default</Tag> : <Tag>No</Tag>
      ),
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      hideInForm: true,
      search: false,
    },
    {
      title: 'Actions',
      valueType: 'option',
      render: (_, record) => [
        <a
          key="edit"
          onClick={() => {
            setCurrentRow(record);
            setUpdateModalVisible(true);
          }}
        >
          Edit
        </a>,
        <Popconfirm
          key="delete"
          title="Are you sure to delete this configuration?"
          onConfirm={async () => {
            try {
              await deleteCredential(record.id);
              message.success('Deleted successfully');
              actionRef.current?.reload();
            } catch (error) {
              message.error('Delete failed');
            }
          }}
        >
          <a style={{ color: 'red' }}>Delete</a>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <PageContainer>
      <ProTable<CloudAPI.Credential>
        headerTitle="Cloud Access Keys"
        actionRef={actionRef}
        rowKey="id"
        search={false}
        toolBarRender={() => [
          <Button
            type="primary"
            key="primary"
            onClick={() => {
              setCurrentRow(undefined);
              setCreateModalVisible(true);
            }}
          >
            <PlusOutlined /> New Config
          </Button>,
        ]}
        request={async (params) => {
            const result = await getCredentials();
            return {
                data: result,
                success: true,
            };
        }}
        columns={columns}
      />

      <ModalForm
        title={currentRow ? "Edit Configuration" : "New Configuration"}
        width="500px"
        formRef={formRef}
        visible={createModalVisible || updateModalVisible}
        onVisibleChange={(visible) => {
            if (!visible) {
                setCreateModalVisible(false);
                setUpdateModalVisible(false);
                setCurrentRow(undefined);
            }
        }}
        initialValues={currentRow}
        modalProps={{
            destroyOnClose: true,
        }}
        onFinish={async (values) => {
            try {
                if (currentRow) {
                    await updateCredential(currentRow.id, values);
                    message.success('Updated successfully');
                } else {
                    await createCredential(values as CloudAPI.CreateCredentialParams);
                    message.success('Created successfully');
                }
                setCreateModalVisible(false);
                setUpdateModalVisible(false);
                actionRef.current?.reload();
                return true;
            } catch (error) {
                message.error('Operation failed');
                return false;
            }
        }}
        submitter={{
            render: (props, defaultDoms) => {
                return [
                    <Button key="test" icon={<ApiOutlined />} loading={testing} onClick={handleTestConnection}>
                        Test Connection
                    </Button>,
                    ...defaultDoms
                ];
            }
        }}
      >
        <ProFormText
          name="name"
          label="Configuration Name"
          placeholder="e.g. Production Tencent Cloud"
          rules={[{ required: true, message: 'Please enter a name' }]}
        />
        <ProFormSelect
          name="provider"
          label="Provider"
          valueEnum={{
            tencent: 'Tencent Cloud',
            aliyun: 'Aliyun',
            aws: 'AWS',
          }}
          placeholder="Select Provider"
          rules={[{ required: true, message: 'Please select a provider' }]}
        />
        <ProFormText
          name="access_key"
          label="Access Key ID"
          placeholder="Enter Access Key"
          rules={[{ required: true, message: 'Please enter Access Key' }]}
        />
        <ProFormText.Password
          name="secret_key"
          label="Secret Access Key"
          placeholder={currentRow ? "Leave empty to keep unchanged" : "Enter Secret Key"}
          rules={[{ required: !currentRow, message: 'Please enter Secret Key' }]}
        />
        <ProFormRadio.Group
            name="is_default"
            label="Set as Default"
            options={[
                { label: 'Yes', value: true },
                { label: 'No', value: false },
            ]}
            initialValue={false}
        />
      </ModalForm>
    </PageContainer>
  );
};

export default CloudKeys;
