import React, { useState, useEffect } from 'react';
import { Radio, Table, Tabs } from 'antd';
import { getImages } from '@/services/tencent/api';

interface ImageSelectorProps {
    value?: string;
    onChange?: (value: string) => void;
    onOsTypeChange?: (osType: string) => void;
    architecture?: string;
    region?: string;
}

const ImageSelector: React.FC<ImageSelectorProps> = ({ value, onChange, onOsTypeChange, architecture, region }) => {
    const [images, setImages] = useState<any[]>([]);
    const [osType, setOsType] = useState<string>('CentOS');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!region) {
            setImages([]);
            return;
        }
        setLoading(true);
        getImages(architecture, osType, region).then(res => {
            setImages(res);
            setLoading(false);
        }).catch(() => {
            setImages([]);
            setLoading(false);
        });
    }, [architecture, osType, region]);

    // Notify parent when osType changes
    useEffect(() => {
        onOsTypeChange?.(osType);
    }, [osType, onOsTypeChange]);

    const columns = [
        { title: '镜像ID', dataIndex: 'value', width: 150 },
        { title: '操作系统', dataIndex: 'os_name' },
        { title: '架构', dataIndex: 'architecture', width: 100 },
        { 
            title: '操作', 
            key: 'action',
            width: 100,
            render: (_: any, record: any) => (
                <Radio checked={value === record.value} onChange={() => onChange?.(record.value)}>
                    选择
                </Radio>
            )
        }
    ];

    return (
        <div>
            <Tabs 
                activeKey={osType} 
                onChange={setOsType}
                type="card"
                items={[
                    { label: 'CentOS', key: 'CentOS' },
                    { label: 'Ubuntu', key: 'Ubuntu' },
                    { label: 'Debian', key: 'Debian' },
                    { label: 'Windows', key: 'Windows' },
                ]}
            />
            <Table 
                dataSource={images} 
                columns={columns} 
                rowKey="value" 
                loading={loading}
                size="small"
                pagination={{ pageSize: 5, showSizeChanger: false }}
                scroll={{ y: 300 }}
                onRow={(record) => ({
                    onClick: () => onChange?.(record.value),
                    style: { cursor: 'pointer' }
                })}
            />
        </div>
    );
};

export default ImageSelector;