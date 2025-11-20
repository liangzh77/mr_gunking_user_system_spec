import * as dotenv from 'dotenv';

// 加载 .env 文件
dotenv.config();

export interface Environment {
  name: string;
  baseURL: string;
  credentials: {
    admin: { username: string; password: string };
    finance: { username: string; password: string };
    operator: { username: string; password: string };
  };
  ignoreHTTPSErrors: boolean;
  database?: {
    host: string;
    port: number;
    database: string;
    user: string;
    password: string;
  };
}

export const environments: Record<string, Environment> = {
  localhost: {
    name: 'localhost',
    baseURL: 'https://localhost',
    credentials: {
      admin: { username: 'admin', password: 'admin123' },
      finance: { username: 'finance1', password: 'finance123' },
      operator: { username: 'operator1', password: 'operator123' },
    },
    ignoreHTTPSErrors: true,
    database: {
      host: 'localhost',
      port: 5432,
      database: 'mr_game_ops',
      user: 'mr_admin',
      password: 'mr_secure_password_2024',
    },
  },

  production: {
    name: 'production',
    baseURL: 'https://mrgun.chu-jiao.com',
    credentials: {
      admin: {
        username: 'admin',
        password: process.env.PROD_ADMIN_PASSWORD || ''
      },
      finance: {
        username: 'finance1',
        password: process.env.PROD_FINANCE_PASSWORD || ''
      },
      operator: {
        username: 'operator1',
        password: process.env.PROD_OPERATOR_PASSWORD || ''
      },
    },
    ignoreHTTPSErrors: false,
    // 生产环境不直接操作数据库
  },
};

/**
 * 从环境变量获取当前测试环境配置
 */
export function getEnvironment(): Environment {
  const envName = process.env.TEST_ENV || 'localhost';
  const env = environments[envName];

  if (!env) {
    throw new Error(
      `Unknown environment: ${envName}. Available: ${Object.keys(environments).join(', ')}`
    );
  }

  // 验证生产环境凭证
  if (env.name === 'production') {
    if (!env.credentials.admin.password ||
        !env.credentials.finance.password ||
        !env.credentials.operator.password) {
      console.warn('⚠️  Warning: Production credentials not fully configured in .env file');
    }
  }

  return env;
}
