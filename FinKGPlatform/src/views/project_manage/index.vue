<template>
  <div class="project-manage-page">
    <n-card class="project-card" :bordered="false">
      <div class="project-header">
        <div class="header-left">
          <div class="header-title">
            <h2>图谱构建空间</h2>
            <p>管理与查看您的金融事件图谱构建空间</p>
          </div>
          <n-tag type="info" size="small" round> 共 {{ totalProjects }} 个项目 </n-tag>
        </div>
        <div class="header-right">
          <n-button type="primary" @click="openAddDialog"> 新建项目 </n-button>
        </div>
      </div>

      <!-- 管理员高级搜索区 -->
      <div v-if="currUserName === 'admin'" class="admin-search-bar">
        <n-space align="center" :size="16">
          <n-input-group>
            <n-select
              v-model:value="searchType"
              :options="searchOptions"
              style="width: 120px"
              placeholder="搜索字段"
            />
            <n-input
              v-model:value="searchKeyword"
              placeholder="请输入搜索内容..."
              clearable
              @keyup.enter="handleSearch"
              @clear="handleSearch"
              style="width: 240px"
            />
          </n-input-group>
          
          <n-date-picker
            v-model:value="dateRange"
            type="daterange"
            clearable
            placeholder="选择创建时间范围"
            @update:value="handleSearch"
            style="width: 280px"
          />

          <n-button type="primary" @click="handleSearch">
            <template #icon>
              <n-icon><SearchOutline /></n-icon>
            </template>
            搜 索
          </n-button>
        </n-space>
      </div>

      <n-spin :show="loadingProjects">
        <div class="cards-wrapper">
          <!-- 先渲染所有项目卡片 -->
          <div v-for="item in graphProjectList" :key="item.id" class="project-item">
            <n-card
              class="project-item-card"
              :bordered="false"
              @click="performGraphProject(item.id)"
            >
              <div class="item-header">
                <div class="item-title">
                  <div class="item-icon">
                    <n-icon size="18">
                      <FolderOpenOutline />
                    </n-icon>
                  </div>
                  <div class="item-title-text">
                    <div class="name">
                      <n-ellipsis style="max-width: 180px">
                        {{ item.name || '-' }}
                      </n-ellipsis>
                    </div>
                    <div class="meta">
                      <span>项目ID：{{ item.id }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div class="item-body">
                <div class="row">
                  <span class="label">创建时间</span>
                  <span class="value">
                    {{ item.create_time || '无' }}
                  </span>
                </div>
                <div class="row" v-if="currUserName === 'admin'">
                  <span class="label">创建者</span>
                  <span class="value">
                    {{ item.creator || '无' }}
                  </span>
                </div>
                <div class="row desc">
                  <span class="label">项目描述</span>
                  <n-ellipsis style="max-width: 100%">
                    {{ item.description || '无' }}
                  </n-ellipsis>
                </div>
              </div>

              <div class="item-footer" @click.stop>
                <n-button text type="warning" @click="openEditDialog(item)"> 编辑 </n-button>
                <n-divider vertical />
                <n-popconfirm
                  positive-text="确定"
                  negative-text="取消"
                  @positive-click="deleteGraphProject(item.id)"
                >
                  <template #trigger>
                    <n-button text type="error"> 删除 </n-button>
                  </template>
                  确定删除此图谱构建空间？
                </n-popconfirm>
              </div>
            </n-card>
          </div>

          <!-- 新建卡片 - 只在最后一页显示 -->
          <div v-if="shouldShowAddCard" class="project-item add-card" @click="openAddDialog">
            <div class="add-inner">
              <div class="add-icon">
                <n-icon size="40">
                  <AddOutline />
                </n-icon>
              </div>
              <div class="add-text">点击创建新的图谱构建空间</div>
            </div>
          </div>
        </div>

        <div class="pagination-wrapper" v-if="totalProjects > 0">
          <n-pagination
            v-model:page="currentPage"
            v-model:page-size="pageSize"
            :item-count="totalProjects"
            :page-sizes="[8, 16, 24, 32]"
            show-size-picker
            show-quick-jumper
            :display-order="['size-picker', 'pages', 'quick-jumper']"
            @update:page="handleCurrentChange"
            @update:page-size="handleSizeChange"
          />
        </div>
      </n-spin>
    </n-card>

    <!-- 新建项目 -->
    <n-modal
      v-model:show="addGraphProjectDialogVisible"
      preset="card"
      title="新建图谱构建空间"
      style="width: 520px"
      :bordered="false"
      :mask-closable="false"
    >
      <n-form :model="newGraphProjectForm" label-placement="left" label-width="80">
        <n-form-item label="项目名称">
          <n-input v-model:value="newGraphProjectForm.name" />
        </n-form-item>
        <n-form-item label="项目描述">
          <n-input
            v-model:value="newGraphProjectForm.description"
            type="textarea"
            :rows="4"
            placeholder="请输入图谱构建空间描述"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="dialog-footer">
          <n-button @click="addGraphProjectDialogVisible = false">取消</n-button>
          <n-button type="primary" :loading="loadingNewProject" @click="addGraphProject">
            确认
          </n-button>
        </div>
      </template>
    </n-modal>

    <!-- 修改项目 -->
    <n-modal
      v-model:show="editGraphProjectDialogVisible"
      preset="card"
      title="修改图谱构建空间"
      style="width: 520px"
      :bordered="false"
      :mask-closable="false"
    >
      <n-form :model="editGraphProjectForm" label-placement="left" label-width="80">
        <n-form-item label="项目名称">
          <n-input v-model:value="editGraphProjectForm.name" />
        </n-form-item>
        <n-form-item label="项目描述">
          <n-input v-model:value="editGraphProjectForm.description" type="textarea" :rows="4" />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="dialog-footer">
          <n-button @click="editGraphProjectDialogVisible = false"> 取消 </n-button>
          <n-button type="primary" :loading="loadingEditProject" @click="submitEditGraphProject">
            保存
          </n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { useRouter } from 'vue-router';
  import { useMessage } from 'naive-ui';
  import { useUserStore } from '@/store/modules/user';
  import {
    getProjectList,
    deleteProject,
    addProject,
    editProject,
    type ProjectItem,
  } from '@/api/project/project';
  import { AddOutline, FolderOpenOutline, SearchOutline } from '@vicons/ionicons5';

  interface GraphProjectView {
    id: string;
    name: string;
    description: string;
    status: string;
    stock_num: string;
    create_time: string;
    creator: string;
  }

  const router = useRouter();
  const message = useMessage();
  const userStore = useUserStore();

  const currUserName = ref(userStore.getUsername || '');

  // 项目列表
  const graphProjectList = ref<GraphProjectView[]>([]);
  const loadingProjects = ref(false);

  // 新增
  const newGraphProjectForm = ref<GraphProjectView>({
    id: '',
    name: '',
    description: '',
    status: '0',
    stock_num: '',
    create_time: '',
    creator: '',
  });
  const loadingNewProject = ref(false);
  const addGraphProjectDialogVisible = ref(false);

  // 是否显示新建卡片 - 只在最后一页显示
  const shouldShowAddCard = computed(() => {
    // 计算总页数
    const totalPages = Math.ceil(totalProjects.value / pageSize.value);

    // 如果是最后一页（或没有数据时），显示新建卡片
    return currentPage.value >= totalPages;
  });

  // 编辑
  const editGraphProjectForm = ref<GraphProjectView>({
    id: '',
    name: '',
    description: '',
    status: '0',
    stock_num: '',
    create_time: '',
    creator: '',
  });
  const loadingEditProject = ref(false);
  const editGraphProjectDialogVisible = ref(false);

  // 删除
  const loadingDeleteProject = ref(false);

  // 分页与高级搜索
  const currentPage = ref(1);
  const pageSize = ref(8);
  const totalProjects = ref(0);
  const searchKeyword = ref('');
  const searchType = ref('all');
  const dateRange = ref<[number, number] | null>(null);

  const searchOptions = [
    { label: '全文搜索', value: 'all' },
    { label: '项目名称', value: 'project_name' },
    { label: '项目ID', value: 'id' },
    { label: '创建者', value: 'creator' },
    { label: '项目描述', value: 'project_desc' },
  ];

  const handleSearch = () => {
    currentPage.value = 1;
    fetchProjects();
  };

  onMounted(async () => {
    if (!currUserName.value) {
      currUserName.value = userStore.getUsername || '';
    }
    await fetchProjects();
  });

  const openAddDialog = () => {
    newGraphProjectForm.value = {
      id: '',
      name: '',
      description: '',
      status: '0',
      stock_num: '',
      create_time: '',
      creator: currUserName.value,
    };
    addGraphProjectDialogVisible.value = true;
  };

  const openEditDialog = (item: GraphProjectView) => {
    editGraphProjectForm.value = { ...item };
    editGraphProjectDialogVisible.value = true;
  };

  // 获取项目列表
  const fetchProjects = async () => {
    if (loadingProjects.value) return;
    loadingProjects.value = true;
    try {
      const payload: any = {
        creator: currUserName.value || 'admin',
        view_scope: 'mine',
        page: currentPage.value,
        page_size: pageSize.value,
      };
      if (currUserName.value === 'admin') {
        if (searchKeyword.value) {
          payload.keyword = searchKeyword.value.trim();
          payload.search_type = searchType.value;
        }
        if (dateRange.value && dateRange.value.length === 2) {
          // 格式化时间为 YYYY-MM-DD
          const formatStr = (ts: number) => {
            const d = new Date(ts);
            const m = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            return `${d.getFullYear()}-${m}-${day}`;
          };
          payload.start_date = formatStr(dateRange.value[0]);
          payload.end_date = formatStr(dateRange.value[1]);
        }
      }
      const res = await getProjectList(payload);
      if (res.status !== 200) {
        message.error('获取项目列表失败');
        loadingProjects.value = false;
        return;
      }
      const dataList = res.projectList || [];
      graphProjectList.value = dataList.map((item: ProjectItem) => ({
        id: item.id,
        name: item.project_name,
        description: item.project_desc || '',
        status: String(item.project_status ?? '0'),
        stock_num: item.stock_num ?? '',
        create_time: item.create_time,
        creator: item.creator || '',
      }));
      totalProjects.value = res.total || dataList.length;
    } catch (error: any) {
      message.error(error?.message || '获取项目列表失败');
      console.error('fetchProjects error:', error);
    } finally {
      loadingProjects.value = false;
    }
  };

  // 进入项目流程
  const performGraphProject = (id: string) => {
    message.success('项目流程跳转成功');
    router.push({
      path: `/project-manage/extract/${id}`,
    });
  };

  // 删除项目
  const deleteGraphProject = async (id: string) => {
    if (loadingDeleteProject.value) return;
    loadingDeleteProject.value = true;
    try {
      const res = await deleteProject(id);
      if (res.status === 200) {
        message.success('删除项目成功');
        graphProjectList.value = graphProjectList.value.filter((item) => item.id !== id);
        totalProjects.value = Math.max(0, totalProjects.value - 1);
        if (graphProjectList.value.length === 0 && currentPage.value > 1) {
          currentPage.value -= 1;
        }
        await fetchProjects();
      } else {
        message.error(res.msg || '删除项目失败');
      }
    } catch (error: any) {
      message.error(error?.message || '删除项目失败');
      console.error('deleteGraphProject error:', error);
    } finally {
      loadingDeleteProject.value = false;
    }
  };

  // 新增项目
  const addGraphProject = async () => {
    if (loadingNewProject.value) return;
    const name = newGraphProjectForm.value.name?.trim();
    const desc = newGraphProjectForm.value.description?.trim();
    if (!name || !desc) {
      message.warning('项目名称和项目描述均不能为空');
      return;
    }
    loadingNewProject.value = true;
    try {
      const res = await addProject({
        project_name: name,
        project_desc: desc,
        creator: currUserName.value || 'admin',
      });
      if (res.status === 200) {
        message.success('新增项目成功');
        addGraphProjectDialogVisible.value = false;
        await fetchProjects();
      } else {
        message.error(res.msg || '新增项目失败');
      }
    } catch (error: any) {
      message.error(error?.message || '新增项目失败');
      console.error('addGraphProject error:', error);
    } finally {
      loadingNewProject.value = false;
    }
  };

  // 保存编辑
  const submitEditGraphProject = async () => {
    if (loadingEditProject.value) return;
    const name = editGraphProjectForm.value.name?.trim();
    const desc = editGraphProjectForm.value.description?.trim();
    if (!name || !desc) {
      message.warning('项目名称和项目描述均不能为空');
      return;
    }
    loadingEditProject.value = true;
    try {
      const res = await editProject({
        project_id: editGraphProjectForm.value.id,
        project_name: name,
        project_desc: desc,
      });
      if (res.status === 200) {
        message.success('修改项目成功');
        editGraphProjectDialogVisible.value = false;
        await fetchProjects();
      } else {
        message.error(res.msg || '修改项目失败');
      }
    } catch (error: any) {
      message.error(error?.message || '修改项目失败');
      console.error('submitEditGraphProject error:', error);
    } finally {
      loadingEditProject.value = false;
    }
  };

  // 分页
  const handleSizeChange = (val: number) => {
    pageSize.value = val;
    currentPage.value = 1;
    fetchProjects();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCurrentChange = (val: number) => {
    currentPage.value = val;
    fetchProjects();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };
</script>

<style scoped lang="scss">
  .project-manage-page {
    min-height: 100%;
    padding: 20px;
    background: linear-gradient(135deg, #f5f7fb 0%, #edf5ff 50%, #f5fbff 100%);
    box-sizing: border-box;
  }

  .admin-search-bar {
    margin-bottom: 20px;
    padding: 16px 20px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  }

  .project-card {
    border-radius: 18px;
    box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
    border: none;
  }

  .project-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;

      .header-title {
        h2 {
          margin: 0;
          font-size: 22px;
          font-weight: 700;
          color: #0f172a;
        }
        p {
          margin: 4px 0 0;
          font-size: 13px;
          color: #6b7280;
        }
      }
    }
  }

  .cards-wrapper {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 20px;
    padding: 16px 8px 24px;
  }

  .project-item {
    min-height: 100%;
  }

  .project-item-card {
    height: 100%;
    min-height: 210px;
    border-radius: 14px;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.25s ease;
    border: 1px solid rgba(229, 231, 235, 0.9);
    padding: 12px 14px 10px;

    &:hover {
      transform: translateY(-4px);
      box-shadow: 0 14px 32px rgba(15, 23, 42, 0.14);
      border-color: #bfdbfe;
    }
  }

  .item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 8px;
    border-bottom: 1px solid #e5e7eb;

    .item-title {
      display: flex;
      align-items: center;
      gap: 10px;

      .item-icon {
        width: 32px;
        height: 32px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #e0f2fe, #dbeafe);
        color: #2563eb;
      }

      .item-title-text {
        .name {
          font-size: 15px;
          font-weight: 600;
          color: #111827;
        }
        .meta {
          margin-top: 2px;
          font-size: 11px;
          color: #9ca3af;
        }
      }
    }
  }

  .item-body {
    padding: 10px 0 6px;
    font-size: 13px;
    color: #4b5563;

    .row {
      display: flex;
      margin-bottom: 8px;

      &.desc {
        align-items: flex-start;
      }

      .label {
        width: 70px;
        color: #9ca3af;
        flex-shrink: 0;
      }
      .value {
        flex: 1;
        word-break: break-all;
      }
    }
  }

  .item-footer {
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed #e5e7eb;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
  }

  .add-card {
    .add-inner {
      border-radius: 14px;
      border: 1px dashed #bfdbfe;
      height: 100%;
      min-height: 210px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.25s ease;
      background: rgba(239, 246, 255, 0.6);

      .add-icon {
        margin-bottom: 8px;
        color: #1d4ed8;
      }

      .add-text {
        font-size: 13px;
        color: #4b5563;
      }

      &:hover {
        background: rgba(219, 234, 254, 0.9);
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 10px 24px rgba(37, 99, 235, 0.25);
      }
    }
  }

  .pagination-wrapper {
    margin-top: 20px;
    display: flex;
    justify-content: center;
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }

  @media (max-width: 768px) {
    .project-manage-page {
      padding: 12px;
    }

    .project-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }

    .cards-wrapper {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 480px) {
    .cards-wrapper {
      grid-template-columns: 1fr;
    }
  }
</style>
