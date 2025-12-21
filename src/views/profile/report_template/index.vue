<template>
  <div class="user-profile-container">
    <n-card :bordered="false" class="profile-card">
      <!-- 模板标签页 -->
      <div class="template-section">
        <div class="template-header-with-actions">
          <n-tabs
            v-model:value="activeTemplate"
            type="line"
            size="large"
            justify-content="start"
            animated
            class="template-tabs"
          >
            <n-tab name="before_report" class="tab-item">
              <div class="tab-content">
                <div class="tab-icon">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path d="M18 8h1a4 4 0 0 1 0 8h-1" />
                    <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z" />
                    <line x1="6" y1="1" x2="6" y2="4" />
                    <line x1="10" y1="1" x2="10" y2="4" />
                    <line x1="14" y1="1" x2="14" y2="4" />
                  </svg>
                </div>
                <div class="tab-text">
                  <div class="tab-name">盘前分析</div>
                </div>
              </div>
            </n-tab>
            <n-tab name="noon_report" class="tab-item">
              <div class="tab-content">
                <div class="tab-icon">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <circle cx="12" cy="12" r="5" />
                    <line x1="12" y1="1" x2="12" y2="3" />
                    <line x1="12" y1="21" x2="12" y2="23" />
                    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                    <line x1="1" y1="12" x2="3" y2="12" />
                    <line x1="21" y1="12" x2="23" y2="12" />
                    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                  </svg>
                </div>
                <div class="tab-text">
                  <div class="tab-name">午间分析</div>
                </div>
              </div>
            </n-tab>
            <n-tab name="working_report" class="tab-item">
              <div class="tab-content">
                <div class="tab-icon">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <line x1="12" y1="2" x2="12" y2="6" />
                    <line x1="12" y1="18" x2="12" y2="22" />
                    <line x1="4.93" y1="4.93" x2="7.76" y2="7.76" />
                    <line x1="16.24" y1="16.24" x2="19.07" y2="19.07" />
                    <line x1="2" y1="12" x2="6" y2="12" />
                    <line x1="18" y1="12" x2="22" y2="12" />
                    <line x1="4.93" y1="19.07" x2="7.76" y2="16.24" />
                    <line x1="16.24" y1="7.76" x2="19.07" y2="4.93" />
                    <circle cx="12" cy="12" r="2" />
                  </svg>
                </div>
                <div class="tab-text">
                  <div class="tab-name">盘中分析</div>
                </div>
              </div>
            </n-tab>
            <n-tab name="after_report" class="tab-item">
              <div class="tab-content">
                <div class="tab-icon">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                  </svg>
                </div>
                <div class="tab-text">
                  <div class="tab-name">盘后分析</div>
                </div>
              </div>
            </n-tab>
          </n-tabs>

          <div class="template-actions">
            <n-button
              v-if="!isEditing"
              type="primary"
              @click="enterEditMode"
              size="medium"
              class="edit-btn"
            >
              <template #icon>
                <n-icon>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                </n-icon>
              </template>
              编辑模板
            </n-button>
            <div v-else class="edit-buttons">
              <n-button type="default" @click="cancelEdit" size="medium" class="cancel-btn">
                <template #icon>
                  <n-icon>
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </n-icon>
                </template>
                取消
              </n-button>
              <n-button
                type="primary"
                @click="handleSubmit"
                :loading="loading"
                size="medium"
                class="save-btn"
              >
                <template #icon>
                  <n-icon>
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </n-icon>
                </template>
                保存更改
              </n-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 模板编辑区 -->
      <div class="editor-section">
        <div class="editor-header">
          <h4 class="editor-title">
            <span class="title-badge">{{ getActiveTemplateTitle() }}</span>
            <span class="title-text">模板内容</span>
          </h4>
          <div class="editor-hint" v-if="!isEditing">
            <n-icon size="16" color="#8c8c8c">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
            </n-icon>
            <span>点击"编辑模板"按钮开始修改</span>
          </div>
          <div class="editor-hint" v-else>
            <n-icon size="16" color="#52c41a">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M16 8s-.1 0 0 0" />
                <path d="M8 8s-.1 0 0 0" />
                <path d="M9 13s1 1 3 1 3-1 3-1" />
              </svg>
            </n-icon>
            <span>编辑模式已开启，请修改模板内容</span>
          </div>
        </div>

        <div class="editor-container">
          <!-- 盘前分析模板 -->
          <n-card 
            v-show="activeTemplate === 'before_report'" 
            :bordered="false"
            class="template-editor-card"
          >
            <n-input
              type="textarea"
              v-model:value="formData.report_template.before_report"
              :disabled="!isEditing"
              :autosize="{ minRows: 18, maxRows: 35 }"
              placeholder="请输入盘前分析模板内容..."
              class="template-editor"
              :class="{ 'disabled-editor': !isEditing }"
            />
          </n-card>

          <!-- 午间分析模板 -->
          <n-card 
            v-show="activeTemplate === 'noon_report'" 
            :bordered="false"
            class="template-editor-card"
          >
            <n-input
              type="textarea"
              v-model:value="formData.report_template.noon_report"
              :disabled="!isEditing"
              :autosize="{ minRows: 18, maxRows: 35 }"
              placeholder="请输入午间分析模板内容..."
              class="template-editor"
              :class="{ 'disabled-editor': !isEditing }"
            />
          </n-card>

          <!-- 盘中分析模板 -->
          <n-card 
            v-show="activeTemplate === 'working_report'" 
            :bordered="false"
            class="template-editor-card"
          >
            <n-input
              type="textarea"
              v-model:value="formData.report_template.working_report"
              :disabled="!isEditing"
              :autosize="{ minRows: 18, maxRows: 35 }"
              placeholder="请输入盘中分析模板内容..."
              class="template-editor"
              :class="{ 'disabled-editor': !isEditing }"
            />
          </n-card>

          <!-- 盘后分析模板 -->
          <n-card 
            v-show="activeTemplate === 'after_report'" 
            :bordered="false"
            class="template-editor-card"
          >
            <n-input
              type="textarea"
              v-model:value="formData.report_template.after_report"
              :disabled="!isEditing"
              :autosize="{ minRows: 18, maxRows: 35 }"
              placeholder="请输入盘后分析模板内容..."
              class="template-editor"
              :class="{ 'disabled-editor': !isEditing }"
            />
          </n-card>
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
  import { ref, reactive, onMounted } from 'vue';
  import { useMessage } from 'naive-ui';
  import { useUser } from '@/store/modules/user';
  import { UserInfoType } from '@/api/user/user';
  import { mockEmptyUserInfo } from '../../../../mock/user';
  import { parseStr, parseTime } from '@/api/time';
  import { getUserInvestmentProfile, updateUserInvestmentProfile } from '@/api/user/user';

  const formRef = ref<any>(null);
  const loading = ref(false);
  const message = useMessage();
  const userStore = useUser();

  const isDataReady = ref(false);
  const isEditing = ref(false);
  const activeTemplate = ref<'before_report' | 'noon_report' | 'working_report' | 'after_report'>('before_report');
  const originalFormData = ref<UserInfoType>({ ...mockEmptyUserInfo });

  // 获取当前激活模板的标题
  const getActiveTemplateTitle = () => {
    switch (activeTemplate.value) {
      case 'before_report': return '盘前分析';
      case 'noon_report': return '午间分析';
      case 'working_report': return '盘中分析';
      case 'after_report': return '盘后分析';
      default: return '模板编辑';
    }
  };

  // 表单数据 - 先初始化为空结构
  const formData = reactive<UserInfoType>({
    name: '',
    account: '',
    password: '',
    report_template: {
      before_report: '',
      noon_report: '',
      working_report: '',
      after_report: '',
    },
    user_investment_profile: {
      personalized_investment_goals: {
        investment_tenure: {
          tenure_type: '',
          pecific_years: 0,
          tenure_description: '',
        },
        expected_return: {
          annualized_return_rate: 0,
          return_stability: '',
          return_description: '',
        },
        risk_tolerance: {
          risk_level: '',
          loss_tolerance_ratio: 0,
          risk_description: '',
        },
      },
      current_holdings: { holding_count: 0, holdings_list: [] },
      watchlist: { watchlist_count: 0, watchlist_list: [] },
    },
  });

  // 进入编辑模式
  const enterEditMode = () => {
    isEditing.value = true;
    originalFormData.value = JSON.parse(JSON.stringify(formData));
  };

  // 取消编辑
  const cancelEdit = () => {
    isEditing.value = false;
    Object.assign(formData, JSON.parse(JSON.stringify(originalFormData.value)));
  };

  // 初始化数据
  onMounted(async () => {
    loading.value = true;
    try {
      const response = await getUserInvestmentProfile(userStore.getToken);

      if (response.code === 0) {
        const userProfile = response.data;

        // 使用后端返回的数据更新 formData
        Object.assign(formData, {
          ...userProfile,
          // 确保 report_template 有默认值
          report_template: {
            before_report: userProfile.report_template?.before_report || '',
            noon_report: userProfile.report_template?.noon_report || '',
            working_report: userProfile.report_template?.working_report || '',
            after_report: userProfile.report_template?.after_report || '',
          }
        });

        // 处理时间格式转换
        if (formData.user_investment_profile.current_holdings?.holdings_list) {
          formData.user_investment_profile.current_holdings.holdings_list.forEach((stock) => {
            if (typeof stock.purchase_time === 'string') {
              stock.purchase_time = parseTime(stock.purchase_time);
            }
          });
        }

        if (formData.user_investment_profile.watchlist?.watchlist_list) {
          formData.user_investment_profile.watchlist.watchlist_list.forEach((stock) => {
            if (typeof stock.add_time === 'string') {
              stock.add_time = parseTime(stock.add_time);
            }
          });
        }

        originalFormData.value = JSON.parse(JSON.stringify(formData));
        isDataReady.value = true;
        message.success('模板数据加载成功');
      } else {
        message.error(response.msg || '数据加载失败');
        // 使用空数据
        Object.assign(formData, mockEmptyUserInfo);
      }
    } catch (e: any) {
      console.error('加载模板数据失败:', e);
      message.error('网络异常，加载模板数据失败');
      // 使用空数据
      Object.assign(formData, mockEmptyUserInfo);
    } finally {
      loading.value = false;
    }
  });

  // 保存时转换时间格式
  const transTimeToString = (userInfo: UserInfoType) => {
    if (userInfo.user_investment_profile.current_holdings?.holdings_list) {
      userInfo.user_investment_profile.current_holdings.holdings_list.forEach((stock) => {
        if (stock.purchase_time) {
          stock.purchase_time = parseStr(stock.purchase_time);
        }
      });
    }
    if (userInfo.user_investment_profile.watchlist?.watchlist_list) {
      userInfo.user_investment_profile.watchlist.watchlist_list.forEach((stock) => {
        if (stock.add_time) {
          stock.add_time = parseStr(stock.add_time);
        }
      });
    }
  };

  // 提交表单
  const handleSubmit = async () => {
    loading.value = true;

    // 创建深拷贝
    const transData = JSON.parse(JSON.stringify(formData));
    transTimeToString(transData);

    // 准备请求参数
    const requestParams = {
      user_investment_profile: transData.user_investment_profile,
      user_report_template: transData.report_template,
    };

    try {
      // 更新本地用户信息
      userStore.setUserInfo(transData);

      // 调用 API 更新数据
      const response = await updateUserInvestmentProfile(userStore.getToken, requestParams);

      if (response.code === 0) {
        message.success('模板保存成功');
        // 更新原始数据，退出编辑模式
        originalFormData.value = JSON.parse(JSON.stringify(formData));
        isEditing.value = false;
      } else {
        message.error(response.msg || '保存失败');
      }
    } catch (e: any) {
      console.error('保存模板失败:', e);
      message.error('网络异常，修改失败');
    } finally {
      loading.value = false;
    }
  };
