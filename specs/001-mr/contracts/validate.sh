#!/bin/bash

# OpenAPI契约验证脚本
# 用途: 验证所有契约文件的语法正确性和规范一致性

echo "============================================"
echo "MR游戏运营管理系统 - OpenAPI契约验证"
echo "============================================"
echo ""

# 检查依赖工具
echo "1. 检查依赖工具..."

if ! command -v npx &> /dev/null; then
    echo "错误: 未安装 npx，请先安装 Node.js"
    exit 1
fi

echo "✓ npx 已安装"
echo ""

# 验证主契约文件
echo "2. 验证主契约文件（openapi.yaml）..."
npx @redocly/cli lint openapi.yaml --skip-rule=no-invalid-media-type-examples

if [ $? -eq 0 ]; then
    echo "✓ openapi.yaml 验证通过"
else
    echo "✗ openapi.yaml 验证失败"
    exit 1
fi
echo ""

# 统计接口数量
echo "3. 统计API接口数量..."
echo ""

auth_count=$(grep -c "operationId:" auth.yaml)
operator_count=$(grep -c "operationId:" operator.yaml)
admin_count=$(grep -c "operationId:" admin.yaml)
finance_count=$(grep -c "operationId:" finance.yaml)
total_count=$((auth_count + operator_count + admin_count + finance_count))

echo "├── 授权接口 (auth.yaml):      $auth_count 个"
echo "├── 运营商接口 (operator.yaml): $operator_count 个"
echo "├── 管理员接口 (admin.yaml):    $admin_count 个"
echo "├── 财务接口 (finance.yaml):    $finance_count 个"
echo "└── 总计:                       $total_count 个"
echo ""

# 统计代码行数
echo "4. 统计代码行数..."
echo ""

openapi_lines=$(wc -l < openapi.yaml)
auth_lines=$(wc -l < auth.yaml)
operator_lines=$(wc -l < operator.yaml)
admin_lines=$(wc -l < admin.yaml)
finance_lines=$(wc -l < finance.yaml)
total_lines=$((openapi_lines + auth_lines + operator_lines + admin_lines + finance_lines))

echo "├── openapi.yaml:  $openapi_lines 行"
echo "├── auth.yaml:     $auth_lines 行"
echo "├── operator.yaml: $operator_lines 行"
echo "├── admin.yaml:    $admin_lines 行"
echo "├── finance.yaml:  $finance_lines 行"
echo "└── 总计:          $total_lines 行"
echo ""

# 验证Schema引用完整性
echo "5. 验证Schema引用完整性..."

# 检查是否所有$ref引用都能找到对应定义
missing_refs=0

for file in auth.yaml operator.yaml admin.yaml finance.yaml; do
    refs=$(grep -o '\$ref.*' $file | sed "s/\$ref: '//g" | sed "s/'//g")

    for ref in $refs; do
        # 跳过外部引用（以../openapi.yaml开头）
        if [[ $ref == ../openapi.yaml* ]]; then
            continue
        fi

        # 检查本地引用
        if ! grep -q "^  $ref:" $file 2>/dev/null; then
            echo "警告: $file 中引用 $ref 可能不存在"
            missing_refs=$((missing_refs + 1))
        fi
    done
done

if [ $missing_refs -eq 0 ]; then
    echo "✓ Schema引用验证通过"
else
    echo "⚠ 发现 $missing_refs 个可能缺失的Schema引用"
fi
echo ""

# 生成文档预览
echo "6. 生成HTML文档预览..."

if npx @redocly/cli build-docs openapi.yaml -o api-docs.html &> /dev/null; then
    echo "✓ HTML文档已生成: api-docs.html"
    echo "  打开方式: 在浏览器中打开 api-docs.html"
else
    echo "✗ HTML文档生成失败"
fi
echo ""

# 验证完成
echo "============================================"
echo "验证完成！"
echo "============================================"
echo ""
echo "接口总数: $total_count 个"
echo "代码总行数: $total_lines 行"
echo ""
echo "下一步操作:"
echo "1. 查看HTML文档: 在浏览器中打开 api-docs.html"
echo "2. 导入Swagger Editor: https://editor.swagger.io/"
echo "3. 生成客户端代码: npx @openapitools/openapi-generator-cli generate"
echo "4. 生成服务端代码: npx @openapitools/openapi-generator-cli generate"
echo ""
