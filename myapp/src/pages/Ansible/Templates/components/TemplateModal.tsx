import React, { useEffect } from 'react';
import { ModalForm, ProFormText, ProFormTextArea } from '@ant-design/pro-components';
import { Form, message } from 'antd';
import { addTemplate, updateTemplate } from '@/services/ansible/api';
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
  const intl = useIntl();

  useEffect(() => {
    if (visible) {
      if (current) {
        let content: any = {};
        try {
            content = JSON.parse(current.content);
        } catch (e) {
            content = { playbook: current.content };
        }
        
        form.setFieldsValue({
            ...current,
            playbook: content.playbook || content.PlaybookContent
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
            version: '1.0',
        });
      }
    }
  }, [visible, current, form]);

  const handleSubmit = async (values: any) => {
    try {
      const payload = {
          name: values.name,
          description: values.description,
          content: values.playbook,
          type: 'ansible'
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
      width={600}
    >
      <ProFormText
        name="name"
        label={intl.formatMessage({ id: 'workflow.field.name' })}
        placeholder={intl.formatMessage({ id: 'workflow.field.name' })}
        rules={[{ required: true, message: intl.formatMessage({ id: 'workflow.message.required' }) }]}
      />
      <ProFormTextArea
        name="description"
        label={intl.formatMessage({ id: 'workflow.field.description' })}
      />
      <ProFormTextArea
        name="playbook"
        label={intl.formatMessage({ id: 'workflow.field.playbook' })}
        placeholder="YAML Content"
        fieldProps={{ rows: 15, style: { fontFamily: 'monospace' } }}
        rules={[{ required: true, message: intl.formatMessage({ id: 'workflow.message.required' }) }]}
      />
    </ModalForm>
  );
};

export default TemplateModal;
