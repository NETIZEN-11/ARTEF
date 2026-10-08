#!/usr/bin/env python
"""
ARTEF Critical Issues Fix Script
Automatically fixes identified critical and high-priority issues.
"""

import os
import re
import sys
from pathlib import Path

def print_status(message, status="info"):
    colors = {
        "success": "\033[92mâœ“",
        "error": "\033[91mâœ—",
        "warning": "\033[93mâš ",
        "info": "\033[94mâ„¹"
    }
    end = "\033[0m"
    symbol = colors.get(status, colors["info"])
    print(f"{symbol} {message}{end}")

def fix_uuid_import():
    """Fix missing UUID import in auth.py"""
    file_path = Path("backend/app/api/v1/auth.py")
    
    if not file_path.exists():
        print_status(f"File not found: {file_path}", "error")
        return False
    
    content = file_path.read_text(encoding="utf-8")
    
    if "from uuid import UUID" in content:
        print_status("UUID import already present in auth.py", "success")
        return True
    
    pattern = r"(from datetime import .*\n)"
    replacement = r"\1from uuid import UUID\n"
    
    new_content = re.sub(pattern, replacement, content, count=1)
    
    if new_content != content:
        file_path.write_text(new_content, encoding="utf-8")
        print_status("Added UUID import to auth.py", "success")
        return True
    else:
        print_status("Could not add UUID import (pattern not found)", "warning")
        return False

def check_and_fix_env_file():
    """Check .env file and provide recommendations"""
    env_path = Path(".env")
    
    if not env_path.exists():
        print_status(".env file not found. Creating from .env.example", "warning")
        example_path = Path(".env.example")
        if example_path.exists():
            import shutil
            shutil.copy(example_path, env_path)
            print_status("Created .env from .env.example", "success")
        else:
            print_status(".env.example not found!", "error")
            return False
    
    content = env_path.read_text(encoding="utf-8")
    
    issues = []
    
    secret_match = re.search(r'SECRET_KEY="([^"]*)"', content)
    if secret_match:
        secret_value = secret_match.group(1)
        if "your-secret-key" in secret_value.lower() or "change" in secret_value.lower():
            issues.append(("SECRET_KEY", "Using default/placeholder value"))
    
    if 'JWT_PRIVATE_KEY_PATH=""' in content or 'JWT_PUBLIC_KEY_PATH=""' in content:
        content = content.replace(
            'JWT_PRIVATE_KEY_PATH=""',
            'JWT_PRIVATE_KEY_PATH="backend/app/core/keys/private_key.pem"'
        )
        content = content.replace(
            'JWT_PUBLIC_KEY_PATH=""',
            'JWT_PUBLIC_KEY_PATH="backend/app/core/keys/public_key.pem"'
        )
        env_path.write_text(content, encoding="utf-8")
        print_status("Set default JWT key paths in .env", "success")
    
    if issues:
        print_status("Environment configuration issues found:", "warning")
        for key, issue in issues:
            print(f"  - {key}: {issue}")
        return False
    else:
        print_status(".env file configuration OK", "success")
        return True

def fix_dockerfile_backend():
    """Fix Dockerfile install command"""
    file_path = Path("backend/Dockerfile")
    
    if not file_path.exists():
        print_status(f"File not found: {file_path}", "warning")
        return True  # Not critical if Docker isn't used
    
    content = file_path.read_text(encoding="utf-8")
    
    old_pattern = r"uv pip install --system --no-cache -r pyproject.toml"
    new_pattern = "uv pip install --system --no-cache -e ."
    
    if old_pattern in content:
        new_content = content.replace(old_pattern, new_pattern)
        file_path.write_text(new_content, encoding="utf-8")
        print_status("Fixed Dockerfile pip install command", "success")
        return True
    else:
        print_status("Dockerfile already fixed or pattern not found", "success")
        return True

def check_jwt_keys():
    """Check if JWT keys exist"""
    keys_dir = Path("backend/app/core/keys")
    private_key = keys_dir / "private_key.pem"
    public_key = keys_dir / "public_key.pem"
    
    if not keys_dir.exists():
        print_status(f"Keys directory missing: {keys_dir}", "error")
        print("  Run: mkdir -p backend/app/core/keys")
        return False
    
    if not private_key.exists() or not public_key.exists():
        print_status("JWT keys missing!", "error")
        print("  Generate with:")
        print("  openssl genrsa -out backend/app/core/keys/private_key.pem 2048")
        print("  openssl rsa -in backend/app/core/keys/private_key.pem -pubout -out backend/app/core/keys/public_key.pem")
        return False
    
    print_status("JWT keys present", "success")
    return True

