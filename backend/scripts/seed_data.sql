-- Seed data for MR Game Operations System
-- Generated: 2025-10-11

-- ============================================
-- 1. System Configurations
-- ============================================
INSERT INTO system_configs (config_key, config_value, value_type, category, description, is_editable, created_at, updated_at)
VALUES
    ('balance_threshold', '100.00', 'float', 'business', '账户余额预警阈值（元）', true, NOW(), NOW()),
    ('session_timeout', '1800', 'integer', 'security', '会话超时时间（秒）', true, NOW(), NOW()),
    ('payment_timeout', '300', 'integer', 'business', '支付超时时间（秒）', true, NOW(), NOW())
ON CONFLICT (config_key) DO NOTHING;

-- ============================================
-- 2. Admin Accounts
-- ============================================
-- Check if admin already exists before inserting
DO $$
BEGIN
    -- Super Admin (all permissions)
    IF NOT EXISTS (SELECT 1 FROM admin_accounts WHERE username = 'superadmin') THEN
        INSERT INTO admin_accounts (id, username, password_hash, full_name, email, phone, role, permissions, is_active, last_login_at, last_login_ip, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'superadmin',
            '$2b$12$Vx7X1BhBCDhR9i3EnKftwuXrWgbpFqrVfc3vbOIacp.8y3D0Y3mWG',
            '系统管理员',
            'admin@example.com',
            '13800138000',
            'super_admin',
            '["*"]'::jsonb,
            true,
            NULL,
            NULL,
            NOW(),
            NOW()
        );
    END IF;

    -- Admin - Zhang (operator management)
    IF NOT EXISTS (SELECT 1 FROM admin_accounts WHERE username = 'admin_zhang') THEN
        INSERT INTO admin_accounts (id, username, password_hash, full_name, email, phone, role, permissions, is_active, last_login_at, last_login_ip, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'admin_zhang',
            '$2b$12$Vx7X1BhBCDhR9i3EnKftwuXrWgbpFqrVfc3vbOIacp.8y3D0Y3mWG',
            '张管理',
            'zhang@example.com',
            '13800138001',
            'admin',
            '["operator:read", "operator:write", "operator:audit"]'::jsonb,
            true,
            NULL,
            NULL,
            NOW(),
            NOW()
        );
    END IF;

    -- Admin - Li (system config)
    IF NOT EXISTS (SELECT 1 FROM admin_accounts WHERE username = 'admin_li') THEN
        INSERT INTO admin_accounts (id, username, password_hash, full_name, email, phone, role, permissions, is_active, last_login_at, last_login_ip, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'admin_li',
            '$2b$12$Vx7X1BhBCDhR9i3EnKftwuXrWgbpFqrVfc3vbOIacp.8y3D0Y3mWG',
            '李管理',
            'li@example.com',
            '13800138002',
            'admin',
            '["config:read", "config:write", "operator:read"]'::jsonb,
            true,
            NULL,
            NULL,
            NOW(),
            NOW()
        );
    END IF;
END $$;

-- ============================================
-- 3. Finance Accounts
-- ============================================
DO $$
BEGIN
    -- Finance - Wang (recharge approval)
    IF NOT EXISTS (SELECT 1 FROM finance_accounts WHERE username = 'finance_wang') THEN
        INSERT INTO finance_accounts (id, username, password_hash, full_name, email, phone, role, permissions, is_active, last_login_at, last_login_ip, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'finance_wang',
            '$2b$12$CchkwqCQkLYZtS25roVS4epzwRG428SmaHr6/2xo7qhxXNFSqh/Vm',
            '王财务',
            'wang@example.com',
            '13800138003',
            'specialist',
            '["recharge:approve", "invoice:read", "finance:read"]'::jsonb,
            true,
            NULL,
            NULL,
            NOW(),
            NOW()
        );
    END IF;

    -- Finance - Liu (invoice management)
    IF NOT EXISTS (SELECT 1 FROM finance_accounts WHERE username = 'finance_liu') THEN
        INSERT INTO finance_accounts (id, username, password_hash, full_name, email, phone, role, permissions, is_active, last_login_at, last_login_ip, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'finance_liu',
            '$2b$12$CchkwqCQkLYZtS25roVS4epzwRG428SmaHr6/2xo7qhxXNFSqh/Vm',
            '刘财务',
            'liu@example.com',
            '13800138004',
            'specialist',
            '["invoice:manage", "finance:read"]'::jsonb,
            true,
            NULL,
            NULL,
            NOW(),
            NOW()
        );
    END IF;
