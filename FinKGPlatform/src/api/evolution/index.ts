import request from '@/utils/axios';

async function callEvolutionApi(config: {
  url: string;
  method: 'get' | 'post';
  params?: Record<string, unknown>;
  data?: Record<string, unknown>;
}) {
  try {
    const res = await request.request({
      url: config.url,
      method: config.method,
      params: config.params,
      data: config.data,
      timeout: 300000,
    });
    return res?.data ?? null;
  } catch {
    return null;
  }
}

export function injectMockEvent(data: {
  project_id: string;
  title: string;
  content: string;
  url?: string;
  source?: string;
}) {
  return callEvolutionApi({
    url: '/old-api/evolution/inject_mock',
    method: 'post',
    data
  });
}

export function getEvolutionStatus(project_id: string) {
  return callEvolutionApi({
    url: '/old-api/evolution/status',
    method: 'get',
    params: { project_id }
  });
}

export function ackEvolutionNotification(log_id: number) {
  return callEvolutionApi({
    url: '/old-api/evolution/ack',
    method: 'post',
    data: { log_id }
  });
}
