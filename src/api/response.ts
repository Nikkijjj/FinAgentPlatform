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
