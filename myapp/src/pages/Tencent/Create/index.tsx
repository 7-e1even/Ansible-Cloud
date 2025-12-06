import React, { useRef } from 'react';
import type { ProFormInstance } from '@ant-design/pro-components';
import { PageContainer, ProFormText, ProFormSelect, StepsForm, ProFormSwitch, ProFormDependency, ProForm, ProFormRadio, ProCard, ProFormDigit } from '@ant-design/pro-components';
import { Card, message, Alert, Typography } from 'antd';
import { createInstance, getZones, getRegions } from '@/services/tencent/api';
import { history } from '@umijs/max';
import { GlobalOutlined, CloudServerOutlined, SafetyCertificateOutlined, RocketOutlined } from '@ant-design/icons';
import InstanceTypeSelector from './components/InstanceTypeSelector';
import ImageSelector from './components/ImageSelector';
import RegionSelector from './components/RegionSelector';

const { Text } = Typography;

export default () => {
  const formRef = useRef<ProFormInstance>();

  return (
    <PageContainer>
        <StepsForm
            formRef={formRef}
            containerStyle={{ width: '100%', maxWidth: '100%' }}
            onFinish={async (values) => {
                    try {
                        const hide = message.loading('正在创建实例...', 0);
                        const res = await createInstance(values);
                        hide();
                        message.success('实例创建请求已提交');
                        
                        // Cache password for auto-sync
                        if (res && res.InstanceIdSet && values.Password) {
                            const cache = JSON.parse(localStorage.getItem('tencent_instance_passwords') || '{}');
                            res.InstanceIdSet.forEach((id: string) => {
                                cache[id] = values.Password;
                            });
                            localStorage.setItem('tencent_instance_passwords', JSON.stringify(cache));
                        }

                        history.push('/tencent/instances');
                        return true;
                    } catch (error: any) {
                        message.error(`创建失败: ${error.message}`);
                        return false;
                    }
                }}
                formProps={{
                    validateMessages: {
                        required: '此项为必填项',
                    },
                }}
            >
                {/* Step 1: Resource Configuration */}
                <StepsForm.StepForm
                    name="resource"
                    title="资源配置"
                    style={{ width: '100%', maxWidth: '100%' }}
                    stepProps={{
                        description: '地域、机型与镜像',
                        icon: <GlobalOutlined />,
                    }}
                    onValuesChange={(changeValues) => {
                        if (changeValues.Region) {
                            formRef.current?.setFieldsValue({ 
                                Zone: undefined,
                                InstanceType: undefined,
                                ImageId: undefined
                            });
                        }
                    }}
                >
                    <Alert
                        message="创建须知"
                        description="请确保您的腾讯云账号余额充足。创建成功后将自动扣费。"
                        type="info"
                        showIcon
                        style={{ marginBottom: 24 }}
                    />

                    <ProCard title="地域与可用区" headerBordered bordered style={{ marginBottom: 16 }}>
                        <ProForm.Item name="Region" label="地域" rules={[{ required: true }]}>
                            <RegionSelector />
                        </ProForm.Item>
                        
                        <ProFormDependency name={['Region']}>
                            {({ Region }) => {
                                return (
                                    <ProFormSelect 
                                        key={Region}
                                        name="Zone" 
                                        label="可用区" 
                                        params={{ region: Region }}
                                        request={async (params) => {
                                            if (!params.region) return [];
                                            const zones = await getZones(params.region);
                                            return zones;
                                        }}
                                        width="md"
                                        rules={[{ required: true }]}
                                        placeholder="请先选择地域"
                                        disabled={!Region}
                                    />
                                );
                            }}
                        </ProFormDependency>
                    </ProCard>

                    <ProFormDependency name={['Zone', 'Region']}>
                        {({ Zone, Region }) => (
                            <ProCard title="实例机型" headerBordered bordered style={{ marginBottom: 16 }}>
                                {Region && Zone ? (
                                    <ProForm.Item name="InstanceType" rules={[{ required: true, message: '请选择实例机型' }]}>
                                        <InstanceTypeSelector zone={Zone} region={Region} />
                                    </ProForm.Item>
                                ) : (
                                    <Text type="secondary">
                                        {!Region ? '请先选择地域' : '请选择可用区以加载机型'}
                                    </Text>
                                )}
                            </ProCard>
                        )}
                    </ProFormDependency>

                    <ProFormDependency name={['Region']}>
                        {({ Region }) => (
                            <ProCard title="镜像选择" headerBordered bordered style={{ marginBottom: 16 }}>
                                {Region ? (
                                    <ProForm.Item name="ImageId" rules={[{ required: true, message: '请选择镜像' }]}>
                                        <ImageSelector architecture="x86_64" region={Region} />
                                    </ProForm.Item>
                                ) : <Text type="secondary">请先选择地域</Text>}
                            </ProCard>
                        )}
                    </ProFormDependency>

                    <ProCard title="计费与存储" headerBordered bordered>
                         <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
                            <div style={{ flex: 1, minWidth: '300px' }}>
                                <ProFormRadio.Group
                                    name="InstanceChargeType"
                                    label="计费模式"
                                    initialValue="POSTPAID_BY_HOUR"
                                    options={[
                                        {
                                            label: '按量计费',
                                            value: 'POSTPAID_BY_HOUR',
                                        },
                                        {
                                            label: '竞价实例',
                                            value: 'SPOTPAID',
                                            disabled: true,
                                        },
                                    ]}
                                />
                                <ProFormDigit
                                    name="InstanceCount"
                                    label="购买数量 (台)"
                                    initialValue={1}
                                    min={1}
                                    max={100}
                                    fieldProps={{ precision: 0 }}
                                    width="sm"
                                />
                            </div>
                            <div style={{ flex: 1, minWidth: '300px' }}>
                                <ProFormSelect
                                    name="SystemDiskType"
                                    label="系统盘类型"
                                    initialValue="CLOUD_PREMIUM"
                                    options={[
                                        { label: '高性能云硬盘', value: 'CLOUD_PREMIUM' },
                                        { label: 'SSD云硬盘', value: 'CLOUD_SSD' },
                                    ]}
                                    width="md"
                                />
                                <ProFormDigit
                                    name="SystemDiskSize"
                                    label="系统盘大小 (GB)"
                                    initialValue={50}
                                    min={50}
                                    max={1000}
                                    fieldProps={{ precision: 0 }}
                                    width="md"
                                />
                            </div>
                        </div>
                    </ProCard>
                </StepsForm.StepForm>

                {/* Step 3: Network & Security */}
                <StepsForm.StepForm
                    name="network"
                    title="网络安全"
                    style={{ width: '100%', maxWidth: '100%' }}
                    stepProps={{
                        description: '公网、安全组与密码',
                        icon: <SafetyCertificateOutlined />,
                    }}
                >
                     <ProCard title="公网访问" headerBordered bordered style={{ marginBottom: 16 }}>
                        <ProFormSwitch 
                            name="InternetAccessible" 
                            label="分配公网IP" 
                            initialValue={true} 
                        />
                        <ProFormDependency name={['InternetAccessible']}>
                            {({ InternetAccessible }) => {
                                return InternetAccessible ? (
                                    <ProFormDigit
                                        name="InternetMaxBandwidthOut"
                                        label="公网出带宽 (Mbps)"
                                        initialValue={1}
                                        min={1}
                                        max={100}
                                        width="sm"
                                    />
                                ) : null;
                            }}
                        </ProFormDependency>
                    </ProCard>

                    <ProCard title="登录设置" headerBordered bordered>
                        <ProFormText
                            name="InstanceName"
                            label="实例名称"
                            rules={[
                                { required: true },
                                { max: 60, message: '最长60个字符' }
                            ]}
                            width="md"
                            placeholder="请输入实例名称"
                        />
                        <ProFormText.Password
                            name="Password"
                            label="登录密码"
                            rules={[
                                { required: true },
                                { min: 8, message: '至少8位' },
                                { pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[^]{8,30}$/, message: '需包含大小写字母和数字' }
                            ]}
                            width="md"
                            placeholder="设置实例密码"
                        />
                    </ProCard>
                </StepsForm.StepForm>
                
                 {/* Step 4: Review */}
                <StepsForm.StepForm
                    name="review"
                    title="确认配置"
                    style={{ width: '100%', maxWidth: '100%' }}
                    stepProps={{
                        description: '确认并创建',
                        icon: <RocketOutlined />,
                    }}
                >
                    <ProCard title="配置清单" headerBordered bordered>
                        <ProForm.Item noStyle shouldUpdate>
                            {(form) => {
                                const values = form.getFieldsValue(true);
                                return (
                                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                                        <div><Text strong>实例名称：</Text> {values.InstanceName}</div>
                                        <div><Text strong>地域：</Text> {values.Region}</div>
                                        <div><Text strong>可用区：</Text> {values.Zone}</div>
                                        <div><Text strong>计费模式：</Text> {values.InstanceChargeType === 'POSTPAID_BY_HOUR' ? '按量计费' : values.InstanceChargeType}</div>
                                        <div><Text strong>购买数量：</Text> {values.InstanceCount} 台</div>
                                        <div><Text strong>实例机型：</Text> {values.InstanceType}</div>
                                        <div><Text strong>镜像ID：</Text> {values.ImageId}</div>
                                        <div><Text strong>系统盘：</Text> {values.SystemDiskSize} GB</div>
                                        <div><Text strong>公网IP：</Text> {values.InternetAccessible ? '分配' : '不分配'}</div>
                                    </div>
                                );
                            }}
                        </ProForm.Item>
                    </ProCard>
                     <Alert
                        message="确认创建"
                        description="点击“提交”后将立即开始创建实例。请确保您的配置无误。"
                        type="warning"
                        showIcon
                        style={{ marginTop: 24 }}
                    />
                </StepsForm.StepForm>
            </StepsForm>
    </PageContainer>
  );
};