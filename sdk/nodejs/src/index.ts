/**
 * MR游戏运营管理系统 Node.js SDK
 *
 * 提供运营商认证、游戏授权、财务管理、余额查询等功能的接口
 */

export { MRSdk } from './sdk';
export {
  OperatorAuth,
  GameService,
  BalanceService,
  TransactionService,
  RechargeService,
  RefundService
} from './services';
export {
  AuthError,
  ApiError,
  ValidationError,
  NetworkError
} from './errors';
export * from './types';

// 默认导出主SDK类
export { MRSdk as default } from './sdk';