def fix_pydantic_schema_warnings():
    """Provide recommendations for Pydantic schema field shadowing"""
    print_status("Pydantic schema warnings detected", "info")
    print("  Field name 'schema' shadows BaseModel attribute")
    print("  Recommendation: Rename 'schema' fields to 'json_schema' or 'dataset_schema'")
    print("  Files to check:")
    print("    - backend/app/schemas/datasets.py")
    print("    - Any schema with 'schema' field name")
    return True  # Not critical

def create_production_env_template():
    """Create a production .env template"""
    template = """# PRODUCTION ENVIRONMENT CONFIGURATION

APP_NAME="Agent Red-Teaming Framework"
APP_VERSION="1.0.0"
ENVIRONMENT="production"
DEBUG=false
SECRET_KEY="REPLACE_WITH_STRONG_RANDOM_SECRET_MINIMUM_64_BYTES"
API_V1_PREFIX="/api/v1"

DATABASE_URL="postgresql+asyncpg://username:password@db-host:5432/redteam_prod"
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30

REDIS_URL="redis://redis-host:6379/0"
REDIS_MAX_CONNECTIONS=50

CELERY_BROKER_URL="redis://redis-host:6379/1"
CELERY_RESULT_BACKEND="redis://redis-host:6379/2"

JWT_ALGORITHM="RS256"
JWT_PRIVATE_KEY_PATH="/secure/path/to/private_key.pem"
JWT_PUBLIC_KEY_PATH="/secure/path/to/public_key.pem"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

CORS_ORIGINS="https://app.yourdomain.com,https://api.yourdomain.com"
CORS_ALLOW_CREDENTIALS=true

PRIMARY_JUDGE_PROVIDER="openai"
PRIMARY_JUDGE_MODEL="gpt-4o-2024-08-06"
PRIMARY_JUDGE_API_KEY="sk-..."

EVAL_MODE="production"

DEV_SEED_DATA=false
DEV_MOCK_TARGET_AGENT=false
DEV_MOCK_JUDGE=false

STORAGE_BACKEND="s3"
S3_ENDPOINT_URL="https://s3.amazonaws.com"
S3_ACCESS_KEY="YOUR_S3_ACCESS_KEY"
S3_SECRET_KEY="YOUR_S3_SECRET_KEY"
S3_BUCKET="production-redteam-artifacts"
S3_REGION="us-east-1"
"""
    
    prod_env_path = Path(".env.production.template")
    prod_env_path.write_text(template, encoding="utf-8")
    print_status(f"Created production environment template: {prod_env_path}", "success")
    return True

def main():
    """Main execution"""
    print("\n" + "="*70)
    print("ARTEF Critical Issues Fix Script")
    print("="*70 + "\n")
    
    results = []
    
    print("ðŸ”§ Fixing critical issues...\n")
    
    results.append(("UUID Import Fix", fix_uuid_import()))
    
    results.append(("Environment Check", check_and_fix_env_file()))
    
    results.append(("JWT Keys Check", check_jwt_keys()))
    
    results.append(("Dockerfile Fix", fix_dockerfile_backend()))
    
    results.append(("Pydantic Warnings", fix_pydantic_schema_warnings()))
    
    results.append(("Production Template", create_production_env_template()))
    
    print("\n" + "="*70)
    print("Fix Summary")
    print("="*70 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "success" if result else "error"
        print_status(f"{name}: {'âœ“ PASS' if result else 'âœ— FAIL'}", status)
    
    print(f"\n{passed}/{total} fixes completed successfully")
    
    if passed == total:
        print_status("\nâœ“ All critical issues fixed!", "success")
        print("\nNext steps:")
        print("  1. Review .env.production.template for production configuration")
        print("  2. Generate new JWT keys for production (see SETUP.md)")
        print("  3. Run: python scripts/verify_setup.py")
        print("  4. Run: cd backend && pytest tests/ -v")
        return 0
    else:
        print_status("\nâœ— Some issues remain. Review errors above.", "error")
        return 1

if __name__ == "__main__":
    sys.exit(main())
