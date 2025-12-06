import React, { useState } from 'react';
import { Modal, Form, Input, Button, Progress, Alert, message, Typography, List, Space, Tag } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, WarningOutlined } from '@ant-design/icons';
import { executePlaybook } from '@/services/ansible/api';

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

interface PlaybookExecutorProps {
  open: boolean;
  onCancel: () => void;
  targetHostIds: number[] | 'all';
  onExecutionComplete: () => void;
}

const defaultPlaybook = `--- 
# Ansible Playbook 示例
- name: 示例任务
  hosts: all
  tasks:
    - name: 执行一个简单的命令
      command: echo "Hello, Ansible!"
      register: hello_result
      
    - name: 显示命令结果
      debug:
        var: hello_result.stdout
`;

const PlaybookExecutor: React.FC<PlaybookExecutorProps> = ({ 
  open, 
  onCancel, 
  targetHostIds, 
  onExecutionComplete 
}) => {
  const [playbook, setPlaybook] = useState(defaultPlaybook);
  const [isExecuting, setIsExecuting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<AnsibleAPI.PlaybookResult | null>(null);

  const handleExecution = async () => {
    if (!playbook.trim()) {
      message.error('请输入Playbook内容');
      return;
    }

    setIsExecuting(true);
    setProgress(10);
    setResult(null);

    try {
      setProgress(30);
      const response = await executePlaybook({
        playbook: playbook.trim(),
        host_ids: targetHostIds === 'all' ? [] : targetHostIds,
      });
      
      setProgress(100);
      setResult(response);

      if (response.success) {
        const { success, failed, unreachable } = response.summary;
        if (failed.length === 0 && unreachable.length === 0) {
          message.success('Playbook执行成功');
        } else {
          message.warning(`Playbook部分成功: 成功 ${success.length}, 失败 ${failed.length}, 不可达 ${unreachable.length}`);
        }
        onExecutionComplete();
      } else {
        message.error(`Playbook执行失败, 返回代码: ${response.return_code}`);
      }
    } catch (error: any) {
      console.error('Playbook execution failed:', error);
      message.error(error.message || '执行失败');
    } finally {
      setIsExecuting(false);
    }
  };

  const handleClose = () => {
    if (isExecuting) return;
    setResult(null);
    setProgress(0);
    onCancel();
  };

  return (
    <Modal
      title="执行 Ansible Playbook"
      open={open}
      onCancel={handleClose}
      footer={[
        <Button key="cancel" onClick={handleClose} disabled={isExecuting}>
          {result ? '关闭' : '取消'}
        </Button>,
        !result && (
          <Button 
            key="execute" 
            type="primary" 
            onClick={handleExecution} 
            loading={isExecuting}
            disabled={!playbook.trim()}
          >
            执行Playbook
          </Button>
        ),
      ]}
      width={800}
      maskClosable={!isExecuting}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <Text strong>Playbook 内容 (YAML格式)</Text>
          <TextArea
            rows={12}
            value={playbook}
            onChange={(e) => setPlaybook(e.target.value)}
            style={{ fontFamily: 'monospace', marginTop: '8px' }}
            disabled={isExecuting}
          />
        </div>

        {isExecuting && <Progress percent={progress} status="active" />}

        {result && (
          <div style={{ marginTop: '16px', padding: '16px', background: '#f5f5f5', borderRadius: '8px' }}>
            <Alert
              message={result.success ? "执行成功" : "执行失败"}
              description={`返回代码: ${result.return_code}`}
              type={result.success ? "success" : "error"}
              showIcon
              style={{ marginBottom: '16px' }}
            />

            <Space direction="vertical" style={{ width: '100%' }}>
              {result.summary.success.length > 0 && (
                <div>
                  <Tag icon={<CheckCircleOutlined />} color="success">成功主机: {result.summary.success.length}</Tag>
                  <List
                    size="small"
                    dataSource={result.summary.success}
                    renderItem={item => <List.Item>{item}</List.Item>}
                    style={{ maxHeight: '100px', overflow: 'auto', marginTop: '8px', background: '#fff' }}
                  />
                </div>
              )}

              {result.summary.failed.length > 0 && (
                <div>
                  <Tag icon={<CloseCircleOutlined />} color="error">失败主机: {result.summary.failed.length}</Tag>
                  <List
                    size="small"
                    dataSource={result.summary.failed}
                    renderItem={item => <List.Item>{item}</List.Item>}
                    style={{ maxHeight: '100px', overflow: 'auto', marginTop: '8px', background: '#fff' }}
                  />
                </div>
              )}

              {result.summary.unreachable.length > 0 && (
                <div>
                  <Tag icon={<WarningOutlined />} color="warning">不可达主机: {result.summary.unreachable.length}</Tag>
                  <List
                    size="small"
                    dataSource={result.summary.unreachable}
                    renderItem={item => <List.Item>{item}</List.Item>}
                    style={{ maxHeight: '100px', overflow: 'auto', marginTop: '8px', background: '#fff' }}
                  />
                </div>
              )}
            </Space>

            <div style={{ marginTop: '16px' }}>
              <Text strong>详细日志</Text>
              <div style={{ 
                backgroundColor: '#000', 
                color: '#4ade80', 
                padding: '12px', 
                borderRadius: '4px', 
                fontFamily: 'monospace', 
                fontSize: '12px',
                height: '200px', 
                overflowY: 'auto',
                marginTop: '8px',
                whiteSpace: 'pre-wrap'
              }}>
                {result.logs.join('\n')}
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default PlaybookExecutor;
