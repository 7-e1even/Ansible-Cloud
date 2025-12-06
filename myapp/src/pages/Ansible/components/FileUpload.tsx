import React, { useState } from 'react';
import { Modal, Upload, Button, message, Form, Input } from 'antd';
import { UploadOutlined, InboxOutlined } from '@ant-design/icons';
import { uploadFile } from '@/services/ansible/api';
import type { UploadFile, UploadProps } from 'antd/es/upload/interface';

const { Dragger } = Upload;

interface FileUploadProps {
  open: boolean;
  onCancel: () => void;
  targetHostIds: number[] | 'all';
  onUploadComplete: () => void;
}

const FileUpload: React.FC<FileUploadProps> = ({
  open,
  onCancel,
  targetHostIds,
  onUploadComplete
}) => {
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [form] = Form.useForm();

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请选择要上传的文件');
      return;
    }

    try {
      const values = await form.validateFields();
      const file = fileList[0];
      
      const formData = new FormData();
      formData.append('file', file.originFileObj as File);
      formData.append('target_path', values.targetPath);
      formData.append('host_ids', targetHostIds === 'all' ? 'all' : JSON.stringify(targetHostIds));

      setUploading(true);

      const response = await uploadFile(formData);
      
      if (response.success) {
        message.success('文件分发成功');
        onUploadComplete();
        handleClose();
      } else {
        message.error(`分发失败: ${response.message}`);
      }
    } catch (error: any) {
      console.error('Upload failed:', error);
      message.error(error.message || '上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    setFileList([]);
    form.resetFields();
    onCancel();
  };

  const uploadProps: UploadProps = {
    onRemove: (file) => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
    beforeUpload: (file) => {
      setFileList([file]); // 只允许单文件
      return false; // 阻止自动上传
    },
    fileList,
  };

  return (
    <Modal
      title="分发文件到主机"
      open={open}
      onCancel={handleClose}
      footer={[
        <Button key="cancel" onClick={handleClose}>
          取消
        </Button>,
        <Button
          key="upload"
          type="primary"
          onClick={handleUpload}
          loading={uploading}
          disabled={fileList.length === 0}
        >
          {uploading ? '分发中...' : '开始分发'}
        </Button>,
      ]}
    >
      <Form form={form} layout="vertical" initialValues={{ targetPath: '/tmp/' }}>
        <Form.Item
          name="targetPath"
          label="目标路径"
          rules={[{ required: true, message: '请输入目标路径' }]}
          help="文件将被上传到远程主机的该路径下"
        >
          <Input placeholder="/tmp/" />
        </Form.Item>

        <Form.Item label="选择文件" required>
          <Dragger {...uploadProps}>
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
            <p className="ant-upload-hint">
              支持单个文件上传。文件将被分发到选中的主机。
            </p>
          </Dragger>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default FileUpload;
