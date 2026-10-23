-- Nex/CppMind 本地开发库初始化（WSL PostgreSQL 18）
-- 幂等：重复执行不报错
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'cppmind') THEN
    CREATE ROLE cppmind LOGIN PASSWORD 'cppmind';
  END IF;
END
$$;

ALTER ROLE cppmind WITH LOGIN PASSWORD 'cppmind';
SELECT 'role ok' AS step;
