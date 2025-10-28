using System;
using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace MrGaming.SDK.Models
{
    /// <summary>
    /// 游戏授权请求
    /// </summary>
    public class GameAuthRequest
    {
        [JsonPropertyName("app_id")]
        [Range(1, int.MaxValue, ErrorMessage = "应用ID必须是正整数")]
        public int AppId { get; set; }

        [JsonPropertyName("player_count")]
        [Range(1, 100, ErrorMessage = "玩家数量必须在1-100之间")]
        public int PlayerCount { get; set; }

        [JsonPropertyName("session_id")]
        [Required(ErrorMessage = "会话ID不能为空")]
        [StringLength(100, MinimumLength = 1, ErrorMessage = "会话ID长度应在1-100个字符之间")]
        public string SessionId { get; set; } = string.Empty;

        [JsonPropertyName("site_id")]
        [StringLength(50, ErrorMessage = "运营点ID长度不能超过50个字符")]
        public string? SiteId { get; set; }
    }

    /// <summary>
    /// 游戏授权响应
    /// </summary>
    public class GameAuthResponse
    {
        [JsonPropertyName("success")]
        public bool Success { get; set; }

        [JsonPropertyName("session_id")]
        public string SessionId { get; set; } = string.Empty;

        [JsonPropertyName("auth_token")]
        public string AuthToken { get; set; } = string.Empty;

        [JsonPropertyName("player_count")]
        public int PlayerCount { get; set; }

        [JsonPropertyName("cost_per_player")]
        public decimal CostPerPlayer { get; set; }

        [JsonPropertyName("expires_at")]
        public DateTime ExpiresAt { get; set; }
    }

    /// <summary>
    /// 结束会话请求
    /// </summary>
    public class EndSessionRequest
    {
        [JsonPropertyName("app_id")]
        [Range(1, int.MaxValue, ErrorMessage = "应用ID必须是正整数")]
        public int AppId { get; set; }

        [JsonPropertyName("session_id")]
        [Required(ErrorMessage = "会话ID不能为空")]
        [StringLength(100, MinimumLength = 1, ErrorMessage = "会话ID长度应在1-100个字符之间")]
        public string SessionId { get; set; } = string.Empty;

        [JsonPropertyName("player_count")]
        [Range(1, 100, ErrorMessage = "玩家数量必须在1-100之间")]
        public int PlayerCount { get; set; }

        [JsonPropertyName("site_id")]
        [StringLength(50, ErrorMessage = "运营点ID长度不能超过50个字符")]
        public string? SiteId { get; set; }
    }

    /// <summary>
    /// 结束会话响应
    /// </summary>
    public class EndSessionResponse
    {
        [JsonPropertyName("success")]
        public bool Success { get; set; }

        [JsonPropertyName("session_id")]
        public string SessionId { get; set; } = string.Empty;

        [JsonPropertyName("total_cost")]
        public decimal TotalCost { get; set; }

        [JsonPropertyName("duration_minutes")]
        public int DurationMinutes { get; set; }
    }

    /// <summary>
    /// 运营点
    /// </summary>
    public class Site
    {
        [JsonPropertyName("site_id")]
        public string SiteId { get; set; } = string.Empty;

        [JsonPropertyName("operator_id")]
        public string OperatorId { get; set; } = string.Empty;

        [JsonPropertyName("site_name")]
        public string SiteName { get; set; } = string.Empty;

        [JsonPropertyName("address")]
        public string Address { get; set; } = string.Empty;

        [JsonPropertyName("contact_person")]
        public string ContactPerson { get; set; } = string.Empty;

        [JsonPropertyName("contact_phone")]
        public string ContactPhone { get; set; } = string.Empty;

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }

        [JsonPropertyName("updated_at")]
        public DateTime UpdatedAt { get; set; }
    }

    /// <summary>
    /// 创建运营点请求
    /// </summary>
    public class CreateSiteRequest
    {
        [JsonPropertyName("site_name")]
        [Required(ErrorMessage = "运营点名称不能为空")]
        [StringLength(100, MinimumLength = 2, ErrorMessage = "运营点名称长度应在2-100个字符之间")]
        public string SiteName { get; set; } = string.Empty;

        [JsonPropertyName("address")]
        [Required(ErrorMessage = "地址不能为空")]
        [StringLength(200, MinimumLength = 5, ErrorMessage = "地址长度应在5-200个字符之间")]
        public string Address { get; set; } = string.Empty;

        [JsonPropertyName("contact_person")]
        [Required(ErrorMessage = "联系人不能为空")]
        [StringLength(50, MinimumLength = 2, ErrorMessage = "联系人姓名长度应在2-50个字符之间")]
        public string ContactPerson { get; set; } = string.Empty;

        [JsonPropertyName("contact_phone")]
        [Required(ErrorMessage = "联系电话不能为空")]
        [Phone(ErrorMessage = "手机号格式不正确")]
        public string ContactPhone { get; set; } = string.Empty;
    }

    /// <summary>
    /// 更新运营点请求
    /// </summary>
    public class UpdateSiteRequest
    {
        [JsonPropertyName("site_name")]
        [StringLength(100, MinimumLength = 2, ErrorMessage = "运营点名称长度应在2-100个字符之间")]
        public string? SiteName { get; set; }

        [JsonPropertyName("address")]
        [StringLength(200, MinimumLength = 5, ErrorMessage = "地址长度应在5-200个字符之间")]
        public string? Address { get; set; }

        [JsonPropertyName("contact_person")]
        [StringLength(50, MinimumLength = 2, ErrorMessage = "联系人姓名长度应在2-50个字符之间")]
        public string? ContactPerson { get; set; }

        [JsonPropertyName("contact_phone")]
        [Phone(ErrorMessage = "手机号格式不正确")]
        public string? ContactPhone { get; set; }
    }

    /// <summary>
    /// 游戏应用
    /// </summary>
    public class GameApp
    {
        [JsonPropertyName("app_id")]
        public int AppId { get; set; }

        [JsonPropertyName("app_name")]
        public string AppName { get; set; } = string.Empty;

        [JsonPropertyName("description")]
        public string? Description { get; set; }

        [JsonPropertyName("cost_per_player_per_minute")]
        public decimal CostPerPlayerPerMinute { get; set; }

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }

        [JsonPropertyName("updated_at")]
        public DateTime UpdatedAt { get; set; }
    }

    /// <summary>
    /// 游戏统计
    /// </summary>
    public class GameStats
    {
        [JsonPropertyName("app_id")]
        public int AppId { get; set; }

        [JsonPropertyName("app_name")]
        public string AppName { get; set; } = string.Empty;

        [JsonPropertyName("total_sessions")]
        public int TotalSessions { get; set; }

        [JsonPropertyName("total_players")]
        public int TotalPlayers { get; set; }

        [JsonPropertyName("total_revenue")]
        public decimal TotalRevenue { get; set; }

        [JsonPropertyName("avg_session_duration")]
        public double AvgSessionDuration { get; set; }

        [JsonPropertyName("revenue_per_session")]
        public decimal RevenuePerSession { get; set; }
    }

    /// <summary>
    /// 消费统计
    /// </summary>
    public class ConsumptionStats
    {
        [JsonPropertyName("total_players")]
        public int TotalPlayers { get; set; }

        [JsonPropertyName("total_duration")]
        public int TotalDuration { get; set; }

        [JsonPropertyName("total_cost")]
        public decimal TotalCost { get; set; }

        [JsonPropertyName("session_count")]
        public int SessionCount { get; set; }

        [JsonPropertyName("avg_session_duration")]
        public double AvgSessionDuration { get; set; }

        [JsonPropertyName("cost_per_hour")]
        public decimal CostPerHour { get; set; }
    }
}