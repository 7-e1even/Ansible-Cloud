import React, { useEffect, useState } from 'react';
import { PageContainer, ProCard, StatisticCard } from '@ant-design/pro-components';
import { theme, Row, Col, Progress, List, Tag, Typography } from 'antd';
import { 
  DesktopOutlined, 
  CheckCircleOutlined, 
  SyncOutlined, 
  ExclamationCircleOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CodeOutlined
} from '@ant-design/icons';
import { getHosts, checkAllHostsStatus } from '@/services/ansible/api';

const { Statistic } = StatisticCard;
const { Paragraph, Title } = Typography;

const Welcome: React.FC = () => {
  const { token } = theme.useToken();
  const [hostStats, setHostStats] = useState({
    total: 0,
    online: 0,
    offline: 0,
    loading: true
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const res = await getHosts({ current: 1, pageSize: 1000 });
      const hosts = res.data || [];
      const total = hosts.length;
      // 简单模拟在线状态统计，实际应从API获取
      // 这里假设 status 为 'success' 或 'active' 的是在线
      const online = hosts.filter((h: any) => h.status === 'success' || h.status === 'active').length;
      
      setHostStats({
        total,
        online,
        offline: total - online,
        loading: false
      });
    } catch (e) {
      console.error(e);
      setHostStats(s => ({ ...s, loading: false }));
    }
  };

  return (
    <PageContainer
      content={
        <div style={{ marginBottom: 24 }}>
          <Title level={4}>欢迎回来，管理员</Title>
          <Paragraph type="secondary">
            这里是 Ansible 自动化运维平台的概览面板。您可以快速查看主机状态、执行任务并监控系统运行情况。
          </Paragraph>
        </div>
      }
    >
      <Row gutter={[24, 24]}>
        {/* 顶部统计卡片 */}
        <Col span={24}>
          <ProCard gutter={24} ghost>
            <ProCard colSpan={6} layout="center" bordered>
              <StatisticCard
                statistic={{
                  title: '总主机数',
                  value: hostStats.total,
                  icon: <DesktopOutlined style={{ fontSize: 24, color: token.colorPrimary }} />,
                }}
              />
            </ProCard>
            <ProCard colSpan={6} layout="center" bordered>
              <StatisticCard
                statistic={{
                  title: '在线主机',
                  value: hostStats.online,
                  status: 'success',
                  icon: <CheckCircleOutlined style={{ fontSize: 24, color: token.colorSuccess }} />,
                }}
              />
            </ProCard>
            <ProCard colSpan={6} layout="center" bordered>
              <StatisticCard
                statistic={{
                  title: '异常主机',
                  value: hostStats.offline,
                  status: 'error',
                  icon: <ExclamationCircleOutlined style={{ fontSize: 24, color: token.colorError }} />,
                }}
              />
            </ProCard>
            <ProCard colSpan={6} layout="center" bordered>
              <StatisticCard
                statistic={{
                  title: '系统负载',
                  value: '12%',
                  icon: <ThunderboltOutlined style={{ fontSize: 24, color: token.colorWarning }} />,
                  description: <Statistic title="较昨日" value="5%" trend="down" />,
                }}
              />
            </ProCard>
          </ProCard>
        </Col>

        {/* 主要内容区域 */}
        <Col span={16}>
          <ProCard title="主机健康度分布" bordered headerBordered>
             <div style={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Row style={{ width: '100%' }} gutter={48}>
                  <Col span={12} style={{ textAlign: 'center' }}>
                     <Progress type="dashboard" percent={hostStats.total > 0 ? Math.round((hostStats.online / hostStats.total) * 100) : 0} width={180} />
                     <div style={{ marginTop: 16 }}>在线率</div>
                  </Col>
                  <Col span={12}>
                    <List
                      size="small"
                      dataSource={[
                        { title: 'SSH 连接正常', count: hostStats.online, color: 'green' },
                        { title: '连接失败', count: hostStats.offline, color: 'red' },
                        { title: '未扫描', count: 0, color: 'gray' },
                      ]}
                      renderItem={item => (
                        <List.Item>
                          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                            <span><Tag color={item.color}>{item.title}</Tag></span>
                            <span>{item.count}</span>
                          </div>
                        </List.Item>
                      )}
                    />
                  </Col>
                </Row>
             </div>
          </ProCard>
        </Col>

        {/* 右侧快捷操作与动态 */}
        <Col span={8}>
          <Row gutter={[0, 24]}>
            <Col span={24}>
              <ProCard title="快捷操作" bordered headerBordered>
                 <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
                    <ProCard hoverable bordered style={{ width: '45%', textAlign: 'center' }} onClick={() => window.location.href='/ansible/hosts'}>
                      <DesktopOutlined style={{ fontSize: 24, marginBottom: 8 }} />
                      <div>主机管理</div>
                    </ProCard>
                    <ProCard hoverable bordered style={{ width: '45%', textAlign: 'center' }} onClick={() => window.location.href='/ansible/batch-execute'}>
                      <CodeOutlined style={{ fontSize: 24, marginBottom: 8 }} />
                      <div>批量执行</div>
                    </ProCard>
                 </div>
              </ProCard>
            </Col>
            <Col span={24}>
              <ProCard title="最近活动" bordered headerBordered>
                 <List
                    size="small"
                    dataSource={[
                      { action: '批量更新', time: '10分钟前', user: 'Admin' },
                      { action: '添加主机 192.168.1.100', time: '2小时前', user: 'Admin' },
                      { action: '系统备份', time: '5小时前', user: 'System' },
                    ]}
                    renderItem={item => (
                      <List.Item>
                         <List.Item.Meta
                            avatar={<ClockCircleOutlined />}
                            title={item.action}
                            description={`${item.user} - ${item.time}`}
                         />
                      </List.Item>
                    )}
                 />
              </ProCard>
            </Col>
          </Row>
        </Col>
      </Row>
    </PageContainer>
  );
};

export default Welcome;
