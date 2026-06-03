-- 抽取历史表：用于存储每次节点/关系抽取的快照，支持在侧栏展示历史并查看对应图谱
-- 请在 MySQL 中执行此脚本创建表

USE finkg1;

CREATE TABLE IF NOT EXISTS extraction_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    run_id VARCHAR(128) NOT NULL COMMENT '抽取运行唯一标识(UUID)',
    project_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    user_id VARCHAR(64) NULL COMMENT '操作人（与 graph_project.creator 对齐）',
    run_type VARCHAR(32) NOT NULL COMMENT '抽取类型: nodes | relations | master | incremental',
    title VARCHAR(255) NULL COMMENT '侧栏列表标题（与会话摘要类似）',
    sample_ids JSON COMMENT '使用的样本ID列表',
    nodes_count INT DEFAULT 0 COMMENT '节点数量',
    edges_count INT DEFAULT 0 COMMENT '关系数量',
    nodes_snapshot LONGTEXT COMMENT '节点快照(JSON数组)',
    edges_snapshot LONGTEXT COMMENT '关系快照(JSON数组)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_run_id (run_id),
    KEY idx_project_id (project_id),
    KEY idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='图谱抽取历史快照表';
