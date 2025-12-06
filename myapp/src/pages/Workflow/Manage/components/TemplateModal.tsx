import React, { useEffect, useState } from 'react';
import { ModalForm, ProFormText, ProFormTextArea, ProFormDigit, ProFormSelect } from '@ant-design/pro-components';
import { Form, message, Tabs } from 'antd';
import { addTemplate, updateTemplate, getTemplates } from '@/services/ansible/api';
import { useIntl } from '@umijs/max';

export type TemplateModalProps = {
  visible: boolean;
  onVisibleChange: (visible: boolean) => void;
  current?: any;
  onFinish: () => void;
};

const TemplateModal: React.FC<TemplateModalProps> = (props) => {
  const { visible, onVisibleChange, current, onFinish } = props;
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('server');
  const [ansibleTemplates, setAnsibleTemplates] = useState<any[]>([]);
  const intl = useIntl();

  useEffect(() => {
    if (visible) {
      getTemplates('ansible').then(data => {
        setAnsibleTemplates(data.map(item => ({ label: item.name, value: item.id, content: item.content })));
      });

      if (current) {
        // Try to parse content if it's JSON
        let content = {};
        try {
            content = JSON.parse(current.content);
        } catch (e) {
            // Legacy content might be raw string
            content = { PlaybookContent: current.content };
        }
        
        form.setFieldsValue({
            ...current,
            ...content
        });
      } else {
        form.resetFields();
        // Default values
        form.setFieldsValue({
            version: '1.0',
            Region: 'ap-guangzhou',
            Zone: 'ap-guangzhou-3',
            InstanceType: 'S2.SMALL1',
            ImageId: 'img-8toqc6s3',
            InstanceChargeType: 'POSTPAID_BY_HOUR',
            SystemDiskSize: 50,
            SystemDiskType: 'CLOUD_PREMIUM',
            InternetAccessible: true,
            InternetMaxBandwidthOut: 1,
            InstanceCount: 1
        });
      }
    }
  }, [visible, current, form]);

  const handleSubmit = async (values: any) => {
    try {
      // Construct the content JSON
      const content = {
          // Server Config
          Region: values.Region,
          Zone: values.Zone,
          InstanceName: values.InstanceName, // Placeholder usually
          Password: values.Password, // Placeholder usually
          ImageId: values.ImageId,
          InstanceType: values.InstanceType,
          InstanceChargeType: values.InstanceChargeType,
          SystemDiskSize: values.SystemDiskSize,
          SystemDiskType: values.SystemDiskType,
          InternetAccessible: values.InternetAccessible,
          InternetMaxBandwidthOut: values.InternetMaxBandwidthOut,
          InstanceCount: values.InstanceCount,
          VpcId: values.VpcId,
          SubnetId: values.SubnetId,
          
          // Ansible Config
          PlaybookContent: values.PlaybookContent,
          
          // Dependencies
          Dependencies: values.Dependencies
      };

      const payload = {
          name: values.name,
          description: values.description,
          version: values.version,
          content: JSON.stringify(content, null, 2),
          type: 'workflow'
      };

      if (current) {
        await updateTemplate(current.id, payload);
        message.success(intl.formatMessage({ id: 'workflow.message.updateSuccess' }));
      } else {
        await addTemplate(payload);
        message.success(intl.formatMessage({ id: 'workflow.message.createSuccess' }));
      }
      onVisibleChange(false);
      onFinish();
    } catch (error) {
      console.error(error);
      message.error(intl.formatMessage({ id: 'workflow.message.operationFailed' }));
    }
  };

  return (
    <ModalForm
      title={current ? intl.formatMessage({ id: 'workflow.action.edit' }) : intl.formatMessage({ id: 'workflow.action.create' })}
      visible={visible}
      onVisibleChange={onVisibleChange}
      form={form}
      onFinish={handleSubmit}
      width={800}
      layout="horizontal"
    >
      <ProFormText
        name="name"
        label={intl.formatMessage({ id: 'workflow.field.name' })}
        placeholder={intl.formatMessage({ id: 'workflow.field.name' })}
        rules={[{ required: true, message: intl.formatMessage({ id: 'workflow.message.required' }) }]}
      />
      <ProFormText
        name="version"
        label={intl.formatMessage({ id: 'workflow.field.version' })}
        placeholder="1.0"
        width="xs"
      />
      <ProFormTextArea
        name="description"
        label={intl.formatMessage({ id: 'workflow.field.description' })}
        placeholder={intl.formatMessage({ id: 'workflow.field.description' })}
      />
      
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <Tabs.TabPane tab={intl.formatMessage({ id: 'workflow.tab.server' })} key="server">
              <ProFormText name="Region" label={intl.formatMessage({ id: 'workflow.field.region' })} width="md" />
              <ProFormText name="Zone" label={intl.formatMessage({ id: 'workflow.field.zone' })} width="md" />
              <ProFormText name="ImageId" label={intl.formatMessage({ id: 'workflow.field.imageId' })} width="md" />
              <ProFormText name="InstanceType" label={intl.formatMessage({ id: 'workflow.field.instanceType' })} width="md" />
              <ProFormText name="InstanceName" label={intl.formatMessage({ id: 'workflow.field.instanceName' })} width="md" />
              <ProFormText.Password name="Password" label={intl.formatMessage({ id: 'workflow.field.password' })} width="md" />
              <ProFormSelect 
                name="InstanceChargeType" 
                label={intl.formatMessage({ id: 'workflow.field.chargeType' })}
                valueEnum={{
                    PREPAID: intl.formatMessage({ id: 'workflow.field.chargeType.prepaid' }),
                    POSTPAID_BY_HOUR: intl.formatMessage({ id: 'workflow.field.chargeType.postpaid' })
                }}
                width="md"
              />
               <ProFormDigit name="SystemDiskSize" label={intl.formatMessage({ id: 'workflow.field.diskSize' })} width="sm" />
               <ProFormSelect 
                name="SystemDiskType" 
                label={intl.formatMessage({ id: 'workflow.field.diskType' })}
                valueEnum={{
                    CLOUD_PREMIUM: intl.formatMessage({ id: 'workflow.field.diskType.premium' }),
                    CLOUD_SSD: intl.formatMessage({ id: 'workflow.field.diskType.ssd' })
                }}
                width="md"
              />
          </Tabs.TabPane>
          
          <Tabs.TabPane tab={intl.formatMessage({ id: 'workflow.tab.ansible' })} key="ansible">
               <ProFormSelect
                 label={intl.formatMessage({ id: 'workflow.field.selectAnsibleTemplate' })}
                 options={ansibleTemplates}
                 placeholder={intl.formatMessage({ id: 'workflow.placeholder.selectAnsibleTemplate' })}
                 fieldProps={{
                     onChange: (value, option: any) => {
                         if (option && option.content) {
                             try {
                                 const content = JSON.parse(option.content);
                                 form.setFieldsValue({
                                     PlaybookContent: content.playbook || content.PlaybookContent
                                 });
                             } catch (e) {
                                 form.setFieldsValue({
                                     PlaybookContent: option.content
                                 });
                             }
                         }
                     }
                 }}
               />
               <ProFormTextArea
                name="PlaybookContent"
                label={intl.formatMessage({ id: 'workflow.field.playbook' })}
                placeholder="YAML Content"
                fieldProps={{ rows: 15, style: { fontFamily: 'monospace' } }}
              />
          </Tabs.TabPane>
          
          <Tabs.TabPane tab={intl.formatMessage({ id: 'workflow.tab.dependencies' })} key="dependencies">
               <ProFormTextArea
                name="Dependencies"
                label={intl.formatMessage({ id: 'workflow.field.dependencies' })}
                placeholder='["component-a", "component-b"]'
                fieldProps={{ rows: 5 }}
              />
              <div style={{ color: '#999', fontSize: '12px' }}>
                  {intl.formatMessage({ id: 'workflow.hint.dependencies' })}
              </div>
          </Tabs.TabPane>
      </Tabs>
      
    </ModalForm>
  );
};

export default TemplateModal;
