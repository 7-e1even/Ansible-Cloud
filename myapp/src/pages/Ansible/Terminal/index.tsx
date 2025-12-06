import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { PageContainer } from '@ant-design/pro-components';
import { Card, Alert, Spin, message } from 'antd';
import { useSearchParams } from '@umijs/max';
import 'xterm/css/xterm.css';
import { getWsToken } from '@/services/ansible/api';

const TerminalPage: React.FC = () => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const [searchParams] = useSearchParams();
  const hostId = searchParams.get('host_id');
  
  const [status, setStatus] = useState<'initializing' | 'connecting' | 'connected' | 'disconnected' | 'error'>('initializing');
  const [errorMsg, setErrorMsg] = useState<string>('');

  useEffect(() => {
    if (!hostId) {
      setStatus('error');
      setErrorMsg('Missing host_id parameter');
      return;
    }

    const initTerminal = async () => {
      try {
        // 1. Initialize xterm
        if (!terminalRef.current) return;
        
        // Avoid double initialization
        if (termRef.current) {
             termRef.current.dispose();
        }

        const term = new Terminal({
          cursorBlink: true,
          fontSize: 14,
          fontFamily: 'Menlo, Monaco, "Courier New", monospace',
          theme: {
            background: '#1e1e1e',
            foreground: '#f0f0f0',
          },
          rows: 30,
        });

        const fitAddon = new FitAddon();
        term.loadAddon(fitAddon);
        term.open(terminalRef.current);
        
        // Initial fit
        setTimeout(() => {
            fitAddon.fit();
        }, 100);

        termRef.current = term;
        fitAddonRef.current = fitAddon;
        
        term.writeln('Requesting access token...');

        // 2. Get Token
        const { token } = await getWsToken(parseInt(hostId));
        
        term.writeln('Connecting to WebSocket...');
        setStatus('connecting');

        // 3. Connect WebSocket
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        
        // Directly connect to backend port 3000 to avoid proxy issues during development
        // In production, this should be handled by Nginx or similar
        const backendHost = window.location.hostname; // 'localhost' or '127.0.0.1'
        const wsUrl = `${protocol}//${backendHost}:3000/ws/terminal/${hostId}?token=${token}`;
        
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          setStatus('connected');
          term.clear(); // Clear initial messages
          term.writeln('\x1b[1;32m*** Connection Established ***\x1b[0m');
          term.write('\r\n');
          term.focus(); // Auto focus terminal
          
          // Send resize event immediately
          const dims = fitAddon.proposeDimensions();
          if (dims) {
              ws.send(JSON.stringify({
                type: 'resize',
                data: { cols: dims.cols, rows: dims.rows }
              }));
          }
        };

        ws.onmessage = (event) => {
          // Check if message is JSON (control message) or plain text (terminal output)
          // The backend currently sends plain text for SSH output
          // But if we want to support more structured data later, we can check here.
          // For now, treat all as text unless it starts with '{' and ends with '}' which is risky for terminal output.
          // Actually, backend only sends raw SSH output as text.
          term.write(event.data);
        };

        ws.onclose = (e) => {
          setStatus('disconnected');
          term.writeln(`\r\n\x1b[1;31m*** Connection closed (Code: ${e.code}) ***\x1b[0m`);
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setStatus('error');
          term.writeln('\r\n\x1b[1;31m*** Connection error ***\x1b[0m');
        };

        term.onData((data) => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'input',
                data: data
            }));
          }
        });

        // Focus terminal on click
        term.attachCustomKeyEventHandler((event) => {
             // You can handle custom keys here if needed
             return true;
        });

        term.onResize((size) => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'resize',
                    data: { cols: size.cols, rows: size.rows }
                }));
            }
        });

        wsRef.current = ws;

      } catch (err: any) {
        console.error(err);
        setStatus('error');
        setErrorMsg(err.message || 'Failed to initialize terminal');
        if (termRef.current) {
            termRef.current.writeln(`\r\n\x1b[1;31mError: ${err.message}\x1b[0m`);
        }
      }
    };

    initTerminal();

    // Window resize handler
    const handleResize = () => {
        if (fitAddonRef.current) {
            fitAddonRef.current.fit();
        }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      if (termRef.current) {
        termRef.current.dispose();
        termRef.current = null;
      }
    };
  }, [hostId]);

  return (
    <PageContainer title={`Terminal (Host ID: ${hostId})`}>
      <Card>
        {status === 'error' && (
           <Alert message={errorMsg} type="error" showIcon style={{ marginBottom: 16 }} />
        )}
        {status === 'initializing' && (
            <div style={{ textAlign: 'center', padding: 20 }}>
                <Spin tip="Initializing connection..." />
            </div>
        )}
        <div 
          ref={terminalRef} 
          style={{ 
            height: '600px', 
            width: '100%', 
            backgroundColor: '#1e1e1e',
            padding: '8px',
            borderRadius: '4px',
            visibility: (status === 'initializing' || (status === 'error' && !termRef.current)) ? 'hidden' : 'visible'
          }} 
        />
      </Card>
    </PageContainer>
  );
};

export default TerminalPage;
