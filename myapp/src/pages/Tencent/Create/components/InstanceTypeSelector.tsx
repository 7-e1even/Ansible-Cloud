import React, { useState, useEffect, useMemo } from 'react';
import { Radio, Table, Space, Select, Input, Button, Tag } from 'antd';
import { getInstanceTypes } from '@/services/tencent/api';
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons';

interface InstanceTypeSelectorProps {
    value?: string;
    onChange?: (value: string) => void;
    zone?: string;
    region?: string;
}

const InstanceTypeSelector: React.FC<InstanceTypeSelectorProps> = ({ value, onChange, zone, region }) => {
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState<any[]>([]);
    const [fetchedKey, setFetchedKey] = useState<string>();
    
    // Filters
    const [filterCpu, setFilterCpu] = useState<string>('all');
    const [filterMemory, setFilterMemory] = useState<string>('all');
    const [filterFamily, setFilterFamily] = useState<string>('all');
    const [search, setSearch] = useState<string>('');
    const [searchQuery, setSearchQuery] = useState<string>('');

    const currentKey = `${region}-${zone}`;

    useEffect(() => {
        if (!zone) {
            setData([]);
            return;
        }
        if (zone && currentKey !== fetchedKey) {
            setFetchedKey(currentKey);
            setLoading(true);
            getInstanceTypes(zone, region).then(res => {
                setData(res);
                setLoading(false);
            }).catch(() => {
                setData([]); // Clear data on error
                setLoading(false);
            });
        }
    }, [zone, region]);

    // Extract unique options
    const cpuOptions = useMemo(() => Array.from(new Set(data.map(item => item.cpu))).sort((a: any, b: any) => a - b), [data]);
    const memoryOptions = useMemo(() => Array.from(new Set(data.map(item => item.memory))).sort((a: any, b: any) => a - b), [data]);
    const familyOptions = useMemo(() => Array.from(new Set(data.map(item => item.family))).filter(Boolean).sort(), [data]);

    // Filter logic without useMemo to ensure real-time updates
    const filteredData = data.filter(item => {
        if (filterCpu !== 'all' && String(item.cpu) !== String(filterCpu)) return false;
        if (filterMemory !== 'all' && String(item.memory) !== String(filterMemory)) return false;
        if (filterFamily !== 'all' && item.family !== filterFamily) return false;
        if (searchQuery && !item.value.toLowerCase().includes(searchQuery.toLowerCase())) return false;
        return true;
    });

    const columns = [
        { 
            title: '实例', 
            key: 'instance',
            render: (_: any, record: any) => (
                <div>
                    <div style={{ fontWeight: 'bold' }}>{record.typeName || record.family}</div>
                    <div style={{ color: '#888' }}>{record.value}</div>
                </div>
            )
        },
        { 
            title: 'vCPU', 
            dataIndex: 'cpu', 
            render: (text: any) => `${text}核`,
            width: 80 
        },
        { 
            title: '内存', 
            dataIndex: 'memory', 
            render: (text: any) => `${text}GB`,
            width: 80
        },
        { 
            title: '处理器型号/主频', 
            key: 'cpu_info',
            render: (_: any, record: any) => (
                <div>
                    <div>{record.model}</div>
                    <div style={{ color: '#888' }}>{record.frequency}</div>
                </div>
            )
        },
        {
            title: '操作',
            key: 'action',
            width: 80,
            render: (_: any, record: any) => (
                <Radio checked={value === record.value} onChange={() => onChange?.(record.value)} />
            )
        }
    ];

    const resetFilters = () => {
        setFilterCpu('all');
        setFilterMemory('all');
        setFilterFamily('all');
        setSearch('');
        setSearchQuery('');
    };

    const handleSearch = () => {
        setSearchQuery(search);
    };

    return (
        <div>
            <Space style={{ marginBottom: 16, flexWrap: 'wrap' }}>
                <Select 
                    value={filterCpu} 
                    onChange={setFilterCpu} 
                    style={{ width: 120 }} 
                    options={[{ label: '全部CPU', value: 'all' }, ...cpuOptions.map(c => ({ label: `${c}核`, value: String(c) }))]} 
                />
                <Select 
                    value={filterMemory} 
                    onChange={setFilterMemory} 
                    style={{ width: 120 }} 
                    options={[{ label: '全部内存', value: 'all' }, ...memoryOptions.map(m => ({ label: `${m}GB`, value: String(m) }))]} 
                />
                <Input 
                    placeholder="搜索规格名称，如 S5.SMALL2" 
                    value={search} 
                    onChange={e => setSearch(e.target.value)} 
                    style={{ width: 200 }}
                    allowClear
                    onPressEnter={handleSearch}
                />
                <Button type="primary" onClick={handleSearch} icon={<SearchOutlined />}>查询</Button>
                <Button type="default" onClick={resetFilters} icon={<ReloadOutlined />}>重置</Button>
            </Space>

            <div style={{ marginBottom: 16 }}>
                <span style={{ marginRight: 8, fontWeight: 'bold' }}>实例族:</span>
                <Radio.Group 
                    value={filterFamily} 
                    onChange={e => setFilterFamily(e.target.value)} 
                    buttonStyle="solid" 
                    size="small"
                >
                    <Radio.Button value="all">全部实例族</Radio.Button>
                    {familyOptions.map((f: any) => (
                        <Radio.Button key={f} value={f}>{f}</Radio.Button>
                    ))}
                </Radio.Group>
            </div>

            {value && (
                <div style={{ marginBottom: 16, padding: '8px 16px', background: '#e6f7ff', border: '1px solid #91d5ff', borderRadius: '2px' }}>
                    <span style={{ marginRight: 8 }}>已选实例:</span>
                    <Tag color="blue" style={{ fontSize: '14px', padding: '4px 8px' }}>{value}</Tag>
                </div>
            )}

            <Table 
                dataSource={filteredData} 
                columns={columns} 
                rowKey="value" 
                loading={loading}
                size="small"
                pagination={{ pageSize: 10, showSizeChanger: true }}
                scroll={{ y: 400 }}
                onRow={(record) => ({
                    onClick: () => onChange?.(record.value),
                    style: { cursor: 'pointer' }
                })}
            />
        </div>
    );
};

export default InstanceTypeSelector;