// 获取用户本地时间
export function getLocalDate(): string {
  const date = new Date();
  return date.getFullYear() + '-' + (date.getMonth() + 1) + '-' + date.getDate();
}

// 时间戳转字符串
export function parseStr(timeStamp: number | null): string {
  if (!timeStamp) return '';
  const date = new Date(timeStamp);
  return (
    date.getFullYear() +
    '-' +
    (date.getMonth() + 1) +
    '-' +
    date.getDate() +
    ' ' +
    date.getHours() +
    ':' +
    date.getMinutes() +
    ':' +
    date.getSeconds()
  );
}

// 字符串转时间戳
export function parseTime(timeString: string | null): number | null {
  if (!timeString) return null;
  const [date, time] = timeString.split(' ');
  const [year, month, day] = date.split('-');
  const [hour, min, sec] = time.split(':');
  const result = new Date(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(min),
    Number(sec)
  );
  return result.getTime();
}

// 时间格式: "2025-11-20 22:42"
