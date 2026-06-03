-- 图谱抽取历史表增强：与「会话标题 / 操作人」对齐，便于侧栏展示与权限过滤
-- 在已有 extraction_history 表上执行（见 create_extraction_history.sql）
-- 若列已存在会报错，可忽略对应语句或先检查 INFORMATION_SCHEMA

USE finkg1;

ALTER TABLE extraction_history
  ADD COLUMN user_id VARCHAR(64) NULL COMMENT '操作人（与 graph_project.creator 对齐）' AFTER project_id;

ALTER TABLE extraction_history
  ADD COLUMN title VARCHAR(255) NULL COMMENT '列表展示标题（与会话首条摘要类似）' AFTER run_type;

ALTER TABLE extraction_history MODIFY run_id VARCHAR(128);
