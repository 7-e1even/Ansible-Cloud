import React, { useState, useEffect } from 'react';
import { Tabs, Button, Space, Spin } from 'antd';
import { getRegions } from '@/services/tencent/api';

interface RegionSelectorProps {
    value?: string;
    onChange?: (value: string) => void;
}

const RegionSelector: React.FC<RegionSelectorProps> = ({ value, onChange }) => {
    const [loading, setLoading] = useState(false);
    const [regions, setRegions] = useState<any[]>([]);

    useEffect(() => {
        setLoading(true);
        getRegions().then(res => {
            setRegions(res);
            setLoading(false);
        }).catch(() => setLoading(false));
    }, []);

    // Group regions (Simplified logic for demo)
    const groups = {
        '中国': ['ap-guangzhou', 'ap-shanghai', 'ap-beijing', 'ap-chengdu', 'ap-chongqing', 'ap-nanjing', 'ap-hongkong', 'ap-taipei'],
        '亚太和中东': ['ap-singapore', 'ap-bangkok', 'ap-jakarta', 'ap-seoul', 'ap-tokyo', 'ap-mumbai'],
        '欧洲和美洲': ['eu-frankfurt', 'eu-moscow', 'na-ashburn', 'na-siliconvalley', 'na-toronto', 'sa-saopaulo']
    };

    const getRegionGroup = (regionValue: string) => {
        for (const [group, prefixes] of Object.entries(groups)) {
            if (prefixes.includes(regionValue)) return group;
        }
        return '其他';
    };

    const groupedRegions: Record<string, any[]> = { '中国': [], '亚太和中东': [], '欧洲和美洲': [], '其他': [] };
    
    regions.forEach(r => {
        const group = getRegionGroup(r.value);
        groupedRegions[group].push(r);
    });

    const [activeTab, setActiveTab] = useState('中国');

    return (
        <Spin spinning={loading}>
            <Tabs 
                activeKey={activeTab} 
                onChange={setActiveTab}
                type="card"
                items={Object.keys(groupedRegions).filter(k => groupedRegions[k].length > 0).map(group => ({
                    label: group,
                    key: group,
                    children: (
                        <Space wrap>
                            {groupedRegions[group].map(region => (
                                <Button 
                                    key={region.value} 
                                    type={value === region.value ? 'primary' : 'default'}
                                    onClick={() => onChange?.(region.value)}
                                >
                                    {region.label}
                                </Button>
                            ))}
                        </Space>
                    )
                }))}
            />
        </Spin>
    );
};

export default RegionSelector;