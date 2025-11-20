// 获取用户本地时间
export function getLocalDate(): string {
  const date = new Date();
  return date.getFullYear() + '-' + (date.getMonth() + 1) + '-' + date.getDate();
}

// 时间戳转字符串
export function parseStr(timeStamp: number | null): string {
  if (!timeStamp) return '';
  const date = new Date(timeStamp);
  return date.getFullYear() + '-' + (date.getMonth() + 1) + '-' + date.getDate();
}

// 字符串转时间戳
export function parseTime(timeString: string | null): number | null {
  if (!timeString) return null;
  const [year, month, day] = timeString.split('-');
  const date = new Date(Number(year), Number(month) - 1, Number(day));
  return date.getTime();
}
