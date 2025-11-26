import request from '@/utils/axios';

export interface responseBody {
  code: number;
  data: any;
  msg: string;
}

export const badResponse = {
  code: 1,
  data: null,
  msg: '网络异常，请重试',
};

export function genRequestHeaders(token: string) {
  return {
    Authorization: token,
  };
}

export async function requestAPI(url, method, headers, body) {
  try {
    const response = await request.request({
      url: url,
      method: method,
      headers: headers,
      data: body,
      timeout: 60000,
    });
    return response.data ?? badResponse;
  } catch (error) {
    console.log(error);
    return badResponse;
  }
}
