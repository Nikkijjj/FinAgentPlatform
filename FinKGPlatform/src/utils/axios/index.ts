import axios from 'axios';

function resolveBaseURL(): string {
  // 可通过环境变量显式指定（推荐生产使用）
  const envBase = (import.meta as any)?.env?.VITE_BACKEND_BASE_URL;
  if (typeof envBase === 'string' && envBase.trim()) {
    return envBase.trim();
  }

  // 开发环境依赖 Vite proxy，保持空 baseURL
  if (!(import.meta as any)?.env?.PROD) return '';

  // 生产/预览环境：若前端运行在 8000，而后端 Flask 运行在 5000，
  // 则自动回退到同主机 5000，避免 /old-api 被静态服务器 404。
  try {
    const { protocol, hostname, port } = window.location;
    if (String(port) === '8000') {
      return `${protocol}//${hostname}:5000`;
    }
  } catch {
    // ignore
  }
  return '';
}

const request = axios.create({
  baseURL: resolveBaseURL(),
  timeout: 120000,
});

export default request;
