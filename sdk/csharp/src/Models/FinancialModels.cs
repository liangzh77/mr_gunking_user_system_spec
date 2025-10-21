using System;
using System.ComponentModel.DataAnnotations;
using System.Text.Json.Serialization;

namespace MrGaming.SDK.Models
{
    /// <summary>
    /// 余额信息
    /// </summary>
    public class BalanceInfo
    {
        [JsonPropertyName("balance")]
        public decimal Balance { get; set; }

        [JsonPropertyName("available_balance")]
        public decimal AvailableBalance { get; set; }

        [JsonPropertyName("frozen_balance")]
        public decimal FrozenBalance { get; set; }

        [JsonPropertyName("currency")]
        public string Currency { get; set; } = "CNY";

        [JsonPropertyName("updated_at")]
        public DateTime UpdatedAt { get; set; }
    }

    /// <summary>
    /// 冻结余额请求
    /// </summary>
    public class FreezeBalanceRequest
    {
        [JsonPropertyName("amount")]
        [Range(0.01, double.MaxValue, ErrorMessage = "冻结金额必须大于0")]
        public decimal Amount { get; set; }

        [JsonPropertyName("reason")]
        [Required(ErrorMessage = "冻结原因不能为空")]
        [StringLength(500, MinimumLength = 1, ErrorMessage = "冻结原因长度应在1-500个字符之间")]
        public string Reason { get; set; } = string.Empty;
    }

    /// <summary>
    /// 解冻余额请求
    /// </summary>
    public class UnfreezeBalanceRequest
    {
        [JsonPropertyName("freeze_id")]
        [Required(ErrorMessage = "冻结记录ID不能为空")]
        public string FreezeId { get; set; } = string.Empty;

        [JsonPropertyName("amount")]
        [Range(0.01, double.MaxValue, ErrorMessage = "解冻金额必须大于0")]
        public decimal? Amount { get; set; }
    }

    /// <summary>
    /// 交易记录
    /// </summary>
    public class Transaction
    {
        [JsonPropertyName("transaction_id")]
        public string TransactionId { get; set; } = string.Empty;

        [JsonPropertyName("operator_id")]
        public string OperatorId { get; set; } = string.Empty;

        [JsonPropertyName("type")]
        public string Type { get; set; } = string.Empty;

        [JsonPropertyName("amount")]
        public decimal Amount { get; set; }

        [JsonPropertyName("balance_before")]
        public decimal BalanceBefore { get; set; }

        [JsonPropertyName("balance_after")]
        public decimal BalanceAfter { get; set; }

        [JsonPropertyName("description")]
        public string Description { get; set; } = string.Empty;

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;
    }

    /// <summary>
    /// 交易记录查询参数
    /// </summary>
    public class TransactionListRequest
    {
        [JsonPropertyName("page")]
        [Range(1, int.MaxValue, ErrorMessage = "页码必须大于0")]
        public int Page { get; set; } = 1;

        [JsonPropertyName("page_size")]
        [Range(1, 100, ErrorMessage = "每页数量必须在1-100之间")]
        public int PageSize { get; set; } = 20;

        [JsonPropertyName("type")]
        public string? Type { get; set; }

        [JsonPropertyName("start_date")]
        public string? StartDate { get; set; }

        [JsonPropertyName("end_date")]
        public string? EndDate { get; set; }
    }

    /// <summary>
    /// 充值请求
    /// </summary>
    public class RechargeRequest
    {
        [JsonPropertyName("amount")]
        [Required(ErrorMessage = "充值金额不能为空")]
        [RegularExpression(@"^\d+(\.\d{1,2})?$", ErrorMessage = "充值金额格式不正确")]
        public string Amount { get; set; } = string.Empty;

        [JsonPropertyName("payment_method")]
        [Required(ErrorMessage = "支付方式不能为空")]
        [RegularExpression(@"^(alipay|wechat|bank_transfer)$", ErrorMessage = "支付方式无效")]
        public string PaymentMethod { get; set; } = string.Empty;

        [JsonPropertyName("return_url")]
        [StringLength(500, ErrorMessage = "返回URL长度不能超过500个字符")]
        public string? ReturnUrl { get; set; }

        [JsonPropertyName("notify_url")]
        [StringLength(500, ErrorMessage = "通知URL长度不能超过500个字符")]
        public string? NotifyUrl { get; set; }
    }

