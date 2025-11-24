/**
 * 格式化工具函数
 */

/**
 * 格式化日期时间为本地时间格式
 * @param dateString ISO 8601格式的时间字符串 (如: 2025-11-10T06:10:38.137119+00:00)
 * @returns 格式化后的本地时间字符串 (如: 2025-11-10 14:10:38)
 */
export function formatDateTime(dateString: string | null | undefined): string {
  if (!dateString) {
    return '-'
  }

  try {
    // 解析ISO 8601格式时间字符串
    const date = new Date(dateString)

    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return dateString
    }

    // 格式化为本地时间: YYYY-MM-DD HH:mm:ss
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const hours = String(date.getHours()).padStart(2, '0')
    const minutes = String(date.getMinutes()).padStart(2, '0')
    const seconds = String(date.getSeconds()).padStart(2, '0')

    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
  } catch (error) {
    console.error('Failed to format date:', dateString, error)
    return dateString
  }
}

/**
 * 格式化日期(仅日期部分)
 * @param dateString ISO 8601格式的时间字符串
 * @returns 格式化后的日期字符串 (如: 2025-11-10)
 */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) {
    return '-'
  }

  try {
    const date = new Date(dateString)

    if (isNaN(date.getTime())) {
      return dateString
    }

    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')

    return `${year}-${month}-${day}`
  } catch (error) {
    console.error('Failed to format date:', dateString, error)
    return dateString
  }
}

/**
 * 格式化金额，整数不显示小数部分
 * @param amount 金额数字或字符串
 * @returns 格式化后的金额字符串 (如: 100 或 100.50)
 */
export function formatAmount(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined || amount === '') {
    return '0'
  }

  const num = typeof amount === 'string' ? parseFloat(amount) : amount

  if (isNaN(num)) {
    return '0'
  }

  // 如果是整数，不显示小数点
  if (Number.isInteger(num)) {
    return num.toString()
  }

  // 如果有小数，保留两位小数
  return num.toFixed(2)
}
