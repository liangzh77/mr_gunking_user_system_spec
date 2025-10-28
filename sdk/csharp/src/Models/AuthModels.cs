using System;
using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace MrGaming.SDK.Models
{
    /// <summary>
    /// 运营商注册请求
    /// </summary>
    public class OperatorRegisterRequest
    {
        [JsonPropertyName("username")]
        [Required(ErrorMessage = "用户名不能为空")]
        [StringLength(50, MinimumLength = 3, ErrorMessage = "用户名长度应在3-50个字符之间")]
        [RegularExpression(@"^[a-zA-Z0-9_]+$", ErrorMessage = "用户名只能包含字母、数字和下划线")]
        public string Username { get; set; } = string.Empty;

        [JsonPropertyName("password")]
        [Required(ErrorMessage = "密码不能为空")]
        [StringLength(100, MinimumLength = 8, ErrorMessage = "密码长度应在8-100个字符之间")]
        public string Password { get; set; } = string.Empty;

        [JsonPropertyName("name")]
        [Required(ErrorMessage = "姓名不能为空")]
        [StringLength(100, MinimumLength = 2, ErrorMessage = "姓名长度应在2-100个字符之间")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("email")]
        [Required(ErrorMessage = "邮箱不能为空")]
        [EmailAddress(ErrorMessage = "邮箱格式不正确")]
        public string Email { get; set; } = string.Empty;

        [JsonPropertyName("phone")]
        [Required(ErrorMessage = "手机号不能为空")]
        [Phone(ErrorMessage = "手机号格式不正确")]
        public string Phone { get; set; } = string.Empty;

        [JsonPropertyName("company_name")]
        [StringLength(200, ErrorMessage = "公司名称长度不能超过200个字符")]
        public string? CompanyName { get; set; }
    }

    /// <summary>
    /// 运营商登录请求
    /// </summary>
    public class OperatorLoginRequest
    {
        [JsonPropertyName("username")]
        [Required(ErrorMessage = "用户名不能为空")]
        public string Username { get; set; } = string.Empty;

        [JsonPropertyName("password")]
        [Required(ErrorMessage = "密码不能为空")]
        public string Password { get; set; } = string.Empty;
    }

    /// <summary>
    /// 认证响应
    /// </summary>
    public class AuthResponse
    {
        [JsonPropertyName("access_token")]
        public string AccessToken { get; set; } = string.Empty;

        [JsonPropertyName("token_type")]
        public string TokenType { get; set; } = string.Empty;

        [JsonPropertyName("expires_in")]
        public int ExpiresIn { get; set; }

        [JsonPropertyName("operator_id")]
        public string OperatorId { get; set; } = string.Empty;

        [JsonPropertyName("username")]
        public string Username { get; set; } = string.Empty;

        [JsonPropertyName("balance")]
        public decimal Balance { get; set; }
    }

    /// <summary>
    /// 运营商信息
    /// </summary>
    public class Operator
    {
        [JsonPropertyName("operator_id")]
        public string OperatorId { get; set; } = string.Empty;

        [JsonPropertyName("username")]
        public string Username { get; set; } = string.Empty;

        [JsonPropertyName("full_name")]
        public string FullName { get; set; } = string.Empty;

        [JsonPropertyName("email")]
        public string Email { get; set; } = string.Empty;

        [JsonPropertyName("phone")]
        public string Phone { get; set; } = string.Empty;

        [JsonPropertyName("company_name")]
        public string? CompanyName { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }

        [JsonPropertyName("updated_at")]
        public DateTime UpdatedAt { get; set; }
    }

    /// <summary>
    /// 修改密码请求
    /// </summary>
    public class ChangePasswordRequest
    {
        [JsonPropertyName("old_password")]
        [Required(ErrorMessage = "旧密码不能为空")]
        public string OldPassword { get; set; } = string.Empty;

        [JsonPropertyName("new_password")]
        [Required(ErrorMessage = "新密码不能为空")]
        [StringLength(100, MinimumLength = 8, ErrorMessage = "密码长度应在8-100个字符之间")]
        public string NewPassword { get; set; } = string.Empty;
    }

    /// <summary>
    /// 刷新Token请求
    /// </summary>
    public class RefreshTokenRequest
    {
        [JsonPropertyName("refresh_token")]
        public string RefreshToken { get; set; } = string.Empty;
    }

    /// <summary>
    /// 密码验证结果
    /// </summary>
    public class PasswordValidationResult
    {
        public bool IsValid { get; set; }
        public List<string> Errors { get; set; } = new List<string>();
    }
}