    /// <summary>
    /// 充值订单
    /// </summary>
    public class RechargeOrder
    {
        [JsonPropertyName("order_id")]
        public string OrderId { get; set; } = string.Empty;

        [JsonPropertyName("amount")]
        public decimal Amount { get; set; }

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;

        [JsonPropertyName("payment_method")]
        public string PaymentMethod { get; set; } = string.Empty;

        [JsonPropertyName("qr_code")]
        public string? QrCode { get; set; }

        [JsonPropertyName("payment_url")]
        public string? PaymentUrl { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }

        [JsonPropertyName("expires_at")]
        public DateTime ExpiresAt { get; set; }
    }

    /// <summary>
    /// 退款请求
    /// </summary>
    public class RefundRequest
    {
        [JsonPropertyName("reason")]
        [Required(ErrorMessage = "退款原因不能为空")]
        [StringLength(500, MinimumLength = 10, ErrorMessage = "退款原因长度应在10-500个字符之间")]
        public string Reason { get; set; } = string.Empty;

        [JsonPropertyName("amount")]
        [RegularExpression(@"^\d+(\.\d{1,2})?$", ErrorMessage = "退款金额格式不正确")]
        public string? Amount { get; set; }

        [JsonPropertyName("transaction_ids")]
        public List<string>? TransactionIds { get; set; }
    }

    /// <summary>
    /// 退款响应
    /// </summary>
    public class RefundResponse
    {
        [JsonPropertyName("refund_request_id")]
        public string RefundRequestId { get; set; } = string.Empty;

        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;

        [JsonPropertyName("amount")]
        public decimal Amount { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }
    }

    /// <summary>
    /// 支付方式
    /// </summary>
    public class PaymentMethod
    {
        [JsonPropertyName("method")]
        public string Method { get; set; } = string.Empty;

        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("icon")]
        public string Icon { get; set; } = string.Empty;

        [JsonPropertyName("is_active")]
        public bool IsActive { get; set; }

        [JsonPropertyName("min_amount")]
        public decimal MinAmount { get; set; }

        [JsonPropertyName("max_amount")]
        public decimal MaxAmount { get; set; }

        [JsonPropertyName("fee_rate")]
        public decimal FeeRate { get; set; }
    }

    /// <summary>
    /// 余额历史记录
    /// </summary>
    public class BalanceHistory
    {
        [JsonPropertyName("history_id")]
        public string HistoryId { get; set; } = string.Empty;

        [JsonPropertyName("type")]
        public string Type { get; set; } = string.Empty;

        [JsonPropertyName("amount")]
        public decimal Amount { get; set; }

        [JsonPropertyName("balance_before")]
        public decimal BalanceBefore { get; set; }

        [JsonPropertyName("balance_after")]
        public decimal BalanceAfter { get; set; }

        [JsonPropertyName("description")]
        public string Description { get; set; } = string.Empty;

        [JsonPropertyName("related_id")]
        public string? RelatedId { get; set; }

        [JsonPropertyName("created_at")]
        public DateTime CreatedAt { get; set; }
    }

    /// <summary>
    /// 财务统计
    /// </summary>
    public class FinancialStats
    {
        [JsonPropertyName("period")]
        public string Period { get; set; } = string.Empty;

        [JsonPropertyName("total_revenue")]
        public decimal TotalRevenue { get; set; }

        [JsonPropertyName("total_cost")]
        public decimal TotalCost { get; set; }

        [JsonPropertyName("net_profit")]
        public decimal NetProfit { get; set; }

        [JsonPropertyName("transaction_count")]
        public int TransactionCount { get; set; }

        [JsonPropertyName("avg_transaction_amount")]
        public decimal AvgTransactionAmount { get; set; }
    }

    /// <summary>
    /// 余额预警设置
    /// </summary>
    public class BalanceAlertSettings
    {
        [JsonPropertyName("low_balance_threshold")]
        [Range(0, double.MaxValue, ErrorMessage = "预警阈值必须大于等于0")]
        public decimal LowBalanceThreshold { get; set; }

        [JsonPropertyName("alert_enabled")]
        public bool AlertEnabled { get; set; }

        [JsonPropertyName("alert_methods")]
        public List<string> AlertMethods { get; set; } = new List<string>();
    }
}