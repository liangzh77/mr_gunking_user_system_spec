import * as fs from 'fs';
import * as path from 'path';

/**
 * 生成最小有效的PNG测试图片
 * 这是一个1x1像素的透明PNG图片
 */
export function createTestImage(outputPath: string): string {
  // 最小有效的PNG文件 (1x1 透明像素)
  const pngBuffer = Buffer.from([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, // PNG signature
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, // IHDR chunk
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, // 1x1 dimensions
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, // RGBA, CRC
    0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41, // IDAT chunk
    0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00, // compressed data
    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00, // CRC
    0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE, // IEND chunk
    0x42, 0x60, 0x82                                 // CRC
  ]);

  // 确保目录存在
  const dir = path.dirname(outputPath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }

  // 写入文件
  fs.writeFileSync(outputPath, pngBuffer);

  console.log(`✅ Test image created: ${outputPath}`);
  return outputPath;
}

/**
 * 删除测试图片
 */
export function deleteTestImage(imagePath: string): void {
  if (fs.existsSync(imagePath)) {
    fs.unlinkSync(imagePath);
    console.log(`🗑️  Test image deleted: ${imagePath}`);
  }
}

/**
 * 获取测试图片的默认路径
 */
export function getTestImagePath(filename: string = 'e2e-test-voucher.png'): string {
  return path.resolve(__dirname, '..', '..', 'test-artifacts', filename);
}
