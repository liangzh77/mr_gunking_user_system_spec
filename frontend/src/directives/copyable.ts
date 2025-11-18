/**
 * v-copyable 指令
 * 为表格单元格添加点击复制功能
 *
 * 使用方法:
 * <el-table v-copyable>
 *   ...
 * </el-table>
 */

import type { Directive, DirectiveBinding } from 'vue'
import { ElMessage } from 'element-plus'
import { copyToClipboard, extractTextFromElement } from '@/utils/clipboard'

interface CopyableElement extends HTMLElement {
  _copyableCleanup?: () => void
}

const copyableDirective: Directive = {
  mounted(el: CopyableElement, binding: DirectiveBinding) {
    // 检查是否是 el-table 元素
    const table = el.classList.contains('el-table') ? el : el.querySelector('.el-table')
    if (!table) {
      console.warn('v-copyable directive should be used on el-table element')
      return
    }

    // 点击处理函数
    const handleCellClick = async (event: Event) => {
      const target = event.target as HTMLElement

      // 查找最近的 td 元素
      let cell = target.closest('td.el-table__cell') as HTMLElement | null
      if (!cell) return

      // 排除操作列（包含按钮的列）
      if (cell.querySelector('button, .el-button, a')) {
        return
      }

      // 排除复选框列
      if (cell.classList.contains('el-table-column--selection')) {
        return
      }

      // 提取文本内容
      const text = extractTextFromElement(cell)
      if (!text) return

      // 复制到剪贴板
      const success = await copyToClipboard(text)

      if (success) {
        // 显示成功提示
        ElMessage.success({
          message: '已复制',
          duration: 1000,
          showClose: false,
        })

        // 添加视觉反馈
        cell.style.backgroundColor = '#e6f7ff'
        cell.style.transition = 'background-color 0.3s'

        setTimeout(() => {
          cell!.style.backgroundColor = ''
        }, 300)
      }
    }

    // 添加事件监听
    table.addEventListener('click', handleCellClick)

    // 保存清理函数
    el._copyableCleanup = () => {
      table.removeEventListener('click', handleCellClick)
    }

    // 添加鼠标悬停样式提示
    const style = document.createElement('style')
    style.textContent = `
      .el-table td.el-table__cell:not(.el-table-column--selection):not(:has(button)):not(:has(.el-button)):not(:has(a)) {
        cursor: copy;
      }
    `
    document.head.appendChild(style)
  },

  unmounted(el: CopyableElement) {
    // 清理事件监听
    if (el._copyableCleanup) {
      el._copyableCleanup()
      delete el._copyableCleanup
    }
  }
}

export default copyableDirective
