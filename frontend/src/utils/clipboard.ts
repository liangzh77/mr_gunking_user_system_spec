/**
 * 复制文本到剪贴板
 * @param text 要复制的文本
 * @returns Promise<boolean> 是否复制成功
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    // 优先使用 Clipboard API
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
      return true
    }

    // 降级方案：使用 document.execCommand
    const textArea = document.createElement('textarea')
    textArea.value = text
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()

    const result = document.execCommand('copy')
    document.body.removeChild(textArea)

    return result
  } catch (error) {
    console.error('复制失败:', error)
    return false
  }
}

/**
 * 从 DOM 元素中提取纯文本内容
 * @param element DOM 元素
 * @returns 纯文本内容
 */
export function extractTextFromElement(element: HTMLElement): string {
  // 移除所有图标和按钮等非文本内容
  const clone = element.cloneNode(true) as HTMLElement

  // 移除图标
  clone.querySelectorAll('.el-icon, i').forEach(icon => icon.remove())

  // 移除按钮
  clone.querySelectorAll('button, .el-button').forEach(btn => btn.remove())

  // 获取纯文本
  return clone.textContent?.trim() || ''
}
