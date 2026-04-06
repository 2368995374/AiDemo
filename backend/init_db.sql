-- ============================================================
-- AI 编码助手 Demo - MySQL 建库建表脚本
-- 数据库名称: AiDemo
-- ============================================================

-- 创建数据库（如不存在）
CREATE DATABASE IF NOT EXISTS AiDemo
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE AiDemo;

-- ============================================================
-- 1. 会话表 sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    id          BIGINT          PRIMARY KEY AUTO_INCREMENT  COMMENT '会话ID',
    title       VARCHAR(255)    NOT NULL                    COMMENT '会话标题',
    system_prompt TEXT          NULL                        COMMENT '系统提示词',
    model_name  VARCHAR(100)    NULL                        COMMENT '使用的模型名称',
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    is_deleted  TINYINT(1)      NOT NULL DEFAULT 0          COMMENT '软删除标记 0=正常 1=已删除'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天会话表';

-- ============================================================
-- 2. 消息表 messages
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    id              BIGINT      PRIMARY KEY AUTO_INCREMENT  COMMENT '消息ID',
    session_id      BIGINT      NOT NULL                    COMMENT '所属会话ID',
    role            VARCHAR(20) NOT NULL                    COMMENT '角色: system/user/assistant',
    content         LONGTEXT    NOT NULL                    COMMENT '消息内容',
    sequence_no     INT         NOT NULL                    COMMENT '消息在会话中的顺序号',
    token_count     INT         NULL                        COMMENT 'token 数量（可选）',
    generation_params JSON      NULL                        COMMENT '生成参数快照（可选）',
    created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP  COMMENT '创建时间',
    CONSTRAINT fk_messages_session FOREIGN KEY (session_id) REFERENCES sessions(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息表';

-- ============================================================
-- 3. 索引
-- ============================================================
CREATE INDEX idx_sessions_updated_at
    ON sessions(updated_at);

CREATE INDEX idx_sessions_is_deleted
    ON sessions(is_deleted);

CREATE INDEX idx_messages_session_sequence
    ON messages(session_id, sequence_no);
