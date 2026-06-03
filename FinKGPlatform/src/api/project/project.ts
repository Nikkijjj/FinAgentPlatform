// src/api/project/project.ts
import { requestAPI } from '@/api/response';

export interface ProjectItem {
  id: string;
  project_name: string;
  project_desc: string;
  project_status: number | string;
  stock_num: string;
  create_time: string;
  creator: string;
}

export interface GetProjectListParams {
  creator: string;
  view_scope?: string;
  keyword?: string;
  search_type?: string;
  start_date?: string;
  end_date?: string;
  page: number;
  page_size: number;
}

export async function getProjectList(params: GetProjectListParams) {
  return (await requestAPI('/old-api/getProjectList', 'post', null, params)) as {
    status: number;
    projectList: ProjectItem[];
    total: number;
  };
}

export async function deleteProject(project_id: string) {
  return (await requestAPI('/old-api/deleteProject', 'post', null, { project_id })) as {
    status: number;
    msg: string;
  };
}

export interface AddProjectParams {
  project_name: string;
  project_desc: string;
  creator: string;
}

export async function addProject(params: AddProjectParams) {
  return (await requestAPI('/old-api/addProject', 'post', null, params)) as {
    status: number;
    msg: string;
    project_id: string;
  };
}

export interface EditProjectParams {
  project_id: string;
  project_name: string;
  project_desc: string;
}

export async function editProject(params: EditProjectParams) {
  return (await requestAPI('/old-api/editProject', 'post', null, params)) as {
    status: number;
    msg: string;
    project_id: string;
  };
}
