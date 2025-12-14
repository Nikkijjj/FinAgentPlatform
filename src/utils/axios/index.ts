import axios from 'axios';

const request = axios.create({
  baseURL: '',
  timeout: 60000,
});

export default request;
