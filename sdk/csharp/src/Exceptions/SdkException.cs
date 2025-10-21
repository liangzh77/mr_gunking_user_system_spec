using System;

namespace MrGaming.SDK.Exceptions
{
    /// <summary>
    /// SDK基础异常类
    /// </summary>
    public class SdkException : Exception
    {
        public string ErrorCode { get; }
        public object? Details { get; }

        public SdkException(string message, string errorCode, object? details = null)
            : base(message)
        {
            ErrorCode = errorCode;
            Details = details;
        }

        public SdkException(string message, string errorCode, Exception innerException, object? details = null)
            : base(message, innerException)
        {
            ErrorCode = errorCode;
            Details = details;
        }

        public override string ToString()
        {
            return $"{GetType().Name}: {Message} (ErrorCode: {ErrorCode})";
        }
    }

    /// <summary>
    /// 认证异常
    /// </summary>
    public class AuthenticationException : SdkException
    {
        public AuthenticationException(string message = "认证失败", object? details = null)
            : base(message, "AUTH_ERROR", details)
        {
        }

        public AuthenticationException(string message, Exception innerException, object? details = null)
            : base(message, "AUTH_ERROR", innerException, details)
        {
        }
    }

    /// <summary>
    /// API异常
    /// </summary>
    public class ApiException : SdkException
    {
        public int? StatusCode { get; }
        public object? ResponseData { get; }

        public ApiException(string message, int? statusCode = null, object? responseData = null)
            : base(message, "API_ERROR", responseData)
        {
            StatusCode = statusCode;
            ResponseData = responseData;
        }

        public ApiException(string message, Exception innerException, int? statusCode = null, object? responseData = null)
            : base(message, "API_ERROR", innerException, responseData)
        {
            StatusCode = statusCode;
            ResponseData = responseData;
        }
    }

    /// <summary>
    /// 验证异常
    /// </summary>
    public class ValidationException : SdkException
    {
        public ValidationException(string message = "数据验证失败", object? details = null)
            : base(message, "VALIDATION_ERROR", details)
        {
        }

        public ValidationException(string message, Exception innerException, object? details = null)
            : base(message, "VALIDATION_ERROR", innerException, details)
        {
        }
    }

    /// <summary>
    /// 网络异常
    /// </summary>
    public class NetworkException : SdkException
    {
        public NetworkException(string message = "网络连接失败", object? details = null)
            : base(message, "NETWORK_ERROR", details)
        {
        }

        public NetworkException(string message, Exception innerException, object? details = null)
            : base(message, "NETWORK_ERROR", innerException, details)
        {
        }
    }

    /// <summary>
    /// 权限异常
    /// </summary>
    public class PermissionException : SdkException
    {
        public PermissionException(string message = "权限不足", object? details = null)
            : base(message, "PERMISSION_ERROR", details)
        {
        }

        public PermissionException(string message, Exception innerException, object? details = null)
            : base(message, "PERMISSION_ERROR", innerException, details)
        {
        }
    }

    /// <summary>
    /// 业务逻辑异常
    /// </summary>
    public class BusinessException : SdkException
    {
        public BusinessException(string message, string errorCode, object? details = null)
            : base(message, errorCode, details)
        {
        }

        public BusinessException(string message, string errorCode, Exception innerException, object? details = null)
            : base(message, errorCode, innerException, details)
        {
        }
    }

    /// <summary>
    /// 余额不足异常
    /// </summary>
    public class InsufficientBalanceException : BusinessException
    {
        public InsufficientBalanceException(string message = "余额不足", object? details = null)
            : base(message, "INSUFFICIENT_BALANCE", details)
        {
        }

        public InsufficientBalanceException(string message, Exception innerException, object? details = null)
            : base(message, "INSUFFICIENT_BALANCE", innerException, details)
        {
        }
    }

    /// <summary>
    /// 游戏会话异常
    /// </summary>
    public class GameSessionException : BusinessException
    {
        public GameSessionException(string message, object? details = null)
            : base(message, "GAME_SESSION_ERROR", details)
        {
        }

        public GameSessionException(string message, Exception innerException, object? details = null)
            : base(message, "GAME_SESSION_ERROR", innerException, details)
        {
        }
    }

    /// <summary>
    /// 重复请求异常
    /// </summary>
    public class DuplicateRequestException : BusinessException
    {
        public DuplicateRequestException(string message = "重复的请求", object? details = null)
            : base(message, "DUPLICATE_REQUEST", details)
        {
        }

        public DuplicateRequestException(string message, Exception innerException, object? details = null)
            : base(message, "DUPLICATE_REQUEST", innerException, details)
        {
        }
    }
}