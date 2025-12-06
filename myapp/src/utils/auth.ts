export const authStorage = {
  // 设置认证状态和JWT令牌，包含过期时间（默认5小时）
  setAuth: (value: boolean, token: string | null = null, expiresInHours: number = 5) => {
    if (typeof localStorage !== 'undefined') {
      const expiresAt = new Date();
      expiresAt.setHours(expiresAt.getHours() + expiresInHours);
      
      localStorage.setItem('isAuthenticated', value ? 'true' : 'false');
      localStorage.setItem('authExpiresAt', expiresAt.toISOString());
      
      // 存储JWT令牌
      if (token) {
        localStorage.setItem('token', token);
      } else if (value === false) {
        localStorage.removeItem('token');
      }
    }
  },
  
  // 获取认证状态，如果已过期则返回false
  getAuth: (): boolean => {
    if (typeof localStorage !== 'undefined') {
      const isAuth = localStorage.getItem('isAuthenticated') === 'true';
      const expiresAt = localStorage.getItem('authExpiresAt');
      
      if (isAuth && expiresAt) {
        // 检查是否过期
        const now = new Date();
        const expiry = new Date(expiresAt);
        
        if (now < expiry) {
          return true;
        } else {
          // 已过期，清除
          authStorage.clearAuth();
        }
      }
    }
    return false;
  },
  
  // 获取JWT令牌
  getToken: (): string | null => {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem('token');
    }
    return null;
  },
  
  // 清除认证状态
  clearAuth: () => {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('isAuthenticated');
      localStorage.removeItem('authExpiresAt');
      localStorage.removeItem('token');
    }
  }
};
