import { GithubOutlined } from '@ant-design/icons';
import { DefaultFooter } from '@ant-design/pro-components';
import React from 'react';

const Footer: React.FC = () => {
  return (
    <DefaultFooter
      style={{
        background: 'none',
      }}
      // copyright="Powered by Ant Desgin"
      copyright="炫压抑实验室"
      links={[
        {
          key: '炫压抑实验室',
          title: '炫压抑实验室',
          href: 'https://edenroom.top',
          blankTarget: true,
        },
        {
          key: 'github',
          title: <GithubOutlined />,
          href: 'https://github.com/7-e1even',
          blankTarget: true,
        },
        {
          key: '77',
          title: '77',
          href: 'https://github.com/7-e1even',
          blankTarget: true,
        },
      ]}
    />
  );
};

export default Footer;