END $$;

-- ============================================
-- 4. Operator Accounts (with balance and API keys)
-- ============================================
DO $$
BEGIN
    -- VIP Tier Operator
    IF NOT EXISTS (SELECT 1 FROM operator_accounts WHERE username = 'operator_vip') THEN
        INSERT INTO operator_accounts (id, username, password_hash, full_name, email, phone, api_key, api_key_hash, balance, customer_tier, is_active, last_login_at, last_login_ip, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'operator_vip',
            '$2b$12$XfuFqZdnDgW2iLxO5qjchufN6C6FeRNhbseU/SkKG7Tk3Sh.hy1t6',
            '赵总(VIP游戏公司)',
            'zhao@vipgame.com',
            '13900139000',
            'vip_' || encode(gen_random_bytes(24), 'hex'),
            '$2b$12$XfuFqZdnDgW2iLxO5qjchufN6C6FeRNhbseU/SkKG7Tk3Sh.hy1t6',
            5000.00,
            'vip',
            true,
            NULL,
            NULL,
            NOW(),
            NOW()
        );
    END IF;

    -- Standard Tier Operator
    IF NOT EXISTS (SELECT 1 FROM operator_accounts WHERE username = 'operator_standard') THEN
        INSERT INTO operator_accounts (id, username, password_hash, full_name, email, phone, api_key, api_key_hash, balance, customer_tier, is_active, last_login_at, last_login_ip, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'operator_standard',
            '$2b$12$XfuFqZdnDgW2iLxO5qjchufN6C6FeRNhbseU/SkKG7Tk3Sh.hy1t6',
            '钱经理(标准游戏工作室)',
            'qian@standardgame.com',
            '13900139001',
            'std_' || encode(gen_random_bytes(24), 'hex'),
            '$2b$12$XfuFqZdnDgW2iLxO5qjchufN6C6FeRNhbseU/SkKG7Tk3Sh.hy1t6',
            1000.00,
            'standard',
            true,
            NULL,
            NULL,
            NOW(),
            NOW()
        );
    END IF;

    -- Trial Tier Operator
    IF NOT EXISTS (SELECT 1 FROM operator_accounts WHERE username = 'operator_trial') THEN
        INSERT INTO operator_accounts (id, username, password_hash, full_name, email, phone, api_key, api_key_hash, balance, customer_tier, is_active, last_login_at, last_login_ip, created_at, updated_at)
        VALUES (
            gen_random_uuid(),
            'operator_trial',
            '$2b$12$XfuFqZdnDgW2iLxO5qjchufN6C6FeRNhbseU/SkKG7Tk3Sh.hy1t6',
            '孙开发(试用游戏团队)',
            'sun@trialgame.com',
            '13900139002',
            'trial_' || encode(gen_random_bytes(24), 'hex'),
            '$2b$12$XfuFqZdnDgW2iLxO5qjchufN6C6FeRNhbseU/SkKG7Tk3Sh.hy1t6',
            50.00,
            'trial',
            true,
            NULL,
            NULL,
            NOW(),
            NOW()
        );
    END IF;
END $$;

-- ============================================
-- Verification Queries
-- ============================================
-- SELECT config_key, config_value, value_type, category FROM system_configs;
-- SELECT username, full_name, role, is_active FROM admin_accounts;
-- SELECT username, full_name, role, is_active FROM finance_accounts;
-- SELECT username, company_name, balance, tier, status FROM operator_accounts;
