-- 为 codo_biz 增加 parent_id 字段, 用于业务父子关系
-- parent_id = 0 表示 root 业务; 非 0 时必须指向一个 root 业务 (业务层级最多两级)
-- 该约束在应用层 (services/biz_service.py: validate_biz_parent) 强制校验

ALTER TABLE `codo_biz`
    ADD COLUMN `parent_id` INT NOT NULL DEFAULT 0 COMMENT '父业务ID, 0为root业务' AFTER `biz_cn_name`,
    ADD INDEX `ix_codo_biz_parent_id` (`parent_id`);