</script>

<style scoped>
  .user-profile-container {
    min-height: 100vh;
    padding: 24px;
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  }

  .page-header {
    margin-bottom: 32px;
  }

  .page-title {
    font-size: 28px;
    font-weight: 600;
    color: #1a1a1a;
    margin: 0 0 8px 0;
    line-height: 1.3;
  }

  .page-subtitle {
    font-size: 15px;
    color: #666;
    margin: 0;
    line-height: 1.5;
  }

  .profile-card {
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
    border: 1px solid rgba(0, 0, 0, 0.04);
    overflow: hidden;
    padding: 32px;
  }

  .action-header {
    margin-bottom: 32px;
  }

  .section-title {
    font-size: 20px;
    font-weight: 600;
    color: #1a1a1a;
    margin: 0 0 8px 0;
  }

  .section-description {
    font-size: 14px;
    color: #666;
    margin: 0;
    line-height: 1.5;
    max-width: 600px;
  }

  .template-section {
    margin-bottom: 32px;
  }

  .template-header-with-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    background: #fafafa;
    border-radius: 12px;
    padding: 8px;
  }

  .template-tabs {
    flex: 1;
    background: transparent;
  }

  .template-actions {
    flex-shrink: 0;
    display: flex;
    gap: 12px;
    padding-right: 12px;
  }

  .tab-item {
    padding: 12px 20px !important;
    transition: all 0.3s ease;
    border-radius: 8px;
  }

  .tab-item.n-tab--active {
    background: #ffffff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .tab-content {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .tab-icon {
    color: #1890ff;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-left: 5px;
  }

  .tab-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-right: 5px;
  }

  .tab-name {
    font-size: 14px;
    font-weight: 500;
    color: #1a1a1a;
    white-space: nowrap;
  }

  .edit-btn {
    background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
    border: none;
    border-radius: 8px;
    font-weight: 500;
    padding: 0 16px;
    height: 36px;
    font-size: 14px;
  }

  .edit-buttons {
    display: flex;
    gap: 8px;
  }

  .cancel-btn {
    border-radius: 8px;
    border: 1px solid #d9d9d9;
    padding: 0 16px;
    height: 36px;
    font-size: 14px;
  }

  .save-btn {
    background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
    border: none;
    border-radius: 8px;
    font-weight: 500;
    padding: 0 16px;
    height: 36px;
    font-size: 14px;
  }

  .editor-section {
    background: #fafafa;
    border-radius: 12px;
    padding: 24px;
  }

  .editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }

  .editor-title {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 0;
  }

  .title-badge {
    background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
  }

  .title-text {
    font-size: 16px;
    font-weight: 600;
    color: #1a1a1a;
  }

  .editor-hint {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }

  .editor-container {
    margin-bottom: 24px;
  }

  .template-editor-card {
    background: #ffffff;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    padding: 0;
  }

  .template-editor {
    font-family: 'SF Mono', Monaco, 'Cascadia Code', Consolas, monospace;
    font-size: 13px;
    line-height: 1.6;
    padding: 16px;
    background: transparent;
    border: none;
    color: #1a1a1a;
    resize: vertical;
  }

  .template-editor::placeholder {
    color: #bfbfbf;
  }

  .template-editor:focus {
    outline: none;
    box-shadow: none;
  }

  .disabled-editor {
    background: #f8f9fa;
    cursor: not-allowed;
    color: #666;
  }

  @media (max-width: 768px) {
    .user-profile-container {
      padding: 16px;
    }

    .profile-card {
      padding: 20px;
    }

    .template-header-with-actions {
      flex-direction: column;
      gap: 16px;
      padding: 16px;
    }

    .template-actions {
      width: 100%;
      justify-content: flex-end;
      padding-right: 0;
    }

    .tab-content {
      flex-direction: column;
      text-align: center;
      gap: 4px;
    }

    .tab-item {
      padding: 10px 16px !important;
    }

    .tab-name {
      font-size: 13px;
    }

    .editor-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 12px;
    }

    .edit-btn,
    .cancel-btn,
    .save-btn {
      height: 32px;
      font-size: 13px;
      padding: 0 12px;
    }
  }

  @media (max-width: 480px) {
    .template-tabs {
      overflow-x: auto;
      width: 100%;
    }
    
    .tab-item {
      padding: 8px 12px !important;
      font-size: 12px;
    }
    
    .tab-name {
      font-size: 12px;
    }
    
    .edit-buttons {
      flex-direction: column;
      width: 100%;
    }
    
    .edit-btn,
    .cancel-btn,
    .save-btn {
      width: 100%;
      justify-content: center;
    }
  }
</style>
