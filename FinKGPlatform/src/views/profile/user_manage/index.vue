<!-- src/views/profile/user_manage/index.vue -->
<script setup lang="ts">
  import { onMounted, ref, computed, h, watch } from 'vue';
  import {
    getAllUsers,
    createUser,
    updateUser,
    deleteUser,
    batchDeleteUsers,
    type UserType,
    type CreateUserParams,
    type UpdateUserParams,
  } from '@/api/user/user';
  import {
    useMessage,
    useDialog,
    NTag,
    NIcon,
    NButton,
    NSpace,
    NInput,
    NModal,
    NForm,
    NFormItem,
    NPopconfirm,
    NDataTable,
    NCard,
    NEllipsis,
    NEmpty,
    NInputGroup,
  } from 'naive-ui';
  import {
    PersonOutline,
    AddOutline,
    TrashOutline,
    CreateOutline,
    SearchOutline,
    RefreshOutline,
    MailOutline,
    TimeOutline,
  } from '@vicons/ionicons5';
  import type { DataTableColumns } from 'naive-ui';

  import { useRouter } from 'vue-router';
  import { useUserStore } from '@/store/modules/user';

  const userStore = useUserStore();
  const router = useRouter();
  const message = useMessage();
  const dialog = useDialog();

  // ==================== 数据状态 ====================
  const allUsers = ref<UserType[]>([]); // 存储所有用户数据
  const filteredUsers = ref<UserType[]>([]); // 存储过滤后的用户数据
  const loading = ref(false);
  const selectedRowKeys = ref<number[]>([]);

  // 分页参数
  const pagination = ref({
    page: 1,
    pageSize: 10,
    total: 0,
    pageCount: 0,
  });

  // 搜索参数
  const searchKeyword = ref('');
  const searchLoading = ref(false); // 搜索加载状态

  // 弹窗控制
  const showModal = ref(false);
  const modalType = ref<'add' | 'edit'>('add');
  const currentUser = ref<UserType | null>(null);
  const formLoading = ref(false);

  // 表单数据
  const formData = ref<CreateUserParams & { id?: number }>({
    username: '',
    password: '',
    email: '',
  });

  // 表单引用
  const formRef = ref<any>(null);

  // ==================== 表单验证规则 ====================
  const formRules = {
    username: {
      required: true,
      message: '请输入用户名',
      trigger: ['blur', 'input'],
    },
    password: [
      {
        required: true,
        message: '请输入密码',
        trigger: ['blur', 'input'],
        validator: (_rule: any, value: string) => {
          if (modalType.value === 'add') {
            return !!value && value.length >= 6;
          }
          // 编辑模式下，密码可选
          return true;
        },
      },
      {
        min: 6,
        message: '密码长度不能小于6位',
        trigger: ['blur', 'input'],
      },
    ],
    email: [
      {
        type: 'email',
        message: '请输入正确的邮箱格式',
        trigger: ['blur', 'input'],
      },
    ],
  };

  // ==================== 计算属性 ====================
  // 计算当前页要显示的数据（使用过滤后的数据）
  const currentPageData = computed(() => {
    const sourceData = filteredUsers.value.length > 0 ? filteredUsers.value : allUsers.value;
    const start = (pagination.value.page - 1) * pagination.value.pageSize;
    const end = start + pagination.value.pageSize;
    return sourceData.slice(start, end);
  });

  // 当前显示的数据总数
  const currentTotal = computed(() => {
    return filteredUsers.value.length > 0 ? filteredUsers.value.length : allUsers.value.length;
  });

  // 表格列定义
  const columns = computed<DataTableColumns<UserType>>(() => [
    {
      type: 'selection',
      width: 50,
      fixed: 'left',
    },
    {
      title: '用户ID',
      key: 'id',
      width: 80,
      align: 'center',
      fixed: 'left',
      render(row) {
        return h(
          'span',
          {
            style: {
              fontWeight: '500',
              color: '#165dff',
            },
          },
          row.id
        );
      },
    },
    {
      title: '用户名',
      key: 'user_name',
      width: 150,
      fixed: 'left',
      render(row) {
        return h(
          'div',
          {
            style: {
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            },
          },
          [
            h(
              'div',
              {
                style: {
                  width: '32px',
                  height: '32px',
                  borderRadius: '6px',
                  background: 'linear-gradient(135deg, #165dff 0%, #4a86ff 100%)',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '14px',
                  fontWeight: '600',
                },
              },
              (row.user_name || '').charAt(0).toUpperCase()
            ),
            h(
              'span',
              {
                style: {
                  fontWeight: '500',
                },
              },
              row.user_name
            ),
          ]
        );
      },
    },
    {
      title: '邮箱',
      key: 'email',
      width: 220,
      render(row) {
        return h(
          'div',
          {
            style: {
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            },
          },
          [
            h(NIcon, { size: 16, color: '#64748b' }, { default: () => h(MailOutline) }),
            h(NEllipsis, { style: 'max-width: 180px' }, { default: () => row.email || '-' }),
          ]
        );
      },
    },
    {
      title: '创建时间',
      key: 'create_time',
      width: 180,
      align: 'center',
      render(row) {
        return h(
          'div',
          {
            style: {
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              fontSize: '13px',
              color: '#475569',
            },
          },
          [
            h(NIcon, { size: 14, color: '#94a3b8' }, { default: () => h(TimeOutline) }),
            h('span', {}, row.create_time || '-'),
          ]
        );
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      align: 'center',
      render(row) {
        return h(
          NSpace,
          { justify: 'center', size: 'small' },
          {
            default: () => [
              h(
                NButton,
                {
                  size: 'tiny',
                  type: 'primary',
                  secondary: true,
                  onClick: (e: Event) => {
                    e.stopPropagation();
                    openEditModal(row);
                  },
                },
                {
                  icon: () => h(NIcon, null, { default: () => h(CreateOutline) }),
                }
              ),
              h(
                NPopconfirm,
                {
                  onPositiveClick: () => handleDelete(row.id),
                  positiveText: '确定',
                  negativeText: '取消',
                },
                {
                  trigger: () =>
                    h(
                      NButton,
                      {
                        size: 'tiny',
                        type: 'error',
                        secondary: true,
                        onClick: (e: Event) => e.stopPropagation(),
                      },
                      {
                        icon: () => h(NIcon, null, { default: () => h(TrashOutline) }),
                      }
                    ),
                  default: () => '确定删除该用户吗？',
                }
              ),
            ],
          }
        );
      },
    },
  ]);

  // ==================== 数据加载 ====================
  // 加载所有用户数据
  async function loadAllUsers() {
    loading.value = true;
    try {
      console.log('开始加载所有用户数据');

      const response = await getAllUsers(); // 不传搜索参数，获取所有用户

      console.log('API响应:', response);

      if (response.status === 200) {
        if (response.data && Array.isArray(response.data.list)) {
          // 存储所有用户数据
          allUsers.value = response.data.list.map((user) => ({
            ...user,
            user_name: user.user_name || user.username,
          }));

          // 清空过滤结果
          filteredUsers.value = [];

          // 更新分页信息
          updatePagination();

          console.log('数据处理完成:', {
            总用户数: allUsers.value.length,
            总页数: pagination.value.pageCount,
          });

          if (allUsers.value.length === 0) {
            message.info('暂无用户数据');
          }
        } else {
          console.error('返回数据格式错误:', response.data);
          message.error('数据格式错误');
        }
      } else {
        message.error(response.message || '加载失败');
      }
    } catch (error) {
      console.error('加载用户列表失败:', error);
      message.error('加载失败，请检查网络连接');
    } finally {
      loading.value = false;
    }
  }

  // 更新分页信息
  function updatePagination() {
    const total =
      filteredUsers.value.length > 0 ? filteredUsers.value.length : allUsers.value.length;
    pagination.value.total = total;
    pagination.value.pageCount = Math.ceil(total / pagination.value.pageSize);
    pagination.value.page = 1; // 重置到第一页
    selectedRowKeys.value = []; // 清空选中
  }

  // ==================== 搜索功能 ====================
  // 执行前端搜索
  function performSearch() {
    const keyword = searchKeyword.value.trim().toLowerCase();

    if (!keyword) {
      // 如果搜索关键词为空，显示所有数据
      filteredUsers.value = [];
      updatePagination();
      return;
    }

    console.log('执行前端搜索，关键词:', keyword);

    // 在前端过滤数据
    filteredUsers.value = allUsers.value.filter((user) => {
      const userName = (user.user_name || '').toLowerCase();
      const email = (user.email || '').toLowerCase();

      return userName.includes(keyword) || email.includes(keyword);
    });

    console.log('搜索结果:', {
      关键词: keyword,
      匹配数量: filteredUsers.value.length,
      匹配用户: filteredUsers.value.map((u) => ({ name: u.user_name, email: u.email })),
    });

    // 更新分页
    updatePagination();

    // 提示搜索结果
    if (filteredUsers.value.length === 0) {
      message.info(`没有找到与"${keyword}"匹配的用户`);
    } else {
      message.success(`找到 ${filteredUsers.value.length} 个匹配的用户`);
    }
  }

  // 搜索处理
  function handleSearch() {
    if (!searchKeyword.value.trim()) {
      // 如果搜索框为空，直接重置
      resetSearch();
      return;
    }

    // 如果还没有加载数据，先加载
    if (allUsers.value.length === 0) {
      loadAllUsers().then(() => {
        performSearch();
      });
    } else {
      performSearch();
    }
  }

  // 重置搜索
  function resetSearch() {
    searchKeyword.value = '';
    filteredUsers.value = [];
    updatePagination();
    message.info('已显示所有用户');
  }

  // 刷新
  function handleRefresh() {
    searchKeyword.value = '';
    filteredUsers.value = [];
    loadAllUsers();
  }

  // ==================== 增删改操作 ====================
  // 打开新增弹窗
  function openAddModal() {
    modalType.value = 'add';
    formData.value = {
      username: '',
      password: '',
      email: '',
    };
    showModal.value = true;
  }

  // 打开编辑弹窗
  function openEditModal(user: UserType) {
    modalType.value = 'edit';
    currentUser.value = user;
    formData.value = {
      id: user.id,
      username: user.user_name,
      email: user.email || '',
      password: '', // 编辑时密码为空，不修改
    };
    showModal.value = true;
  }

  // 提交表单
  async function handleSubmit() {
    try {
      // 表单验证
      await formRef.value?.validate();

      formLoading.value = true;

      if (modalType.value === 'add') {
        const response = await createUser(formData.value as CreateUserParams);
        if (response.status === 201) {
          message.success('创建成功');
          showModal.value = false;
          await loadAllUsers(); // 重新加载数据
          // 如果有搜索关键词，重新应用搜索
          if (searchKeyword.value) {
            performSearch();
          }
        } else {
          message.error(response.message || '创建失败');
        }
      } else {
        if (!currentUser.value) return;

        // 只传递需要更新的字段
        const updateParams: UpdateUserParams = {};
        if (formData.value.username && formData.value.username !== currentUser.value.user_name) {
          updateParams.username = formData.value.username;
        }
        if (formData.value.email !== currentUser.value.email) {
          updateParams.email = formData.value.email;
        }
        if (formData.value.password) {
          updateParams.password = formData.value.password;
        }

        // 如果没有要更新的字段，提示用户
        if (Object.keys(updateParams).length === 0) {
          message.info('没有要更新的内容');
          showModal.value = false;
          return;
        }

        const response = await updateUser(currentUser.value.id, updateParams);
        if (response.status === 200) {
          message.success('更新成功');
          showModal.value = false;
          await loadAllUsers(); // 重新加载数据
          // 如果有搜索关键词，重新应用搜索
          if (searchKeyword.value) {
            performSearch();
          }
        } else {
          message.error(response.message || '更新失败');
        }
      }
    } catch (error: any) {
      console.error('提交失败:', error);
      if (error.message) {
        message.error(error.message);
      }
    } finally {
      formLoading.value = false;
    }
  }

  // 删除单个用户
  async function handleDelete(userId: number) {
    try {
      const response = await deleteUser(userId);
      if (response.status === 200) {
        message.success('删除成功');

        // 从数据源中移除
        const sourceData = filteredUsers.value.length > 0 ? filteredUsers.value : allUsers.value;
        const index = sourceData.findIndex((user) => user.id === userId);
        if (index !== -1) {
          sourceData.splice(index, 1);

          // 更新分页
          updatePagination();

          // 如果当前页没有数据了，且不是第一页，则跳转到上一页
          if (currentPageData.value.length === 0 && pagination.value.page > 1) {
            pagination.value.page--;
          }

          // 清空选中
          selectedRowKeys.value = selectedRowKeys.value.filter((id) => id !== userId);
        }
      } else {
        message.error(response.message || '删除失败');
      }
    } catch (error) {
      console.error('删除失败:', error);
      message.error('删除失败');
    }
  }

  // 批量删除
  function handleBatchDelete() {
    if (selectedRowKeys.value.length === 0) {
      message.warning('请选择要删除的用户');
      return;
    }

    dialog.warning({
      title: '确认删除',
      content: `确定要删除选中的 ${selectedRowKeys.value.length} 个用户吗？`,
      positiveText: '确定',
      negativeText: '取消',
      onPositiveClick: async () => {
        try {
          const response = await batchDeleteUsers(selectedRowKeys.value);
          if (response.status === 200) {
            message.success(`成功删除 ${response.data.deleted_count} 个用户`);

            // 从数据源中移除
            const sourceData =
              filteredUsers.value.length > 0 ? filteredUsers.value : allUsers.value;
            allUsers.value = allUsers.value.filter(
              (user) => !selectedRowKeys.value.includes(user.id)
            );

            if (filteredUsers.value.length > 0) {
              filteredUsers.value = filteredUsers.value.filter(
                (user) => !selectedRowKeys.value.includes(user.id)
              );
            }

            // 更新分页
            updatePagination();

            // 如果当前页没有数据了，且不是第一页，则跳转到上一页
            if (currentPageData.value.length === 0 && pagination.value.page > 1) {
              pagination.value.page--;
            }

            // 清空选中
            selectedRowKeys.value = [];
          } else {
            message.error(response.message || '删除失败');
          }
        } catch (error) {
          console.error('批量删除失败:', error);
          message.error('批量删除失败');
        }
      },
    });
  }

  // ==================== 分页处理 ====================
  function handlePageChange(page: number) {
    console.log('页码变化:', page);
    pagination.value.page = page;
  }

  function handlePageSizeChange(pageSize: number) {
    console.log('每页条数变化:', pageSize);
    pagination.value.pageSize = pageSize;
    pagination.value.page = 1; // 重置到第一页
    pagination.value.pageCount = Math.ceil(currentTotal.value / pageSize);
  }

  // ==================== 监听器 ====================
  // 监听弹窗关闭，重置表单
  watch(showModal, (newVal) => {
    if (!newVal) {
      formData.value = {
        username: '',
        password: '',
        email: '',
      };
      currentUser.value = null;
    }
  });

  // ==================== 初始化 ====================
  onMounted(() => {
    // 如果不是管理员（ID不为1），重定向到首页
    if (!userStore.isAdmin) {
      message.warning('您没有权限访问该页面');
      router.push('/');
      return;
    }
    loadAllUsers();
  });
</script>

<template>
  <div class="user-manage-page">
    <n-card class="user-manage-card" :bordered="false">
      <div class="page-header">
        <div>
          <h2>用户管理</h2>
          <p>管理员可在此查看、检索、编辑并维护平台用户。</p>
        </div>
        <div class="page-header__tags">
          <n-tag size="small" type="info" round>
            {{ filteredUsers.length > 0 ? '搜索结果' : '全部用户' }}: {{ currentTotal }} 人
          </n-tag>
          <n-tag v-if="filteredUsers.length > 0" size="small" type="success" round>
            搜索: "{{ searchKeyword }}"
          </n-tag>
        </div>
      </div>

      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <n-button type="primary" @click="openAddModal">
            <template #icon>
              <n-icon :component="AddOutline" />
            </template>
            新增用户
          </n-button>
          <n-button type="error" :disabled="selectedRowKeys.length === 0" @click="handleBatchDelete">
            <template #icon>
              <n-icon :component="TrashOutline" />
            </template>
            批量删除 ({{ selectedRowKeys.length }})
          </n-button>
          <n-button @click="handleRefresh">
            <template #icon>
              <n-icon :component="RefreshOutline" />
            </template>
            刷新
          </n-button>
        </div>
        <div class="toolbar-right">
          <n-input-group>
            <n-input
              v-model:value="searchKeyword"
              placeholder="输入用户名或邮箱搜索"
              clearable
              style="width: 300px"
              @keyup.enter="handleSearch"
              @clear="resetSearch"
            >
              <template #prefix>
                <n-icon :component="SearchOutline" />
              </template>
            </n-input>
            <n-button type="primary" @click="handleSearch" :loading="searchLoading"> 搜索 </n-button>
            <n-button v-if="filteredUsers.length > 0" @click="resetSearch"> 显示全部 </n-button>
          </n-input-group>
        </div>
      </div>

      <!-- 数据表格 -->
      <n-data-table
        :columns="columns"
        :data="currentPageData"
        :loading="loading"
        :row-key="(row: UserType) => row.id"
        v-model:checked-row-keys="selectedRowKeys"
        class="user-table"
        :bordered="false"
        :single-line="false"
        max-height="550px"
        scroll-x="1000"
      >
        <template #empty>
          <n-empty :description="searchKeyword ? '没有找到匹配的用户' : '暂无用户数据'">
            <template #icon>
              <n-icon :component="PersonOutline" />
            </template>
            <template #extra>
              <n-button size="small" @click="resetSearch" v-if="searchKeyword"> 清除搜索 </n-button>
            </template>
          </n-empty>
        </template>
      </n-data-table>

      <!-- 底部统计和分页 -->
      <div class="table-footer">
        <div class="footer-right">
          <n-pagination
            v-model:page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :item-count="currentTotal"
            :page-sizes="[10, 20, 50, 100]"
            :show-size-picker="true"
            :show-quick-jumper="true"
            :show-total="(total) => `共 ${total} 条`"
            @update:page="handlePageChange"
            @update:page-size="handlePageSizeChange"
          />
        </div>
      </div>
    </n-card>
  </div>

  <!-- 新增/编辑用户弹窗 -->
  <n-modal
    v-model:show="showModal"
    :title="modalType === 'add' ? '新增用户' : '编辑用户'"
    preset="card"
    style="width: 450px"
    :bordered="false"
    :mask-closable="false"
  >
    <n-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-placement="left"
      label-width="70px"
      require-mark-placement="right-hanging"
      size="medium"
    >
      <n-form-item label="用户名" path="username">
        <n-input
          v-model:value="formData.username"
          placeholder="请输入用户名"
          :disabled="modalType === 'edit'"
        />
      </n-form-item>

      <n-form-item :label="modalType === 'add' ? '密码' : '新密码'" path="password">
        <n-input
          v-model:value="formData.password"
          type="password"
          :placeholder="modalType === 'add' ? '请输入密码（至少6位）' : '如需修改密码请输入新密码'"
          show-password-on="click"
        />
      </n-form-item>

      <n-form-item label="邮箱" path="email">
        <n-input v-model:value="formData.email" placeholder="请输入邮箱" />
      </n-form-item>
    </n-form>

    <template #footer>
      <n-space justify="end">
        <n-button @click="showModal = false">取消</n-button>
        <n-button type="primary" :loading="formLoading" @click="handleSubmit"> 确定 </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<style scoped lang="less">
  .user-manage-page {
    padding: 16px;
  }

  .user-manage-card {
    border-radius: 14px;

    :deep(.n-card__content) {
      padding: 24px;
    }
  }

  .page-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;

    h2 {
      margin: 0;
      font-size: 22px;
      line-height: 1.25;
      color: #0f172a;
    }

    p {
      margin: 6px 0 0;
      font-size: 13px;
      color: #64748b;
    }

    .page-header__tags {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
  }

  .toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;

    .toolbar-left {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .toolbar-right {
      display: flex;
      gap: 12px;
    }
  }

  .user-table {
    margin-bottom: 24px;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

    :deep(.n-data-table-th) {
      background: #f1f5f9;
      color: #1e293b;
      font-weight: 600;
      font-size: 13px;
      padding: 14px 16px;
    }

    :deep(.n-data-table-td) {
      padding: 16px;
    }

    :deep(.n-data-table-tr) {
      transition: all 0.2s ease;

      &:hover {
        background: #f8fafc;
      }
    }
  }

  .table-footer {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding-top: 16px;

    .footer-right {
      display: flex;
      justify-content: center;
      width: 100%;
    }
  }

  // 响应式适配
  @media (max-width: 768px) {
    .page-header {
      flex-direction: column;
      align-items: flex-start;
    }

    .toolbar {
      flex-direction: column;
      gap: 16px;
      align-items: stretch;

      .toolbar-left,
      .toolbar-right {
        width: 100%;
      }

      .toolbar-right {
        :deep(.n-input-group) {
          display: flex;

          .n-input {
            flex: 1;
          }
        }
      }

      .toolbar-left {
        flex-wrap: wrap;

        .n-button {
          flex: 1;
        }
      }
    }

    .table-footer {
      flex-direction: column;
      gap: 16px;
      align-items: center;

      .footer-right {
        width: 100%;
        overflow-x: auto;
        justify-content: center;
      }
    }
  }

  // 动画效果
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .user-table :deep(.n-data-table-tr) {
    animation: fadeIn 0.3s ease-out;
    animation-fill-mode: both;
  }

  // 滚动条样式
  :deep(.n-data-table-base-table-body) {
    &::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }

    &::-webkit-scrollbar-track {
      background: #f1f1f1;
      border-radius: 3px;
    }

    &::-webkit-scrollbar-thumb {
      background: #c1c1c1;
      border-radius: 3px;

      &:hover {
        background: #a8a8a8;
      }
    }
  }
</style>
