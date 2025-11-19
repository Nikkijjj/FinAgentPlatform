// 获取用户本地时间
export function getLocalDate(): string {
  const date = new Date();
  return date.getFullYear() + '-' + (date.getMonth() + 1) + '-' + date.getDate();
}
